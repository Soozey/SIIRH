from datetime import datetime, timezone

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_employer, get_inspector_assigned_employer_ids, require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.compliance_service import (
    build_contract_checklist,
    build_contract_queue,
    build_employee_flow,
    collect_integrity_issues,
    create_contract_version,
    json_dump,
    json_load,
    sync_employer_register,
)
from ..services.employee_portal_service import next_sequence
from ..services.file_storage import sanitize_filename_part, save_upload_file
from ..services.legal_operations_service import build_legal_modules_status
from ..services.master_data_service import sync_worker_master_data


router = APIRouter(prefix="/compliance", tags=["compliance"])

READ_ROLES = ("admin", "rh", "employeur", "manager", "juridique", "direction", "audit", "inspecteur")
WRITE_ROLES = ("admin", "rh", "employeur", "juridique", "direction")
INSPECTOR_ROLES = ("admin", "rh", "juridique", "direction", "inspecteur")


def _assert_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        return
    if user_has_any_role(db, user, "inspecteur") and can_access_employer(db, user, employer_id):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        if user.employer_id == employer_id:
            return
    if user_has_any_role(db, user, "manager") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _serialize_contract_version(item: models.ContractVersion) -> schemas.ContractVersionOut:
    return schemas.ContractVersionOut.model_validate(item)


