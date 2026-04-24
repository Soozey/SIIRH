import hashlib
import json
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models, schemas
from ..security import get_user_active_role_codes, get_user_effective_base_roles
from .file_storage import build_static_path, sanitize_filename_part, save_upload_file
from .master_data_service import build_worker_master_view, sync_worker_master_data


SECTION_TITLES = {
    "identity": "Identité",
    "administration_contract": "Administration & contrat",
    "recruitment": "Recrutement",
    "health": "Santé au travail",
    "affiliations": "Affiliations sociales et fiscales",
    "payroll": "Paie & rémunération",
    "time_absence": "Temps de travail / congés / absences",
    "career": "Carrière & mobilité",
    "disciplinary": "Disciplinaire / litiges",
    "exit": "Fin de contrat / sortie",
    "documents": "Documents",
}

FULL_READ_BASE_ROLES = {"admin", "rh", "employeur", "direction", "juridique", "audit", "inspecteur"}
FULL_WRITE_BASE_ROLES = {"admin", "rh", "employeur"}
PAYROLL_READ_BASE_ROLES = {"comptable"}
MANAGER_READ_BASE_ROLES = {"manager", "departement"}
EMPLOYEE_READ_BASE_ROLES = {"employe"}
FULL_READ_ACTIVE_ROLE_CODES = {"hr_manager", "hr_officer", "employer_admin", "labor_inspector", "labor_inspector_supervisor"}


