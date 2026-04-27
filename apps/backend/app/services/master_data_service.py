import hashlib
import json
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models, schemas


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dump(payload).encode("utf-8")).hexdigest()


def _job_profile_for_posting(job_posting: Optional[models.RecruitmentJobPosting]) -> Optional[models.RecruitmentJobProfile]:
    if not job_posting:
        return None
    profile = getattr(job_posting, "job_profile", None)
    if isinstance(profile, list):
        return profile[0] if profile else None
    return profile


def _resolve_workforce_job_profile(
    db: Session,
    worker: models.Worker,
    job_posting: Optional[models.RecruitmentJobPosting],
    job_profile: Optional[models.RecruitmentJobProfile],
) -> Optional[models.WorkforceJobProfile]:
    if job_profile and job_profile.workforce_job_profile_id:
        linked = (
            db.query(models.WorkforceJobProfile)
            .filter(models.WorkforceJobProfile.id == job_profile.workforce_job_profile_id)
            .first()
        )
        if linked:
            return linked

    title = (worker.poste or (job_posting.title if job_posting else None) or "").strip()
    department = (
        (worker.effective_departement if hasattr(worker, "effective_departement") else worker.departement)
        or (job_posting.department if job_posting else None)
        or ""
    ).strip()
    if not title:
        return None
    query = (
        db.query(models.WorkforceJobProfile)
        .filter(models.WorkforceJobProfile.employer_id == worker.employer_id)
        .filter(models.WorkforceJobProfile.title == title)
    )
    if department:
        query = query.filter(models.WorkforceJobProfile.department == department)
    return query.first()


def _latest_contract(db: Session, worker_id: int) -> Optional[models.CustomContract]:
    return (
        db.query(models.CustomContract)
        .filter(models.CustomContract.worker_id == worker_id)
        .order_by(models.CustomContract.is_default.desc(), models.CustomContract.updated_at.desc())
        .first()
    )


def _latest_contract_version(db: Session, worker_id: int) -> Optional[models.ContractVersion]:
    return (
        db.query(models.ContractVersion)
        .filter(models.ContractVersion.worker_id == worker_id)
        .order_by(models.ContractVersion.version_number.desc(), models.ContractVersion.created_at.desc())
        .first()
    )


def _latest_recruitment_decision(db: Session, worker_id: int) -> Optional[models.RecruitmentDecision]:
    return (
        db.query(models.RecruitmentDecision)
        .filter(models.RecruitmentDecision.converted_worker_id == worker_id)
        .order_by(models.RecruitmentDecision.decided_at.desc(), models.RecruitmentDecision.updated_at.desc())
        .first()
    )


def _organization_values(worker: models.Worker) -> dict[str, Any]:
    return {
        "organizational_unit_id": worker.organizational_unit_id,
        "establishment": worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement,
        "department": worker.effective_departement if hasattr(worker, "effective_departement") else worker.departement,
        "service": worker.effective_service if hasattr(worker, "effective_service") else worker.service,
        "unit": worker.effective_unite if hasattr(worker, "effective_unite") else worker.unite,
        "position_title": worker.poste,
        "effective_from": worker.date_embauche,
    }


