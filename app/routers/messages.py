from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_employer, require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.employee_portal_service import json_dump, json_load
from ..services.file_storage import sanitize_filename_part, save_upload_file
from ..services.messages_service import build_messages_dashboard, channel_query_for_user, next_internal_channel_code


router = APIRouter(prefix="/messages", tags=["messages"])

MESSAGE_ROLES = ("admin", "rh", "employeur", "manager", "employe", "inspecteur", "juridique", "direction", "recrutement", "audit")
BROADCAST_ROLES = {"admin", "rh", "direction", "juridique", "audit", "employeur", "recrutement"}


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh", "direction", "juridique", "audit", "recrutement"):
        return
    if user_has_any_role(db, user, "inspecteur") and can_access_employer(db, user, employer_id):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == employer_id:
        return
    if user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _serialize_user(user: models.AppUser | None) -> Optional[schemas.AppUserLightOut]:
    if not user:
        return None
    return schemas.AppUserLightOut.model_validate(user)


def _is_inspector_user(db: Session, user: models.AppUser) -> bool:
    return user_has_any_role(db, user, "inspecteur")


def _get_channel_or_404(db: Session, channel_id: int) -> models.InternalMessageChannel:
    item = db.query(models.InternalMessageChannel).filter(models.InternalMessageChannel.id == channel_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internal channel not found")
    return item


def _assert_channel_access(db: Session, user: models.AppUser, channel: models.InternalMessageChannel) -> None:
    _assert_employer_scope(db, user, channel.employer_id)
    if user_has_any_role(db, user, *BROADCAST_ROLES):
        return
    member = (
        db.query(models.InternalMessageChannelMember)
        .filter(
            models.InternalMessageChannelMember.channel_id == channel.id,
            models.InternalMessageChannelMember.user_id == user.id,
            models.InternalMessageChannelMember.is_active.is_(True),
        )
        .first()
    )
    if member:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _touch_membership_read_state(db: Session, user: models.AppUser, channel_id: int) -> None:
    membership = (
        db.query(models.InternalMessageChannelMember)
        .filter(
            models.InternalMessageChannelMember.channel_id == channel_id,
            models.InternalMessageChannelMember.user_id == user.id,
        )
        .first()
    )
    if membership:
        membership.last_read_at = datetime.now(timezone.utc)


def _serialize_channel(db: Session, user: models.AppUser, channel: models.InternalMessageChannel) -> schemas.InternalMessageChannelOut:
    membership = (
        db.query(models.InternalMessageChannelMember)
        .filter(
            models.InternalMessageChannelMember.channel_id == channel.id,
            models.InternalMessageChannelMember.user_id == user.id,
        )
        .first()
    )
    unread_count = (
        db.query(models.InternalMessage)
        .filter(
            models.InternalMessage.channel_id == channel.id,
            models.InternalMessage.author_user_id != user.id,
            models.InternalMessage.created_at > (membership.last_read_at if membership and membership.last_read_at else datetime(2000, 1, 1)),
        )
        .count()
    )
    return schemas.InternalMessageChannelOut(
        id=channel.id,
        channel_code=channel.channel_code,
        employer_id=channel.employer_id,
        created_by_user_id=channel.created_by_user_id,
        channel_type=channel.channel_type,
        title=channel.title,
        description=channel.description,
        visibility=channel.visibility,
        ack_required=channel.ack_required,
        status=channel.status,
        member_count=len(channel.members),
        unread_count=unread_count,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def _serialize_message(db: Session, user: models.AppUser, item: models.InternalMessage) -> schemas.InternalMessageOut:
    receipt = (
        db.query(models.InternalMessageReceipt)
        .filter(
            models.InternalMessageReceipt.message_id == item.id,
            models.InternalMessageReceipt.user_id == user.id,
        )
        .first()
    )
    return schemas.InternalMessageOut(
        id=item.id,
        channel_id=item.channel_id,
        employer_id=item.employer_id,
        author_user_id=item.author_user_id,
        message_type=item.message_type,
        body=item.body,
        attachments=json_load(item.attachments_json, []),
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
        author=_serialize_user(item.author),
        receipt_status=receipt.status if receipt else None,
    )


def _serialize_receipt(item: models.InternalMessageReceipt) -> dict:
    return {
        "id": item.id,
        "message_id": item.message_id,
        "user_id": item.user_id,
        "status": item.status,
        "read_at": item.read_at,
        "acknowledged_at": item.acknowledged_at,
        "user": _serialize_user(item.user).model_dump() if item.user else None,
    }


def _serialize_notice(db: Session, user: models.AppUser, item: models.InternalNotice) -> schemas.InternalNoticeOut:
    ack = (
        db.query(models.InternalNoticeAcknowledgement)
        .filter(
            models.InternalNoticeAcknowledgement.notice_id == item.id,
            models.InternalNoticeAcknowledgement.user_id == user.id,
        )
        .first()
    )
    return schemas.InternalNoticeOut(
        id=item.id,
        employer_id=item.employer_id,
        created_by_user_id=item.created_by_user_id,
        title=item.title,
        body=item.body,
        notice_type=item.notice_type,
        audience_role=item.audience_role,
        status=item.status,
        ack_required=item.ack_required,
        attachments=json_load(item.attachments_json, []),
        published_at=item.published_at,
        expires_at=item.expires_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        acknowledged_by_current_user=ack is not None,
    )


@router.get("/dashboard", response_model=schemas.InternalMessagesDashboardOut)
def get_messages_dashboard(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    target_employer_id = employer_id or user.employer_id
    if not target_employer_id:
        raise HTTPException(status_code=400, detail="employer_id is required")
    _assert_employer_scope(db, user, target_employer_id)
    return schemas.InternalMessagesDashboardOut.model_validate(build_messages_dashboard(db, user=user, employer_id=target_employer_id))


@router.get("/available-users", response_model=list[schemas.AppUserLightOut])
def list_available_users(
    employer_id: Optional[int] = Query(None),
    role_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    target_employer_id = employer_id or user.employer_id
    if not target_employer_id:
        raise HTTPException(status_code=400, detail="employer_id is required")
    _assert_employer_scope(db, user, target_employer_id)
    query = db.query(models.AppUser).filter(
        models.AppUser.employer_id == target_employer_id,
        models.AppUser.is_active.is_(True),
    )
    users = query.order_by(models.AppUser.full_name.asc(), models.AppUser.username.asc()).all()
    filtered = []
    for item in users:
        if _is_inspector_user(db, item):
            continue
        if role_code and not user_has_any_role(db, item, role_code):
            continue
        filtered.append(item)
    return [schemas.AppUserLightOut.model_validate(item) for item in filtered]


@router.get("/channels", response_model=list[schemas.InternalMessageChannelOut])
def list_channels(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    target_employer_id = employer_id or user.employer_id
    if not target_employer_id:
        raise HTTPException(status_code=400, detail="employer_id is required")
    channels = channel_query_for_user(db, user, target_employer_id).order_by(models.InternalMessageChannel.updated_at.desc()).all()
    return [_serialize_channel(db, user, channel) for channel in channels]


@router.post("/channels", response_model=schemas.InternalMessageChannelOut)
def create_channel(
    payload: schemas.InternalMessageChannelCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=422, detail="Channel title is required")
    _assert_employer_scope(db, user, payload.employer_id)
    normalized_title = payload.title.strip()
    duplicate = (
        db.query(models.InternalMessageChannel.id)
        .filter(
            models.InternalMessageChannel.employer_id == payload.employer_id,
            models.InternalMessageChannel.status == "active",
            models.InternalMessageChannel.title == normalized_title,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="A channel with this name already exists for this employer")
    channel = models.InternalMessageChannel(
        channel_code=next_internal_channel_code(db, payload.employer_id),
        employer_id=payload.employer_id,
        created_by_user_id=user.id,
        channel_type=payload.channel_type,
        title=normalized_title,
        description=payload.description.strip() if payload.description else None,
        visibility=payload.visibility,
        ack_required=payload.ack_required,
        status="active",
    )
    db.add(channel)
    db.flush()

    member_ids = {user.id, *payload.member_user_ids}
    members = (
        db.query(models.AppUser)
        .filter(
            models.AppUser.id.in_(member_ids),
            models.AppUser.employer_id == payload.employer_id,
            models.AppUser.is_active.is_(True),
        )
        .all()
    )
    members = [member for member in members if not _is_inspector_user(db, member)]
    for member in members:
        db.add(
            models.InternalMessageChannelMember(
                channel_id=channel.id,
                user_id=member.id,
                member_role="owner" if member.id == user.id else "member",
                is_active=True,
            )
        )

    record_audit(
        db,
        actor=user,
        action="messages.channel.create",
        entity_type="internal_message_channel",
        entity_id=channel.id,
        route="/messages/channels",
        employer_id=channel.employer_id,
        after=channel,
    )
    db.commit()
    db.refresh(channel)
    return _serialize_channel(db, user, channel)


@router.get("/channels/{channel_id}/members", response_model=list[schemas.InternalMessageChannelMemberOut])
def list_channel_members(
    channel_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_channel_access(db, user, channel)
    items = (
        db.query(models.InternalMessageChannelMember)
        .filter(models.InternalMessageChannelMember.channel_id == channel_id)
        .order_by(models.InternalMessageChannelMember.joined_at.asc())
        .all()
    )
    return [
        schemas.InternalMessageChannelMemberOut(
            id=item.id,
            channel_id=item.channel_id,
            user_id=item.user_id,
            member_role=item.member_role,
            is_active=item.is_active,
            last_read_at=item.last_read_at,
            joined_at=item.joined_at,
            user=_serialize_user(item.user),
        )
        for item in items
    ]


@router.post("/channels/{channel_id}/members", response_model=schemas.InternalMessageChannelMemberOut)
def add_channel_member(
    channel_id: int,
    payload: schemas.InternalMessageChannelMemberCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "inspecteur", "direction", "juridique", "recrutement")),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_employer_scope(db, user, channel.employer_id)
    target_user = (
        db.query(models.AppUser)
        .filter(
            models.AppUser.id == payload.user_id,
            models.AppUser.employer_id == channel.employer_id,
            models.AppUser.is_active.is_(True),
        )
        .first()
    )
    if target_user and _is_inspector_user(db, target_user):
        target_user = None
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found for this employer")

    item = (
        db.query(models.InternalMessageChannelMember)
        .filter(
            models.InternalMessageChannelMember.channel_id == channel_id,
            models.InternalMessageChannelMember.user_id == payload.user_id,
        )
        .first()
    )
    if item:
        item.is_active = True
        item.member_role = payload.member_role
    else:
        item = models.InternalMessageChannelMember(
            channel_id=channel_id,
            user_id=payload.user_id,
            member_role=payload.member_role,
            is_active=True,
        )
        db.add(item)

    record_audit(
        db,
        actor=user,
        action="messages.channel.member.add",
        entity_type="internal_message_channel_member",
        entity_id=f"{channel_id}:{payload.user_id}",
        route=f"/messages/channels/{channel_id}/members",
        employer_id=channel.employer_id,
        after={"channel_id": channel_id, "user_id": payload.user_id, "member_role": payload.member_role},
    )
    db.commit()
    db.refresh(item)
    return schemas.InternalMessageChannelMemberOut(
        id=item.id,
        channel_id=item.channel_id,
        user_id=item.user_id,
        member_role=item.member_role,
        is_active=item.is_active,
        last_read_at=item.last_read_at,
        joined_at=item.joined_at,
        user=_serialize_user(target_user),
    )


@router.get("/channels/{channel_id}/messages", response_model=list[schemas.InternalMessageOut])
def list_channel_messages(
    channel_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_channel_access(db, user, channel)
    items = (
        db.query(models.InternalMessage)
        .filter(models.InternalMessage.channel_id == channel_id)
        .order_by(models.InternalMessage.created_at.asc())
        .all()
    )
    for item in items:
        if item.author_user_id == user.id:
            continue
        receipt = (
            db.query(models.InternalMessageReceipt)
            .filter(
                models.InternalMessageReceipt.message_id == item.id,
                models.InternalMessageReceipt.user_id == user.id,
            )
            .first()
        )
        if not receipt:
            db.add(
                models.InternalMessageReceipt(
                    message_id=item.id,
                    user_id=user.id,
                    status="read",
                    read_at=datetime.now(timezone.utc),
                )
            )
        elif not receipt.read_at:
            receipt.status = "read"
            receipt.read_at = datetime.now(timezone.utc)
    _touch_membership_read_state(db, user, channel_id)
    db.commit()
    return [_serialize_message(db, user, item) for item in items]


@router.post("/channels/{channel_id}/read")
def mark_channel_read(
    channel_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_channel_access(db, user, channel)
    items = (
        db.query(models.InternalMessage)
        .filter(
            models.InternalMessage.channel_id == channel_id,
            models.InternalMessage.author_user_id != user.id,
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for item in items:
        receipt = (
            db.query(models.InternalMessageReceipt)
            .filter(
                models.InternalMessageReceipt.message_id == item.id,
                models.InternalMessageReceipt.user_id == user.id,
            )
            .first()
        )
        if not receipt:
            db.add(models.InternalMessageReceipt(message_id=item.id, user_id=user.id, status="read", read_at=now))
        elif not receipt.read_at:
            receipt.status = "read"
            receipt.read_at = now
    _touch_membership_read_state(db, user, channel_id)
    db.commit()
    return {"ok": True, "channel_id": channel_id}


@router.get("/channels/{channel_id}/read-receipts")
def list_channel_read_receipts(
    channel_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "inspecteur", "direction", "juridique", "audit", "recrutement")),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_channel_access(db, user, channel)
    receipts = (
        db.query(models.InternalMessageReceipt)
        .join(models.InternalMessage, models.InternalMessage.id == models.InternalMessageReceipt.message_id)
        .filter(models.InternalMessage.channel_id == channel_id)
        .order_by(models.InternalMessageReceipt.read_at.desc().nullslast(), models.InternalMessageReceipt.id.desc())
        .all()
    )
    return [_serialize_receipt(item) for item in receipts]


@router.post("/channels/{channel_id}/messages", response_model=schemas.InternalMessageOut)
def create_channel_message(
    channel_id: int,
    payload: schemas.InternalMessageCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_channel_access(db, user, channel)
    if not payload.body or not payload.body.strip():
        raise HTTPException(status_code=422, detail="Message body is required")

    item = models.InternalMessage(
        channel_id=channel.id,
        employer_id=channel.employer_id,
        author_user_id=user.id,
        message_type=payload.message_type,
        body=payload.body.strip(),
        attachments_json=json_dump(payload.attachments),
        status="sent",
    )
    db.add(item)
    channel.updated_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=user,
        action="messages.message.create",
        entity_type="internal_message",
        entity_id=f"pending:{channel_id}",
        route=f"/messages/channels/{channel_id}/messages",
        employer_id=channel.employer_id,
        after={"message_type": payload.message_type, "channel_id": channel_id},
    )
    db.commit()
    db.refresh(item)
    return _serialize_message(db, user, item)


@router.post("/channels/{channel_id}/messages/upload", response_model=schemas.InternalMessageOut)
async def create_channel_message_upload(
    channel_id: int,
    body: str = Form(...),
    message_type: str = Form("message"),
    attachments: Optional[list[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    channel = _get_channel_or_404(db, channel_id)
    _assert_channel_access(db, user, channel)

    uploaded_attachments = []
    for attachment in attachments or []:
        safe_name = sanitize_filename_part(Path(attachment.filename or "piece_jointe").name)
        storage_name = (
            f"internal_messages/{channel.channel_code}/"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{safe_name}"
        )
        save_upload_file(attachment.file, filename=storage_name)
        uploaded_attachments.append(
            {
                "name": attachment.filename,
                "content_type": attachment.content_type,
                "path": storage_name,
            }
        )

    item = models.InternalMessage(
        channel_id=channel.id,
        employer_id=channel.employer_id,
        author_user_id=user.id,
        message_type=message_type,
        body=body,
        attachments_json=json_dump(uploaded_attachments),
        status="sent",
    )
    db.add(item)
    channel.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _serialize_message(db, user, item)


@router.post("/entries/{message_id}/ack", response_model=schemas.InternalMessageOut)
def acknowledge_message(
    message_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    item = db.query(models.InternalMessage).filter(models.InternalMessage.id == message_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internal message not found")
    channel = _get_channel_or_404(db, item.channel_id)
    _assert_channel_access(db, user, channel)

    receipt = (
        db.query(models.InternalMessageReceipt)
        .filter(
            models.InternalMessageReceipt.message_id == message_id,
            models.InternalMessageReceipt.user_id == user.id,
        )
        .first()
    )
    if not receipt:
        receipt = models.InternalMessageReceipt(
            message_id=message_id,
            user_id=user.id,
            status="acknowledged",
            read_at=datetime.now(timezone.utc),
            acknowledged_at=datetime.now(timezone.utc),
        )
        db.add(receipt)
    else:
        receipt.status = "acknowledged"
        receipt.read_at = receipt.read_at or datetime.now(timezone.utc)
        receipt.acknowledged_at = datetime.now(timezone.utc)

    record_audit(
        db,
        actor=user,
        action="messages.message.ack",
        entity_type="internal_message",
        entity_id=item.id,
        route=f"/messages/entries/{message_id}/ack",
        employer_id=item.employer_id,
        after={"status": "acknowledged"},
    )
    db.commit()
    return _serialize_message(db, user, item)


@router.get("/notices", response_model=list[schemas.InternalNoticeOut])
def list_notices(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    target_employer_id = employer_id or user.employer_id
    if not target_employer_id:
        raise HTTPException(status_code=400, detail="employer_id is required")
    _assert_employer_scope(db, user, target_employer_id)
    items = (
        db.query(models.InternalNotice)
        .filter(models.InternalNotice.employer_id == target_employer_id)
        .order_by(models.InternalNotice.published_at.desc().nullslast(), models.InternalNotice.created_at.desc())
        .all()
    )
    visible = []
    for item in items:
        if item.audience_role and not user_has_any_role(db, user, item.audience_role) and not user_has_any_role(db, user, *BROADCAST_ROLES):
            continue
        visible.append(_serialize_notice(db, user, item))
    return visible


@router.post("/notices", response_model=schemas.InternalNoticeOut)
def create_notice(
    payload: schemas.InternalNoticeCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "direction", "juridique", "recrutement")),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.InternalNotice(
        employer_id=payload.employer_id,
        created_by_user_id=user.id,
        title=payload.title,
        body=payload.body,
        notice_type=payload.notice_type,
        audience_role=payload.audience_role,
        status="published",
        ack_required=payload.ack_required,
        attachments_json=json_dump(payload.attachments),
        published_at=datetime.now(timezone.utc),
        expires_at=payload.expires_at,
    )
    db.add(item)
    record_audit(
        db,
        actor=user,
        action="messages.notice.create",
        entity_type="internal_notice",
        entity_id="pending",
        route="/messages/notices",
        employer_id=item.employer_id,
        after={"title": payload.title, "audience_role": payload.audience_role},
    )
    db.commit()
    db.refresh(item)
    return _serialize_notice(db, user, item)


@router.post("/notices/{notice_id}/ack", response_model=schemas.InternalNoticeOut)
def acknowledge_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_ROLES)),
):
    item = db.query(models.InternalNotice).filter(models.InternalNotice.id == notice_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internal notice not found")
    _assert_employer_scope(db, user, item.employer_id)
    if item.audience_role and not user_has_any_role(db, user, item.audience_role) and not user_has_any_role(db, user, *BROADCAST_ROLES):
        raise HTTPException(status_code=403, detail="Forbidden")

    ack = (
        db.query(models.InternalNoticeAcknowledgement)
        .filter(
            models.InternalNoticeAcknowledgement.notice_id == notice_id,
            models.InternalNoticeAcknowledgement.user_id == user.id,
        )
        .first()
    )
    if not ack:
        ack = models.InternalNoticeAcknowledgement(
            notice_id=notice_id,
            user_id=user.id,
            status="acknowledged",
            acknowledged_at=datetime.now(timezone.utc),
        )
        db.add(ack)

    record_audit(
        db,
        actor=user,
        action="messages.notice.ack",
        entity_type="internal_notice",
        entity_id=notice_id,
        route=f"/messages/notices/{notice_id}/ack",
        employer_id=item.employer_id,
        after={"status": "acknowledged"},
    )
    db.commit()
    return _serialize_notice(db, user, item)


