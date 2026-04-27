from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.file_storage import sanitize_filename_part, save_upload_file
from ..services.statutory_reporting_service import (
    build_export_preview,
    download_path_for_job,
    ensure_export_templates,
    generate_export_job,
    serialize_declaration,
    serialize_export_job,
    serialize_template,
)


router = APIRouter(prefix="/statutory-exports", tags=["statutory-exports"])

READ_ROLES = ("admin", "rh", "comptable", "employeur", "manager", "juridique", "direction", "audit", "inspecteur")
WRITE_ROLES = ("admin", "rh", "comptable", "employeur", "juridique", "direction")


def _assert_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh", "comptable", "juridique", "direction", "audit"):
        return
    if user_has_any_role(db, user, "employeur", "inspecteur") and user.employer_id:
        if user.employer_id == employer_id:
            return
    if user_has_any_role(db, user, "inspecteur") and user.employer_id is None:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/templates", response_model=list[schemas.ExportTemplateOut])
def list_export_templates(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _ = user
    return [schemas.ExportTemplateOut(**serialize_template(item)) for item in ensure_export_templates(db)]


@router.post("/preview", response_model=schemas.StatutoryExportPreviewOut)
def preview_export(
    payload: schemas.StatutoryExportPreviewRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, payload.employer_id)
    preview = build_export_preview(
        db,
        employer_id=payload.employer_id,
        template_code=payload.template_code,
        start_period=payload.start_period,
        end_period=payload.end_period,
    )
    preview["issues"] = [schemas.IntegrityIssueOut(**item) for item in preview["issues"]]
    return schemas.StatutoryExportPreviewOut(**preview)


@router.post("/generate", response_model=schemas.ExportJobOut)
def generate_export(
    payload: schemas.StatutoryExportPreviewRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_scope(db, user, payload.employer_id)
    job = generate_export_job(
        db,
        employer_id=payload.employer_id,
        template_code=payload.template_code,
        start_period=payload.start_period,
        end_period=payload.end_period,
        requested_by=user,
    )
    record_audit(
        db,
        actor=user,
        action="statutory_export.generate",
        entity_type="export_job",
        entity_id=job.id,
        route="/statutory-exports/generate",
        employer_id=payload.employer_id,
        after=job,
    )
    db.commit()
    db.refresh(job)
    return schemas.ExportJobOut(**serialize_export_job(job))


@router.get("/jobs", response_model=list[schemas.ExportJobOut])
def list_export_jobs(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    items = (
        db.query(models.ExportJob)
        .filter(models.ExportJob.employer_id == employer_id)
        .order_by(models.ExportJob.created_at.desc())
        .all()
    )
    return [schemas.ExportJobOut(**serialize_export_job(item)) for item in items]


@router.get("/jobs/{job_id}/download")
def download_export_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    job = db.query(models.ExportJob).filter(models.ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    _assert_scope(db, user, job.employer_id)
    path = download_path_for_job(job)
    return FileResponse(path, filename=path.name)


@router.get("/declarations", response_model=list[schemas.StatutoryDeclarationOut])
def list_statutory_declarations(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    items = (
        db.query(models.StatutoryDeclaration)
        .filter(models.StatutoryDeclaration.employer_id == employer_id)
        .order_by(models.StatutoryDeclaration.updated_at.desc())
        .all()
    )
    return [schemas.StatutoryDeclarationOut(**serialize_declaration(item)) for item in items]


@router.post("/declarations/{declaration_id}/submit", response_model=schemas.DeclarationSubmissionOut)
def submit_declaration(
    declaration_id: int,
    reference_number: str = Form(...),
    status: str = Form("submitted"),
    receipt: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.StatutoryDeclaration).filter(models.StatutoryDeclaration.id == declaration_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Declaration not found")
    _assert_scope(db, user, item.employer_id)

    item.reference_number = reference_number
    item.status = status
    item.submitted_at = item.submitted_at or datetime.now(timezone.utc)

    if receipt is not None and receipt.filename:
        ext = Path(receipt.filename).suffix or ".pdf"
        filename = (
            f"declarations/{item.employer_id}/"
            f"{sanitize_filename_part(item.channel)}_"
            f"{sanitize_filename_part(item.period_label)}{ext}"
        )
        item.receipt_path = save_upload_file(receipt.file, filename=filename)

    record_audit(
        db,
        actor=user,
        action="statutory_declaration.submit",
        entity_type="statutory_declaration",
        entity_id=item.id,
        route=f"/statutory-exports/declarations/{declaration_id}/submit",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return schemas.DeclarationSubmissionOut(
        declaration=schemas.StatutoryDeclarationOut(**serialize_declaration(item)),
        download_url=item.receipt_path,
    )


