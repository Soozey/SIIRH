import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..leave_logic import calculate_leave_balance, calculate_permission_balance
from ..security import can_access_worker
from .workflow_service import get_or_create_workflow


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def json_load(value: Any, default: Any):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


DEFAULT_LEAVE_TYPES: tuple[dict[str, Any], ...] = (
    {"code": "CONGE_ANNUEL", "label": "Conge annuel", "category": "leave", "deduct_from_annual_balance": True, "validation_required": True, "justification_required": False, "payroll_impact": "none", "attendance_impact": "leave"},
    {"code": "PERMISSION_LEGALE", "label": "Permission legale / exceptionnelle", "category": "permission", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": False, "payroll_impact": "none", "attendance_impact": "authorized_absence"},
    {"code": "ABSENCE_AUTORISEE", "label": "Absence autorisee", "category": "permission", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": False, "payroll_impact": "none", "attendance_impact": "authorized_absence"},
    {"code": "ABSENCE_NON_AUTORISEE", "label": "Absence non autorisee", "category": "absence", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": False, "payroll_impact": "deduction", "attendance_impact": "unauthorized_absence", "payroll_code": "ABSNR_J"},
    {"code": "CONGE_MALADIE", "label": "Conge maladie", "category": "sick_leave", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": False, "payroll_impact": "informative", "attendance_impact": "medical_leave", "payroll_code": "ABSM_J"},
    {"code": "MATERNITE", "label": "Maternite / paternite", "category": "protected_leave", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": True, "payroll_impact": "special", "attendance_impact": "protected_leave"},
    {"code": "ACCIDENT_TRAVAIL", "label": "Accident du travail", "category": "protected_leave", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": True, "payroll_impact": "special", "attendance_impact": "protected_leave"},
    {"code": "FORMATION", "label": "Formation / conge education", "category": "training", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": False, "payroll_impact": "none", "attendance_impact": "training"},
    {"code": "SORTIE_COURTE", "label": "Sortie courte / permission horaire", "category": "hourly_permission", "deduct_from_annual_balance": False, "validation_required": True, "justification_required": False, "payroll_impact": "none", "attendance_impact": "hourly_absence", "supports_hour_range": True},
)


def ensure_default_leave_types(db: Session, employer_id: Optional[int] = None) -> list[models.LeaveTypeRule]:
    existing = {
        item.code: item
        for item in db.query(models.LeaveTypeRule).filter(models.LeaveTypeRule.employer_id == employer_id).all()
    }
    created = False
    for payload in DEFAULT_LEAVE_TYPES:
        if payload["code"] in existing:
            continue
        db.add(models.LeaveTypeRule(employer_id=employer_id, **payload))
        created = True
    if created:
        db.flush()
    return (
        db.query(models.LeaveTypeRule)
        .filter(models.LeaveTypeRule.employer_id == employer_id)
        .order_by(models.LeaveTypeRule.label.asc())
        .all()
    )


def _date_range(start_date: date, end_date: date) -> Iterable[date]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _business_days(start_date: date, end_date: date) -> float:
    total = 0.0
    for day in _date_range(start_date, end_date):
        if day.weekday() != 6:
            total += 1.0
    return total


def _default_approver_candidates(db: Session, worker: models.Worker, kind: str) -> list[models.AppUser]:
    query = db.query(models.AppUser).filter(models.AppUser.is_active == True)  # noqa: E712
    if worker.employer_id:
        query = query.filter(or_(models.AppUser.employer_id == worker.employer_id, models.AppUser.employer_id.is_(None)))
    users = query.all()
    if kind == "manager":
        if worker.organizational_unit_id:
            scoped: list[models.AppUser] = []
            for item in users:
                if item.role_code != "manager" or not item.worker_id:
                    continue
                manager_worker = db.query(models.Worker).filter(models.Worker.id == item.worker_id).first()
                if manager_worker and manager_worker.organizational_unit_id == worker.organizational_unit_id:
                    scoped.append(item)
            if scoped:
                return scoped
        return [item for item in users if item.role_code == "manager" and item.employer_id == worker.employer_id]
    if kind == "n_plus_2":
        return [item for item in users if item.role_code in {"direction", "departement"} and item.employer_id == worker.employer_id]
    if kind == "rh":
        return [item for item in users if item.role_code in {"rh", "admin"} and item.employer_id == worker.employer_id]
    if kind == "direction":
        return [item for item in users if item.role_code in {"direction", "admin"} and item.employer_id == worker.employer_id]
    if kind in {"site_manager", "department_manager"}:
        return [item for item in users if item.role_code in {"departement", "manager"} and item.employer_id == worker.employer_id]
    return []


def _resolve_rule(db: Session, worker: models.Worker, leave_type_code: str) -> Optional[models.LeaveApprovalRule]:
    query = db.query(models.LeaveApprovalRule).filter(
        models.LeaveApprovalRule.active == True,  # noqa: E712
        or_(models.LeaveApprovalRule.employer_id == worker.employer_id, models.LeaveApprovalRule.employer_id.is_(None)),
        models.LeaveApprovalRule.leave_type_code == leave_type_code,
    )
    rules = query.order_by(models.LeaveApprovalRule.employer_id.desc().nullslast(), models.LeaveApprovalRule.id.asc()).all()
    for rule in rules:
        if rule.worker_category and (worker.categorie_prof or "") != rule.worker_category:
            continue
        if rule.organizational_unit_id and rule.organizational_unit_id != worker.organizational_unit_id:
            continue
        return rule
    return None


def ensure_default_approval_rule(db: Session, worker: models.Worker, leave_type_code: str) -> models.LeaveApprovalRule:
    existing = _resolve_rule(db, worker, leave_type_code)
    if existing:
        return existing
    rule = models.LeaveApprovalRule(
        employer_id=worker.employer_id,
        leave_type_code=leave_type_code,
        approval_mode="sequential",
        fallback_on_reject="reject",
        active=True,
    )
    db.add(rule)
    db.flush()
    db.add(models.LeaveApprovalRuleStep(rule_id=rule.id, step_order=1, parallel_group=1, approver_kind="manager", approver_role_code="manager", label="N+1"))
    db.add(models.LeaveApprovalRuleStep(rule_id=rule.id, step_order=2, parallel_group=1, approver_kind="rh", approver_role_code="rh", label="RH"))
    db.flush()
    return rule


def _get_type_rule(db: Session, worker: models.Worker, code: str) -> models.LeaveTypeRule:
    item = (
        db.query(models.LeaveTypeRule)
        .filter(
            models.LeaveTypeRule.code == code,
            models.LeaveTypeRule.active == True,  # noqa: E712
            or_(models.LeaveTypeRule.employer_id == worker.employer_id, models.LeaveTypeRule.employer_id.is_(None)),
        )
        .order_by(models.LeaveTypeRule.employer_id.desc().nullslast(), models.LeaveTypeRule.id.desc())
        .first()
    )
    if not item:
        ensure_default_leave_types(db, worker.employer_id)
        item = (
            db.query(models.LeaveTypeRule)
            .filter(
                models.LeaveTypeRule.code == code,
                or_(models.LeaveTypeRule.employer_id == worker.employer_id, models.LeaveTypeRule.employer_id.is_(None)),
            )
            .order_by(models.LeaveTypeRule.employer_id.desc().nullslast(), models.LeaveTypeRule.id.desc())
            .first()
        )
    if not item:
        raise ValueError("Leave type not found")
    return item


def _request_alerts(
    db: Session,
    worker: models.Worker,
    type_rule: models.LeaveTypeRule,
    start_date: date,
    end_date: date,
    duration_days: float,
    attachment_count: int,
    exclude_request_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    period = start_date.strftime("%Y-%m")
    balance = calculate_leave_balance(db, worker.id, period)
    if type_rule.deduct_from_annual_balance and duration_days > balance.get("balance", 0.0):
        alerts.append({"code": "insufficient_balance", "severity": "warning", "message": "La demande depasse le solde de conge disponible."})
    if type_rule.justification_required and attachment_count <= 0:
        alerts.append({"code": "missing_attachment", "severity": "warning", "message": "Une piece justificative est requise pour ce type d'absence."})
    query = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.worker_id == worker.id,
        models.LeaveRequest.status.in_(("submitted", "pending_validation_1", "pending_validation_2", "pending_parallel", "approved", "integrated", "requalified")),
        models.LeaveRequest.start_date <= end_date,
        models.LeaveRequest.end_date >= start_date,
    )
    if exclude_request_id:
        query = query.filter(models.LeaveRequest.id != exclude_request_id)
    if query.count():
        alerts.append({"code": "overlap", "severity": "warning", "message": "La demande chevauche une absence existante."})
    if worker.date_embauche:
        months_service = max(0, (start_date.year - worker.date_embauche.year) * 12 + start_date.month - worker.date_embauche.month)
        if months_service < 12 and type_rule.code == "CONGE_ANNUEL":
            alerts.append({"code": "opening_right_not_reached", "severity": "info", "message": "Le droit complet au conge annuel n'a pas encore atteint 12 mois de service."})
    return alerts


def _approver_label(approval: models.LeaveRequestApproval) -> str:
    if approval.label:
        return approval.label
    if approval.approver_user:
        return approval.approver_user.full_name or approval.approver_user.username
    return approval.approver_role_code or approval.approver_kind


def _serialize_history(item: models.LeaveRequestHistory) -> schemas.LeaveRequestHistoryOut:
    actor_name = None
    if item.actor:
        actor_name = item.actor.full_name or item.actor.username
    return schemas.LeaveRequestHistoryOut(
        id=item.id,
        action=item.action,
        from_status=item.from_status,
        to_status=item.to_status,
        actor_user_id=item.actor_user_id,
        actor_name=actor_name,
        comment=item.comment,
        metadata=json_load(item.metadata_json, {}),
        created_at=item.created_at,
    )


def serialize_leave_request(item: models.LeaveRequest) -> schemas.LeaveRequestOut:
    approvals = [
        schemas.LeaveRequestApprovalOut(
            id=approval.id,
            step_order=approval.step_order,
            parallel_group=approval.parallel_group,
            approver_kind=approval.approver_kind,
            approver_user_id=approval.approver_user_id,
            approver_role_code=approval.approver_role_code,
            approver_label=_approver_label(approval),
            label=approval.label,
            is_required=approval.is_required,
            status=approval.status,
            acted_at=approval.acted_at,
            comment=approval.comment,
        )
        for approval in sorted(item.approvals, key=lambda row: (row.step_order, row.parallel_group, row.id))
    ]
    remaining = [_approver_label(approval) for approval in item.approvals if approval.status == "pending"]
    requester_name = None
    if item.requested_by:
        requester_name = item.requested_by.full_name or item.requested_by.username
    return schemas.LeaveRequestOut(
        id=item.id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        request_ref=item.request_ref,
        leave_type_code=item.leave_type_code,
        initial_leave_type_code=item.initial_leave_type_code,
        final_leave_type_code=item.final_leave_type_code,
        status=item.status,
        approval_mode=item.approval_mode,
        fallback_on_reject=item.fallback_on_reject,
        current_step_order=item.current_step_order,
        period=item.period,
        start_date=item.start_date,
        end_date=item.end_date,
        duration_days=item.duration_days,
        duration_hours=item.duration_hours,
        partial_day_mode=item.partial_day_mode,
        subject=item.subject,
        reason=item.reason,
        comment=item.comment,
        attachment_required=item.attachment_required,
        attachment_count=item.attachment_count,
        attachments=json_load(item.attachments_json, []),
        estimated_balance_delta=item.estimated_balance_delta,
        estimated_payroll_impact=item.estimated_payroll_impact,
        estimated_attendance_impact=item.estimated_attendance_impact,
        legacy_request_type=item.legacy_request_type,
        legacy_request_id=item.legacy_request_id,
        requested_by_user_id=item.requested_by_user_id,
        requested_by_name=requester_name,
        approved_at=item.approved_at,
        rejected_at=item.rejected_at,
        submitted_at=item.submitted_at,
        cancelled_at=item.cancelled_at,
        integrated_at=item.integrated_at,
        requalified_at=item.requalified_at,
        validations_remaining=remaining,
        alerts=[],
        approvals=approvals,
        history=[_serialize_history(row) for row in sorted(item.history, key=lambda row: row.created_at)],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _write_history(
    db: Session,
    leave_request: models.LeaveRequest,
    action: str,
    actor: Optional[models.AppUser],
    from_status: Optional[str],
    to_status: Optional[str],
    comment: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
):
    db.add(
        models.LeaveRequestHistory(
            leave_request_id=leave_request.id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor.id if actor else None,
            comment=comment,
            metadata_json=json_dump(metadata or {}),
        )
    )


def _next_request_ref(db: Session, worker: models.Worker) -> str:
    prefix = f"ABS-{datetime.now(timezone.utc).strftime('%Y%m')}"
    count = db.query(models.LeaveRequest).filter(models.LeaveRequest.request_ref.like(f"{prefix}-%")).count() + 1
    return f"{prefix}-{count:04d}"


def _build_approvals(db: Session, leave_request: models.LeaveRequest, worker: models.Worker, rule: models.LeaveApprovalRule) -> list[models.LeaveRequestApproval]:
    rows: list[models.LeaveRequestApproval] = []
    for step in sorted(rule.steps, key=lambda item: (item.step_order, item.parallel_group, item.id)):
        users: list[models.AppUser] = []
        if step.approver_user_id:
            user = db.query(models.AppUser).filter(models.AppUser.id == step.approver_user_id, models.AppUser.is_active == True).first()  # noqa: E712
            if user:
                users = [user]
        else:
            users = _default_approver_candidates(db, worker, step.approver_kind)
            if step.approver_role_code:
                users = [user for user in users if user.role_code == step.approver_role_code]
        if not users:
            rows.append(
                models.LeaveRequestApproval(
                    leave_request_id=leave_request.id,
                    step_order=step.step_order,
                    parallel_group=step.parallel_group,
                    approver_kind=step.approver_kind,
                    approver_role_code=step.approver_role_code,
                    label=step.label,
                    is_required=step.is_required,
                    status="pending",
                )
            )
            continue
        for user in users:
            rows.append(
                models.LeaveRequestApproval(
                    leave_request_id=leave_request.id,
                    step_order=step.step_order,
                    parallel_group=step.parallel_group,
                    approver_kind=step.approver_kind,
                    approver_user_id=user.id,
                    approver_role_code=step.approver_role_code or user.role_code,
                    label=step.label,
                    is_required=step.is_required,
                    status="pending",
                )
            )
    return rows


def _update_status_after_approval_change(leave_request: models.LeaveRequest):
    pending = [row for row in leave_request.approvals if row.status == "pending"]
    rejected = [row for row in leave_request.approvals if row.status == "rejected"]
    if rejected:
        leave_request.status = "rejected"
        leave_request.rejected_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return
    if pending:
        steps = sorted({row.step_order for row in pending})
        leave_request.current_step_order = steps[0]
        same_step = [row for row in pending if row.step_order == steps[0]]
        leave_request.status = "pending_parallel" if len(same_step) > 1 else f"pending_validation_{steps[0]}"
        return
    leave_request.status = "approved"
    leave_request.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    leave_request.current_step_order = None


def _legacy_absence_code(type_rule: models.LeaveTypeRule) -> Optional[str]:
    if type_rule.payroll_code:
        return type_rule.payroll_code
    if type_rule.payroll_impact == "deduction":
        return "ABSNR_J"
    return None


def _attendance_snapshot(db: Session, leave_request: models.LeaveRequest, type_rule: models.LeaveTypeRule) -> tuple[dict[str, Any], str, str, str]:
    calculations = (
        db.query(models.HSCalculationHS)
        .join(models.HSJourHS, models.HSJourHS.calculation_id_HS == models.HSCalculationHS.id_HS)
        .filter(
            models.HSCalculationHS.worker_id_HS == leave_request.worker_id,
            models.HSJourHS.date_HS >= leave_request.start_date,
            models.HSJourHS.date_HS <= leave_request.end_date,
        )
        .order_by(models.HSJourHS.date_HS.asc(), models.HSJourHS.id_HS.asc())
        .all()
    )
    day_rows: list[models.HSJourHS] = []
    for calc in calculations:
        for row in calc.jours_HS:
            if leave_request.start_date <= row.date_HS <= leave_request.end_date:
                day_rows.append(row)
    worked_days = []
    total_hours = 0.0
    for row in day_rows:
        start_minutes = row.entree_HS.hour * 60 + row.entree_HS.minute
        end_minutes = row.sortie_HS.hour * 60 + row.sortie_HS.minute
        duration_hours = max(0.0, round((end_minutes - start_minutes) / 60, 2))
        total_hours += duration_hours
        worked_days.append(
            {
                "date": row.date_HS.isoformat(),
                "type_jour": row.type_jour_HS,
                "entree": row.entree_HS.isoformat(timespec="minutes"),
                "sortie": row.sortie_HS.isoformat(timespec="minutes"),
                "duration_hours": duration_hours,
            }
        )
    payload = {
        "source": "hs_jours_HS" if worked_days else "hs_jours_HS_empty",
        "worked_days_count": len(worked_days),
        "worked_dates": [item["date"] for item in worked_days],
        "total_hours": round(total_hours, 2),
        "entries": worked_days[:10],
    }
    if not worked_days:
        return payload, "validated_request_reference", "none", "Aucune presence detaillee detectee dans le pointage sur la periode de la demande."
    if type_rule.supports_hour_range or (leave_request.duration_hours or 0.0) > 0:
        return payload, "attendance_review_required", "medium", "Presence detectee sur une demande horaire: verifier la coherence horaire avant cloture."
    return payload, "attendance_conflict", "high", "Presence detectee pendant une demande validee: verifier, requalifier, annuler ou supprimer selon les droits."


def _legacy_absence_snapshot(db: Session, leave_request: models.LeaveRequest, type_rule: models.LeaveTypeRule) -> tuple[dict[str, Any], str, str, str]:
    payroll_code = _legacy_absence_code(type_rule)
    if not payroll_code:
        return {}, "validated_request_reference", "none", "Aucune ecriture paie attendue pour ce type de demande."
    absence = db.query(models.Absence).filter(models.Absence.worker_id == leave_request.worker_id, models.Absence.mois == leave_request.period).first()
    actual = float(getattr(absence, payroll_code, 0.0) or 0.0) if absence else 0.0
    expected = float(leave_request.duration_days or 0.0)
    payload = {
        "source": "absence_legacy",
        "payroll_code": payroll_code,
        "actual_quantity": actual,
        "expected_quantity": expected,
    }
    if not absence:
        return payload, "missing_legacy_absence", "medium", f"Aucune absence paie {payroll_code} enregistree pour la periode."
    if round(actual, 2) != round(expected, 2):
        return payload, "mismatch", "high", f"Ecart entre l'absence paie {payroll_code} ({actual}) et la demande validee ({expected})."
    return payload, "validated_request_reference", "none", f"Absence paie {payroll_code} alignee avec la demande validee."


def _merge_reconciliation_payloads(
    attendance_payload: dict[str, Any],
    legacy_payload: dict[str, Any],
    attendance_status: str,
    attendance_level: str,
    attendance_notes: str,
    legacy_status: str,
    legacy_level: str,
    legacy_notes: str,
) -> tuple[str, str, dict[str, Any], str]:
    payload: dict[str, Any] = {"attendance": attendance_payload}
    if legacy_payload:
        payload["legacy_absence"] = legacy_payload
    severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
    candidates = [
        (attendance_status, attendance_level, attendance_notes),
        (legacy_status, legacy_level, legacy_notes),
    ]
    chosen_status = "validated_request_reference"
    chosen_level = "none"
    chosen_notes = attendance_notes or legacy_notes
    for status, level, notes in candidates:
        if severity_rank.get(level, 0) > severity_rank.get(chosen_level, 0):
            chosen_status = status
            chosen_level = level
            chosen_notes = notes
    if chosen_level == "none" and legacy_payload:
        chosen_notes = legacy_notes
    return chosen_status, chosen_level, payload, chosen_notes


def _upsert_reconciliation_record(db: Session, leave_request: models.LeaveRequest, type_rule: models.LeaveTypeRule) -> models.AttendanceLeaveReconciliation:
    reconciliation = (
        db.query(models.AttendanceLeaveReconciliation)
        .filter(models.AttendanceLeaveReconciliation.leave_request_id == leave_request.id)
        .first()
    )
    if not reconciliation:
        reconciliation = models.AttendanceLeaveReconciliation(
            leave_request_id=leave_request.id,
            employer_id=leave_request.employer_id,
            worker_id=leave_request.worker_id,
            period=leave_request.period,
        )
        db.add(reconciliation)
        db.flush()
    recalculate_reconciliation(db, reconciliation, type_rule=type_rule)
    return reconciliation


def _integrate_approved_request(db: Session, leave_request: models.LeaveRequest, type_rule: models.LeaveTypeRule):
    leave_request.status = "integrated"
    leave_request.integrated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if type_rule.deduct_from_annual_balance:
        legacy = None
        if leave_request.legacy_request_type == "leave" and leave_request.legacy_request_id:
            legacy = db.query(models.Leave).filter(models.Leave.id == leave_request.legacy_request_id).first()
        if not legacy:
            legacy = models.Leave(
                worker_id=leave_request.worker_id,
                period=leave_request.period,
                start_date=leave_request.start_date,
                end_date=leave_request.end_date,
                days_taken=leave_request.duration_days,
                notes=leave_request.subject,
            )
            db.add(legacy)
            db.flush()
        else:
            legacy.period = leave_request.period
            legacy.start_date = leave_request.start_date
            legacy.end_date = leave_request.end_date
            legacy.days_taken = leave_request.duration_days
            legacy.notes = leave_request.subject
        leave_request.legacy_request_type = "leave"
        leave_request.legacy_request_id = legacy.id
        workflow = get_or_create_workflow(db, "leave", legacy.id)
        workflow.overall_status = "approved"
        workflow.manager_status = "approved"
        workflow.rh_status = "approved"
    else:
        legacy = None
        if leave_request.legacy_request_type == "permission" and leave_request.legacy_request_id:
            legacy = db.query(models.Permission).filter(models.Permission.id == leave_request.legacy_request_id).first()
        if not legacy:
            legacy = models.Permission(
                worker_id=leave_request.worker_id,
                period=leave_request.period,
                start_date=leave_request.start_date,
                end_date=leave_request.end_date,
                days_taken=leave_request.duration_days,
                notes=leave_request.subject,
            )
            db.add(legacy)
            db.flush()
        else:
            legacy.period = leave_request.period
            legacy.start_date = leave_request.start_date
            legacy.end_date = leave_request.end_date
            legacy.days_taken = leave_request.duration_days
            legacy.notes = leave_request.subject
        leave_request.legacy_request_type = "permission"
        leave_request.legacy_request_id = legacy.id
        workflow = get_or_create_workflow(db, "permission", legacy.id)
        workflow.overall_status = "approved"
        workflow.manager_status = "approved"
        workflow.rh_status = "approved"
    payroll_code = _legacy_absence_code(type_rule)
    if payroll_code:
        absence = db.query(models.Absence).filter(models.Absence.worker_id == leave_request.worker_id, models.Absence.mois == leave_request.period).first()
        if not absence:
            absence = models.Absence(worker_id=leave_request.worker_id, mois=leave_request.period)
            db.add(absence)
            db.flush()
        setattr(absence, payroll_code, float(getattr(absence, payroll_code, 0.0) or 0.0) + float(leave_request.duration_days))
    _upsert_reconciliation_record(db, leave_request, type_rule)


def create_leave_request(db: Session, worker: models.Worker, payload: schemas.LeaveRequestCreate, actor: Optional[models.AppUser]) -> models.LeaveRequest:
    type_rule = _get_type_rule(db, worker, payload.leave_type_code)
    duration_days = payload.duration_days if payload.duration_days is not None else _business_days(payload.start_date, payload.end_date)
    rule = ensure_default_approval_rule(db, worker, type_rule.code)
    request = models.LeaveRequest(
        employer_id=worker.employer_id,
        worker_id=worker.id,
        request_ref=_next_request_ref(db, worker),
        leave_type_code=type_rule.code,
        initial_leave_type_code=type_rule.code,
        final_leave_type_code=type_rule.code,
        status="submitted" if payload.submit_now else "draft",
        approval_mode=rule.approval_mode,
        fallback_on_reject=rule.fallback_on_reject,
        current_step_order=1 if payload.submit_now and type_rule.validation_required else None,
        period=payload.start_date.strftime("%Y-%m"),
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=duration_days,
        duration_hours=payload.duration_hours,
        partial_day_mode=payload.partial_day_mode,
        subject=payload.subject,
        reason=payload.reason,
        comment=payload.comment,
        attachment_required=type_rule.justification_required,
        attachment_count=len(payload.attachments),
        attachments_json=json_dump(payload.attachments),
        estimated_balance_delta=-duration_days if type_rule.deduct_from_annual_balance else 0.0,
        estimated_payroll_impact=type_rule.payroll_impact,
        estimated_attendance_impact=type_rule.attendance_impact,
        requested_by_user_id=actor.id if actor else None,
        submitted_at=datetime.now(timezone.utc).replace(tzinfo=None) if payload.submit_now else None,
    )
    db.add(request)
    db.flush()
    if type_rule.validation_required:
        for approval in _build_approvals(db, request, worker, rule):
            db.add(approval)
        db.flush()
    _write_history(db, request, "request.created", actor, None, request.status, metadata={"leave_type_code": type_rule.code})
    alerts = _request_alerts(db, worker, type_rule, request.start_date, request.end_date, request.duration_days, request.attachment_count)
    if alerts:
        _write_history(db, request, "request.alerted", actor, request.status, request.status, metadata={"alerts": alerts})
    if not type_rule.validation_required:
        request.status = "approved"
        request.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        _integrate_approved_request(db, request, type_rule)
    else:
        _update_status_after_approval_change(request)
    db.flush()
    return request


def act_on_leave_request(db: Session, leave_request: models.LeaveRequest, actor: models.AppUser, payload: schemas.LeaveRequestDecisionIn) -> models.LeaveRequest:
    action = (payload.action or "").strip().lower()
    if action == "cancel":
        if leave_request.integrated_at or leave_request.status in {"integrated", "approved"}:
            raise ValueError("La demande est deja consommee ou cloturee et ne peut plus etre annulee.")
        if actor.worker_id not in {leave_request.worker_id, None} and actor.role_code not in {"admin", "rh", "employeur", "manager", "direction"}:
            raise ValueError("Seul le salarie concerne ou un role RH/validation peut annuler cette demande.")
        old_status = leave_request.status
        leave_request.status = "cancelled"
        leave_request.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        _write_history(db, leave_request, "request.cancelled", actor, old_status, leave_request.status, payload.comment)
        return leave_request

    pending = [row for row in leave_request.approvals if row.status == "pending"]
    if not pending:
        raise ValueError("No pending approval")
    approval = next((row for row in pending if row.approver_user_id == actor.id), None)
    if not approval and actor.role_code in {"admin", "rh"}:
        approval = pending[0]
    if not approval:
        raise ValueError("Approval step not assigned to this actor")
    old_status = leave_request.status
    approval.comment = payload.comment
    approval.acted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if action in {"approve", "validate"}:
        approval.status = "approved"
    elif action in {"reject", "return", "request_correction"}:
        if not (payload.comment or "").strip():
            raise ValueError("A comment is required for rejection or correction request")
        approval.status = "rejected"
    else:
        raise ValueError("Unsupported action")
    _update_status_after_approval_change(leave_request)
    if leave_request.status == "approved":
        type_rule = _get_type_rule(db, leave_request.worker, leave_request.final_leave_type_code)
        _integrate_approved_request(db, leave_request, type_rule)
    _write_history(db, leave_request, f"request.{action}", actor, old_status, leave_request.status, payload.comment)
    return leave_request


def requalify_leave_request(db: Session, leave_request: models.LeaveRequest, actor: models.AppUser, payload: schemas.LeaveRequestRequalifyIn) -> models.LeaveRequest:
    type_rule = _get_type_rule(db, leave_request.worker, payload.new_leave_type_code)
    old_status = leave_request.status
    old_type = leave_request.final_leave_type_code
    leave_request.final_leave_type_code = type_rule.code
    leave_request.leave_type_code = type_rule.code
    leave_request.estimated_balance_delta = -leave_request.duration_days if type_rule.deduct_from_annual_balance else 0.0
    leave_request.estimated_payroll_impact = type_rule.payroll_impact
    leave_request.estimated_attendance_impact = type_rule.attendance_impact
    leave_request.requalified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if leave_request.status not in {"approved", "integrated"}:
        leave_request.status = "requalified"
    _write_history(db, leave_request, "request.requalified", actor, old_status, leave_request.status, payload.comment, metadata={"from": old_type, "to": type_rule.code})
    if leave_request.status in {"approved", "integrated"}:
        _integrate_approved_request(db, leave_request, type_rule)
    else:
        _upsert_reconciliation_record(db, leave_request, type_rule)
    return leave_request


def delete_leave_request(db: Session, leave_request: models.LeaveRequest, actor: models.AppUser):
    if leave_request.integrated_at or leave_request.legacy_request_id or leave_request.status in {"approved", "integrated"}:
        raise ValueError("La demande est deja integree ou rattachee a une ecriture historique et ne peut plus etre supprimee.")
    if actor.worker_id not in {leave_request.worker_id, None} and actor.role_code not in {"admin", "rh", "employeur", "manager", "direction"}:
        raise ValueError("Seul le salarie concerne ou un role RH/validation peut supprimer cette demande.")
    for row in list(leave_request.approvals):
        db.delete(row)
    for row in list(leave_request.history):
        db.delete(row)
    for row in db.query(models.AttendanceLeaveReconciliation).filter(models.AttendanceLeaveReconciliation.leave_request_id == leave_request.id).all():
        db.delete(row)
    db.delete(leave_request)


def get_worker_leave_dashboard(db: Session, worker: models.Worker, period: str) -> schemas.LeaveDashboardOut:
    ensure_default_leave_types(db, worker.employer_id)
    requests = db.query(models.LeaveRequest).filter(models.LeaveRequest.worker_id == worker.id).order_by(models.LeaveRequest.created_at.desc()).all()
    request_payloads = [serialize_leave_request(item) for item in requests]
    for payload in request_payloads:
        type_rule = _get_type_rule(db, worker, payload.final_leave_type_code)
        payload.alerts = _request_alerts(db, worker, type_rule, payload.start_date, payload.end_date, payload.duration_days, payload.attachment_count, exclude_request_id=payload.id)
    pending_balance = sum(abs(item.estimated_balance_delta) for item in requests if item.status.startswith("pending") or item.status == "submitted")
    leave_balance = calculate_leave_balance(db, worker.id, period)
    permission_balance = calculate_permission_balance(db, worker.id, int(period.split("-")[0]))
    calendar = [
        {"id": item.id, "start_date": item.start_date.isoformat(), "end_date": item.end_date.isoformat(), "status": item.status, "leave_type_code": item.final_leave_type_code, "subject": item.subject}
        for item in requests
        if item.status in {"approved", "integrated", "pending_validation_1", "pending_validation_2", "pending_parallel", "submitted", "requalified"}
    ]
    alerts = []
    if leave_balance.get("balance", 0.0) > 15 and not any(item.duration_days >= 15 and item.final_leave_type_code == "CONGE_ANNUEL" and item.status in {"approved", "integrated"} for item in requests):
        alerts.append({"code": "mandatory_fraction", "severity": "info", "message": "La premiere fraction continue de 15 jours du conge annuel reste a planifier."})
    if leave_balance.get("balance", 0.0) > 20:
        alerts.append({"code": "old_balance", "severity": "warning", "message": "Un reliquat important de conge annuel doit etre consomme."})
    notifications = [{"type": "workflow", "label": f"{item.request_ref} - {item.status}", "status": item.status} for item in requests[:8]]
    return schemas.LeaveDashboardOut(
        worker_id=worker.id,
        employer_id=worker.employer_id,
        period=period,
        balances={
            "acquired": leave_balance.get("accrued", 0.0),
            "consumed": leave_balance.get("taken", 0.0),
            "annual_balance": leave_balance.get("balance", 0.0),
            "pending_annual": round(pending_balance, 2),
            "projected_annual_balance": round(leave_balance.get("balance", 0.0) - pending_balance, 2),
            "permission_allowance": permission_balance.get("allowance", 0.0),
            "permission_consumed": permission_balance.get("taken", 0.0),
            "permission_balance": permission_balance.get("balance", 0.0),
        },
        requests=request_payloads,
        alerts=alerts,
        notifications=notifications,
        calendar=calendar,
    )


def get_validator_dashboard(db: Session, actor: models.AppUser, employer_id: Optional[int] = None) -> schemas.LeaveValidatorDashboardOut:
    query = db.query(models.LeaveRequestApproval).join(models.LeaveRequest).filter(
        models.LeaveRequestApproval.status == "pending",
        models.LeaveRequest.status.notin_(("approved", "integrated", "cancelled", "rejected")),
    )
    if actor.role_code not in {"admin", "rh"}:
        query = query.filter(models.LeaveRequestApproval.approver_user_id == actor.id)
    if employer_id is not None:
        query = query.filter(models.LeaveRequest.employer_id == employer_id)
    approvals = query.order_by(models.LeaveRequest.start_date.asc()).all()
    requests = []
    seen = set()
    for approval in approvals:
        if approval.leave_request_id in seen:
            continue
        seen.add(approval.leave_request_id)
        requests.append(serialize_leave_request(approval.leave_request))
    urgent = [item for item in requests if item.start_date <= date.today() + timedelta(days=2)]
    reconciliations_query = db.query(models.AttendanceLeaveReconciliation)
    if employer_id is not None:
        reconciliations_query = reconciliations_query.filter(models.AttendanceLeaveReconciliation.employer_id == employer_id)
    reconciliations = reconciliations_query.order_by(models.AttendanceLeaveReconciliation.updated_at.desc()).all()
    conflicted_ids: set[int] = set()
    for row in reconciliations:
        if actor.role_code not in {"admin", "rh"} and not can_access_worker(db, actor, row.worker):
            continue
        recalculate_reconciliation(db, row)
        if row.discrepancy_level != "none":
            conflicted_ids.add(row.leave_request_id)
    conflicts = [
        serialize_leave_request(db.query(models.LeaveRequest).filter(models.LeaveRequest.id == request_id).first())
        for request_id in conflicted_ids
        if db.query(models.LeaveRequest).filter(models.LeaveRequest.id == request_id).first() is not None
    ]
    overlap_conflicts = [item for item in requests if any(alert["code"] == "overlap" for alert in item.alerts)]
    seen_conflict_ids = {item.id for item in conflicts}
    for item in overlap_conflicts:
        if item.id not in seen_conflict_ids:
            conflicts.append(item)
    return schemas.LeaveValidatorDashboardOut(
        metrics={"pending": len(requests), "urgent": len(urgent), "conflicts": len(conflicts)},
        pending_requests=requests,
        urgent_requests=urgent,
        conflicts=conflicts,
        alerts=[
            {"severity": "warning", "message": "Aucun validateur affecte sur certaines demandes."}
            for item in requests
            if any(approval.approver_user_id is None for approval in item.approvals)
        ],
    )


def create_planning_cycle(db: Session, payload: schemas.LeavePlanningCycleIn, actor: models.AppUser) -> models.LeavePlanningCycle:
    item = models.LeavePlanningCycle(
        employer_id=payload.employer_id,
        title=payload.title,
        planning_year=payload.planning_year,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        max_absent_per_unit=payload.max_absent_per_unit,
        blackout_periods_json=json_dump(payload.blackout_periods),
        family_priority_enabled=payload.family_priority_enabled,
        notes=payload.notes,
        created_by_user_id=actor.id if actor else None,
    )
    db.add(item)
    db.flush()
    return item


def _planning_score(db: Session, worker: models.Worker, start_date: date, end_date: date, cycle: models.LeavePlanningCycle) -> tuple[float, list[dict[str, Any]]]:
    rationale: list[dict[str, Any]] = []
    score = 0.0
    period = start_date.strftime("%Y-%m")
    leave_balance = calculate_leave_balance(db, worker.id, period)
    months_service = 0
    if worker.date_embauche:
        months_service = max(0, (start_date.year - worker.date_embauche.year) * 12 + start_date.month - worker.date_embauche.month)
    if months_service >= 12:
        score += 25
        rationale.append({"factor": "opening_right", "weight": 25, "message": "Droit au conge annuel ouvert."})
    if leave_balance.get("balance", 0.0) >= 15:
        score += 20
        rationale.append({"factor": "mandatory_fraction", "weight": 20, "message": "Premiere fraction de 15 jours encore due ou fortement recommandee."})
    seniority_bonus = min(months_service, 20)
    score += seniority_bonus
    rationale.append({"factor": "seniority", "weight": seniority_bonus, "message": "Priorite basee sur l'anciennete."})
    old_reliquat = max(0.0, leave_balance.get("balance", 0.0) - 30.0)
    if old_reliquat > 0:
        bonus = min(old_reliquat, 15.0)
        score += bonus
        rationale.append({"factor": "old_balance", "weight": bonus, "message": "Reliquat ancien a consommer."})
    overlap_count = db.query(models.LeaveRequest).filter(models.LeaveRequest.employer_id == worker.employer_id, models.LeaveRequest.worker_id != worker.id, models.LeaveRequest.status.in_(("approved", "integrated", "pending_validation_1", "pending_validation_2", "pending_parallel", "submitted")), models.LeaveRequest.start_date <= end_date, models.LeaveRequest.end_date >= start_date).count()
    penalty = min(overlap_count * 10, 30)
    if penalty:
        score -= penalty
        rationale.append({"factor": "service_continuity", "weight": -penalty, "message": "Penalite de continuite de service sur la periode."})
    for blackout in json_load(cycle.blackout_periods_json, []):
        raw_start = blackout.get("start_date")
        raw_end = blackout.get("end_date")
        if not raw_start or not raw_end:
            continue
        blackout_start = date.fromisoformat(raw_start)
        blackout_end = date.fromisoformat(raw_end)
        if blackout_start <= end_date and blackout_end >= start_date:
            score -= 50
            rationale.append({"factor": "blackout", "weight": -50, "message": "Periode sensible / blackout."})
            break
    return score, rationale


def generate_planning_proposals(db: Session, cycle: models.LeavePlanningCycle, actor: Optional[models.AppUser] = None) -> list[schemas.LeavePlanningProposalOut]:
    workers = db.query(models.Worker).filter(models.Worker.employer_id == cycle.employer_id).order_by(models.Worker.nom.asc(), models.Worker.prenom.asc()).all()
    proposals: list[schemas.LeavePlanningProposalOut] = []
    for worker in workers:
        score, rationale = _planning_score(db, worker, cycle.start_date, cycle.end_date, cycle)
        proposal = models.LeavePlanningProposal(cycle_id=cycle.id, worker_id=worker.id, leave_type_code="CONGE_ANNUEL", start_date=cycle.start_date, end_date=cycle.end_date, score=score, rationale_json=json_dump(rationale), status="proposed", created_by_user_id=actor.id if actor else None)
        db.add(proposal)
        db.flush()
        proposals.append(schemas.LeavePlanningProposalOut(id=proposal.id, cycle_id=proposal.cycle_id, worker_id=worker.id, worker_name=f"{worker.nom or ''} {worker.prenom or ''}".strip(), leave_type_code=proposal.leave_type_code, start_date=proposal.start_date, end_date=proposal.end_date, score=proposal.score, rationale=json_load(proposal.rationale_json, []), status=proposal.status))
    proposals.sort(key=lambda item: item.score, reverse=True)
    return proposals


def recalculate_reconciliation(db: Session, reconciliation: models.AttendanceLeaveReconciliation, type_rule: Optional[models.LeaveTypeRule] = None):
    leave_request = reconciliation.leave_request
    if not leave_request:
        return
    resolved_type_rule = type_rule or _get_type_rule(db, leave_request.worker, leave_request.final_leave_type_code)
    attendance_payload, attendance_status, attendance_level, attendance_notes = _attendance_snapshot(db, leave_request, resolved_type_rule)
    legacy_payload, legacy_status, legacy_level, legacy_notes = _legacy_absence_snapshot(db, leave_request, resolved_type_rule)
    status, discrepancy_level, merged_payload, notes = _merge_reconciliation_payloads(
        attendance_payload,
        legacy_payload,
        attendance_status,
        attendance_level,
        attendance_notes,
        legacy_status,
        legacy_level,
        legacy_notes,
    )
    reconciliation.status = status
    reconciliation.discrepancy_level = discrepancy_level
    reconciliation.attendance_payload_json = json_dump(merged_payload)
    reconciliation.leave_payload_json = json_dump(
        {
            "leave_type_code": resolved_type_rule.code,
            "duration_days": leave_request.duration_days,
            "duration_hours": leave_request.duration_hours,
            "attendance_impact": resolved_type_rule.attendance_impact,
            "payroll_impact": resolved_type_rule.payroll_impact,
        }
    )
    reconciliation.notes = notes


def list_reconciliations(db: Session, employer_id: Optional[int] = None) -> list[schemas.AttendanceLeaveReconciliationOut]:
    query = db.query(models.AttendanceLeaveReconciliation)
    if employer_id is not None:
        query = query.filter(models.AttendanceLeaveReconciliation.employer_id == employer_id)
    rows = query.order_by(models.AttendanceLeaveReconciliation.updated_at.desc()).all()
    payloads: list[schemas.AttendanceLeaveReconciliationOut] = []
    for row in rows:
        recalculate_reconciliation(db, row)
        payloads.append(
            schemas.AttendanceLeaveReconciliationOut(
                id=row.id,
                leave_request_id=row.leave_request_id,
                employer_id=row.employer_id,
                worker_id=row.worker_id,
                worker_name=(" ".join(part for part in [row.worker.nom or "", row.worker.prenom or ""] if part).strip() if row.worker else None),
                request_ref=row.leave_request.request_ref if row.leave_request else None,
                leave_type_code=row.leave_request.final_leave_type_code if row.leave_request else None,
                subject=row.leave_request.subject if row.leave_request else None,
                start_date=row.leave_request.start_date if row.leave_request else None,
                end_date=row.leave_request.end_date if row.leave_request else None,
                period=row.period,
                status=row.status,
                discrepancy_level=row.discrepancy_level,
                attendance_payload=json_load(row.attendance_payload_json, {}),
                leave_payload=json_load(row.leave_payload_json, {}),
                notes=row.notes,
                resolved_by_user_id=row.resolved_by_user_id,
                resolved_at=row.resolved_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return payloads
