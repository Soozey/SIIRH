from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config.config import get_db
from ..leave_logic import (
    calculate_leave_balance,
    calculate_permission_balance,
    get_leave_summary_for_period,
    get_permission_summary_for_period,
)
from .. import models, schemas
from ..security import (
    MANAGER_REVIEW_ROLES,
    READ_PAYROLL_ROLES,
    RH_REVIEW_ROLES,
    WRITE_RH_ROLES,
    can_access_worker,
    can_manage_worker,
    require_roles,
)
from ..services.audit_service import record_audit
from ..services.workflow_service import get_or_create_workflow, review_as_manager, review_as_rh


router = APIRouter(prefix="/leaves", tags=["leaves"])

REQUEST_SUBMISSION_ROLES = {"admin", "rh", "employeur", "manager", "employe"}


def _reset_workflow(workflow: models.RequestWorkflow):
    workflow.overall_status = "pending_manager"
    workflow.manager_status = "pending"
    workflow.rh_status = "pending"
    workflow.manager_comment = None
    workflow.rh_comment = None
    workflow.manager_actor_user_id = None
    workflow.rh_actor_user_id = None


def _serialize_workflow(workflow: models.RequestWorkflow | None) -> Dict[str, Any] | None:
    if not workflow:
        return None
    return schemas.RequestWorkflowOut.model_validate(workflow).model_dump(mode="json")


def _serialize_entry(entry, workflow: models.RequestWorkflow | None) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "start_date": entry.start_date.isoformat(),
        "end_date": entry.end_date.isoformat(),
        "days_taken": entry.days_taken,
        "notes": entry.notes,
        "workflow": _serialize_workflow(workflow),
    }


def _can_submit_request(db: Session, user: models.AppUser, worker: models.Worker) -> bool:
    if can_manage_worker(db, user, worker=worker):
        return True
    return can_access_worker(db, user, worker)


def _get_worker_or_404(db: Session, worker_id: int) -> models.Worker:
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _get_entry_and_workflow(
    db: Session,
    request_type: str,
    entry_id: int,
) -> Tuple[models.Leave | models.Permission, models.RequestWorkflow]:
    model = models.Leave if request_type == "leave" else models.Permission
    entry = db.query(model).filter(model.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"{request_type.title()} not found")
    workflow = get_or_create_workflow(db, request_type, entry.id)
    return entry, workflow


