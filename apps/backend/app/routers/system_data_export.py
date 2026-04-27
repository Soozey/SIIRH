from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import require_module_access, user_has_any_role
from ..services.audit_service import record_audit
from ..services.system_data_export_service import (
    build_system_data_update_package_zip,
    build_system_data_export_zip,
    preview_system_data_export,
)


router = APIRouter(prefix="/system-data-export", tags=["system-data-export"])


def _apply_export_scope(db: Session, options: schemas.SystemExportOptions, user: models.AppUser) -> schemas.SystemExportOptions:
    if user_has_any_role(db, user, "employeur"):
        if user.employer_id is None:
            raise HTTPException(status_code=403, detail="Employeur sans scope entreprise.")
        if options.employer_id and options.employer_id != user.employer_id:
            raise HTTPException(status_code=403, detail="Vous ne pouvez exporter que votre employeur.")
        options.employer_id = user.employer_id
    return options


@router.post("/preview", response_model=schemas.SystemDataExportPreview)
def preview_export_package(
    payload: schemas.SystemExportOptions,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    scoped_options = _apply_export_scope(db, payload, user)
    preview = preview_system_data_export(db=db, options=scoped_options)
    record_audit(
        db,
        actor=user,
        action="system_data_export.preview",
        entity_type="system_data_export",
        entity_id="preview",
        route="/system-data-export/preview",
        after={
            "employer_id": scoped_options.employer_id,
            "selected_modules": scoped_options.selected_modules,
            "modules_exported": preview.manifest.modules_exported,
            "total_records": preview.total_records,
        },
    )
    db.commit()
    return preview


@router.post("")
def export_package(
    payload: schemas.SystemExportOptions,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    scoped_options = _apply_export_scope(db, payload, user)
    zip_bytes, filename, preview = build_system_data_export_zip(db=db, options=scoped_options)

    record_audit(
        db,
        actor=user,
        action="system_data_export.execute",
        entity_type="system_data_export",
        entity_id=filename,
        route="/system-data-export",
        after={
            "filename": filename,
            "employer_id": scoped_options.employer_id,
            "selected_modules": scoped_options.selected_modules,
            "modules_exported": preview.manifest.modules_exported,
            "total_records": preview.total_records,
            "warnings": preview.warnings,
        },
    )
    db.commit()

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        content=iter([zip_bytes]),
        media_type="application/zip",
        headers=headers,
    )


@router.post("/update-package")
def export_update_package(
    payload: schemas.SystemExportOptions,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    scoped_options = _apply_export_scope(db, payload, user)
    zip_bytes, filename, preview = build_system_data_update_package_zip(db=db, options=scoped_options)

    record_audit(
        db,
        actor=user,
        action="system_data_export.update_package",
        entity_type="system_data_export",
        entity_id=filename,
        route="/system-data-export/update-package",
        after={
            "filename": filename,
            "package_type": "migration_update",
            "employer_id": scoped_options.employer_id,
            "selected_modules": scoped_options.selected_modules,
            "modules_exported": preview.manifest.modules_exported,
            "total_records": preview.total_records,
            "warnings": preview.warnings,
        },
    )
    db.commit()

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        content=iter([zip_bytes]),
        media_type="application/zip",
        headers=headers,
    )
