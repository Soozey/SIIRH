from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import require_module_access
from ..services.audit_service import record_audit
from ..services.legal_operations_service import build_debug_execution_panel, seed_legal_demo_data
from ..services.update_service import get_update_job, list_update_jobs, start_update_job


router = APIRouter(prefix="/system-update", tags=["system-update"])


@router.post("/start", response_model=schemas.SystemUpdateJobStatus)
async def start_system_update(
    package_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    try:
        job = start_update_job(package_file_obj=package_file.file, package_filename=package_file.filename or "update.zip")
        record_audit(
            db,
            actor=user,
            action="system_update.start",
            entity_type="system_update",
            entity_id=job.job_id,
            route="/system-update/start",
            after={
                "job_id": job.job_id,
                "package_filename": job.package_filename,
                "status": job.status,
                "stage": job.stage,
            },
        )
        db.commit()
        return job
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Echec lancement update: {exc}") from exc


@router.get("/jobs/{job_id}", response_model=schemas.SystemUpdateJobStatus)
def get_system_update_status(
    job_id: str,
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    try:
        _ = user
        return get_update_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lecture statut impossible: {exc}") from exc


@router.get("/jobs", response_model=list[schemas.SystemUpdateJobStatus])
def list_system_update_jobs(
    limit: int = 20,
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    _ = user
    return list_update_jobs(limit=max(1, min(100, limit)))


@router.get("/debug-execution-panel", response_model=schemas.DebugExecutionPanelOut)
def get_debug_execution_panel(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    _ = user
    return build_debug_execution_panel(db)


@router.post("/seed-legal-demo")
def run_legal_demo_seed(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_module_access("master_data", "admin")),
):
    summary = seed_legal_demo_data(db, actor=user)
    return {"status": "ok", "summary": summary}
