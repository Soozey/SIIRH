from collections import defaultdict
from typing import Mapping

from sqlalchemy.orm import Query, Session
from sqlalchemy import and_, or_

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
        unit = db.query(models.OrganizationalUnit).filter(
            models.OrganizationalUnit.id == int(raw_value),
            models.OrganizationalUnit.employer_id == employer_id,
            models.OrganizationalUnit.level == level,
            models.OrganizationalUnit.is_active == True,
        ).first()
        if unit:
            candidates.add(str(unit.id))
            candidates.add(unit.name)
        return list(candidates)

    matching_units = db.query(models.OrganizationalUnit.id).filter(
        models.OrganizationalUnit.employer_id == employer_id,
        models.OrganizationalUnit.level == level,
        models.OrganizationalUnit.name == raw_value,
        models.OrganizationalUnit.is_active == True,
    ).all()
    for unit_id, in matching_units:
        candidates.add(str(unit_id))

    return list(candidates)


def _resolve_selected_node(
    db: Session,
    *,
    employer_id: int,
    level: str,
    raw_value: str,
):
    query = db.query(models.OrganizationalUnit).filter(
        models.OrganizationalUnit.employer_id == employer_id,
        models.OrganizationalUnit.level == level,
        models.OrganizationalUnit.is_active == True,
    )

    if raw_value.isdigit():
        return query.filter(models.OrganizationalUnit.id == int(raw_value)).first()

    return query.filter(models.OrganizationalUnit.name == raw_value).first()


def _collect_descendants(
    db: Session,
    *,
    employer_id: int,
    root_node_id: int,
) -> list[models.OrganizationalUnit]:
    nodes = db.query(models.OrganizationalUnit).filter(
        models.OrganizationalUnit.employer_id == employer_id,
        models.OrganizationalUnit.is_active == True,
    ).all()

    by_parent: dict[int | None, list[models.OrganizationalNode]] = defaultdict(list)
    by_id: dict[int, models.OrganizationalNode] = {}
    for node in nodes:
        by_parent[node.parent_id].append(node)
        by_id[node.id] = node

    root = by_id.get(root_node_id)
    if not root:
        return []

    collected = [root]
    stack = [root.id]

    while stack:
        current_id = stack.pop()
        children = by_parent.get(current_id, [])
        for child in children:
            collected.append(child)
            stack.append(child.id)

    return collected


def _build_hierarchical_predicate(
    db: Session,
    *,
    employer_id: int,
    level: str,
    raw_value: str,
):
    selected_node = _resolve_selected_node(
        db,
        employer_id=employer_id,
        level=level,
        raw_value=raw_value,
    )
    if not selected_node:
        return None

    descendants = _collect_descendants(
        db,
        employer_id=employer_id,
        root_node_id=selected_node.id,
    )

    unit_ids: set[int] = set()
    for node in descendants:
        unit_ids.add(node.id)

    predicates = [models.Worker.organizational_unit_id.in_(list(unit_ids))]

    if not predicates:
        return None

    return or_(*predicates)


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
        hierarchical_predicate = _build_hierarchical_predicate(
            db,
            employer_id=employer_id,
            level=level,
            raw_value=raw_value,
        )
        if hierarchical_predicate is not None:
            query = query.filter(
                or_(
                    hierarchical_predicate,
                    and_(
                        models.Worker.organizational_unit_id.is_(None),
                        getattr(models.Worker, worker_field).in_(candidates),
                    ),
                )
            )
            continue
        query = query.filter(getattr(models.Worker, worker_field).in_(candidates))

    return query
