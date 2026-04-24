from datetime import datetime, UTC
import re
from typing import Any, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..schemas import AbsenceCalculationResult, AbsenceInput
from ..security import (
    PAYROLL_WRITE_ROLES,
    READ_PAYROLL_ROLES,
    can_access_worker,
    require_roles,
)
from ..services.absence_service import calculate_absence_retentions
from ..services.audit_service import record_audit
from ..services.tabular_io import (
    build_column_mapping,
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    issues_to_csv,
    read_tabular_bytes,
)

router = APIRouter(
    prefix="/absences",
    tags=["Absences"],
)

ABSENCE_TEMPLATE_COLUMNS = [
    "Matricule",
    "Nom",
    "Prenom",
    "Mois (YYYY-MM)",
    "ABSM_J",
    "ABSM_H",
    "ABSNR_J",
    "ABSNR_H",
    "ABSMP",
    "ABS1_J",
    "ABS1_H",
    "ABS2_J",
    "ABS2_H",
]
ABSENCE_REQUIRED_COLUMNS = ["Matricule", "Mois (YYYY-MM)"]
PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _parse_period(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if PERIOD_PATTERN.match(raw):
        return raw
    return None


def _add_issue(
    issues: list[dict[str, Any]],
    *,
    row_number: int,
    code: str,
    message: str,
    column: Optional[str] = None,
    value: Optional[Any] = None,
) -> None:
    issues.append(
        {
            "row_number": row_number,
            "column": column,
            "code": code,
            "message": message,
            "value": None if value is None else str(value),
        }
    )


def _build_report(
    *,
    mode: str,
    total_rows: int,
    processed_rows: int,
    created: int,
    updated: int,
    skipped: int,
    failed: int,
    unknown_columns: list[str],
    missing_columns: list[str],
    issues: list[dict[str, Any]],
) -> schemas.TabularImportReport:
    # Keep local import report format aligned with global import standard.
    return schemas.TabularImportReport(
        mode=mode,
        total_rows=total_rows,
        processed_rows=processed_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        unknown_columns=unknown_columns,
        missing_columns=missing_columns,
        issues=[schemas.ImportIssue(**item) for item in issues],
        error_report_csv=issues_to_csv(issues) if issues else None,
    )


def _value(row: Any, mapping: dict[str, str], column: str) -> Any:
    source_col = mapping.get(column)
    if not source_col:
        return None
    return row.get(source_col)


def calculate_absences(absence_input: AbsenceInput) -> AbsenceCalculationResult:
    """Backward-compatible alias used by tests and callers."""
    return calculate_absence_retentions(absence_input)


class AbsenceSavedOut(BaseModel):
    id: int
    worker_id: int
    mois: str
    total_retenues_absence: float


class AbsenceStoredOut(BaseModel):
    id: int
    worker_id: int
    employer_id: Optional[int] = None
    worker_matricule: Optional[str] = None
    worker_nom: Optional[str] = None
    worker_prenom: Optional[str] = None
    mois: str
    ABSM_J: float
    ABSM_H: float
    ABSNR_J: float
    ABSNR_H: float
    ABSMP: float
    ABS1_J: float
    ABS1_H: float
    ABS2_J: float
    ABS2_H: float


@router.get("/import/template")
def download_absence_template(
    employer_id: Optional[int] = Query(None),
    prefilled: bool = Query(False),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
    current_user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    rows: list[dict[str, Any]] = []
    effective_prefilled = prefilled or employer_id is not None
    if effective_prefilled:
        workers_query = db.query(models.Worker)
        if employer_id is not None:
            workers_query = workers_query.filter(models.Worker.employer_id == employer_id)
        workers = workers_query.order_by(models.Worker.matricule.asc()).all()
        current_month = datetime.now(UTC).strftime("%Y-%m")
        for worker in workers:
            if not can_access_worker(db, current_user, worker):
                continue
            current_absence = (
                db.query(models.Absence)
                .filter(models.Absence.worker_id == worker.id, models.Absence.mois == current_month)
                .order_by(models.Absence.updated_at.desc(), models.Absence.id.desc())
                .first()
            )
            rows.append(
                {
                    "Matricule": worker.matricule,
                    "Nom": worker.nom or "",
                    "Prenom": worker.prenom or "",
                    "Mois (YYYY-MM)": current_month,
                    "ABSM_J": float(current_absence.ABSM_J or 0.0) if current_absence else 0,
                    "ABSM_H": float(current_absence.ABSM_H or 0.0) if current_absence else 0,
                    "ABSNR_J": float(current_absence.ABSNR_J or 0.0) if current_absence else 0,
                    "ABSNR_H": float(current_absence.ABSNR_H or 0.0) if current_absence else 0,
                    "ABSMP": float(current_absence.ABSMP or 0.0) if current_absence else 0,
                    "ABS1_J": float(current_absence.ABS1_J or 0.0) if current_absence else 0,
                    "ABS1_H": float(current_absence.ABS1_H or 0.0) if current_absence else 0,
                    "ABS2_J": float(current_absence.ABS2_J or 0.0) if current_absence else 0,
                    "ABS2_H": float(current_absence.ABS2_H or 0.0) if current_absence else 0,
                }
            )
    else:
        rows.append(
            {
                "Matricule": "M001",
                "Nom": "RAKOTO",
                "Prenom": "Jean",
                "Mois (YYYY-MM)": datetime.now(UTC).strftime("%Y-%m"),
                "ABSM_J": 0,
                "ABSM_H": 0,
                "ABSNR_J": 1,
                "ABSNR_H": 0,
                "ABSMP": 0,
                "ABS1_J": 0,
                "ABS1_H": 0,
                "ABS2_J": 0,
                "ABS2_H": 0,
            }
        )

    df = pd.DataFrame(rows, columns=ABSENCE_TEMPLATE_COLUMNS)
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        filename = "absences_template_prefilled.csv" if prefilled else "absences_template.csv"
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    content = dataframe_to_xlsx_bytes(df, sheet_name="Absences")
    filename = "absences_template_prefilled.xlsx" if effective_prefilled else "absences_template.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=schemas.TabularImportReport)
async def import_absences(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        ABSENCE_TEMPLATE_COLUMNS,
        ABSENCE_REQUIRED_COLUMNS,
    )
    issues: list[dict[str, Any]] = []
    if unknown_columns:
        _add_issue(
            issues,
            row_number=1,
            code="unknown_columns",
            message=f"Colonnes inconnues: {', '.join(unknown_columns)}",
        )
    if missing_columns:
        _add_issue(
            issues,
            row_number=1,
            code="missing_columns",
            message=f"Colonnes obligatoires manquantes: {', '.join(missing_columns)}",
        )
    if unknown_columns or missing_columns:
        return _build_report(
            mode="mixed" if update_existing else "create",
            total_rows=0,
            processed_rows=0,
            created=0,
            updated=0,
            skipped=0,
            failed=0,
            unknown_columns=unknown_columns,
            missing_columns=missing_columns,
            issues=issues,
        )

    total_rows = 0
    processed_rows = 0
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    seen_keys: set[tuple[str, str]] = set()

    for idx, row in df.iterrows():
        row_number = idx + 2
        if all((value is None or str(value).strip() == "" or str(value).lower() == "nan") for value in row.values):
            continue
        total_rows += 1

        matricule = str(_value(row, mapping, "Matricule") or "").strip()
        period_raw = _value(row, mapping, "Mois (YYYY-MM)")
        period = _parse_period(period_raw)
        if not matricule:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="missing_matricule",
                message="Matricule obligatoire.",
                column="Matricule",
            )
            continue
        if not period:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="invalid_period",
                message="Période invalide. Format attendu: YYYY-MM.",
                column="Mois (YYYY-MM)",
                value=period_raw,
            )
            continue
        dedupe_key = (matricule.upper(), period)
        if dedupe_key in seen_keys:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="duplicate_in_file",
                message=f"Doublon dans le fichier pour {matricule} / {period}.",
            )
            continue
        seen_keys.add(dedupe_key)

        worker = db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
        if not worker:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="unknown_worker",
                message=f"Matricule inconnu: {matricule}.",
                column="Matricule",
                value=matricule,
            )
            continue
        if not can_access_worker(db, current_user, worker):
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="forbidden_worker_scope",
                message=f"Droits insuffisants sur le salarié {matricule}.",
            )
            continue

        values = {
            "ABSM_J": _safe_float(_value(row, mapping, "ABSM_J")),
            "ABSM_H": _safe_float(_value(row, mapping, "ABSM_H")),
            "ABSNR_J": _safe_float(_value(row, mapping, "ABSNR_J")),
            "ABSNR_H": _safe_float(_value(row, mapping, "ABSNR_H")),
            "ABSMP": _safe_float(_value(row, mapping, "ABSMP")),
            "ABS1_J": _safe_float(_value(row, mapping, "ABS1_J")),
            "ABS1_H": _safe_float(_value(row, mapping, "ABS1_H")),
            "ABS2_J": _safe_float(_value(row, mapping, "ABS2_J")),
            "ABS2_H": _safe_float(_value(row, mapping, "ABS2_H")),
        }

        try:
            with db.begin_nested():
                existing = (
                    db.query(models.Absence)
                    .filter(models.Absence.worker_id == worker.id, models.Absence.mois == period)
                    .first()
                )
                if existing:
                    if not update_existing:
                        skipped += 1
                        _add_issue(
                            issues,
                            row_number=row_number,
                            code="existing_skipped",
                            message=f"Absence existante ignorée pour {matricule} / {period}.",
                        )
                        continue
                    for key, val in values.items():
                        setattr(existing, key, val)
                    existing.updated_at = _utcnow()
                    updated += 1
                else:
                    db.add(models.Absence(worker_id=worker.id, mois=period, **values))
                    created += 1
                processed_rows += 1
        except Exception as exc:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="row_error",
                message=str(exc),
            )

    if dry_run:
        db.rollback()
    else:
        if created > 0 or updated > 0:
            record_audit(
                db,
                actor=current_user,
                action="absences.import",
                entity_type="absence_import",
                entity_id=f"{created}:{updated}:{skipped}",
                route="/absences/import",
                after={
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                    "issues": len(issues),
                },
            )
            db.commit()
        else:
            db.rollback()

    return _build_report(
        mode="mixed" if update_existing else "create",
        total_rows=total_rows,
        processed_rows=processed_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        unknown_columns=unknown_columns,
        missing_columns=missing_columns,
        issues=issues,
    )


