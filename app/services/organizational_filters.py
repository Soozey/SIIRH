from typing import Mapping

from sqlalchemy.orm import Query, Session

from .. import models


_WORKER_FILTER_FIELDS = {
    "etablissement": ("etablissement", "etablissement"),
    "departement": ("departement", "departement"),
    "service": ("service", "service"),
    "unite": ("unite", "unite"),
}


def normalize_filter_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_filter_candidates(
    db: Session,
    *,
    employer_id: int,
    level: str,
    raw_value: str,
) -> list[str]:
    candidates = {raw_value}

    if raw_value.isdigit():
        node = db.query(models.OrganizationalNode).filter(
            models.OrganizationalNode.id == int(raw_value),
            models.OrganizationalNode.employer_id == employer_id,
            models.OrganizationalNode.level == level,
        ).first()
        if node:
            candidates.add(str(node.id))
            candidates.add(node.name)
        return list(candidates)

    matching_nodes = db.query(models.OrganizationalNode.id).filter(
        models.OrganizationalNode.employer_id == employer_id,
        models.OrganizationalNode.level == level,
        models.OrganizationalNode.name == raw_value,
    ).all()
    for node_id, in matching_nodes:
        candidates.add(str(node_id))

    return list(candidates)


def apply_worker_hierarchy_filters(
    query: Query,
    db: Session,
    *,
    employer_id: int,
    filters: Mapping[str, object] | None,
) -> Query:
    if not filters:
        return query

    for filter_key, (worker_field, level) in _WORKER_FILTER_FIELDS.items():
        raw_value = normalize_filter_value(filters.get(filter_key))
        if not raw_value:
            continue
        candidates = _resolve_filter_candidates(
            db,
            employer_id=employer_id,
            level=level,
            raw_value=raw_value,
        )
        query = query.filter(getattr(models.Worker, worker_field).in_(candidates))

    return query
