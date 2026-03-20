from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_worker, can_manage_worker, require_roles
from ..services.audit_service import record_audit


router = APIRouter(prefix="/talents", tags=["talents"])

READ_ROLES = ("admin", "rh", "employeur", "manager", "employe")
WRITE_ROLES = ("admin", "rh", "employeur")


def _assert_employer_scope(user: models.AppUser, employer_id: int) -> None:
    if user.role_code in {"admin", "rh"}:
        return
    if user.role_code == "employeur" and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/skills", response_model=list[schemas.TalentSkillOut])
def list_skills(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentSkill)
    if user.role_code == "employeur" and user.employer_id:
        query = query.filter(models.TalentSkill.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.TalentSkill.employer_id == employer_id)
    return query.order_by(models.TalentSkill.name.asc()).all()


@router.post("/skills", response_model=schemas.TalentSkillOut)
def create_skill(
    payload: schemas.TalentSkillCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(user, payload.employer_id)
    item = models.TalentSkill(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.skill.create",
        entity_type="talent_skill",
        entity_id=item.id,
        route="/talents/skills",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/skills/{skill_id}", response_model=schemas.TalentSkillOut)
def update_skill(
    skill_id: int,
    payload: schemas.TalentSkillUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TalentSkill).filter(models.TalentSkill.id == skill_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Skill not found")
    _assert_employer_scope(user, item.employer_id)
    before = {"name": item.name, "code": item.code, "is_active": item.is_active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="talents.skill.update",
        entity_type="talent_skill",
        entity_id=item.id,
        route=f"/talents/skills/{skill_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/employee-skills", response_model=list[schemas.TalentEmployeeSkillOut])
def list_employee_skills(
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentEmployeeSkill)
    if worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        if not worker or not can_access_worker(db, user, worker):
            raise HTTPException(status_code=403, detail="Forbidden")
        query = query.filter(models.TalentEmployeeSkill.worker_id == worker_id)
    elif user.role_code == "employe" and user.worker_id:
        query = query.filter(models.TalentEmployeeSkill.worker_id == user.worker_id)
    return query.order_by(models.TalentEmployeeSkill.updated_at.desc()).all()


@router.post("/employee-skills", response_model=schemas.TalentEmployeeSkillOut)
def create_employee_skill(
    payload: schemas.TalentEmployeeSkillCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == payload.worker_id).first()
    skill = db.query(models.TalentSkill).filter(models.TalentSkill.id == payload.skill_id).first()
    if not worker or not skill:
        raise HTTPException(status_code=404, detail="Worker or skill not found")
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    item = models.TalentEmployeeSkill(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.employee_skill.create",
        entity_type="talent_employee_skill",
        entity_id=item.id,
        route="/talents/employee-skills",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/employee-skills/{employee_skill_id}", response_model=schemas.TalentEmployeeSkillOut)
def update_employee_skill(
    employee_skill_id: int,
    payload: schemas.TalentEmployeeSkillUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TalentEmployeeSkill).filter(models.TalentEmployeeSkill.id == employee_skill_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Employee skill not found")
    worker = db.query(models.Worker).filter(models.Worker.id == item.worker_id).first()
    if not worker or not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    before = {"level": item.level, "source": item.source}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="talents.employee_skill.update",
        entity_type="talent_employee_skill",
        entity_id=item.id,
        route=f"/talents/employee-skills/{employee_skill_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/trainings", response_model=list[schemas.TalentTrainingOut])
def list_trainings(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentTraining)
    if user.role_code == "employeur" and user.employer_id:
        query = query.filter(models.TalentTraining.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.TalentTraining.employer_id == employer_id)
    return query.order_by(models.TalentTraining.updated_at.desc()).all()


@router.post("/trainings", response_model=schemas.TalentTrainingOut)
def create_training(
    payload: schemas.TalentTrainingCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(user, payload.employer_id)
    item = models.TalentTraining(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.training.create",
        entity_type="talent_training",
        entity_id=item.id,
        route="/talents/trainings",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/trainings/{training_id}", response_model=schemas.TalentTrainingOut)
def update_training(
    training_id: int,
    payload: schemas.TalentTrainingUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TalentTraining).filter(models.TalentTraining.id == training_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Training not found")
    _assert_employer_scope(user, item.employer_id)
    before = {"title": item.title, "status": item.status}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="talents.training.update",
        entity_type="talent_training",
        entity_id=item.id,
        route=f"/talents/trainings/{training_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/training-sessions", response_model=list[schemas.TalentTrainingSessionOut])
def list_training_sessions(
    training_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentTrainingSession)
    if training_id:
        query = query.filter(models.TalentTrainingSession.training_id == training_id)
    return query.order_by(models.TalentTrainingSession.start_date.desc()).all()


@router.post("/training-sessions", response_model=schemas.TalentTrainingSessionOut)
def create_training_session(
    payload: schemas.TalentTrainingSessionCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    training = db.query(models.TalentTraining).filter(models.TalentTraining.id == payload.training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found")
    _assert_employer_scope(user, training.employer_id)
    item = models.TalentTrainingSession(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.training_session.create",
        entity_type="talent_training_session",
        entity_id=item.id,
        route="/talents/training-sessions",
        employer_id=training.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item
