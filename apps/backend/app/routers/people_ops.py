from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_worker, can_manage_worker, require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.employee_portal_service import json_dump, json_load
from ..services.people_ops_service import build_hr_dashboard


router = APIRouter(prefix="/people-ops", tags=["people-ops"])

READ_ROLES = ("admin", "rh", "employeur", "manager", "direction", "juridique", "audit", "employe")
WRITE_ROLES = ("admin", "rh", "employeur", "manager", "direction", "juridique")


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh", "direction", "juridique", "audit"):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _assert_worker_scope(db: Session, user: models.AppUser, worker: models.Worker) -> None:
    if user_has_any_role(db, user, "admin", "rh", "direction", "juridique", "audit"):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == worker.employer_id:
        return
    if user_has_any_role(db, user, "manager", "employe") and can_access_worker(db, user, worker):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _get_worker_or_404(db: Session, worker_id: int) -> models.Worker:
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _years_of_service(worker: models.Worker, effective_date: Optional[date]) -> int:
    if not worker.date_embauche or not effective_date or effective_date < worker.date_embauche:
        return 0
    days = (effective_date - worker.date_embauche).days
    return max(days // 365, 0)


def _termination_checklist_payload(
    *,
    worker: models.Worker,
    termination_type: str,
    motif: str,
    effective_date: Optional[date],
    notification_sent_at: Optional[datetime],
    notification_received_at: Optional[datetime],
    pre_hearing_notice_sent_at: Optional[datetime],
    pre_hearing_scheduled_at: Optional[datetime],
    economic_consultation_started_at: Optional[date],
    economic_inspection_referral_at: Optional[date],
    technical_layoff_declared_at: Optional[date],
    technical_layoff_end_at: Optional[date],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], str]:
    normalized_type = (termination_type or "").strip().lower()
    motif_text = (motif or "").strip()
    years = _years_of_service(worker, effective_date)
    salary_base = float(worker.salaire_base or 0.0)
    monthly_reference = salary_base
    economic_days = min(years * 10, 180)
    economic_indemnity = round(monthly_reference * (economic_days / 30), 2) if monthly_reference else 0.0

    checklist: list[dict[str, Any]] = [
        {
            "code": "written_notification",
            "label": "Notification ecrite motivee",
            "done": bool(notification_sent_at),
            "required": normalized_type not in {"end_of_fixed_term"},
            "legal_basis": "Code du travail 2024 - notification ecrite de la rupture",
        },
        {
            "code": "acknowledgement_of_receipt",
            "label": "Point de depart du preavis a la reception",
            "done": bool(notification_received_at),
            "required": normalized_type in {"resignation", "mutual_agreement", "disciplinary_dismissal", "economic_dismissal", "termination_after_technical_layoff"},
            "legal_basis": "Le point de depart du preavis court a reception de la lettre",
        },
        {
            "code": "work_certificate",
            "label": "Certificat de travail a preparer",
            "done": False,
            "required": True,
            "legal_basis": "Certificat de travail obligatoire a la cessation du contrat",
        },
    ]

    risk_level = "normal"
    alerts: list[dict[str, Any]] = []

    if normalized_type == "disciplinary_dismissal":
        min_notice_ok = False
        if pre_hearing_notice_sent_at and pre_hearing_scheduled_at:
            min_notice_ok = (pre_hearing_scheduled_at.date() - pre_hearing_notice_sent_at.date()).days >= 3
        checklist.extend(
            [
                {
                    "code": "grievance_notice",
                    "label": "Information ecrite prealable des faits reproches",
                    "done": bool(notification_sent_at),
                    "required": True,
                    "legal_basis": "Information ecrite prealable des faits reproches",
                },
                {
                    "code": "pre_hearing_notice",
                    "label": "Convocation a entretien prealable",
                    "done": bool(pre_hearing_notice_sent_at and pre_hearing_scheduled_at),
                    "required": True,
                    "legal_basis": "Entretien prealable et convocation",
                },
                {
                    "code": "pre_hearing_delay",
                    "label": "Delai minimum de 3 jours ouvrables",
                    "done": min_notice_ok,
                    "required": True,
                    "legal_basis": "3 jours ouvrables minimum avant entretien",
                },
            ]
        )
        if not min_notice_ok:
            risk_level = "high"
            alerts.append(
                {
                    "code": "disciplinary_notice_gap",
                    "severity": "high",
                    "message": "Le delai minimum de 3 jours avant l'entretien prealable n'est pas justifie.",
                }
            )

    if normalized_type == "economic_dismissal":
        checklist.extend(
            [
                {
                    "code": "economic_consultation",
                    "label": "Consultation prealable delegues / comite",
                    "done": bool(economic_consultation_started_at),
                    "required": True,
                    "legal_basis": "Consultation prealable avant licenciement economique",
                },
                {
                    "code": "economic_referral",
                    "label": "Saisine obligatoire de l'inspection",
                    "done": bool(economic_inspection_referral_at),
                    "required": True,
                    "legal_basis": "Saisine obligatoire de l'inspection apres consultation",
                },
            ]
        )
        if not economic_consultation_started_at or not economic_inspection_referral_at:
            risk_level = "high"
            alerts.append(
                {
                    "code": "economic_workflow_gap",
                    "severity": "high",
                    "message": "La procedure economique est incomplete sans consultation prealable et saisine inspection.",
                }
            )

    if normalized_type == "termination_after_technical_layoff":
        checklist.extend(
            [
                {
                    "code": "technical_layoff_declared",
                    "label": "Declaration prealable du chomage technique",
                    "done": bool(technical_layoff_declared_at),
                    "required": True,
                    "legal_basis": "Declaration prealable a l'inspection avec motif, duree et personnel touche",
                },
                {
                    "code": "technical_layoff_duration",
                    "label": "Suivi de la duree du chomage technique",
                    "done": bool(technical_layoff_declared_at and technical_layoff_end_at),
                    "required": True,
                    "legal_basis": "Suivi des seuils de 3 mois et 6 mois",
                },
            ]
        )

    if normalized_type == "resignation" and not motif_text:
        risk_level = "medium"
        alerts.append(
            {
                "code": "resignation_reason_missing",
                "severity": "medium",
                "message": "Le motif de demission doit etre renseigne pour la traçabilite du dossier.",
            }
        )

    preavis_start_date = notification_received_at.date() if notification_received_at else None
    legal_metadata = {
        "termination_type": normalized_type,
        "years_of_service": years,
        "alerts": alerts,
        "preavis_start_date": preavis_start_date.isoformat() if preavis_start_date else None,
        "economic_indemnity_days": economic_days if normalized_type == "economic_dismissal" else 0,
    }
    readonly_stc = {
        "worker_id": worker.id,
        "worker_name": " ".join(part for part in [worker.prenom, worker.nom] if part).strip(),
        "matricule": worker.matricule,
        "base_salary": monthly_reference,
        "years_of_service": years,
        "economic_indemnity_estimate": economic_indemnity if normalized_type == "economic_dismissal" else 0.0,
        "certificate_required": True,
        "notes": [
            "Lecture seule pour controle RH / inspection.",
            "Le detail STC n'altere pas le moteur de paie existant.",
        ],
    }
    return checklist, legal_metadata, readonly_stc, risk_level


