from datetime import datetime
from typing import Any, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import READ_PAYROLL_ROLES, WRITE_RH_ROLES, can_access_worker, can_manage_worker, require_roles
from ..services.audit_service import record_audit
from ..services.compliance_service import create_contract_version
from ..services.master_data_service import sync_worker_master_data
from ..services.recruitment_assistant_service import build_contract_guidance, json_dump
from ..services.tabular_io import (
    build_column_mapping,
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    issues_to_csv,
    read_tabular_bytes,
)


router = APIRouter(prefix="/custom-contracts", tags=["custom-contracts"])
CONTRACT_WRITE_ROLES = {*WRITE_RH_ROLES, "inspecteur"}
CONTRACT_IMPORT_COLUMNS = [
    "Employeur",
    "Matricule",
    "Template Type",
    "Titre",
    "Contenu",
    "Par Defaut (Oui/Non)",
]
CONTRACT_REQUIRED_COLUMNS = ["Matricule", "Template Type", "Titre", "Contenu"]


def _get_worker_or_404(db: Session, worker_id: int) -> models.Worker:
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _get_contract_or_404(db: Session, contract_id: int) -> models.CustomContract:
    contract = db.query(models.CustomContract).filter(models.CustomContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


def _parse_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    return raw in {"1", "true", "oui", "yes", "y", "o"}


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


def _value(row: Any, mapping: dict[str, str], column: str) -> Any:
    source_col = mapping.get(column)
    if not source_col:
        return None
    return row.get(source_col)


@router.get("/import/template")
def download_custom_contracts_template(
    employer_id: Optional[int] = Query(None),
    prefilled: bool = Query(False),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    rows: list[dict[str, Any]] = []
    if prefilled:
        contracts_query = db.query(models.CustomContract).order_by(
            models.CustomContract.updated_at.desc(),
            models.CustomContract.id.desc(),
        )
        if employer_id is not None:
            contracts_query = contracts_query.filter(models.CustomContract.employer_id == employer_id)
        contracts = contracts_query.all()
        employers = db.query(models.Employer).all()
        employers_by_id = {item.id: item for item in employers}

        for contract in contracts:
            worker = db.query(models.Worker).filter(models.Worker.id == contract.worker_id).first()
            if not worker or not can_access_worker(db, user, worker):
                continue
            employer = employers_by_id.get(contract.employer_id)
            rows.append(
                {
                    "Employeur": employer.raison_sociale if employer else "",
                    "Matricule": worker.matricule or "",
                    "Template Type": contract.template_type,
                    "Titre": contract.title,
                    "Contenu": contract.content,
                    "Par Defaut (Oui/Non)": "Oui" if contract.is_default else "Non",
                }
            )
    else:
        rows.append(
            {
                "Employeur": "Karibo Services",
                "Matricule": "M001",
                "Template Type": "employment_contract",
                "Titre": "Contrat de Travail",
                "Contenu": "<h1>Contrat</h1><p>Contenu personnalisé...</p>",
                "Par Defaut (Oui/Non)": "Oui",
            }
        )

    df = pd.DataFrame(rows, columns=CONTRACT_IMPORT_COLUMNS)
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        filename = "custom_contracts_template_prefilled.csv" if prefilled else "custom_contracts_template.csv"
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    content = dataframe_to_xlsx_bytes(df, sheet_name="Contrats")
    filename = "custom_contracts_template_prefilled.xlsx" if prefilled else "custom_contracts_template.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=schemas.TabularImportReport)
async def import_custom_contracts(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*CONTRACT_WRITE_ROLES)),
):
    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        CONTRACT_IMPORT_COLUMNS,
        CONTRACT_REQUIRED_COLUMNS,
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
    employer_by_name = {item.raison_sociale.strip().lower(): item for item in employers}

    total_rows = 0
    processed_rows = 0
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    for idx, row in df.iterrows():
        row_number = idx + 2
        if all((value is None or str(value).strip() == "" or str(value).lower() == "nan") for value in row.values):
            continue
        total_rows += 1

        matricule = str(_value(row, mapping, "Matricule") or "").strip()
        if not matricule:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="missing_matricule",
                message="Matricule obligatoire.",
                column="Matricule",
            )
            continue

        worker = db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
        if not worker:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="unknown_worker",
                message=f"Matricule inconnu: {matricule}.",
                column="Matricule",
                value=matricule,
            )
            continue
        if not can_manage_worker(db, user, worker=worker):
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="forbidden_worker_scope",
                message=f"Droits insuffisants pour modifier {matricule}.",
            )
            continue

        employer_name = str(_value(row, mapping, "Employeur") or "").strip()
        if employer_name:
            employer = employer_by_name.get(employer_name.lower())
            if not employer:
                failed += 1
                _add_issue(
                    issues,
                    row_number=row_number,
                    code="unknown_employer",
                    message=f"Employeur introuvable: {employer_name}.",
                    column="Employeur",
                    value=employer_name,
                )
                continue
            if employer.id != worker.employer_id:
                failed += 1
                _add_issue(
                    issues,
                    row_number=row_number,
                    code="worker_employer_mismatch",
                    message=f"Le matricule {matricule} n'appartient pas à {employer_name}.",
                    column="Employeur",
                    value=employer_name,
                )
                continue

        template_type = str(_value(row, mapping, "Template Type") or "").strip() or "employment_contract"
        title = str(_value(row, mapping, "Titre") or "").strip()
        content_html = str(_value(row, mapping, "Contenu") or "").strip()
        is_default = _parse_bool(_value(row, mapping, "Par Defaut (Oui/Non)"))

        if not title:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="missing_title",
                message="Titre obligatoire.",
                column="Titre",
            )
            continue
        if not content_html:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="missing_content",
                message="Contenu obligatoire.",
                column="Contenu",
            )
            continue

        try:
            with db.begin_nested():
                existing = db.query(models.CustomContract).filter(
                    models.CustomContract.worker_id == worker.id,
                    models.CustomContract.template_type == template_type,
                    models.CustomContract.title == title,
                ).first()

                if existing:
                    if not update_existing:
                        skipped += 1
                        _add_issue(
                            issues,
                            row_number=row_number,
                            code="existing_skipped",
                            message=f"Contrat déjà existant ignoré pour {matricule} / {title}.",
                        )
                        continue
                    existing.content = content_html
                    existing.is_default = is_default
                    contract = existing
                    updated += 1
                else:
                    contract = models.CustomContract(
                        worker_id=worker.id,
                        employer_id=worker.employer_id,
                        title=title,
                        content=content_html,
                        template_type=template_type,
                        is_default=is_default,
                    )
                    db.add(contract)
                    db.flush()
                    created += 1

                if is_default:
                    db.query(models.CustomContract).filter(
                        models.CustomContract.worker_id == worker.id,
                        models.CustomContract.template_type == template_type,
                        models.CustomContract.id != contract.id,
                    ).update({"is_default": False})

                sync_worker_master_data(db, worker, contract=contract)
                processed_rows += 1
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
    else:
        if created > 0 or updated > 0:
            record_audit(
                db,
                actor=user,
                action="custom_contract.import",
                entity_type="custom_contract_import",
                entity_id=f"{created}:{updated}:{skipped}",
                route="/custom-contracts/import",
                after={
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                    "issues": len(issues),
                },
            )
            db.commit()
        else:
            db.rollback()

    return _build_report(
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


@router.post("/", response_model=schemas.CustomContractOut)
def create_custom_contract(
    contract: schemas.CustomContractIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*CONTRACT_WRITE_ROLES)),
):
    worker = _get_worker_or_404(db, contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    employer = db.query(models.Employer).filter(models.Employer.id == contract.employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    if contract.is_default:
        db.query(models.CustomContract).filter(
            models.CustomContract.worker_id == contract.worker_id,
            models.CustomContract.template_type == contract.template_type,
        ).update({"is_default": False})

    db_contract = models.CustomContract(**contract.model_dump())
    db.add(db_contract)
    db.flush()
    create_contract_version(
        db,
        contract=db_contract,
        worker=worker,
        actor=user,
        source_module="contracts",
        status=db_contract.validation_status or "active_non_validated",
    )
    db_contract.active_version_number = len(db_contract.versions)
    db_contract.last_published_at = datetime.now()
    sync_worker_master_data(db, worker, contract=db_contract)
    record_audit(
        db,
        actor=user,
        action="custom_contract.create",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route="/custom-contracts/",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after=db_contract,
    )
    db.commit()
    db.refresh(db_contract)
    return db_contract


@router.get("/", response_model=List[schemas.CustomContractOut])
def list_custom_contracts(
    employer_id: Optional[int] = None,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = db.query(models.CustomContract)
    if employer_id is not None:
        query = query.filter(models.CustomContract.employer_id == employer_id)
    if template_type:
        query = query.filter(models.CustomContract.template_type == template_type)

    contracts = query.order_by(models.CustomContract.updated_at.desc()).all()
    visible_contracts: list[models.CustomContract] = []
    for contract in contracts:
        worker = _get_worker_or_404(db, contract.worker_id)
        if can_access_worker(db, user, worker):
            visible_contracts.append(contract)
    return visible_contracts


@router.get("/worker/{worker_id}", response_model=List[schemas.CustomContractOut])
def get_worker_contracts(
    worker_id: int,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    query = db.query(models.CustomContract).filter(models.CustomContract.worker_id == worker_id)
    if template_type:
        query = query.filter(models.CustomContract.template_type == template_type)
    return query.order_by(models.CustomContract.updated_at.desc()).all()


@router.get("/worker/{worker_id}/default", response_model=schemas.CustomContractOut)
def get_worker_default_contract(
    worker_id: int,
    template_type: str = "employment_contract",
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    contract = db.query(models.CustomContract).filter(
        models.CustomContract.worker_id == worker_id,
        models.CustomContract.template_type == template_type,
        models.CustomContract.is_default == True,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="No default contract found")
    return contract


@router.get("/worker/{worker_id}/guidance", response_model=schemas.RecruitmentContractGuidanceOut)
def get_worker_contract_guidance(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    decision = (
        db.query(models.RecruitmentDecision)
        .filter(models.RecruitmentDecision.converted_worker_id == worker.id)
        .order_by(models.RecruitmentDecision.decided_at.desc(), models.RecruitmentDecision.updated_at.desc())
        .first()
    )
    application = decision.application if decision else None
    job = application.job_posting if application else None
    profile = None
    if job:
        linked = getattr(job, "job_profile", None)
        profile = linked[0] if isinstance(linked, list) and linked else linked

    guidance = build_contract_guidance(
        job
        or models.RecruitmentJobPosting(
            employer_id=worker.employer_id,
            title=worker.poste or "Poste a confirmer",
            department=worker.departement,
            location=worker.etablissement,
            contract_type=worker.nature_contrat or "CDI",
            description="",
        ),
        {
            "mission_summary": profile.mission_summary if profile else "",
            "classification": profile.classification if profile else worker.indice,
            "salary_min": profile.salary_min if profile else worker.salaire_base,
            "desired_start_date": profile.desired_start_date.isoformat() if profile and profile.desired_start_date else (worker.date_embauche.isoformat() if worker.date_embauche else ""),
        },
    )
    guidance["suggested_defaults"]["fonction"] = worker.poste or guidance["suggested_defaults"].get("fonction") or ""
    guidance["suggested_defaults"]["categorie_professionnelle"] = worker.categorie_prof or guidance["suggested_defaults"].get("categorie_professionnelle") or ""
    guidance["suggested_defaults"]["date_effet"] = worker.date_embauche.isoformat() if worker.date_embauche else guidance["suggested_defaults"].get("date_effet") or ""
    return schemas.RecruitmentContractGuidanceOut(**guidance)


@router.get("/{contract_id}", response_model=schemas.CustomContractOut)
def get_custom_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, contract.worker_id)
    if not can_access_worker(db, user, worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    return contract


@router.put("/{contract_id}", response_model=schemas.CustomContractOut)
def update_custom_contract(
    contract_id: int,
    contract_update: schemas.CustomContractUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*CONTRACT_WRITE_ROLES)),
):
    db_contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, db_contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    before = {
        "title": db_contract.title,
        "template_type": db_contract.template_type,
        "is_default": db_contract.is_default,
    }
    if contract_update.is_default:
        db.query(models.CustomContract).filter(
            models.CustomContract.worker_id == db_contract.worker_id,
            models.CustomContract.template_type == db_contract.template_type,
            models.CustomContract.id != contract_id,
        ).update({"is_default": False})

    update_data = contract_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_contract, field, value)
    if "content" in update_data or "title" in update_data:
        if "validation_status" not in update_data:
            db_contract.validation_status = "active_non_validated"
        if "inspection_status" not in update_data:
            db_contract.inspection_status = "pending_review"
        create_contract_version(
            db,
            contract=db_contract,
            worker=worker,
            actor=user,
            source_module="contracts",
            status=db_contract.validation_status or "active_non_validated",
        )
        db_contract.active_version_number = len(db_contract.versions)
        db_contract.last_published_at = datetime.now()
    db.flush()
    sync_worker_master_data(db, worker, contract=db_contract)

    record_audit(
        db,
        actor=user,
        action="custom_contract.update",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route=f"/custom-contracts/{contract_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=db_contract,
    )
    db.commit()
    db.refresh(db_contract)
    return db_contract


@router.delete("/{contract_id}")
def delete_custom_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*CONTRACT_WRITE_ROLES)),
):
    db_contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, db_contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    record_audit(
        db,
        actor=user,
        action="custom_contract.delete",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route=f"/custom-contracts/{contract_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=db_contract,
        after=None,
    )
    db.delete(db_contract)
    db.flush()
    sync_worker_master_data(db, worker)
    db.commit()
    return {"message": "Contract deleted successfully"}


@router.post("/{contract_id}/set-default")
def set_default_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*CONTRACT_WRITE_ROLES)),
):
    db_contract = _get_contract_or_404(db, contract_id)
    worker = _get_worker_or_404(db, db_contract.worker_id)
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")

    db.query(models.CustomContract).filter(
        models.CustomContract.worker_id == db_contract.worker_id,
        models.CustomContract.template_type == db_contract.template_type,
        models.CustomContract.id != contract_id,
    ).update({"is_default": False})

    db_contract.is_default = True
    db.flush()
    sync_worker_master_data(db, worker, contract=db_contract)
    record_audit(
        db,
        actor=user,
        action="custom_contract.default",
        entity_type="custom_contract",
        entity_id=db_contract.id,
        route=f"/custom-contracts/{contract_id}/set-default",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after=db_contract,
    )
    db.commit()
    db.refresh(db_contract)
    return db_contract
