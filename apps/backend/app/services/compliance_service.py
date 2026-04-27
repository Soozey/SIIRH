import json
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def json_load(value: Any, default: Any):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _normalized_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _has_contract_text(content: Optional[str], fragment: Optional[str]) -> bool:
    if not content or not fragment:
        return False
    return _normalized_text(fragment) in _normalized_text(content)


def _effective_date(worker: models.Worker) -> Optional[date]:
    return worker.date_embauche or None


def _job_profile_for_posting(job_posting: Optional[models.RecruitmentJobPosting]):
    if not job_posting:
        return None
    profile = getattr(job_posting, "job_profile", None)
    if isinstance(profile, list):
        return profile[0] if profile else None
    return profile


def _identity_gaps(worker: models.Worker) -> list[str]:
    gaps: list[str] = []
    if not worker.nom or not worker.prenom:
        gaps.append("identite")
    if not worker.cin:
        gaps.append("cin")
    if not worker.date_naissance:
        gaps.append("date_naissance")
    if not worker.adresse:
        gaps.append("adresse")
    if not worker.poste:
        gaps.append("fonction")
    if not worker.categorie_prof:
        gaps.append("categorie_professionnelle")
    if not worker.indice:
        gaps.append("indice_classification")
    if not worker.salaire_base or worker.salaire_base <= 0:
        gaps.append("salaire")
    if not worker.date_embauche:
        gaps.append("date_effet")
    return gaps


def build_contract_snapshot(
    contract: models.CustomContract,
    worker: models.Worker,
    *,
    salary_amount: Optional[float] = None,
    effective_date: Optional[date] = None,
    classification_index: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "contract_id": contract.id,
        "contract_title": contract.title,
        "template_type": contract.template_type,
        "worker": {
            "id": worker.id,
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenom": worker.prenom,
            "poste": worker.poste,
            "categorie_prof": worker.categorie_prof,
            "indice": classification_index or worker.indice,
            "salaire_base": salary_amount if salary_amount is not None else worker.salaire_base,
            "date_effet": (effective_date or _effective_date(worker)).isoformat() if (effective_date or _effective_date(worker)) else None,
            "nature_contrat": worker.nature_contrat,
            "etablissement": worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement,
            "departement": worker.effective_departement if hasattr(worker, "effective_departement") else worker.departement,
        },
        "content": contract.content,
    }


def build_contract_checklist(
    contract: models.CustomContract,
    worker: models.Worker,
    *,
    salary_amount: Optional[float] = None,
    effective_date: Optional[date] = None,
    classification_index: Optional[str] = None,
) -> list[dict[str, Any]]:
    effective = effective_date or _effective_date(worker)
    salary = salary_amount if salary_amount is not None else worker.salaire_base
    index_value = classification_index or worker.indice
    content = contract.content or ""
    checks = [
        {
            "code": "function",
            "label": "Fonction / poste",
            "status": "ok" if worker.poste else "missing",
            "value": worker.poste,
            "source": "worker.poste",
            "present_in_document": _has_contract_text(content, worker.poste),
        },
        {
            "code": "professional_category",
            "label": "Categorie professionnelle",
            "status": "ok" if worker.categorie_prof else "missing",
            "value": worker.categorie_prof,
            "source": "worker.categorie_prof",
            "present_in_document": _has_contract_text(content, worker.categorie_prof),
        },
        {
            "code": "classification_index",
            "label": "Indice minimum de classification",
            "status": "ok" if index_value else "missing",
            "value": index_value,
            "source": "worker.indice",
            "present_in_document": _has_contract_text(content, index_value),
        },
        {
            "code": "salary",
            "label": "Salaire convenu",
            "status": "ok" if salary and salary > 0 else "missing",
            "value": salary,
            "source": "worker.salaire_base",
            "present_in_document": _has_contract_text(content, str(int(salary))) if salary else False,
        },
        {
            "code": "effective_date",
            "label": "Date d'effet",
            "status": "ok" if effective else "missing",
            "value": effective.isoformat() if effective else None,
            "source": "worker.date_embauche",
            "present_in_document": _has_contract_text(content, effective.isoformat()) if effective else False,
        },
        {
            "code": "contract_type",
            "label": "Nature du contrat",
            "status": "ok" if worker.nature_contrat else "missing",
            "value": worker.nature_contrat,
            "source": "worker.nature_contrat",
            "present_in_document": _has_contract_text(content, worker.nature_contrat),
        },
    ]
    return checks


