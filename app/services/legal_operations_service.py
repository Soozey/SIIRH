from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models
from ..config.config import BACKEND_ROOT, settings
from ..security import hash_password, seed_iam_catalog
from .audit_service import record_audit
from .employee_portal_service import json_dump, json_load, next_inspector_case_number, next_sequence
from .file_storage import build_static_path, save_upload_file


LEGAL_MODULE_NAMES = [
    "inspection_individual_disputes",
    "collective_grievances",
    "termination_workflows",
    "disciplinary_workflows",
    "economic_dismissal",
    "technical_layoff",
    "document_generation",
    "rbac_and_audit",
]


@dataclass
class SeedWorkerPayload:
    matricule: str
    nom: str
    prenom: str
    sexe: str
    poste: str
    department: str
    service: str
    unit: str
    category: str
    salary: float
    email: str
    date_embauche: date
    nature_contrat: str = "CDI"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dt(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour, minute=0), tzinfo=timezone.utc)


def _safe_username(local_part: str) -> str:
    return f"{local_part.strip().lower()}@siirh.com"


def _count_test_cases() -> int:
    count = 0
    for path in BACKEND_ROOT.glob("test_*.py"):
        try:
            count += path.read_text(encoding="utf-8").count("def test_")
        except OSError:
            continue
    return count


def _serialize_employer_highlight(db: Session, employer: models.Employer) -> dict[str, Any]:
    worker_count = db.query(models.Worker).filter(models.Worker.employer_id == employer.id).count()
    case_count = db.query(models.InspectorCase).filter(models.InspectorCase.employer_id == employer.id).count()
    pv_count = db.query(models.LabourPV).filter(models.LabourPV.employer_id == employer.id).count()
    termination_count = db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.employer_id == employer.id).count()
    return {
        "id": employer.id,
        "raison_sociale": employer.raison_sociale,
        "workers": worker_count,
        "inspection_cases": case_count,
        "pv_generated": pv_count,
        "termination_workflows": termination_count,
    }


def build_legal_modules_status(db: Session, employer_ids: Iterable[int]) -> dict[str, Any]:
    scoped_ids = sorted({int(item) for item in employer_ids if item is not None})
    if not scoped_ids:
        return {
            "modules_implemented": len(LEGAL_MODULE_NAMES),
            "procedures_created": 0,
            "pv_generated": 0,
            "test_cases": _count_test_cases(),
            "employers": [],
            "highlights": [],
            "role_coverage": [],
        }

    employers = db.query(models.Employer).filter(models.Employer.id.in_(scoped_ids)).order_by(models.Employer.raison_sociale.asc()).all()
    procedures_created = (
        db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_(scoped_ids)).count()
        + db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.employer_id.in_(scoped_ids)).count()
        + db.query(models.DisciplinaryCase).filter(models.DisciplinaryCase.employer_id.in_(scoped_ids)).count()
    )
    pv_generated = db.query(models.LabourPV).filter(models.LabourPV.employer_id.in_(scoped_ids)).count()
    highlights = [
        {
            "label": "Active disputes",
            "value": db.query(models.InspectorCase)
            .filter(
                models.InspectorCase.employer_id.in_(scoped_ids),
                models.InspectorCase.status.notin_(("closed", "archived", "CLOTURE", "ARCHIVE")),
            )
            .count(),
        },
        {
            "label": "Collective grievances",
            "value": db.query(models.InspectorCase)
            .filter(models.InspectorCase.employer_id.in_(scoped_ids), models.InspectorCase.case_type.in_(("collective_grievance", "doleance_collective")))
            .count(),
        },
        {
            "label": "Technical layoff workflows",
            "value": db.query(models.TerminationWorkflow)
            .filter(
                models.TerminationWorkflow.employer_id.in_(scoped_ids),
                (
                    (models.TerminationWorkflow.termination_type == "technical_layoff")
                    | (models.TerminationWorkflow.termination_type == "termination_after_technical_layoff")
                ),
            )
            .count(),
        },
        {
            "label": "Economic dismissal workflows",
            "value": db.query(models.TerminationWorkflow)
            .filter(models.TerminationWorkflow.employer_id.in_(scoped_ids), models.TerminationWorkflow.termination_type == "economic_dismissal")
            .count(),
        },
    ]
    return {
        "modules_implemented": len(LEGAL_MODULE_NAMES),
        "procedures_created": procedures_created,
        "pv_generated": pv_generated,
        "test_cases": _count_test_cases(),
        "employers": [_serialize_employer_highlight(db, employer) for employer in employers],
        "highlights": highlights,
        "role_coverage": [
            "system_admin",
            "employer_admin",
            "hr_manager",
            "hr_officer",
            "employee",
            "labor_inspector",
            "labor_inspector_supervisor",
            "staff_delegate",
            "works_council_member",
            "judge_readonly",
            "court_clerk_readonly",
            "auditor_readonly",
        ],
    }


def build_debug_execution_panel(db: Session) -> dict[str, Any]:
    last_seed = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action == "system.seed.legal_demo")
        .order_by(models.AuditLog.created_at.desc())
        .first()
    )
    last_errors: list[dict[str, Any]] = []
    for path in sorted(BACKEND_ROOT.glob("*.err.log"), key=lambda item: item.stat().st_mtime, reverse=True)[:5]:
        try:
            lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
        except OSError:
            continue
        if not lines:
            continue
        last_errors.append(
            {
                "label": path.name,
                "value": lines[-1][:240],
                "at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
            }
        )

    migration_versions = [str(row[0]) for row in db.execute(text("SELECT version_num FROM alembic_version")).fetchall() if row and row[0]]
    last_migrations: list[dict[str, Any]] = []
    versions_dir = BACKEND_ROOT / "alembic" / "versions"
    for version in migration_versions:
        match = next(iter(versions_dir.glob(f"{version}_*.py")), None)
        label = match.name if match else version
        at = datetime.fromtimestamp(match.stat().st_mtime, tz=timezone.utc) if match else None
        last_migrations.append({"label": version, "value": label, "at": at})
    if not last_migrations:
        for path in sorted(versions_dir.glob("*.py"), key=lambda item: item.stat().st_mtime, reverse=True)[:3]:
            last_migrations.append(
                {
                    "label": path.stem.split("_", 1)[0],
                    "value": path.name,
                    "at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
                }
            )

    seed_items: list[dict[str, Any]] = []
    if last_seed is not None:
        payload = json_load(last_seed.after_json, {})
        summary = f"employers={payload.get('employers_seeded', 0)}, workers={payload.get('workers_seeded', 0)}, cases={payload.get('cases_seeded', 0)}, pv={payload.get('pv_seeded', 0)}"
        seed_items.append({"label": "system.seed.legal_demo", "value": summary, "at": last_seed.created_at})

    return {
        "last_migrations_executed": last_migrations,
        "last_seed_executed": seed_items,
        "last_errors": last_errors,
        "modules_created": [
            {"label": "Inspection workspace", "value": "inspection, conciliation, PV, GED", "at": None},
            {"label": "People ops legal flows", "value": "disciplinary, resignation, dismissal, economic, technical layoff", "at": None},
            {"label": "Legal dashboard", "value": "SIIRH LEGAL MODULES STATUS", "at": None},
            {"label": "Execution debug", "value": "DEBUG EXECUTION PANEL", "at": None},
        ],
    }


def _get_or_create_employer(db: Session, *, raison_sociale: str, **fields: Any) -> models.Employer:
    item = db.query(models.Employer).filter(models.Employer.raison_sociale == raison_sociale).first()
    if item is None:
        item = models.Employer(raison_sociale=raison_sociale)
        db.add(item)
        db.flush()
    for key, value in fields.items():
        setattr(item, key, value)
    return item


def _get_or_create_worker(db: Session, employer: models.Employer, payload: SeedWorkerPayload) -> models.Worker:
    item = db.query(models.Worker).filter(models.Worker.matricule == payload.matricule).first()
    if item is None:
        item = models.Worker(employer_id=employer.id, matricule=payload.matricule)
        db.add(item)
        db.flush()
    item.employer_id = employer.id
    item.nom = payload.nom
    item.prenom = payload.prenom
    item.sexe = payload.sexe
    item.poste = payload.poste
    item.departement = payload.department
    item.service = payload.service
    item.unite = payload.unit
    item.categorie_prof = payload.category
    item.salaire_base = payload.salary
    item.email = payload.email
    item.date_embauche = payload.date_embauche
    item.nature_contrat = payload.nature_contrat
    item.mode_paiement = item.mode_paiement or "virement"
    item.horaire_hebdo = item.horaire_hebdo or 40
    item.vhm = item.vhm or 173.33
    item.secteur = item.secteur or "non_agricole"
    item.adresse = item.adresse or "Antananarivo"
    item.telephone = item.telephone or "0340000000"
    item.date_naissance = item.date_naissance or date(1995, 1, 1)
    item.cin = item.cin or f"CIN-{payload.matricule}"
    item.groupe_preavis = item.groupe_preavis or 3
    item.salaire_horaire = item.salaire_horaire or round(payload.salary / 173.33, 2)
    return item


def _get_or_create_contract(db: Session, employer: models.Employer, worker: models.Worker) -> models.CustomContract:
    item = (
        db.query(models.CustomContract)
        .filter(models.CustomContract.employer_id == employer.id, models.CustomContract.worker_id == worker.id)
        .order_by(models.CustomContract.id.asc())
        .first()
    )
    content = (
        f"Contrat de travail\n"
        f"Employeur: {employer.raison_sociale}\n"
        f"Salarie: {worker.prenom} {worker.nom}\n"
        f"Poste: {worker.poste}\n"
        f"Nature du contrat: {worker.nature_contrat or 'CDI'}\n"
        f"Salaire de base: {worker.salaire_base}\n"
    )
    if item is None:
        item = models.CustomContract(
            worker_id=worker.id,
            employer_id=employer.id,
            title=f"Contrat {worker.prenom} {worker.nom}",
            content=content,
            template_type="employment_contract",
            is_default=True,
            validation_status="active_non_validated",
            inspection_status="pending_review",
        )
        db.add(item)
        db.flush()
    else:
        item.title = f"Contrat {worker.prenom} {worker.nom}"
        item.content = content
    return item


