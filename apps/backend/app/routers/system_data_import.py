import re
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import require_module_access
from ..services.audit_service import record_audit
from ..services.system_data_import_service import import_system_data_package


router = APIRouter(prefix="/system-data-import", tags=["system-data-import"])


def _parse_selected_modules(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in re.split(r"[,\n;|]+", raw) if item and item.strip()]


def _build_options(
    *,
    update_existing: bool,
    skip_exact_duplicates: bool,
    continue_on_error: bool,
    strict_mode: bool,
    selected_modules: Optional[str],
) -> schemas.SystemImportOptions:
    return schemas.SystemImportOptions(
        update_existing=update_existing,
        skip_exact_duplicates=skip_exact_duplicates,
        continue_on_error=continue_on_error,
        strict_mode=strict_mode,
        selected_modules=_parse_selected_modules(selected_modules),
    )


@router.post("/preview", response_model=schemas.SystemDataImportReport)
async def preview_system_data_import(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    skip_exact_duplicates: bool = Form(True),
    continue_on_error: bool = Form(True),
    strict_mode: bool = Form(False),
    selected_modules: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    package_bytes = await file.read()
    options = _build_options(
        update_existing=update_existing,
        skip_exact_duplicates=skip_exact_duplicates,
        continue_on_error=continue_on_error,
        strict_mode=strict_mode,
        selected_modules=selected_modules,
    )
    try:
        report = import_system_data_package(
            db=db,
            package_bytes=package_bytes,
            filename=file.filename,
            options=options,
            dry_run=True,
        )
        record_audit(
            db,
            actor=user,
            action="system_data_import.preview",
            entity_type="system_data_import",
            entity_id=file.filename or "package",
            route="/system-data-import/preview",
            after={
                "dry_run": True,
                "total_processed_rows": report.total_processed_rows,
                "total_created": report.total_created,
                "total_updated": report.total_updated,
                "total_failed": report.total_failed,
                "total_conflicts": report.total_conflicts,
                "modules": [item.module for item in report.modules],
            },
        )
        db.commit()
        return report
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:  # pragma: no cover - defensive catch
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Preview import impossible: {exc}") from exc


@router.post("", response_model=schemas.SystemDataImportExecuteResponse)
async def execute_system_data_import(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    skip_exact_duplicates: bool = Form(True),
    continue_on_error: bool = Form(True),
    strict_mode: bool = Form(False),
    selected_modules: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    package_bytes = await file.read()
    options = _build_options(
        update_existing=update_existing,
        skip_exact_duplicates=skip_exact_duplicates,
        continue_on_error=continue_on_error,
        strict_mode=strict_mode,
        selected_modules=selected_modules,
    )
    try:
        report = import_system_data_package(
            db=db,
            package_bytes=package_bytes,
            filename=file.filename,
            options=options,
            dry_run=False,
        )
        record_audit(
            db,
            actor=user,
            action="system_data_import.execute",
            entity_type="system_data_import",
            entity_id=file.filename or "package",
            route="/system-data-import",
            after=report.model_dump(mode="json"),
        )
        db.commit()
        return schemas.SystemDataImportExecuteResponse(
            imported=report.total_created,
            updated=report.total_updated,
            skipped=report.total_skipped,
            failed=report.total_failed,
            conflicts=report.total_conflicts,
            report=report,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:  # pragma: no cover - defensive catch
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Execution import impossible: {exc}") from exc