def create_contract_version(
    db: Session,
    *,
    contract: models.CustomContract,
    worker: models.Worker,
    actor: Optional[models.AppUser],
    source_module: str,
    status: str,
    effective_date: Optional[date] = None,
    salary_amount: Optional[float] = None,
    classification_index: Optional[str] = None,
) -> models.ContractVersion:
    last_version = (
        db.query(models.ContractVersion)
        .filter(models.ContractVersion.contract_id == contract.id)
        .order_by(models.ContractVersion.version_number.desc())
        .first()
    )
    version_number = (last_version.version_number if last_version else 0) + 1
    snapshot = build_contract_snapshot(
        contract,
        worker,
        salary_amount=salary_amount,
        effective_date=effective_date,
        classification_index=classification_index,
    )
    version = models.ContractVersion(
        contract_id=contract.id,
        worker_id=worker.id,
        employer_id=contract.employer_id,
        version_number=version_number,
        source_module=source_module,
        status=status,
        effective_date=effective_date or worker.date_embauche,
        salary_amount=salary_amount if salary_amount is not None else worker.salaire_base,
        classification_index=classification_index or worker.indice,
        snapshot_json=json_dump(snapshot),
        created_by_user_id=actor.id if actor else None,
    )
    db.add(version)
    db.flush()
    return version


def build_employee_flow(db: Session, worker: models.Worker) -> dict[str, Any]:
    decision = (
        db.query(models.RecruitmentDecision)
        .filter(models.RecruitmentDecision.converted_worker_id == worker.id)
        .first()
    )
    contract = (
        db.query(models.CustomContract)
        .filter(models.CustomContract.worker_id == worker.id)
        .order_by(models.CustomContract.updated_at.desc())
        .first()
    )
    contract_versions = (
        db.query(models.ContractVersion)
        .filter(models.ContractVersion.worker_id == worker.id)
        .order_by(models.ContractVersion.version_number.desc())
        .all()
    )
    declarations = (
        db.query(models.StatutoryDeclaration)
        .filter(models.StatutoryDeclaration.employer_id == worker.employer_id)
        .order_by(models.StatutoryDeclaration.updated_at.desc())
        .limit(10)
        .all()
    )

    application = decision.application if decision else None
    candidate = application.candidate if application else None
    job_posting = application.job_posting if application else None
    profile = _job_profile_for_posting(job_posting)
    workforce_job_profile = None
    if profile and profile.workforce_job_profile_id:
        workforce_job_profile = (
            db.query(models.WorkforceJobProfile)
            .filter(models.WorkforceJobProfile.id == profile.workforce_job_profile_id)
            .first()
        )

    issues: list[dict[str, Any]] = []
    identity_gaps = _identity_gaps(worker)
    if identity_gaps:
        issues.append(
            {
                "severity": "high",
                "issue_type": "worker_identity_incomplete",
                "entity_type": "worker",
                "entity_id": str(worker.id),
                "message": "L'identite du salarie est incomplete pour un flux contractuel conforme.",
                "details": {"missing_fields": identity_gaps},
            }
        )
    if candidate and worker.email and candidate.email and worker.email != candidate.email:
        issues.append(
            {
                "severity": "medium",
                "issue_type": "candidate_worker_email_mismatch",
                "entity_type": "worker",
                "entity_id": str(worker.id),
                "message": "L'email du candidat retenu differe de celui du dossier salarie.",
                "details": {"candidate_email": candidate.email, "worker_email": worker.email},
            }
        )
    if profile and profile.salary_min and worker.salaire_base and abs(profile.salary_min - worker.salaire_base) > 1:
        issues.append(
            {
                "severity": "medium",
                "issue_type": "salary_source_mismatch",
                "entity_type": "worker",
                "entity_id": str(worker.id),
                "message": "Le salaire repris dans le dossier salarie differe de la valeur validee en recrutement.",
                "details": {"recruitment_salary_min": profile.salary_min, "worker_salary_base": worker.salaire_base},
            }
        )

    return {
        "worker": {
            "id": worker.id,
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenom": worker.prenom,
            "poste": worker.poste,
            "categorie_prof": worker.categorie_prof,
            "indice": worker.indice,
            "salaire_base": worker.salaire_base,
            "date_embauche": worker.date_embauche.isoformat() if worker.date_embauche else None,
            "etablissement": worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement,
            "departement": worker.effective_departement if hasattr(worker, "effective_departement") else worker.departement,
            "email": worker.email,
            "telephone": worker.telephone,
        },
        "candidate": {
            "id": candidate.id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "status": candidate.status,
            "source": candidate.source,
        } if candidate else {},
        "job_posting": {
            "id": job_posting.id,
            "title": job_posting.title,
            "department": job_posting.department,
            "location": job_posting.location,
            "contract_type": job_posting.contract_type,
            "status": job_posting.status,
            "salary_range": job_posting.salary_range,
            "desired_start_date": profile.desired_start_date.isoformat() if profile and profile.desired_start_date else None,
            "salary_min": profile.salary_min if profile else None,
            "salary_max": profile.salary_max if profile else None,
        } if job_posting else {},
        "job_profile": {
            "id": profile.id,
            "classification": profile.classification,
            "mission_summary": profile.mission_summary,
            "main_activities": json_load(profile.main_activities_json, []),
            "technical_skills": json_load(profile.technical_skills_json, []),
            "behavioral_skills": json_load(profile.behavioral_skills_json, []),
            "languages": json_load(profile.languages_json, []),
        } if profile else {},
        "workforce_job_profile": {
            "id": workforce_job_profile.id,
            "title": workforce_job_profile.title,
            "department": workforce_job_profile.department,
            "classification_index": workforce_job_profile.classification_index,
            "category_prof": workforce_job_profile.category_prof,
        } if workforce_job_profile else {},
        "decision": {
            "id": decision.id,
            "status": decision.decision_status,
            "comment": decision.decision_comment,
            "shortlist_rank": decision.shortlist_rank,
            "contract_draft_id": decision.contract_draft_id,
            "decided_at": decision.decided_at.isoformat() if decision and decision.decided_at else None,
        } if decision else {},
        "contract": {
            "id": contract.id,
            "title": contract.title,
            "template_type": contract.template_type,
            "is_default": contract.is_default,
            "updated_at": contract.updated_at.isoformat() if contract else None,
        } if contract else {},
        "contract_versions": [
            {
                "id": item.id,
                "version_number": item.version_number,
                "status": item.status,
                "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                "salary_amount": item.salary_amount,
                "classification_index": item.classification_index,
                "created_at": item.created_at.isoformat(),
            }
            for item in contract_versions
        ],
        "declarations": [
            {
                "id": item.id,
                "channel": item.channel,
                "period_label": item.period_label,
                "status": item.status,
                "reference_number": item.reference_number,
                "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
            }
            for item in declarations
        ],
        "integrity_issues": issues,
    }