def _load_json(raw: Optional[str], fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _safe_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _file_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_hr_dossier_access_scope(db: Session, user: models.AppUser, worker: models.Worker) -> str:
    active_role_codes = {role.strip().lower() for role in get_user_active_role_codes(db, user)}
    primary_role = (user.role_code or "").strip().lower()
    if primary_role:
        active_role_codes.add(primary_role)
    base_roles = get_user_effective_base_roles(db, user)

    if base_roles.intersection(FULL_READ_BASE_ROLES) or active_role_codes.intersection(FULL_READ_ACTIVE_ROLE_CODES):
        return "full"
    if base_roles.intersection(PAYROLL_READ_BASE_ROLES):
        return "payroll"
    if base_roles.intersection(MANAGER_READ_BASE_ROLES):
        return "manager"
    if base_roles.intersection(EMPLOYEE_READ_BASE_ROLES) or "employee" in active_role_codes:
        return "self" if user.worker_id == worker.id else "none"
    return "none"


def can_write_hr_dossier(db: Session, user: models.AppUser, worker: models.Worker) -> bool:
    active_role_codes = {role.strip().lower() for role in get_user_active_role_codes(db, user)}
    primary_role = (user.role_code or "").strip().lower()
    if primary_role:
        active_role_codes.add(primary_role)
    base_roles = get_user_effective_base_roles(db, user)
    if base_roles.intersection(FULL_WRITE_BASE_ROLES):
        return True
    return bool(active_role_codes.intersection({"hr_manager", "hr_officer", "employer_admin"}))


def ensure_hr_employee_file(db: Session, worker: models.Worker, actor: Optional[models.AppUser] = None) -> models.HrEmployeeFile:
    item = db.query(models.HrEmployeeFile).filter(models.HrEmployeeFile.worker_id == worker.id).first()
    if item:
        if item.employer_id != worker.employer_id:
            item.employer_id = worker.employer_id
        return item
    item = models.HrEmployeeFile(
        employer_id=worker.employer_id,
        worker_id=worker.id,
        created_by_user_id=actor.id if actor else None,
        updated_by_user_id=actor.id if actor else None,
    )
    db.add(item)
    db.flush()
    return item


def _append_event(
    db: Session,
    *,
    worker: models.Worker,
    hr_file: models.HrEmployeeFile,
    actor: Optional[models.AppUser],
    section_code: str,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    status: str = "recorded",
    source_module: str = "hr_dossier",
    source_record_type: Optional[str] = None,
    source_record_id: Optional[int] = None,
    payload: Optional[dict[str, Any]] = None,
    event_date: Optional[datetime] = None,
) -> models.HrEmployeeEvent:
    event = models.HrEmployeeEvent(
        employer_id=worker.employer_id,
        worker_id=worker.id,
        hr_file_id=hr_file.id,
        section_code=section_code,
        event_type=event_type,
        title=title,
        description=description,
        status=status,
        event_date=event_date or _now_naive(),
        source_module=source_module,
        source_record_type=source_record_type,
        source_record_id=source_record_id,
        payload_json=_dump_json(payload or {}),
        created_by_user_id=actor.id if actor else None,
    )
    db.add(event)
    db.flush()
    return event


def update_hr_dossier_section(
    db: Session,
    *,
    worker: models.Worker,
    section_key: str,
    data: dict[str, Any],
    actor: models.AppUser,
) -> models.HrEmployeeFile:
    hr_file = ensure_hr_employee_file(db, worker, actor)
    manual_sections = _load_json(hr_file.manual_sections_json, {})
    manual_sections[section_key] = data or {}
    hr_file.manual_sections_json = _dump_json(manual_sections)
    hr_file.revision_number = (hr_file.revision_number or 0) + 1
    hr_file.updated_by_user_id = actor.id
    db.flush()
    _append_event(
        db,
        worker=worker,
        hr_file=hr_file,
        actor=actor,
        section_code=section_key,
        event_type="section_updated",
        title=f"Mise à jour de la section {SECTION_TITLES.get(section_key, section_key)}",
        payload={"section_key": section_key, "keys": sorted((data or {}).keys())},
    )
    return hr_file


def _document_can_be_seen(document: schemas.HrDossierDocumentOut, access_scope: str) -> bool:
    if access_scope == "full":
        return True
    if access_scope == "payroll":
        return document.visible_to_payroll or document.section_code in {"administration_contract", "affiliations", "payroll"}
    if access_scope == "manager":
        return document.visible_to_manager or document.section_code in {"career", "time_absence"}
    if access_scope == "self":
        return document.metadata.get("visible_to_employee", False) or document.section_code in {"identity", "documents"}
    return False


def _section_out(key: str, source: str, data: dict[str, Any]) -> schemas.HrDossierSectionOut:
    return schemas.HrDossierSectionOut(key=key, title=SECTION_TITLES.get(key, key), source=source, data=data)


def _virtual_document(
    *,
    id_value: str,
    title: str,
    section_code: str,
    document_type: str,
    source_module: str,
    source_record_type: Optional[str],
    source_record_id: Optional[int],
    document_date: Any = None,
    expiration_date: Any = None,
    download_url: Optional[str] = None,
    preview_url: Optional[str] = None,
    can_preview: bool = False,
    status: str = "linked",
    metadata: Optional[dict[str, Any]] = None,
) -> schemas.HrDossierDocumentOut:
    expiration_str = _iso_date(expiration_date)
    is_expired = False
    if isinstance(expiration_date, date):
        is_expired = expiration_date < date.today()
    return schemas.HrDossierDocumentOut(
        id=id_value,
        title=title,
        section_code=section_code,
        document_type=document_type,
        status=status,
        source_module=source_module,
        source_record_type=source_record_type,
        source_record_id=source_record_id,
        document_date=_iso_date(document_date),
        expiration_date=expiration_str,
        is_expired=is_expired,
        can_preview=can_preview,
        download_url=download_url,
        preview_url=preview_url,
        metadata=metadata or {},
    )


def _build_uploaded_documents(
    db: Session,
    *,
    worker: models.Worker,
) -> list[schemas.HrDossierDocumentOut]:
    items = (
        db.query(models.HrEmployeeDocument)
        .filter(models.HrEmployeeDocument.worker_id == worker.id)
        .order_by(models.HrEmployeeDocument.updated_at.desc(), models.HrEmployeeDocument.id.desc())
        .all()
    )
    documents: list[schemas.HrDossierDocumentOut] = []
    for item in items:
        versions = sorted(item.versions, key=lambda version: version.version_number, reverse=True)
        current_version = versions[0] if versions else None
        preview_url = build_static_path(current_version.storage_path) if current_version else None
        can_preview = bool(current_version and (current_version.mime_type or "").startswith("image/")) or bool(
            current_version and (current_version.mime_type or "").startswith("application/pdf")
        )
        version_items = [
            schemas.HrDossierDocumentVersionOut(
                id=f"{version.id}",
                version_number=version.version_number,
                original_name=version.original_name,
                mime_type=version.mime_type,
                file_size=version.file_size,
                created_at=version.created_at,
                created_by_user_id=version.created_by_user_id,
            )
            for version in versions
        ]
        is_expired = bool(item.expiration_date and item.expiration_date < date.today())
        documents.append(
            schemas.HrDossierDocumentOut(
                id=str(item.id),
                title=item.title,
                section_code=item.section_code,
                document_type=item.document_type,
                status=item.status,
                source_module=item.source_module,
                source_record_type=item.source_record_type,
                source_record_id=item.source_record_id,
                document_date=_iso_date(item.document_date),
                expiration_date=_iso_date(item.expiration_date),
                is_expired=is_expired,
                comment=item.comment,
                visibility_scope=item.visibility_scope,
                can_preview=can_preview,
                download_url=f"/master-data/workers/{worker.id}/hr-dossier/documents/{item.id}/download",
                preview_url=preview_url,
                current_version_number=item.current_version_number,
                metadata={
                    **_load_json(item.metadata_json, {}),
                    "visible_to_employee": item.visible_to_employee,
                    "visible_to_manager": item.visible_to_manager,
                    "visible_to_payroll": item.visible_to_payroll,
                },
                versions=version_items,
            )
        )
    return documents


def _build_source_documents(db: Session, worker: models.Worker, master_view: schemas.MasterDataWorkerViewOut) -> list[schemas.HrDossierDocumentOut]:
    documents: list[schemas.HrDossierDocumentOut] = []

    candidate_id = master_view.recruitment.get("candidate", {}).get("id") if master_view.recruitment else None
    if candidate_id:
        candidate = db.query(models.RecruitmentCandidate).filter(models.RecruitmentCandidate.id == candidate_id).first()
        if candidate and candidate.cv_file_path:
            static_path = build_static_path(candidate.cv_file_path)
            documents.append(
                _virtual_document(
                    id_value=f"recruitment-cv-{candidate.id}",
                    title=f"CV - {candidate.first_name} {candidate.last_name}",
                    section_code="recruitment",
                    document_type="cv",
                    source_module="recruitment",
                    source_record_type="candidate",
                    source_record_id=candidate.id,
                    document_date=candidate.updated_at,
                    download_url=static_path,
                    preview_url=static_path,
                    can_preview=True,
                    metadata={"visible_to_employee": False, "visible_to_manager": True, "visible_to_payroll": False},
                )
            )

    contract = (
        db.query(models.CustomContract)
        .filter(models.CustomContract.worker_id == worker.id)
        .order_by(models.CustomContract.updated_at.desc())
        .first()
    )
    if contract:
        documents.append(
            _virtual_document(
                id_value=f"contract-{contract.id}",
                title=contract.title or "Contrat de travail",
                section_code="administration_contract",
                document_type="contract",
                source_module="contracts",
                source_record_type="custom_contract",
                source_record_id=contract.id,
                document_date=contract.updated_at,
                can_preview=False,
                metadata={"visible_to_employee": True, "visible_to_manager": True, "visible_to_payroll": True},
            )
        )

    for case in db.query(models.DisciplinaryCase).filter(models.DisciplinaryCase.worker_id == worker.id).order_by(models.DisciplinaryCase.updated_at.desc()).all():
        for index, item in enumerate(_load_json(case.documents_json, []), start=1):
            payload = item if isinstance(item, dict) else {"name": str(item)}
            documents.append(
                _virtual_document(
                    id_value=f"disciplinary-{case.id}-{index}",
                    title=payload.get("title") or payload.get("name") or case.subject,
                    section_code="disciplinary",
                    document_type="sanction",
                    source_module="people_ops",
                    source_record_type="disciplinary_case",
                    source_record_id=case.id,
                    document_date=case.updated_at,
                    metadata={"visible_to_employee": False, "visible_to_manager": False, "visible_to_payroll": False, **payload},
                )
            )

    for workflow in db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.worker_id == worker.id).order_by(models.TerminationWorkflow.updated_at.desc()).all():
        for index, item in enumerate(_load_json(workflow.documents_json, []), start=1):
            payload = item if isinstance(item, dict) else {"name": str(item)}
            title = payload.get("title") or payload.get("name") or f"Document de sortie {index}"
            documents.append(
                _virtual_document(
                    id_value=f"termination-{workflow.id}-{index}",
                    title=title,
                    section_code="exit",
                    document_type="exit_document",
                    source_module="people_ops",
                    source_record_type="termination_workflow",
                    source_record_id=workflow.id,
                    document_date=workflow.updated_at,
                    metadata={"visible_to_employee": True, "visible_to_manager": False, "visible_to_payroll": True, **payload},
                )
            )
    return documents


