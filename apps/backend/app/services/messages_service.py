from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from .. import models
from ..security import user_has_any_role
from .employee_portal_service import json_load, next_sequence


INTERNAL_BROADCAST_ROLES = {"admin", "rh", "direction", "juridique", "audit", "employeur", "recrutement"}


def next_internal_channel_code(db: Session, employer_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m")
    return next_sequence(
        db,
        model=models.InternalMessageChannel,
        field_name="channel_code",
        prefix=f"MSG-{employer_id:03d}-{today}",
    )


def channel_query_for_user(db: Session, user: models.AppUser, employer_id: int):
    query = db.query(models.InternalMessageChannel).filter(models.InternalMessageChannel.employer_id == employer_id)
    if user_has_any_role(db, user, *INTERNAL_BROADCAST_ROLES):
        if user_has_any_role(db, user, "employeur") and user.employer_id != employer_id:
            return query.filter(False)
        return query
    member_channel_ids = (
        db.query(models.InternalMessageChannelMember.channel_id)
        .filter(
            models.InternalMessageChannelMember.user_id == user.id,
            models.InternalMessageChannelMember.is_active.is_(True),
        )
    )
    return query.filter(models.InternalMessageChannel.id.in_(member_channel_ids))


def build_messages_dashboard(db: Session, *, user: models.AppUser, employer_id: int) -> dict[str, Any]:
    channels = channel_query_for_user(db, user, employer_id).order_by(models.InternalMessageChannel.updated_at.desc()).all()
    unread_messages = 0
    channel_items = []

    for channel in channels:
        member = (
            db.query(models.InternalMessageChannelMember)
            .filter(
                models.InternalMessageChannelMember.channel_id == channel.id,
                models.InternalMessageChannelMember.user_id == user.id,
            )
            .first()
        )
        last_read_at = member.last_read_at if member else None
        unread_count = (
            db.query(models.InternalMessage)
            .filter(
                models.InternalMessage.channel_id == channel.id,
                models.InternalMessage.author_user_id != user.id,
                models.InternalMessage.created_at > (last_read_at or datetime(2000, 1, 1)),
            )
            .count()
        )
        unread_messages += unread_count
        channel_items.append(
            {
                "id": channel.id,
                "channel_code": channel.channel_code,
                "employer_id": channel.employer_id,
                "created_by_user_id": channel.created_by_user_id,
                "channel_type": channel.channel_type,
                "title": channel.title,
                "description": channel.description,
                "visibility": channel.visibility,
                "ack_required": channel.ack_required,
                "status": channel.status,
                "member_count": len(channel.members),
                "unread_count": unread_count,
                "created_at": channel.created_at,
                "updated_at": channel.updated_at,
            }
        )

    visible_notices = (
        db.query(models.InternalNotice)
        .filter(
            models.InternalNotice.employer_id == employer_id,
            models.InternalNotice.status == "published",
        )
        .order_by(models.InternalNotice.published_at.desc().nullslast(), models.InternalNotice.created_at.desc())
        .all()
    )
    notices = []
    pending_acknowledgements = 0
    for notice in visible_notices:
        if notice.audience_role and not user_has_any_role(db, user, notice.audience_role):
            continue
        ack = (
            db.query(models.InternalNoticeAcknowledgement)
            .filter(
                models.InternalNoticeAcknowledgement.notice_id == notice.id,
                models.InternalNoticeAcknowledgement.user_id == user.id,
            )
            .first()
        )
        acknowledged = ack is not None
        if notice.ack_required and not acknowledged:
            pending_acknowledgements += 1
        notices.append(
            {
                "id": notice.id,
                "employer_id": notice.employer_id,
                "created_by_user_id": notice.created_by_user_id,
                "title": notice.title,
                "body": notice.body,
                "notice_type": notice.notice_type,
                "audience_role": notice.audience_role,
                "status": notice.status,
                "ack_required": notice.ack_required,
                "attachments": json_load(notice.attachments_json, []),
                "published_at": notice.published_at,
                "expires_at": notice.expires_at,
                "created_at": notice.created_at,
                "updated_at": notice.updated_at,
                "acknowledged_by_current_user": acknowledged,
            }
        )

    online_cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    online_rows = (
        db.query(models.AuthSession.user_id, models.AppUser)
        .join(models.AppUser, models.AuthSession.user_id == models.AppUser.id)
        .filter(
            models.AuthSession.revoked_at.is_(None),
            models.AuthSession.expires_at >= datetime.now(timezone.utc),
            models.AuthSession.last_seen_at >= online_cutoff,
            models.AppUser.employer_id == employer_id,
            models.AppUser.is_active.is_(True),
        )
        .all()
    )
    online_users = len({user_row.id for _user_id, user_row in online_rows if not user_has_any_role(db, user_row, "inspecteur")})

    return {
        "online_users": online_users,
        "active_channels": len(channel_items),
        "unread_messages": unread_messages,
        "pending_acknowledgements": pending_acknowledgements,
        "notices": notices[:10],
        "channels": channel_items[:20],
    }


