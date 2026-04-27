from datetime import date
from typing import Any, Dict, List, Tuple

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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
    user_has_any_role,
)
from ..services.audit_service import record_audit
from ..services.file_storage import build_static_path, sanitize_filename_part, save_upload_file
from ..services.leave_management_service import (
    act_on_leave_request,
    create_leave_request,
    create_planning_cycle,
    delete_leave_request,
    ensure_default_approval_rule,
    ensure_default_leave_types,
    generate_planning_proposals,
    get_validator_dashboard,
    get_worker_leave_dashboard,
    json_load,
    json_dump,
    list_reconciliations,
    requalify_leave_request,
    serialize_leave_request,
)
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
    if workflow and workflow.overall_status == "approved" and not user_has_any_role(db, user, *WRITE_RH_ROLES):
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
    if workflow and workflow.overall_status == "approved" and not user_has_any_role(db, user, *WRITE_RH_ROLES):
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


def _assert_leave_scope(db: Session, user: models.AppUser, worker: models.Worker, leave_request: models.LeaveRequest | None = None):
    if can_access_worker(db, user, worker) or can_manage_worker(db, user, worker=worker):
        return
    if leave_request and any(approval.approver_user_id == user.id for approval in leave_request.approvals):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _request_or_404(db: Session, request_id: int) -> models.LeaveRequest:
    item = db.query(models.LeaveRequest).filter(models.LeaveRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return item


@router.get("/types", response_model=list[schemas.LeaveTypeRuleOut])
def list_leave_types(
    employer_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "direction")),
):
    scope_employer_id = employer_id if employer_id is not None else user.employer_id
    ensure_default_leave_types(db, scope_employer_id)
    rows = (
        db.query(models.LeaveTypeRule)
        .filter(
            (models.LeaveTypeRule.employer_id == scope_employer_id) | (models.LeaveTypeRule.employer_id.is_(None)),
            models.LeaveTypeRule.active == True,  # noqa: E712
        )
        .order_by(models.LeaveTypeRule.employer_id.desc().nullslast(), models.LeaveTypeRule.label.asc())
        .all()
    )
    return rows


