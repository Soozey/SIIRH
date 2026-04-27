from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import PAYROLL_WRITE_ROLES, can_access_worker, require_roles
from ..services.payroll_period_service import ensure_payroll_period_open, payroll_period_write_guard

router = APIRouter(prefix="/variables", tags=["variables"])


@router.post("/upsert", response_model=schemas.PayVarOut, summary="Upsert Variables")
@payroll_period_write_guard
def upsert_variables(
    payload: schemas.PayVarIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == payload.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    ensure_payroll_period_open(db, worker.employer_id, period=payload.period)

    var = (
        db.query(models.PayVar)
        .filter(
            models.PayVar.worker_id == payload.worker_id,
            models.PayVar.period == payload.period,
        )
        .first()
    )
    if var is None:
        var = models.PayVar(worker_id=payload.worker_id, period=payload.period)
        db.add(var)

    data = payload.model_dump()
    for field_name, value in data.items():
        if field_name in ("worker_id", "period"):
            continue
        if hasattr(var, field_name):
            setattr(var, field_name, value)

    db.commit()
    db.refresh(var)
    return var
