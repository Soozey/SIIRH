from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.tabular_io import (
    build_column_mapping,
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    issues_to_csv,
    read_tabular_bytes,
)

router = APIRouter(prefix="/recruitment/import", tags=["recruitment-import"])

READ_ROLES = ("admin", "rh", "employeur", "manager")
WRITE_ROLES = ("admin", "rh", "employeur")

RECRUITMENT_IMPORT_COLUMNS = {
    "candidates": [
        "Employeur",
        "Prénom",
        "Nom",
        "Email",
        "Téléphone",
        "Niveau Études",
        "Années Expérience",
        "Source",
        "Statut",
        "Résumé",
    ],
    "jobs": [
        "Employeur",
        "Intitulé",
        "Département",
        "Localisation",
        "Type Contrat",
        "Statut",
        "Fourchette Salaire",
        "Description",
        "Compétences",
    ],
}

RECRUITMENT_REQUIRED_COLUMNS = {
    "candidates": ["Employeur", "Prénom", "Nom", "Email"],
    "jobs": ["Employeur", "Intitulé"],
}


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh"):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


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


@router.get("/template")
def download_recruitment_template(
    resource: str = Query(..., pattern="^(candidates|jobs)$"),
    employer_id: Optional[int] = Query(None),
    prefilled: bool = Query(False),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    columns = RECRUITMENT_IMPORT_COLUMNS[resource]
    rows: list[dict[str, Any]] = []
    if prefilled:
        if employer_id is None:
            raise HTTPException(status_code=400, detail="employer_id requis pour template prérempli.")
        _assert_employer_scope(db, user, employer_id)
        employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
        if not employer:
            raise HTTPException(status_code=404, detail="Employer not found")
        if resource == "candidates":
            for item in db.query(models.RecruitmentCandidate).filter(models.RecruitmentCandidate.employer_id == employer_id).all():
                rows.append(
                    {
                        "Employeur": employer.raison_sociale,
                        "Prénom": item.first_name,
                        "Nom": item.last_name,
                        "Email": item.email,
                        "Téléphone": item.phone,
                        "Niveau Études": item.education_level,
                        "Années Expérience": item.experience_years,
                        "Source": item.source,
                        "Statut": item.status,
                        "Résumé": item.summary,
                    }
                )
        else:
            for item in db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.employer_id == employer_id).all():
                rows.append(
                    {
                        "Employeur": employer.raison_sociale,
                        "Intitulé": item.title,
                        "Département": item.department,
                        "Localisation": item.location,
                        "Type Contrat": item.contract_type,
                        "Statut": item.status,
                        "Fourchette Salaire": item.salary_range,
                        "Description": item.description,
                        "Compétences": item.skills_required,
                    }
                )

    df = pd.DataFrame(rows, columns=columns)
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="recruitment_{resource}_template.csv"'},
        )
    content = dataframe_to_xlsx_bytes(df, sheet_name="Template")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="recruitment_{resource}_template.xlsx"'},
    )


