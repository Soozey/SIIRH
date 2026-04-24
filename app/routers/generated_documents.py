from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..routers.payroll import generate_preview_data
from ..routers.reporting import (
    REPORTING_ROLES,
    _build_report_filters,
    _ensure_reporting_scope,
    _prepare_report_columns,
    get_full_report_data,
)
from ..security import READ_PAYROLL_ROLES, can_access_worker, get_current_user, require_roles
from ..services.master_data_service import build_worker_reporting_payload
from ..services.pdf_generation_service import build_contract_pdf, build_payslip_pdf, build_report_pdf


router = APIRouter(prefix="/generated-documents", tags=["generated-documents"])


@router.get("/payslip/{worker_id}/{period}")
def generate_payslip_pdf_document(
    worker_id: int,
    period: str,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    preview = generate_preview_data(worker_id, period, db)
    worker_identity = build_worker_reporting_payload(db, worker)
    worker_name = f"{worker_identity.get('prenom', '')} {worker_identity.get('nom', '')}".strip()
    worker_number = worker_identity.get("matricule") or worker.matricule
    pdf_bytes = build_payslip_pdf(preview, worker_name, period)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bulletin_{worker_number}_{period}.pdf"'},
    )


@router.get("/contracts/{contract_id}")
def generate_contract_pdf_document(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    worker = db.query(models.Worker).filter(models.Worker.id == contract.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    worker_identity = build_worker_reporting_payload(db, worker)
    worker_name = f"{worker_identity.get('prenom', '')} {worker_identity.get('nom', '')}".strip()
    pdf_bytes = build_contract_pdf(contract.title, contract.content, worker_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contrat_{contract.id}.pdf"'},
    )


@router.post("/reporting")
def generate_reporting_pdf_document(
    request: schemas.ReportRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REPORTING_ROLES)),
):
    _ensure_reporting_scope(db, user, request.employer_id)
    columns = _prepare_report_columns(request)
    filters = _build_report_filters(request)
    data = get_full_report_data(
        request.employer_id,
        request.start_period,
        request.end_period,
        columns,
        db,
        filters=filters,
        viewer=user,
    )
    pdf_bytes = build_report_pdf(
        "Rapport RH SIIRH",
        f"Periode {request.start_period} a {request.end_period}",
        columns,
        data,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="reporting_{request.employer_id}_{request.start_period}_{request.end_period}.pdf"'
            )
        },
    )