def _build_fixed_primes(db: Session, worker: models.Worker) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    links = (
        db.query(models.WorkerPrimeLink)
        .filter(models.WorkerPrimeLink.worker_id == worker.id, models.WorkerPrimeLink.is_active.is_(True))
        .all()
    )
    for link in links:
        if link.prime:
            items.append({"id": link.prime.id, "label": link.prime.label, "mode": "global", "active": True})
    for item in db.query(models.WorkerPrime).filter(models.WorkerPrime.worker_id == worker.id, models.WorkerPrime.is_active.is_(True)).all():
        items.append({"id": item.id, "label": item.label, "mode": "worker", "active": True})
    return items


def _build_sections(
    db: Session,
    *,
    worker: models.Worker,
    master_view: schemas.MasterDataWorkerViewOut,
    manual_sections: dict[str, Any],
) -> dict[str, schemas.HrDossierSectionOut]:
    identity_data = dict(master_view.identity.data)
    identity_data.update(manual_sections.get("identity", {}))

    administration_contract = {
        "employeur_juridique": worker.employer.raison_sociale if worker.employer else None,
        "etablissement": master_view.organization.data.get("establishment"),
        "departement": master_view.organization.data.get("department"),
        "service": master_view.organization.data.get("service"),
        "unite": master_view.organization.data.get("unit"),
        "poste": master_view.employment.data.get("job_title"),
        "categorie_professionnelle": master_view.employment.data.get("professional_category"),
        "indice_classification": master_view.employment.data.get("classification_index"),
        "type_contrat": master_view.employment.data.get("contract_type"),
        "date_effet_contrat": master_view.contract.get("created_at"),
        "date_fin_contrat": master_view.contract.get("end_date"),
        "periode_essai_jours": master_view.employment.data.get("trial_period_days"),
        "date_fin_essai": master_view.employment.data.get("trial_end_date"),
        "manager": manual_sections.get("administration_contract", {}).get("manager"),
        "statut_salarie": master_view.employment.data.get("employment_status"),
    }
    administration_contract.update(manual_sections.get("administration_contract", {}))

    recruitment_section = {
        "source_recrutement": master_view.recruitment.get("candidate", {}).get("source"),
        "fiche_de_poste": master_view.recruitment.get("job_profile", {}).get("title")
        or master_view.recruitment.get("job_posting", {}).get("title"),
        "note_decision_embauche": master_view.recruitment.get("decision", {}).get("comment")
        or master_view.recruitment.get("decision", {}).get("decision"),
        "date_prevue_entree": master_view.recruitment.get("decision", {}).get("expected_start_date"),
        "date_reelle_entree": master_view.employment.data.get("hire_date"),
    }
    recruitment_section.update(manual_sections.get("recruitment", {}))

    incidents = db.query(models.SstIncident).filter(models.SstIncident.worker_id == worker.id).order_by(models.SstIncident.occurred_at.desc()).all()
    health_section = {
        "visite_medicale_embauche": manual_sections.get("health", {}).get("visite_medicale_embauche"),
        "date_visite": manual_sections.get("health", {}).get("date_visite"),
        "resultat_aptitude": manual_sections.get("health", {}).get("resultat_aptitude"),
        "observations": manual_sections.get("health", {}).get("observations"),
        "visites_periodiques": manual_sections.get("health", {}).get("visites_periodiques", []),
        "accidents_maladies": [
            {
                "id": item.id,
                "type": item.incident_type,
                "gravite": item.severity,
                "statut": item.status,
                "date": _iso_date(item.occurred_at),
                "description": item.description,
            }
            for item in incidents[:10]
        ],
    }
    health_section.update(manual_sections.get("health", {}))

    affiliations_section = {
        "numero_cnaps": identity_data.get("cnaps_number") or worker.cnaps_num,
        "ostie_smie": worker.smie_carte_num or worker.smie_agence,
        "nif": manual_sections.get("affiliations", {}).get("nif"),
        "personnes_a_charge": worker.nombre_enfant,
        "pieces_justificatives": manual_sections.get("affiliations", {}).get("pieces_justificatives", []),
    }
    affiliations_section.update(manual_sections.get("affiliations", {}))

    payroll_section = {
        "salaire_base": master_view.compensation.data.get("salary_base"),
        "salaire_valide": master_view.compensation.data.get("validated_salary_amount"),
        "primes_fixes": _build_fixed_primes(db, worker),
        "indemnites_fixes": manual_sections.get("payroll", {}).get("indemnites_fixes", []),
        "avantages_en_nature": master_view.compensation.data.get("benefits", {}),
        "mode_paiement": master_view.compensation.data.get("payment_mode"),
        "banque": master_view.compensation.data.get("bank_name"),
        "reference_bancaire": master_view.compensation.data.get("rib"),
        "historique_remuneration": [
            {
                "contract_version_id": item.get("id"),
                "version": item.get("version_number"),
                "salary_amount": item.get("salary_amount"),
                "effective_date": item.get("effective_date"),
            }
            for item in master_view.contract_versions
        ],
    }
    payroll_section.update(manual_sections.get("payroll", {}))

    leave_requests = db.query(models.LeaveRequest).filter(models.LeaveRequest.worker_id == worker.id).all()
    absences = db.query(models.Absence).filter(models.Absence.worker_id == worker.id).all()
    permissions = db.query(models.Permission).filter(models.Permission.worker_id == worker.id).all()
    time_absence_section = {
        "horaire_travail": master_view.compensation.data.get("weekly_hours"),
        "type_horaire": manual_sections.get("time_absence", {}).get("type_horaire"),
        "conges_acquis": worker.solde_conge_initial,
        "conges_pris": len(leave_requests),
        "solde_conges": manual_sections.get("time_absence", {}).get("solde_conges"),
        "permissions": len(permissions),
        "absences": len(absences),
        "amenagements_horaires": manual_sections.get("time_absence", {}).get("amenagements_horaires"),
    }
    time_absence_section.update(manual_sections.get("time_absence", {}))

    performance_reviews = db.query(models.PerformanceReview).filter(models.PerformanceReview.worker_id == worker.id).order_by(models.PerformanceReview.updated_at.desc()).all()
    training_items = db.query(models.TrainingPlanItem).filter(models.TrainingPlanItem.worker_id == worker.id).order_by(models.TrainingPlanItem.updated_at.desc()).all()
    skill_items = db.query(models.TalentEmployeeSkill).filter(models.TalentEmployeeSkill.worker_id == worker.id).all()
    career_section = {
        "promotions_mutations": [
            {
                "id": item.id,
                "poste": item.poste,
                "categorie": item.categorie_prof,
                "indice": item.indice,
                "debut": _iso_date(item.start_date),
                "fin": _iso_date(item.end_date),
            }
            for item in worker.position_history
        ],
        "formations": [
            {
                "id": item.id,
                "training_id": item.training_id,
                "status": item.status,
                "debut": _iso_date(item.scheduled_start),
                "fin": _iso_date(item.scheduled_end),
            }
            for item in training_items
        ],
        "evaluations": [
            {
                "id": item.id,
                "status": item.status,
                "score": item.overall_score,
                "promotion_recommendation": item.promotion_recommendation,
                "updated_at": _iso_date(item.updated_at),
            }
            for item in performance_reviews
        ],
        "competences_habilitations": [
            {
                "skill": item.skill.name if item.skill else None,
                "level": item.level,
                "source": item.source,
            }
            for item in skill_items
        ],
    }
    career_section.update(manual_sections.get("career", {}))

    disciplinary_cases = db.query(models.DisciplinaryCase).filter(models.DisciplinaryCase.worker_id == worker.id).order_by(models.DisciplinaryCase.updated_at.desc()).all()
    disciplinary_section = {
        "avertissements_sanctions": [
            {
                "id": item.id,
                "type": item.case_type,
                "sujet": item.subject,
                "statut": item.status,
                "sanction": item.sanction_type,
                "date": _iso_date(item.happened_at),
            }
            for item in disciplinary_cases
        ],
        "observations_salarie": manual_sections.get("disciplinary", {}).get("observations_salarie", []),
    }
    disciplinary_section.update(manual_sections.get("disciplinary", {}))

    latest_exit = db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.worker_id == worker.id).order_by(models.TerminationWorkflow.updated_at.desc()).first()
    exit_section = {
        "motif_sortie": latest_exit.motif if latest_exit else worker.type_sortie,
        "date_sortie": _iso_date(latest_exit.effective_date) if latest_exit else _iso_date(worker.date_debauche),
        "preavis": _iso_date(latest_exit.preavis_start_date) if latest_exit else worker.jours_preavis_deja_faits,
        "certificat_travail": bool(latest_exit and _load_json(latest_exit.documents_json, [])),
        "solde_tout_compte": _load_json(latest_exit.readonly_stc_json, {}) if latest_exit else {},
        "pieces_cloture": _load_json(latest_exit.documents_json, []) if latest_exit else [],
    }
    exit_section.update(manual_sections.get("exit", {}))

    return {
        "identity": _section_out("identity", "linked+manual", identity_data),
        "administration_contract": _section_out("administration_contract", "linked+manual", administration_contract),
        "recruitment": _section_out("recruitment", "linked+manual", recruitment_section),
        "health": _section_out("health", "manual+sst", health_section),
        "affiliations": _section_out("affiliations", "linked+manual", affiliations_section),
        "payroll": _section_out("payroll", "linked+manual", payroll_section),
        "time_absence": _section_out("time_absence", "linked+manual", time_absence_section),
        "career": _section_out("career", "linked+manual", career_section),
        "disciplinary": _section_out("disciplinary", "linked+manual", disciplinary_section),
        "exit": _section_out("exit", "linked+manual", exit_section),
        "documents": _section_out("documents", "linked", {"count": 0}),
    }