@router.post("", response_model=schemas.TabularImportReport)
async def import_recruitment_resource(
    resource: str = Form(...),
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    if resource not in RECRUITMENT_IMPORT_COLUMNS:
        raise HTTPException(status_code=400, detail="Resource import recruitment invalide.")

    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        RECRUITMENT_IMPORT_COLUMNS[resource],
        RECRUITMENT_REQUIRED_COLUMNS[resource],
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
    employer_map = {item.raison_sociale.strip().lower(): item for item in employers}

    total_rows = 0
    processed_rows = 0
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    def _value(row: Any, column: str) -> Any:
        source_col = mapping.get(column)
        return row.get(source_col) if source_col else None

    for idx, row in df.iterrows():
        row_number = idx + 2
        if all((value is None or str(value).strip() == "" or str(value).lower() == "nan") for value in row.values):
            continue
        total_rows += 1

        employer_name = str(_value(row, "Employeur") or "").strip()
        employer = employer_map.get(employer_name.lower())
        if not employer:
            failed += 1
            _add_issue(
                issues,
                row_number=row_number,
                code="unknown_employer",
                message=f"Employeur introuvable: {employer_name}",
                column="Employeur",
                value=employer_name,
            )
            continue
        _assert_employer_scope(db, user, employer.id)

        try:
            with db.begin_nested():
                if resource == "candidates":
                    first_name = str(_value(row, "Prénom") or "").strip()
                    last_name = str(_value(row, "Nom") or "").strip()
                    email = str(_value(row, "Email") or "").strip().lower()
                    if not first_name or not last_name or not email:
                        raise ValueError("Prénom, nom et email sont obligatoires.")
                    existing = db.query(models.RecruitmentCandidate).filter(
                        models.RecruitmentCandidate.employer_id == employer.id,
                        models.RecruitmentCandidate.email == email,
                    ).first()
                    if existing:
                        if not update_existing:
                            skipped += 1
                            _add_issue(
                                issues,
                                row_number=row_number,
                                code="existing_skipped",
                                message=f"Candidat {email} déjà existant (ignoré).",
                            )
                            continue
                        existing.first_name = first_name
                        existing.last_name = last_name
                        existing.phone = str(_value(row, "Téléphone") or "").strip() or None
                        existing.education_level = str(_value(row, "Niveau Études") or "").strip() or None
                        existing.experience_years = float(_value(row, "Années Expérience") or 0.0)
                        existing.source = str(_value(row, "Source") or "").strip() or None
                        existing.status = str(_value(row, "Statut") or "new").strip() or "new"
                        existing.summary = str(_value(row, "Résumé") or "").strip() or None
                        updated += 1
                    else:
                        db.add(
                            models.RecruitmentCandidate(
                                employer_id=employer.id,
                                first_name=first_name,
                                last_name=last_name,
                                email=email,
                                phone=str(_value(row, "Téléphone") or "").strip() or None,
                                education_level=str(_value(row, "Niveau Études") or "").strip() or None,
                                experience_years=float(_value(row, "Années Expérience") or 0.0),
                                source=str(_value(row, "Source") or "").strip() or None,
                                status=str(_value(row, "Statut") or "new").strip() or "new",
                                summary=str(_value(row, "Résumé") or "").strip() or None,
                            )
                        )
                        created += 1
                else:
                    title = str(_value(row, "Intitulé") or "").strip()
                    if not title:
                        raise ValueError("Intitulé obligatoire.")
                    existing = db.query(models.RecruitmentJobPosting).filter(
                        models.RecruitmentJobPosting.employer_id == employer.id,
                        models.RecruitmentJobPosting.title == title,
                    ).first()
                    if existing:
                        if not update_existing:
                            skipped += 1
                            _add_issue(
                                issues,
                                row_number=row_number,
                                code="existing_skipped",
                                message=f"Poste {title} déjà existant (ignoré).",
                            )
                            continue
                        existing.department = str(_value(row, "Département") or "").strip() or None
                        existing.location = str(_value(row, "Localisation") or "").strip() or None
                        existing.contract_type = str(_value(row, "Type Contrat") or "CDI").strip() or "CDI"
                        existing.status = str(_value(row, "Statut") or "draft").strip() or "draft"
                        existing.salary_range = str(_value(row, "Fourchette Salaire") or "").strip() or None
                        existing.description = str(_value(row, "Description") or "").strip() or None
                        existing.skills_required = str(_value(row, "Compétences") or "").strip() or None
                        updated += 1
                    else:
                        db.add(
                            models.RecruitmentJobPosting(
                                employer_id=employer.id,
                                title=title,
                                department=str(_value(row, "Département") or "").strip() or None,
                                location=str(_value(row, "Localisation") or "").strip() or None,
                                contract_type=str(_value(row, "Type Contrat") or "CDI").strip() or "CDI",
                                status=str(_value(row, "Statut") or "draft").strip() or "draft",
                                salary_range=str(_value(row, "Fourchette Salaire") or "").strip() or None,
                                description=str(_value(row, "Description") or "").strip() or None,
                                skills_required=str(_value(row, "Compétences") or "").strip() or None,
                            )
                        )
                        created += 1
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
        record_audit(
            db,
            actor=user,
            action=f"recruitment.import.{resource}",
            entity_type="recruitment_import",
            entity_id=resource,
            route="/recruitment/import",
            after={
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "issues": len(issues),
            },
        )
        db.commit()

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