def _get_or_create_user(
    db: Session,
    *,
    username: str,
    role_code: str,
    full_name: str,
    employer_id: int | None = None,
    worker_id: int | None = None,
) -> models.AppUser:
    item = db.query(models.AppUser).filter(models.AppUser.username == username).first()
    if item is None:
        item = models.AppUser(
            username=username,
            role_code=role_code,
            full_name=full_name,
            employer_id=employer_id,
            worker_id=worker_id,
            is_active=True,
            account_status="PASSWORD_RESET_REQUIRED",
            must_change_password=True,
            password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        )
        db.add(item)
        db.flush()
    else:
        item.role_code = role_code
        item.full_name = full_name
        item.employer_id = employer_id
        item.worker_id = worker_id
        item.is_active = True
        if not getattr(item, "account_status", None):
            item.account_status = "ACTIVE"
    return item


def _get_or_create_assignment(db: Session, employer_id: int, inspector_user_id: int, assigned_by_user_id: int | None) -> models.LabourInspectorAssignment:
    item = (
        db.query(models.LabourInspectorAssignment)
        .filter(
            models.LabourInspectorAssignment.employer_id == employer_id,
            models.LabourInspectorAssignment.inspector_user_id == inspector_user_id,
        )
        .first()
    )
    if item is None:
        item = models.LabourInspectorAssignment(
            employer_id=employer_id,
            inspector_user_id=inspector_user_id,
            assigned_by_user_id=assigned_by_user_id,
            assignment_scope="portfolio",
            status="active",
            circonscription="Antananarivo",
            notes="Affectation seed demo juridique Madagascar 2024",
        )
        db.add(item)
        db.flush()
    else:
        item.status = "active"
        item.circonscription = "Antananarivo"
        item.notes = "Affectation seed demo juridique Madagascar 2024"
        item.assigned_by_user_id = assigned_by_user_id
    return item


def _get_or_create_case(
    db: Session,
    *,
    employer: models.Employer,
    worker: models.Worker | None,
    filed_by_user: models.AppUser | None,
    assigned_inspector_user: models.AppUser | None,
    case_type: str,
    sub_type: str | None,
    source_party: str,
    subject: str,
    description: str,
    status: str,
    current_stage: str,
    category: str,
    resolution_type: str | None = None,
    outcome_summary: str | None = None,
    urgency: str = "normal",
    received_at: datetime | None = None,
) -> models.InspectorCase:
    item = (
        db.query(models.InspectorCase)
        .filter(models.InspectorCase.employer_id == employer.id, models.InspectorCase.subject == subject)
        .first()
    )
    if item is None:
        item = models.InspectorCase(
            case_number=next_inspector_case_number(db, employer.id),
            employer_id=employer.id,
            worker_id=worker.id if worker else None,
            filed_by_user_id=filed_by_user.id if filed_by_user else None,
            assigned_inspector_user_id=assigned_inspector_user.id if assigned_inspector_user else None,
            case_type=case_type,
            sub_type=sub_type,
            source_party=source_party,
            subject=subject,
            description=description,
            category=category,
            district="Antananarivo",
            urgency=urgency,
            status=status,
            current_stage=current_stage,
            confidentiality="standard",
            amicable_attempt_status="documented",
            outcome_summary=outcome_summary,
            resolution_type=resolution_type,
            received_at=received_at or _now(),
            is_sensitive=False,
            attachments_json="[]",
            tags_json=json_dump(["legal_seed"]),
        )
        db.add(item)
        db.flush()
    else:
        item.worker_id = worker.id if worker else None
        item.filed_by_user_id = filed_by_user.id if filed_by_user else None
        item.assigned_inspector_user_id = assigned_inspector_user.id if assigned_inspector_user else None
        item.case_type = case_type
        item.sub_type = sub_type
        item.source_party = source_party
        item.description = description
        item.category = category
        item.district = "Antananarivo"
        item.urgency = urgency
        item.status = status
        item.current_stage = current_stage
        item.outcome_summary = outcome_summary
        item.resolution_type = resolution_type
        item.received_at = received_at or item.received_at or _now()
        item.last_response_at = _now()
    return item


