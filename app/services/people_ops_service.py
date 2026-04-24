from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from .. import models
from .employee_portal_service import json_load
from .legal_operations_service import build_legal_modules_status


def build_hr_dashboard(db: Session, employer_id: int) -> dict[str, Any]:
    workers = db.query(models.Worker).filter(models.Worker.employer_id == employer_id).all()
    active_workers = [worker for worker in workers if not worker.date_debauche]
    open_requests = (
        db.query(models.EmployeePortalRequest)
        .filter(
            models.EmployeePortalRequest.employer_id == employer_id,
            models.EmployeePortalRequest.status.notin_(["closed", "resolved"]),
        )
        .count()
    )
    open_cases = (
        db.query(models.InspectorCase)
        .filter(
            models.InspectorCase.employer_id == employer_id,
            models.InspectorCase.status.notin_(["closed", "archived"]),
        )
        .count()
    )
    open_reviews = (
        db.query(models.PerformanceReview)
        .filter(
            models.PerformanceReview.employer_id == employer_id,
            models.PerformanceReview.status.notin_(["completed", "archived"]),
        )
        .count()
    )
    training_needs = (
        db.query(models.TrainingNeed)
        .filter(
            models.TrainingNeed.employer_id == employer_id,
            models.TrainingNeed.status.notin_(["completed", "cancelled"]),
        )
        .all()
    )
    plans = db.query(models.TrainingPlan).filter(models.TrainingPlan.employer_id == employer_id).all()
    disciplinary_open = (
        db.query(models.DisciplinaryCase)
        .filter(
            models.DisciplinaryCase.employer_id == employer_id,
            models.DisciplinaryCase.status.notin_(["closed", "cancelled"]),
        )
        .count()
    )
    terminations_open = (
        db.query(models.TerminationWorkflow)
        .filter(
            models.TerminationWorkflow.employer_id == employer_id,
            models.TerminationWorkflow.status.notin_(["closed", "cancelled"]),
        )
        .count()
    )
    incidents_open = (
        db.query(models.SstIncident)
        .filter(
            models.SstIncident.employer_id == employer_id,
            models.SstIncident.status.notin_(["closed", "resolved"]),
        )
        .count()
    )
    duer_open = (
        db.query(models.DuerEntry)
        .filter(models.DuerEntry.employer_id == employer_id, models.DuerEntry.status != "closed")
        .count()
    )
    prevention_actions = (
        db.query(models.PreventionAction)
        .filter(
            models.PreventionAction.employer_id == employer_id,
            models.PreventionAction.status.notin_(["done", "cancelled"]),
        )
        .all()
    )
    avg_score = (
        db.query(models.PerformanceReview)
        .filter(models.PerformanceReview.employer_id == employer_id, models.PerformanceReview.overall_score.isnot(None))
        .all()
    )

    alerts: list[dict[str, Any]] = []
    missing_identity = [worker for worker in active_workers if not worker.cin or not worker.date_naissance or not worker.adresse]
    if missing_identity:
        alerts.append(
            {
                "severity": "high",
                "code": "worker_identity_incomplete",
                "message": f"{len(missing_identity)} dossier(s) salarie incomplet(s) pour la conformite contractuelle malgache.",
            }
        )
    if open_cases:
        alerts.append(
            {
                "severity": "high",
                "code": "inspection_cases_open",
                "message": f"{open_cases} dossier(s) inspection ouverts ou en attente.",
            }
        )
    overdue_training = [need for need in training_needs if need.due_date and need.due_date < date.today()]
    if overdue_training:
        alerts.append(
            {
                "severity": "medium",
                "code": "training_needs_overdue",
                "message": f"{len(overdue_training)} besoin(s) de formation sont echus.",
            }
        )
    overdue_prevention = [action for action in prevention_actions if action.due_date and action.due_date < date.today()]
    if overdue_prevention:
        alerts.append(
            {
                "severity": "medium",
                "code": "prevention_actions_overdue",
                "message": f"{len(overdue_prevention)} action(s) DUER/PAP sont en retard.",
            }
        )
    critical_profiles = (
        db.query(models.WorkforceJobProfile)
        .filter(models.WorkforceJobProfile.employer_id == employer_id, models.WorkforceJobProfile.criticality == "critical")
        .all()
    )
    critical_without_successor = [
        profile for profile in critical_profiles if not json_load(profile.succession_candidates_json, [])
    ]
    if critical_without_successor:
        alerts.append(
            {
                "severity": "medium",
                "code": "critical_roles_without_successor",
                "message": f"{len(critical_without_successor)} poste(s) critique(s) sans succession preparee.",
            }
        )

    return {
        "workforce": {
            "workers_total": len(workers),
            "workers_active": len(active_workers),
            "portal_requests_open": open_requests,
            "inspection_cases_open": open_cases,
            "job_profiles": db.query(models.WorkforceJobProfile).filter(models.WorkforceJobProfile.employer_id == employer_id).count(),
        },
        "performance": {
            "cycles": db.query(models.PerformanceCycle).filter(models.PerformanceCycle.employer_id == employer_id).count(),
            "reviews_open": open_reviews,
            "average_score": round(sum(item.overall_score for item in avg_score if item.overall_score is not None) / len(avg_score), 2) if avg_score else None,
        },
        "training": {
            "needs_open": len(training_needs),
            "plans": len(plans),
            "plan_items": db.query(models.TrainingPlanItem)
            .join(models.TrainingPlan, models.TrainingPlanItem.training_plan_id == models.TrainingPlan.id)
            .filter(models.TrainingPlan.employer_id == employer_id)
            .count(),
            "evaluations": db.query(models.TrainingEvaluation).filter(models.TrainingEvaluation.employer_id == employer_id).count(),
        },
        "discipline": {
            "disciplinary_open": disciplinary_open,
            "terminations_open": terminations_open,
        },
        "safety": {
            "incidents_open": incidents_open,
            "duer_open": duer_open,
            "prevention_actions_open": len(prevention_actions),
        },
        "legal_status": build_legal_modules_status(db, [employer_id]),
        "alerts": alerts,
    }
