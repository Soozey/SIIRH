from typing import Any, List, Literal, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..config.config import get_db
from ..security import (
    PAYROLL_WRITE_ROLES,
    READ_PAYROLL_ROLES,
    WRITE_RH_ROLES,
    can_access_employer,
    can_access_worker,
    require_roles,
)
from ..services.audit_service import record_audit
from ..services.organizational_filters import apply_worker_hierarchy_filters
from ..services.tabular_io import (
    build_column_mapping,
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    issues_to_csv,
    read_tabular_bytes,
)

router = APIRouter(
    prefix="/primes",
    tags=["primes"],
    responses={404: {"description": "Not found"}},
)


class PrimeBase(BaseModel):
    label: str
    description: Optional[str] = None
    formula_nombre: Optional[str] = None
    formula_base: Optional[str] = None
    formula_taux: Optional[str] = None
    operation_1: Optional[str] = "*"
    operation_2: Optional[str] = "*"
    is_active: bool = True
    is_cotisable: bool = True
    is_imposable: bool = True
    target_mode: Literal["global", "segment", "individual"] = "global"
    target_worker_ids: List[int] = []
    excluded_worker_ids: List[int] = []
    target_organizational_node_ids: List[int] = []
    target_organizational_unit_ids: List[int] = []


class PrimeCreate(PrimeBase):
    employer_id: int


class PrimeOut(PrimeBase):
    id: int
    employer_id: int
    model_config = {"from_attributes": True}


class AssociationRequest(BaseModel):
    worker_id: int
    prime_id: int
    is_active: bool = True
    link_type: Literal["include", "exclude"] = "include"


class PrimeValuesOut(BaseModel):
    worker_id: int
    matricule: str
    nom: str
    prenom: str
    prime_13: float
    prime1: float
    prime2: float
    prime3: float
    prime4: float
    prime5: float


class PrimeValuesUpdate(BaseModel):
    prime_13: float
    prime1: float
    prime2: float
    prime3: float
    prime4: float
    prime5: float