def _get_or_create_claim(
    db: Session,
    *,
    case_item: models.InspectorCase,
    created_by_user: models.AppUser | None,
    claim_type: str,
    claimant_party: str,
    factual_basis: str,
    amount_requested: float | None = None,
    status: str = "submitted",
    conciliation_outcome: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> models.LabourCaseClaim:
    item = (
        db.query(models.LabourCaseClaim)
        .filter(models.LabourCaseClaim.case_id == case_item.id, models.LabourCaseClaim.claim_type == claim_type)
        .first()
    )
    if item is None:
        item = models.LabourCaseClaim(
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            created_by_user_id=created_by_user.id if created_by_user else None,
            claim_type=claim_type,
            claimant_party=claimant_party,
            factual_basis=factual_basis,
            amount_requested=amount_requested,
            status=status,
            conciliation_outcome=conciliation_outcome,
            metadata_json=json_dump(metadata or {}),
        )
        db.add(item)
        db.flush()
    else:
        item.factual_basis = factual_basis
        item.amount_requested = amount_requested
        item.status = status
        item.conciliation_outcome = conciliation_outcome
        item.metadata_json = json_dump(metadata or {})
    return item


def _get_or_create_event(
    db: Session,
    *,
    case_item: models.InspectorCase,
    created_by_user: models.AppUser | None,
    event_type: str,
    title: str,
    description: str,
    status: str,
    scheduled_at: datetime | None,
    completed_at: datetime | None,
    metadata: dict[str, Any] | None = None,
) -> models.LabourCaseEvent:
    item = (
        db.query(models.LabourCaseEvent)
        .filter(models.LabourCaseEvent.case_id == case_item.id, models.LabourCaseEvent.title == title)
        .first()
    )
    if item is None:
        item = models.LabourCaseEvent(
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            created_by_user_id=created_by_user.id if created_by_user else None,
            event_type=event_type,
            title=title,
            description=description,
            status=status,
            scheduled_at=scheduled_at,
            completed_at=completed_at,
            participants_json="[]",
            metadata_json=json_dump(metadata or {}),
        )
        db.add(item)
        db.flush()
    else:
        item.description = description
        item.status = status
        item.scheduled_at = scheduled_at
        item.completed_at = completed_at
        item.metadata_json = json_dump(metadata or {})
    return item


def _next_pv_number(db: Session, employer_id: int) -> str:
    return next_sequence(
        db,
        model=models.LabourPV,
        field_name="pv_number",
        prefix=f"PV-IT-{employer_id:03d}-{datetime.now(timezone.utc).strftime('%Y%m')}",
    )


def _next_labour_message_reference(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m")
    return next_sequence(
        db,
        model=models.LabourFormalMessage,
        field_name="reference_number",
        prefix=f"LMSG-{today}",
    )


def _get_or_create_pv(
    db: Session,
    *,
    case_item: models.InspectorCase,
    generated_by_user: models.AppUser | None,
    pv_type: str,
    title: str,
    content: str,
    status: str,
    measures_to_execute: str | None = None,
    execution_deadline: datetime | None = None,
    delivered_to_parties_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> models.LabourPV:
    item = (
        db.query(models.LabourPV)
        .filter(models.LabourPV.case_id == case_item.id, models.LabourPV.pv_type == pv_type)
        .first()
    )
    if item is None:
        item = models.LabourPV(
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            generated_by_user_id=generated_by_user.id if generated_by_user else None,
            pv_number=_next_pv_number(db, case_item.employer_id),
            pv_type=pv_type,
            title=title,
            content=content,
            status=status,
            version_number=1,
            measures_to_execute=measures_to_execute,
            execution_deadline=execution_deadline,
            delivered_to_parties_at=delivered_to_parties_at,
            metadata_json=json_dump(metadata or {}),
        )
        db.add(item)
        db.flush()
    else:
        item.title = title
        item.content = content
        item.status = status
        item.measures_to_execute = measures_to_execute
        item.execution_deadline = execution_deadline
        item.delivered_to_parties_at = delivered_to_parties_at
        item.metadata_json = json_dump(metadata or {})
    return item


def _ensure_seed_upload(relative_path: str, content: str) -> dict[str, Any]:
    payload = content.encode("utf-8")
    save_upload_file(io.BytesIO(payload), filename=relative_path)
    return {
        "storage_path": relative_path,
        "static_url": build_static_path(relative_path),
        "checksum": hashlib.sha256(payload).hexdigest(),
        "file_size": len(payload),
    }


def _get_or_create_job_offer(
    db: Session,
    *,
    employer: models.Employer,
    created_by_user: models.AppUser | None,
    title: str,
    department: str,
    location: str,
    contract_type: str,
    status: str,
    salary_range: str,
    description: str,
    skills_required: str,
    workflow_status: str,
    validation_comment: str | None,
    publication_mode: str | None,
    publication_url: str | None,
    desired_start_date: date | None,
    application_deadline: date | None,
    submitted_to_inspection_at: datetime | None,
    attachments: list[dict[str, Any]] | None = None,
    announcement_status: str | None = None,
) -> tuple[models.RecruitmentJobPosting, models.RecruitmentJobProfile]:
    job = (
        db.query(models.RecruitmentJobPosting)
        .filter(models.RecruitmentJobPosting.employer_id == employer.id, models.RecruitmentJobPosting.title == title)
        .first()
    )
    if job is None:
        job = models.RecruitmentJobPosting(
            employer_id=employer.id,
            title=title,
            department=department,
            location=location,
            contract_type=contract_type,
            status=status,
            salary_range=salary_range,
            description=description,
            skills_required=skills_required,
        )
        db.add(job)
        db.flush()
    else:
        job.department = department
        job.location = location
        job.contract_type = contract_type
        job.status = status
        job.salary_range = salary_range
        job.description = description
        job.skills_required = skills_required

    profile = db.query(models.RecruitmentJobProfile).filter(models.RecruitmentJobProfile.job_posting_id == job.id).first()
    if profile is None:
        profile = models.RecruitmentJobProfile(job_posting_id=job.id)
        db.add(profile)
        db.flush()

    profile.manager_title = department
    profile.mission_summary = description
    profile.main_activities_json = json_dump(
        [
            "Preparation des dossiers et suivi des obligations sociales",
            "Coordination avec les equipes RH, paie et inspection",
            "Production des rapports et pieces justificatives",
        ]
    )
    profile.technical_skills_json = json_dump([item.strip() for item in skills_required.split(",") if item.strip()])
    profile.behavioral_skills_json = json_dump(["rigueur", "organisation", "communication"])
    profile.education_level = "Bac+3 minimum"
    profile.experience_required = "3 ans minimum"
    profile.languages_json = json_dump(["Français", "Malgache"])
    profile.tools_json = json_dump(["Suite bureautique", "SIIRH"])
    profile.salary_min = None
    profile.salary_max = None
    profile.working_hours = "40h/semaine"
    profile.benefits_json = json_dump(["CNaPS", "Mutuelle", "Transport"])
    profile.desired_start_date = desired_start_date
    profile.application_deadline = application_deadline
    profile.publication_channels_json = json_dump(["presse", "site_entreprise", "inspection"])
    profile.classification = "Cadre" if "responsable" in title.lower() or "chef" in title.lower() else "Employe"
    profile.workflow_status = workflow_status
    profile.validation_comment = validation_comment
    profile.validated_by_user_id = created_by_user.id if created_by_user and workflow_status in {"validated", "validated_with_observations"} else None
    profile.validated_at = _now() if profile.validated_by_user_id else None
    profile.assistant_source_json = json_dump({"source": "legal_seed"})
    profile.interview_criteria_json = json_dump(["competences_metier", "communication", "conformite"])
    profile.announcement_title = f"{title} - {employer.raison_sociale}"
    profile.announcement_body = description
    profile.announcement_status = announcement_status or ("published" if status == "published" else "draft")
    profile.announcement_slug = f"{employer.raison_sociale.lower().replace(' ', '-')}-{title.lower().replace(' ', '-')}"
    profile.announcement_share_pack_json = json_dump(
        {
            "title": f"{title} - {employer.raison_sociale}",
            "slug": profile.announcement_slug,
            "public_url": publication_url or f"https://jobs.siirh.local/{profile.announcement_slug}",
            "web_body": description,
            "email_subject": f"Recrutement {title}",
            "email_body": description,
            "facebook_text": description,
            "linkedin_text": description,
            "whatsapp_text": description,
            "copy_text": description,
            "channels": ["linkedin", "site", "inspection"],
        }
    )
    profile.submission_attachments_json = json_dump(attachments or [])
    profile.contract_guidance_json = json_dump({"legal_review": "required"})
    profile.publication_mode = publication_mode
    profile.publication_url = publication_url
    profile.submitted_to_inspection_at = submitted_to_inspection_at
    profile.last_reviewed_at = _now()

    activity_exists = (
        db.query(models.RecruitmentActivity)
        .filter(
            models.RecruitmentActivity.job_posting_id == job.id,
            models.RecruitmentActivity.event_type == "inspection.seed.job_offer",
        )
        .first()
    )
    if activity_exists is None:
        db.add(
            models.RecruitmentActivity(
                employer_id=employer.id,
                job_posting_id=job.id,
                actor_user_id=created_by_user.id if created_by_user else None,
                event_type="inspection.seed.job_offer",
                visibility="internal",
                message=f"Offre seeded pour le portail inspection: {title}",
                payload_json=json_dump({"workflow_status": workflow_status, "status": status}),
            )
        )

    return job, profile


def _get_or_create_formal_message(
    db: Session,
    *,
    sender_user: models.AppUser,
    subject: str,
    body: str,
    message_scope: str,
    related_entity_type: str | None,
    related_entity_id: str | None,
    recipients: list[dict[str, Any]],
    status: str = "sent",
    metadata: dict[str, Any] | None = None,
) -> models.LabourFormalMessage:
    item = (
        db.query(models.LabourFormalMessage)
        .filter(models.LabourFormalMessage.sender_user_id == sender_user.id, models.LabourFormalMessage.subject == subject)
        .first()
    )
    if item is None:
        item = models.LabourFormalMessage(
            reference_number=_next_labour_message_reference(db),
            thread_key=None,
            sender_user_id=sender_user.id,
            sender_employer_id=sender_user.employer_id,
            sender_role=sender_user.role_code,
            subject=subject,
            body=body,
            message_scope=message_scope,
            status=status,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            attachments_json="[]",
            metadata_json=json_dump(metadata or {}),
            sent_at=_now() if status == "sent" else None,
        )
        item.thread_key = item.reference_number
        db.add(item)
        db.flush()
    else:
        item.sender_employer_id = sender_user.employer_id
        item.sender_role = sender_user.role_code
        item.body = body
        item.message_scope = message_scope
        item.status = status
        item.related_entity_type = related_entity_type
        item.related_entity_id = related_entity_id
        item.metadata_json = json_dump(metadata or {})
        item.sent_at = _now() if status == "sent" else item.sent_at

    existing_recipients = {(recipient.user_id, recipient.employer_id, recipient.recipient_type): recipient for recipient in item.recipients}
    for recipient_payload in recipients:
        key = (
            recipient_payload.get("user_id"),
            recipient_payload.get("employer_id"),
            recipient_payload.get("recipient_type", "employer"),
        )
        recipient = existing_recipients.get(key)
        if recipient is None:
            recipient = models.LabourFormalMessageRecipient(
                message_id=item.id,
                employer_id=recipient_payload.get("employer_id"),
                user_id=recipient_payload.get("user_id"),
                recipient_type=recipient_payload.get("recipient_type", "employer"),
                status=recipient_payload.get("status", status),
                metadata_json=json_dump(recipient_payload.get("metadata", {})),
            )
            db.add(recipient)
        else:
            recipient.status = recipient_payload.get("status", status)
            recipient.metadata_json = json_dump(recipient_payload.get("metadata", {}))
    return item


def _get_or_create_compliance_review(
    db: Session,
    *,
    employer: models.Employer,
    worker: models.Worker | None,
    contract: models.CustomContract | None,
    created_by_user: models.AppUser | None,
    reviewed_by_user: models.AppUser | None,
    review_type: str,
    review_stage: str,
    status: str,
    source_module: str,
    due_at: datetime | None,
    tags: list[str] | None = None,
) -> models.ComplianceReview:
    item = (
        db.query(models.ComplianceReview)
        .filter(
            models.ComplianceReview.employer_id == employer.id,
            models.ComplianceReview.review_type == review_type,
            models.ComplianceReview.source_module == source_module,
            models.ComplianceReview.worker_id == (worker.id if worker else None),
        )
        .first()
    )
    if item is None:
        item = models.ComplianceReview(
            employer_id=employer.id,
            worker_id=worker.id if worker else None,
            contract_id=contract.id if contract else None,
            review_type=review_type,
            review_stage=review_stage,
            status=status,
            source_module=source_module,
            checklist_json=json_dump([]),
            observations_json=json_dump([]),
            requested_documents_json=json_dump([]),
            tags_json=json_dump(tags or ["legal_seed"]),
            due_at=due_at,
            submitted_to_inspector_at=_now(),
            reviewed_by_user_id=reviewed_by_user.id if reviewed_by_user else None,
            created_by_user_id=created_by_user.id if created_by_user else None,
        )
        db.add(item)
        db.flush()
    else:
        item.contract_id = contract.id if contract else item.contract_id
        item.review_stage = review_stage
        item.status = status
        item.due_at = due_at
        item.tags_json = json_dump(tags or ["legal_seed"])
        item.submitted_to_inspector_at = item.submitted_to_inspector_at or _now()
        item.reviewed_by_user_id = reviewed_by_user.id if reviewed_by_user else item.reviewed_by_user_id
        item.created_by_user_id = created_by_user.id if created_by_user else item.created_by_user_id
    return item


def _get_or_create_observation(
    db: Session,
    *,
    review: models.ComplianceReview,
    author_user: models.AppUser | None,
    observation_type: str,
    status_marker: str,
    message: str,
    structured_payload: dict[str, Any] | None = None,
) -> models.InspectorObservation:
    item = (
        db.query(models.InspectorObservation)
        .filter(models.InspectorObservation.review_id == review.id, models.InspectorObservation.message == message)
        .first()
    )
    if item is None:
        item = models.InspectorObservation(
            review_id=review.id,
            employer_id=review.employer_id,
            author_user_id=author_user.id if author_user else None,
            visibility="restricted",
            observation_type=observation_type,
            status_marker=status_marker,
            message=message,
            structured_payload_json=json_dump(structured_payload or {}),
        )
        db.add(item)
        db.flush()
    else:
        item.author_user_id = author_user.id if author_user else item.author_user_id
        item.observation_type = observation_type
        item.status_marker = status_marker
        item.structured_payload_json = json_dump(structured_payload or {})
    return item


def _get_or_create_inspector_message(
    db: Session,
    *,
    case_item: models.InspectorCase,
    author_user: models.AppUser | None,
    sender_role: str,
    direction: str,
    message_type: str,
    visibility: str,
    body: str,
) -> models.InspectorMessage:
    item = (
        db.query(models.InspectorMessage)
        .filter(models.InspectorMessage.case_id == case_item.id, models.InspectorMessage.body == body)
        .first()
    )
    if item is None:
        item = models.InspectorMessage(
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            author_user_id=author_user.id if author_user else None,
            sender_role=sender_role,
            direction=direction,
            message_type=message_type,
            visibility=visibility,
            body=body,
            attachments_json="[]",
            status="sent",
        )
        db.add(item)
        db.flush()
    else:
        item.author_user_id = author_user.id if author_user else item.author_user_id
        item.sender_role = sender_role
        item.direction = direction
        item.message_type = message_type
        item.visibility = visibility
        item.status = "sent"
    case_item.last_response_at = _now()
    return item


def _get_or_create_case_assignment(
    db: Session,
    *,
    case_item: models.InspectorCase,
    inspector_user: models.AppUser,
    assigned_by_user: models.AppUser | None,
    scope: str,
    notes: str,
) -> models.InspectorCaseAssignment:
    item = (
        db.query(models.InspectorCaseAssignment)
        .filter(
            models.InspectorCaseAssignment.case_id == case_item.id,
            models.InspectorCaseAssignment.inspector_user_id == inspector_user.id,
        )
        .first()
    )
    if item is None:
        item = models.InspectorCaseAssignment(
            case_id=case_item.id,
            inspector_user_id=inspector_user.id,
            assigned_by_user_id=assigned_by_user.id if assigned_by_user else None,
            scope=scope,
            status="active",
            notes=notes,
        )
        db.add(item)
        db.flush()
    else:
        item.assigned_by_user_id = assigned_by_user.id if assigned_by_user else item.assigned_by_user_id
        item.scope = scope
        item.status = "active"
        item.notes = notes
        item.revoked_at = None
    return item


def _get_or_create_inspection_document(
    db: Session,
    *,
    case_item: models.InspectorCase,
    uploaded_by_user: models.AppUser | None,
    document_type: str,
    title: str,
    description: str,
    original_name: str,
    body: str,
    notes: str,
) -> models.InspectionDocument:
    document = (
        db.query(models.InspectionDocument)
        .filter(models.InspectionDocument.case_id == case_item.id, models.InspectionDocument.title == title)
        .first()
    )
    if document is None:
        document = models.InspectionDocument(
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            uploaded_by_user_id=uploaded_by_user.id if uploaded_by_user else None,
            document_type=document_type,
            title=title,
            description=description,
            visibility="case_parties",
            confidentiality="restricted",
            status="active",
            current_version_number=0,
            tags_json=json_dump(["legal_seed", document_type]),
        )
        db.add(document)
        db.flush()
    else:
        document.uploaded_by_user_id = uploaded_by_user.id if uploaded_by_user else document.uploaded_by_user_id
        document.document_type = document_type
        document.description = description
        document.status = "active"

    version = (
        db.query(models.InspectionDocumentVersion)
        .filter(models.InspectionDocumentVersion.document_id == document.id, models.InspectionDocumentVersion.version_number == 1)
        .first()
    )
    stored = _ensure_seed_upload(
        f"inspection_vault/{case_item.case_number}/document_{document.id}/v001_seed_{original_name}",
        body,
    )
    if version is None:
        version = models.InspectionDocumentVersion(
            document_id=document.id,
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            uploaded_by_user_id=uploaded_by_user.id if uploaded_by_user else None,
            version_number=1,
            file_name=original_name,
            original_name=original_name,
            storage_path=stored["storage_path"],
            static_url=stored["static_url"],
            content_type="text/plain",
            file_size=stored["file_size"],
            checksum=stored["checksum"],
            notes=notes,
        )
        db.add(version)
        db.flush()
    else:
        version.uploaded_by_user_id = uploaded_by_user.id if uploaded_by_user else version.uploaded_by_user_id
        version.storage_path = stored["storage_path"]
        version.static_url = stored["static_url"]
        version.file_size = stored["file_size"]
        version.checksum = stored["checksum"]
        version.notes = notes

    document.current_version_number = 1

    access_exists = (
        db.query(models.InspectionDocumentAccessLog)
        .filter(
            models.InspectionDocumentAccessLog.document_id == document.id,
            models.InspectionDocumentAccessLog.action == "seed_load",
        )
        .first()
    )
    if access_exists is None:
        db.add(
            models.InspectionDocumentAccessLog(
                document_id=document.id,
                version_id=version.id,
                case_id=case_item.id,
                user_id=uploaded_by_user.id if uploaded_by_user else None,
                action="seed_load",
                metadata_json=json_dump({"source": "legal_seed"}),
            )
        )
    return document


def _get_or_create_disciplinary_case(
    db: Session,
    *,
    employer: models.Employer,
    worker: models.Worker,
    inspection_case: models.InspectorCase | None,
    created_by_user: models.AppUser | None,
    subject: str,
    description: str,
    hearing_at: datetime | None,
) -> models.DisciplinaryCase:
    item = (
        db.query(models.DisciplinaryCase)
        .filter(models.DisciplinaryCase.employer_id == employer.id, models.DisciplinaryCase.subject == subject)
        .first()
    )
    if item is None:
        item = models.DisciplinaryCase(
            employer_id=employer.id,
            worker_id=worker.id,
            inspection_case_id=inspection_case.id if inspection_case else None,
            created_by_user_id=created_by_user.id if created_by_user else None,
            case_type="hearing",
            severity="high",
            status="hearing_scheduled",
            subject=subject,
            description=description,
            happened_at=_now() - timedelta(days=12),
            hearing_at=hearing_at,
            sanction_type="dismissal",
            documents_json=json_dump(
                [
                    "notification_ecrite_faits",
                    "convocation_entretien_prealable",
                    "preuve_notification",
                    "rapport_interne",
                ]
            ),
        )
        db.add(item)
        db.flush()
    else:
        item.hearing_at = hearing_at
        item.inspection_case_id = inspection_case.id if inspection_case else item.inspection_case_id
    return item


def _get_or_create_termination(
    db: Session,
    *,
    employer: models.Employer,
    worker: models.Worker,
    contract: models.CustomContract | None,
    inspection_case: models.InspectorCase | None,
    created_by_user: models.AppUser | None,
    termination_type: str,
    motif: str,
    status: str,
    effective_date: date,
    notification_sent_at: datetime | None,
    notification_received_at: datetime | None,
    pre_hearing_notice_sent_at: datetime | None = None,
    pre_hearing_scheduled_at: datetime | None = None,
    preavis_start_date: date | None = None,
    economic_consultation_started_at: date | None = None,
    economic_inspection_referral_at: date | None = None,
    technical_layoff_declared_at: date | None = None,
    technical_layoff_end_at: date | None = None,
    sensitive_case: bool = False,
    inspection_required: bool = False,
    legal_risk_level: str = "normal",
    checklist: list[dict[str, Any]] | None = None,
    documents: list[str] | None = None,
    legal_metadata: dict[str, Any] | None = None,
    readonly_stc: dict[str, Any] | None = None,
    notes: str | None = None,
) -> models.TerminationWorkflow:
    item = (
        db.query(models.TerminationWorkflow)
        .filter(models.TerminationWorkflow.employer_id == employer.id, models.TerminationWorkflow.worker_id == worker.id, models.TerminationWorkflow.termination_type == termination_type)
        .first()
    )
    if item is None:
        item = models.TerminationWorkflow(
            employer_id=employer.id,
            worker_id=worker.id,
            contract_id=contract.id if contract else None,
            inspection_case_id=inspection_case.id if inspection_case else None,
            created_by_user_id=created_by_user.id if created_by_user else None,
            termination_type=termination_type,
            motif=motif,
            status=status,
            effective_date=effective_date,
            notification_sent_at=notification_sent_at,
            notification_received_at=notification_received_at,
            pre_hearing_notice_sent_at=pre_hearing_notice_sent_at,
            pre_hearing_scheduled_at=pre_hearing_scheduled_at,
            preavis_start_date=preavis_start_date,
            economic_consultation_started_at=economic_consultation_started_at,
            economic_inspection_referral_at=economic_inspection_referral_at,
            technical_layoff_declared_at=technical_layoff_declared_at,
            technical_layoff_end_at=technical_layoff_end_at,
            sensitive_case=sensitive_case,
            inspection_required=inspection_required,
            legal_risk_level=legal_risk_level,
            checklist_json=json_dump(checklist or []),
            documents_json=json_dump(documents or []),
            legal_metadata_json=json_dump(legal_metadata or {}),
            readonly_stc_json=json_dump(readonly_stc or {}),
            notes=notes,
        )
        db.add(item)
        db.flush()
    else:
        item.contract_id = contract.id if contract else item.contract_id
        item.inspection_case_id = inspection_case.id if inspection_case else item.inspection_case_id
        item.motif = motif
        item.status = status
        item.effective_date = effective_date
        item.notification_sent_at = notification_sent_at
        item.notification_received_at = notification_received_at
        item.pre_hearing_notice_sent_at = pre_hearing_notice_sent_at
        item.pre_hearing_scheduled_at = pre_hearing_scheduled_at
        item.preavis_start_date = preavis_start_date
        item.economic_consultation_started_at = economic_consultation_started_at
        item.economic_inspection_referral_at = economic_inspection_referral_at
        item.technical_layoff_declared_at = technical_layoff_declared_at
        item.technical_layoff_end_at = technical_layoff_end_at
        item.sensitive_case = sensitive_case
        item.inspection_required = inspection_required
        item.legal_risk_level = legal_risk_level
        item.checklist_json = json_dump(checklist or [])
        item.documents_json = json_dump(documents or [])
        item.legal_metadata_json = json_dump(legal_metadata or {})
        item.readonly_stc_json = json_dump(readonly_stc or {})
        item.notes = notes
    return item


def seed_legal_demo_data(db: Session, actor: models.AppUser | None = None) -> dict[str, Any]:
    seed_iam_catalog(db)

    avenir = _get_or_create_employer(
        db,
        raison_sociale="ENTREPRISE AVENIR SARL",
        activite="Services numeriques et support RH",
        adresse="Lot II M 45 Ankorondrano",
        ville="Antananarivo",
        pays="Madagascar",
        telephone="0341100001",
        email="contact@avenir.example",
        representant="Ramanitra Tojo",
        contact_rh="Rasoanaivo Hanitra",
        nif="400000001",
        stat="62011 11 2024 00001",
        rcs="TNR 2024 B 00001",
        cnaps_num="CNaPS-AVENIR-001",
    )
    madatech = _get_or_create_employer(
        db,
        raison_sociale="MADATECH INDUSTRIES",
        activite="Transformation industrielle et maintenance",
        adresse="Zone industrielle Forello Tanjombato",
        ville="Antananarivo",
        pays="Madagascar",
        telephone="0341100002",
        email="contact@madatech.example",
        representant="Rakoto Andry",
        contact_rh="Randriamialy Voahangy",
        nif="400000002",
        stat="25999 11 2024 00002",
        rcs="TNR 2024 B 00002",
        cnaps_num="CNaPS-MADATECH-002",
    )

    avenir_workers_payload = [
        SeedWorkerPayload("AVN0001", "RAKOTONDRABE", "Hanitra", "F", "Chargee RH", "RH", "Administration RH", "Pole RH", "Cadre", 1400000, "hanitra.rakotondrabe@avenir.example", date(2021, 2, 15)),
        SeedWorkerPayload("AVN0002", "RATSIMBAZAFY", "Tovo", "M", "Technicien support", "Operations", "Support", "Equipe support", "Employe", 900000, "tovo.ratsimbazafy@avenir.example", date(2020, 6, 1)),
        SeedWorkerPayload("AVN0003", "RAFANOMEZANTSOA", "Lova", "F", "Assistante administrative", "Administration", "Backoffice", "Unite documents", "Employe", 780000, "lova.rafanomezantsoa@avenir.example", date(2022, 1, 10)),
        SeedWorkerPayload("AVN0004", "RANDRIANANTOANINA", "Toky", "M", "Developpeur applicatif", "IT", "Applications", "Equipe produit", "Cadre", 1600000, "toky.randrianantoanina@avenir.example", date(2019, 9, 23)),
        SeedWorkerPayload("AVN0005", "RASOAMANARIVO", "Fanja", "F", "Comptable", "Finance", "Comptabilite", "Equipe finance", "Employe", 1200000, "fanja.rasoamanarivo@avenir.example", date(2018, 4, 4)),
    ]
    madatech_workers_payload = [
        SeedWorkerPayload("MDT0001", "RAKOTOMALALA", "Bodo", "F", "Cheffe d'atelier", "Production", "Extrusion", "Ligne A", "Cadre", 1500000, "bodo.rakotomalala@madatech.example", date(2017, 7, 1)),
        SeedWorkerPayload("MDT0002", "RABEARIMANANA", "Solo", "M", "Operateur machine", "Production", "Extrusion", "Ligne A", "Employe", 850000, "solo.rabearimanana@madatech.example", date(2021, 3, 12)),
        SeedWorkerPayload("MDT0003", "RAKOTONIRINA", "Mamy", "M", "Magasinier", "Logistique", "Depot", "Equipe stock", "Employe", 820000, "mamy.rakotonirina@madatech.example", date(2020, 11, 2)),
        SeedWorkerPayload("MDT0004", "RANDRIANARISON", "Aina", "F", "Assistante QHSE", "QHSE", "Conformite", "Equipe audit", "Employe", 980000, "aina.randrianarison@madatech.example", date(2022, 5, 16)),
        SeedWorkerPayload("MDT0005", "RABENARIVO", "Koloina", "F", "Responsable maintenance", "Maintenance", "Technique", "Equipe maintenance", "Cadre", 1450000, "koloina.rabenarivo@madatech.example", date(2016, 8, 8)),
    ]

    avenir_workers = [_get_or_create_worker(db, avenir, payload) for payload in avenir_workers_payload]
    madatech_workers = [_get_or_create_worker(db, madatech, payload) for payload in madatech_workers_payload]
    all_workers = avenir_workers + madatech_workers
    contracts = [_get_or_create_contract(db, avenir, worker) for worker in avenir_workers] + [_get_or_create_contract(db, madatech, worker) for worker in madatech_workers]

    admin_user = _get_or_create_user(db, username="admin@siirh.com", role_code="admin", full_name="System Administrator")
    employer_admin_avenir = _get_or_create_user(db, username=_safe_username("employer.admin.avenir"), role_code="employer_admin", full_name="Employer Admin Avenir", employer_id=avenir.id)
    hr_manager_avenir = _get_or_create_user(db, username=_safe_username("hr.manager.avenir"), role_code="hr_manager", full_name="HR Manager Avenir", employer_id=avenir.id)
    hr_officer_avenir = _get_or_create_user(db, username=_safe_username("hr.officer.avenir"), role_code="hr_officer", full_name="HR Officer Avenir", employer_id=avenir.id)
    employer_admin_madatech = _get_or_create_user(db, username=_safe_username("employer.admin.madatech"), role_code="employer_admin", full_name="Employer Admin Madatech", employer_id=madatech.id)
    hr_manager_madatech = _get_or_create_user(db, username=_safe_username("hr.manager.madatech"), role_code="hr_manager", full_name="HR Manager Madatech", employer_id=madatech.id)
    hr_officer_madatech = _get_or_create_user(db, username=_safe_username("hr.officer.madatech"), role_code="hr_officer", full_name="HR Officer Madatech", employer_id=madatech.id)
    inspector_user = _get_or_create_user(db, username=_safe_username("labor.inspector"), role_code="labor_inspector", full_name="Labor Inspector")
    inspector_supervisor = _get_or_create_user(db, username=_safe_username("labor.inspector.supervisor"), role_code="labor_inspector_supervisor", full_name="Labor Inspector Supervisor")
    _get_or_create_user(db, username=_safe_username("judge.readonly"), role_code="judge_readonly", full_name="Judge Readonly")
    _get_or_create_user(db, username=_safe_username("court.clerk.readonly"), role_code="court_clerk_readonly", full_name="Court Clerk Readonly")
    _get_or_create_user(db, username=_safe_username("auditor.readonly"), role_code="auditor_readonly", full_name="Auditor Readonly")
    delegate_avenir = _get_or_create_user(db, username=_safe_username("staff.delegate.avenir"), role_code="staff_delegate", full_name="Staff Delegate Avenir", employer_id=avenir.id, worker_id=avenir_workers[1].id)
    _get_or_create_user(db, username=_safe_username("works.council.avenir"), role_code="works_council_member", full_name="Works Council Avenir", employer_id=avenir.id, worker_id=avenir_workers[0].id)
    delegate_madatech = _get_or_create_user(db, username=_safe_username("staff.delegate.madatech"), role_code="staff_delegate", full_name="Staff Delegate Madatech", employer_id=madatech.id, worker_id=madatech_workers[1].id)
    _get_or_create_user(db, username=_safe_username("works.council.madatech"), role_code="works_council_member", full_name="Works Council Madatech", employer_id=madatech.id, worker_id=madatech_workers[0].id)

    for worker in all_workers:
        _get_or_create_user(
            db,
            username=worker.email.strip().lower(),
            role_code="employee",
            full_name=f"{worker.prenom} {worker.nom}",
            employer_id=worker.employer_id,
            worker_id=worker.id,
        )

    for employer in (avenir, madatech):
        _get_or_create_assignment(db, employer.id, inspector_user.id, admin_user.id)
        _get_or_create_assignment(db, employer.id, inspector_supervisor.id, admin_user.id)

    today = date.today()
    avenir_worker_user_2 = _get_or_create_user(db, username=avenir_workers[1].email.strip().lower(), role_code="employee", full_name=f"{avenir_workers[1].prenom} {avenir_workers[1].nom}", employer_id=avenir.id, worker_id=avenir_workers[1].id)
    avenir_worker_user_3 = _get_or_create_user(db, username=avenir_workers[2].email.strip().lower(), role_code="employee", full_name=f"{avenir_workers[2].prenom} {avenir_workers[2].nom}", employer_id=avenir.id, worker_id=avenir_workers[2].id)
    madatech_worker_user_3 = _get_or_create_user(db, username=madatech_workers[2].email.strip().lower(), role_code="employee", full_name=f"{madatech_workers[2].prenom} {madatech_workers[2].nom}", employer_id=madatech.id, worker_id=madatech_workers[2].id)

    avenir_active_case = _get_or_create_case(
        db,
        employer=avenir,
        worker=avenir_workers[1],
        filed_by_user=avenir_worker_user_2,
        assigned_inspector_user=inspector_user,
        case_type="individual_dispute",
        sub_type="salary_dispute",
        source_party="employee",
        subject="Reclamation pour rappels d'heures supplementaires AVENIR",
        description="Le travailleur conteste le paiement incomplet d'heures supplementaires et demande une regularisation amiable pendant l'execution du contrat.",
        status="EN_CONCILIATION",
        current_stage="conciliation",
        category="individual_dispute",
        urgency="high",
        received_at=_dt(today - timedelta(days=9), 9),
    )
    _get_or_create_claim(db, case_item=avenir_active_case, created_by_user=hr_officer_avenir, claim_type="salaires_impayes", claimant_party="employee", factual_basis="Regularisation des heures supplementaires de janvier a mars avec rappel de majorations.", amount_requested=450000)
    _get_or_create_event(db, case_item=avenir_active_case, created_by_user=inspector_user, event_type="convocation", title="Convocation 1 AVENIR", description="Premiere convocation des parties pour tentative de conciliation.", status="sent", scheduled_at=_dt(today + timedelta(days=2), 10), completed_at=None, metadata={"attendance": "scheduled"})
    _get_or_create_event(db, case_item=avenir_active_case, created_by_user=inspector_user, event_type="conciliation", title="Seance de conciliation AVENIR", description="Conciliation programmee apres reception des observations employeur.", status="scheduled", scheduled_at=_dt(today + timedelta(days=4), 10), completed_at=None, metadata={"attendance": "scheduled"})

    avenir_non_concil = _get_or_create_case(
        db,
        employer=avenir,
        worker=avenir_workers[2],
        filed_by_user=avenir_worker_user_3,
        assigned_inspector_user=inspector_user,
        case_type="individual_dispute",
        sub_type="disciplinary_dispute",
        source_party="employee",
        subject="Contestations disciplinaires et non-conciliation AVENIR",
        description="Le salarie conteste la procedure disciplinaire et l'absence de communication complete du dossier.",
        status="NON_CONCILIE",
        current_stage="pv",
        category="individual_dispute",
        resolution_type="non_conciliation",
        outcome_summary="Echec total de la conciliation apres expose contradictoire.",
        received_at=_dt(today - timedelta(days=22), 9),
    )
    _get_or_create_claim(db, case_item=avenir_non_concil, created_by_user=delegate_avenir, claim_type="di_rupture_abusive", claimant_party="employee", factual_basis="Le salarie invoque une procedure irreguliere et demande orientation juridictionnelle.", amount_requested=2500000, conciliation_outcome="failed")
    _get_or_create_event(db, case_item=avenir_non_concil, created_by_user=inspector_user, event_type="convocation", title="Convocation 1 non-conciliation AVENIR", description="Premiere convocation executee.", status="completed", scheduled_at=_dt(today - timedelta(days=18), 9), completed_at=_dt(today - timedelta(days=18), 10), metadata={"attendance": "present"})
    _get_or_create_event(db, case_item=avenir_non_concil, created_by_user=inspector_user, event_type="conciliation", title="Conciliation echec AVENIR", description="Les positions sont irreconciliables a ce stade.", status="completed", scheduled_at=_dt(today - timedelta(days=16), 9), completed_at=_dt(today - timedelta(days=16), 11), metadata={"attendance": "present"})
    _get_or_create_pv(
        db,
        case_item=avenir_non_concil,
        generated_by_user=inspector_user,
        pv_type="non_conciliation",
        title="PV de non-conciliation AVENIR",
        content="Proces-verbal de non-conciliation: desaccord maintenu sur la regularite de la procedure disciplinaire et les consequences indemnitaires. Rappel de saisine possible de la juridiction competente.",
        status="issued",
        delivered_to_parties_at=_dt(today - timedelta(days=12), 15),
        metadata={"remedy": "juridiction_competente", "under_contract": True},
    )

    avenir_non_exec = _get_or_create_case(
        db,
        employer=avenir,
        worker=avenir_workers[4],
        filed_by_user=hr_manager_avenir,
        assigned_inspector_user=inspector_supervisor,
        case_type="individual_dispute",
        sub_type="stc_dispute",
        source_party="employee",
        subject="Non-execution d'accord partiel sur STC AVENIR",
        description="L'employeur n'a pas execute integralement les engagements de paiement prevus au PV de conciliation partielle.",
        status="NON_EXECUTE",
        current_stage="execution_followup",
        category="individual_dispute",
        resolution_type="non_execution",
        outcome_summary="Constat de non-execution partielle des engagements de paiement.",
        received_at=_dt(today - timedelta(days=28), 8),
    )
    _get_or_create_event(db, case_item=avenir_non_exec, created_by_user=inspector_supervisor, event_type="conciliation", title="Conciliation partielle STC AVENIR", description="Accord partiel obtenu sur le solde de tout compte.", status="completed", scheduled_at=_dt(today - timedelta(days=25), 10), completed_at=_dt(today - timedelta(days=25), 11), metadata={"attendance": "present"})
    _get_or_create_event(db, case_item=avenir_non_exec, created_by_user=inspector_supervisor, event_type="execution_followup", title="Suivi execution STC AVENIR", description="Constat de non-paiement complet du rappel convenu.", status="completed", scheduled_at=_dt(today - timedelta(days=8), 9), completed_at=_dt(today - timedelta(days=8), 9), metadata={"attendance": "present"})
    _get_or_create_pv(
        db,
        case_item=avenir_non_exec,
        generated_by_user=inspector_supervisor,
        pv_type="non_execution",
        title="PV de non-execution STC AVENIR",
        content="Proces-verbal de non-execution: l'accord partiel de conciliation sur le STC n'a pas ete execute en totalite par l'employeur.",
        status="issued",
        measures_to_execute="Payer le reliquat du STC et remettre les justificatifs de paiement.",
        execution_deadline=_dt(today + timedelta(days=7), 16),
        delivered_to_parties_at=_dt(today - timedelta(days=6), 16),
        metadata={"stc_visibility": "inspection_readonly"},
    )

    avenir_collective = _get_or_create_case(
        db,
        employer=avenir,
        worker=None,
        filed_by_user=delegate_avenir,
        assigned_inspector_user=inspector_supervisor,
        case_type="collective_grievance",
        sub_type="doleance_collective",
        source_party="representative",
        subject="Lettre de doleances collectives AVENIR",
        description="Doleances collectives signees par les representants du personnel sur la charge de travail et l'organisation des astreintes.",
        status="in_review",
        current_stage="collective",
        category="negociation_collective",
        received_at=_dt(today - timedelta(days=5), 9),
    )
    _get_or_create_event(db, case_item=avenir_collective, created_by_user=delegate_avenir, event_type="collective_notice", title="Notification lettre de doleances AVENIR", description="Lettre notifiee a l'employeur avec copie a l'inspection.", status="completed", scheduled_at=_dt(today - timedelta(days=5), 9), completed_at=_dt(today - timedelta(days=5), 9), metadata={"signed_by": ["staff_delegate", "works_council_member"]})
    _get_or_create_event(db, case_item=avenir_collective, created_by_user=employer_admin_avenir, event_type="negotiation_meeting", title="Premiere reunion de negociation AVENIR", description="Premiere reunion programmee apres le delai de six jours ouvrables.", status="scheduled", scheduled_at=_dt(today + timedelta(days=3), 9), completed_at=None, metadata={"legal_delay_working_days": 6})

    avenir_dismissal_case = _get_or_create_case(
        db,
        employer=avenir,
        worker=avenir_workers[3],
        filed_by_user=hr_manager_avenir,
        assigned_inspector_user=inspector_supervisor,
        case_type="disciplinary_case",
        sub_type="dismissal",
        source_party="employer",
        subject="Licenciement disciplinaire AVENIR - Toky",
        description="Procedure de licenciement disciplinaire avec information ecrite des griefs, entretien prealable et conservation des pieces.",
        status="in_review",
        current_stage="instruction",
        category="disciplinary_case",
        received_at=_dt(today - timedelta(days=7), 10),
    )
    _get_or_create_disciplinary_case(
        db,
        employer=avenir,
        worker=avenir_workers[3],
        inspection_case=avenir_dismissal_case,
        created_by_user=hr_manager_avenir,
        subject="Procedure disciplinaire Toky RANDRIANANTOANINA",
        description="Absences injustifiees repetees et refus documente d'instruction interne.",
        hearing_at=_dt(today - timedelta(days=3), 9),
    )
    _get_or_create_termination(
        db,
        employer=avenir,
        worker=avenir_workers[0],
        contract=contracts[0],
        inspection_case=None,
        created_by_user=hr_manager_avenir,
        termination_type="resignation",
        motif="Demission pour convenance personnelle",
        status="notified",
        effective_date=today + timedelta(days=20),
        notification_sent_at=_dt(today - timedelta(days=1), 9),
        notification_received_at=_dt(today - timedelta(days=1), 10),
        preavis_start_date=today - timedelta(days=1),
        inspection_required=False,
        legal_risk_level="low",
        checklist=[{"label": "Lettre de demission motivee", "done": True}, {"label": "Preavis calcule a reception", "done": True}, {"label": "Certificat de travail a preparer", "done": False}],
        documents=["lettre_demission", "preuve_reception", "certificat_travail"],
        legal_metadata={"code_reference": "article_41_43", "certificate_required": True},
        readonly_stc={"status": "draft", "inspection_visibility": "read_only"},
        notes="Attestation provisoire d'emploi a remettre pendant le preavis.",
    )
    _get_or_create_termination(
        db,
        employer=avenir,
        worker=avenir_workers[3],
        contract=contracts[3],
        inspection_case=avenir_dismissal_case,
        created_by_user=hr_manager_avenir,
        termination_type="disciplinary_dismissal",
        motif="Faute lourde alleguee: absences injustifiees et refus d'instruction",
        status="under_review",
        effective_date=today + timedelta(days=1),
        notification_sent_at=_dt(today - timedelta(days=6), 8),
        notification_received_at=_dt(today - timedelta(days=6), 10),
        pre_hearing_notice_sent_at=_dt(today - timedelta(days=6), 8),
        pre_hearing_scheduled_at=_dt(today - timedelta(days=3), 9),
        preavis_start_date=today - timedelta(days=6),
        sensitive_case=True,
        inspection_required=True,
        legal_risk_level="high",
        checklist=[{"label": "Information ecrite prealable des griefs", "done": True}, {"label": "Delai minimum de 3 jours ouvrables avant entretien", "done": True}, {"label": "Assistance par une personne de choix", "done": True}, {"label": "Archivage 5 ans", "done": True}],
        documents=["notification_griefs", "convocation_entretien", "preuve_notification", "lettre_licenciement"],
        legal_metadata={"abusive_risk_indicator": "elevated", "document_retention_years": 5},
        readonly_stc={"status": "prepared", "inspection_comments_allowed": True},
        notes="Verifier le reglement interieur et la preuve de remise ou refus.",
    )

    madatech_case = _get_or_create_case(
        db,
        employer=madatech,
        worker=madatech_workers[2],
        filed_by_user=madatech_worker_user_3,
        assigned_inspector_user=inspector_user,
        case_type="individual_dispute",
        sub_type="inspection_claim",
        source_party="employee",
        subject="Saisine inspection pour STC MADATECH",
        description="Refus partiel de paiement du solde de tout compte apres rupture deja notifiee.",
        status="received",
        current_stage="filing",
        category="individual_dispute",
        urgency="high",
        received_at=_dt(today - timedelta(days=3), 14),
    )
    _get_or_create_claim(db, case_item=madatech_case, created_by_user=delegate_madatech, claim_type="preavis", claimant_party="employee", factual_basis="Paiement du preavis et du reliquat de droits de sortie conteste.", amount_requested=1200000)

    madatech_collective = _get_or_create_case(
        db,
        employer=madatech,
        worker=None,
        filed_by_user=delegate_madatech,
        assigned_inspector_user=inspector_supervisor,
        case_type="collective_grievance",
        sub_type="doleance_collective",
        source_party="representative",
        subject="Lettre de doleances collectives MADATECH",
        description="Lettre de doleances sur l'organisation des rotations et la maintenance preventive.",
        status="in_review",
        current_stage="collective",
        category="negociation_collective",
        received_at=_dt(today - timedelta(days=11), 10),
    )
    _get_or_create_event(db, case_item=madatech_collective, created_by_user=delegate_madatech, event_type="collective_notice", title="Notification lettre de doleances MADATECH", description="Copie transmise a l'inspection.", status="completed", scheduled_at=_dt(today - timedelta(days=11), 10), completed_at=_dt(today - timedelta(days=11), 10), metadata={"signed_by": ["staff_delegate", "works_council_member"]})
    _get_or_create_event(db, case_item=madatech_collective, created_by_user=employer_admin_madatech, event_type="negotiation_meeting", title="Premiere reunion de negociation MADATECH", description="Premiere reunion tenue conformement au circuit collectif.", status="completed", scheduled_at=_dt(today - timedelta(days=3), 9), completed_at=_dt(today - timedelta(days=3), 11), metadata={"legal_delay_working_days": 6})
    _get_or_create_event(db, case_item=madatech_collective, created_by_user=inspector_supervisor, event_type="negotiation_minutes", title="PV de negociation MADATECH", description="Reglement partiel sur les rotations, maintien du desaccord sur l'indemnite de panier.", status="completed", scheduled_at=_dt(today - timedelta(days=3), 11), completed_at=_dt(today - timedelta(days=3), 11), metadata={"outcome": "partial"})

    technical_layoff_case = _get_or_create_case(
        db,
        employer=madatech,
        worker=None,
        filed_by_user=employer_admin_madatech,
        assigned_inspector_user=inspector_user,
        case_type="technical_layoff",
        sub_type="prior_declaration",
        source_party="employer",
        subject="Declaration prealable de chomage technique MADATECH",
        description="Declaration prealable a l'inspection avec motif, duree et liste nominative du personnel touche, information parallele CNaPS.",
        status="in_review",
        current_stage="instruction",
        category="technical_layoff",
        urgency="high",
        received_at=_dt(today - timedelta(days=14), 8),
    )
    _get_or_create_event(db, case_item=technical_layoff_case, created_by_user=inspector_user, event_type="execution_followup", title="Suivi declaration chomage technique MADATECH", description="Suivi des echeances de 3 mois et 6 mois, ordre de priorite et information CNaPS.", status="planned", scheduled_at=_dt(today + timedelta(days=75), 8), completed_at=None, metadata={"cnaps_notified": True, "duration_months": 3, "employees_impacted": [w.matricule for w in madatech_workers[:3]]})

    _get_or_create_termination(
        db,
        employer=madatech,
        worker=madatech_workers[1],
        contract=contracts[6],
        inspection_case=technical_layoff_case,
        created_by_user=hr_manager_madatech,
        termination_type="technical_layoff",
        motif="Baisse d'activite temporaire et panne majeure de ligne d'extrusion",
        status="declared",
        effective_date=today,
        notification_sent_at=_dt(today - timedelta(days=14), 8),
        notification_received_at=_dt(today - timedelta(days=14), 9),
        technical_layoff_declared_at=today - timedelta(days=14),
        technical_layoff_end_at=today + timedelta(days=76),
        inspection_required=True,
        legal_risk_level="medium",
        checklist=[{"label": "Declaration prealable inspection", "done": True}, {"label": "Information CNaPS", "done": True}, {"label": "Alerte 3 mois rupture sans preavis", "done": True}, {"label": "Alerte 6 mois rupture reputee", "done": True}],
        documents=["declaration_chomage_technique", "liste_personnel_touche", "preuve_information_cnaps"],
        legal_metadata={"three_month_alert_at": str(today + timedelta(days=76)), "six_month_alert_at": str(today + timedelta(days=166))},
        readonly_stc={"status": "not_applicable_yet"},
        notes="Le motif doit etre clos des disparition de la cause de suspension.",
    )
    _get_or_create_termination(
        db,
        employer=madatech,
        worker=madatech_workers[4],
        contract=contracts[9],
        inspection_case=None,
        created_by_user=hr_manager_madatech,
        termination_type="economic_dismissal",
        motif="Suppression de poste dans le cadre d'une reorganisation industrielle",
        status="inspection_review",
        effective_date=today + timedelta(days=30),
        notification_sent_at=_dt(today - timedelta(days=8), 10),
        notification_received_at=_dt(today - timedelta(days=8), 11),
        economic_consultation_started_at=today - timedelta(days=12),
        economic_inspection_referral_at=today - timedelta(days=7),
        inspection_required=True,
        legal_risk_level="high",
        checklist=[{"label": "Consultation CE / delegues", "done": True}, {"label": "PV de consultation affiche", "done": True}, {"label": "Avis sous 20 jours", "done": True}, {"label": "Saisine inspection sous pieces", "done": True}, {"label": "Controle ordre de licenciement", "done": True}],
        documents=["pv_consultation_economique", "liste_personnel_touche", "saisine_inspection_economique"],
        legal_metadata={"economic_indemnity_rule": "10_jours_par_annee_complete_plafond_6_mois", "reemployment_priority_tracked": True},
        readonly_stc={"economic_indemnity_estimate": 2416666.67, "inspection_comments_allowed": True},
        notes="PV consultation CE et ordre de licenciement traces dans le workflow.",
    )
    _get_or_create_termination(
        db,
        employer=madatech,
        worker=madatech_workers[3],
        contract=contracts[8],
        inspection_case=None,
        created_by_user=hr_officer_madatech,
        termination_type="mutual_agreement",
        motif="Rupture d'un commun accord formalisee par ecrit",
        status="ready_for_signature",
        effective_date=today + timedelta(days=12),
        notification_sent_at=_dt(today - timedelta(days=2), 15),
        notification_received_at=_dt(today - timedelta(days=2), 15),
        preavis_start_date=today - timedelta(days=2),
        inspection_required=False,
        legal_risk_level="low",
        checklist=[{"label": "Accord ecrit des parties", "done": True}, {"label": "Documents de sortie prepares", "done": True}],
        documents=["accord_rupture_amiable", "certificat_travail", "stc_detail"],
        legal_metadata={"certificate_required": True},
        readonly_stc={"status": "prepared", "inspection_comments_allowed": True},
        notes="STC detaille en lecture seule pour remarques inspection si saisi ulterieurement.",
    )

    avenir_offer_attachment = _ensure_seed_upload(
        "inspection_seed/offres/avenir_assistant_rh.txt",
        "Offre Avenir RH\nDossier de soumission inspection.\nPieces: fiche de poste, grille salariale, circuit de validation.\n",
    )
    madatech_offer_attachment = _ensure_seed_upload(
        "inspection_seed/offres/madatech_chef_atelier.txt",
        "Offre Madatech Production\nDemande de validation inspection avec observations sur les horaires et la classification.\n",
    )

    _get_or_create_job_offer(
        db,
        employer=avenir,
        created_by_user=hr_manager_avenir,
        title="Assistant RH et conformite sociale",
        department="RH",
        location="Ankorondrano",
        contract_type="CDI",
        status="pending_validation",
        salary_range="900000 - 1200000 MGA",
        description="Renforcer le suivi des dossiers salariaux, de la conformite sociale et des pieces destinees a l'inspection du travail.",
        skills_required="droit social, paie, bureautique, redaction administrative",
        workflow_status="pending_validation",
        validation_comment="Soumission initiale en attente d'examen par l'inspection.",
        publication_mode=None,
        publication_url=None,
        desired_start_date=today + timedelta(days=30),
        application_deadline=today + timedelta(days=15),
        submitted_to_inspection_at=_dt(today - timedelta(days=1), 11),
        attachments=[
            {
                "name": "assistant_rh_avenir.txt",
                "path": avenir_offer_attachment["storage_path"],
            }
        ],
    )
    _get_or_create_job_offer(
        db,
        employer=avenir,
        created_by_user=hr_manager_avenir,
        title="Gestionnaire administration du personnel",
        department="RH",
        location="Ankorondrano",
        contract_type="CDI",
        status="published",
        salary_range="1100000 - 1350000 MGA",
        description="Gestion des dossiers du personnel, suivi des contrats, attestations et coordination avec les services paie et inspection.",
        skills_required="administration du personnel, droit du travail, excel, suivi contractuel",
        workflow_status="validated_with_observations",
        validation_comment="Publication autorisee avec rappel sur la mention des horaires et de la classification.",
        publication_mode="site_entreprise",
        publication_url="https://carriere.avenir.example/gestionnaire-administration-personnel",
        desired_start_date=today + timedelta(days=25),
        application_deadline=today + timedelta(days=12),
        submitted_to_inspection_at=_dt(today - timedelta(days=8), 10),
        attachments=[],
        announcement_status="published",
    )
    _get_or_create_job_offer(
        db,
        employer=avenir,
        created_by_user=hr_officer_avenir,
        title="Responsable formation interne",
        department="RH",
        location="Ankorondrano",
        contract_type="CDI",
        status="validated",
        salary_range="1300000 - 1550000 MGA",
        description="Pilotage du plan de formation, suivi des sessions internes et coordination des besoins de montee en competences.",
        skills_required="formation, gestion de projet RH, reporting, coordination",
        workflow_status="validated",
        validation_comment="Offre validee, publication programmee apres finalisation du calendrier.",
        publication_mode="site_entreprise",
        publication_url="https://carriere.avenir.example/responsable-formation-interne",
        desired_start_date=today + timedelta(days=40),
        application_deadline=today + timedelta(days=20),
        submitted_to_inspection_at=_dt(today - timedelta(days=4), 9),
        attachments=[],
        announcement_status="ready",
    )
    _get_or_create_job_offer(
        db,
        employer=madatech,
        created_by_user=hr_manager_madatech,
        title="Chef d'atelier maintenance preventive",
        department="Production",
        location="Tanjombato",
        contract_type="CDI",
        status="needs_correction",
        salary_range="1400000 - 1700000 MGA",
        description="Pilotage d'une equipe de maintenance preventive sur ligne industrielle avec suivi des astreintes et de la securite.",
        skills_required="maintenance industrielle, management, securite, rapports d'intervention",
        workflow_status="needs_correction",
        validation_comment="Preciser l'ordre de priorite, les horaires et la classification pour conformite inspection.",
        publication_mode="external",
        publication_url="https://careers.madatech.example/chef-atelier-maintenance",
        desired_start_date=today + timedelta(days=45),
        application_deadline=today + timedelta(days=18),
        submitted_to_inspection_at=_dt(today - timedelta(days=2), 10),
        attachments=[
            {
                "name": "chef_atelier_madatech.txt",
                "path": madatech_offer_attachment["storage_path"],
            }
        ],
    )
    _get_or_create_job_offer(
        db,
        employer=madatech,
        created_by_user=hr_manager_madatech,
        title="Controleur qualite ligne B",
        department="QHSE",
        location="Tanjombato",
        contract_type="CDI",
        status="published",
        salary_range="950000 - 1150000 MGA",
        description="Suivi qualite en production, controles documentaires, verification des incidents et coordination avec l'inspection en cas d'observation.",
        skills_required="controle qualite, audit, reporting, normes securite",
        workflow_status="validated",
        validation_comment="Fiche validee et publiee.",
        publication_mode="external",
        publication_url="https://careers.madatech.example/controleur-qualite-ligne-b",
        desired_start_date=today + timedelta(days=20),
        application_deadline=today + timedelta(days=10),
        submitted_to_inspection_at=_dt(today - timedelta(days=10), 9),
        attachments=[],
        announcement_status="published",
    )

    _get_or_create_formal_message(
        db,
        sender_user=inspector_user,
        subject="Demande de pieces complementaires - AVENIR heures supplementaires",
        body="Merci de transmettre sous 72h le detail des heures supplementaires, la preuve de notification des convocations et la situation de paie correspondante.",
        message_scope="individual",
        related_entity_type="inspector_case",
        related_entity_id=str(avenir_active_case.id),
        recipients=[
            {"employer_id": avenir.id, "recipient_type": "employer", "status": "sent"},
        ],
        metadata={"case_number": avenir_active_case.case_number, "priority": "high"},
    )
    _get_or_create_formal_message(
        db,
        sender_user=employer_admin_avenir,
        subject="Transmission observations employeur - dossier AVENIR",
        body="L'employeur transmet ses observations, les feuilles de temps et demande confirmation de la date de conciliation.",
        message_scope="individual",
        related_entity_type="inspector_case",
        related_entity_id=str(avenir_active_case.id),
        recipients=[
            {"user_id": inspector_user.id, "recipient_type": "inspector", "status": "read"},
        ],
        metadata={"case_number": avenir_active_case.case_number, "channel": "formal"},
    )
    _get_or_create_formal_message(
        db,
        sender_user=inspector_supervisor,
        subject="Observation inspection - licenciement economique MADATECH",
        body="Veuillez produire le PV de consultation, la liste nominative du personnel touche et les criteres d'ordre de licenciement avant toute suite.",
        message_scope="collective",
        related_entity_type="termination_workflow",
        related_entity_id="economic_dismissal_madatech",
        recipients=[
            {"employer_id": madatech.id, "recipient_type": "employer", "status": "sent"},
        ],
        metadata={"topic": "economic_dismissal", "priority": "high"},
    )
    _get_or_create_formal_message(
        db,
        sender_user=hr_manager_madatech,
        subject="Reponse employeur - chomage technique MADATECH",
        body="Pieces jointes pretes pour la declaration prealable, liste du personnel touchee et preuve d'information CNaPS.",
        message_scope="individual",
        related_entity_type="inspector_case",
        related_entity_id=str(technical_layoff_case.id),
        recipients=[
            {"user_id": inspector_user.id, "recipient_type": "inspector", "status": "sent"},
        ],
        metadata={"case_number": technical_layoff_case.case_number},
    )

    avenir_review = _get_or_create_compliance_review(
        db,
        employer=avenir,
        worker=avenir_workers[3],
        contract=contracts[3],
        created_by_user=hr_manager_avenir,
        reviewed_by_user=inspector_supervisor,
        review_type="disciplinary_case",
        review_stage="inspection_instruction",
        status="submitted",
        source_module="inspection",
        due_at=_dt(today + timedelta(days=5), 16),
        tags=["disciplinary", "inspection", "legal_seed"],
    )
    madatech_review = _get_or_create_compliance_review(
        db,
        employer=madatech,
        worker=madatech_workers[4],
        contract=contracts[9],
        created_by_user=hr_manager_madatech,
        reviewed_by_user=inspector_user,
        review_type="economic_dismissal",
        review_stage="inspection_instruction",
        status="submitted",
        source_module="termination",
        due_at=_dt(today + timedelta(days=7), 15),
        tags=["economic", "inspection", "legal_seed"],
    )
    _get_or_create_observation(
        db,
        review=avenir_review,
        author_user=inspector_supervisor,
        observation_type="procedure",
        status_marker="warning",
        message="Verifier la preuve de remise de la convocation et le respect du delai minimum de trois jours ouvrables avant entretien.",
        structured_payload={"case_number": avenir_dismissal_case.case_number},
    )
    _get_or_create_observation(
        db,
        review=madatech_review,
        author_user=inspector_user,
        observation_type="economic",
        status_marker="action_required",
        message="Le dossier economique doit contenir le PV de consultation et la liste du personnel touche avant avis final de l'inspection.",
        structured_payload={"termination_type": "economic_dismissal"},
    )

    _get_or_create_inspector_message(
        db,
        case_item=avenir_active_case,
        author_user=avenir_worker_user_2,
        sender_role="employee",
        direction="employee_to_inspector",
        message_type="message",
        visibility="case_parties",
        body="Je confirme ma presence a la seance et joins le recapitulatif de mes heures supplementaires.",
    )
    _get_or_create_inspector_message(
        db,
        case_item=avenir_active_case,
        author_user=inspector_user,
        sender_role="inspecteur",
        direction="inspector_to_parties",
        message_type="instruction",
        visibility="case_parties",
        body="Convocation maintenue. Merci aux parties de se presenter avec les bulletins et feuilles de temps des trois derniers mois.",
    )
    _get_or_create_inspector_message(
        db,
        case_item=madatech_case,
        author_user=madatech_worker_user_3,
        sender_role="employee",
        direction="employee_to_inspector",
        message_type="message",
        visibility="case_parties",
        body="Je sollicite la mediation de l'inspection pour le paiement du reliquat de mon solde de tout compte.",
    )
    _get_or_create_inspector_message(
        db,
        case_item=madatech_case,
        author_user=inspector_user,
        sender_role="inspecteur",
        direction="inspector_to_parties",
        message_type="instruction",
        visibility="case_parties",
        body="Le dossier est ouvert. L'employeur est invite a produire le detail du calcul de STC et les preuves de notification.",
    )

    _get_or_create_inspection_document(
        db,
        case_item=avenir_active_case,
        uploaded_by_user=inspector_user,
        document_type="inspection_order",
        title="Convocation inspection AVENIR",
        description="Convocation des parties pour tentative de conciliation.",
        original_name="convocation_avenir.txt",
        body="Convocation inspection AVENIR\nDate: prochaine seance\nObjet: rappels d'heures supplementaires.\n",
        notes="Version initiale seeded pour la GED inspection.",
    )
    _get_or_create_inspection_document(
        db,
        case_item=avenir_non_concil,
        uploaded_by_user=inspector_user,
        document_type="supporting_document",
        title="Pieces disciplinaires AVENIR",
        description="Lot de pieces disciplinaires verse au dossier de non-conciliation.",
        original_name="pieces_disciplinaires_avenir.txt",
        body="Pieces disciplinaires AVENIR\nNotification griefs\nConvocation entretien\nCommentaires employeur\n",
        notes="GED inspection seed.",
    )
    _get_or_create_inspection_document(
        db,
        case_item=technical_layoff_case,
        uploaded_by_user=inspector_user,
        document_type="supporting_document",
        title="Declaration chomage technique MADATECH",
        description="Declaration prealable et liste du personnel touche.",
        original_name="declaration_chomage_technique_madatech.txt",
        body="Declaration prealable MADATECH\nMotif: panne majeure de ligne\nDuree initiale: 3 mois\nPersonnel touche: MDT0001, MDT0002, MDT0003\n",
        notes="Version seed visible dans le module inspection.",
    )

    for case_item in (
        avenir_active_case,
        avenir_non_concil,
        avenir_non_exec,
        avenir_collective,
        avenir_dismissal_case,
        madatech_case,
        madatech_collective,
        technical_layoff_case,
    ):
        _get_or_create_case_assignment(
            db,
            case_item=case_item,
            inspector_user=inspector_user,
            assigned_by_user=admin_user,
            scope="portfolio",
            notes="Visibilite seed inspecteur principal portail inspection.",
        )
        _get_or_create_case_assignment(
            db,
            case_item=case_item,
            inspector_user=inspector_supervisor,
            assigned_by_user=admin_user,
            scope="supervision",
            notes="Visibilite seed supervision inspection.",
        )

    db.flush()
    summary = {
        "employers_seeded": 2,
        "workers_seeded": len(all_workers),
        "contracts_seeded": len(contracts),
        "cases_seeded": db.query(models.InspectorCase).filter(models.InspectorCase.employer_id.in_([avenir.id, madatech.id])).count(),
        "pv_seeded": db.query(models.LabourPV).filter(models.LabourPV.employer_id.in_([avenir.id, madatech.id])).count(),
        "terminations_seeded": db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.employer_id.in_([avenir.id, madatech.id])).count(),
        "job_offers_seeded": db.query(models.RecruitmentJobPosting).filter(models.RecruitmentJobPosting.employer_id.in_([avenir.id, madatech.id])).count(),
        "formal_messages_seeded": db.query(models.LabourFormalMessage).count(),
        "inspection_documents_seeded": db.query(models.InspectionDocument).filter(models.InspectionDocument.employer_id.in_([avenir.id, madatech.id])).count(),
        "observations_seeded": db.query(models.InspectorObservation).filter(models.InspectorObservation.employer_id.in_([avenir.id, madatech.id])).count(),
    }
    record_audit(
        db,
        actor=actor,
        action="system.seed.legal_demo",
        entity_type="legal_seed",
        entity_id="malagasy_labour_2024",
        route="/system-update/seed-legal-demo",
        after=summary,
    )
    db.commit()
    return summary