@router.get("/{payroll_run_id}/all")
def get_all_leaves_for_payroll(
    payroll_run_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    payroll_run = db.query(models.PayrollRun).filter(models.PayrollRun.id == payroll_run_id).first()
    if not payroll_run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    period = payroll_run.period
    employer_id = payroll_run.employer_id
    workers = db.query(models.Worker).filter( models.Worker.employer_id == employer_id).order_by(
        models.Worker.nom.asc(),
        models.Worker.prenom.asc(),
    ).all()

    result = []
    for worker in workers:
        if not can_access_worker(db, user, worker):
            continue

        leaves = db.query(models.Leave).filter(
            models.Leave.worker_id == worker.id,
            models.Leave.period == period,
        ).order_by(models.Leave.start_date.asc()).all()
        permissions = db.query(models.Permission).filter(
            models.Permission.worker_id == worker.id,
            models.Permission.period == period,
        ).order_by(models.Permission.start_date.asc()).all()

        leave_workflows = {
            workflow.request_id: workflow
            for workflow in db.query(models.RequestWorkflow).filter(
                models.RequestWorkflow.request_type == "leave",
                models.RequestWorkflow.request_id.in_([entry.id for entry in leaves]) if leaves else False,
            ).all()
        }
        permission_workflows = {
            workflow.request_id: workflow
            for workflow in db.query(models.RequestWorkflow).filter(
                models.RequestWorkflow.request_type == "permission",
                models.RequestWorkflow.request_id.in_([entry.id for entry in permissions]) if permissions else False,
            ).all()
        }

        approved_leave_entries = [
            entry for entry in leaves
            if not leave_workflows.get(entry.id) or leave_workflows[entry.id].overall_status == "approved"
        ]
        approved_permission_entries = [
            entry for entry in permissions
            if not permission_workflows.get(entry.id) or permission_workflows[entry.id].overall_status == "approved"
        ]

        leave_balance = calculate_leave_balance(db, worker.id, period)
        perm_balance = calculate_permission_balance(db, worker.id, int(period.split("-")[0]))

        result.append({
            "worker_id": worker.id,
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenom": worker.prenom,
            "leave": {
                "days_taken": round(sum(entry.days_taken for entry in approved_leave_entries), 2),
                "pending_days_taken": round(
                    sum(entry.days_taken for entry in leaves if leave_workflows.get(entry.id) and leave_workflows[entry.id].overall_status != "approved"),
                    2,
                ),
                "balance": leave_balance["balance"],
                "start_date": min((entry.start_date for entry in approved_leave_entries), default=None),
                "end_date": max((entry.end_date for entry in approved_leave_entries), default=None),
                "entries": [_serialize_entry(entry, leave_workflows.get(entry.id)) for entry in leaves],
            },
            "permission": {
                "days_taken": round(sum(entry.days_taken for entry in approved_permission_entries), 2),
                "pending_days_taken": round(
                    sum(
                        entry.days_taken
                        for entry in permissions
                        if permission_workflows.get(entry.id) and permission_workflows[entry.id].overall_status != "approved"
                    ),
                    2,
                ),
                "balance": perm_balance["balance"],
                "start_date": min((entry.start_date for entry in approved_permission_entries), default=None),
                "end_date": max((entry.end_date for entry in approved_permission_entries), default=None),
                "entries": [_serialize_entry(entry, permission_workflows.get(entry.id)) for entry in permissions],
            },
        })

    return result


@router.post("/leave")
def create_or_update_leave(
    data: schemas.LeaveCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REQUEST_SUBMISSION_ROLES)),
):
    worker = _get_worker_or_404(db, data.worker_id)
    if not _can_submit_request(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    existing = db.query(models.Leave).filter(
        models.Leave.worker_id == data.worker_id,
        models.Leave.period == data.period,
        models.Leave.start_date == data.start_date,
    ).first()

    if existing:
        before = {
            "start_date": existing.start_date.isoformat(),
            "end_date": existing.end_date.isoformat(),
            "days_taken": existing.days_taken,
            "notes": existing.notes,
        }
        existing.end_date = data.end_date
        existing.days_taken = data.days_taken
        existing.notes = data.notes
        entry = existing
        action = "leave.update"
    else:
        before = None
        entry = models.Leave(**data.model_dump())
        db.add(entry)
        db.flush()
        action = "leave.create"

    workflow = get_or_create_workflow(db, "leave", entry.id)
    _reset_workflow(workflow)
    record_audit(
        db,
        actor=user,
        action=action,
        entity_type="leave",
        entity_id=entry.id,
        route="/leaves/leave",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=entry,
    )
    db.commit()
    db.refresh(entry)
    db.refresh(workflow)
    return {"leave": entry, "workflow": _serialize_workflow(workflow)}


@router.delete("/leave/{leave_id}")
def delete_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REQUEST_SUBMISSION_ROLES)),
):
    leave = db.query(models.Leave).filter(models.Leave.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    worker = _get_worker_or_404(db, leave.worker_id)
    workflow = db.query(models.RequestWorkflow).filter(
        models.RequestWorkflow.request_type == "leave",
        models.RequestWorkflow.request_id == leave.id,
    ).first()
    if not _can_submit_request(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    if workflow and workflow.overall_status == "approved" and user.role_code not in WRITE_RH_ROLES:
        raise HTTPException(status_code=409, detail="Approved leave can only be deleted by RH or employer administrators")

    before = {
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
        "days_taken": leave.days_taken,
        "notes": leave.notes,
    }
    if workflow:
        db.delete(workflow)
    db.delete(leave)
    record_audit(
        db,
        actor=user,
        action="leave.delete",
        entity_type="leave",
        entity_id=leave_id,
        route=f"/leaves/leave/{leave_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=None,
    )
    db.commit()
    return {"message": "Leave deleted"}


@router.post("/permission")
def create_or_update_permission(
    data: schemas.PermissionCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REQUEST_SUBMISSION_ROLES)),
):
    worker = _get_worker_or_404(db, data.worker_id)
    if not _can_submit_request(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    existing = db.query(models.Permission).filter(
        models.Permission.worker_id == data.worker_id,
        models.Permission.period == data.period,
        models.Permission.start_date == data.start_date,
    ).first()

    if existing:
        before = {
            "start_date": existing.start_date.isoformat(),
            "end_date": existing.end_date.isoformat(),
            "days_taken": existing.days_taken,
            "notes": existing.notes,
        }
        existing.end_date = data.end_date
        existing.days_taken = data.days_taken
        existing.notes = data.notes
        entry = existing
        action = "permission.update"
    else:
        before = None
        entry = models.Permission(**data.model_dump())
        db.add(entry)
        db.flush()
        action = "permission.create"

    workflow = get_or_create_workflow(db, "permission", entry.id)
    _reset_workflow(workflow)
    record_audit(
        db,
        actor=user,
        action=action,
        entity_type="permission",
        entity_id=entry.id,
        route="/leaves/permission",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=entry,
    )
    db.commit()
    db.refresh(entry)
    db.refresh(workflow)
    return {"permission": entry, "workflow": _serialize_workflow(workflow)}


@router.delete("/permission/{permission_id}")
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REQUEST_SUBMISSION_ROLES)),
):
    permission = db.query(models.Permission).filter(models.Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    worker = _get_worker_or_404(db, permission.worker_id)
    workflow = db.query(models.RequestWorkflow).filter(
        models.RequestWorkflow.request_type == "permission",
        models.RequestWorkflow.request_id == permission.id,
    ).first()
    if not _can_submit_request(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    if workflow and workflow.overall_status == "approved" and user.role_code not in WRITE_RH_ROLES:
        raise HTTPException(status_code=409, detail="Approved permission can only be deleted by RH or employer administrators")

    before = {
        "start_date": permission.start_date.isoformat(),
        "end_date": permission.end_date.isoformat(),
        "days_taken": permission.days_taken,
        "notes": permission.notes,
    }
    if workflow:
        db.delete(workflow)
    db.delete(permission)
    record_audit(
        db,
        actor=user,
        action="permission.delete",
        entity_type="permission",
        entity_id=permission_id,
        route=f"/leaves/permission/{permission_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=None,
    )
    db.commit()
    return {"message": "Permission deleted"}


def _review_request(
    request_type: str,
    entry_id: int,
    payload: schemas.ReviewWorkflowIn,
    db: Session,
    user: models.AppUser,
    stage: str,
):
    entry, workflow = _get_entry_and_workflow(db, request_type, entry_id)
    worker = _get_worker_or_404(db, entry.worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    if stage == "manager":
        review_as_manager(workflow, actor=user, approved=payload.approved, comment=payload.comment)
        action = f"{request_type}.review.manager"
    else:
        if workflow.manager_status != "approved":
            raise HTTPException(status_code=409, detail="Manager approval required before RH review")
        review_as_rh(workflow, actor=user, approved=payload.approved, comment=payload.comment)
        action = f"{request_type}.review.rh"

    record_audit(
        db,
        actor=user,
        action=action,
        entity_type=request_type,
        entity_id=entry.id,
        route=f"/leaves/{request_type}/{entry.id}/review/{stage}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=None,
        after=workflow,
    )
    db.commit()
    db.refresh(workflow)
    return workflow


@router.post("/leave/{leave_id}/review/manager", response_model=schemas.RequestWorkflowOut)
def manager_review_leave(
    leave_id: int,
    payload: schemas.ReviewWorkflowIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MANAGER_REVIEW_ROLES)),
):
    return _review_request("leave", leave_id, payload, db, user, "manager")


@router.post("/leave/{leave_id}/review/rh", response_model=schemas.RequestWorkflowOut)
def rh_review_leave(
    leave_id: int,
    payload: schemas.ReviewWorkflowIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*RH_REVIEW_ROLES)),
):
    return _review_request("leave", leave_id, payload, db, user, "rh")


@router.post("/permission/{permission_id}/review/manager", response_model=schemas.RequestWorkflowOut)
def manager_review_permission(
    permission_id: int,
    payload: schemas.ReviewWorkflowIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MANAGER_REVIEW_ROLES)),
):
    return _review_request("permission", permission_id, payload, db, user, "manager")


@router.post("/permission/{permission_id}/review/rh", response_model=schemas.RequestWorkflowOut)
def rh_review_permission(
    permission_id: int,
    payload: schemas.ReviewWorkflowIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*RH_REVIEW_ROLES)),
):
    return _review_request("permission", permission_id, payload, db, user, "rh")


@router.get("/summary/{worker_id}/{period}")
def get_leave_permission_summary(
    worker_id: int,
    period: str,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    leave_summary = get_leave_summary_for_period(db, worker_id, period)
    perm_summary = get_permission_summary_for_period(db, worker_id, period)
    return {
        "leave": leave_summary,
        "permission": perm_summary,
    }