def _build_timeline(db: Session, *, worker: models.Worker, hr_file: models.HrEmployeeFile) -> list[schemas.HrDossierTimelineEventOut]:
    timeline: list[schemas.HrDossierTimelineEventOut] = []

    for event in db.query(models.HrEmployeeEvent).filter(models.HrEmployeeEvent.worker_id == worker.id).order_by(models.HrEmployeeEvent.event_date.desc()).limit(50).all():
        timeline.append(
            schemas.HrDossierTimelineEventOut(
                id=f"manual-{event.id}",
                section_code=event.section_code,
                event_type=event.event_type,
                title=event.title,
                description=event.description,
                status=event.status,
                event_date=_iso_date(event.event_date),
                source_module=event.source_module,
                source_record_type=event.source_record_type,
                source_record_id=event.source_record_id,
                payload=_load_json(event.payload_json, {}),
            )
        )

    for contract in db.query(models.CustomContract).filter(models.CustomContract.worker_id == worker.id).order_by(models.CustomContract.updated_at.desc()).limit(10).all():
        timeline.append(
            schemas.HrDossierTimelineEventOut(
                id=f"contract-{contract.id}",
                section_code="administration_contract",
                event_type="contract_update",
                title=contract.title or "Contrat de travail",
                description=f"Statut validation: {contract.validation_status}",
                status=contract.validation_status,
                event_date=_iso_date(contract.updated_at),
                source_module="contracts",
                source_record_type="custom_contract",
                source_record_id=contract.id,
                payload={"template_type": contract.template_type, "active_version_number": contract.active_version_number},
            )
        )

    for item in worker.position_history:
        timeline.append(
            schemas.HrDossierTimelineEventOut(
                id=f"position-{item.id}",
                section_code="career",
                event_type="position_change",
                title=item.poste,
                description=f"Categorie: {item.categorie_prof or '-'} | Indice: {item.indice or '-'}",
                status="historique",
                event_date=_iso_date(item.start_date),
                source_module="workforce",
                source_record_type="worker_position_history",
                source_record_id=item.id,
                payload={"end_date": _iso_date(item.end_date)},
            )
        )

    for review in db.query(models.PerformanceReview).filter(models.PerformanceReview.worker_id == worker.id).order_by(models.PerformanceReview.updated_at.desc()).limit(10).all():
        timeline.append(
            schemas.HrDossierTimelineEventOut(
                id=f"review-{review.id}",
                section_code="career",
                event_type="performance_review",
                title="Evaluation de performance",
                description=review.manager_comment or review.hr_comment,
                status=review.status,
                event_date=_iso_date(review.updated_at),
                source_module="talents",
                source_record_type="performance_review",
                source_record_id=review.id,
                payload={"score": review.overall_score, "promotion_recommendation": review.promotion_recommendation},
            )
        )

    for case in db.query(models.DisciplinaryCase).filter(models.DisciplinaryCase.worker_id == worker.id).order_by(models.DisciplinaryCase.updated_at.desc()).limit(10).all():
        timeline.append(
            schemas.HrDossierTimelineEventOut(
                id=f"disciplinary-{case.id}",
                section_code="disciplinary",
                event_type="disciplinary_case",
                title=case.subject,
                description=case.description,
                status=case.status,
                event_date=_iso_date(case.updated_at),
                source_module="people_ops",
                source_record_type="disciplinary_case",
                source_record_id=case.id,
                payload={"case_type": case.case_type, "sanction_type": case.sanction_type},
            )
        )

    latest_exit = db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.worker_id == worker.id).order_by(models.TerminationWorkflow.updated_at.desc()).first()
    if latest_exit:
        timeline.append(
            schemas.HrDossierTimelineEventOut(
                id=f"exit-{latest_exit.id}",
                section_code="exit",
                event_type="termination_workflow",
                title=latest_exit.termination_type,
                description=latest_exit.motif,
                status=latest_exit.status,
                event_date=_iso_date(latest_exit.updated_at),
                source_module="people_ops",
                source_record_type="termination_workflow",
                source_record_id=latest_exit.id,
                payload={"effective_date": _iso_date(latest_exit.effective_date)},
            )
        )

    timeline.sort(key=lambda item: item.event_date or "", reverse=True)
    return timeline[:60]