def _serialize_review(item: models.ComplianceReview) -> schemas.ComplianceReviewOut:
    return schemas.ComplianceReviewOut(
        id=item.id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        contract_id=item.contract_id,
        contract_version_id=item.contract_version_id,
        review_type=item.review_type,
        review_stage=item.review_stage,
        status=item.status,
        source_module=item.source_module,
        checklist=json_load(item.checklist_json, []),
        observations=json_load(item.observations_json, []),
        requested_documents=json_load(item.requested_documents_json, []),
        tags=json_load(item.tags_json, []),
        due_at=item.due_at,
        submitted_to_inspector_at=item.submitted_to_inspector_at,
        reviewed_by_user_id=item.reviewed_by_user_id,
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_observation(item: models.InspectorObservation) -> schemas.InspectorObservationOut:
    return schemas.InspectorObservationOut(
        id=item.id,
        review_id=item.review_id,
        employer_id=item.employer_id,
        author_user_id=item.author_user_id,
        visibility=item.visibility,
        observation_type=item.observation_type,
        status_marker=item.status_marker,
        message=item.message,
        structured_payload=json_load(item.structured_payload_json, {}),
        created_at=item.created_at,
    )


def _serialize_visit(item: models.ComplianceVisit) -> schemas.ComplianceVisitOut:
    return schemas.ComplianceVisitOut(
        id=item.id,
        employer_id=item.employer_id,
        review_id=item.review_id,
        visit_type=item.visit_type,
        status=item.status,
        inspector_name=item.inspector_name,
        scheduled_at=item.scheduled_at,
        occurred_at=item.occurred_at,
        notes=item.notes,
        attachments=json_load(item.attachments_json, []),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _visible_employer_ids(db: Session, user: models.AppUser) -> list[int]:
    if user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        return [item.id for item in db.query(models.Employer.id).order_by(models.Employer.raison_sociale.asc()).all()]
    if user_has_any_role(db, user, "inspecteur"):
        return sorted(get_inspector_assigned_employer_ids(db, user))
    if user.employer_id:
        return [user.employer_id]
    return []


def _serialize_labour_assignment(item: models.LabourInspectorAssignment) -> schemas.LabourInspectorAssignmentOut:
    return schemas.LabourInspectorAssignmentOut(
        id=item.id,
        employer_id=item.employer_id,
        inspector_user_id=item.inspector_user_id,
        assigned_by_user_id=item.assigned_by_user_id,
        assignment_scope=item.assignment_scope,
        circonscription=item.circonscription,
        sector_filter=item.sector_filter,
        status=item.status,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
        inspector=schemas.AppUserLightOut.model_validate(item.inspector) if item.inspector else None,
    )


def _next_labour_message_reference(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m")
    return next_sequence(
        db,
        model=models.LabourFormalMessage,
        field_name="reference_number",
        prefix=f"LMSG-{today}",
    )


def _serialize_labour_recipient(item: models.LabourFormalMessageRecipient) -> schemas.LabourFormalMessageRecipientOut:
    return schemas.LabourFormalMessageRecipientOut(
        id=item.id,
        employer_id=item.employer_id,
        user_id=item.user_id,
        recipient_type=item.recipient_type,
        status=item.status,
        read_at=item.read_at,
        acknowledged_at=item.acknowledged_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_labour_message(item: models.LabourFormalMessage) -> schemas.LabourFormalMessageOut:
    return schemas.LabourFormalMessageOut(
        id=item.id,
        reference_number=item.reference_number,
        thread_key=item.thread_key,
        sender_user_id=item.sender_user_id,
        sender_employer_id=item.sender_employer_id,
        sender_role=item.sender_role,
        subject=item.subject,
        body=item.body,
        message_scope=item.message_scope,
        status=item.status,
        related_entity_type=item.related_entity_type,
        related_entity_id=item.related_entity_id,
        attachments=json_load(item.attachments_json, []),
        metadata=json_load(item.metadata_json, {}),
        sent_at=item.sent_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        recipients=[_serialize_labour_recipient(recipient) for recipient in item.recipients],
    )


def _formal_messages_query_for_user(db: Session, user: models.AppUser):
    query = db.query(models.LabourFormalMessage)
    if user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        return query
    if user_has_any_role(db, user, "inspecteur"):
        employer_ids = _visible_employer_ids(db, user)
        return query.join(models.LabourFormalMessageRecipient).filter(
            (models.LabourFormalMessage.sender_user_id == user.id)
            | (models.LabourFormalMessageRecipient.user_id == user.id)
            | (models.LabourFormalMessageRecipient.employer_id.in_(employer_ids) if employer_ids else False)
        )
    if user.employer_id:
        return query.join(models.LabourFormalMessageRecipient).filter(
            (models.LabourFormalMessage.sender_user_id == user.id)
            | (models.LabourFormalMessageRecipient.user_id == user.id)
            | (models.LabourFormalMessageRecipient.employer_id == user.employer_id)
        )
    return query.filter(False)


def _serialize_job_offer_summary(
    *,
    job: models.RecruitmentJobPosting,
    profile: models.RecruitmentJobProfile | None,
    employer: models.Employer | None,
) -> dict:
    attachments = json_load(profile.submission_attachments_json, []) if profile else []
    return {
        "id": job.id,
        "employer_id": job.employer_id,
        "employer_name": employer.raison_sociale if employer else None,
        "title": job.title,
        "department": job.department,
        "location": job.location,
        "contract_type": job.contract_type,
        "status": job.status,
        "description": job.description,
        "workflow_status": profile.workflow_status if profile else "draft",
        "validation_comment": profile.validation_comment if profile else None,
        "submitted_to_inspection_at": profile.submitted_to_inspection_at if profile else None,
        "last_reviewed_at": profile.last_reviewed_at if profile else None,
        "publication_mode": profile.publication_mode if profile else None,
        "publication_url": profile.publication_url if profile else None,
        "announcement_status": profile.announcement_status if profile else "draft",
        "attachments": attachments,
    }


def _serialize_job_profile(item: models.RecruitmentJobProfile) -> schemas.RecruitmentJobProfileOut:
    return schemas.RecruitmentJobProfileOut(
        id=item.id,
        job_posting_id=item.job_posting_id,
        manager_title=item.manager_title,
        mission_summary=item.mission_summary,
        main_activities=json_load(item.main_activities_json, []),
        technical_skills=json_load(item.technical_skills_json, []),
        behavioral_skills=json_load(item.behavioral_skills_json, []),
        education_level=item.education_level,
        experience_required=item.experience_required,
        languages=json_load(item.languages_json, []),
        tools=json_load(item.tools_json, []),
        certifications=json_load(item.certifications_json, []),
        salary_min=item.salary_min,
        salary_max=item.salary_max,
        working_hours=item.working_hours,
        benefits=json_load(item.benefits_json, []),
        desired_start_date=item.desired_start_date,
        application_deadline=item.application_deadline,
        publication_channels=json_load(item.publication_channels_json, []),
        classification=item.classification,
        workflow_status=item.workflow_status,
        validation_comment=item.validation_comment,
        assistant_source=json_load(item.assistant_source_json, {}),
        interview_criteria=json_load(item.interview_criteria_json, []),
        announcement_title=item.announcement_title,
        announcement_body=item.announcement_body,
        announcement_status=item.announcement_status,
        announcement_share_pack=json_load(item.announcement_share_pack_json, {}),
        submission_attachments=json_load(item.submission_attachments_json, []),
        publication_mode=item.publication_mode,
        publication_url=item.publication_url,
        submitted_to_inspection_at=item.submitted_to_inspection_at,
        last_reviewed_at=item.last_reviewed_at,
        announcement_slug=item.announcement_slug,
        validated_by_user_id=item.validated_by_user_id,
        validated_at=item.validated_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_inspector_case(item: models.InspectorCase) -> schemas.InspectorCaseOut:
    return schemas.InspectorCaseOut(
        id=item.id,
        case_number=item.case_number,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        contract_id=item.contract_id,
        portal_request_id=item.portal_request_id,
        case_type=item.case_type,
        sub_type=item.sub_type,
        source_party=item.source_party,
        subject=item.subject,
        description=item.description,
        category=item.category,
        district=item.district,
        urgency=item.urgency,
        confidentiality=item.confidentiality,
        amicable_attempt_status=item.amicable_attempt_status,
        current_stage=item.current_stage,
        outcome_summary=item.outcome_summary,
        resolution_type=item.resolution_type,
        due_at=item.due_at,
        received_at=item.received_at,
        is_sensitive=item.is_sensitive,
        attachments=json_load(item.attachments_json, []),
        tags=json_load(item.tags_json, []),
        status=item.status,
        receipt_reference=item.receipt_reference,
        assigned_inspector_user_id=item.assigned_inspector_user_id,
        filed_by_user_id=item.filed_by_user_id,
        last_response_at=item.last_response_at,
        closed_at=item.closed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_inspection_document(item: models.InspectionDocument) -> schemas.InspectionDocumentOut:
    versions = sorted(item.versions, key=lambda version: version.version_number, reverse=True)
    return schemas.InspectionDocumentOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        uploaded_by_user_id=item.uploaded_by_user_id,
        document_type=item.document_type,
        title=item.title,
        description=item.description,
        visibility=item.visibility,
        confidentiality=item.confidentiality,
        status=item.status,
        current_version_number=item.current_version_number,
        tags=json_load(item.tags_json, []),
        created_at=item.created_at,
        updated_at=item.updated_at,
        versions=[
            schemas.InspectionDocumentVersionOut(
                id=version.id,
                document_id=version.document_id,
                case_id=version.case_id,
                employer_id=version.employer_id,
                version_number=version.version_number,
                file_name=version.file_name,
                original_name=version.original_name,
                storage_path=version.storage_path,
                download_url=version.static_url,
                content_type=version.content_type,
                file_size=version.file_size,
                checksum=version.checksum,
                notes=version.notes,
                uploaded_by_user_id=version.uploaded_by_user_id,
                created_at=version.created_at,
            )
            for version in versions
        ],
    )


@router.get("/dashboard", response_model=schemas.ComplianceDashboardOut)
def get_compliance_dashboard(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    reviews = db.query(models.ComplianceReview).filter(models.ComplianceReview.employer_id == employer_id).all()
    review_counts: dict[str, int] = {}
    for item in reviews:
        review_counts[item.status] = review_counts.get(item.status, 0) + 1
    declarations = (
        db.query(models.StatutoryDeclaration)
        .filter(models.StatutoryDeclaration.employer_id == employer_id)
        .order_by(models.StatutoryDeclaration.updated_at.desc())
        .limit(10)
        .all()
    )
    visits = (
        db.query(models.ComplianceVisit)
        .filter(models.ComplianceVisit.employer_id == employer_id)
        .order_by(models.ComplianceVisit.scheduled_at.asc())
        .limit(10)
        .all()
    )
    return schemas.ComplianceDashboardOut(
        review_counts=review_counts,
        contract_queue=build_contract_queue(db, employer_id),
        integrity_issues=[schemas.IntegrityIssueOut(**issue) for issue in collect_integrity_issues(db, employer_id)],
        pending_declarations=[
            {
                "id": item.id,
                "channel": item.channel,
                "status": item.status,
                "period_label": item.period_label,
                "reference_number": item.reference_number,
            }
            for item in declarations
        ],
        upcoming_visits=[_serialize_visit(item) for item in visits],
    )


@router.get("/contracts/queue")
def list_contract_queue(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    return build_contract_queue(db, employer_id)


@router.post("/contracts/{contract_id}/versions", response_model=schemas.ContractVersionOut)
def create_reviewable_contract_version(
    contract_id: int,
    payload: schemas.ContractVersionCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    worker = db.query(models.Worker).filter(models.Worker.id == contract.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    _assert_scope(db, user, contract.employer_id)

    checklist = build_contract_checklist(
        contract,
        worker,
        salary_amount=payload.salary_amount,
        effective_date=payload.effective_date,
        classification_index=payload.classification_index,
    )
    missing = [item["label"] for item in checklist if item["status"] != "ok"]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"message": "Le contrat ne peut pas etre genere tant que les champs obligatoires sont incomplets.", "missing_items": missing},
        )

    item = create_contract_version(
        db,
        contract=contract,
        worker=worker,
        actor=user,
        source_module=payload.source_module,
        status=payload.status,
        effective_date=payload.effective_date,
        salary_amount=payload.salary_amount,
        classification_index=payload.classification_index,
    )
    sync_worker_master_data(db, worker, contract=contract, contract_version=item)
    sync_employer_register(db, contract.employer_id)
    record_audit(
        db,
        actor=user,
        action="compliance.contract_version.create",
        entity_type="contract_version",
        entity_id=item.id,
        route=f"/compliance/contracts/{contract_id}/versions",
        employer_id=contract.employer_id,
        worker_id=worker.id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_contract_version(item)


@router.get("/contracts/{contract_id}/versions", response_model=list[schemas.ContractVersionOut])
def list_contract_versions(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    _assert_scope(db, user, contract.employer_id)
    items = (
        db.query(models.ContractVersion)
        .filter(models.ContractVersion.contract_id == contract_id)
        .order_by(models.ContractVersion.version_number.desc())
        .all()
    )
    return [_serialize_contract_version(item) for item in items]


@router.post("/contracts/{contract_id}/reviews", response_model=schemas.ComplianceReviewOut)
def create_compliance_review(
    contract_id: int,
    payload: schemas.ComplianceReviewCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    worker = db.query(models.Worker).filter(models.Worker.id == contract.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    _assert_scope(db, user, contract.employer_id)

    contract_version = None
    if payload.contract_version_id:
        contract_version = db.query(models.ContractVersion).filter(models.ContractVersion.id == payload.contract_version_id).first()
    if not contract_version:
        contract_version = (
            db.query(models.ContractVersion)
            .filter(models.ContractVersion.contract_id == contract_id)
            .order_by(models.ContractVersion.version_number.desc())
            .first()
        )

    checklist = build_contract_checklist(contract, worker)
    item = models.ComplianceReview(
        employer_id=contract.employer_id,
        worker_id=worker.id,
        contract_id=contract.id,
        contract_version_id=contract_version.id if contract_version else None,
        review_type=payload.review_type,
        review_stage=payload.review_stage,
        status=payload.status,
        source_module="contracts",
        checklist_json=json_dump(checklist),
        observations_json=json_dump([]),
        requested_documents_json=json_dump(payload.requested_documents),
        tags_json=json_dump(payload.tags),
        due_at=payload.due_at,
        created_by_user_id=user.id,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="compliance.review.create",
        entity_type="compliance_review",
        entity_id=item.id,
        route=f"/compliance/contracts/{contract_id}/reviews",
        employer_id=contract.employer_id,
        worker_id=worker.id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_review(item)


@router.get("/contracts/{contract_id}/reviews", response_model=list[schemas.ComplianceReviewOut])
def list_contract_reviews(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    _assert_scope(db, user, contract.employer_id)
    items = (
        db.query(models.ComplianceReview)
        .filter(models.ComplianceReview.contract_id == contract_id)
        .order_by(models.ComplianceReview.updated_at.desc())
        .all()
    )
    return [_serialize_review(item) for item in items]


@router.post("/reviews/{review_id}/status", response_model=schemas.ComplianceReviewOut)
def update_review_status(
    review_id: int,
    payload: schemas.ComplianceReviewStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*INSPECTOR_ROLES)),
):
    item = db.query(models.ComplianceReview).filter(models.ComplianceReview.id == review_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review not found")
    _assert_scope(db, user, item.employer_id)
    before = {"status": item.status, "review_stage": item.review_stage}
    item.status = payload.status
    if payload.review_stage:
        item.review_stage = payload.review_stage
    item.reviewed_by_user_id = user.id
    if payload.status in {"submitted_control", "conforme", "a_corriger", "observations_emises"} and not item.submitted_to_inspector_at:
        item.submitted_to_inspector_at = datetime.now(timezone.utc)
    observations = json_load(item.observations_json, [])
    if payload.note:
        observations.append(
            {
                "author_user_id": user.id,
                "author_role": user.role_code,
                "message": payload.note,
                "status_marker": payload.status,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        item.observations_json = json_dump(observations)
    record_audit(
        db,
        actor=user,
        action="compliance.review.status",
        entity_type="compliance_review",
        entity_id=item.id,
        route=f"/compliance/reviews/{review_id}/status",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_review(item)


@router.post("/reviews/{review_id}/observations", response_model=schemas.InspectorObservationOut)
def add_review_observation(
    review_id: int,
    payload: schemas.InspectorObservationCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*INSPECTOR_ROLES)),
):
    review = db.query(models.ComplianceReview).filter(models.ComplianceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    _assert_scope(db, user, review.employer_id)
    item = models.InspectorObservation(
        review_id=review.id,
        employer_id=review.employer_id,
        author_user_id=user.id,
        visibility=payload.visibility,
        observation_type=payload.observation_type,
        status_marker=payload.status_marker,
        message=payload.message,
        structured_payload_json=json_dump(payload.structured_payload),
    )
    db.add(item)
    db.flush()
    observations = json_load(review.observations_json, [])
    observations.append(
        {
            "id": item.id,
            "message": payload.message,
            "status_marker": payload.status_marker,
            "author_role": user.role_code,
            "created_at": item.created_at.isoformat(),
        }
    )
    review.observations_json = json_dump(observations)
    record_audit(
        db,
        actor=user,
        action="compliance.observation.create",
        entity_type="inspector_observation",
        entity_id=item.id,
        route=f"/compliance/reviews/{review_id}/observations",
        employer_id=review.employer_id,
        worker_id=review.worker_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_observation(item)


@router.get("/reviews/{review_id}/observations", response_model=list[schemas.InspectorObservationOut])
def list_review_observations(
    review_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    review = db.query(models.ComplianceReview).filter(models.ComplianceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    _assert_scope(db, user, review.employer_id)
    items = (
        db.query(models.InspectorObservation)
        .filter(models.InspectorObservation.review_id == review_id)
        .order_by(models.InspectorObservation.created_at.desc())
        .all()
    )
    return [_serialize_observation(item) for item in items]


@router.get("/register", response_model=list[schemas.EmployerRegisterEntryOut])
def list_employer_register(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    items = (
        db.query(models.EmployerRegisterEntry)
        .filter(models.EmployerRegisterEntry.employer_id == employer_id)
        .order_by(models.EmployerRegisterEntry.updated_at.desc())
        .all()
    )
    return [
        schemas.EmployerRegisterEntryOut(
            id=item.id,
            employer_id=item.employer_id,
            worker_id=item.worker_id,
            contract_id=item.contract_id,
            contract_version_id=item.contract_version_id,
            entry_type=item.entry_type,
            registry_label=item.registry_label,
            status=item.status,
            effective_date=item.effective_date,
            archived_at=item.archived_at,
            details=json_load(item.details_json, {}),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.post("/register/sync", response_model=list[schemas.EmployerRegisterEntryOut])
def rebuild_employer_register(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_scope(db, user, employer_id)
    synced = sync_employer_register(db, employer_id)
    record_audit(
        db,
        actor=user,
        action="compliance.register.sync",
        entity_type="employer_register",
        entity_id=employer_id,
        route="/compliance/register/sync",
        employer_id=employer_id,
        after={"synced_entries": len(synced)},
    )
    db.commit()
    return [
        schemas.EmployerRegisterEntryOut(
            id=item.id,
            employer_id=item.employer_id,
            worker_id=item.worker_id,
            contract_id=item.contract_id,
            contract_version_id=item.contract_version_id,
            entry_type=item.entry_type,
            registry_label=item.registry_label,
            status=item.status,
            effective_date=item.effective_date,
            archived_at=item.archived_at,
            details=json_load(item.details_json, {}),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in synced
    ]


@router.get("/data-integrity", response_model=list[schemas.IntegrityIssueOut])
def list_integrity_issues(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    return [schemas.IntegrityIssueOut(**item) for item in collect_integrity_issues(db, employer_id)]


@router.post("/visits", response_model=schemas.ComplianceVisitOut)
def create_compliance_visit(
    payload: schemas.ComplianceVisitCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*INSPECTOR_ROLES)),
):
    _assert_scope(db, user, payload.employer_id)
    item = models.ComplianceVisit(
        employer_id=payload.employer_id,
        review_id=payload.review_id,
        visit_type=payload.visit_type,
        status=payload.status,
        inspector_name=payload.inspector_name,
        scheduled_at=payload.scheduled_at,
        notes=payload.notes,
        attachments_json=json_dump(payload.attachments),
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="compliance.visit.create",
        entity_type="compliance_visit",
        entity_id=item.id,
        route="/compliance/visits",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_visit(item)


@router.get("/visits", response_model=list[schemas.ComplianceVisitOut])
def list_compliance_visits(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    _assert_scope(db, user, employer_id)
    items = (
        db.query(models.ComplianceVisit)
        .filter(models.ComplianceVisit.employer_id == employer_id)
        .order_by(models.ComplianceVisit.scheduled_at.desc())
        .all()
    )
    return [_serialize_visit(item) for item in items]


@router.get("/employee-flow/{worker_id}", response_model=schemas.EmployeeFlowOut)
def get_employee_flow(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    _assert_scope(db, user, worker.employer_id)
    payload = build_employee_flow(db, worker)
    payload["integrity_issues"] = [schemas.IntegrityIssueOut(**item) for item in payload["integrity_issues"]]
    return schemas.EmployeeFlowOut(**payload)


@router.get("/inspector-dashboard", response_model=schemas.InspectorDashboardOut)
def get_inspector_dashboard(
    employer_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "audit", "inspecteur")),
):
    visible_ids = _visible_employer_ids(db, user)
    if employer_id is not None:
        _assert_scope(db, user, employer_id)
        visible_ids = [employer_id]
    if not visible_ids:
        return schemas.InspectorDashboardOut(scope={"employer_ids": [], "role": user.role_code}, metrics={})

    employers = db.query(models.Employer).filter(models.Employer.id.in_(visible_ids)).all()
    company_summaries: list[schemas.InspectorEmployerSummaryOut] = []
    unread_total = 0
    pending_offer_total = 0
    pending_review_total = 0
    correction_total = 0

    for employer in employers:
        worker_count = db.query(models.Worker).filter(models.Worker.employer_id == employer.id).count()
        open_cases = db.query(models.InspectorCase).filter(
            models.InspectorCase.employer_id == employer.id,
            models.InspectorCase.status.notin_(("closed", "archived", "rejected")),
        ).count()
        pending_offers = db.query(models.RecruitmentJobPosting).filter(
            models.RecruitmentJobPosting.employer_id == employer.id,
            models.RecruitmentJobPosting.status.in_(("pending_validation", "needs_correction")),
        ).count()
        pending_reviews = db.query(models.ComplianceReview).filter(
            models.ComplianceReview.employer_id == employer.id,
            models.ComplianceReview.status.notin_(("conforme", "rejetee", "archived")),
        ).count()
        unread_messages = db.query(models.LabourFormalMessageRecipient).filter(
            models.LabourFormalMessageRecipient.employer_id == employer.id,
            models.LabourFormalMessageRecipient.status != "read",
        ).count()
        latest_case = db.query(models.InspectorCase.updated_at).filter(models.InspectorCase.employer_id == employer.id).order_by(models.InspectorCase.updated_at.desc()).first()
        latest_offer = db.query(models.RecruitmentJobPosting.updated_at).filter(models.RecruitmentJobPosting.employer_id == employer.id).order_by(models.RecruitmentJobPosting.updated_at.desc()).first()
        latest_review = db.query(models.ComplianceReview.updated_at).filter(models.ComplianceReview.employer_id == employer.id).order_by(models.ComplianceReview.updated_at.desc()).first()
        latest_values = [value for value in [latest_case[0] if latest_case else None, latest_offer[0] if latest_offer else None, latest_review[0] if latest_review else None] if value is not None]
        company_summaries.append(
            schemas.InspectorEmployerSummaryOut(
                id=employer.id,
                raison_sociale=employer.raison_sociale,
                nif=employer.nif,
                stat=employer.stat,
                rccm=employer.rcs,
                adresse=employer.adresse or employer.ville,
                secteur=employer.activite,
                contact_rh=employer.contact_rh or employer.email,
                company_size=worker_count,
                open_cases=open_cases,
                pending_job_offers=pending_offers,
                pending_reviews=pending_reviews,
                unread_messages=unread_messages,
                latest_activity_at=max(latest_values) if latest_values else None,
            )
        )
        unread_total += unread_messages
        pending_offer_total += pending_offers
        pending_review_total += pending_reviews
        correction_total += db.query(models.InspectorCase).filter(
            models.InspectorCase.employer_id == employer.id,
            models.InspectorCase.status == "correction_requested",
        ).count()

    case_query = db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids))
    if status:
        case_query = case_query.filter(models.InspectorCase.status == status)
    recent_cases = case_query.order_by(models.InspectorCase.updated_at.desc()).limit(8).all()

    pending_profiles = (
        db.query(models.RecruitmentJobProfile, models.RecruitmentJobPosting, models.Employer)
        .join(models.RecruitmentJobPosting, models.RecruitmentJobProfile.job_posting_id == models.RecruitmentJobPosting.id)
        .join(models.Employer, models.Employer.id == models.RecruitmentJobPosting.employer_id)
        .filter(
            models.RecruitmentJobPosting.employer_id.in_(visible_ids),
            models.RecruitmentJobProfile.workflow_status.in_(("pending_validation", "needs_correction")),
        )
        .order_by(models.RecruitmentJobProfile.updated_at.desc())
        .limit(8)
        .all()
    )
    recent_messages = _formal_messages_query_for_user(db, user).distinct().order_by(models.LabourFormalMessage.updated_at.desc()).limit(8).all()
    pending_documents = (
        db.query(models.InspectionDocument, models.InspectorCase)
        .join(models.InspectorCase, models.InspectorCase.id == models.InspectionDocument.case_id)
        .filter(models.InspectionDocument.employer_id.in_(visible_ids))
        .order_by(models.InspectionDocument.updated_at.desc())
        .limit(8)
        .all()
    )
    high_alert_cases = db.query(models.InspectorCase).filter(
        models.InspectorCase.employer_id.in_(visible_ids),
        (models.InspectorCase.urgency == "high") | (models.InspectorCase.is_sensitive.is_(True)),
        models.InspectorCase.status.notin_(("closed", "archived", "rejected")),
    ).all()
    stale_since = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - 7 * 24 * 60 * 60)

    return schemas.InspectorDashboardOut(
        scope={"employer_ids": visible_ids, "role": user.role_code},
        metrics={
            "companies_followed": len(visible_ids),
            "pending_job_offers": pending_offer_total,
            "pending_reviews": pending_review_total,
            "complaints_new": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status == "received").count(),
            "complaints_in_progress": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("received", "in_review", "investigating", "conciliation", "correction_requested"))).count(),
            "complaints_closed": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("closed", "archived"))).count(),
            "cases_to_qualify": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("received", "A_QUALIFIER", "SOUMIS"))).count(),
            "convocations_to_emit": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("A_QUALIFIER", "EN_ATTENTE_PIECES", "in_review"))).count(),
            "conciliations_scheduled": db.query(models.LabourCaseEvent).filter(models.LabourCaseEvent.employer_id.in_(visible_ids), models.LabourCaseEvent.event_type == "conciliation", models.LabourCaseEvent.status.in_(("planned", "scheduled"))).count(),
            "waiting_employer": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("EN_ATTENTE_EMPLOYEUR", "correction_requested"))).count(),
            "waiting_employee": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status == "EN_ATTENTE_EMPLOYE").count(),
            "urgent_sensitive_cases": len(high_alert_cases),
            "stale_cases_7d": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.notin_(("closed", "archived", "CLOTURE", "ARCHIVE")), models.InspectorCase.updated_at <= stale_since).count(),
            "pv_to_produce": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("PV_A_EMETTRE", "EN_CONCILIATION", "CONCILIATION_PARTIELLE", "NON_CONCILIE", "CARENCE"))).count(),
            "pv_issued": db.query(models.LabourPV).filter(models.LabourPV.employer_id.in_(visible_ids), models.LabourPV.status.in_(("issued", "PV_EMIS", "sent"))).count(),
            "non_execution_cases": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.status.in_(("NON_EXECUTE", "EN_SUIVI_EXECUTION"))).count(),
            "sanction_reviews": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.case_type.in_(("sanction_review", "contestation_sanction"))).count(),
            "delegate_protection_cases": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.case_type.in_(("delegate_protection", "dossier_delegue_personnel"))).count(),
            "collective_grievances": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(visible_ids), models.InspectorCase.case_type.in_(("collective_grievance", "doleance_collective"))).count(),
            "unread_messages": unread_total,
            "pending_corrections": correction_total
            + db.query(models.RecruitmentJobProfile)
            .join(models.RecruitmentJobPosting, models.RecruitmentJobProfile.job_posting_id == models.RecruitmentJobPosting.id)
            .filter(models.RecruitmentJobPosting.employer_id.in_(visible_ids), models.RecruitmentJobProfile.workflow_status == "needs_correction")
            .count(),
            "critical_alerts": len(high_alert_cases),
        },
        recent_companies=sorted(company_summaries, key=lambda item: item.latest_activity_at or datetime.min, reverse=True)[:6],
        recent_cases=[_serialize_inspector_case(item) for item in recent_cases],
        recent_messages=[_serialize_labour_message(item) for item in recent_messages],
        pending_job_offers=[_serialize_job_offer_summary(job=job, profile=profile, employer=employer) for profile, job, employer in pending_profiles],
        pending_documents=[
            {
                "document_id": document.id,
                "case_id": case_item.id,
                "case_number": case_item.case_number,
                "employer_id": document.employer_id,
                "title": document.title,
                "document_type": document.document_type,
                "status": document.status,
                "updated_at": document.updated_at,
            }
            for document, case_item in pending_documents
        ],
        alerts=[
            {
                "case_id": item.id,
                "case_number": item.case_number,
                "subject": item.subject,
                "urgency": item.urgency,
                "status": item.status,
            }
            for item in high_alert_cases[:8]
        ],
    )


