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


router = APIRouter(prefix="/talents", tags=["talents"])

READ_ROLES = ("admin", "rh", "employeur", "manager", "employe")
WRITE_ROLES = ("admin", "rh", "employeur")


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh"):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == employer_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


TALENTS_IMPORT_COLUMNS = {
    "skills": [
        "Employeur",
        "Code",
        "Nom",
        "Description",
        "Echelle Max",
        "Actif (oui/non)",
    ],
    "trainings": [
        "Employeur",
        "Titre",
        "Organisme",
        "Durée (heures)",
        "Mode",
        "Prix",
        "Objectifs",
        "Statut",
    ],
    "employee-skills": [
        "Matricule",
        "Code Compétence",
        "Niveau",
        "Source",
    ],
}

TALENTS_REQUIRED_COLUMNS = {
    "skills": ["Code", "Nom"],
    "trainings": ["Titre"],
    "employee-skills": ["Matricule", "Code Compétence"],
}


def _talents_add_issue(
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


def _build_talents_template(
    *,
    resource: str,
    db: Session,
    user: models.AppUser,
    employer_id: Optional[int],
    prefilled: bool,
):
    import pandas as pd

    if resource not in TALENTS_IMPORT_COLUMNS:
        raise HTTPException(status_code=400, detail="Resource import talents invalide.")

    columns = TALENTS_IMPORT_COLUMNS[resource]
    if not prefilled:
        return pd.DataFrame(columns=columns)

    if resource in {"skills", "trainings"} and employer_id is None:
        raise HTTPException(status_code=400, detail="employer_id requis pour un template prérempli.")
    if employer_id is not None:
        _assert_employer_scope(db, user, employer_id)

    rows: list[dict[str, Any]] = []
    if resource == "skills":
        query = db.query(models.TalentSkill)
        if employer_id is not None:
            query = query.filter(models.TalentSkill.employer_id == employer_id)
        skills = query.order_by(models.TalentSkill.name.asc()).all()
        employer_ids = {item.employer_id for item in skills}
        employers = db.query(models.Employer).filter(models.Employer.id.in_(employer_ids)).all() if employer_ids else []
        employer_map = {item.id: item.raison_sociale for item in employers}
        for item in skills:
            rows.append(
                {
                    "Employeur": employer_map.get(item.employer_id, ""),
                    "Code": item.code,
                    "Nom": item.name,
                    "Description": item.description,
                    "Echelle Max": item.scale_max,
                    "Actif (oui/non)": "oui" if item.is_active else "non",
                }
            )
    elif resource == "trainings":
        query = db.query(models.TalentTraining)
        if employer_id is not None:
            query = query.filter(models.TalentTraining.employer_id == employer_id)
        trainings = query.order_by(models.TalentTraining.title.asc()).all()
        employer_ids = {item.employer_id for item in trainings}
        employers = db.query(models.Employer).filter(models.Employer.id.in_(employer_ids)).all() if employer_ids else []
        employer_map = {item.id: item.raison_sociale for item in employers}
        for item in trainings:
            rows.append(
                {
                    "Employeur": employer_map.get(item.employer_id, ""),
                    "Titre": item.title,
                    "Organisme": item.provider,
                    "Durée (heures)": item.duration_hours,
                    "Mode": item.mode,
                    "Prix": item.price,
                    "Objectifs": item.objectives,
                    "Statut": item.status,
                }
            )
    else:
        query = db.query(models.TalentEmployeeSkill).join(models.Worker, models.Worker.id == models.TalentEmployeeSkill.worker_id).join(
            models.TalentSkill, models.TalentSkill.id == models.TalentEmployeeSkill.skill_id
        )
        if employer_id is not None:
            query = query.filter(models.Worker.employer_id == employer_id)
        items = query.order_by(models.Worker.matricule.asc()).all()
        for item in items:
            rows.append(
                {
                    "Matricule": item.worker.matricule if item.worker else "",
                    "Code Compétence": item.skill.code if item.skill else "",
                    "Niveau": item.level,
                    "Source": item.source,
                }
            )

    return pd.DataFrame(rows, columns=columns)


def _resolve_employer_from_name(
    *,
    db: Session,
    user: models.AppUser,
    default_employer_id: Optional[int],
    name: str,
) -> Optional[models.Employer]:
    if default_employer_id is not None:
        employer = db.query(models.Employer).filter(models.Employer.id == default_employer_id).first()
        if employer:
            _assert_employer_scope(db, user, employer.id)
        return employer
    normalized = name.strip().lower()
    if not normalized:
        return None
    employer = db.query(models.Employer).filter(models.Employer.raison_sociale.ilike(name.strip())).first()
    if employer:
        _assert_employer_scope(db, user, employer.id)
    return employer


def _build_talents_report(
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


@router.get("/import/template")
def download_talents_template(
    resource: str = Query(..., pattern="^(skills|trainings|employee-skills)$"),
    employer_id: Optional[int] = Query(None),
    prefilled: bool = Query(False),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    df = _build_talents_template(
        resource=resource,
        db=db,
        user=user,
        employer_id=employer_id,
        prefilled=prefilled,
    )
    if export_format == "csv":
        content = dataframe_to_csv_bytes(df)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="talents_{resource}_template.csv"'},
        )
    content = dataframe_to_xlsx_bytes(df, sheet_name="Template")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="talents_{resource}_template.xlsx"'},
    )


@router.post("/import", response_model=schemas.TabularImportReport)
async def import_talents_resource(
    resource: str = Form(...),
    file: UploadFile = File(...),
    employer_id: Optional[int] = Form(None),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    if resource not in TALENTS_IMPORT_COLUMNS:
        raise HTTPException(status_code=400, detail="Resource import talents invalide.")
    if employer_id is not None:
        _assert_employer_scope(db, user, employer_id)

    content = await file.read()
    df = read_tabular_bytes(content, file.filename)
    mapping, unknown_columns, missing_columns = build_column_mapping(
        df.columns.tolist(),
        TALENTS_IMPORT_COLUMNS[resource],
        TALENTS_REQUIRED_COLUMNS[resource],
    )
    issues: list[dict[str, Any]] = []
    if unknown_columns:
        _talents_add_issue(
            issues,
            row_number=1,
            code="unknown_columns",
            message=f"Colonnes inconnues: {', '.join(unknown_columns)}",
        )
    if missing_columns:
        _talents_add_issue(
            issues,
            row_number=1,
            code="missing_columns",
            message=f"Colonnes obligatoires manquantes: {', '.join(missing_columns)}",
        )
    if unknown_columns or missing_columns:
        return _build_talents_report(
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

        try:
            with db.begin_nested():
                if resource == "skills":
                    code = str(_value(row, "Code") or "").strip()
                    name = str(_value(row, "Nom") or "").strip()
                    employer_name = str(_value(row, "Employeur") or "").strip()
                    employer = _resolve_employer_from_name(
                        db=db,
                        user=user,
                        default_employer_id=employer_id,
                        name=employer_name,
                    )
                    if not employer:
                        raise ValueError("Employeur introuvable.")
                    if not code or not name:
                        raise ValueError("Code et nom sont obligatoires.")
                    existing = db.query(models.TalentSkill).filter(
                        models.TalentSkill.employer_id == employer.id,
                        models.TalentSkill.code == code,
                    ).first()
                    active_raw = str(_value(row, "Actif (oui/non)") or "").strip().lower()
                    is_active = active_raw in {"", "oui", "yes", "true", "1"}
                    if existing:
                        if not update_existing:
                            skipped += 1
                            _talents_add_issue(
                                issues,
                                row_number=row_number,
                                code="existing_skipped",
                                message=f"Compétence {code} déjà existante (ignorée).",
                                column="Code",
                                value=code,
                            )
                            continue
                        existing.name = name
                        existing.description = str(_value(row, "Description") or "").strip() or None
                        existing.scale_max = int(float(_value(row, "Echelle Max") or 5))
                        existing.is_active = is_active
                        updated += 1
                    else:
                        db.add(
                            models.TalentSkill(
                                employer_id=employer.id,
                                code=code,
                                name=name,
                                description=str(_value(row, "Description") or "").strip() or None,
                                scale_max=int(float(_value(row, "Echelle Max") or 5)),
                                is_active=is_active,
                            )
                        )
                        created += 1
                elif resource == "trainings":
                    title = str(_value(row, "Titre") or "").strip()
                    employer_name = str(_value(row, "Employeur") or "").strip()
                    employer = _resolve_employer_from_name(
                        db=db,
                        user=user,
                        default_employer_id=employer_id,
                        name=employer_name,
                    )
                    if not employer:
                        raise ValueError("Employeur introuvable.")
                    if not title:
                        raise ValueError("Titre obligatoire.")
                    existing = db.query(models.TalentTraining).filter(
                        models.TalentTraining.employer_id == employer.id,
                        models.TalentTraining.title == title,
                    ).first()
                    if existing:
                        if not update_existing:
                            skipped += 1
                            _talents_add_issue(
                                issues,
                                row_number=row_number,
                                code="existing_skipped",
                                message=f"Formation {title} déjà existante (ignorée).",
                                column="Titre",
                                value=title,
                            )
                            continue
                        existing.provider = str(_value(row, "Organisme") or "").strip() or None
                        existing.duration_hours = float(_value(row, "Durée (heures)") or 0.0)
                        existing.mode = str(_value(row, "Mode") or "").strip() or None
                        existing.price = float(_value(row, "Prix") or 0.0)
                        existing.objectives = str(_value(row, "Objectifs") or "").strip() or None
                        existing.status = str(_value(row, "Statut") or "").strip() or "draft"
                        updated += 1
                    else:
                        db.add(
                            models.TalentTraining(
                                employer_id=employer.id,
                                title=title,
                                provider=str(_value(row, "Organisme") or "").strip() or None,
                                duration_hours=float(_value(row, "Durée (heures)") or 0.0),
                                mode=str(_value(row, "Mode") or "").strip() or None,
                                price=float(_value(row, "Prix") or 0.0),
                                objectives=str(_value(row, "Objectifs") or "").strip() or None,
                                status=str(_value(row, "Statut") or "").strip() or "draft",
                            )
                        )
                        created += 1
                else:
                    matricule = str(_value(row, "Matricule") or "").strip()
                    skill_code = str(_value(row, "Code Compétence") or "").strip()
                    if not matricule or not skill_code:
                        raise ValueError("Matricule et code compétence obligatoires.")
                    worker = db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
                    if not worker or not can_manage_worker(db, user, worker=worker):
                        raise ValueError(f"Salarié introuvable ou hors périmètre: {matricule}.")
                    skill = db.query(models.TalentSkill).filter(
                        models.TalentSkill.code == skill_code,
                        models.TalentSkill.employer_id == worker.employer_id,
                    ).first()
                    if not skill:
                        raise ValueError(f"Compétence introuvable: {skill_code}.")
                    existing = db.query(models.TalentEmployeeSkill).filter(
                        models.TalentEmployeeSkill.worker_id == worker.id,
                        models.TalentEmployeeSkill.skill_id == skill.id,
                    ).first()
                    level = int(float(_value(row, "Niveau") or 1))
                    source = str(_value(row, "Source") or "manager").strip() or "manager"
                    if existing:
                        if not update_existing:
                            skipped += 1
                            _talents_add_issue(
                                issues,
                                row_number=row_number,
                                code="existing_skipped",
                                message=f"Compétence déjà affectée à {matricule} (ignorée).",
                            )
                            continue
                        existing.level = level
                        existing.source = source
                        updated += 1
                    else:
                        db.add(
                            models.TalentEmployeeSkill(
                                worker_id=worker.id,
                                skill_id=skill.id,
                                level=level,
                                source=source,
                            )
                        )
                        created += 1

                processed_rows += 1
        except Exception as exc:
            failed += 1
            _talents_add_issue(
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
            action=f"talents.import.{resource}",
            entity_type="talents_import",
            entity_id=f"{resource}:{employer_id or 'all'}",
            route="/talents/import",
            employer_id=employer_id,
            after={
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "issues": len(issues),
            },
        )
        db.commit()

    return _build_talents_report(
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


@router.get("/skills", response_model=list[schemas.TalentSkillOut])
def list_skills(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentSkill)
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.TalentSkill.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.TalentSkill.employer_id == employer_id)
    return query.order_by(models.TalentSkill.name.asc()).all()


@router.post("/skills", response_model=schemas.TalentSkillOut)
def create_skill(
    payload: schemas.TalentSkillCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.TalentSkill(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.skill.create",
        entity_type="talent_skill",
        entity_id=item.id,
        route="/talents/skills",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/skills/{skill_id}", response_model=schemas.TalentSkillOut)
def update_skill(
    skill_id: int,
    payload: schemas.TalentSkillUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TalentSkill).filter(models.TalentSkill.id == skill_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Skill not found")
    _assert_employer_scope(db, user, item.employer_id)
    before = {"name": item.name, "code": item.code, "is_active": item.is_active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="talents.skill.update",
        entity_type="talent_skill",
        entity_id=item.id,
        route=f"/talents/skills/{skill_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/employee-skills", response_model=list[schemas.TalentEmployeeSkillOut])
def list_employee_skills(
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentEmployeeSkill)
    if worker_id:
        worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
        if not worker or not can_access_worker(db, user, worker):
            raise HTTPException(status_code=403, detail="Forbidden")
        query = query.filter(models.TalentEmployeeSkill.worker_id == worker_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.TalentEmployeeSkill.worker_id == user.worker_id)
    return query.order_by(models.TalentEmployeeSkill.updated_at.desc()).all()


@router.post("/employee-skills", response_model=schemas.TalentEmployeeSkillOut)
def create_employee_skill(
    payload: schemas.TalentEmployeeSkillCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    worker = db.query(models.Worker).filter(models.Worker.id == payload.worker_id).first()
    skill = db.query(models.TalentSkill).filter(models.TalentSkill.id == payload.skill_id).first()
    if not worker or not skill:
        raise HTTPException(status_code=404, detail="Worker or skill not found")
    if not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    item = models.TalentEmployeeSkill(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.employee_skill.create",
        entity_type="talent_employee_skill",
        entity_id=item.id,
        route="/talents/employee-skills",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/employee-skills/{employee_skill_id}", response_model=schemas.TalentEmployeeSkillOut)
def update_employee_skill(
    employee_skill_id: int,
    payload: schemas.TalentEmployeeSkillUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TalentEmployeeSkill).filter(models.TalentEmployeeSkill.id == employee_skill_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Employee skill not found")
    worker = db.query(models.Worker).filter(models.Worker.id == item.worker_id).first()
    if not worker or not can_manage_worker(db, user, worker=worker):
        raise HTTPException(status_code=403, detail="Forbidden")
    before = {"level": item.level, "source": item.source}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="talents.employee_skill.update",
        entity_type="talent_employee_skill",
        entity_id=item.id,
        route=f"/talents/employee-skills/{employee_skill_id}",
        employer_id=worker.employer_id,
        worker_id=worker.id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/trainings", response_model=list[schemas.TalentTrainingOut])
def list_trainings(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentTraining)
    if user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.TalentTraining.employer_id == user.employer_id)
    elif employer_id:
        query = query.filter(models.TalentTraining.employer_id == employer_id)
    return query.order_by(models.TalentTraining.updated_at.desc()).all()


@router.post("/trainings", response_model=schemas.TalentTrainingOut)
def create_training(
    payload: schemas.TalentTrainingCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    item = models.TalentTraining(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.training.create",
        entity_type="talent_training",
        entity_id=item.id,
        route="/talents/trainings",
        employer_id=item.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/trainings/{training_id}", response_model=schemas.TalentTrainingOut)
def update_training(
    training_id: int,
    payload: schemas.TalentTrainingUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    item = db.query(models.TalentTraining).filter(models.TalentTraining.id == training_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Training not found")
    _assert_employer_scope(db, user, item.employer_id)
    before = {"title": item.title, "status": item.status}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit(
        db,
        actor=user,
        action="talents.training.update",
        entity_type="talent_training",
        entity_id=item.id,
        route=f"/talents/trainings/{training_id}",
        employer_id=item.employer_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/training-sessions", response_model=list[schemas.TalentTrainingSessionOut])
def list_training_sessions(
    training_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.TalentTrainingSession)
    if training_id:
        query = query.filter(models.TalentTrainingSession.training_id == training_id)
    return query.order_by(models.TalentTrainingSession.start_date.desc()).all()


@router.post("/training-sessions", response_model=schemas.TalentTrainingSessionOut)
def create_training_session(
    payload: schemas.TalentTrainingSessionCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_ROLES)),
):
    training = db.query(models.TalentTraining).filter(models.TalentTraining.id == payload.training_id).first()
    if not training:
        raise HTTPException(status_code=404, detail="Training not found")
    _assert_employer_scope(db, user, training.employer_id)
    item = models.TalentTrainingSession(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="talents.training_session.create",
        entity_type="talent_training_session",
        entity_id=item.id,
        route="/talents/training-sessions",
        employer_id=training.employer_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return item