@router.post("/types", response_model=schemas.LeaveTypeRuleOut)
def create_leave_type(
    payload: schemas.LeaveTypeRuleIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur")),
):
    item = models.LeaveTypeRule(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/approval-rules", response_model=list[schemas.LeaveApprovalRuleOut])
def list_approval_rules(
    employer_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction")),
):
    scope_employer_id = employer_id if employer_id is not None else user.employer_id
    rows = (
        db.query(models.LeaveApprovalRule)
        .filter((models.LeaveApprovalRule.employer_id == scope_employer_id) | (models.LeaveApprovalRule.employer_id.is_(None)))
        .order_by(models.LeaveApprovalRule.leave_type_code.asc(), models.LeaveApprovalRule.id.asc())
        .all()
    )
    return [
        schemas.LeaveApprovalRuleOut(
            id=row.id,
            employer_id=row.employer_id,
            leave_type_code=row.leave_type_code,
            worker_category=row.worker_category,
            organizational_unit_id=row.organizational_unit_id,
            approval_mode=row.approval_mode,
            fallback_on_reject=row.fallback_on_reject,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
            steps=[
                schemas.LeaveApprovalRuleStepOut(
                    id=step.id,
                    step_order=step.step_order,
                    parallel_group=step.parallel_group,
                    approver_kind=step.approver_kind,
                    approver_role_code=step.approver_role_code,
                    approver_user_id=step.approver_user_id,
                    is_required=step.is_required,
                    label=step.label,
                    created_at=step.created_at,
                    updated_at=step.updated_at,
                )
                for step in sorted(row.steps, key=lambda item: (item.step_order, item.parallel_group, item.id))
            ],
        )
        for row in rows
    ]


@router.post("/approval-rules", response_model=schemas.LeaveApprovalRuleOut)
def create_approval_rule(
    payload: schemas.LeaveApprovalRuleIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur")),
):
    rule = models.LeaveApprovalRule(
        employer_id=payload.employer_id,
        leave_type_code=payload.leave_type_code,
        worker_category=payload.worker_category,
        organizational_unit_id=payload.organizational_unit_id,
        approval_mode=payload.approval_mode,
        fallback_on_reject=payload.fallback_on_reject,
        active=payload.active,
    )
    db.add(rule)
    db.flush()
    for step in payload.steps:
        db.add(models.LeaveApprovalRuleStep(rule_id=rule.id, **step.model_dump()))
    db.commit()
    db.refresh(rule)
    return schemas.LeaveApprovalRuleOut(
        id=rule.id,
        employer_id=rule.employer_id,
        leave_type_code=rule.leave_type_code,
        worker_category=rule.worker_category,
        organizational_unit_id=rule.organizational_unit_id,
        approval_mode=rule.approval_mode,
        fallback_on_reject=rule.fallback_on_reject,
        active=rule.active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        steps=[
            schemas.LeaveApprovalRuleStepOut(
                id=step.id,
                step_order=step.step_order,
                parallel_group=step.parallel_group,
                approver_kind=step.approver_kind,
                approver_role_code=step.approver_role_code,
                approver_user_id=step.approver_user_id,
                is_required=step.is_required,
                label=step.label,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
            for step in sorted(rule.steps, key=lambda item: (item.step_order, item.parallel_group, item.id))
        ],
    )


@router.put("/approval-rules/{rule_id}", response_model=schemas.LeaveApprovalRuleOut)
def update_approval_rule(
    rule_id: int,
    payload: schemas.LeaveApprovalRuleIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur")),
):
    rule = db.query(models.LeaveApprovalRule).filter(models.LeaveApprovalRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Approval rule not found")
    rule.employer_id = payload.employer_id
    rule.leave_type_code = payload.leave_type_code
    rule.worker_category = payload.worker_category
    rule.organizational_unit_id = payload.organizational_unit_id
    rule.approval_mode = payload.approval_mode
    rule.fallback_on_reject = payload.fallback_on_reject
    rule.active = payload.active
    for step in list(rule.steps):
        db.delete(step)
    db.flush()
    for step in payload.steps:
        db.add(models.LeaveApprovalRuleStep(rule_id=rule.id, **step.model_dump()))
    db.commit()
    db.refresh(rule)
    return schemas.LeaveApprovalRuleOut(
        id=rule.id,
        employer_id=rule.employer_id,
        leave_type_code=rule.leave_type_code,
        worker_category=rule.worker_category,
        organizational_unit_id=rule.organizational_unit_id,
        approval_mode=rule.approval_mode,
        fallback_on_reject=rule.fallback_on_reject,
        active=rule.active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        steps=[
            schemas.LeaveApprovalRuleStepOut(
                id=step.id,
                step_order=step.step_order,
                parallel_group=step.parallel_group,
                approver_kind=step.approver_kind,
                approver_role_code=step.approver_role_code,
                approver_user_id=step.approver_user_id,
                is_required=step.is_required,
                label=step.label,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
            for step in sorted(rule.steps, key=lambda item: (item.step_order, item.parallel_group, item.id))
        ],
    )


@router.delete("/approval-rules/{rule_id}")
def delete_approval_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur")),
):
    rule = db.query(models.LeaveApprovalRule).filter(models.LeaveApprovalRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Approval rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "Approval rule deleted"}


@router.post("/requests", response_model=schemas.LeaveRequestOut)
def submit_leave_request(
    payload: schemas.LeaveRequestCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REQUEST_SUBMISSION_ROLES)),
):
    worker = _get_worker_or_404(db, payload.worker_id)
    if not _can_submit_request(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    ensure_default_leave_types(db, worker.employer_id)
    request = create_leave_request(db, worker, payload, user)
    record_audit(
        db,
        actor=user,
        action="leave_request.create",
        entity_type="leave_request",
        entity_id=request.id,
        route="/leaves/requests",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after={"request_ref": request.request_ref, "status": request.status},
    )
    db.commit()
    db.refresh(request)
    return serialize_leave_request(request)


@router.get("/requests", response_model=list[schemas.LeaveRequestOut])
def list_leave_requests(
    worker_id: int | None = None,
    employer_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "direction")),
):
    query = db.query(models.LeaveRequest)
    if worker_id is not None:
        worker = _get_worker_or_404(db, worker_id)
        _assert_leave_scope(db, user, worker)
        query = query.filter(models.LeaveRequest.worker_id == worker_id)
    elif employer_id is not None:
        query = query.filter(models.LeaveRequest.employer_id == employer_id)
    elif user.worker_id:
        query = query.filter(models.LeaveRequest.worker_id == user.worker_id)
    if status_filter:
        query = query.filter(models.LeaveRequest.status == status_filter)
    rows = query.order_by(models.LeaveRequest.created_at.desc()).all()
    return [serialize_leave_request(row) for row in rows]