@router.get("/inspector-employers", response_model=list[schemas.InspectorEmployerSummaryOut])
def list_inspector_employers(
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "audit", "inspecteur")),
):
    visible_ids = _visible_employer_ids(db, user)
    if not visible_ids:
        return []
    query = db.query(models.Employer).filter(models.Employer.id.in_(visible_ids))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (models.Employer.raison_sociale.ilike(pattern))
            | (models.Employer.nif.ilike(pattern))
            | (models.Employer.stat.ilike(pattern))
            | (models.Employer.activite.ilike(pattern))
        )
    employers = query.order_by(models.Employer.raison_sociale.asc()).all()
    items = []
    for employer in employers:
        items.append(
            schemas.InspectorEmployerSummaryOut(
                id=employer.id,
                raison_sociale=employer.raison_sociale,
                nif=employer.nif,
                stat=employer.stat,
                rccm=employer.rcs,
                adresse=employer.adresse or employer.ville,
                secteur=employer.activite,
                contact_rh=employer.contact_rh or employer.email,
                company_size=db.query(models.Worker).filter(models.Worker.employer_id == employer.id).count(),
                open_cases=db.query(models.InspectorCase).filter(models.InspectorCase.employer_id == employer.id, models.InspectorCase.status.notin_(("closed", "archived"))).count(),
                pending_job_offers=db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.employer_id == employer.id, models.RecruitmentJobPosting.status.in_(("pending_validation", "needs_correction"))).count(),
                pending_reviews=db.query(models.ComplianceReview).filter(models.ComplianceReview.employer_id == employer.id, models.ComplianceReview.status.notin_(("conforme", "rejetee", "archived"))).count(),
                unread_messages=db.query(models.LabourFormalMessageRecipient).filter(models.LabourFormalMessageRecipient.employer_id == employer.id, models.LabourFormalMessageRecipient.status != "read").count(),
            )
        )
    return items


