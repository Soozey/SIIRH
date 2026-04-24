from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_worker, can_manage_worker, require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.tabular_io import (
    build_column_mapping,
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    issues_to_csv,
    read_tabular_bytes,
)


router = APIRouter(prefix="/sst", tags=["sst"])

READ_ROLES = ("admin", "rh", "employeur", "manager", "employe")
WRITE_ROLES = ("admin", "rh", "employeur", "manager")


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh"):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


SST_IMPORT_COLUMNS = [
    "Employeur",
    "Matricule",
    "Type Incident",
    "Gravité",
    "Statut",
    "Date Heure (YYYY-MM-DD HH:MM)",
    "Lieu",
    "Description",
    "Actions",
    "Témoins",
]

SST_REQUIRED_COLUMNS = ["Employeur", "Type Incident", "Description", "Date Heure (YYYY-MM-DD HH:MM)"]


def _add_sst_issue(
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


def _build_sst_report(
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


@router.get("/incidents/template")
def download_incidents_template(
    employer_id: Optional[int] = Query(None),
    prefilled: bool = Query(False),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    import pandas as pd

    if employer_id is not None:
        _assert_employer_scope(db, user, employer_id)

    rows: list[dict[str, Any]] = []
    if prefilled:
        query = db.query(models.SstIncident)
        if employer_id is not None:
            query = query.filter(models.SstIncident.employer_id == employer_id)
        incidents = query.order_by(models.SstIncident.occurred_at.desc()).all()
        employer_ids = {item.employer_id for item in incidents}
        employers = db.query(models.Employer).filter(models.Employer.id.in_(employer_ids)).all() if employer_ids else []
        employer_map = {item.id: item.raison_sociale for item in employers}
        worker_ids = {item.worker_id for item in incidents if item.worker_id}
        workers = db.query(models.Worker).filter(models.Worker.id.in_(worker_ids)).all() if worker_ids else []
        worker_map = {item.id: item.matricule for item in workers}
        for item in incidents:
            rows.append(
                {
                    "Employeur": employer_map.get(item.employer_id, ""),
                    "Matricule": worker_map.get(item.worker_id, ""),
                    "Type Incident": item.incident_type,
                    "Gravité": item.severity,
                    "Statut": item.status,
                    "Date Heure (YYYY-MM-DD HH:MM)": item.occurred_at.strftime("%Y-%m-%d %H:%M"),
                    "Lieu": item.location,
                    "Description": item.description,
                    "Actions": item.action_taken,
                    "Témoins": item.witnesses,
                }
            )

    df = pd.DataFrame(rows, columns=SST_IMPORT_COLUMNS)
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="sst_incidents_template.csv"'},
        )
    content = dataframe_to_xlsx_bytes(df, sheet_name="Incidents")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sst_incidents_template.xlsx"'},
    )


@router.post("/incidents/import", response_model=schemas.TabularImportReport)
async def import_incidents(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        SST_IMPORT_COLUMNS,
        SST_REQUIRED_COLUMNS,
    )
    issues: list[dict[str, Any]] = []
    if unknown_columns:
        _add_sst_issue(
            issues,
            row_number=1,
            code="unknown_columns",
            message=f"Colonnes inconnues: {', '.join(unknown_columns)}",
        )
    if missing_columns:
        _add_sst_issue(
            issues,
            row_number=1,
            code="missing_columns",
            message=f"Colonnes obligatoires manquantes: {', '.join(missing_columns)}",
        )
    if unknown_columns or missing_columns:
        return _build_sst_report(
            mode="mixed" if update_existing else "create",
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

    employers = db.query(models.Employer).all()
    employer_map = {item.raison_sociale.strip().lower(): item for item in employers}
    workers = db.query(models.Worker).all()
    workers_by_matricule = {item.matricule: item for item in workers if item.matricule}

    total_rows = 0
    processed_rows = 0
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    def _value(row: Any, column: str) -> Any:
        source_column = mapping.get(column)
        return row.get(source_column) if source_column else None

    for idx, row in df.iterrows():
        row_number = idx + 2
        if all((value is None or str(value).strip() == "" or str(value).lower() == "nan") for value in row.values):
            continue
        total_rows += 1

        employer_name = str(_value(row, "Employeur") or "").strip()
        employer = employer_map.get(employer_name.lower())
        if not employer:
            failed += 1
            _add_sst_issue(
                issues,
                row_number=row_number,
                code="unknown_employer",
                message=f"Employeur introuvable: {employer_name}",
                column="Employeur",
                value=employer_name,
            )
            continue
        _assert_employer_scope(db, user, employer.id)

        matricule = str(_value(row, "Matricule") or "").strip()
        worker = workers_by_matricule.get(matricule) if matricule else None
        if worker and worker.employer_id != employer.id:
            failed += 1
            _add_sst_issue(
                issues,
                row_number=row_number,
                code="worker_employer_mismatch",
                message=f"Matricule {matricule} hors périmètre employeur.",
                column="Matricule",
                value=matricule,
            )
            continue
        if worker and not can_manage_worker(db, user, worker=worker):
            failed += 1
            _add_sst_issue(
                issues,
                row_number=row_number,
                code="forbidden_worker_scope",
                message=f"Droits insuffisants pour le salarié {matricule}.",
                column="Matricule",
                value=matricule,
            )
            continue

        incident_type = str(_value(row, "Type Incident") or "").strip()
        description = str(_value(row, "Description") or "").strip()
        if not incident_type or not description:
            failed += 1
            _add_sst_issue(
                issues,
                row_number=row_number,
                code="missing_required_values",
                message="Type incident et description sont obligatoires.",
            )
            continue

        occurred_raw = str(_value(row, "Date Heure (YYYY-MM-DD HH:MM)") or "").strip()
        try:
            occurred_at = datetime.strptime(occurred_raw, "%Y-%m-%d %H:%M")
        except ValueError:
            failed += 1
            _add_sst_issue(
                issues,
                row_number=row_number,
                code="invalid_datetime",
                message="Format date/heure invalide (attendu YYYY-MM-DD HH:MM).",
                column="Date Heure (YYYY-MM-DD HH:MM)",
                value=occurred_raw,
            )
            continue

        severity = str(_value(row, "Gravité") or "medium").strip() or "medium"
        status_value = str(_value(row, "Statut") or "open").strip() or "open"
        location = str(_value(row, "Lieu") or "").strip() or None
        action_taken = str(_value(row, "Actions") or "").strip() or None
        witnesses = str(_value(row, "Témoins") or "").strip() or None

        try:
            with db.begin_nested():
                existing = db.query(models.SstIncident).filter(
                    models.SstIncident.employer_id == employer.id,
                    models.SstIncident.worker_id == (worker.id if worker else None),
                    models.SstIncident.incident_type == incident_type,
                    models.SstIncident.occurred_at == occurred_at,
                ).first()
                if existing:
                    if not update_existing:
                        skipped += 1
                        _add_sst_issue(
                            issues,
                            row_number=row_number,
                            code="existing_skipped",
                            message="Incident déjà existant (ignoré).",
                        )
                        continue
                    existing.severity = severity
                    existing.status = status_value
                    existing.location = location
                    existing.description = description
                    existing.action_taken = action_taken
                    existing.witnesses = witnesses
                    updated += 1
                else:
                    db.add(
                        models.SstIncident(
                            employer_id=employer.id,
                            worker_id=worker.id if worker else None,
                            incident_type=incident_type,
                            severity=severity,
                            status=status_value,
                            occurred_at=occurred_at,
                            location=location,
                            description=description,
                            action_taken=action_taken,
                            witnesses=witnesses,
                        )
                    )
                    created += 1
                processed_rows += 1
        except Exception as exc:
            failed += 1
            _add_sst_issue(
                issues,
                row_number=row_number,
                code="row_error",
                message=str(exc),
            )

    if dry_run:
        db.rollback()
    else:
        record_audit(
            db,
            actor=user,
            action="sst.incidents.import",
            entity_type="sst_incident_import",
            entity_id=str(total_rows),
            route="/sst/incidents/import",
            after={
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "issues": len(issues),
            },
        )
        db.commit()

    return _build_sst_report(
        mode="mixed" if update_existing else "create",
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


@router.get("/incidents", response_model=list[schemas.SstIncidentOut])
def list_incidents(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.SstIncident)
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.SstIncident.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.SstIncident.employer_id == employer_id)

    if user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.SstIncident.worker_id == user.worker_id)
    elif worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        if worker and not can_access_worker(db, user, worker):
            raise HTTPException(status_code=403, detail="Forbidden")
        query = query.filter(models.SstIncident.worker_id == worker_id)

    return query.order_by(models.SstIncident.occurred_at.desc()).all()


@router.post("/incidents", response_model=schemas.SstIncidentOut)
def create_incident(
    payload: schemas.SstIncidentCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    if payload.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == payload.worker_id).first()
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        if not can_manage_worker(db, user, worker=worker):
            raise HTTPException(status_code=403, detail="Forbidden")
    item = models.SstIncident(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="sst.incident.create",
        entity_type="sst_incident",
        entity_id=item.id,
        route="/sst/incidents",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/incidents/{incident_id}", response_model=schemas.SstIncidentOut)
def update_incident(
    incident_id: int,
    payload: schemas.SstIncidentUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.SstIncident).filter(models.SstIncident.id == incident_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found")
    _assert_employer_scope(db, user, item.employer_id)
    if item.worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == item.worker_id).first()
        if worker and not can_manage_worker(db, user, worker=worker):
            raise HTTPException(status_code=403, detail="Forbidden")
    before = {"severity": item.severity, "status": item.status}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="sst.incident.update",
        entity_type="sst_incident",
        entity_id=item.id,
        route=f"/sst/incidents/{incident_id}",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item