def _ensure_employer_access(db: Session, user: models.AppUser, employer_id: int) -> None:
    if not can_access_employer(db, user, employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")


def _get_worker_or_404(db: Session, worker_id: int) -> models.Worker:
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _prime_query(db: Session):
    return db.query(models.Prime).options(
        selectinload(models.Prime.worker_links),
        selectinload(models.Prime.organizational_targets).selectinload(models.PrimeOrganizationalTarget.node),
        selectinload(models.Prime.organizational_unit_targets).selectinload(models.PrimeOrganizationalUnitTarget.organizational_unit),
    )


def _serialize_prime(prime: models.Prime) -> PrimeOut:
    included_worker_ids = []
    excluded_worker_ids = []
    target_node_ids = []
    target_unit_ids = []
    for link in prime.worker_links:
        if (link.link_type or "include") == "exclude":
            excluded_worker_ids.append(link.worker_id)
        else:
            included_worker_ids.append(link.worker_id)
    for target in prime.organizational_targets:
        if target.node is not None and target.node.employer_id == prime.employer_id:
            target_node_ids.append(target.node_id)
    for target in prime.organizational_unit_targets:
        if target.organizational_unit is not None and target.organizational_unit.employer_id == prime.employer_id:
            target_unit_ids.append(target.organizational_unit_id)

    return PrimeOut(
        id=prime.id,
        employer_id=prime.employer_id,
        label=prime.label,
        description=prime.description,
        formula_nombre=prime.formula_nombre,
        formula_base=prime.formula_base,
        formula_taux=prime.formula_taux,
        operation_1=prime.operation_1,
        operation_2=prime.operation_2,
        is_active=prime.is_active,
        is_cotisable=prime.is_cotisable,
        is_imposable=prime.is_imposable,
        target_mode=(prime.target_mode or "global"),
        target_worker_ids=sorted(included_worker_ids),
        excluded_worker_ids=sorted(excluded_worker_ids),
        target_organizational_node_ids=sorted(target_node_ids),
        target_organizational_unit_ids=sorted(target_unit_ids),
    )


def _replace_prime_targets(db: Session, prime: models.Prime, payload: PrimeCreate) -> None:
    target_mode = payload.target_mode or "global"
    prime.target_mode = target_mode

    existing_links = {
        (link.worker_id, (link.link_type or "include")): link
        for link in list(prime.worker_links)
    }
    desired_keys = set()

    included_ids = set(payload.target_worker_ids or [])
    excluded_ids = set(payload.excluded_worker_ids or [])
    requested_node_ids = set(payload.target_organizational_node_ids or [])
    requested_unit_ids = set(payload.target_organizational_unit_ids or [])

    if target_mode == "individual" and not included_ids:
        raise HTTPException(status_code=400, detail="Veuillez selectionner au moins un salarie pour une prime individuelle.")
    if target_mode == "segment" and not (requested_node_ids or requested_unit_ids):
        raise HTTPException(status_code=400, detail="Veuillez selectionner au moins un segment de la hierarchie organisationnelle.")

    worker_rows = {}
    all_worker_ids = included_ids | excluded_ids
    if all_worker_ids:
        rows = db.query(models.Worker).filter(models.Worker.id.in_(all_worker_ids)).all()
        worker_rows = {worker.id: worker for worker in rows}
        missing_ids = sorted(all_worker_ids - set(worker_rows.keys()))
        if missing_ids:
            raise HTTPException(status_code=400, detail=f"Salaries introuvables: {', '.join(str(item) for item in missing_ids)}")
        invalid_scope_ids = sorted(
            worker_id for worker_id, worker in worker_rows.items() if worker.employer_id != prime.employer_id
        )
        if invalid_scope_ids:
            raise HTTPException(status_code=400, detail=f"Salaries hors perimetre employeur: {', '.join(str(item) for item in invalid_scope_ids)}")

    for worker_id in included_ids:
        desired_keys.add((worker_id, "include"))
    for worker_id in excluded_ids:
        desired_keys.add((worker_id, "exclude"))

    for key, link in existing_links.items():
        if key not in desired_keys:
            db.delete(link)

    for worker_id, link_type in desired_keys:
        if (worker_id, link_type) in existing_links:
            existing_links[(worker_id, link_type)].is_active = True
            existing_links[(worker_id, link_type)].link_type = link_type
            continue
        db.add(
            models.WorkerPrimeLink(
                worker_id=worker_id,
                prime_id=prime.id,
                is_active=True,
                link_type=link_type,
            )
        )

    desired_node_ids = requested_node_ids
    existing_targets = {}
    for target in list(prime.organizational_targets):
        if target.node is None or target.node.employer_id != prime.employer_id:
            db.delete(target)
            continue
        existing_targets[target.node_id] = target
    if desired_node_ids:
        nodes = db.query(models.OrganizationalNode).filter(models.OrganizationalNode.id.in_(desired_node_ids)).all()
        node_map = {node.id: node for node in nodes}
        missing_node_ids = sorted(desired_node_ids - set(node_map.keys()))
        if missing_node_ids:
            raise HTTPException(status_code=400, detail=f"Noeuds organisationnels introuvables: {', '.join(str(item) for item in missing_node_ids)}")
        invalid_node_ids = sorted(
            node_id for node_id, node in node_map.items() if node.employer_id != prime.employer_id
        )
        if invalid_node_ids:
            raise HTTPException(status_code=400, detail=f"Noeuds organisationnels hors perimetre employeur: {', '.join(str(item) for item in invalid_node_ids)}")

    for node_id, target in existing_targets.items():
        if node_id not in desired_node_ids:
            db.delete(target)
    for node_id in desired_node_ids:
        if node_id not in existing_targets:
            db.add(models.PrimeOrganizationalTarget(prime_id=prime.id, node_id=node_id))

    desired_unit_ids = requested_unit_ids
    existing_unit_targets = {}
    for target in list(prime.organizational_unit_targets):
        if target.organizational_unit is None or target.organizational_unit.employer_id != prime.employer_id:
            db.delete(target)
            continue
        existing_unit_targets[target.organizational_unit_id] = target
    if desired_unit_ids:
        units = db.query(models.OrganizationalUnit).filter(models.OrganizationalUnit.id.in_(desired_unit_ids)).all()
        unit_map = {unit.id: unit for unit in units}
        missing_unit_ids = sorted(desired_unit_ids - set(unit_map.keys()))
        if missing_unit_ids:
            raise HTTPException(status_code=400, detail=f"Unites organisationnelles introuvables: {', '.join(str(item) for item in missing_unit_ids)}")
        invalid_unit_ids = sorted(
            unit_id for unit_id, unit in unit_map.items() if unit.employer_id != prime.employer_id or not unit.is_active
        )
        if invalid_unit_ids:
            raise HTTPException(status_code=400, detail=f"Unites organisationnelles hors perimetre ou inactives: {', '.join(str(item) for item in invalid_unit_ids)}")

    for unit_id, target in existing_unit_targets.items():
        if unit_id not in desired_unit_ids:
            db.delete(target)
    for unit_id in desired_unit_ids:
        if unit_id not in existing_unit_targets:
            db.add(models.PrimeOrganizationalUnitTarget(prime_id=prime.id, organizational_unit_id=unit_id))


def _safe_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _add_issue(
    issues: list[dict[str, Any]],
    *,
    row_number: int,
    code: str,
    message: str,
    column: Optional[str] = None,
    value: Optional[Any] = None,
) -> None:
    issues.append(
        {
            "row_number": row_number,
            "column": column,
            "code": code,
            "message": message,
            "value": None if value is None else str(value),
        }
    )


def _build_report(
    *,
    mode: str,
    total_rows: int,
    processed_rows: int,
    created: int,
    updated: int,
    skipped: int,
    failed: int,
    unknown_columns: list[str],
    missing_columns: list[str],
    issues: list[dict[str, Any]],
) -> schemas.TabularImportReport:
    return schemas.TabularImportReport(
        mode=mode,
        total_rows=total_rows,
        processed_rows=processed_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        unknown_columns=unknown_columns,
        missing_columns=missing_columns,
        issues=[schemas.ImportIssue(**item) for item in issues],
        error_report_csv=issues_to_csv(issues) if issues else None,
    )


def _build_expected_prime_columns(prime_labels: list[str]) -> list[str]:
    columns = ["ID", "Matricule", "Nom", "Prenom"]
    for label in prime_labels:
        columns.extend([f"{label} (Nombre)", f"{label} (Base)"])
    return columns


def _build_prime_template_df(
    db: Session,
    employer_id: int,
    *,
    prefilled: bool,
    filters: dict[str, object] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    prime_labels = [
        prime.label
        for prime in db.query(models.Prime)
        .filter(
            models.Prime.employer_id == employer_id,
            models.Prime.is_active == True,
        )
        .order_by(models.Prime.label.asc())
        .all()
    ]
    columns = _build_expected_prime_columns(prime_labels)
    rows: list[dict[str, Any]] = []

    if prefilled:
        workers = (
            apply_worker_hierarchy_filters(
                db.query(models.Worker).filter(models.Worker.employer_id == employer_id),
                db,
                employer_id=employer_id,
                filters=filters,
            )
            .order_by(models.Worker.matricule.asc())
            .all()
        )
        for worker in workers:
            row: dict[str, Any] = {
                "ID": worker.id,
                "Matricule": worker.matricule or "",
                "Nom": worker.nom or "",
                "Prenom": worker.prenom or "",
            }
            for label in prime_labels:
                row[f"{label} (Nombre)"] = None
                row[f"{label} (Base)"] = None
            rows.append(row)
    else:
        row = {"ID": 1, "Matricule": "M001", "Nom": "RAKOTO", "Prenom": "Jean"}
        for label in prime_labels:
            row[f"{label} (Nombre)"] = 1
            row[f"{label} (Base)"] = 5000
        rows.append(row)

    return pd.DataFrame(rows, columns=columns), prime_labels


def _import_primes_dataframe(
    *,
    df: pd.DataFrame,
    period: str,
    employer_id: int,
    update_existing: bool,
    db: Session,
    user: models.AppUser,
    dry_run: bool,
    filters: dict[str, object] | None = None,
) -> schemas.TabularImportReport:
    mode = "mixed" if update_existing else "create"
    _ensure_employer_access(db, user, employer_id)
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    prime_labels = [
        prime.label
        for prime in db.query(models.Prime)
        .filter(
            models.Prime.employer_id == employer_id,
            models.Prime.is_active == True,
        )
        .order_by(models.Prime.label.asc())
        .all()
    ]
    filter_active = bool(filters and any(filters.values()))
    allowed_worker_ids = {
        worker.id
        for worker in apply_worker_hierarchy_filters(
            db.query(models.Worker).filter(models.Worker.employer_id == employer_id),
            db,
            employer_id=employer_id,
            filters=filters,
        ).all()
    }
    expected_columns = _build_expected_prime_columns(prime_labels)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        expected_columns,
        [],
    )

    issues: list[dict[str, Any]] = []
    if unknown_columns:
        _add_issue(
            issues,
            row_number=1,
            code="unknown_columns",
            message=f"Colonnes inconnues: {', '.join(unknown_columns)}",
        )
    if missing_columns:
        _add_issue(
            issues,
            row_number=1,
            code="missing_columns",
            message=f"Colonnes obligatoires manquantes: {', '.join(missing_columns)}",
        )
    if unknown_columns or missing_columns:
        return _build_report(
            mode=mode,
            total_rows=0,
            processed_rows=0,
            created=0,
            updated=0,
            skipped=0,
            failed=0,
            unknown_columns=unknown_columns,
            missing_columns=missing_columns,
            issues=issues,
        )

    total_rows = 0
    processed_rows = 0
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    label_to_field = {
        "13??me Mois": "prime_13",
        employer.label_prime1 or "Prime 1": "prime1",
        employer.label_prime2 or "Prime 2": "prime2",
        employer.label_prime3 or "Prime 3": "prime3",
        employer.label_prime4 or "Prime 4": "prime4",
        employer.label_prime5 or "Prime 5": "prime5",
    }

    for idx, row in df.iterrows():
        row_number = idx + 2
        if all((value is None or str(value).strip() == "" or str(value).lower() == "nan") for value in row.values):
            continue
        total_rows += 1

        source_id_col = mapping.get("ID")
        source_matricule_col = mapping.get("Matricule")
        worker_id_value = _safe_optional_float(row.get(source_id_col) if source_id_col else None)
        matricule = str(row.get(source_matricule_col) if source_matricule_col else "").strip()
        if worker_id_value is None and not matricule:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="missing_worker_identifier",
                message="ID ou Matricule obligatoire.",
                column="ID",
            )
            continue

        worker = None
        if worker_id_value is not None:
            worker = db.query(models.Worker).filter(
                models.Worker.id == int(worker_id_value),
                models.Worker.employer_id == employer_id,
            ).first()
        if worker is None and matricule:
            worker = db.query(models.Worker).filter(
                models.Worker.matricule == matricule,
                models.Worker.employer_id == employer_id,
            ).first()
        if not worker:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="unknown_worker",
                message=f"Salarie introuvable pour l'employeur: {int(worker_id_value) if worker_id_value is not None else matricule}.",
                column="ID" if worker_id_value is not None else "Matricule",
                value=int(worker_id_value) if worker_id_value is not None else matricule,
            )
            continue
        if filter_active and worker.id not in allowed_worker_ids:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="worker_out_of_scope",
                message="Salarie hors du filtre organisationnel actif.",
                column="Matricule",
                value=worker.matricule,
            )
            continue

        row_created = False
        row_updated = False
        row_skipped = False

        try:
            with db.begin_nested():
                existing_entries = db.query(models.PayrollPrime).filter(
                    models.PayrollPrime.worker_id == worker.id,
                    models.PayrollPrime.period == period,
                ).all()
                entries_map = {item.prime_label: item for item in existing_entries}
                payvar: Optional[models.PayVar] = None

                for label in prime_labels:
                    nombre_col = mapping.get(f"{label} (Nombre)")
                    base_col = mapping.get(f"{label} (Base)")
                    nombre = _safe_optional_float(row.get(nombre_col) if nombre_col else None)
                    base = _safe_optional_float(row.get(base_col) if base_col else None)
                    taux = None

                    if nombre is None and base is None and taux is None:
                        continue

                    entry = entries_map.get(label)
                    if entry:
                        if not update_existing:
                            row_skipped = True
                            continue
                        entry.nombre = nombre
                        entry.base = base
                        entry.taux = taux
                        row_updated = True
                    else:
                        db.add(
                            models.PayrollPrime(
                                worker_id=worker.id,
                                period=period,
                                prime_label=label,
                                nombre=nombre,
                                base=base,
                                taux=taux,
                            )
                        )
                        row_created = True

                    if any(v is not None for v in [nombre, base, taux]):
                        payvar_field = label_to_field.get(label)
                        if payvar_field:
                            if payvar is None:
                                payvar = db.query(models.PayVar).filter(
                                    models.PayVar.worker_id == worker.id,
                                    models.PayVar.period == period,
                                ).first()
                            if payvar:
                                setattr(payvar, payvar_field, 0.0)

                if row_created or row_updated:
                    processed_rows += 1
                elif row_skipped:
                    skipped += 1
                else:
                    skipped += 1

            if row_created:
                created += 1
            if row_updated:
                updated += 1
        except Exception as exc:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="row_error",
                message=str(exc),
            )

    if dry_run:
        db.rollback()

    return _build_report(
        mode=mode,
        total_rows=total_rows,
        processed_rows=processed_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        unknown_columns=unknown_columns,
        missing_columns=missing_columns,
        issues=issues,
    )


