from typing import Optional

from sqlalchemy.orm import Session

from .. import models


DEFAULT_MANAGER_STATUS = "pending"
DEFAULT_RH_STATUS = "pending"
DEFAULT_OVERALL_STATUS = "pending_manager"


def get_or_create_workflow(db: Session, request_type: str, request_id: int) -> models.RequestWorkflow:
    workflow = db.query(models.RequestWorkflow).filter(
        models.RequestWorkflow.request_type == request_type,
        models.RequestWorkflow.request_id == request_id,
    ).first()
    if workflow:
        return workflow

    workflow = models.RequestWorkflow(
        request_type=request_type,
        request_id=request_id,
        overall_status=DEFAULT_OVERALL_STATUS,
        manager_status=DEFAULT_MANAGER_STATUS,
        rh_status=DEFAULT_RH_STATUS,
    )
    db.add(workflow)
    db.flush()
    return workflow


def review_as_manager(
    workflow: models.RequestWorkflow,
    *,
    actor: Optional[models.AppUser],
    approved: bool,
    comment: Optional[str],
):
    workflow.manager_status = "approved" if approved else "rejected"
    workflow.manager_comment = comment
    workflow.manager_actor_user_id = actor.id if actor else None
    workflow.overall_status = "pending_rh" if approved else "rejected"
    if not approved:
        workflow.rh_status = "pending"


def review_as_rh(
    workflow: models.RequestWorkflow,
    *,
    actor: Optional[models.AppUser],
    approved: bool,
    comment: Optional[str],
):
    workflow.rh_status = "approved" if approved else "rejected"
    workflow.rh_comment = comment
    workflow.rh_actor_user_id = actor.id if actor else None
    workflow.overall_status = "approved" if approved else "rejected"