@router.get("/legal-modules-status", response_model=schemas.LegalModulesStatusOut)
def get_legal_modules_status(
    employer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    visible_ids = _visible_employer_ids(db, user)
    if employer_id is not None:
        _assert_scope(db, user, employer_id)
        visible_ids = [employer_id]
    return build_legal_modules_status(db, visible_ids)


@router.get("/inspector-employers/{employer_id}", response_model=schemas.InspectorEmployerDetailOut)
def get_inspector_employer_detail(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "audit", "inspecteur")),
):
    _assert_scope(db, user, employer_id)
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    cases = db.query(models.InspectorCase).filter(models.InspectorCase.employer_id == employer_id).order_by(models.InspectorCase.updated_at.desc()).limit(12).all()
    documents = db.query(models.InspectionDocument).filter(models.InspectionDocument.employer_id == employer_id).order_by(models.InspectionDocument.updated_at.desc()).limit(12).all()
    offers = (
        db.query(models.RecruitmentJobPosting, models.RecruitmentJobProfile)
        .outerjoin(models.RecruitmentJobProfile, models.RecruitmentJobProfile.job_posting_id == models.RecruitmentJobPosting.id)
        .filter(models.RecruitmentJobPosting.employer_id == employer_id)
        .order_by(models.RecruitmentJobPosting.updated_at.desc())
        .limit(12)
        .all()
    )
    formal_messages = (
        db.query(models.LabourFormalMessage)
        .join(models.LabourFormalMessageRecipient)
        .filter(models.LabourFormalMessageRecipient.employer_id == employer_id)
        .order_by(models.LabourFormalMessage.updated_at.desc())
        .limit(12)
        .all()
    )
    observations = db.query(models.InspectorObservation).filter(models.InspectorObservation.employer_id == employer_id).order_by(models.InspectorObservation.created_at.desc()).limit(12).all()
    actions = db.query(models.AuditLog).filter(models.AuditLog.employer_id == employer_id).order_by(models.AuditLog.created_at.desc()).limit(20).all()
    contacts = [
        {"label": "RH", "value": employer.contact_rh},
        {"label": "Email", "value": employer.email},
        {"label": "Telephone", "value": employer.telephone},
        {"label": "Representant", "value": employer.representant},
    ]
    contacts = [item for item in contacts if item["value"]]
    return schemas.InspectorEmployerDetailOut(
        employer={
            "id": employer.id,
            "raison_sociale": employer.raison_sociale,
            "nif": employer.nif,
            "stat": employer.stat,
            "rccm": employer.rcs,
            "adresse": employer.adresse,
            "ville": employer.ville,
            "activite": employer.activite,
            "contact_rh": employer.contact_rh,
            "email": employer.email,
            "telephone": employer.telephone,
            "representant": employer.representant,
            "effectif_declare": db.query(models.Worker).filter(models.Worker.employer_id == employer_id).count(),
        },
        compliance_status={
            "open_cases": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id == employer_id, models.InspectorCase.status.notin_(("closed", "archived"))).count(),
            "pending_reviews": db.query(models.ComplianceReview).filter(models.ComplianceReview.employer_id == employer_id, models.ComplianceReview.status.notin_(("conforme", "rejetee", "archived"))).count(),
            "pending_job_offers": db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.employer_id == employer_id, models.RecruitmentJobPosting.status.in_(("pending_validation", "needs_correction"))).count(),
        },
        contacts=contacts,
        documents=[_serialize_inspection_document(item) for item in documents],
        cases=[_serialize_inspector_case(item) for item in cases],
        job_offers=[_serialize_job_offer_summary(job=job, profile=profile, employer=employer) for job, profile in offers],
        formal_messages=[_serialize_labour_message(item) for item in formal_messages],
        observations=[
            {
                "id": item.id,
                "review_id": item.review_id,
                "message": item.message,
                "observation_type": item.observation_type,
                "status_marker": item.status_marker,
                "created_at": item.created_at,
            }
            for item in observations
        ],
        actions=[
            {
                "id": item.id,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "actor_role": item.actor_role,
                "created_at": item.created_at,
            }
            for item in actions
        ],
    )