@router.get("/requests/{request_id}", response_model=schemas.LeaveRequestOut)
def get_leave_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "direction")),
):
    item = _request_or_404(db, request_id)
    _assert_leave_scope(db, user, item.worker, item)
    return serialize_leave_request(item)


@router.post("/requests/{request_id}/decision", response_model=schemas.LeaveRequestOut)
def decide_leave_request(
    request_id: int,
    payload: schemas.LeaveRequestDecisionIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction", "employe")),
):
    item = _request_or_404(db, request_id)
    _assert_leave_scope(db, user, item.worker, item)
    try:
        act_on_leave_request(db, item, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit(
        db,
        actor=user,
        action=f"leave_request.{payload.action}",
        entity_type="leave_request",
        entity_id=item.id,
        route=f"/leaves/requests/{item.id}/decision",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after={"status": item.status},
    )
    db.commit()
    db.refresh(item)
    return serialize_leave_request(item)


@router.delete("/requests/{request_id}")
def remove_leave_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction", "employe")),
):
    item = _request_or_404(db, request_id)
    _assert_leave_scope(db, user, item.worker, item)
    before = {
        "request_ref": item.request_ref,
        "status": item.status,
        "leave_type_code": item.final_leave_type_code,
        "start_date": item.start_date.isoformat(),
        "end_date": item.end_date.isoformat(),
    }
    try:
        delete_leave_request(db, item, user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    record_audit(
        db,
        actor=user,
        action="leave_request.delete",
        entity_type="leave_request",
        entity_id=request_id,
        route=f"/leaves/requests/{request_id}",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after=None,
    )
    db.commit()
    return {"message": "Leave request deleted"}


@router.post("/requests/{request_id}/attachments/upload", response_model=schemas.LeaveRequestOut)
async def upload_leave_request_attachment(
    request_id: int,
    attachment: UploadFile = File(...),
    label: str | None = Form(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*REQUEST_SUBMISSION_ROLES, "admin", "rh", "manager", "direction", "employeur")),
):
    item = _request_or_404(db, request_id)
    _assert_leave_scope(db, user, item.worker, item)
    safe_name = sanitize_filename_part(Path(attachment.filename or "justificatif").name)
    storage_name = f"leaves/requests/{item.id}/{date.today().strftime('%Y%m%d')}_{safe_name}"
    stored_path = save_upload_file(attachment.file, filename=storage_name)
    attachments = json_load(item.attachments_json, [])
    attachments.append(
        {
            "name": label or attachment.filename,
            "original_name": attachment.filename,
            "content_type": attachment.content_type,
            "path": stored_path,
            "download_url": build_static_path(storage_name),
            "uploaded_by_user_id": user.id,
        }
    )
    item.attachments_json = json_dump(attachments)
    item.attachment_count = len(attachments)
    record_audit(
        db,
        actor=user,
        action="leave_request.attachment.upload",
        entity_type="leave_request",
        entity_id=item.id,
        route=f"/leaves/requests/{item.id}/attachments/upload",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after={"attachments": len(attachments)},
    )
    db.commit()
    db.refresh(item)
    return serialize_leave_request(item)


