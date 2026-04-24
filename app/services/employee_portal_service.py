import json
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from ..security import user_has_any_role
from .compliance_service import build_employee_flow


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


def next_sequence(db: Session, *, model, field_name: str, prefix: str) -> str:
    existing = db.query(getattr(model, field_name)).filter(getattr(model, field_name).like(f"{prefix}-%")).all()
    max_seq = 0
    for (value,) in existing:
        if not value:
            continue
        try:
            max_seq = max(max_seq, int(str(value).split("-")[-1]))
        except ValueError:
            continue
    return f"{prefix}-{max_seq + 1:05d}"


def next_request_number(db: Session, employer_id: int) -> str:
    today = date.today().strftime("%Y%m")
    return next_sequence(
        db,
        model=models.EmployeePortalRequest,
        field_name="case_number",
        prefix=f"REQ-{employer_id:03d}-{today}",
    )


def next_inspector_case_number(db: Session, employer_id: int) -> str:
    today = date.today().strftime("%Y%m")
    return next_sequence(
        db,
        model=models.InspectorCase,
        field_name="case_number",
        prefix=f"INS-{employer_id:03d}-{today}",
    )


def pick_auto_assigned_inspector(db: Session, employer_id: int) -> Optional[models.AppUser]:
    assignment_rows = (
        db.query(models.LabourInspectorAssignment)
        .filter(
            models.LabourInspectorAssignment.employer_id == employer_id,
            models.LabourInspectorAssignment.status == "active",
        )
        .order_by(models.LabourInspectorAssignment.created_at.asc())
        .all()
    )
    candidate_ids = [row.inspector_user_id for row in assignment_rows if row.inspector_user_id is not None]
    if not candidate_ids:
        fallback_users = (
            db.query(models.AppUser)
            .filter(
                models.AppUser.is_active.is_(True),
                (models.AppUser.employer_id == employer_id) | (models.AppUser.employer_id.is_(None)),
            )
            .order_by(models.AppUser.full_name.asc().nullslast(), models.AppUser.username.asc())
            .all()
        )
        candidate_ids = [user.id for user in fallback_users if user_has_any_role(db, user, "inspecteur")]

    if not candidate_ids:
        return None

    candidates = (
        db.query(models.AppUser)
        .filter(
            models.AppUser.id.in_(candidate_ids),
            models.AppUser.is_active.is_(True),
        )
        .all()
    )
    scored: list[tuple[int, datetime, models.AppUser]] = []
    for user in candidates:
        if not user_has_any_role(db, user, "inspecteur"):
            continue
        open_case_count = (
            db.query(models.InspectorCase)
            .filter(
                models.InspectorCase.assigned_inspector_user_id == user.id,
                models.InspectorCase.status.notin_(["closed", "archived"]),
            )
            .count()
        )
        latest_assignment = (
            db.query(models.InspectorCaseAssignment.assigned_at)
            .filter(
                models.InspectorCaseAssignment.inspector_user_id == user.id,
                models.InspectorCaseAssignment.status == "active",
            )
            .order_by(models.InspectorCaseAssignment.assigned_at.desc())
            .first()
        )
        last_assigned_at = latest_assignment[0] if latest_assignment and latest_assignment[0] else datetime(1970, 1, 1, tzinfo=timezone.utc)
        scored.append((open_case_count, last_assigned_at, user))

    if not scored:
        return None

    scored.sort(key=lambda item: (item[0], item[1], (item[2].full_name or item[2].username or "").lower()))
    return scored[0][2]


def append_history(history_json: Any, *, actor: Optional[models.AppUser], status: str, note: Optional[str]) -> str:
    history = json_load(history_json, [])
    history.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "actor_user_id": actor.id if actor else None,
            "actor_role": actor.role_code if actor else None,
            "status": status,
            "note": note,
        }
    )
    return json_dump(history)


def build_portal_dashboard(db: Session, worker: models.Worker) -> dict[str, Any]:
    requests = (
        db.query(models.EmployeePortalRequest)
        .filter(models.EmployeePortalRequest.worker_id == worker.id)
        .order_by(models.EmployeePortalRequest.updated_at.desc())
        .limit(10)
        .all()
    )
    inspector_cases = (
        db.query(models.InspectorCase)
        .filter(models.InspectorCase.worker_id == worker.id)
        .order_by(models.InspectorCase.updated_at.desc())
        .limit(10)
        .all()
    )
    contracts = (
        db.query(models.CustomContract)
        .filter(models.CustomContract.worker_id == worker.id)
        .order_by(models.CustomContract.updated_at.desc())
        .limit(10)
        .all()
    )
    reviews = (
        db.query(models.PerformanceReview)
        .filter(models.PerformanceReview.worker_id == worker.id)
        .order_by(models.PerformanceReview.updated_at.desc())
        .limit(10)
        .all()
    )
    plan_items = (
        db.query(models.TrainingPlanItem)
        .filter(models.TrainingPlanItem.worker_id == worker.id)
        .order_by(models.TrainingPlanItem.updated_at.desc())
        .limit(10)
        .all()
    )

    notifications: list[dict[str, Any]] = []
    for item in inspector_cases:
        if item.status not in {"closed", "archived"}:
            notifications.append(
                {
                    "type": "inspection_case",
                    "label": item.subject,
                    "status": item.status,
                    "case_number": item.case_number,
                }
            )
    for item in requests:
        if item.status not in {"closed", "resolved"}:
            notifications.append(
                {
                    "type": "portal_request",
                    "label": item.title,
                    "status": item.status,
                    "case_number": item.case_number,
                }
            )

    return {
        "worker": build_employee_flow(db, worker)["worker"],
        "requests": requests,
        "inspector_cases": inspector_cases,
        "contracts": [
            {
                "id": contract.id,
                "title": contract.title,
                "template_type": contract.template_type,
                "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
            }
            for contract in contracts
        ],
        "performance_reviews": [
            {
                "id": review.id,
                "cycle_id": review.cycle_id,
                "status": review.status,
                "overall_score": review.overall_score,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None,
            }
            for review in reviews
        ],
        "training_plan_items": [
            {
                "id": item.id,
                "training_plan_id": item.training_plan_id,
                "status": item.status,
                "scheduled_start": item.scheduled_start.isoformat() if item.scheduled_start else None,
                "scheduled_end": item.scheduled_end.isoformat() if item.scheduled_end else None,
            }
            for item in plan_items
        ],
        "notifications": notifications[:10],
    }


