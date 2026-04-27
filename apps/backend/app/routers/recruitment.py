import json
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_manage_worker, require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.compliance_service import create_contract_version, sync_employer_register
from ..services.file_storage import sanitize_filename_part, save_upload_file
from ..services.master_data_service import sync_worker_master_data
from ..services.pdf_generation_service import build_recruitment_announcement_pdf
from ..services.recruitment_assistant_service import (
    _normalize_key,
    build_announcement_payload,
    build_contract_guidance,
    build_contract_draft_html,
    extract_text_from_upload,
    get_library_entries,
    json_dump,
    parse_candidate_profile,
    suggest_job_profile,
)
from ..services.recruitment_publication_service import (
    get_or_create_publication_channels,
    json_load as publication_json_load,
    mask_channel_config,
    merge_channel_config,
    publish_job_channels,
)


router = APIRouter(prefix="/recruitment", tags=["recruitment"])

READ_ROLES = ("admin", "rh", "employeur", "manager")
WRITE_ROLES = ("admin", "rh", "employeur")
PUBLICATION_WRITE_ROLES = ("admin", "rh", "recrutement")
PUBLICATION_READ_ROLES = ("admin", "rh", "recrutement")


def _json_load(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh"):
        return
    if user_has_any_role(db, user, "employeur", "recrutement") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _serialize_library_item(item: models.RecruitmentLibraryItem) -> schemas.RecruitmentLibraryItemOut:
    return schemas.RecruitmentLibraryItemOut(
        id=item.id,
        employer_id=item.employer_id,
        category=item.category,
        label=item.label,
        normalized_key=item.normalized_key,
        description=item.description,
        payload=_json_load(item.payload_json, {}),
        is_system=item.is_system,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_profile(profile: models.RecruitmentJobProfile) -> schemas.RecruitmentJobProfileOut:
    return schemas.RecruitmentJobProfileOut(
        id=profile.id,
        job_posting_id=profile.job_posting_id,
        manager_title=profile.manager_title,
        mission_summary=profile.mission_summary,
        main_activities=_json_load(profile.main_activities_json, []),
        technical_skills=_json_load(profile.technical_skills_json, []),
        behavioral_skills=_json_load(profile.behavioral_skills_json, []),
        education_level=profile.education_level,
        experience_required=profile.experience_required,
        languages=_json_load(profile.languages_json, []),
        tools=_json_load(profile.tools_json, []),
        certifications=_json_load(profile.certifications_json, []),
        salary_min=profile.salary_min,
        salary_max=profile.salary_max,
        working_hours=profile.working_hours,
        benefits=_json_load(profile.benefits_json, []),
        desired_start_date=profile.desired_start_date,
        application_deadline=profile.application_deadline,
        publication_channels=_json_load(profile.publication_channels_json, []),
        classification=profile.classification,
        workflow_status=profile.workflow_status,
        validation_comment=profile.validation_comment,
        assistant_source=_json_load(profile.assistant_source_json, {}),
        interview_criteria=_json_load(profile.interview_criteria_json, []),
        announcement_title=profile.announcement_title,
        announcement_body=profile.announcement_body,
        announcement_status=profile.announcement_status,
        announcement_share_pack=_json_load(profile.announcement_share_pack_json, {}),
        submission_attachments=_json_load(profile.submission_attachments_json, []),
        workforce_job_profile_id=profile.workforce_job_profile_id,
        contract_guidance=_json_load(profile.contract_guidance_json, {}),
        publication_mode=profile.publication_mode,
        publication_url=profile.publication_url,
        submitted_to_inspection_at=profile.submitted_to_inspection_at,
        last_reviewed_at=profile.last_reviewed_at,
        announcement_slug=profile.announcement_slug,
        validated_by_user_id=profile.validated_by_user_id,
        validated_at=profile.validated_at,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _serialize_job(item: models.RecruitmentJobPosting) -> schemas.RecruitmentJobPostingOut:
    return schemas.RecruitmentJobPostingOut(
        id=item.id,
        employer_id=item.employer_id,
        title=item.title,
        department=item.department,
        location=item.location,
        contract_type=item.contract_type,
        status=item.status,
        salary_range=item.salary_range,
        description=item.description,
        skills_required=item.skills_required,
        publish_channels=_json_load(getattr(item, "publish_channels_json", "[]"), []),
        publish_status=getattr(item, "publish_status", "draft") or "draft",
        publish_logs=_json_load(getattr(item, "publish_logs_json", "[]"), []),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_publication_channel(item: models.RecruitmentPublicationChannel) -> schemas.RecruitmentPublicationChannelOut:
    raw_config = publication_json_load(item.config_json, {})
    masked_config, configured_secret_fields = mask_channel_config(raw_config)
    return schemas.RecruitmentPublicationChannelOut(
        id=item.id,
        company_id=item.company_id,
        channel_type=item.channel_type,
        is_active=item.is_active,
        default_publish=item.default_publish,
        config=masked_config,
        secret_fields_configured=configured_secret_fields,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_publication_log(item: models.RecruitmentPublicationLog) -> schemas.RecruitmentPublicationLogOut:
    return schemas.RecruitmentPublicationLogOut(
        id=item.id,
        job_id=item.job_id,
        channel=item.channel,
        status=item.status,
        message=item.message,
        details=_json_load(item.details_json, {}),
        triggered_by_user_id=item.triggered_by_user_id,
        timestamp=item.timestamp,
    )


def _serialize_asset(asset: models.RecruitmentCandidateAsset) -> schemas.RecruitmentCandidateAssetOut:
    return schemas.RecruitmentCandidateAssetOut(
        id=asset.id,
        candidate_id=asset.candidate_id,
        resume_original_name=asset.resume_original_name,
        resume_storage_path=asset.resume_storage_path,
        attachments=_json_load(asset.attachments_json, []),
        raw_extract_text=asset.raw_extract_text,
        parsed_profile=_json_load(asset.parsed_profile_json, {}),
        parsing_status=asset.parsing_status,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _serialize_interview(interview: models.RecruitmentInterview) -> schemas.RecruitmentInterviewOut:
    return schemas.RecruitmentInterviewOut(
        id=interview.id,
        application_id=interview.application_id,
        round_number=interview.round_number,
        round_label=interview.round_label,
        interview_type=interview.interview_type,
        scheduled_at=interview.scheduled_at,
        interviewer_user_id=interview.interviewer_user_id,
        interviewer_name=interview.interviewer_name,
        status=interview.status,
        score_total=interview.score_total,
        scorecard=_json_load(interview.scorecard_json, []),
        notes=interview.notes,
        recommendation=interview.recommendation,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
    )


def _serialize_decision(decision: models.RecruitmentDecision) -> schemas.RecruitmentDecisionOut:
    return schemas.RecruitmentDecisionOut(
        id=decision.id,
        application_id=decision.application_id,
        shortlist_rank=decision.shortlist_rank,
        decision_status=decision.decision_status,
        decision_comment=decision.decision_comment,
        decided_by_user_id=decision.decided_by_user_id,
        decided_at=decision.decided_at,
        converted_worker_id=decision.converted_worker_id,
        contract_draft_id=decision.contract_draft_id,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )


def _serialize_activity(activity: models.RecruitmentActivity) -> schemas.RecruitmentActivityOut:
    return schemas.RecruitmentActivityOut(
        id=activity.id,
        employer_id=activity.employer_id,
        job_posting_id=activity.job_posting_id,
        candidate_id=activity.candidate_id,
        application_id=activity.application_id,
        interview_id=activity.interview_id,
        actor_user_id=activity.actor_user_id,
        event_type=activity.event_type,
        visibility=activity.visibility,
        message=activity.message,
        payload=_json_load(activity.payload_json, {}),
        created_at=activity.created_at,
    )


def _log_activity(
    db: Session,
    *,
    employer_id: int,
    user: models.AppUser,
    event_type: str,
    message: str,
    job_posting_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    application_id: Optional[int] = None,
    interview_id: Optional[int] = None,
    visibility: str = "internal",
    payload: Optional[dict] = None,
) -> models.RecruitmentActivity:
    item = models.RecruitmentActivity(
        employer_id=employer_id,
        job_posting_id=job_posting_id,
        candidate_id=candidate_id,
        application_id=application_id,
        interview_id=interview_id,
        actor_user_id=user.id if user else None,
        event_type=event_type,
        visibility=visibility,
        message=message,
        payload_json=json_dump(payload or {}),
    )
    db.add(item)
    return item


def _get_job_or_404(db: Session, job_id: int) -> models.RecruitmentJobPosting:
    item = db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.id == job_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return item


def _get_candidate_or_404(db: Session, candidate_id: int) -> models.RecruitmentCandidate:
    item = db.query(models.RecruitmentCandidate).filter(models.RecruitmentCandidate.id == candidate_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return item


def _get_application_or_404(db: Session, application_id: int) -> models.RecruitmentApplication:
    item = db.query(models.RecruitmentApplication).filter(models.RecruitmentApplication.id == application_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Application not found")
    return item


def _get_profile(db: Session, job_id: int) -> Optional[models.RecruitmentJobProfile]:
    return db.query(models.RecruitmentJobProfile).filter(models.RecruitmentJobProfile.job_posting_id == job_id).first()


def _get_or_create_profile(db: Session, job: models.RecruitmentJobPosting) -> models.RecruitmentJobProfile:
    profile = _get_profile(db, job.id)
    if profile:
        return profile
    profile = models.RecruitmentJobProfile(job_posting_id=job.id)
    db.add(profile)
    db.flush()
    return profile


def _serialize_profile_dict(profile: models.RecruitmentJobProfile) -> dict:
    return {
        "manager_title": profile.manager_title,
        "mission_summary": profile.mission_summary,
        "main_activities": _json_load(profile.main_activities_json, []),
        "technical_skills": _json_load(profile.technical_skills_json, []),
        "behavioral_skills": _json_load(profile.behavioral_skills_json, []),
        "education_level": profile.education_level,
        "experience_required": profile.experience_required,
        "languages": _json_load(profile.languages_json, []),
        "tools": _json_load(profile.tools_json, []),
        "certifications": _json_load(profile.certifications_json, []),
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
        "working_hours": profile.working_hours,
        "working_days": _json_load(profile.working_days_json, []),
        "benefits": _json_load(profile.benefits_json, []),
        "desired_start_date": profile.desired_start_date.isoformat() if profile.desired_start_date else None,
        "application_deadline": profile.application_deadline.isoformat() if profile.application_deadline else None,
        "publication_channels": _json_load(profile.publication_channels_json, []),
        "classification": profile.classification,
        "workflow_status": profile.workflow_status,
        "validation_comment": profile.validation_comment,
        "assistant_source": _json_load(profile.assistant_source_json, {}),
        "interview_criteria": _json_load(profile.interview_criteria_json, []),
        "announcement_title": profile.announcement_title,
        "announcement_body": profile.announcement_body,
        "announcement_status": profile.announcement_status,
        "announcement_share_pack": _json_load(profile.announcement_share_pack_json, {}),
        "submission_attachments": _json_load(profile.submission_attachments_json, []),
        "workforce_job_profile_id": profile.workforce_job_profile_id,
        "contract_guidance": _json_load(profile.contract_guidance_json, {}),
        "publication_mode": profile.publication_mode,
        "publication_url": profile.publication_url,
        "submitted_to_inspection_at": profile.submitted_to_inspection_at.isoformat() if profile.submitted_to_inspection_at else None,
        "last_reviewed_at": profile.last_reviewed_at.isoformat() if profile.last_reviewed_at else None,
    }


def _apply_profile_payload(profile: models.RecruitmentJobProfile, payload: schemas.RecruitmentJobProfileUpsert) -> None:
    profile.manager_title = payload.manager_title
    profile.mission_summary = payload.mission_summary
    profile.main_activities_json = json_dump(payload.main_activities)
    profile.technical_skills_json = json_dump(payload.technical_skills)
    profile.behavioral_skills_json = json_dump(payload.behavioral_skills)
    profile.education_level = payload.education_level
    profile.experience_required = payload.experience_required
    profile.languages_json = json_dump(payload.languages)
    profile.tools_json = json_dump(payload.tools)
    profile.certifications_json = json_dump(payload.certifications)
    profile.salary_min = payload.salary_min
    profile.salary_max = payload.salary_max
    profile.working_hours = payload.working_hours
    profile.working_days_json = json_dump(payload.working_days)
    profile.benefits_json = json_dump(payload.benefits)
    profile.desired_start_date = payload.desired_start_date
    profile.application_deadline = payload.application_deadline
    profile.publication_channels_json = json_dump(payload.publication_channels)
    profile.classification = payload.classification
    profile.workflow_status = payload.workflow_status
    profile.validation_comment = payload.validation_comment
    profile.assistant_source_json = json_dump(payload.assistant_source)
    profile.interview_criteria_json = json_dump(payload.interview_criteria)
    profile.announcement_title = payload.announcement_title
    profile.announcement_body = payload.announcement_body
    profile.announcement_status = payload.announcement_status
    profile.announcement_share_pack_json = json_dump(payload.announcement_share_pack)
    profile.submission_attachments_json = json_dump(payload.submission_attachments)
    profile.workforce_job_profile_id = payload.workforce_job_profile_id
    profile.contract_guidance_json = json_dump(payload.contract_guidance)
    profile.publication_mode = payload.publication_mode
    profile.publication_url = payload.publication_url
    profile.submitted_to_inspection_at = payload.submitted_to_inspection_at
    profile.last_reviewed_at = payload.last_reviewed_at


def _sync_workforce_job_profile(
    db: Session,
    *,
    job: models.RecruitmentJobPosting,
    profile: models.RecruitmentJobProfile,
) -> models.WorkforceJobProfile:
    workforce_profile = None
    if profile.workforce_job_profile_id:
        workforce_profile = (
            db.query(models.WorkforceJobProfile)
            .filter(models.WorkforceJobProfile.id == profile.workforce_job_profile_id)
            .first()
        )
    if workforce_profile is None:
        workforce_profile = (
            db.query(models.WorkforceJobProfile)
            .filter(models.WorkforceJobProfile.employer_id == job.employer_id)
            .filter(models.WorkforceJobProfile.title == job.title)
            .filter(models.WorkforceJobProfile.department == job.department)
            .first()
        )
    if workforce_profile is None:
        workforce_profile = models.WorkforceJobProfile(employer_id=job.employer_id, title=job.title, department=job.department)
        db.add(workforce_profile)
        db.flush()

    workforce_profile.title = job.title
    workforce_profile.department = job.department
    workforce_profile.category_prof = job.contract_type
    workforce_profile.classification_index = profile.classification
    workforce_profile.notes = profile.mission_summary
    workforce_profile.required_skills_json = json_dump(
        [
            {"type": "technical", "label": item}
            for item in _json_load(profile.technical_skills_json, [])
        ]
        + [
            {"type": "behavioral", "label": item}
            for item in _json_load(profile.behavioral_skills_json, [])
        ]
        + [
            {"type": "language", "label": item}
            for item in _json_load(profile.languages_json, [])
        ]
    )
    profile.workforce_job_profile_id = workforce_profile.id
    return workforce_profile


def _build_candidate_download_name(path_value: str, fallback: str) -> str:
    path = Path(path_value) if path_value else None
    return path.name if path else fallback


def _next_worker_matricule(db: Session, employer_id: int) -> str:
    prefix = f"REC{employer_id:03d}"
    existing = db.query(models.Worker.matricule).filter(models.Worker.matricule.like(f"{prefix}-%")).all()
    max_seq = 0
    for (value,) in existing:
        if not value:
            continue
        try:
            max_seq = max(max_seq, int(str(value).split("-")[-1]))
        except ValueError:
            continue
    return f"{prefix}-{max_seq + 1:04d}"


@router.get("/library-items", response_model=list[schemas.RecruitmentLibraryItemOut])
def list_library_items(
    employer_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    scoped_employer_id = employer_id
    if user_has_any_role(db, user, "employeur"):
        scoped_employer_id = user.employer_id
    items = get_library_entries(db, employer_id=scoped_employer_id, category=category)
    return [_serialize_library_item(item) for item in items]


@router.post("/library-items", response_model=schemas.RecruitmentLibraryItemOut)
def create_library_item(
    payload: schemas.RecruitmentLibraryItemCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    if payload.employer_id is not None:
        _assert_employer_scope(db, user, payload.employer_id)
    item = models.RecruitmentLibraryItem(
        employer_id=payload.employer_id,
        category=payload.category,
        label=payload.label,
        normalized_key=_normalize_key(payload.label),
        description=payload.description,
        payload_json=json_dump(payload.payload),
        is_system=False,
        is_active=payload.is_active,
    )
    db.add(item)
    db.flush()
    if payload.employer_id:
        _log_activity(
            db,
            employer_id=payload.employer_id,
            user=user,
            event_type="recruitment.library.create",
            message=f"Ã‰lÃ©ment de bibliothÃ¨que crÃ©Ã©: {payload.label}",
            payload={"category": payload.category},
        )
    record_audit(
        db,
        actor=user,
        action="recruitment.library.create",
        entity_type="recruitment_library_item",
        entity_id=item.id,
        route="/recruitment/library-items",
        employer_id=payload.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_library_item(item)


@router.put("/library-items/{item_id}", response_model=schemas.RecruitmentLibraryItemOut)
def update_library_item(
    item_id: int,
    payload: schemas.RecruitmentLibraryItemUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.RecruitmentLibraryItem).filter(models.RecruitmentLibraryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")
    if item.is_system:
        raise HTTPException(status_code=400, detail="System library items are read-only")
    if item.employer_id is not None:
        _assert_employer_scope(db, user, item.employer_id)

    before = {"label": item.label, "description": item.description, "is_active": item.is_active}
    update_data = payload.model_dump(exclude_unset=True)
    if "label" in update_data and update_data["label"]:
        item.normalized_key = _normalize_key(update_data["label"])
    if "payload" in update_data and update_data["payload"] is not None:
        update_data["payload_json"] = json_dump(update_data.pop("payload"))
    for field, value in update_data.items():
        setattr(item, field, value)

    record_audit(
        db,
        actor=user,
        action="recruitment.library.update",
        entity_type="recruitment_library_item",
        entity_id=item.id,
        route=f"/recruitment/library-items/{item_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_library_item(item)


@router.post("/job-assistant/suggest", response_model=schemas.RecruitmentJobAssistantOut)
def get_job_assistant_suggestions(
    payload: schemas.RecruitmentJobAssistantRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    if payload.employer_id is not None and user_has_any_role(db, user, "employeur"):
        _assert_employer_scope(db, user, payload.employer_id)
    suggestions = suggest_job_profile(
        db,
        title=payload.title,
        department=payload.department,
        description=payload.description,
        employer_id=payload.employer_id if not user_has_any_role(db, user, "employeur") else user.employer_id,
        contract_type=payload.contract_type,
        sector=payload.sector,
        mode=payload.mode,
        version=payload.version,
        focus_block=payload.focus_block,
    )
    return schemas.RecruitmentJobAssistantOut(**suggestions)


@router.get("/jobs", response_model=list[schemas.RecruitmentJobPostingOut])
def list_job_postings(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.RecruitmentJobPosting)
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.RecruitmentJobPosting.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.RecruitmentJobPosting.employer_id == employer_id)
    items = query.order_by(models.RecruitmentJobPosting.updated_at.desc()).all()
    return [_serialize_job(item) for item in items]


@router.post("/jobs", response_model=schemas.RecruitmentJobPostingOut)
def create_job_posting(
    payload: schemas.RecruitmentJobPostingCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    payload_data = payload.model_dump()
    item = models.RecruitmentJobPosting(
        employer_id=payload_data["employer_id"],
        title=payload_data["title"],
        department=payload_data.get("department"),
        location=payload_data.get("location"),
        contract_type=payload_data.get("contract_type") or "CDI",
        status=payload_data.get("status") or "draft",
        salary_range=payload_data.get("salary_range"),
        description=payload_data.get("description"),
        skills_required=payload_data.get("skills_required"),
        publish_channels_json=json_dump(payload_data.get("publish_channels") or []),
        publish_status=payload_data.get("publish_status") or "draft",
        publish_logs_json=json_dump(payload_data.get("publish_logs") or []),
    )
    db.add(item)
    db.flush()
    _log_activity(
        db,
        employer_id=item.employer_id,
        user=user,
        event_type="recruitment.job.create",
        message=f"Fiche de poste crÃ©Ã©e: {item.title}",
        job_posting_id=item.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.create",
        entity_type="recruitment_job_posting",
        entity_id=item.id,
        route="/recruitment/jobs",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_job(item)


@router.put("/jobs/{job_id}", response_model=schemas.RecruitmentJobPostingOut)
def update_job_posting(
    job_id: int,
    payload: schemas.RecruitmentJobPostingUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, item.employer_id)
    before = {"title": item.title, "status": item.status, "department": item.department}
    update_data = payload.model_dump(exclude_unset=True)
    if "publish_channels" in update_data:
        item.publish_channels_json = json_dump(update_data.pop("publish_channels") or [])
    if "publish_logs" in update_data:
        item.publish_logs_json = json_dump(update_data.pop("publish_logs") or [])
    for field, value in update_data.items():
        setattr(item, field, value)
    _log_activity(
        db,
        employer_id=item.employer_id,
        user=user,
        event_type="recruitment.job.update",
        message=f"Fiche de poste mise Ã  jour: {item.title}",
        job_posting_id=item.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.update",
        entity_type="recruitment_job_posting",
        entity_id=item.id,
        route=f"/recruitment/jobs/{job_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_job(item)


@router.get("/publication-channels", response_model=list[schemas.RecruitmentPublicationChannelOut])
def list_publication_channels(
    employer_id: int = Query(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PUBLICATION_READ_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    items = get_or_create_publication_channels(db, employer_id)
    db.commit()
    for item in items:
        db.refresh(item)
    return [_serialize_publication_channel(item) for item in items]


@router.put("/publication-channels/{channel_type}", response_model=schemas.RecruitmentPublicationChannelOut)
def upsert_publication_channel(
    channel_type: str,
    payload: schemas.RecruitmentPublicationChannelUpsert,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PUBLICATION_WRITE_ROLES)),
):
    normalized_channel_type = (channel_type or "").strip().lower()
    if normalized_channel_type != payload.channel_type.strip().lower():
        raise HTTPException(status_code=400, detail="Channel type mismatch")
    _assert_employer_scope(db, user, payload.company_id)
    items = get_or_create_publication_channels(db, payload.company_id)
    item = next((row for row in items if row.channel_type == normalized_channel_type), None)
    if not item:
        raise HTTPException(status_code=404, detail="Publication channel not found")
    existing_config = publication_json_load(item.config_json, {})
    item.is_active = payload.is_active
    item.default_publish = payload.default_publish
    item.config_json = json_dump(merge_channel_config(existing_config, payload.config.model_dump()))
    record_audit(
        db,
        actor=user,
        action="recruitment.publication_channel.update",
        entity_type="recruitment_publication_channel",
        entity_id=item.id,
        route=f"/recruitment/publication-channels/{normalized_channel_type}",
        employer_id=payload.company_id,
        after={"channel_type": item.channel_type, "is_active": item.is_active, "default_publish": item.default_publish},
    )
    db.commit()
    db.refresh(item)
    return _serialize_publication_channel(item)


@router.get("/jobs/{job_id}/profile", response_model=schemas.RecruitmentJobProfileOut)
def get_job_profile(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    if not _json_load(profile.contract_guidance_json, {}):
        profile.contract_guidance_json = json_dump(build_contract_guidance(job, _serialize_profile(profile).model_dump()))
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.put("/jobs/{job_id}/profile", response_model=schemas.RecruitmentJobProfileOut)
def upsert_job_profile(
    job_id: int,
    payload: schemas.RecruitmentJobProfileUpsert,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    before = _serialize_profile_dict(profile)
    _apply_profile_payload(profile, payload)
    profile.contract_guidance_json = json_dump(build_contract_guidance(job, _serialize_profile(profile).model_dump()))
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.profile.update",
        message=f"Fiche de poste enrichie: {job.title}",
        job_posting_id=job.id,
        payload={"workflow_status": profile.workflow_status},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.profile.update",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/profile",
        employer_id=job.employer_id,
        before=before,
        after=profile,
    )
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.get("/jobs/{job_id}/contract-guidance", response_model=schemas.RecruitmentContractGuidanceOut)
def get_contract_guidance(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    payload = build_contract_guidance(job, _serialize_profile(profile).model_dump())
    profile.contract_guidance_json = json_dump(payload)
    db.commit()
    return schemas.RecruitmentContractGuidanceOut(**payload)


@router.post("/jobs/{job_id}/sync-workforce-profile", response_model=schemas.RecruitmentJobProfileOut)
def sync_job_to_workforce_profile(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    workforce_profile = _sync_workforce_job_profile(db, job=job, profile=profile)
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.workforce_profile.synced",
        message=f"Fiche de poste RH synchronisee: {job.title}",
        job_posting_id=job.id,
        payload={"workforce_job_profile_id": workforce_profile.id},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.workforce_profile.synced",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/sync-workforce-profile",
        employer_id=job.employer_id,
        after={"workforce_job_profile_id": workforce_profile.id},
    )
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.post("/jobs/{job_id}/submit-for-validation", response_model=schemas.RecruitmentJobProfileOut)
def submit_job_for_validation(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    if profile.workflow_status not in {"validated", "validated_with_observations", "archived"}:
        profile.workflow_status = "en_revue_inspecteur"
    if job.status not in {"published", "published_non_conforme"}:
        job.status = "en_revue_inspecteur"
    profile.submitted_to_inspection_at = datetime.now(timezone.utc)
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.validation.requested",
        message=f"Offre signalee a l'inspection pour controle a posteriori: {job.title}",
        job_posting_id=job.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.validation.requested",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/submit-for-validation",
        employer_id=job.employer_id,
        after=profile,
    )
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.post("/jobs/{job_id}/validation", response_model=schemas.RecruitmentJobProfileOut)
def validate_job_profile(
    job_id: int,
    payload: schemas.RecruitmentValidationIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh")),
):
    job = _get_job_or_404(db, job_id)
    profile = _get_or_create_profile(db, job)
    if not payload.approved and not (payload.comment or "").strip():
        raise HTTPException(status_code=422, detail="A comment is required when validation is refused")
    profile.workflow_status = "validated_with_observations" if payload.approved and (payload.comment or "").strip() else ("validated" if payload.approved else "rejected")
    profile.validation_comment = payload.comment
    profile.validated_by_user_id = user.id
    profile.validated_at = datetime.now(timezone.utc)
    profile.last_reviewed_at = datetime.now(timezone.utc)
    if payload.approved:
        job.status = "published" if job.status in {"published", "published_non_validated", "en_revue_inspecteur"} else "validated"
    else:
        job.status = "published_non_conforme" if job.status in {"published", "published_non_validated", "en_revue_inspecteur"} else "rejected"
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.validation.done",
        message=f"Fiche de poste {'validÃ©e' if payload.approved else 'rejetÃ©e'}: {job.title}",
        job_posting_id=job.id,
        payload={"comment": payload.comment},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.validation.done",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/validation",
        employer_id=job.employer_id,
        after=profile,
    )
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.post("/jobs/{job_id}/attachments/upload", response_model=schemas.RecruitmentJobProfileOut)
async def upload_job_submission_attachment(
    job_id: int,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)

    safe_name = sanitize_filename_part(Path(attachment.filename or "piece_jointe").name)
    storage_name = f"recruitment/jobs/{job.id}/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{safe_name}"
    stored_path = save_upload_file(attachment.file, filename=storage_name)
    attachments = _json_load(profile.submission_attachments_json, [])
    attachments.append(
        {
            "name": attachment.filename,
            "content_type": attachment.content_type,
            "path": stored_path,
        }
    )
    profile.submission_attachments_json = json_dump(attachments)

    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.attachment.uploaded",
        message=f"Piece jointe ajoutee a l'offre: {job.title}",
        job_posting_id=job.id,
        payload={"filename": attachment.filename},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.attachment.uploaded",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/attachments/upload",
        employer_id=job.employer_id,
        after={"filename": attachment.filename},
    )
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.post("/jobs/{job_id}/generate-announcement", response_model=schemas.RecruitmentAnnouncementOut)
def generate_announcement(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    payload = build_announcement_payload(job, _serialize_profile(profile).model_dump())
    profile.announcement_title = payload["title"]
    profile.announcement_body = payload["web_body"]
    profile.announcement_status = "ready"
    profile.announcement_slug = payload["slug"]
    profile.announcement_share_pack_json = json_dump(payload)
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.announcement.generated",
        message=f"Annonce gÃ©nÃ©rÃ©e depuis la fiche: {job.title}",
        job_posting_id=job.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.announcement.generated",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/generate-announcement",
        employer_id=job.employer_id,
        after=profile,
    )
    db.commit()
    return schemas.RecruitmentAnnouncementOut(**payload)


@router.post("/jobs/{job_id}/publish", response_model=schemas.RecruitmentPublishResultOut)
def publish_job(
    job_id: int,
    payload: schemas.RecruitmentPublishRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PUBLICATION_WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    try:
        logs = publish_job_channels(
            db,
            job=job,
            profile=profile,
            user=user,
            requested_channels=payload.channels,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.published",
        message=f"Annonce publiée sur {len(logs)} canal(aux): {job.title}",
        job_posting_id=job.id,
        payload={"publish_status": job.publish_status, "channels": [item.channel for item in logs]},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.job.published",
        entity_type="recruitment_job_profile",
        entity_id=profile.id,
        route=f"/recruitment/jobs/{job_id}/publish",
        employer_id=job.employer_id,
        after=profile,
    )
    db.commit()
    db.refresh(profile)
    db.refresh(job)
    for item in logs:
        db.refresh(item)
    return schemas.RecruitmentPublishResultOut(
        job=_serialize_job(job),
        profile=_serialize_profile(profile),
        channel_results=[_serialize_publication_log(item) for item in logs],
    )


@router.get("/jobs/{job_id}/publication-logs", response_model=list[schemas.RecruitmentPublicationLogOut])
def list_job_publication_logs(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    items = (
        db.query(models.RecruitmentPublicationLog)
        .filter(models.RecruitmentPublicationLog.job_id == job_id)
        .order_by(models.RecruitmentPublicationLog.timestamp.desc(), models.RecruitmentPublicationLog.id.desc())
        .all()
    )
    return [_serialize_publication_log(item) for item in items]


@router.post("/jobs/{job_id}/publish/retry", response_model=schemas.RecruitmentPublishResultOut)
def retry_publish_job_channel(
    job_id: int,
    payload: schemas.RecruitmentPublishRetryRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PUBLICATION_WRITE_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    try:
        logs = publish_job_channels(
            db,
            job=job,
            profile=profile,
            user=user,
            requested_channels=[payload.channel],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.job.publish.retry",
        message=f"Relance de publication sur {payload.channel}: {job.title}",
        job_posting_id=job.id,
        payload={"channel": payload.channel},
    )
    db.commit()
    db.refresh(job)
    db.refresh(profile)
    for item in logs:
        db.refresh(item)
    return schemas.RecruitmentPublishResultOut(
        job=_serialize_job(job),
        profile=_serialize_profile(profile),
        channel_results=[_serialize_publication_log(item) for item in logs],
    )


@router.get("/jobs/{job_id}/share-pack", response_model=schemas.RecruitmentAnnouncementOut)
def get_share_pack(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    payload = _json_load(profile.announcement_share_pack_json, {})
    if not payload:
        payload = build_announcement_payload(job, _serialize_profile(profile).model_dump())
        profile.announcement_title = payload["title"]
        profile.announcement_body = payload["web_body"]
        profile.announcement_slug = payload["slug"]
        profile.announcement_share_pack_json = json_dump(payload)
        db.commit()
    return schemas.RecruitmentAnnouncementOut(**payload)


@router.get("/jobs/{job_id}/announcement-pdf")
def get_announcement_pdf(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    job = _get_job_or_404(db, job_id)
    _assert_employer_scope(db, user, job.employer_id)
    profile = _get_or_create_profile(db, job)
    payload = _json_load(profile.announcement_share_pack_json, {})
    if not payload:
        payload = build_announcement_payload(job, _serialize_profile(profile).model_dump())
    subtitle = f"{job.department or ''} | {job.location or ''} | {job.contract_type}".strip(" |")
    pdf_bytes = build_recruitment_announcement_pdf(payload["title"], subtitle or "Annonce de recrutement", payload["web_body"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="annonce_{job.id}.pdf"'},
    )


@router.get("/candidates", response_model=list[schemas.RecruitmentCandidateOut])
def list_candidates(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.RecruitmentCandidate)
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.RecruitmentCandidate.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.RecruitmentCandidate.employer_id == employer_id)
    return query.order_by(models.RecruitmentCandidate.updated_at.desc()).all()


@router.post("/candidates", response_model=schemas.RecruitmentCandidateOut)
def create_candidate(
    payload: schemas.RecruitmentCandidateCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.RecruitmentCandidate(**payload.model_dump())
    db.add(item)
    db.flush()
    _log_activity(
        db,
        employer_id=item.employer_id,
        user=user,
        event_type="recruitment.candidate.create",
        message=f"Candidat crÃ©Ã©: {item.first_name} {item.last_name}",
        candidate_id=item.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.candidate.create",
        entity_type="recruitment_candidate",
        entity_id=item.id,
        route="/recruitment/candidates",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/candidates/upload", response_model=schemas.RecruitmentCandidateUploadOut)
async def upload_candidate(
    employer_id: int = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    education_level: str = Form(""),
    experience_years: float = Form(0.0),
    source: str = Form(""),
    status: str = Form("new"),
    summary: str = Form(""),
    job_posting_id: Optional[int] = Form(None),
    cv_file: UploadFile = File(...),
    attachments: Optional[list[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, employer_id)
    if job_posting_id:
        job = _get_job_or_404(db, job_posting_id)
        if job.employer_id != employer_id:
            raise HTTPException(status_code=400, detail="Job posting does not belong to employer")

    cv_bytes = await cv_file.read()
    extracted_text = extract_text_from_upload(cv_file.filename or "cv", cv_bytes)
    parsed_profile = parse_candidate_profile(extracted_text, db=db, employer_id=employer_id)

    candidate = models.RecruitmentCandidate(
        employer_id=employer_id,
        first_name=(first_name or "").strip() or "PrÃ©nom Ã  confirmer",
        last_name=(last_name or "").strip() or "Nom Ã  confirmer",
        email=(email or "").strip() or parsed_profile.get("email") or f"candidate-{datetime.now(timezone.utc).timestamp():.0f}@placeholder.local",
        phone=(phone or "").strip() or parsed_profile.get("phone"),
        education_level=(education_level or "").strip() or parsed_profile.get("education_level"),
        experience_years=experience_years or parsed_profile.get("experience_years") or 0.0,
        source=(source or "").strip() or "upload",
        status=status or "new",
        summary=(summary or "").strip() or parsed_profile.get("summary"),
    )
    db.add(candidate)
    db.flush()

    safe_base = sanitize_filename_part(f"{candidate.last_name}_{candidate.first_name}_{candidate.id}")
    cv_name = sanitize_filename_part(Path(cv_file.filename or "cv").name)
    cv_relative_path = f"recruitment/{employer_id}/candidates/{candidate.id}/{safe_base}_cv_{cv_name}"
    save_upload_file(BytesIO(cv_bytes), filename=cv_relative_path)
    candidate.cv_file_path = cv_relative_path

    attachment_entries = []
    for attachment in attachments or []:
        attachment_bytes = await attachment.read()
        attachment_name = sanitize_filename_part(Path(attachment.filename or "piece").name)
        attachment_path = f"recruitment/{employer_id}/candidates/{candidate.id}/{safe_base}_attachment_{attachment_name}"
        save_upload_file(BytesIO(attachment_bytes), filename=attachment_path)
        attachment_entries.append(
            {
                "original_name": attachment.filename or attachment_name,
                "storage_path": attachment_path,
            }
        )

    asset = models.RecruitmentCandidateAsset(
        candidate_id=candidate.id,
        resume_original_name=cv_file.filename,
        resume_storage_path=cv_relative_path,
        attachments_json=json_dump(attachment_entries),
        raw_extract_text=extracted_text,
        parsed_profile_json=json_dump(parsed_profile),
        parsing_status="parsed" if extracted_text else "stored",
    )
    db.add(asset)
    db.flush()

    application_id = None
    if job_posting_id:
        existing_application = db.query(models.RecruitmentApplication).filter(
            models.RecruitmentApplication.job_posting_id == job_posting_id,
            models.RecruitmentApplication.candidate_id == candidate.id,
        ).first()
        if not existing_application:
            application = models.RecruitmentApplication(
                job_posting_id=job_posting_id,
                candidate_id=candidate.id,
                stage="applied",
                score=None,
                notes="Candidature crÃ©Ã©e depuis le formulaire avec CV et piÃ¨ces jointes.",
            )
            db.add(application)
            db.flush()
            application_id = application.id
            _log_activity(
                db,
                employer_id=employer_id,
                user=user,
                event_type="recruitment.application.create",
                message="Candidature crÃ©Ã©e depuis le dÃ©pÃ´t de CV",
                job_posting_id=job_posting_id,
                candidate_id=candidate.id,
                application_id=application.id,
            )
        else:
            application_id = existing_application.id

    _log_activity(
        db,
        employer_id=employer_id,
        user=user,
        event_type="recruitment.candidate.upload",
        message=f"CV original dÃ©posÃ© pour {candidate.first_name} {candidate.last_name}",
        candidate_id=candidate.id,
        application_id=application_id,
        payload={"cv_file": cv_file.filename, "attachments_count": len(attachment_entries)},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.candidate.upload",
        entity_type="recruitment_candidate_asset",
        entity_id=asset.id,
        route="/recruitment/candidates/upload",
        employer_id=employer_id,
        after=asset,
    )
    db.commit()
    db.refresh(candidate)
    db.refresh(asset)
    return schemas.RecruitmentCandidateUploadOut(
        candidate=candidate,
        asset=_serialize_asset(asset),
        application_id=application_id,
    )


@router.put("/candidates/{candidate_id}", response_model=schemas.RecruitmentCandidateOut)
def update_candidate(
    candidate_id: int,
    payload: schemas.RecruitmentCandidateUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = _get_candidate_or_404(db, candidate_id)
    _assert_employer_scope(db, user, item.employer_id)
    before = {"first_name": item.first_name, "last_name": item.last_name, "status": item.status}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    _log_activity(
        db,
        employer_id=item.employer_id,
        user=user,
        event_type="recruitment.candidate.update",
        message=f"Candidat mis Ã  jour: {item.first_name} {item.last_name}",
        candidate_id=item.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.candidate.update",
        entity_type="recruitment_candidate",
        entity_id=item.id,
        route=f"/recruitment/candidates/{candidate_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/candidates/{candidate_id}/asset", response_model=schemas.RecruitmentCandidateAssetOut)
def get_candidate_asset(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    candidate = _get_candidate_or_404(db, candidate_id)
    _assert_employer_scope(db, user, candidate.employer_id)
    asset = db.query(models.RecruitmentCandidateAsset).filter(models.RecruitmentCandidateAsset.candidate_id == candidate_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Candidate asset not found")
    return _serialize_asset(asset)


@router.get("/candidates/{candidate_id}/resume")
def download_candidate_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    candidate = _get_candidate_or_404(db, candidate_id)
    _assert_employer_scope(db, user, candidate.employer_id)
    asset = db.query(models.RecruitmentCandidateAsset).filter(models.RecruitmentCandidateAsset.candidate_id == candidate_id).first()
    if not asset or not asset.resume_storage_path:
        raise HTTPException(status_code=404, detail="Resume not found")
    path = Path(asset.resume_storage_path)
    if not path.is_absolute():
        path = Path("uploads") / asset.resume_storage_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume file missing")
    return FileResponse(path, filename=_build_candidate_download_name(asset.resume_storage_path, asset.resume_original_name or "cv"))


@router.get("/applications", response_model=list[schemas.RecruitmentApplicationOut])
def list_applications(
    employer_id: Optional[int] = Query(None),
    job_posting_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.RecruitmentApplication).join(
        models.RecruitmentJobPosting,
        models.RecruitmentApplication.job_posting_id == models.RecruitmentJobPosting.id,
    )
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.RecruitmentJobPosting.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.RecruitmentJobPosting.employer_id == employer_id)
    if job_posting_id:
        query = query.filter(models.RecruitmentApplication.job_posting_id == job_posting_id)
    return query.order_by(models.RecruitmentApplication.updated_at.desc()).all()


@router.post("/applications", response_model=schemas.RecruitmentApplicationOut)
def create_application(
    payload: schemas.RecruitmentApplicationCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    job = _get_job_or_404(db, payload.job_posting_id)
    candidate = _get_candidate_or_404(db, payload.candidate_id)
    if job.employer_id != candidate.employer_id:
        raise HTTPException(status_code=400, detail="Candidate and job posting must belong to the same employer")
    _assert_employer_scope(db, user, job.employer_id)
    item = models.RecruitmentApplication(**payload.model_dump())
    db.add(item)
    db.flush()
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.application.create",
        message=f"Candidature crÃ©Ã©e pour {candidate.first_name} {candidate.last_name}",
        job_posting_id=job.id,
        candidate_id=candidate.id,
        application_id=item.id,
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.application.create",
        entity_type="recruitment_application",
        entity_id=item.id,
        route="/recruitment/applications",
        employer_id=job.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/applications/{application_id}", response_model=schemas.RecruitmentApplicationOut)
def update_application(
    application_id: int,
    payload: schemas.RecruitmentApplicationUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = _get_application_or_404(db, application_id)
    job = _get_job_or_404(db, item.job_posting_id)
    _assert_employer_scope(db, user, job.employer_id)
    before = {"stage": item.stage, "score": item.score}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    candidate = _get_candidate_or_404(db, item.candidate_id)
    if payload.stage:
        candidate.status = payload.stage
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.application.update",
        message=f"Candidature mise Ã  jour: Ã©tape {item.stage}",
        job_posting_id=job.id,
        candidate_id=item.candidate_id,
        application_id=item.id,
        payload={"score": item.score},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.application.update",
        entity_type="recruitment_application",
        entity_id=item.id,
        route=f"/recruitment/applications/{application_id}",
        employer_id=job.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/applications/{application_id}/activities", response_model=list[schemas.RecruitmentActivityOut])
def list_application_activities(
    application_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    application = _get_application_or_404(db, application_id)
    job = _get_job_or_404(db, application.job_posting_id)
    _assert_employer_scope(db, user, job.employer_id)
    items = db.query(models.RecruitmentActivity).filter(
        models.RecruitmentActivity.application_id == application_id
    ).order_by(models.RecruitmentActivity.created_at.desc()).all()
    return [_serialize_activity(item) for item in items]


@router.get("/applications/{application_id}/interviews", response_model=list[schemas.RecruitmentInterviewOut])
def list_interviews(
    application_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    application = _get_application_or_404(db, application_id)
    job = _get_job_or_404(db, application.job_posting_id)
    _assert_employer_scope(db, user, job.employer_id)
    items = db.query(models.RecruitmentInterview).filter(
        models.RecruitmentInterview.application_id == application_id
    ).order_by(models.RecruitmentInterview.round_number.asc(), models.RecruitmentInterview.scheduled_at.asc()).all()
    return [_serialize_interview(item) for item in items]


@router.post("/applications/{application_id}/interviews", response_model=schemas.RecruitmentInterviewOut)
def create_interview(
    application_id: int,
    payload: schemas.RecruitmentInterviewCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    application = _get_application_or_404(db, application_id)
    job = _get_job_or_404(db, application.job_posting_id)
    _assert_employer_scope(db, user, job.employer_id)
    item = models.RecruitmentInterview(
        application_id=application_id,
        round_number=payload.round_number,
        round_label=payload.round_label,
        interview_type=payload.interview_type,
        scheduled_at=payload.scheduled_at,
        interviewer_user_id=payload.interviewer_user_id,
        interviewer_name=payload.interviewer_name,
        status=payload.status,
        score_total=payload.score_total,
        scorecard_json=json_dump(payload.scorecard),
        notes=payload.notes,
        recommendation=payload.recommendation,
    )
    db.add(item)
    application.stage = "interview"
    _get_candidate_or_404(db, application.candidate_id).status = "interview"
    db.flush()
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.interview.create",
        message=f"Entretien planifiÃ© ({item.round_label})",
        job_posting_id=job.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        interview_id=item.id,
        payload={"scheduled_at": payload.scheduled_at.isoformat() if payload.scheduled_at else None},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.interview.create",
        entity_type="recruitment_interview",
        entity_id=item.id,
        route=f"/recruitment/applications/{application_id}/interviews",
        employer_id=job.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_interview(item)


@router.put("/interviews/{interview_id}", response_model=schemas.RecruitmentInterviewOut)
def update_interview(
    interview_id: int,
    payload: schemas.RecruitmentInterviewUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.RecruitmentInterview).filter(models.RecruitmentInterview.id == interview_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Interview not found")
    application = _get_application_or_404(db, item.application_id)
    job = _get_job_or_404(db, application.job_posting_id)
    _assert_employer_scope(db, user, job.employer_id)
    before = {"status": item.status, "score_total": item.score_total}
    update_data = payload.model_dump(exclude_unset=True)
    if "scorecard" in update_data and update_data["scorecard"] is not None:
        item.scorecard_json = json_dump(update_data.pop("scorecard"))
    for field, value in update_data.items():
        setattr(item, field, value)
    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.interview.update",
        message=f"Entretien mis Ã  jour ({item.round_label})",
        job_posting_id=job.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        interview_id=item.id,
        payload={"status": item.status, "recommendation": item.recommendation},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.interview.update",
        entity_type="recruitment_interview",
        entity_id=item.id,
        route=f"/recruitment/interviews/{interview_id}",
        employer_id=job.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_interview(item)


@router.post("/applications/{application_id}/decision", response_model=schemas.RecruitmentDecisionOut)
def record_decision(
    application_id: int,
    payload: schemas.RecruitmentDecisionIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    application = _get_application_or_404(db, application_id)
    job = _get_job_or_404(db, application.job_posting_id)
    _assert_employer_scope(db, user, job.employer_id)
    candidate = _get_candidate_or_404(db, application.candidate_id)
    item = db.query(models.RecruitmentDecision).filter(models.RecruitmentDecision.application_id == application_id).first()
    if not item:
        item = models.RecruitmentDecision(application_id=application_id)
        db.add(item)
        db.flush()

    before = {"decision_status": item.decision_status, "shortlist_rank": item.shortlist_rank}
    item.shortlist_rank = payload.shortlist_rank
    item.decision_status = payload.decision_status
    item.decision_comment = payload.decision_comment
    item.decided_by_user_id = user.id
    item.decided_at = datetime.now(timezone.utc)

    if payload.shortlist_rank is not None:
        application.stage = "shortlist"
        candidate.status = "shortlist"
    if payload.decision_status in {"offer_sent", "offer_accepted"}:
        application.stage = "offer"
        candidate.status = "offer"
    if payload.decision_status in {"rejected", "rejected_after_interview"}:
        application.stage = "rejected"
        candidate.status = "rejected"

    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.decision.recorded",
        message=f"DÃ©cision enregistrÃ©e: {payload.decision_status}",
        job_posting_id=job.id,
        candidate_id=candidate.id,
        application_id=application.id,
        payload={"shortlist_rank": payload.shortlist_rank, "comment": payload.decision_comment},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.decision.recorded",
        entity_type="recruitment_decision",
        entity_id=item.id,
        route=f"/recruitment/applications/{application_id}/decision",
        employer_id=job.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_decision(item)

@router.post("/applications/{application_id}/convert-to-worker", response_model=schemas.RecruitmentConversionOut)
def convert_application_to_worker(
    application_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    application = _get_application_or_404(db, application_id)
    job = _get_job_or_404(db, application.job_posting_id)
    candidate = _get_candidate_or_404(db, application.candidate_id)
    _assert_employer_scope(db, user, job.employer_id)

    decision = db.query(models.RecruitmentDecision).filter(models.RecruitmentDecision.application_id == application_id).first()
    if not decision:
        decision = models.RecruitmentDecision(application_id=application_id, decision_status="offer_accepted")
        db.add(decision)
        db.flush()
    if decision.converted_worker_id:
        return schemas.RecruitmentConversionOut(
            worker_id=decision.converted_worker_id,
            contract_draft_id=decision.contract_draft_id,
            decision_id=decision.id,
        )

    profile = _get_or_create_profile(db, job)
    employer = db.query(models.Employer).filter(models.Employer.id == job.employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    worker = models.Worker(
        employer_id=job.employer_id,
        matricule=_next_worker_matricule(db, job.employer_id),
        nom=candidate.last_name,
        prenom=candidate.first_name,
        telephone=candidate.phone,
        email=candidate.email,
        date_embauche=profile.desired_start_date or date.today(),
        nature_contrat=job.contract_type,
        etablissement=job.location,
        departement=job.department,
        poste=job.title,
        categorie_prof=profile.classification,
        indice=profile.classification,
        salaire_base=profile.salary_min or 0.0,
        vhm=173.33,
        horaire_hebdo=40.0,
        salaire_horaire=(profile.salary_min or 0.0) / 173.33 if profile.salary_min else 0.0,
        solde_conge_initial=0.0,
        mode_paiement="Virement",
    )
    if not can_manage_worker(db, user, employer_id=worker.employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    db.add(worker)
    db.flush()

    contract_content = build_contract_draft_html(candidate, job, employer, _serialize_profile(profile).model_dump())
    contract = models.CustomContract(
        worker_id=worker.id,
        employer_id=job.employer_id,
        title=f"Promesse / Brouillon de contrat - {job.title}",
        content=contract_content,
        template_type="employment_contract",
        is_default=True,
    )
    db.add(contract)
    db.flush()
    contract_version = create_contract_version(
        db,
        contract=contract,
        worker=worker,
        actor=user,
        source_module="recruitment_conversion",
        status="draft",
        effective_date=worker.date_embauche,
        salary_amount=profile.salary_min or worker.salaire_base,
        classification_index=profile.classification or worker.indice,
    )

    application.stage = "hired"
    candidate.status = "hired"
    decision.decision_status = "hired"
    decision.decided_by_user_id = user.id
    decision.decided_at = datetime.now(timezone.utc)
    decision.converted_worker_id = worker.id
    decision.contract_draft_id = contract.id
    sync_worker_master_data(
        db,
        worker,
        candidate=candidate,
        application=application,
        decision=decision,
        job_posting=job,
        job_profile=profile,
        contract=contract,
        contract_version=contract_version,
    )
    sync_employer_register(db, job.employer_id)

    _log_activity(
        db,
        employer_id=job.employer_id,
        user=user,
        event_type="recruitment.conversion.completed",
        message=f"Candidat converti en salariÃ©: {candidate.first_name} {candidate.last_name}",
        job_posting_id=job.id,
        candidate_id=candidate.id,
        application_id=application.id,
        payload={"worker_id": worker.id, "contract_draft_id": contract.id},
    )
    record_audit(
        db,
        actor=user,
        action="recruitment.conversion.completed",
        entity_type="worker",
        entity_id=worker.id,
        route=f"/recruitment/applications/{application_id}/convert-to-worker",
        employer_id=job.employer_id,
        worker_id=worker.id,
        after=worker,
    )
    db.commit()
    return schemas.RecruitmentConversionOut(worker_id=worker.id, contract_draft_id=contract.id, decision_id=decision.id)


