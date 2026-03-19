"""
Router pour la gestion des templates de documents globaux
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import READ_PAYROLL_ROLES, WRITE_RH_ROLES, can_access_worker, require_roles
from ..services.audit_service import record_audit


router = APIRouter(prefix="/document-templates", tags=["document-templates"])
DOCUMENT_TEMPLATE_READ_ROLES = {"admin", "rh", "comptable", "employeur", "manager"}


def _viewer_employer_id(db: Session, user: models.AppUser) -> Optional[int]:
    if user.role_code == "employeur":
        return user.employer_id
    if user.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        return worker.employer_id if worker else None
    return None


def _can_manage_template(user: models.AppUser, employer_id: Optional[int]) -> bool:
    if employer_id is None:
        return user.role_code == "admin"
    if user.role_code in {"admin", "rh"}:
        return True
    return user.role_code == "employeur" and user.employer_id == employer_id


def _template_query_for_user(db: Session, user: models.AppUser):
    query = db.query(models.DocumentTemplate).filter(models.DocumentTemplate.is_active == True)
    if user.role_code in {"admin", "rh", "comptable", "audit"}:
        return query

    employer_id = _viewer_employer_id(db, user)
    if not employer_id:
        return query.filter(models.DocumentTemplate.id == -1)

    return query.filter(
        or_(
            models.DocumentTemplate.employer_id == employer_id,
            models.DocumentTemplate.employer_id.is_(None),
        )
    )


def _get_template_for_user_or_404(db: Session, user: models.AppUser, template_id: int) -> models.DocumentTemplate:
    template = _template_query_for_user(db, user).filter(models.DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/", response_model=List[schemas.DocumentTemplateOut])
def get_document_templates(
    employer_id: Optional[int] = None,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*DOCUMENT_TEMPLATE_READ_ROLES)),
):
    query = _template_query_for_user(db, user)

    if employer_id:
        viewer_employer_id = _viewer_employer_id(db, user)
        if user.role_code not in {"admin", "rh", "comptable", "audit"} and employer_id != viewer_employer_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        query = query.filter(
            or_(
                models.DocumentTemplate.employer_id == employer_id,
                models.DocumentTemplate.employer_id.is_(None),
            )
        )

    if template_type:
        query = query.filter(models.DocumentTemplate.template_type == template_type)

    return query.order_by(models.DocumentTemplate.name).all()


@router.post("/", response_model=schemas.DocumentTemplateOut)
def create_document_template(
    template: schemas.DocumentTemplateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    if not _can_manage_template(user, template.employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    if template.employer_id:
        employer = db.query(models.Employer).filter(
            models.Employer.id == template.employer_id
        ).first()
        if not employer:
            raise HTTPException(status_code=404, detail="Employer not found")

    db_template = models.DocumentTemplate(**template.model_dump())
    db.add(db_template)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="document_template.create",
        entity_type="document_template",
        entity_id=db_template.id,
        route="/document-templates/",
        employer_id=db_template.employer_id,
        after=db_template,
    )
    db.commit()
    db.refresh(db_template)
    return db_template


@router.get("/{template_id}", response_model=schemas.DocumentTemplateOut)
def get_document_template(
    template_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*DOCUMENT_TEMPLATE_READ_ROLES)),
):
    return _get_template_for_user_or_404(db, user, template_id)


@router.put("/{template_id}", response_model=schemas.DocumentTemplateOut)
def update_document_template(
    template_id: int,
    template_update: schemas.DocumentTemplateUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_template = db.query(models.DocumentTemplate).filter(
        models.DocumentTemplate.id == template_id
    ).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not _can_manage_template(user, db_template.employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if db_template.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system template")

    before = models.DocumentTemplate(
        id=db_template.id,
        employer_id=db_template.employer_id,
        name=db_template.name,
        description=db_template.description,
        template_type=db_template.template_type,
        content=db_template.content,
        is_active=db_template.is_active,
        is_system=db_template.is_system,
        created_at=db_template.created_at,
        updated_at=db_template.updated_at,
    )

    for field, value in template_update.model_dump(exclude_unset=True).items():
        setattr(db_template, field, value)

    record_audit(
        db,
        actor=user,
        action="document_template.update",
        entity_type="document_template",
        entity_id=db_template.id,
        route=f"/document-templates/{template_id}",
        employer_id=db_template.employer_id,
        before=before,
        after=db_template,
    )
    db.commit()
    db.refresh(db_template)
    return db_template


@router.delete("/{template_id}")
def delete_document_template(
    template_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_template = db.query(models.DocumentTemplate).filter(
        models.DocumentTemplate.id == template_id
    ).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not _can_manage_template(user, db_template.employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if db_template.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system template")

    record_audit(
        db,
        actor=user,
        action="document_template.delete",
        entity_type="document_template",
        entity_id=db_template.id,
        route=f"/document-templates/{template_id}",
        employer_id=db_template.employer_id,
        before=db_template,
    )
    db.delete(db_template)
    db.commit()
    return {"message": "Template deleted successfully"}


@router.post("/{template_id}/apply/{worker_id}")
def apply_template_to_worker(
    template_id: int,
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    template = db.query(models.DocumentTemplate).filter(
        models.DocumentTemplate.id == template_id,
        models.DocumentTemplate.is_active == True,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    if template.employer_id and template.employer_id != worker.employer_id:
        raise HTTPException(status_code=403, detail="Template not available for this worker")

    from .constants import get_employer_constants, get_system_constants, get_worker_constants

    worker_data = get_worker_constants(worker_id, db)
    employer_data = get_employer_constants(worker.employer_id, db)
    system_data = get_system_constants()
    all_data = {**worker_data, **employer_data, **system_data}

    content = template.content
    for key, value in all_data.items():
        for placeholder in [
            f"{{{{{key}}}}}",
            f"{{{{worker.{key}}}}}",
            f"{{{{employer.{key}}}}}",
            f"{{{{system.{key}}}}}",
            f"{{{{payroll.{key}}}}}",
        ]:
            content = content.replace(placeholder, str(value or ""))

    return {
        "template_id": template_id,
        "template_name": template.name,
        "worker_id": worker_id,
        "worker_name": f"{worker.prenom} {worker.nom}",
        "content": content,
        "original_content": template.content,
    }