@router.get("/job-offers")
def list_inspection_job_offers(
    employer_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "juridique", "direction", "inspecteur")),
):
    visible_ids = _visible_employer_ids(db, user)
    if employer_id is not None:
        _assert_scope(db, user, employer_id)
        visible_ids = [employer_id]
    query = (
        db.query(models.RecruitmentJobPosting, models.RecruitmentJobProfile, models.Employer)
        .outerjoin(models.RecruitmentJobProfile, models.RecruitmentJobProfile.job_posting_id == models.RecruitmentJobPosting.id)
        .join(models.Employer, models.Employer.id == models.RecruitmentJobPosting.employer_id)
        .filter(models.RecruitmentJobPosting.employer_id.in_(visible_ids))
    )
    if status:
        query = query.filter(
            (models.RecruitmentJobPosting.status == status)
            | (models.RecruitmentJobProfile.workflow_status == status)
        )
    rows = query.order_by(models.RecruitmentJobPosting.updated_at.desc()).all()
    return [_serialize_job_offer_summary(job=job, profile=profile, employer=employer) for job, profile, employer in rows]


@router.post("/job-offers/{job_id}/decision", response_model=schemas.RecruitmentJobProfileOut)
def review_job_offer(
    job_id: int,
    payload: schemas.RecruitmentInspectorDecisionIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "inspecteur")),
):
    job = db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    _assert_scope(db, user, job.employer_id)
    profile = db.query(models.RecruitmentJobProfile).filter(models.RecruitmentJobProfile.job_posting_id == job.id).first()
    if not profile:
        profile = models.RecruitmentJobProfile(job_posting_id=job.id)
        db.add(profile)
        db.flush()

    action = (payload.action or "").strip().lower()
    if action in {"request_correction", "refuse"} and not (payload.comment or "").strip():
        raise HTTPException(status_code=422, detail="A motivation is required for this decision")

    before = {"workflow_status": profile.workflow_status, "job_status": job.status, "validation_comment": profile.validation_comment}
    if action == "request_correction":
        profile.workflow_status = "needs_correction"
        if job.status not in {"published", "published_non_conforme"}:
            job.status = "needs_correction"
        profile.validation_comment = payload.comment
    elif action == "approve":
        profile.workflow_status = "validated_with_observations" if (payload.comment or "").strip() else "validated"
        job.status = "published" if job.status in {"published", "published_non_validated", "en_revue_inspecteur", "published_non_conforme"} else "validated"
        profile.validation_comment = payload.comment
        profile.validated_by_user_id = user.id
        profile.validated_at = datetime.now(timezone.utc)
    elif action == "refuse":
        profile.workflow_status = "rejected"
        job.status = "published_non_conforme" if job.status in {"published", "published_non_validated", "en_revue_inspecteur"} else "rejected"
        profile.validation_comment = payload.comment
        profile.validated_by_user_id = user.id
        profile.validated_at = datetime.now(timezone.utc)
    elif action == "archive":
        profile.workflow_status = "archived"
        job.status = "archived"
    elif action == "record_publication":
        profile.publication_mode = payload.publication_mode or profile.publication_mode
        profile.publication_url = payload.publication_url or profile.publication_url
        profile.announcement_status = "published"
        job.status = "published"
        if profile.workflow_status in {"draft", "en_revue_inspecteur"}:
            profile.workflow_status = "published_non_validated"
    else:
        raise HTTPException(status_code=422, detail="Unsupported inspection decision")

    profile.last_reviewed_at = datetime.now(timezone.utc)
    db.add(
        models.RecruitmentActivity(
            employer_id=job.employer_id,
            job_posting_id=job.id,
            actor_user_id=user.id,
            event_type=f"inspection.job.{action}",
            visibility="internal",
            message=f"Decision inspection: {action}",
            payload_json=json_dump({"comment": payload.comment, "publication_mode": payload.publication_mode, "publication_url": payload.publication_url}),
        )
    )
    record_audit(
        db,
        actor=user,
        action=f"compliance.job_offer.{action}",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/compliance/job-offers/{job_id}/decision",
        employer_id=job.employer_id,
        before=before,
        after=profile,
    )
    db.commit()
    db.refresh(profile)
    return _serialize_job_profile(profile)


