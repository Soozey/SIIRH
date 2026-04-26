from __future__ import annotations

import json
import inspect
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models


def parse_period(period: str) -> tuple[int, int]:
    value = (period or "").strip()
    try:
        year_text, month_text = value.split("-", 1)
        year = int(year_text)
        month = int(month_text)
    except (AttributeError, ValueError):
        raise HTTPException(status_code=400, detail="Période invalide. Format attendu YYYY-MM.")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mois de paie invalide.")
    return month, year


def format_period(month: int, year: int) -> str:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mois de paie invalide.")
    return f"{int(year):04d}-{int(month):02d}"


def get_or_create_payroll_period(db: Session, employer_id: int, month: int, year: int) -> models.PayrollPeriod:
    period = (
        db.query(models.PayrollPeriod)
        .filter(
            models.PayrollPeriod.employer_id == employer_id,
            models.PayrollPeriod.month == month,
            models.PayrollPeriod.year == year,
        )
        .first()
    )
    if period is not None:
        return period
    period = models.PayrollPeriod(employer_id=employer_id, month=month, year=year, is_closed=False)
    db.add(period)
    db.flush()
    return period


def is_payroll_period_closed(db: Session, employer_id: int, month: int, year: int) -> bool:
    period = (
        db.query(models.PayrollPeriod)
        .filter(
            models.PayrollPeriod.employer_id == employer_id,
            models.PayrollPeriod.month == month,
            models.PayrollPeriod.year == year,
        )
        .first()
    )
    return bool(period and period.is_closed)


def ensure_payroll_period_open(db: Session, employer_id: int, period: Optional[str] = None, month: Optional[int] = None, year: Optional[int] = None) -> None:
    if period:
        month, year = parse_period(period)
    if month is None or year is None:
        raise HTTPException(status_code=400, detail="Période de paie requise.")
    if is_payroll_period_closed(db, employer_id, int(month), int(year)):
        raise HTTPException(status_code=423, detail="Période de paie clôturée: modifications interdites.")


def _resolve_period_from_endpoint(db: Session, kwargs: dict[str, Any]) -> tuple[Optional[int], Optional[str]]:
    payroll_run_id = kwargs.get("payroll_run_id")
    if payroll_run_id is not None:
        run = db.query(models.PayrollRun).filter(models.PayrollRun.id == payroll_run_id).first()
        if run is None:
            return None, None
        return run.employer_id, run.period

    employer_id = kwargs.get("employer_id")
    period = kwargs.get("period")
    if employer_id is not None and period:
        return int(employer_id), str(period)

    payload = kwargs.get("payload") or kwargs.get("values") or kwargs.get("request")
    worker_id = getattr(payload, "worker_id", None)
    period = getattr(payload, "period", None)
    if worker_id is not None and period:
        worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        if worker is None:
            return None, None
        return worker.employer_id, str(period)

    return None, None


def payroll_period_write_guard(func: Callable) -> Callable:
    def _check(kwargs: dict[str, Any]) -> None:
        db = kwargs.get("db")
        if isinstance(db, Session):
            employer_id, period = _resolve_period_from_endpoint(db, kwargs)
            if employer_id is not None and period:
                ensure_payroll_period_open(db, employer_id, period=period)

    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _check(kwargs)
            return await func(*args, **kwargs)

        return async_wrapper

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _check(kwargs)
        return func(*args, **kwargs)

    return wrapper


def _float_total(totals: dict[str, Any], key: str) -> float:
    try:
        return float(totals.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def close_payroll_period(
    db: Session,
    employer_id: int,
    month: int,
    year: int,
    closed_by_user_id: Optional[int] = None,
) -> tuple[models.PayrollPeriod, int]:
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if employer is None:
        raise HTTPException(status_code=404, detail="Employeur introuvable.")

    period_text = format_period(month, year)
    period = get_or_create_payroll_period(db, employer_id, month, year)
    if period.is_closed:
        existing_count = db.query(models.PayrollArchive.id).filter(models.PayrollArchive.payroll_period_id == period.id).count()
        return period, existing_count

    from ..routers.payroll import generate_preview_data

    workers = (
        db.query(models.Worker)
        .filter(models.Worker.employer_id == employer_id, models.Worker.is_active.is_(True))
        .order_by(models.Worker.id.asc())
        .all()
    )
    db.query(models.PayrollArchive).filter(models.PayrollArchive.payroll_period_id == period.id).delete(synchronize_session=False)

    archived_count = 0
    for worker in workers:
        preview = generate_preview_data(worker.id, period_text, db)
        totals = preview.get("totaux") or preview.get("totals") or {}
        lines = preview.get("lignes") or preview.get("lines") or []
        archive = models.PayrollArchive(
            payroll_period_id=period.id,
            employer_id=employer_id,
            worker_id=worker.id,
            period=period_text,
            month=month,
            year=year,
            worker_matricule=worker.matricule,
            worker_full_name=" ".join(part for part in [worker.nom, worker.prenom] if part).strip() or None,
            brut=_float_total(totals, "brut"),
            cotisations_salariales=_float_total(totals, "cotisations_salariales"),
            cotisations_patronales=_float_total(totals, "cotisations_patronales"),
            irsa=_float_total(totals, "irsa"),
            net=_float_total(totals, "net"),
            totals_json=json.dumps(totals, ensure_ascii=False, default=str),
            lines_json=json.dumps(lines, ensure_ascii=False, default=str),
            archived_at=datetime.utcnow(),
        )
        db.add(archive)
        archived_count += 1

    period.is_closed = True
    period.closed_at = datetime.utcnow()
    period.closed_by_user_id = closed_by_user_id
    db.commit()
    db.refresh(period)
    return period, archived_count


def reopen_payroll_period(db: Session, employer_id: int, month: int, year: int, reopened_by_user_id: Optional[int] = None) -> models.PayrollPeriod:
    period = get_or_create_payroll_period(db, employer_id, month, year)
    period.is_closed = False
    period.reopened_at = datetime.utcnow()
    period.reopened_by_user_id = reopened_by_user_id
    db.commit()
    db.refresh(period)
    return period