@router.get("/", response_model=List[PrimeOut])
def get_primes(
    employer_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    _ensure_employer_access(db, user, employer_id)
    primes = _prime_query(db).filter(models.Prime.employer_id == employer_id).all()
    return [_serialize_prime(prime) for prime in primes]


@router.post("/", response_model=PrimeOut)
def create_prime(
    prime: PrimeCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    _ensure_employer_access(db, user, prime.employer_id)
    payload = prime.model_dump(exclude={"target_worker_ids", "excluded_worker_ids", "target_organizational_node_ids", "target_organizational_unit_ids"})
    db_prime = models.Prime(**payload)
    db.add(db_prime)
    db.flush()
    _replace_prime_targets(db, db_prime, prime)
    db.commit()
    db.refresh(db_prime)
    db.refresh(db_prime, attribute_names=["worker_links", "organizational_targets", "organizational_unit_targets"])
    return _serialize_prime(db_prime)


@router.put("/{prime_id}", response_model=PrimeOut)
def update_prime(
    prime_id: int,
    prime: PrimeCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_prime = _prime_query(db).filter(models.Prime.id == prime_id).first()
    if not db_prime:
        raise HTTPException(status_code=404, detail="Prime not found")
    _ensure_employer_access(db, user, db_prime.employer_id)
    if prime.employer_id != db_prime.employer_id:
        raise HTTPException(status_code=400, detail="Changing employer_id is not allowed")

    for key, value in prime.model_dump(exclude={"target_worker_ids", "excluded_worker_ids", "target_organizational_node_ids", "target_organizational_unit_ids"}).items():
        setattr(db_prime, key, value)

    _replace_prime_targets(db, db_prime, prime)
    db.commit()
    db.refresh(db_prime)
    db.refresh(db_prime, attribute_names=["worker_links", "organizational_targets", "organizational_unit_targets"])
    return _serialize_prime(db_prime)


@router.delete("/{prime_id}")
def delete_prime(
    prime_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    db_prime = _prime_query(db).filter(models.Prime.id == prime_id).first()
    if not db_prime:
        raise HTTPException(status_code=404, detail="Prime not found")
    _ensure_employer_access(db, user, db_prime.employer_id)
    db.delete(db_prime)
    db.commit()
    return {"message": "Deleted"}


@router.post("/associations")
def set_worker_prime_association(
    assoc: AssociationRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    worker = _get_worker_or_404(db, assoc.worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    prime = db.query(models.Prime).filter(models.Prime.id == assoc.prime_id).first()
    if not prime:
        raise HTTPException(status_code=404, detail="Prime not found")
    if prime.employer_id != worker.employer_id:
        raise HTTPException(status_code=400, detail="Prime and worker must belong to same employer")

    link = db.query(models.WorkerPrimeLink).filter(
        models.WorkerPrimeLink.worker_id == assoc.worker_id,
        models.WorkerPrimeLink.prime_id == assoc.prime_id,
    ).first()

    if link and (link.link_type or "include") != assoc.link_type:
        db.delete(link)
        db.flush()
        link = None

    if not link:
        link = models.WorkerPrimeLink(
            worker_id=assoc.worker_id,
            prime_id=assoc.prime_id,
            link_type=assoc.link_type,
        )
        db.add(link)

    link.is_active = assoc.is_active
    link.link_type = assoc.link_type
    db.commit()
    return {"message": "Updated"}


@router.get("/associations", response_model=List[dict])
def get_worker_associations(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    links = db.query(models.WorkerPrimeLink).filter(models.WorkerPrimeLink.worker_id == worker_id).all()
    return [{"prime_id": l.prime_id, "is_active": l.is_active, "link_type": l.link_type or "include"} for l in links]


@router.post("/reset-overrides")
def reset_prime_overrides(
    period: str = Query(...),
    employer_id: int = Query(...),
    etablissement: Optional[str] = Query(None),
    departement: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    unite: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    _ensure_employer_access(db, user, employer_id)
    workers = apply_worker_hierarchy_filters(
        db.query(models.Worker).filter(models.Worker.employer_id == employer_id),
        db,
        employer_id=employer_id,
        filters={
            "etablissement": etablissement,
            "departement": departement,
            "service": service,
            "unite": unite,
        },
    ).all()
    worker_ids = [w.id for w in workers]

    if not worker_ids:
        return {"message": "Aucun salariÃ© trouvÃ© pour cet employeur", "deleted_count": 0}

    deleted_count = db.query(models.PayrollPrime).filter(
        models.PayrollPrime.worker_id.in_(worker_ids),
        models.PayrollPrime.period == period,
    ).delete(synchronize_session=False)

    db.commit()
    return {"message": "Les valeurs par dÃ©faut sont restaurÃ©es", "deleted_count": deleted_count}


@router.get("/export-primes-template/{employer_id}")
def export_primes_template(
    employer_id: int,
    prefilled: bool = Query(True),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    etablissement: Optional[str] = Query(None),
    departement: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    unite: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    _ensure_employer_access(db, user, employer_id)
    df, _ = _build_prime_template_df(
        db,
        employer_id,
        prefilled=prefilled,
        filters={
            "etablissement": etablissement,
            "departement": departement,
            "service": service,
            "unite": unite,
        },
    )
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=Modele_Import_Primes_{employer_id}.csv"},
        )

    content = dataframe_to_xlsx_bytes(df, sheet_name="Import Primes")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Modele_Import_Primes_{employer_id}.xlsx"},
    )


@router.get("/template")
def download_primes_template(
    employer_id: int = Query(...),
    prefilled: bool = Query(True),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    etablissement: Optional[str] = Query(None),
    departement: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    unite: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    return export_primes_template(
        employer_id=employer_id,
        prefilled=prefilled,
        export_format=export_format,
        etablissement=etablissement,
        departement=departement,
        service=service,
        unite=unite,
        db=db,
        user=user,
    )


@router.post("/import/preview", response_model=schemas.TabularImportReport)
async def preview_primes_import(
    file: UploadFile = File(...),
    period: str = Form(...),
    employer_id: int = Form(...),
    update_existing: bool = Form(True),
    etablissement: Optional[str] = Form(None),
    departement: Optional[str] = Form(None),
    service: Optional[str] = Form(None),
    unite: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    return _import_primes_dataframe(
        df=df,
        period=period,
        employer_id=employer_id,
        update_existing=update_existing,
        db=db,
        user=user,
        dry_run=True,
        filters={
            "etablissement": etablissement,
            "departement": departement,
            "service": service,
            "unite": unite,
        },
    )


@router.post("/import")
async def import_primes(
    file: UploadFile = File(...),
    period: str = Form(...),
    employer_id: int = Form(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    etablissement: Optional[str] = Form(None),
    departement: Optional[str] = Form(None),
    service: Optional[str] = Form(None),
    unite: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*PAYROLL_WRITE_ROLES)),
):
    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    report = _import_primes_dataframe(
        df=df,
        period=period,
        employer_id=employer_id,
        update_existing=update_existing,
        db=db,
        user=user,
        dry_run=dry_run,
        filters={
            "etablissement": etablissement,
            "departement": departement,
            "service": service,
            "unite": unite,
        },
    )

    if not dry_run:
        if report.created > 0 or report.updated > 0:
            record_audit(
                db,
                actor=user,
                action="primes.import",
                entity_type="prime_import",
                entity_id=f"{report.created}:{report.updated}:{report.skipped}",
                route="/primes/import",
                after=report.model_dump(mode="json"),
            )
            db.commit()
        else:
            db.rollback()

    return {
        "message": "Import terminÃ© avec succÃ¨s",
        "updated_items": report.created + report.updated,
        "errors": [issue.message for issue in report.issues],
        "imported": report.created,
        "updated": report.updated,
        "skipped": report.skipped,
        "report": report.model_dump(mode="json"),
    }


@router.get("/values/{payroll_run_id}", response_model=List[PrimeValuesOut])
def get_prime_values(payroll_run_id: int, db: Session = Depends(get_db)):
    run = db.query(models.PayrollRun).filter(models.PayrollRun.id == payroll_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    period = run.period
    employer_id = run.employer_id

    workers = db.query(models.Worker).filter(models.Worker.employer_id == employer_id).all()
    payvars = db.query(models.PayVar).filter(models.PayVar.period == period).all()
    pv_map = {p.worker_id: p for p in payvars}

    result = []
    for worker in workers:
        pv = pv_map.get(worker.id)
        result.append(
            {
                "worker_id": worker.id,
                "matricule": worker.matricule,
                "nom": worker.nom,
                "prenom": worker.prenom,
                "prime_13": pv.prime_13 if pv else 0.0,
                "prime1": pv.prime1 if pv else 0.0,
                "prime2": pv.prime2 if pv else 0.0,
                "prime3": pv.prime3 if pv else 0.0,
                "prime4": pv.prime4 if pv else 0.0,
                "prime5": pv.prime5 if pv else 0.0,
            }
        )
    return result


@router.put("/values/{payroll_run_id}/{worker_id}")
def update_prime_values(
    payroll_run_id: int,
    worker_id: int,
    values: PrimeValuesUpdate,
    db: Session = Depends(get_db),
):
    run = db.query(models.PayrollRun).filter(models.PayrollRun.id == payroll_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    period = run.period
    employer = db.query(models.Employer).filter(models.Employer.id == run.employer_id).first()

    pv = db.query(models.PayVar).filter(models.PayVar.worker_id == worker_id, models.PayVar.period == period).first()
    if not pv:
        pv = models.PayVar(worker_id=worker_id, period=period)
        db.add(pv)

    pv.prime_13 = values.prime_13
    pv.prime1 = values.prime1
    pv.prime2 = values.prime2
    pv.prime3 = values.prime3
    pv.prime4 = values.prime4
    pv.prime5 = values.prime5

    if employer:
        prime_labels_to_delete = [
            employer.label_prime1 or "Prime 1",
            employer.label_prime2 or "Prime 2",
            employer.label_prime3 or "Prime 3",
            employer.label_prime4 or "Prime 4",
            employer.label_prime5 or "Prime 5",
            "13Ã¨me Mois",
        ]
        db.query(models.PayrollPrime).filter(
            models.PayrollPrime.worker_id == worker_id,
            models.PayrollPrime.period == period,
            models.PayrollPrime.prime_label.in_(prime_labels_to_delete),
        ).delete(synchronize_session=False)

    db.commit()
    return {"message": "Updated"}


@router.post("/values/{payroll_run_id}/reset-bulk")
def reset_bulk_prime_values(
    payroll_run_id: int,
    worker_ids: List[int],
    db: Session = Depends(get_db),
):
    run = db.query(models.PayrollRun).filter(models.PayrollRun.id == payroll_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    period = run.period
    db.query(models.PayVar).filter(
        models.PayVar.period == period,
        models.PayVar.worker_id.in_(worker_ids),
    ).update(
        {
            "prime_13": 0.0,
            "prime1": 0.0,
            "prime2": 0.0,
            "prime3": 0.0,
            "prime4": 0.0,
            "prime5": 0.0,
        },
        synchronize_session=False,
    )

    db.commit()
    return {"message": "Reset done"}