@router.post("/job-offers/{job_id}/attachments/upload", response_model=schemas.RecruitmentJobProfileOut)
async def upload_inspection_job_offer_attachment(
    job_id: int,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "juridique", "direction", "inspecteur")),
):
    job = db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    _assert_scope(db, user, job.employer_id)
    profile = db.query(models.RecruitmentJobProfile).filter(models.RecruitmentJobProfile.job_posting_id == job.id).first()
    if not profile:
        profile = models.RecruitmentJobProfile(job_posting_id=job.id)
        db.add(profile)
        db.flush()

    safe_name = sanitize_filename_part(Path(attachment.filename or "piece_jointe").name)
    storage_name = f"inspection/job_offers/{job.id}/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{safe_name}"
    stored_path = save_upload_file(attachment.file, filename=storage_name)
    attachments = json_load(profile.submission_attachments_json, [])
    attachments.append(
        {
            "name": attachment.filename,
            "content_type": attachment.content_type,
            "path": stored_path,
            "uploaded_by_user_id": user.id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    profile.submission_attachments_json = json_dump(attachments)
    record_audit(
        db,
        actor=user,
        action="compliance.job_offer.attachment",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/compliance/job-offers/{job_id}/attachments/upload",
        employer_id=job.employer_id,
        after={"filename": attachment.filename},
    )
    db.commit()
    db.refresh(profile)
    return _serialize_job_profile(profile)


@router.get("/formal-messages", response_model=list[schemas.LabourFormalMessageOut])
def list_formal_messages(
    employer_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "inspecteur", "juridique", "direction", "audit")),
):
    query = _formal_messages_query_for_user(db, user)
    if employer_id is not None:
        _assert_scope(db, user, employer_id)
        recipient_message_ids = db.query(models.LabourFormalMessageRecipient.message_id).filter(
            models.LabourFormalMessageRecipient.employer_id == employer_id
        )
        query = query.filter(
            (models.LabourFormalMessage.sender_employer_id == employer_id)
            | (models.LabourFormalMessage.id.in_(recipient_message_ids))
        )
    if status:
        query = query.filter(models.LabourFormalMessage.status == status)
    items = query.distinct().order_by(models.LabourFormalMessage.updated_at.desc()).all()
    return [_serialize_labour_message(item) for item in items]