@router.post("/calcul", response_model=AbsenceCalculationResult)
def calculer_absences(
    payload: AbsenceInput,
    _current_user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """Calcule les retenues liées aux absences sans persistance."""
    return calculate_absence_retentions(payload)


@router.post("/calculate-and-save", response_model=AbsenceSavedOut)
def calculate_and_save_absences(
    payload: AbsenceInput,
    mois: Optional[str] = Query(None, description="Période YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    if not payload.worker_id:
        raise HTTPException(status_code=400, detail="worker_id est obligatoire")

    worker = db.query(models.Worker).filter(models.Worker.id == payload.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, current_user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    period = mois or datetime.now(UTC).strftime("%Y-%m")
    result = calculate_absence_retentions(payload)

    existing = db.query(models.Absence).filter(
        models.Absence.worker_id == payload.worker_id,
        models.Absence.mois == period,
    ).first()

    values = {
        "ABSM_J": float(payload.ABSM_J or 0.0),
        "ABSM_H": float(payload.ABSM_H or 0.0),
        "ABSNR_J": float(payload.ABSNR_J or 0.0),
        "ABSNR_H": float(payload.ABSNR_H or 0.0),
        "ABSMP": float(payload.ABSMP or 0.0),
        "ABS1_J": float(payload.ABS1_J or 0.0),
        "ABS1_H": float(payload.ABS1_H or 0.0),
        "ABS2_J": float(payload.ABS2_J or 0.0),
        "ABS2_H": float(payload.ABS2_H or 0.0),
    }

    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.updated_at = _utcnow()
        record = existing
    else:
        record = models.Absence(
            worker_id=payload.worker_id,
            mois=period,
            **values,
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    return AbsenceSavedOut(
        id=record.id,
        worker_id=record.worker_id,
        mois=record.mois,
        total_retenues_absence=float(result.total_retenues_absence),
    )


@router.get("/all", response_model=List[AbsenceStoredOut])
def get_all_absences(
    worker_id: Optional[int] = Query(None),
    employer_id: Optional[int] = Query(None),
    mois: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = db.query(models.Absence)
    if worker_id is not None:
        query = query.filter(models.Absence.worker_id == worker_id)
    if mois:
        query = query.filter(models.Absence.mois == mois)

    rows = query.order_by(models.Absence.updated_at.desc()).all()
    allowed: List[models.Absence] = []
    worker_map: dict[int, models.Worker] = {}
    for row in rows:
        worker = worker_map.get(row.worker_id)
        if worker is None:
            worker = db.query(models.Worker).filter(models.Worker.id == row.worker_id).first()
            if worker is not None:
                worker_map[row.worker_id] = worker
        if not worker:
            continue
        if employer_id is not None and worker.employer_id != employer_id:
            continue
        if can_access_worker(db, current_user, worker):
            allowed.append(row)

    return [
        AbsenceStoredOut(
            id=r.id,
            worker_id=r.worker_id,
            employer_id=worker_map.get(r.worker_id).employer_id if worker_map.get(r.worker_id) else None,
            worker_matricule=worker_map.get(r.worker_id).matricule if worker_map.get(r.worker_id) else None,
            worker_nom=worker_map.get(r.worker_id).nom if worker_map.get(r.worker_id) else None,
            worker_prenom=worker_map.get(r.worker_id).prenom if worker_map.get(r.worker_id) else None,
            mois=r.mois,
            ABSM_J=float(r.ABSM_J or 0.0),
            ABSM_H=float(r.ABSM_H or 0.0),
            ABSNR_J=float(r.ABSNR_J or 0.0),
            ABSNR_H=float(r.ABSNR_H or 0.0),
            ABSMP=float(r.ABSMP or 0.0),
            ABS1_J=float(r.ABS1_J or 0.0),
            ABS1_H=float(r.ABS1_H or 0.0),
            ABS2_J=float(r.ABS2_J or 0.0),
            ABS2_H=float(r.ABS2_H or 0.0),
        )
        for r in allowed
    ]


@router.delete("/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence(
    absence_id: int,
    db: Session = Depends(get_db),
    current_user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
) -> None:
    record = db.query(models.Absence).filter(models.Absence.id == absence_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Absence id={absence_id} introuvable.")

    worker = db.query(models.Worker).filter(models.Worker.id == record.worker_id).first()
    if not worker or not can_access_worker(db, current_user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    db.delete(record)
    db.commit()
    return None