@router.post("/requests/{request_id}/requalify", response_model=schemas.LeaveRequestOut)
def requalify_request(
    request_id: int,
    payload: schemas.LeaveRequestRequalifyIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction")),
):
    item = _request_or_404(db, request_id)
    _assert_leave_scope(db, user, item.worker)
    requalify_leave_request(db, item, user, payload)
    record_audit(
        db,
        actor=user,
        action="leave_request.requalify",
        entity_type="leave_request",
        entity_id=item.id,
        route=f"/leaves/requests/{item.id}/requalify",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after={"status": item.status, "final_leave_type_code": item.final_leave_type_code},
    )
    db.commit()
    db.refresh(item)
    return serialize_leave_request(item)


@router.get("/dashboard/worker/{worker_id}", response_model=schemas.LeaveDashboardOut)
def get_worker_dashboard(
    worker_id: int,
    period: str | None = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "direction")),
):
    worker = _get_worker_or_404(db, worker_id)
    _assert_leave_scope(db, user, worker)
    effective_period = period or date.today().strftime("%Y-%m")
    return get_worker_leave_dashboard(db, worker, effective_period)


@router.get("/dashboard/validator", response_model=schemas.LeaveValidatorDashboardOut)
def get_leave_validator_dashboard(
    employer_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction")),
):
    return get_validator_dashboard(db, user, employer_id)


@router.get("/reconciliation", response_model=list[schemas.AttendanceLeaveReconciliationOut])
def get_leave_reconciliation(
    employer_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction")),
):
    rows = []
    for row in list_reconciliations(db, employer_id):
        worker = db.query(models.Worker).filter(models.Worker.id == row.worker_id).first()
        if worker and (user_has_any_role(db, user, "admin", "rh", "employeur") or can_access_worker(db, user, worker)):
            rows.append(row)
    db.commit()
    return rows


@router.post("/planning/cycles", response_model=schemas.LeavePlanningCycleOut)
def create_leave_planning_cycle(
    payload: schemas.LeavePlanningCycleIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "direction")),
):
    item = create_planning_cycle(db, payload, user)
    db.commit()
    db.refresh(item)
    return schemas.LeavePlanningCycleOut(
        id=item.id,
        employer_id=item.employer_id,
        title=item.title,
        planning_year=item.planning_year,
        start_date=item.start_date,
        end_date=item.end_date,
        status=item.status,
        max_absent_per_unit=item.max_absent_per_unit,
        blackout_periods=json_load(item.blackout_periods_json, []),
        family_priority_enabled=item.family_priority_enabled,
        notes=item.notes,
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/planning/cycles/{cycle_id}/proposals", response_model=list[schemas.LeavePlanningProposalOut])
def get_planning_proposals(
    cycle_id: int,
    regenerate: bool = False,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "direction")),
):
    cycle = db.query(models.LeavePlanningCycle).filter(models.LeavePlanningCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Planning cycle not found")
    if regenerate:
        for row in db.query(models.LeavePlanningProposal).filter(models.LeavePlanningProposal.cycle_id == cycle.id).all():
            db.delete(row)
        db.flush()
        rows = generate_planning_proposals(db, cycle, user)
        db.commit()
        return rows
    rows = db.query(models.LeavePlanningProposal).filter(models.LeavePlanningProposal.cycle_id == cycle.id).order_by(models.LeavePlanningProposal.score.desc()).all()
    if not rows:
        generated = generate_planning_proposals(db, cycle, user)
        db.commit()
        return generated
    return [
        schemas.LeavePlanningProposalOut(
            id=row.id,
            cycle_id=row.cycle_id,
            worker_id=row.worker_id,
            worker_name=f"{row.worker.nom or ''} {row.worker.prenom or ''}".strip(),
            leave_type_code=row.leave_type_code,
            start_date=row.start_date,
            end_date=row.end_date,
            score=row.score,
            rationale=json_load(row.rationale_json, []),
            status=row.status,
        )
        for row in rows
    ]