@router.post("/formal-messages", response_model=schemas.LabourFormalMessageOut)
def create_formal_message(
    payload: schemas.LabourFormalMessageCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "inspecteur", "juridique", "direction")),
):
    item = models.LabourFormalMessage(
        reference_number=_next_labour_message_reference(db),
        thread_key=None,
        sender_user_id=user.id,
        sender_employer_id=user.employer_id,
        sender_role=user.role_code,
        subject=payload.subject,
        body=payload.body,
        message_scope=payload.message_scope,
        status="sent" if payload.send_now else "draft",
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        attachments_json=json_dump(payload.attachments),
        metadata_json=json_dump({"recipient_count": len(payload.recipients)}),
        sent_at=datetime.now(timezone.utc) if payload.send_now else None,
    )
    item.thread_key = item.reference_number
    db.add(item)
    db.flush()

    for recipient in payload.recipients:
        target_user = None
        employer_target_id = recipient.employer_id
        if recipient.user_id is not None:
            target_user = db.query(models.AppUser).filter(models.AppUser.id == recipient.user_id).first()
            if not target_user:
                raise HTTPException(status_code=404, detail="Recipient user not found")
            employer_target_id = target_user.employer_id or employer_target_id
        if employer_target_id is not None:
            _assert_scope(db, user, employer_target_id)
        db.add(
            models.LabourFormalMessageRecipient(
                message_id=item.id,
                employer_id=employer_target_id,
                user_id=recipient.user_id,
                recipient_type=recipient.recipient_type,
                status="sent" if payload.send_now else "draft",
                metadata_json=json_dump({}),
            )
        )

    record_audit(
        db,
        actor=user,
        action="compliance.formal_message.create",
        entity_type="labour_formal_message",
        entity_id=item.id,
        route="/compliance/formal-messages",
        employer_id=user.employer_id,
        after={"subject": payload.subject, "status": item.status},
    )
    db.commit()
    db.refresh(item)
    return _serialize_labour_message(item)