def _build_completeness(
    *,
    sections: dict[str, schemas.HrDossierSectionOut],
    documents: list[schemas.HrDossierDocumentOut],
) -> tuple[schemas.HrDossierCompletenessOut, list[schemas.HrDossierAlertOut]]:
    alerts: list[schemas.HrDossierAlertOut] = []
    checks = {
        "matricule": bool(sections["identity"].data.get("employee_number")),
        "nom_prenom": bool(sections["identity"].data.get("first_name") and sections["identity"].data.get("last_name")),
        "cin": bool(sections["identity"].data.get("cin_number")),
        "date_naissance": bool(sections["identity"].data.get("birth_date")),
        "adresse": bool(sections["identity"].data.get("address")),
        "date_embauche": bool(sections["administration_contract"].data.get("date_effet_contrat") or sections["administration_contract"].data.get("type_contrat") or sections["administration_contract"].data.get("statut_salarie")),
        "poste": bool(sections["administration_contract"].data.get("poste")),
        "cnaps": bool(sections["affiliations"].data.get("numero_cnaps")),
        "visite_medicale": bool(sections["health"].data.get("date_visite")),
        "contrat_document": any(doc.document_type in {"contract", "avenant"} for doc in documents),
        "piece_identite": any(doc.document_type in {"cin_passport", "identity_document"} for doc in documents),
    }
    missing_items = [item for item, ok in checks.items() if not ok]
    completed_items = sum(1 for ok in checks.values() if ok)
    total_items = len(checks)
    score = round((completed_items / total_items) * 100) if total_items else 0

    if "contrat_document" in missing_items:
        alerts.append(
            schemas.HrDossierAlertOut(
                code="missing_contract_document",
                severity="high",
                message="Aucun contrat ou avenant rattache au dossier permanent.",
                details={},
            )
        )
    if "visite_medicale" in missing_items:
        alerts.append(
            schemas.HrDossierAlertOut(
                code="missing_medical_visit",
                severity="medium",
                message="La visite medicale d'embauche n'est pas renseignee.",
                details={},
            )
        )
    if "cnaps" in missing_items:
        alerts.append(
            schemas.HrDossierAlertOut(
                code="missing_cnaps",
                severity="medium",
                message="Le numero CNaPS est absent du dossier.",
                details={},
            )
        )

    expired_documents = [doc for doc in documents if doc.is_expired]
    if expired_documents:
        alerts.append(
            schemas.HrDossierAlertOut(
                code="expired_documents",
                severity="medium",
                message=f"{len(expired_documents)} document(s) expire(s) dans le dossier.",
                details={"document_ids": [doc.id for doc in expired_documents]},
            )
        )

    return (
        schemas.HrDossierCompletenessOut(
            score=score,
            completed_items=completed_items,
            total_items=total_items,
            missing_items=missing_items,
        ),
        alerts,
    )