def _serialize_job_profile(item: models.WorkforceJobProfile) -> schemas.WorkforceJobProfileOut:
    return schemas.WorkforceJobProfileOut(
        id=item.id,
        employer_id=item.employer_id,
        title=item.title,
        department=item.department,
        category_prof=item.category_prof,
        classification_index=item.classification_index,
        criticality=item.criticality,
        target_headcount=item.target_headcount,
        required_skills=json_load(item.required_skills_json, []),
        mobility_paths=json_load(item.mobility_paths_json, []),
        succession_candidates=json_load(item.succession_candidates_json, []),
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_performance_cycle(item: models.PerformanceCycle) -> schemas.PerformanceCycleOut:
    return schemas.PerformanceCycleOut(
        id=item.id,
        employer_id=item.employer_id,
        name=item.name,
        cycle_type=item.cycle_type,
        start_date=item.start_date,
        end_date=item.end_date,
        status=item.status,
        objectives=json_load(item.objectives_json, []),
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_performance_review(item: models.PerformanceReview) -> schemas.PerformanceReviewOut:
    return schemas.PerformanceReviewOut(
        id=item.id,
        cycle_id=item.cycle_id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        status=item.status,
        overall_score=item.overall_score,
        self_assessment=item.self_assessment,
        manager_comment=item.manager_comment,
        hr_comment=item.hr_comment,
        objectives=json_load(item.objectives_json, []),
        competencies=json_load(item.competencies_json, []),
        development_actions=json_load(item.development_actions_json, []),
        promotion_recommendation=item.promotion_recommendation,
        reviewer_user_id=item.reviewer_user_id,
        manager_user_id=item.manager_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_workforce_plan(item: models.WorkforcePlanning) -> schemas.WorkforcePlanningOut:
    return schemas.WorkforcePlanningOut(
        id=item.id,
        employer_id=item.employer_id,
        planning_year=item.planning_year,
        title=item.title,
        job_profile_id=item.job_profile_id,
        current_headcount=item.current_headcount,
        target_headcount=item.target_headcount,
        recruitment_need=item.recruitment_need,
        mobility_need=item.mobility_need,
        criticality=item.criticality,
        status=item.status,
        assumptions=json_load(item.assumptions_json, []),
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_training_need(item: models.TrainingNeed) -> schemas.TrainingNeedOut:
    return schemas.TrainingNeedOut(
        id=item.id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        review_id=item.review_id,
        job_profile_id=item.job_profile_id,
        source=item.source,
        priority=item.priority,
        title=item.title,
        description=item.description,
        target_skill=item.target_skill,
        gap_level=item.gap_level,
        recommended_training_id=item.recommended_training_id,
        status=item.status,
        due_date=item.due_date,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_training_plan(item: models.TrainingPlan) -> schemas.TrainingPlanOut:
    return schemas.TrainingPlanOut(
        id=item.id,
        employer_id=item.employer_id,
        name=item.name,
        plan_year=item.plan_year,
        budget_amount=item.budget_amount,
        status=item.status,
        objectives=json_load(item.objectives_json, []),
        fmfp_tracking=json_load(item.fmfp_tracking_json, {}),
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_training_plan_item(item: models.TrainingPlanItem) -> schemas.TrainingPlanItemOut:
    return schemas.TrainingPlanItemOut(
        id=item.id,
        training_plan_id=item.training_plan_id,
        need_id=item.need_id,
        training_id=item.training_id,
        training_session_id=item.training_session_id,
        worker_id=item.worker_id,
        status=item.status,
        estimated_cost=item.estimated_cost,
        funding_source=item.funding_source,
        fmfp_eligible=item.fmfp_eligible,
        scheduled_start=item.scheduled_start,
        scheduled_end=item.scheduled_end,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_training_evaluation(item: models.TrainingEvaluation) -> schemas.TrainingEvaluationOut:
    return schemas.TrainingEvaluationOut(
        id=item.id,
        employer_id=item.employer_id,
        training_session_id=item.training_session_id,
        worker_id=item.worker_id,
        evaluation_type=item.evaluation_type,
        score=item.score,
        impact_level=item.impact_level,
        comments=item.comments,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_disciplinary_case(item: models.DisciplinaryCase) -> schemas.DisciplinaryCaseOut:
    return schemas.DisciplinaryCaseOut(
        id=item.id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        inspection_case_id=item.inspection_case_id,
        case_type=item.case_type,
        severity=item.severity,
        status=item.status,
        subject=item.subject,
        description=item.description,
        happened_at=item.happened_at,
        hearing_at=item.hearing_at,
        defense_notes=item.defense_notes,
        sanction_type=item.sanction_type,
        monetary_sanction_flag=item.monetary_sanction_flag,
        documents=json_load(item.documents_json, []),
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_termination(item: models.TerminationWorkflow) -> schemas.TerminationWorkflowOut:
    return schemas.TerminationWorkflowOut(
        id=item.id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        contract_id=item.contract_id,
        inspection_case_id=item.inspection_case_id,
        termination_type=item.termination_type,
        motif=item.motif,
        status=item.status,
        effective_date=item.effective_date,
        notification_sent_at=item.notification_sent_at,
        notification_received_at=item.notification_received_at,
        pre_hearing_notice_sent_at=item.pre_hearing_notice_sent_at,
        pre_hearing_scheduled_at=item.pre_hearing_scheduled_at,
        preavis_start_date=item.preavis_start_date,
        economic_consultation_started_at=item.economic_consultation_started_at,
        economic_inspection_referral_at=item.economic_inspection_referral_at,
        technical_layoff_declared_at=item.technical_layoff_declared_at,
        technical_layoff_end_at=item.technical_layoff_end_at,
        sensitive_case=item.sensitive_case,
        handover_required=item.handover_required,
        inspection_required=item.inspection_required,
        legal_risk_level=item.legal_risk_level,
        checklist=json_load(item.checklist_json, []),
        documents=json_load(item.documents_json, []),
        legal_metadata=json_load(item.legal_metadata_json, {}),
        readonly_stc=json_load(item.readonly_stc_json, {}),
        notes=item.notes,
        created_by_user_id=item.created_by_user_id,
        validated_by_user_id=item.validated_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_duer(item: models.DuerEntry) -> schemas.DuerEntryOut:
    return schemas.DuerEntryOut(
        id=item.id,
        employer_id=item.employer_id,
        site_name=item.site_name,
        risk_family=item.risk_family,
        hazard=item.hazard,
        exposure_population=item.exposure_population,
        probability=item.probability,
        severity=item.severity,
        existing_controls=item.existing_controls,
        residual_risk=item.residual_risk,
        owner_name=item.owner_name,
        status=item.status,
        last_reviewed_at=item.last_reviewed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_prevention_action(item: models.PreventionAction) -> schemas.PreventionActionOut:
    return schemas.PreventionActionOut(
        id=item.id,
        employer_id=item.employer_id,
        duer_entry_id=item.duer_entry_id,
        action_title=item.action_title,
        action_type=item.action_type,
        owner_name=item.owner_name,
        due_date=item.due_date,
        status=item.status,
        measure_details=item.measure_details,
        inspection_follow_up=item.inspection_follow_up,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/dashboard", response_model=schemas.HrDashboardOut)
def get_people_dashboard(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    return build_hr_dashboard(db, employer_id)


@router.get("/job-profiles", response_model=list[schemas.WorkforceJobProfileOut])
def list_job_profiles(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = (
        db.query(models.WorkforceJobProfile)
        .filter(models.WorkforceJobProfile.employer_id == employer_id)
        .order_by(models.WorkforceJobProfile.title.asc())
        .all()
    )
    return [_serialize_job_profile(item) for item in items]


@router.post("/job-profiles", response_model=schemas.WorkforceJobProfileOut)
def create_job_profile(
    payload: schemas.WorkforceJobProfileCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.WorkforceJobProfile(
        employer_id=payload.employer_id,
        title=payload.title,
        department=payload.department,
        category_prof=payload.category_prof,
        classification_index=payload.classification_index,
        criticality=payload.criticality,
        target_headcount=payload.target_headcount,
        required_skills_json=json_dump(payload.required_skills),
        mobility_paths_json=json_dump(payload.mobility_paths),
        succession_candidates_json=json_dump(payload.succession_candidates),
        notes=payload.notes,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="people_ops.job_profile.create",
        entity_type="workforce_job_profile",
        entity_id=item.id,
        route="/people-ops/job-profiles",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_job_profile(item)


@router.put("/job-profiles/{job_profile_id}", response_model=schemas.WorkforceJobProfileOut)
def update_job_profile(
    job_profile_id: int,
    payload: schemas.WorkforceJobProfileUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.WorkforceJobProfile).filter(models.WorkforceJobProfile.id == job_profile_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job profile not found")
    _assert_employer_scope(db, user, item.employer_id)
    before = _serialize_job_profile(item)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "required_skills":
            item.required_skills_json = json_dump(value)
        elif field == "mobility_paths":
            item.mobility_paths_json = json_dump(value)
        elif field == "succession_candidates":
            item.succession_candidates_json = json_dump(value)
        else:
            setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="people_ops.job_profile.update",
        entity_type="workforce_job_profile",
        entity_id=item.id,
        route=f"/people-ops/job-profiles/{job_profile_id}",
        employer_id=item.employer_id,
        before=before.model_dump(),
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_job_profile(item)


@router.get("/performance-cycles", response_model=list[schemas.PerformanceCycleOut])
def list_performance_cycles(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = (
        db.query(models.PerformanceCycle)
        .filter(models.PerformanceCycle.employer_id == employer_id)
        .order_by(models.PerformanceCycle.start_date.desc())
        .all()
    )
    return [_serialize_performance_cycle(item) for item in items]


@router.post("/performance-cycles", response_model=schemas.PerformanceCycleOut)
def create_performance_cycle(
    payload: schemas.PerformanceCycleCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.PerformanceCycle(
        employer_id=payload.employer_id,
        name=payload.name,
        cycle_type=payload.cycle_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        objectives_json=json_dump(payload.objectives),
        created_by_user_id=user.id,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="people_ops.performance_cycle.create",
        entity_type="performance_cycle",
        entity_id=item.id,
        route="/people-ops/performance-cycles",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_performance_cycle(item)


@router.get("/performance-reviews", response_model=list[schemas.PerformanceReviewOut])
def list_performance_reviews(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    cycle_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.PerformanceReview)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.PerformanceReview.worker_id == worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.PerformanceReview.employer_id == employer_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.PerformanceReview.worker_id == user.worker_id)
    if cycle_id:
        query = query.filter(models.PerformanceReview.cycle_id == cycle_id)
    items = query.order_by(models.PerformanceReview.updated_at.desc()).all()
    return [_serialize_performance_review(item) for item in items]


@router.post("/performance-reviews", response_model=schemas.PerformanceReviewOut)
def create_performance_review(
    payload: schemas.PerformanceReviewCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    worker = _get_worker_or_404(db, payload.worker_id)
    if not can_manage_worker(db, user, worker=worker) and not user_has_any_role(db, user, "admin", "rh", "direction", "juridique"):
        raise HTTPException(status_code=403, detail="Forbidden")
    item = models.PerformanceReview(
        cycle_id=payload.cycle_id,
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
        reviewer_user_id=payload.reviewer_user_id or user.id,
        manager_user_id=payload.manager_user_id,
        status=payload.status,
        overall_score=payload.overall_score,
        self_assessment=payload.self_assessment,
        manager_comment=payload.manager_comment,
        hr_comment=payload.hr_comment,
        objectives_json=json_dump(payload.objectives),
        competencies_json=json_dump(payload.competencies),
        development_actions_json=json_dump(payload.development_actions),
        promotion_recommendation=payload.promotion_recommendation,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="people_ops.performance_review.create",
        entity_type="performance_review",
        entity_id=item.id,
        route="/people-ops/performance-reviews",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_performance_review(item)


@router.patch("/performance-reviews/{review_id}/status", response_model=schemas.PerformanceReviewOut)
def update_performance_review_status(
    review_id: int,
    payload: schemas.PerformanceReviewStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.PerformanceReview).filter(models.PerformanceReview.id == review_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Performance review not found")
    _assert_employer_scope(db, user, item.employer_id)
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return _serialize_performance_review(item)


@router.get("/workforce-plans", response_model=list[schemas.WorkforcePlanningOut])
def list_workforce_plans(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = (
        db.query(models.WorkforcePlanning)
        .filter(models.WorkforcePlanning.employer_id == employer_id)
        .order_by(models.WorkforcePlanning.planning_year.desc(), models.WorkforcePlanning.title.asc())
        .all()
    )
    return [_serialize_workforce_plan(item) for item in items]


@router.post("/workforce-plans", response_model=schemas.WorkforcePlanningOut)
def create_workforce_plan(
    payload: schemas.WorkforcePlanningCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.WorkforcePlanning(
        employer_id=payload.employer_id,
        planning_year=payload.planning_year,
        title=payload.title,
        job_profile_id=payload.job_profile_id,
        current_headcount=payload.current_headcount,
        target_headcount=payload.target_headcount,
        recruitment_need=payload.recruitment_need,
        mobility_need=payload.mobility_need,
        criticality=payload.criticality,
        status=payload.status,
        assumptions_json=json_dump(payload.assumptions),
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_workforce_plan(item)


@router.get("/training-needs", response_model=list[schemas.TrainingNeedOut])
def list_training_needs(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TrainingNeed)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.TrainingNeed.worker_id == worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.TrainingNeed.employer_id == employer_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.TrainingNeed.worker_id == user.worker_id)
    items = query.order_by(models.TrainingNeed.updated_at.desc()).all()
    return [_serialize_training_need(item) for item in items]


@router.post("/training-needs", response_model=schemas.TrainingNeedOut)
def create_training_need(
    payload: schemas.TrainingNeedCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    if payload.worker_id:
        worker = _get_worker_or_404(db, payload.worker_id)
        _assert_worker_scope(db, user, worker)
    item = models.TrainingNeed(
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
        review_id=payload.review_id,
        job_profile_id=payload.job_profile_id,
        source=payload.source,
        priority=payload.priority,
        title=payload.title,
        description=payload.description,
        target_skill=payload.target_skill,
        gap_level=payload.gap_level,
        recommended_training_id=payload.recommended_training_id,
        status=payload.status,
        due_date=payload.due_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_training_need(item)


@router.patch("/training-needs/{need_id}/status", response_model=schemas.TrainingNeedOut)
def update_training_need_status(
    need_id: int,
    payload: schemas.TrainingNeedStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TrainingNeed).filter(models.TrainingNeed.id == need_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Training need not found")
    _assert_employer_scope(db, user, item.employer_id)
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return _serialize_training_need(item)


@router.get("/training-plans", response_model=list[schemas.TrainingPlanOut])
def list_training_plans(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = (
        db.query(models.TrainingPlan)
        .filter(models.TrainingPlan.employer_id == employer_id)
        .order_by(models.TrainingPlan.plan_year.desc(), models.TrainingPlan.name.asc())
        .all()
    )
    return [_serialize_training_plan(item) for item in items]


@router.post("/training-plans", response_model=schemas.TrainingPlanOut)
def create_training_plan(
    payload: schemas.TrainingPlanCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.TrainingPlan(
        employer_id=payload.employer_id,
        name=payload.name,
        plan_year=payload.plan_year,
        budget_amount=payload.budget_amount,
        status=payload.status,
        objectives_json=json_dump(payload.objectives),
        fmfp_tracking_json=json_dump(payload.fmfp_tracking),
        created_by_user_id=user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_training_plan(item)


@router.get("/training-plan-items", response_model=list[schemas.TrainingPlanItemOut])
def list_training_plan_items(
    training_plan_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TrainingPlanItem)
    if training_plan_id:
        item = db.query(models.TrainingPlan).filter(models.TrainingPlan.id == training_plan_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Training plan not found")
        _assert_employer_scope(db, user, item.employer_id)
        query = query.filter(models.TrainingPlanItem.training_plan_id == training_plan_id)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.TrainingPlanItem.worker_id == worker_id)
    items = query.order_by(models.TrainingPlanItem.updated_at.desc()).all()
    return [_serialize_training_plan_item(item) for item in items]


@router.post("/training-plan-items", response_model=schemas.TrainingPlanItemOut)
def create_training_plan_item(
    payload: schemas.TrainingPlanItemCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    plan = db.query(models.TrainingPlan).filter(models.TrainingPlan.id == payload.training_plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    _assert_employer_scope(db, user, plan.employer_id)
    if payload.worker_id:
        worker = _get_worker_or_404(db, payload.worker_id)
        _assert_worker_scope(db, user, worker)
    item = models.TrainingPlanItem(
        training_plan_id=payload.training_plan_id,
        need_id=payload.need_id,
        training_id=payload.training_id,
        training_session_id=payload.training_session_id,
        worker_id=payload.worker_id,
        status=payload.status,
        estimated_cost=payload.estimated_cost,
        funding_source=payload.funding_source,
        fmfp_eligible=payload.fmfp_eligible,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_training_plan_item(item)


@router.get("/training-evaluations", response_model=list[schemas.TrainingEvaluationOut])
def list_training_evaluations(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TrainingEvaluation)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.TrainingEvaluation.worker_id == worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.TrainingEvaluation.employer_id == employer_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.TrainingEvaluation.worker_id == user.worker_id)
    items = query.order_by(models.TrainingEvaluation.updated_at.desc()).all()
    return [_serialize_training_evaluation(item) for item in items]


@router.post("/training-evaluations", response_model=schemas.TrainingEvaluationOut)
def create_training_evaluation(
    payload: schemas.TrainingEvaluationCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    worker = _get_worker_or_404(db, payload.worker_id)
    _assert_worker_scope(db, user, worker)
    item = models.TrainingEvaluation(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_training_evaluation(item)


@router.get("/disciplinary-cases", response_model=list[schemas.DisciplinaryCaseOut])
def list_disciplinary_cases(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.DisciplinaryCase)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.DisciplinaryCase.worker_id == worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.DisciplinaryCase.employer_id == employer_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.DisciplinaryCase.worker_id == user.worker_id)
    items = query.order_by(models.DisciplinaryCase.updated_at.desc()).all()
    return [_serialize_disciplinary_case(item) for item in items]


@router.post("/disciplinary-cases", response_model=schemas.DisciplinaryCaseOut)
def create_disciplinary_case(
    payload: schemas.DisciplinaryCaseCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    worker = _get_worker_or_404(db, payload.worker_id)
    if payload.monetary_sanction_flag:
        raise HTTPException(status_code=400, detail="Monetary sanctions are forbidden")
    if not can_manage_worker(db, user, worker=worker) and not user_has_any_role(db, user, "admin", "rh", "direction", "juridique"):
        raise HTTPException(status_code=403, detail="Forbidden")
    item = models.DisciplinaryCase(
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
        inspection_case_id=payload.inspection_case_id,
        created_by_user_id=user.id,
        case_type=payload.case_type,
        severity=payload.severity,
        status=payload.status,
        subject=payload.subject,
        description=payload.description,
        happened_at=payload.happened_at,
        hearing_at=payload.hearing_at,
        defense_notes=payload.defense_notes,
        sanction_type=payload.sanction_type,
        monetary_sanction_flag=False,
        documents_json=json_dump(payload.documents),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_disciplinary_case(item)


@router.patch("/disciplinary-cases/{case_id}/status", response_model=schemas.DisciplinaryCaseOut)
def update_disciplinary_case_status(
    case_id: int,
    payload: schemas.DisciplinaryCaseStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.DisciplinaryCase).filter(models.DisciplinaryCase.id == case_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Disciplinary case not found")
    _assert_employer_scope(db, user, item.employer_id)
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return _serialize_disciplinary_case(item)


@router.get("/termination-workflows", response_model=list[schemas.TerminationWorkflowOut])
def list_termination_workflows(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TerminationWorkflow)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.TerminationWorkflow.worker_id == worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.TerminationWorkflow.employer_id == employer_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.TerminationWorkflow.worker_id == user.worker_id)
    items = query.order_by(models.TerminationWorkflow.updated_at.desc()).all()
    return [_serialize_termination(item) for item in items]


@router.post("/termination-workflows", response_model=schemas.TerminationWorkflowOut)
def create_termination_workflow(
    payload: schemas.TerminationWorkflowCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    worker = _get_worker_or_404(db, payload.worker_id)
    if not can_manage_worker(db, user, worker=worker) and not user_has_any_role(db, user, "admin", "rh", "direction", "juridique"):
        raise HTTPException(status_code=403, detail="Forbidden")
    checklist, legal_metadata, readonly_stc, risk_level = _termination_checklist_payload(
        worker=worker,
        termination_type=payload.termination_type,
        motif=payload.motif,
        effective_date=payload.effective_date,
        notification_sent_at=payload.notification_sent_at,
        notification_received_at=payload.notification_received_at,
        pre_hearing_notice_sent_at=payload.pre_hearing_notice_sent_at,
        pre_hearing_scheduled_at=payload.pre_hearing_scheduled_at,
        economic_consultation_started_at=payload.economic_consultation_started_at,
        economic_inspection_referral_at=payload.economic_inspection_referral_at,
        technical_layoff_declared_at=payload.technical_layoff_declared_at,
        technical_layoff_end_at=payload.technical_layoff_end_at,
    )
    item = models.TerminationWorkflow(
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
        contract_id=payload.contract_id,
        inspection_case_id=payload.inspection_case_id,
        created_by_user_id=user.id,
        termination_type=payload.termination_type,
        motif=payload.motif,
        status=payload.status,
        effective_date=payload.effective_date,
        notification_sent_at=payload.notification_sent_at,
        notification_received_at=payload.notification_received_at,
        pre_hearing_notice_sent_at=payload.pre_hearing_notice_sent_at,
        pre_hearing_scheduled_at=payload.pre_hearing_scheduled_at,
        preavis_start_date=payload.notification_received_at.date() if payload.notification_received_at else payload.preavis_start_date,
        economic_consultation_started_at=payload.economic_consultation_started_at,
        economic_inspection_referral_at=payload.economic_inspection_referral_at,
        technical_layoff_declared_at=payload.technical_layoff_declared_at,
        technical_layoff_end_at=payload.technical_layoff_end_at,
        sensitive_case=payload.sensitive_case,
        handover_required=payload.handover_required,
        inspection_required=payload.inspection_required,
        legal_risk_level=risk_level,
        checklist_json=json_dump(payload.checklist or checklist),
        documents_json=json_dump(payload.documents),
        legal_metadata_json=json_dump(legal_metadata),
        readonly_stc_json=json_dump(readonly_stc),
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_termination(item)


@router.patch("/termination-workflows/{workflow_id}/status", response_model=schemas.TerminationWorkflowOut)
def update_termination_workflow_status(
    workflow_id: int,
    payload: schemas.TerminationWorkflowStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.id == workflow_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Termination workflow not found")
    _assert_employer_scope(db, user, item.employer_id)
    worker = _get_worker_or_404(db, item.worker_id)
    item.status = payload.status
    if payload.status in {"validated", "approved"}:
        item.validated_by_user_id = user.id
    checklist, legal_metadata, readonly_stc, risk_level = _termination_checklist_payload(
        worker=worker,
        termination_type=item.termination_type,
        motif=item.motif,
        effective_date=item.effective_date,
        notification_sent_at=item.notification_sent_at,
        notification_received_at=item.notification_received_at,
        pre_hearing_notice_sent_at=item.pre_hearing_notice_sent_at,
        pre_hearing_scheduled_at=item.pre_hearing_scheduled_at,
        economic_consultation_started_at=item.economic_consultation_started_at,
        economic_inspection_referral_at=item.economic_inspection_referral_at,
        technical_layoff_declared_at=item.technical_layoff_declared_at,
        technical_layoff_end_at=item.technical_layoff_end_at,
    )
    item.preavis_start_date = item.notification_received_at.date() if item.notification_received_at else item.preavis_start_date
    item.legal_risk_level = risk_level
    item.checklist_json = json_dump(checklist)
    item.legal_metadata_json = json_dump(legal_metadata)
    item.readonly_stc_json = json_dump(readonly_stc)
    db.commit()
    db.refresh(item)
    return _serialize_termination(item)


@router.get("/duer", response_model=list[schemas.DuerEntryOut])
def list_duer_entries(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = (
        db.query(models.DuerEntry)
        .filter(models.DuerEntry.employer_id == employer_id)
        .order_by(models.DuerEntry.updated_at.desc())
        .all()
    )
    return [_serialize_duer(item) for item in items]


@router.post("/duer", response_model=schemas.DuerEntryOut)
def create_duer_entry(
    payload: schemas.DuerEntryCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    residual = payload.residual_risk if payload.residual_risk is not None else payload.probability * payload.severity
    item = models.DuerEntry(
        employer_id=payload.employer_id,
        site_name=payload.site_name,
        risk_family=payload.risk_family,
        hazard=payload.hazard,
        exposure_population=payload.exposure_population,
        probability=payload.probability,
        severity=payload.severity,
        existing_controls=payload.existing_controls,
        residual_risk=residual,
        owner_name=payload.owner_name,
        status=payload.status,
        last_reviewed_at=payload.last_reviewed_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_duer(item)


@router.get("/prevention-actions", response_model=list[schemas.PreventionActionOut])
def list_prevention_actions(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = (
        db.query(models.PreventionAction)
        .filter(models.PreventionAction.employer_id == employer_id)
        .order_by(models.PreventionAction.updated_at.desc())
        .all()
    )
    return [_serialize_prevention_action(item) for item in items]


@router.post("/prevention-actions", response_model=schemas.PreventionActionOut)
def create_prevention_action(
    payload: schemas.PreventionActionCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.PreventionAction(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_prevention_action(item)


@router.patch("/prevention-actions/{action_id}/status", response_model=schemas.PreventionActionOut)
def update_prevention_action_status(
    action_id: int,
    payload: schemas.PreventionActionStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.PreventionAction).filter(models.PreventionAction.id == action_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Prevention action not found")
    _assert_employer_scope(db, user, item.employer_id)
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return _serialize_prevention_action(item)
