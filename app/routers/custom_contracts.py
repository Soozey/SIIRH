from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import READ_PAYROLL_ROLES, WRITE_RH_ROLES, can_access_worker, can_manage_worker, require_roles
from ..services.audit_service import record_audit


router = APIRouter(prefix="/custom-contracts", tags=["custom-contracts"])


def _get_worker_or_404(db: Session, worker_id: int) -> models.Worker:
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _get_contract_or_404(db: Session, contract_id: int) -> models.CustomContract:
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("/", response_model=schemas.CustomContractOut)
def create_custom_contract(
    contract: schemas.CustomContractIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    worker = _get_worker_or_404(db, contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    employer = db.query(models.Employer).filter(models.Employer.id == contract.employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    if contract.is_default:
        db.query(models.CustomContract).filter(
            models.CustomContract.worker_id == contract.worker_id,
            models.CustomContract.template_type == contract.template_type,
        ).update({"is_default": False})

    db_contract = models.CustomContract(**contract.model_dump())
    db.add(db_contract)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="custom_contract.create",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route="/custom-contracts/",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after=db_contract,
    )
    db.commit()
    db.refresh(db_contract)
    return db_contract


@router.get("/worker/{worker_id}", response_model=List[schemas.CustomContractOut])
def get_worker_contracts(
    worker_id: int,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    query = db.query(models.CustomContract).filter(models.CustomContract.worker_id == worker_id)
    if template_type:
        query = query.filter(models.CustomContract.template_type == template_type)
    return query.order_by(models.CustomContract.updated_at.desc()).all()


@router.get("/worker/{worker_id}/default", response_model=schemas.CustomContractOut)
def get_worker_default_contract(
    worker_id: int,
    template_type: str = "employment_contract",
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    contract = db.query(models.CustomContract).filter(
        models.CustomContract.worker_id == worker_id,
        models.CustomContract.template_type == template_type,
        models.CustomContract.is_default == True,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="No default contract found")
    return contract


@router.get("/{contract_id}", response_model=schemas.CustomContractOut)
def get_custom_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, contract.worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    return contract


@router.put("/{contract_id}", response_model=schemas.CustomContractOut)
def update_custom_contract(
    contract_id: int,
    contract_update: schemas.CustomContractUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, db_contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    before = {
        "title": db_contract.title,
        "template_type": db_contract.template_type,
        "is_default": db_contract.is_default,
    }
    if contract_update.is_default:
        db.query(models.CustomContract).filter(
            models.CustomContract.worker_id == db_contract.worker_id,
            models.CustomContract.template_type == db_contract.template_type,
            models.CustomContract.id != contract_id,
        ).update({"is_default": False})

    update_data = contract_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_contract, field, value)

    record_audit(
        db,
        actor=user,
        action="custom_contract.update",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route=f"/custom-contracts/{contract_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=db_contract,
    )
    db.commit()
    db.refresh(db_contract)
    return db_contract


@router.delete("/{contract_id}")
def delete_custom_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, db_contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    record_audit(
        db,
        actor=user,
        action="custom_contract.delete",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route=f"/custom-contracts/{contract_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=db_contract,
        after=None,
    )
    db.delete(db_contract)
    db.commit()
    return {"message": "Contract deleted successfully"}


@router.post("/{contract_id}/set-default")
def set_default_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, db_contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    db.query(models.CustomContract).filter(
        models.CustomContract.worker_id == db_contract.worker_id,
        models.CustomContract.template_type == db_contract.template_type,
        models.CustomContract.id != contract_id,
    ).update({"is_default": False})

    db_contract.is_default = True
    record_audit(
        db,
        actor=user,
        action="custom_contract.default",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route=f"/custom-contracts/{contract_id}/set-default",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after=db_contract,
    )
    db.commit()
    db.refresh(db_contract)
    return db_contract