@router.post("/formal-messages/{message_id}/send", response_model=schemas.LabourFormalMessageOut)
def send_formal_message(
    message_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "inspecteur", "juridique", "direction")),
):
    item = db.query(models.LabourFormalMessage).filter(models.LabourFormalMessage.id == message_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Formal message not found")
    if item.sender_user_id != user.id and not user_has_any_role(db, user, "admin", "rh", "juridique", "direction"):
        raise HTTPException(status_code=403, detail="Forbidden")
    item.status = "sent"
    item.sent_at = datetime.now(timezone.utc)
    for recipient in item.recipients:
        recipient.status = "sent"
    record_audit(
        db,
        actor=user,
        action="compliance.formal_message.send",
        entity_type="labour_formal_message",
        entity_id=item.id,
        route=f"/compliance/formal-messages/{message_id}/send",
        employer_id=item.sender_employer_id,
        after={"status": item.status},
    )
    db.commit()
    db.refresh(item)
    return _serialize_labour_message(item)


@router.post("/formal-messages/{message_id}/read", response_model=schemas.LabourFormalMessageOut)
def mark_formal_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "employe", "inspecteur", "juridique", "direction", "audit")),
):
    item = db.query(models.LabourFormalMessage).filter(models.LabourFormalMessage.id == message_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Formal message not found")
    visible = False
    for recipient in item.recipients:
        if recipient.user_id == user.id or (recipient.employer_id and user.employer_id and recipient.employer_id == user.employer_id):
            recipient.status = "read"
            recipient.read_at = datetime.now(timezone.utc)
            visible = True
    if not visible and item.sender_user_id != user.id and not user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db.commit()
    db.refresh(item)
    return _serialize_labour_message(item)


@router.get("/parameters", response_model=list[schemas.RecruitmentLibraryItemOut])
def list_inspection_parameters(
    category: str = Query(...),
    employer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "inspecteur")),
):
    scoped_employer_id = employer_id
    if scoped_employer_id is not None:
        _assert_scope(db, user, scoped_employer_id)
    query = db.query(models.RecruitmentLibraryItem).filter(models.RecruitmentLibraryItem.category == category)
    if scoped_employer_id is not None:
        query = query.filter(
            (models.RecruitmentLibraryItem.employer_id == scoped_employer_id)
            | (models.RecruitmentLibraryItem.employer_id.is_(None))
        )
    items = query.order_by(models.RecruitmentLibraryItem.label.asc()).all()
    return [schemas.RecruitmentLibraryItemOut.model_validate(item) for item in items]


@router.post("/parameters", response_model=schemas.RecruitmentLibraryItemOut)
def create_inspection_parameter(
    payload: schemas.RecruitmentLibraryItemCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction")),
):
    if payload.employer_id is not None:
        _assert_scope(db, user, payload.employer_id)
    item = models.RecruitmentLibraryItem(
        employer_id=payload.employer_id,
        category=payload.category,
        label=payload.label,
        normalized_key=payload.label.strip().lower().replace(" ", "_"),
        description=payload.description,
        payload_json=json_dump(payload.payload),
        is_system=False,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return schemas.RecruitmentLibraryItemOut.model_validate(item)


@router.post("/inspector-assignments", response_model=schemas.LabourInspectorAssignmentOut)
def create_inspector_assignment(
    payload: schemas.LabourInspectorAssignmentCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction")),
):
    employer = db.query(models.Employer).filter(models.Employer.id == payload.employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    inspector_user = db.query(models.AppUser).filter(models.AppUser.id == payload.inspector_user_id, models.AppUser.is_active.is_(True)).first()
    if not inspector_user or not user_has_any_role(db, inspector_user, "inspecteur"):
        raise HTTPException(status_code=404, detail="Inspector user not found")
    item = (
        db.query(models.LabourInspectorAssignment)
        .filter(
            models.LabourInspectorAssignment.employer_id == payload.employer_id,
            models.LabourInspectorAssignment.inspector_user_id == payload.inspector_user_id,
        )
        .first()
    )
    if item is None:
        item = models.LabourInspectorAssignment(
            employer_id=payload.employer_id,
            inspector_user_id=payload.inspector_user_id,
            assigned_by_user_id=user.id,
            assignment_scope=payload.assignment_scope,
            circonscription=payload.circonscription,
            sector_filter=payload.sector_filter,
            status="active",
            notes=payload.notes,
        )
        db.add(item)
    else:
        item.assignment_scope = payload.assignment_scope
        item.circonscription = payload.circonscription
        item.sector_filter = payload.sector_filter
        item.status = "active"
        item.notes = payload.notes
        item.assigned_by_user_id = user.id
    record_audit(
        db,
        actor=user,
        action="compliance.inspector_assignment.upsert",
        entity_type="labour_inspector_assignment",
        entity_id=f"{payload.employer_id}:{payload.inspector_user_id}",
        route="/compliance/inspector-assignments",
        employer_id=payload.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_labour_assignment(item)


@router.get("/inspector-assignments", response_model=list[schemas.LabourInspectorAssignmentOut])
def list_inspector_assignments(
    employer_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "inspecteur")),
):
    query = db.query(models.LabourInspectorAssignment)
    if user_has_any_role(db, user, "inspecteur"):
        query = query.filter(models.LabourInspectorAssignment.inspector_user_id == user.id)
    if employer_id is not None:
        _assert_scope(db, user, employer_id)
        query = query.filter(models.LabourInspectorAssignment.employer_id == employer_id)
    items = query.order_by(models.LabourInspectorAssignment.updated_at.desc()).all()
    return [_serialize_labour_assignment(item) for item in items]


