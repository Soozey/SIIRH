from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_worker, can_manage_worker, require_roles
from ..services.audit_service import record_audit


router = APIRouter(prefix="/sst", tags=["sst"])

READ_ROLES = ("admin", "rh", "employeur", "manager", "employe")
WRITE_ROLES = ("admin", "rh", "employeur", "manager")


def _assert_employer_scope(user: models.AppUser, employer_id: int) -> None:
    if user.role_code in {"admin", "rh"}:
        return
    if user.role_code == "employeur" and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/incidents", response_model=list[schemas.SstIncidentOut])
def list_incidents(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.SstIncident)
    if user.role_code == "employeur" and user.employer_id:
        query = query.filter(models.SstIncident.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.SstIncident.employer_id == employer_id)

    if user.role_code == "employe" and user.worker_id:
        query = query.filter(models.SstIncident.worker_id == user.worker_id)
    elif worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        if worker and not can_access_worker(db, user, worker):
            raise HTTPException(status_code=403, detail="Forbidden")
        query = query.filter(models.SstIncident.worker_id == worker_id)

    return query.order_by(models.SstIncident.occurred_at.desc()).all()


@router.post("/incidents", response_model=schemas.SstIncidentOut)
def create_incident(
    payload: schemas.SstIncidentCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(user, payload.employer_id)
    if payload.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == payload.worker_id).first()
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        if not can_manage_worker(db, user, worker=worker):
            raise HTTPException(status_code=403, detail="Forbidden")
    item = models.SstIncident(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="sst.incident.create",
        entity_type="sst_incident",
        entity_id=item.id,
        route="/sst/incidents",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/incidents/{incident_id}", response_model=schemas.SstIncidentOut)
def update_incident(
    incident_id: int,
    payload: schemas.SstIncidentUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.SstIncident).filter(models.SstIncident.id == incident_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found")
    _assert_employer_scope(user, item.employer_id)
    if item.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == item.worker_id).first()
        if worker and not can_manage_worker(db, user, worker=worker):
            raise HTTPException(status_code=403, detail="Forbidden")
    before = {"severity": item.severity, "status": item.status}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="sst.incident.update",
        entity_type="sst_incident",
        entity_id=item.id,
        route=f"/sst/incidents/{incident_id}",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item