def build_hr_dossier_view(db: Session, *, worker: models.Worker, user: models.AppUser) -> schemas.HrDossierViewOut:
    sync_worker_master_data(db, worker)
    master_view = build_worker_master_view(db, worker)
    hr_file = ensure_hr_employee_file(db, worker, user)
    access_scope = get_hr_dossier_access_scope(db, user, worker)
    if access_scope == "none":
        raise PermissionError("Forbidden")

    manual_sections = _load_json(hr_file.manual_sections_json, {})
    sections = _build_sections(db, worker=worker, master_view=master_view, manual_sections=manual_sections)
    uploaded_documents = _build_uploaded_documents(db, worker=worker)
    linked_documents = _build_source_documents(db, worker, master_view)
    all_documents = uploaded_documents + linked_documents
    completeness, alerts = _build_completeness(sections=sections, documents=all_documents)
    sections["documents"] = _section_out(
        "documents",
        "linked+uploaded",
        {
            "count": len(all_documents),
            "uploaded_count": len(uploaded_documents),
            "linked_count": len(linked_documents),
            "expired_count": sum(1 for item in all_documents if item.is_expired),
        },
    )
    timeline = _build_timeline(db, worker=worker, hr_file=hr_file)

    if access_scope == "manager":
        allowed_sections = {"identity", "administration_contract", "time_absence", "career", "documents"}
        sections = {key: value for key, value in sections.items() if key in allowed_sections}
    elif access_scope == "payroll":
        allowed_sections = {"identity", "administration_contract", "affiliations", "payroll", "documents"}
        sections = {key: value for key, value in sections.items() if key in allowed_sections}
    elif access_scope == "self":
        allowed_sections = {"identity", "administration_contract", "time_absence", "documents"}
        sections = {key: value for key, value in sections.items() if key in allowed_sections}

    visible_documents = [item for item in all_documents if _document_can_be_seen(item, access_scope)]
    if access_scope in {"manager", "payroll", "self"}:
        timeline = [item for item in timeline if item.section_code in sections]

    return schemas.HrDossierViewOut(
        worker=master_view.worker,
        access_scope=access_scope,
        summary={
            "worker_id": worker.id,
            "employer_id": worker.employer_id,
            "revision_number": hr_file.revision_number,
            "updated_at": _iso_date(hr_file.updated_at),
            "alerts_count": len(alerts),
            "documents_count": len(visible_documents),
        },
        completeness=completeness,
        alerts=alerts,
        sections=sections,
        documents=visible_documents,
        timeline=timeline,
    )