def _identity_issues(identity: dict[str, Any], employment: dict[str, Any], compensation: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    missing = []
    if not identity.get("first_name") or not identity.get("last_name"):
        missing.append("nom_prenom")
    if not identity.get("birth_date"):
        missing.append("date_naissance")
    if not identity.get("address"):
        missing.append("adresse")
    if not identity.get("cin_number"):
        missing.append("cin")
    if not employment.get("job_title"):
        missing.append("poste")
    if not employment.get("classification_index"):
        missing.append("indice")
    if not compensation.get("validated_salary_amount"):
        missing.append("salaire_valide")
    if not employment.get("hire_date"):
        missing.append("date_embauche")
    if missing:
        issues.append(
            {
                "severity": "high",
                "issue_type": "master_data_incomplete",
                "entity_type": "master_data",
                "entity_id": str(identity.get("worker_id") or ""),
                "message": "Le dossier maitre salarie reste incomplet pour certains usages RH et conformite.",
                "details": {"missing_fields": missing},
            }
        )
    return issues


def sync_worker_master_data(
    db: Session,
    worker: models.Worker,
    *,
    candidate: Optional[models.RecruitmentCandidate] = None,
    application: Optional[models.RecruitmentApplication] = None,
    decision: Optional[models.RecruitmentDecision] = None,
    job_posting: Optional[models.RecruitmentJobPosting] = None,
    job_profile: Optional[models.RecruitmentJobProfile] = None,
    contract: Optional[models.CustomContract] = None,
    contract_version: Optional[models.ContractVersion] = None,
) -> None:
    decision = decision or _latest_recruitment_decision(db, worker.id)
    application = application or (decision.application if decision else None)
    candidate = candidate or (application.candidate if application else None)
    job_posting = job_posting or (application.job_posting if application else None)
    job_profile = job_profile or _job_profile_for_posting(job_posting)
    workforce_job_profile = _resolve_workforce_job_profile(db, worker, job_posting, job_profile)
    contract = contract or _latest_contract(db, worker.id)
    contract_version = contract_version or _latest_contract_version(db, worker.id)

    identity_payload = {
        "worker_id": worker.id,
        "employer_id": worker.employer_id,
        "recruitment_candidate_id": candidate.id if candidate else None,
        "recruitment_application_id": application.id if application else None,
        "recruitment_decision_id": decision.id if decision else None,
        "first_name": worker.prenom or (candidate.first_name if candidate else None),
        "last_name": worker.nom or (candidate.last_name if candidate else None),
        "full_name": f"{worker.prenom or ''} {worker.nom or ''}".strip() or None,
        "sex": worker.sexe,
        "marital_status": worker.situation_familiale,
        "birth_date": worker.date_naissance,
        "birth_place": worker.lieu_naissance,
        "address": worker.adresse,
        "phone": worker.telephone or (candidate.phone if candidate else None),
        "email": worker.email or (candidate.email if candidate else None),
        "cin_number": worker.cin,
        "cin_issued_at": worker.cin_delivre_le,
        "cin_issued_place": worker.cin_lieu,
        "cnaps_number": worker.cnaps_num,
        "employee_number": worker.matricule,
    }
    identity = db.query(models.EmployeeMasterRecord).filter(models.EmployeeMasterRecord.worker_id == worker.id).first()
    if not identity:
        identity = models.EmployeeMasterRecord(worker_id=worker.id, employer_id=worker.employer_id)
        db.add(identity)
    identity.employer_id = worker.employer_id
    identity.recruitment_candidate_id = identity_payload["recruitment_candidate_id"]
    identity.recruitment_application_id = identity_payload["recruitment_application_id"]
    identity.recruitment_decision_id = identity_payload["recruitment_decision_id"]
    identity.first_name = identity_payload["first_name"]
    identity.last_name = identity_payload["last_name"]
    identity.full_name = identity_payload["full_name"]
    identity.sex = identity_payload["sex"]
    identity.marital_status = identity_payload["marital_status"]
    identity.birth_date = identity_payload["birth_date"]
    identity.birth_place = identity_payload["birth_place"]
    identity.address = identity_payload["address"]
    identity.phone = identity_payload["phone"]
    identity.email = identity_payload["email"]
    identity.cin_number = identity_payload["cin_number"]
    identity.cin_issued_at = identity_payload["cin_issued_at"]
    identity.cin_issued_place = identity_payload["cin_issued_place"]
    identity.cnaps_number = identity_payload["cnaps_number"]
    identity.employee_number = identity_payload["employee_number"]
    identity.source_status = "synced"
    identity.canonical_hash = _hash_payload(identity_payload)

    employment_status = "inactive" if worker.date_debauche else "active"
    employment_payload = {
        "worker_id": worker.id,
        "employer_id": worker.employer_id,
        "recruitment_job_posting_id": job_posting.id if job_posting else None,
        "recruitment_job_profile_id": job_profile.id if job_profile else None,
        "workforce_job_profile_id": workforce_job_profile.id if workforce_job_profile else None,
        "contract_id": contract.id if contract else None,
        "contract_version_id": contract_version.id if contract_version else None,
        "contract_type": worker.nature_contrat or (job_posting.contract_type if job_posting else None),
        "employment_status": employment_status,
        "hire_date": worker.date_embauche,
        "exit_date": worker.date_debauche,
        "trial_period_days": worker.duree_essai_jours,
        "trial_end_date": worker.date_fin_essai,
        "job_title": worker.poste or (job_posting.title if job_posting else None),
        "professional_category": worker.categorie_prof,
        "classification_index": contract_version.classification_index if contract_version and contract_version.classification_index else worker.indice,
        "work_location": worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement,
    }
    employment = db.query(models.EmploymentMasterRecord).filter(models.EmploymentMasterRecord.worker_id == worker.id).first()
    if not employment:
        employment = models.EmploymentMasterRecord(worker_id=worker.id, employer_id=worker.employer_id)
        db.add(employment)
    employment.employer_id = worker.employer_id
    employment.recruitment_job_posting_id = employment_payload["recruitment_job_posting_id"]
    employment.recruitment_job_profile_id = employment_payload["recruitment_job_profile_id"]
    employment.workforce_job_profile_id = employment_payload["workforce_job_profile_id"]
    employment.contract_id = employment_payload["contract_id"]
    employment.contract_version_id = employment_payload["contract_version_id"]
    employment.contract_type = employment_payload["contract_type"]
    employment.employment_status = employment_payload["employment_status"]
    employment.hire_date = employment_payload["hire_date"]
    employment.exit_date = employment_payload["exit_date"]
    employment.trial_period_days = employment_payload["trial_period_days"]
    employment.trial_end_date = employment_payload["trial_end_date"]
    employment.job_title = employment_payload["job_title"]
    employment.professional_category = employment_payload["professional_category"]
    employment.classification_index = employment_payload["classification_index"]
    employment.work_location = employment_payload["work_location"]
    employment.source_status = "synced"
    employment.canonical_hash = _hash_payload(employment_payload)

    validated_salary = (
        contract_version.salary_amount
        if contract_version and contract_version.salary_amount is not None
        else (job_profile.salary_min if job_profile and job_profile.salary_min is not None else worker.salaire_base)
    )
    compensation_payload = {
        "worker_id": worker.id,
        "employer_id": worker.employer_id,
        "contract_version_id": contract_version.id if contract_version else None,
        "validated_salary_amount": validated_salary,
        "salary_base": worker.salaire_base,
        "hourly_rate": worker.salaire_horaire,
        "vhm": worker.vhm,
        "weekly_hours": worker.horaire_hebdo,
        "payment_mode": worker.mode_paiement,
        "bank_name": worker.banque,
        "rib": worker.rib,
        "bic": worker.bic,
        "benefits_json": {
            "vehicule": worker.avantage_vehicule,
            "logement": worker.avantage_logement,
            "telephone": worker.avantage_telephone,
            "autres": worker.avantage_autres,
        },
    }
    compensation = db.query(models.CompensationMasterRecord).filter(models.CompensationMasterRecord.worker_id == worker.id).first()
    if not compensation:
        compensation = models.CompensationMasterRecord(worker_id=worker.id, employer_id=worker.employer_id)
        db.add(compensation)
    compensation.employer_id = worker.employer_id
    compensation.contract_version_id = compensation_payload["contract_version_id"]
    compensation.validated_salary_amount = compensation_payload["validated_salary_amount"]
    compensation.salary_base = compensation_payload["salary_base"]
    compensation.hourly_rate = compensation_payload["hourly_rate"]
    compensation.vhm = compensation_payload["vhm"]
    compensation.weekly_hours = compensation_payload["weekly_hours"]
    compensation.payment_mode = compensation_payload["payment_mode"]
    compensation.bank_name = compensation_payload["bank_name"]
    compensation.rib = compensation_payload["rib"]
    compensation.bic = compensation_payload["bic"]
    compensation.benefits_json = _json_dump(compensation_payload["benefits_json"])
    compensation.source_status = "synced"
    compensation.canonical_hash = _hash_payload(compensation_payload)

    organization_payload = {"worker_id": worker.id, "employer_id": worker.employer_id, **_organization_values(worker)}
    organization = (
        db.query(models.OrganizationAssignmentRecord)
        .filter(models.OrganizationAssignmentRecord.worker_id == worker.id)
        .first()
    )
    if not organization:
        organization = models.OrganizationAssignmentRecord(worker_id=worker.id, employer_id=worker.employer_id)
        db.add(organization)
    organization.employer_id = worker.employer_id
    organization.organizational_unit_id = organization_payload["organizational_unit_id"]
    organization.establishment = organization_payload["establishment"]
    organization.department = organization_payload["department"]
    organization.service = organization_payload["service"]
    organization.unit = organization_payload["unit"]
    organization.position_title = organization_payload["position_title"]
    organization.effective_from = organization_payload["effective_from"]
    organization.source_status = "synced"
    organization.canonical_hash = _hash_payload(organization_payload)

    db.flush()


def sync_employer_master_data(db: Session, employer_id: int) -> None:
    workers = db.query(models.Worker).filter(models.Worker.employer_id == employer_id).all()
    for worker in workers:
        sync_worker_master_data(db, worker)


def build_worker_master_view(db: Session, worker: models.Worker) -> schemas.MasterDataWorkerViewOut:
    sync_worker_master_data(db, worker)

    identity = db.query(models.EmployeeMasterRecord).filter(models.EmployeeMasterRecord.worker_id == worker.id).first()
    employment = db.query(models.EmploymentMasterRecord).filter(models.EmploymentMasterRecord.worker_id == worker.id).first()
    compensation = db.query(models.CompensationMasterRecord).filter(models.CompensationMasterRecord.worker_id == worker.id).first()
    organization = (
        db.query(models.OrganizationAssignmentRecord)
        .filter(models.OrganizationAssignmentRecord.worker_id == worker.id)
        .first()
    )
    decision = _latest_recruitment_decision(db, worker.id)
    application = decision.application if decision else None
    candidate = application.candidate if application else None
    job_posting = application.job_posting if application else None
    job_profile = _job_profile_for_posting(job_posting)
    workforce_job_profile = _resolve_workforce_job_profile(db, worker, job_posting, job_profile)
    contract = _latest_contract(db, worker.id)
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

    identity_data = {
        "worker_id": worker.id,
        "employee_number": identity.employee_number if identity else worker.matricule,
        "first_name": identity.first_name if identity else worker.prenom,
        "last_name": identity.last_name if identity else worker.nom,
        "full_name": identity.full_name if identity else f"{worker.prenom or ''} {worker.nom or ''}".strip(),
        "sex": identity.sex if identity else worker.sexe,
        "marital_status": identity.marital_status if identity else worker.situation_familiale,
        "birth_date": identity.birth_date.isoformat() if identity and identity.birth_date else None,
        "birth_place": identity.birth_place if identity else worker.lieu_naissance,
        "address": identity.address if identity else worker.adresse,
        "phone": identity.phone if identity else worker.telephone,
        "email": identity.email if identity else worker.email,
        "cin_number": identity.cin_number if identity else worker.cin,
        "cnaps_number": identity.cnaps_number if identity else worker.cnaps_num,
    }
    employment_data = {
        "worker_id": worker.id,
        "workforce_job_profile_id": employment.workforce_job_profile_id if employment else (workforce_job_profile.id if workforce_job_profile else None),
        "contract_type": employment.contract_type if employment else worker.nature_contrat,
        "employment_status": employment.employment_status if employment else ("inactive" if worker.date_debauche else "active"),
        "hire_date": employment.hire_date.isoformat() if employment and employment.hire_date else None,
        "exit_date": employment.exit_date.isoformat() if employment and employment.exit_date else None,
        "trial_period_days": employment.trial_period_days if employment else worker.duree_essai_jours,
        "trial_end_date": employment.trial_end_date.isoformat() if employment and employment.trial_end_date else None,
        "job_title": employment.job_title if employment else worker.poste,
        "professional_category": employment.professional_category if employment else worker.categorie_prof,
        "classification_index": employment.classification_index if employment else worker.indice,
        "work_location": employment.work_location if employment else (worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement),
        "contract_id": employment.contract_id if employment else (contract.id if contract else None),
        "contract_version_id": employment.contract_version_id if employment else (contract_versions[0].id if contract_versions else None),
    }
    compensation_data = {
        "worker_id": worker.id,
        "validated_salary_amount": compensation.validated_salary_amount if compensation else worker.salaire_base,
        "salary_base": compensation.salary_base if compensation else worker.salaire_base,
        "hourly_rate": compensation.hourly_rate if compensation else worker.salaire_horaire,
        "vhm": compensation.vhm if compensation else worker.vhm,
        "weekly_hours": compensation.weekly_hours if compensation else worker.horaire_hebdo,
        "payment_mode": compensation.payment_mode if compensation else worker.mode_paiement,
        "bank_name": compensation.bank_name if compensation else worker.banque,
        "rib": compensation.rib if compensation else worker.rib,
        "bic": compensation.bic if compensation else worker.bic,
        "benefits": json.loads(compensation.benefits_json) if compensation and compensation.benefits_json else {
            "vehicule": worker.avantage_vehicule,
            "logement": worker.avantage_logement,
            "telephone": worker.avantage_telephone,
            "autres": worker.avantage_autres,
        },
    }
    organization_data = {
        "worker_id": worker.id,
        "organizational_unit_id": organization.organizational_unit_id if organization else worker.organizational_unit_id,
        "establishment": organization.establishment if organization else (worker.effective_etablissement if hasattr(worker, "effective_etablissement") else worker.etablissement),
        "department": organization.department if organization else (worker.effective_departement if hasattr(worker, "effective_departement") else worker.departement),
        "service": organization.service if organization else (worker.effective_service if hasattr(worker, "effective_service") else worker.service),
        "unit": organization.unit if organization else (worker.effective_unite if hasattr(worker, "effective_unite") else worker.unite),
        "position_title": organization.position_title if organization else worker.poste,
        "effective_from": organization.effective_from.isoformat() if organization and organization.effective_from else None,
    }

    issues = _identity_issues(identity_data, employment_data, compensation_data)
    if candidate and identity_data.get("email") and candidate.email and identity_data["email"] != candidate.email:
        issues.append(
            {
                "severity": "medium",
                "issue_type": "candidate_worker_email_mismatch",
                "entity_type": "employee_master_record",
                "entity_id": str(worker.id),
                "message": "Le dossier maitre salarie ne reprend pas le meme email que le candidat recrute.",
                "details": {"candidate_email": candidate.email, "master_email": identity_data["email"]},
            }
        )
    if job_profile and compensation_data.get("validated_salary_amount") and job_profile.salary_min and abs(float(compensation_data["validated_salary_amount"]) - float(job_profile.salary_min)) > 1:
        issues.append(
            {
                "severity": "medium",
                "issue_type": "salary_alignment_issue",
                "entity_type": "compensation_master_record",
                "entity_id": str(worker.id),
                "message": "Le salaire maitre n'est pas aligne avec le salaire minimum valide en recrutement.",
                "details": {
                    "recruitment_salary_min": job_profile.salary_min,
                    "master_validated_salary_amount": compensation_data["validated_salary_amount"],
                },
            }
        )

    return schemas.MasterDataWorkerViewOut(
        worker={
            "id": worker.id,
            "employer_id": worker.employer_id,
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenom": worker.prenom,
            "date_embauche": worker.date_embauche.isoformat() if worker.date_embauche else None,
            "date_debauche": worker.date_debauche.isoformat() if worker.date_debauche else None,
        },
        identity=schemas.MasterDataSectionOut(
            data=identity_data,
            canonical_hash=identity.canonical_hash if identity else None,
            source_status=identity.source_status if identity else "derived",
            updated_at=identity.updated_at if identity else None,
        ),
        employment=schemas.MasterDataSectionOut(
            data=employment_data,
            canonical_hash=employment.canonical_hash if employment else None,
            source_status=employment.source_status if employment else "derived",
            updated_at=employment.updated_at if employment else None,
        ),
        compensation=schemas.MasterDataSectionOut(
            data=compensation_data,
            canonical_hash=compensation.canonical_hash if compensation else None,
            source_status=compensation.source_status if compensation else "derived",
            updated_at=compensation.updated_at if compensation else None,
        ),
        organization=schemas.MasterDataSectionOut(
            data=organization_data,
            canonical_hash=organization.canonical_hash if organization else None,
            source_status=organization.source_status if organization else "derived",
            updated_at=organization.updated_at if organization else None,
        ),
        recruitment={
            "candidate": {
                "id": candidate.id,
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "status": candidate.status,
            } if candidate else {},
            "job_posting": {
                "id": job_posting.id,
                "title": job_posting.title,
                "department": job_posting.department,
                "location": job_posting.location,
                "contract_type": job_posting.contract_type,
                "status": job_posting.status,
            } if job_posting else {},
            "job_profile": {
                "id": job_profile.id,
                "salary_min": job_profile.salary_min,
                "salary_max": job_profile.salary_max,
                "desired_start_date": job_profile.desired_start_date.isoformat() if job_profile and job_profile.desired_start_date else None,
                "classification": job_profile.classification,
            } if job_profile else {},
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
                "contract_draft_id": decision.contract_draft_id,
                "decided_at": decision.decided_at.isoformat() if decision and decision.decided_at else None,
            } if decision else {},
        },
        contract={
            "id": contract.id,
            "title": contract.title,
            "template_type": contract.template_type,
            "is_default": contract.is_default,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
        } if contract else {},
        contract_versions=[
            {
                "id": item.id,
                "version_number": item.version_number,
                "status": item.status,
                "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                "salary_amount": item.salary_amount,
                "classification_index": item.classification_index,
                "source_module": item.source_module,
                "created_at": item.created_at.isoformat(),
            }
            for item in contract_versions
        ],
        declarations=[
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
        integrity_issues=[schemas.IntegrityIssueOut(**issue) for issue in issues],
    )


def build_worker_document_payload(db: Session, worker: models.Worker) -> dict[str, Any]:
    master = build_worker_master_view(db, worker)
    identity = master.identity.data
    employment = master.employment.data
    compensation = master.compensation.data
    organization = master.organization.data
    salary_value = compensation.get("validated_salary_amount") or compensation.get("salary_base") or 0

    return {
        "matricule": identity.get("employee_number") or worker.matricule,
        "nom": identity.get("last_name") or worker.nom,
        "prenom": identity.get("first_name") or worker.prenom,
        "nom_complet": identity.get("full_name") or f"{worker.prenom or ''} {worker.nom or ''}".strip(),
        "sexe": "Masculin" if identity.get("sex") == "M" else ("Féminin" if identity.get("sex") == "F" else ""),
        "date_naissance": datetime.fromisoformat(identity["birth_date"]).strftime("%d/%m/%Y") if identity.get("birth_date") else "",
        "lieu_naissance": identity.get("birth_place") or "",
        "adresse": identity.get("address") or "",
        "cin": identity.get("cin_number") or "",
        "cnaps": identity.get("cnaps_number") or "",
        "date_embauche": datetime.fromisoformat(employment["hire_date"]).strftime("%d/%m/%Y") if employment.get("hire_date") else "",
        "poste": employment.get("job_title") or "",
        "categorie_prof": employment.get("professional_category") or "",
        "salaire_base": f"{float(salary_value):,.0f} Ar" if salary_value else "0 Ar",
        "nature_contrat": employment.get("contract_type") or "",
        "etablissement": organization.get("establishment") or "",
        "departement": organization.get("department") or "",
        "service": organization.get("service") or "",
        "unite": organization.get("unit") or "",
    }


def build_worker_reporting_payload(db: Session, worker: models.Worker) -> dict[str, Any]:
    master = build_worker_master_view(db, worker)
    identity = master.identity.data
    employment = master.employment.data
    compensation = master.compensation.data
    organization = master.organization.data

    return {
        "matricule": identity.get("employee_number") or worker.matricule or "",
        "nom": identity.get("last_name") or worker.nom or "",
        "prenom": identity.get("first_name") or worker.prenom or "",
        "sexe": identity.get("sex") or worker.sexe or "",
        "adresse": identity.get("address") or worker.adresse or "",
        "email": identity.get("email") or worker.email or "",
        "telephone": identity.get("phone") or worker.telephone or "",
        "cin": identity.get("cin_number") or worker.cin or "",
        "date_naissance": identity.get("birth_date") or (worker.date_naissance.isoformat() if worker.date_naissance else ""),
        "date_embauche": employment.get("hire_date") or (worker.date_embauche.isoformat() if worker.date_embauche else ""),
        "date_debauche": employment.get("exit_date") or (worker.date_debauche.isoformat() if worker.date_debauche else ""),
        "poste": employment.get("job_title") or worker.poste or "",
        "categorie_prof": employment.get("professional_category") or worker.categorie_prof or "",
        "nature_contrat": employment.get("contract_type") or worker.nature_contrat or "",
        "mode_paiement": compensation.get("payment_mode") or worker.mode_paiement or "",
        "cnaps_num": identity.get("cnaps_number") or worker.cnaps_num or "",
        "nombre_enfant": worker.nombre_enfant if worker.nombre_enfant is not None else "",
        "etablissement": organization.get("establishment") or worker.etablissement or "",
        "departement": organization.get("department") or worker.departement or "",
        "service": organization.get("service") or worker.service or "",
        "unite": organization.get("unit") or worker.unite or "",
        "salaire_base": compensation.get("salary_base") if compensation.get("salary_base") is not None else worker.salaire_base,
        "salaire_horaire": compensation.get("hourly_rate") if compensation.get("hourly_rate") is not None else worker.salaire_horaire,
        "vhm": compensation.get("vhm") if compensation.get("vhm") is not None else worker.vhm,
        "horaire_hebdo": compensation.get("weekly_hours") if compensation.get("weekly_hours") is not None else worker.horaire_hebdo,
    }
