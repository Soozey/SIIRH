import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from .. import models
from .email_publication_service import publish_email_campaign
from .external_api_publication_service import publish_external_api
from .facebook_service import publish_facebook_post
from .internal_portal_service import publish_internal_job
from .linkedin_service import publish_linkedin_post
from .recruitment_assistant_service import build_announcement_payload


SUPPORTED_PUBLICATION_CHANNELS = ("facebook", "linkedin", "site_interne", "email", "api_externe")
SECRET_CONFIG_FIELDS = {"access_token", "api_key", "api_secret"}


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_load(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def mask_channel_config(raw_config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    masked: dict[str, Any] = {}
    configured_secret_fields: list[str] = []
    for key, value in raw_config.items():
        if key in SECRET_CONFIG_FIELDS:
            if value not in (None, ""):
                configured_secret_fields.append(key)
                masked[key] = "********"
            continue
        masked[key] = value
    return masked, configured_secret_fields


def merge_channel_config(existing_config: dict[str, Any], incoming_config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing_config)
    for key, value in incoming_config.items():
        if key in SECRET_CONFIG_FIELDS:
            if value not in (None, ""):
                merged[key] = value
            continue
        if isinstance(value, list):
            merged[key] = [item for item in value if item not in (None, "", [])]
        elif value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def get_or_create_publication_channels(db: Session, company_id: int) -> list[models.RecruitmentPublicationChannel]:
    existing = {
        item.channel_type: item
        for item in db.query(models.RecruitmentPublicationChannel)
        .filter(models.RecruitmentPublicationChannel.company_id == company_id)
        .all()
    }
    created = False
    for channel_type in SUPPORTED_PUBLICATION_CHANNELS:
        if channel_type in existing:
            continue
        item = models.RecruitmentPublicationChannel(
            company_id=company_id,
            channel_type=channel_type,
            is_active=(channel_type == "site_interne"),
            default_publish=(channel_type == "site_interne"),
            config_json=json_dump(
                {
                    "page_name": "" if channel_type != "facebook" else "Page entreprise",
                    "organization_id": "" if channel_type != "linkedin" else "",
                    "sender_email": "" if channel_type != "email" else "",
                    "audience_emails": [],
                    "webhook_url": "" if channel_type != "api_externe" else "",
                    "notes": "",
                }
            ),
        )
        db.add(item)
        existing[channel_type] = item
        created = True
    if created:
        db.flush()
    return [existing[channel_type] for channel_type in SUPPORTED_PUBLICATION_CHANNELS]


def ensure_share_pack(
    db: Session,
    *,
    job: models.RecruitmentJobPosting,
    profile: models.RecruitmentJobProfile,
) -> dict[str, Any]:
    share_pack = json_load(profile.announcement_share_pack_json, {})
    if share_pack:
        return share_pack
    profile_dict = {
        "announcement_title": profile.announcement_title,
        "mission_summary": profile.mission_summary,
        "main_activities": json_load(profile.main_activities_json, []),
        "technical_skills": json_load(profile.technical_skills_json, []),
        "behavioral_skills": json_load(profile.behavioral_skills_json, []),
        "education_level": profile.education_level,
        "experience_required": profile.experience_required,
        "languages": json_load(profile.languages_json, []),
        "tools": json_load(profile.tools_json, []),
        "certifications": json_load(profile.certifications_json, []),
        "benefits": json_load(profile.benefits_json, []),
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
        "application_deadline": profile.application_deadline.isoformat() if profile.application_deadline else None,
    }
    share_pack = build_announcement_payload(job, profile_dict)
    profile.announcement_title = share_pack["title"]
    profile.announcement_body = share_pack["web_body"]
    profile.announcement_slug = share_pack["slug"]
    profile.announcement_share_pack_json = json_dump(share_pack)
    if profile.announcement_status == "draft":
        profile.announcement_status = "ready"
    db.flush()
    return share_pack


def resolve_target_channels(
    job: models.RecruitmentJobPosting,
    available_channels: Iterable[models.RecruitmentPublicationChannel],
    requested_channels: Optional[list[str]] = None,
) -> list[models.RecruitmentPublicationChannel]:
    requested = [item for item in (requested_channels or []) if item in SUPPORTED_PUBLICATION_CHANNELS]
    if not requested:
        mapped_channels = [item for item in json_load(job.publish_channels_json, []) if item in SUPPORTED_PUBLICATION_CHANNELS]
        requested = mapped_channels
    active_channels = [item for item in available_channels if item.is_active]
    if not requested:
        requested = [item.channel_type for item in active_channels if item.default_publish] or [item.channel_type for item in active_channels]
    return [item for item in available_channels if item.channel_type in requested and item.is_active]


def collect_candidate_emails(db: Session, employer_id: int) -> list[str]:
    rows = (
        db.query(models.RecruitmentCandidate.email)
        .filter(models.RecruitmentCandidate.employer_id == employer_id)
        .all()
    )
    return sorted({str(email).strip() for (email,) in rows if str(email or "").strip()})


def publish_to_channel(
    *,
    db: Session,
    channel: models.RecruitmentPublicationChannel,
    job: models.RecruitmentJobPosting,
    share_pack: dict[str, Any],
) -> dict[str, Any]:
    config = json_load(channel.config_json, {})
    if channel.channel_type == "facebook":
        return publish_facebook_post(config=config, share_pack=share_pack)
    if channel.channel_type == "linkedin":
        return publish_linkedin_post(config=config, share_pack=share_pack)
    if channel.channel_type == "site_interne":
        return publish_internal_job(job_id=job.id, share_pack=share_pack)
    if channel.channel_type == "email":
        recipient_emails = collect_candidate_emails(db, job.employer_id)
        return publish_email_campaign(config=config, share_pack=share_pack, recipient_emails=recipient_emails)
    if channel.channel_type == "api_externe":
        return publish_external_api(config=config, share_pack=share_pack)
    return {"status": "failed", "message": "Canal non supporté.", "details": {"channel": channel.channel_type}}


def append_publish_log_summary(job: models.RecruitmentJobPosting, log: models.RecruitmentPublicationLog) -> None:
    history = json_load(job.publish_logs_json, [])
    history.append(
        {
            "id": log.id,
            "channel": log.channel,
            "status": log.status,
            "message": log.message,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
    )
    job.publish_logs_json = json_dump(history[-100:])


def publish_job_channels(
    db: Session,
    *,
    job: models.RecruitmentJobPosting,
    profile: models.RecruitmentJobProfile,
    user: models.AppUser,
    requested_channels: Optional[list[str]] = None,
) -> list[models.RecruitmentPublicationLog]:
    available_channels = get_or_create_publication_channels(db, job.employer_id)
    target_channels = resolve_target_channels(job, available_channels, requested_channels=requested_channels)
    if not target_channels:
        raise ValueError("Aucun canal de publication actif ou sélectionné n'est disponible.")

    share_pack = ensure_share_pack(db, job=job, profile=profile)
    created_logs: list[models.RecruitmentPublicationLog] = []
    attempted_channels: list[str] = []

    for channel in target_channels:
        attempted_channels.append(channel.channel_type)
        result = publish_to_channel(db=db, channel=channel, job=job, share_pack=share_pack)
        log = models.RecruitmentPublicationLog(
            job_id=job.id,
            channel=channel.channel_type,
            status=result.get("status", "failed"),
            message=result.get("message"),
            details_json=json_dump(result.get("details", {})),
            triggered_by_user_id=user.id if user else None,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(log)
        db.flush()
        append_publish_log_summary(job, log)
        created_logs.append(log)

    job.publish_channels_json = json_dump(attempted_channels)
    if all(item.status == "success" for item in created_logs):
        job.publish_status = "published"
    elif any(item.status == "success" for item in created_logs):
        job.publish_status = "partial"
    else:
        job.publish_status = "failed"

    profile.announcement_status = "published" if any(item.status == "success" for item in created_logs) else "failed"
    if profile.workflow_status not in {"validated", "validated_with_observations"}:
        profile.workflow_status = "published_non_validated" if any(item.status == "success" for item in created_logs) else profile.workflow_status
    if not profile.submitted_to_inspection_at:
        profile.submitted_to_inspection_at = datetime.now(timezone.utc)
    job.status = "published" if any(item.status == "success" for item in created_logs) else "publication_failed"
    db.flush()
    return created_logs
