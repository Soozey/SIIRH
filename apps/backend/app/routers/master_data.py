from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..services.file_storage import get_upload_root
from ..security import can_access_employer, can_access_worker, require_roles, user_has_any_role
from ..services.hr_dossier_service import (
    add_hr_document_version,
    build_hr_dossier_report,
    build_hr_dossier_view,
    can_write_hr_dossier,
    get_hr_dossier_access_scope,
    update_hr_dossier_section,
    upload_hr_document,
)
from ..services.master_data_service import build_worker_master_view, sync_employer_master_data


router = APIRouter(prefix="/master-data", tags=["master-data"])

READ_ROLES = ("admin", "rh", "comptable", "employeur", "manager", "employe", "audit", "juridique", "direction", "inspecteur")
WRITE_ROLES = ("admin", "rh", "employeur", "juridique", "direction")
HR_DOSSIER_WRITE_ROLES = ("admin", "rh", "employeur", "hr_manager", "hr_officer", "employer_admin")


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh", "comptable", "audit", "juridique", "direction"):
        return
    if user_has_any_role(db, user, "inspecteur") and can_access_employer(db, user, employer_id):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/workers/{worker_id}", response_model=schemas.MasterDataWorkerViewOut)
def get_worker_master_data(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    return build_worker_master_view(db, worker)


@router.get("/workers/{worker_id}/hr-dossier", response_model=schemas.HrDossierViewOut)
def get_worker_hr_dossier(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        return build_hr_dossier_view(db, worker=worker, user=user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None


@router.patch("/workers/{worker_id}/hr-dossier", response_model=schemas.HrDossierViewOut)
def patch_worker_hr_dossier(
    worker_id: int,
    payload: schemas.HrDossierSectionUpdateIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*HR_DOSSIER_WRITE_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker) or not can_write_hr_dossier(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    update_hr_dossier_section(db, worker=worker, section_key=payload.section_key, data=payload.data, actor=user)
    db.commit()
    return build_hr_dossier_view(db, worker=worker, user=user)


@router.post("/workers/{worker_id}/hr-dossier/documents/upload", response_model=schemas.HrDossierViewOut)
async def upload_worker_hr_documents(
    worker_id: int,
    files: list[UploadFile] = File(...),
    title: Optional[str] = Form(None),
    section_code: str = Form("documents"),
    document_type: str = Form("other"),
    document_date: Optional[str] = Form(None),
    expiration_date: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    visibility_scope: str = Form("hr_only"),
    visible_to_employee: bool = Form(False),
    visible_to_manager: bool = Form(False),
    visible_to_payroll: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*HR_DOSSIER_WRITE_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker) or not can_write_hr_dossier(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    parsed_document_date = date.fromisoformat(document_date) if document_date else None
    parsed_expiration_date = date.fromisoformat(expiration_date) if expiration_date else None
    meta = schemas.HrDossierDocumentUploadMetaIn(
        title=title,
        section_code=section_code,
        document_type=document_type,
        document_date=parsed_document_date,
        expiration_date=parsed_expiration_date,
        comment=comment,
        visibility_scope=visibility_scope,
        visible_to_employee=visible_to_employee,
        visible_to_manager=visible_to_manager,
        visible_to_payroll=visible_to_payroll,
    )
    content_items: list[tuple[UploadFile, bytes]] = []
    for file in files:
        content_items.append((file, await file.read()))
    upload_hr_document(db, worker=worker, actor=user, files=content_items, meta=meta)
    db.commit()
    return build_hr_dossier_view(db, worker=worker, user=user)


@router.post("/workers/{worker_id}/hr-dossier/documents/{document_id}/new-version", response_model=schemas.HrDossierViewOut)
async def upload_worker_hr_document_version(
    worker_id: int,
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*HR_DOSSIER_WRITE_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker) or not can_write_hr_dossier(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    document = (
        db.query(models.HrEmployeeDocument)
        .filter(models.HrEmployeeDocument.id == document_id, models.HrEmployeeDocument.worker_id == worker_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    add_hr_document_version(db, worker=worker, actor=user, document=document, upload_file=file, content=await file.read())
    db.commit()
    return build_hr_dossier_view(db, worker=worker, user=user)


@router.get("/workers/{worker_id}/hr-dossier/documents/{document_id}/download")
def download_worker_hr_document(
    worker_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    document = (
        db.query(models.HrEmployeeDocument)
        .filter(models.HrEmployeeDocument.id == document_id, models.HrEmployeeDocument.worker_id == worker_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    dossier = build_hr_dossier_view(db, worker=worker, user=user)
    if not any(item.id == str(document_id) for item in dossier.documents):
        raise HTTPException(status_code=403, detail="Forbidden")
    version = (
        db.query(models.HrEmployeeDocumentVersion)
        .filter(models.HrEmployeeDocumentVersion.document_id == document_id)
        .order_by(models.HrEmployeeDocumentVersion.version_number.desc())
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found")
    path = Path(get_upload_root()) / version.storage_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path, filename=version.original_name, media_type=version.mime_type or "application/octet-stream")


@router.get("/employers/{employer_id}/hr-dossiers/report", response_model=schemas.HrDossierReportOut)
def get_employer_hr_dossier_report(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    return build_hr_dossier_report(db, employer_id=employer_id, user=user)


@router.post("/employers/{employer_id}/sync")
def sync_employer_master_scope(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    sync_employer_master_data(db, employer_id)
    db.commit()
    return {"ok": True, "employer_id": employer_id}


@router.get("/employers/{employer_id}/health")
def get_employer_master_health(
    employer_id: int,
    sample_limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    workers = (
        db.query(models.Worker)
        .filter(models.Worker.employer_id == employer_id)
        .order_by(models.Worker.nom.asc(), models.Worker.prenom.asc())
        .limit(sample_limit)
        .all()
    )
    snapshots = [build_worker_master_view(db, worker) for worker in workers]
    return {
        "employer_id": employer_id,
        "sample_size": len(snapshots),
        "workers_with_issues": sum(1 for item in snapshots if item.integrity_issues),
        "items": [item.model_dump() for item in snapshots],
    }