def upload_hr_document(
    db: Session,
    *,
    worker: models.Worker,
    actor: models.AppUser,
    files: list[tuple[Any, bytes]],
    meta: schemas.HrDossierDocumentUploadMetaIn,
) -> list[models.HrEmployeeDocument]:
    hr_file = ensure_hr_employee_file(db, worker, actor)
    created_items: list[models.HrEmployeeDocument] = []
    for upload_file, content in files:
        safe_worker = sanitize_filename_part(f"{worker.matricule or worker.id}_{worker.nom}_{worker.prenom}")
        safe_name = sanitize_filename_part(Path(upload_file.filename or "document").name)
        relative_path = f"hr_dossiers/{worker.employer_id}/{worker.id}/{safe_worker}/{_now_naive().strftime('%Y%m%d%H%M%S')}_{safe_name}"
        save_upload_file(BytesIO(content), filename=relative_path)
        document = models.HrEmployeeDocument(
            employer_id=worker.employer_id,
            worker_id=worker.id,
            hr_file_id=hr_file.id,
            section_code=meta.section_code,
            document_type=meta.document_type,
            title=meta.title or Path(upload_file.filename or safe_name).stem,
            status="active",
            source_module="hr_dossier",
            document_date=meta.document_date,
            expiration_date=meta.expiration_date,
            comment=meta.comment,
            visibility_scope=meta.visibility_scope,
            visible_to_employee=meta.visible_to_employee,
            visible_to_manager=meta.visible_to_manager,
            visible_to_payroll=meta.visible_to_payroll,
            metadata_json=_dump_json({}),
            current_version_number=1,
            created_by_user_id=actor.id,
            updated_by_user_id=actor.id,
        )
        db.add(document)
        db.flush()
        version = models.HrEmployeeDocumentVersion(
            employer_id=worker.employer_id,
            worker_id=worker.id,
            document_id=document.id,
            version_number=1,
            storage_path=relative_path,
            original_name=upload_file.filename or safe_name,
            mime_type=getattr(upload_file, "content_type", None),
            file_size=len(content),
            checksum=_file_checksum(content),
            metadata_json=_dump_json({}),
            created_by_user_id=actor.id,
        )
        db.add(version)
        db.flush()
        _append_event(
            db,
            worker=worker,
            hr_file=hr_file,
            actor=actor,
            section_code=meta.section_code,
            event_type="document_uploaded",
            title=f"Document ajoute: {document.title}",
            source_module="hr_dossier",
            source_record_type="document",
            source_record_id=document.id,
            payload={"document_type": meta.document_type, "filename": upload_file.filename},
        )
        created_items.append(document)
    hr_file.revision_number = (hr_file.revision_number or 0) + 1
    hr_file.updated_by_user_id = actor.id
    db.flush()
    return created_items