def collect_integrity_issues(db: Session, employer_id: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    workers = db.query(models.Worker).filter(models.Worker.employer_id == employer_id).all()

    seen_matricules: dict[str, int] = {}
    for worker in workers:
        if worker.matricule:
            if worker.matricule in seen_matricules:
                issues.append(
                    {
                        "severity": "critical",
                        "issue_type": "duplicate_matricule",
                        "entity_type": "worker",
                        "entity_id": str(worker.id),
                        "message": "Conflit de matricule detecte.",
                        "details": {"matricule": worker.matricule, "other_worker_id": seen_matricules[worker.matricule]},
                    }
                )
            else:
                seen_matricules[worker.matricule] = worker.id

        missing_fields = _identity_gaps(worker)
        if missing_fields:
            issues.append(
                {
                    "severity": "high",
                    "issue_type": "incomplete_worker_identity",
                    "entity_type": "worker",
                    "entity_id": str(worker.id),
                    "message": "Le dossier salarie ne contient pas toutes les donnees minimales pour contrat et controle.",
                    "details": {"missing_fields": missing_fields},
                }
            )

    decisions = (
        db.query(models.RecruitmentDecision)
        .join(models.RecruitmentApplication, models.RecruitmentDecision.application_id == models.RecruitmentApplication.id)
        .join(models.RecruitmentJobPosting, models.RecruitmentApplication.job_posting_id == models.RecruitmentJobPosting.id)
        .filter(models.RecruitmentJobPosting.employer_id == employer_id)
        .all()
    )
    for decision in decisions:
        if not decision.converted_worker_id:
            continue
        worker = db.query(models.Worker).filter(models.Worker.id == decision.converted_worker_id).first()
        application = decision.application
        candidate = application.candidate if application else None
        job_posting = application.job_posting if application else None
        profile = _job_profile_for_posting(job_posting)
        if worker and candidate and worker.email and candidate.email and worker.email != candidate.email:
            issues.append(
                {
                    "severity": "medium",
                    "issue_type": "candidate_worker_email_mismatch",
                    "entity_type": "recruitment_decision",
                    "entity_id": str(decision.id),
                    "message": "Le candidat retenu et le dossier salarie ne partagent pas le meme email.",
                    "details": {"candidate_email": candidate.email, "worker_email": worker.email, "worker_id": worker.id},
                }
            )
        if worker and profile and profile.salary_min and worker.salaire_base and abs(profile.salary_min - worker.salaire_base) > 1:
            issues.append(
                {
                    "severity": "medium",
                    "issue_type": "salary_alignment_issue",
                    "entity_type": "recruitment_decision",
                    "entity_id": str(decision.id),
                    "message": "Le salaire valide en recrutement n'est pas aligne avec le contrat/dossier salarie.",
                    "details": {"worker_id": worker.id, "recruitment_salary_min": profile.salary_min, "worker_salary_base": worker.salaire_base},
                }
            )
        if worker and job_posting and worker.nature_contrat and job_posting.contract_type and worker.nature_contrat != job_posting.contract_type:
            issues.append(
                {
                    "severity": "medium",
                    "issue_type": "contract_type_mismatch",
                    "entity_type": "worker",
                    "entity_id": str(worker.id),
                    "message": "La nature de contrat du salarie differe de celle de la fiche de poste retenue.",
                    "details": {"job_contract_type": job_posting.contract_type, "worker_contract_type": worker.nature_contrat},
                }
            )

    return issues


def build_contract_queue(db: Session, employer_id: int) -> list[dict[str, Any]]:
    contracts = (
        db.query(models.CustomContract, models.Worker)
        .join(models.Worker, models.CustomContract.worker_id == models.Worker.id)
        .filter(models.CustomContract.employer_id == employer_id)
        .order_by(models.CustomContract.updated_at.desc())
        .all()
    )
    queue: list[dict[str, Any]] = []
    for contract, worker in contracts:
        latest_review = (
            db.query(models.ComplianceReview)
            .filter(models.ComplianceReview.contract_id == contract.id)
            .order_by(models.ComplianceReview.updated_at.desc())
            .first()
        )
        queue.append(
            {
                "contract_id": contract.id,
                "contract_title": contract.title,
                "worker_id": worker.id,
                "worker_name": f"{worker.nom} {worker.prenom}".strip(),
                "matricule": worker.matricule,
                "status": latest_review.status if latest_review else "not_reviewed",
                "review_stage": latest_review.review_stage if latest_review else None,
                "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
                "missing_fields": _identity_gaps(worker),
            }
        )
    return queue


def sync_employer_register(db: Session, employer_id: int) -> list[models.EmployerRegisterEntry]:
    workers = db.query(models.Worker).filter(models.Worker.employer_id == employer_id).all()
    synced: list[models.EmployerRegisterEntry] = []
    for worker in workers:
        contract = (
            db.query(models.CustomContract)
            .filter(models.CustomContract.worker_id == worker.id)
            .order_by(models.CustomContract.updated_at.desc())
            .first()
        )
        latest_version = (
            db.query(models.ContractVersion)
            .filter(models.ContractVersion.worker_id == worker.id)
            .order_by(models.ContractVersion.version_number.desc())
            .first()
        )
        payload = {
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenom": worker.prenom,
            "poste": worker.poste,
            "categorie_prof": worker.categorie_prof,
            "indice": worker.indice,
            "nature_contrat": worker.nature_contrat,
            "date_embauche": worker.date_embauche.isoformat() if worker.date_embauche else None,
            "date_debauche": worker.date_debauche.isoformat() if worker.date_debauche else None,
            "etablissement": worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement,
        }
        entry = (
            db.query(models.EmployerRegisterEntry)
            .filter(
                models.EmployerRegisterEntry.employer_id == employer_id,
                models.EmployerRegisterEntry.worker_id == worker.id,
                models.EmployerRegisterEntry.entry_type == "employer_register",
            )
            .first()
        )
        if not entry:
            entry = models.EmployerRegisterEntry(
                employer_id=employer_id,
                worker_id=worker.id,
                contract_id=contract.id if contract else None,
                contract_version_id=latest_version.id if latest_version else None,
                entry_type="employer_register",
                registry_label="Registre employeur",
                status="inactive" if worker.date_debauche else "active",
                effective_date=worker.date_embauche,
                details_json=json_dump(payload),
            )
            db.add(entry)
        else:
            entry.contract_id = contract.id if contract else None
            entry.contract_version_id = latest_version.id if latest_version else None
            entry.status = "inactive" if worker.date_debauche else "active"
            entry.effective_date = worker.date_embauche
            entry.details_json = json_dump(payload)
        synced.append(entry)
    db.flush()
    return synced
