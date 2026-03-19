import json
from datetime import datetime
from typing import Any, Optional

from .. import models


def _normalize(value: Any):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items()}
    if hasattr(value, "__table__"):
        payload = {}
        for column in value.__table__.columns:
            payload[column.name] = _normalize(getattr(value, column.name))
        return payload
    return str(value)


def serialize_model(instance: Any) -> Optional[str]:
    normalized = _normalize(instance)
    if normalized is None:
        return None
    return json.dumps(normalized, ensure_ascii=False)


def record_audit(
    db,
    *,
    actor: Optional[models.AppUser],
    action: str,
    entity_type: str,
    entity_id: Any,
    route: Optional[str] = None,
    employer_id: Optional[int] = None,
    worker_id: Optional[int] = None,
    before: Any = None,
    after: Any = None,
):
    entry = models.AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_role=actor.role_code if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        route=route,
        employer_id=employer_id,
        worker_id=worker_id,
        before_json=serialize_model(before),
        after_json=serialize_model(after),
    )
    db.add(entry)
    return entry