def add_hr_document_version(
    db: Session,
    *,
    worker: models.Worker,
    actor: models.AppUser,
    document: models.HrEmployeeDocument,
    upload_file: Any,
    content: bytes,
) -> models.HrEmployeeDocumentVersion:
    hr_file = ensure_hr_employee_file(db, worker, actor)
    next_version_number = (document.current_version_number or 0) + 1
    safe_worker = sanitize_filename_part(f"{worker.matricule or worker.id}_{worker.nom}_{worker.prenom}")
    safe_name = sanitize_filename_part(Path(upload_file.filename or "document").name)
    relative_path = f"hr_dossiers/{worker.employer_id}/{worker.id}/{safe_worker}/{_now_naive().strftime('%Y%m%d%H%M%S')}_v{next_version_number}_{safe_name}"
    save_upload_file(BytesIO(content), filename=relative_path)
    version = models.HrEmployeeDocumentVersion(
        employer_id=worker.employer_id,
        worker_id=worker.id,
        document_id=document.id,
        version_number=next_version_number,
        storage_path=relative_path,
        original_name=upload_file.filename or safe_name,
        mime_type=getattr(upload_file, "content_type", None),
        file_size=len(content),
        checksum=_file_checksum(content),
        metadata_json=_dump_json({}),
        created_by_user_id=actor.id,
    )
    db.add(version)
    document.current_version_number = next_version_number
    document.updated_by_user_id = actor.id
    document.updated_at = _now_naive()
    hr_file.revision_number = (hr_file.revision_number or 0) + 1
    hr_file.updated_by_user_id = actor.id
    db.flush()
    _append_event(
        db,
        worker=worker,
        hr_file=hr_file,
        actor=actor,
        section_code=document.section_code,
        event_type="document_version_uploaded",
        title=f"Nouvelle version: {document.title}",
        source_module="hr_dossier",
        source_record_type="document",
        source_record_id=document.id,
        payload={"version_number": next_version_number, "filename": upload_file.filename},
    )
    return version


def build_hr_dossier_report(db: Session, *, employer_id: int, user: models.AppUser) -> schemas.HrDossierReportOut:
    workers = (
        db.query(models.Worker)
        .filter(models.Worker.employer_id == employer_id, models.Worker.is_active.is_(True))
        .order_by(models.Worker.nom.asc(), models.Worker.prenom.asc())
        .all()
    )
    rows: list[schemas.HrDossierReportRowOut] = []
    for worker in workers:
        try:
            dossier = build_hr_dossier_view(db, worker=worker, user=user)
        except PermissionError:
            continue
        missing_items = dossier.completeness.missing_items
        row = schemas.HrDossierReportRowOut(
            worker_id=worker.id,
            employer_id=worker.employer_id,
            matricule=worker.matricule,
            full_name=f"{worker.nom or ''} {worker.prenom or ''}".strip(),
            completeness_score=dossier.completeness.score,
            missing_contract_document="contrat_document" in missing_items,
            missing_medical_visit="visite_medicale" in missing_items,
            missing_cnaps_number="cnaps" in missing_items,
            expired_document_count=sum(1 for item in dossier.documents if item.is_expired),
            missing_items=missing_items,
        )
        rows.append(row)
    return schemas.HrDossierReportOut(
        employer_id=employer_id,
        total_workers=len(rows),
        incomplete_workers=sum(1 for item in rows if item.completeness_score < 100),
        missing_contract_document_workers=sum(1 for item in rows if item.missing_contract_document),
        missing_medical_visit_workers=sum(1 for item in rows if item.missing_medical_visit),
        missing_cnaps_number_workers=sum(1 for item in rows if item.missing_cnaps_number),
        workers_with_expired_documents=sum(1 for item in rows if item.expired_document_count > 0),
        rows=rows,
    )
