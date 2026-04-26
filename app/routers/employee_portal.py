from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config.config import get_db
from ..security import can_access_employer, can_access_worker, get_inspector_assigned_employer_ids, require_roles, user_has_any_role
from ..services.audit_service import record_audit
from ..services.compliance_service import build_employee_flow
from ..services.employee_portal_service import (
    append_history,
    build_portal_dashboard,
    json_dump,
    json_load,
    next_inspector_case_number,
    next_request_number,
    next_sequence,
    pick_auto_assigned_inspector,
)
from ..services.file_storage import sanitize_filename_part, save_upload_file
from ..services.inspection_vault_service import (
    log_inspection_document_access,
    next_inspection_document_version,
    store_inspection_upload,
)
from ..services.pdf_generation_service import build_labour_pv_pdf
from ..services.pdf_generation_service import build_payslip_pdf


router = APIRouter(prefix="/employee-portal", tags=["employee-portal"])

READ_ROLES = (
    "admin",
    "rh",
    "employeur",
    "manager",
    "employe",
    "inspecteur",
    "juridique",
    "direction",
    "audit",
    "judge_readonly",
    "court_clerk_readonly",
)
WRITE_REQUEST_ROLES = ("admin", "rh", "employeur", "manager", "employe")
CASE_MANAGE_ROLES = ("admin", "rh", "inspecteur", "juridique", "direction")
ASSIGNMENT_ROLES = ("admin", "rh", "juridique", "direction")
MESSAGE_WRITE_ROLES = ("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction", "judge_readonly")
DOCUMENT_WRITE_ROLES = ("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction", "court_clerk_readonly")
JUDICIAL_READ_ROLES = ("judge_readonly", "court_clerk_readonly")
EMPLOYEE_WITHDRAW_PENDING_STATUSES = {"received", "submitted", "SOUMIS", "A_QUALIFIER", "EN_ATTENTE_PIECES"}


def _assert_employer_scope(db: Session, user: models.AppUser, employer_id: int) -> None:
    if user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        return
    if can_access_employer(db, user, employer_id):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _assert_worker_scope(db: Session, user: models.AppUser, worker: models.Worker) -> None:
    if user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        return
    if user_has_any_role(db, user, "inspecteur") and can_access_employer(db, user, worker.employer_id):
        return
    if user_has_any_role(db, user, "employeur") and user.employer_id == worker.employer_id:
        return
    if user_has_any_role(db, user, "employe", "manager") and can_access_worker(db, user, worker):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _is_case_assigned_to_inspector(db: Session, case_item: models.InspectorCase, user: models.AppUser) -> bool:
    if case_item.assigned_inspector_user_id == user.id:
        return True
    assignment = (
        db.query(models.InspectorCaseAssignment)
        .filter(
            models.InspectorCaseAssignment.case_id == case_item.id,
            models.InspectorCaseAssignment.inspector_user_id == user.id,
            models.InspectorCaseAssignment.status == "active",
        )
        .first()
    )
    return assignment is not None


def _get_worker_or_404(db: Session, worker_id: int) -> models.Worker:
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


def _get_case_or_404(db: Session, case_id: int) -> models.InspectorCase:
    item = db.query(models.InspectorCase).filter(models.InspectorCase.id == case_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inspector case not found")
    return item


def _get_request_or_404(db: Session, request_id: int) -> models.EmployeePortalRequest:
    item = db.query(models.EmployeePortalRequest).filter(models.EmployeePortalRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portal request not found")
    return item


def _get_document_or_404(db: Session, document_id: int) -> models.InspectionDocument:
    item = db.query(models.InspectionDocument).filter(models.InspectionDocument.id == document_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inspection document not found")
    return item


def _assert_case_scope(db: Session, user: models.AppUser, case_item: models.InspectorCase) -> None:
    if user_has_any_role(db, user, "admin", "rh", "juridique", "direction", "audit"):
        return
    if user_has_any_role(db, user, *JUDICIAL_READ_ROLES):
        if _is_judicial_case_visible(case_item):
            return
        raise HTTPException(status_code=403, detail="Forbidden")
    if user_has_any_role(db, user, "inspecteur"):
        if _is_case_assigned_to_inspector(db, case_item, user):
            return
        if can_access_employer(db, user, case_item.employer_id):
            return
        raise HTTPException(status_code=403, detail="Forbidden")
    if case_item.worker_id:
        worker = _get_worker_or_404(db, case_item.worker_id)
        _assert_worker_scope(db, user, worker)
        return
    _assert_employer_scope(db, user, case_item.employer_id)


def _serialize_user(user: models.AppUser | None) -> Optional[schemas.AppUserLightOut]:
    if not user:
        return None
    return schemas.AppUserLightOut.model_validate(user)


def _normalized_case_status(case_item: models.InspectorCase) -> str:
    return (case_item.status or "").strip().lower()


def _normalized_resolution_type(case_item: models.InspectorCase) -> str:
    return (case_item.resolution_type or "").strip().lower()


def _is_judicial_case_visible(case_item: models.InspectorCase) -> bool:
    status = _normalized_case_status(case_item)
    resolution_type = _normalized_resolution_type(case_item)
    current_stage = (case_item.current_stage or "").strip().lower()
    return (
        bool(case_item.closed_at)
        or status in {"non_concilie", "oriente_juridiction", "cloture", "archive", "closed", "archived", "pv_emis"}
        or resolution_type in {"non_conciliation", "contentieux", "court_referral", "oriente_juridiction"}
        or current_stage in {"judicial", "court", "contentieux"}
    )


def _can_view_pv_records(db: Session, user: models.AppUser) -> bool:
    return not user_has_any_role(db, user, "employe")


def _filter_pv_records_for_user(
    db: Session,
    user: models.AppUser,
    pv_records: list[models.LabourPV],
) -> list[models.LabourPV]:
    if user_has_any_role(db, user, "employe"):
        return []
    if user_has_any_role(db, user, *JUDICIAL_READ_ROLES):
        return [item for item in pv_records if (item.pv_type or "").strip().lower() == "non_conciliation"]
    return pv_records


def _serialize_request(item: models.EmployeePortalRequest) -> schemas.EmployeePortalRequestOut:
    return schemas.EmployeePortalRequestOut(
        id=item.id,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        request_type=item.request_type,
        destination=item.destination,
        title=item.title,
        description=item.description,
        priority=item.priority,
        confidentiality=item.confidentiality,
        attachments=json_load(item.attachments_json, []),
        status=item.status,
        case_number=item.case_number,
        history=json_load(item.history_json, []),
        created_by_user_id=item.created_by_user_id,
        assigned_to_user_id=item.assigned_to_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_case(item: models.InspectorCase) -> schemas.InspectorCaseOut:
    return schemas.InspectorCaseOut(
        id=item.id,
        case_number=item.case_number,
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        contract_id=item.contract_id,
        portal_request_id=item.portal_request_id,
        case_type=item.case_type,
        sub_type=item.sub_type,
        source_party=item.source_party,
        subject=item.subject,
        description=item.description,
        category=item.category,
        district=item.district,
        urgency=item.urgency,
        confidentiality=item.confidentiality,
        amicable_attempt_status=item.amicable_attempt_status,
        current_stage=item.current_stage,
        outcome_summary=item.outcome_summary,
        resolution_type=item.resolution_type,
        due_at=item.due_at,
        received_at=item.received_at,
        is_sensitive=item.is_sensitive,
        attachments=json_load(item.attachments_json, []),
        tags=json_load(item.tags_json, []),
        status=item.status,
        receipt_reference=item.receipt_reference,
        assigned_inspector_user_id=item.assigned_inspector_user_id,
        filed_by_user_id=item.filed_by_user_id,
        last_response_at=item.last_response_at,
        closed_at=item.closed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_message(item: models.InspectorMessage) -> schemas.InspectorMessageOut:
    return schemas.InspectorMessageOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        author_user_id=item.author_user_id,
        sender_role=item.sender_role,
        direction=item.direction,
        message_type=item.message_type,
        visibility=item.visibility,
        body=item.body,
        attachments=json_load(item.attachments_json, []),
        status=item.status,
        created_at=item.created_at,
    )


def _serialize_assignment(item: models.InspectorCaseAssignment) -> schemas.InspectorCaseAssignmentOut:
    return schemas.InspectorCaseAssignmentOut(
        id=item.id,
        case_id=item.case_id,
        inspector_user_id=item.inspector_user_id,
        assigned_by_user_id=item.assigned_by_user_id,
        scope=item.scope,
        status=item.status,
        notes=item.notes,
        assigned_at=item.assigned_at,
        revoked_at=item.revoked_at,
        inspector=_serialize_user(item.inspector),
    )


def _serialize_document_version(item: models.InspectionDocumentVersion) -> schemas.InspectionDocumentVersionOut:
    return schemas.InspectionDocumentVersionOut(
        id=item.id,
        document_id=item.document_id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        version_number=item.version_number,
        file_name=item.file_name,
        original_name=item.original_name,
        storage_path=item.storage_path,
        download_url=item.static_url,
        content_type=item.content_type,
        file_size=item.file_size,
        checksum=item.checksum,
        notes=item.notes,
        uploaded_by_user_id=item.uploaded_by_user_id,
        created_at=item.created_at,
    )


def _serialize_document(item: models.InspectionDocument) -> schemas.InspectionDocumentOut:
    ordered_versions = sorted(item.versions, key=lambda version: version.version_number, reverse=True)
    return schemas.InspectionDocumentOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        uploaded_by_user_id=item.uploaded_by_user_id,
        document_type=item.document_type,
        title=item.title,
        description=item.description,
        visibility=item.visibility,
        confidentiality=item.confidentiality,
        status=item.status,
        current_version_number=item.current_version_number,
        tags=json_load(item.tags_json, []),
        created_at=item.created_at,
        updated_at=item.updated_at,
        versions=[_serialize_document_version(version) for version in ordered_versions],
    )


def _serialize_document_access_log(item: models.InspectionDocumentAccessLog) -> schemas.InspectionDocumentAccessLogOut:
    return schemas.InspectionDocumentAccessLogOut(
        id=item.id,
        document_id=item.document_id,
        version_id=item.version_id,
        case_id=item.case_id,
        user_id=item.user_id,
        action=item.action,
        metadata=json_load(item.metadata_json, {}),
        created_at=item.created_at,
    )


def _serialize_claim(item: models.LabourCaseClaim) -> schemas.LabourCaseClaimOut:
    return schemas.LabourCaseClaimOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        created_by_user_id=item.created_by_user_id,
        claim_type=item.claim_type,
        claimant_party=item.claimant_party,
        factual_basis=item.factual_basis,
        amount_requested=float(item.amount_requested) if item.amount_requested is not None else None,
        status=item.status,
        conciliation_outcome=item.conciliation_outcome,
        inspector_observations=item.inspector_observations,
        metadata=json_load(item.metadata_json, {}),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_event(item: models.LabourCaseEvent) -> schemas.LabourCaseEventOut:
    return schemas.LabourCaseEventOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        created_by_user_id=item.created_by_user_id,
        event_type=item.event_type,
        title=item.title,
        description=item.description,
        status=item.status,
        scheduled_at=item.scheduled_at,
        completed_at=item.completed_at,
        participants=json_load(item.participants_json, []),
        metadata=json_load(item.metadata_json, {}),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_pv(item: models.LabourPV) -> schemas.LabourPVOut:
    return schemas.LabourPVOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        generated_by_user_id=item.generated_by_user_id,
        pv_number=item.pv_number,
        pv_type=item.pv_type,
        title=item.title,
        content=item.content,
        status=item.status,
        version_number=item.version_number,
        measures_to_execute=item.measures_to_execute,
        execution_deadline=item.execution_deadline,
        delivered_to_parties_at=item.delivered_to_parties_at,
        metadata=json_load(item.metadata_json, {}),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _next_labour_pv_number(db: Session, employer_id: int) -> str:
    return next_sequence(
        db,
        model=models.LabourPV,
        field_name="pv_number",
        prefix=f"PV-IT-{employer_id:03d}-{datetime.now(timezone.utc).strftime('%Y%m')}",
    )


def _employment_relationship_active(case_item: models.InspectorCase) -> bool:
    contract = case_item.contract
    if contract is None:
        return case_item.closed_at is None
    contract_status = (getattr(contract, "status", "") or "").strip().lower()
    return contract_status not in {"terminated", "closed", "ended", "resilie", "rompu", "expire"}


def _event_metadata(item: models.LabourCaseEvent) -> dict:
    return json_load(item.metadata_json, {})


def _is_no_show_convocation(item: models.LabourCaseEvent) -> bool:
    metadata = _event_metadata(item)
    attendance = str(metadata.get("attendance") or metadata.get("attendance_status") or "").strip().lower()
    description = (item.description or "").strip().lower()
    return attendance in {
        "no_show",
        "absent",
        "requester_absent",
        "respondent_absent",
        "both_absent",
        "parties_absentes",
        "non_comparution",
    } or "non comparution" in description or "absence" in description


def _build_labour_case_legal_summary(
    case_item: models.InspectorCase,
    events: list[models.LabourCaseEvent],
    pv_records: list[models.LabourPV],
) -> schemas.LabourCaseLegalSummaryOut:
    convocation_events = [item for item in events if (item.event_type or "").strip().lower() == "convocation"]
    no_show_count = sum(1 for item in convocation_events if _is_no_show_convocation(item))
    active_relationship = _employment_relationship_active(case_item)
    requires_inspection_before_court = active_relationship and (case_item.source_party or "").strip().lower() in {"employee", "employe", "employer", "employeur"}

    eligible_pv_types = ["conciliation", "conciliation_partielle", "non_conciliation", "non_execution"]
    if no_show_count >= 3 or len(convocation_events) >= 3:
        eligible_pv_types.append("carence")

    last_delivered = max((item.delivered_to_parties_at for item in pv_records if item.delivered_to_parties_at), default=None)
    received_at = case_item.received_at or case_item.created_at
    pv_due_at = received_at + timedelta(days=30) if received_at else None
    alerts: list[schemas.LabourLegalAlertOut] = []

    if requires_inspection_before_court:
        alerts.append(
            schemas.LabourLegalAlertOut(
                code="inspection_prerequisite",
                severity="info",
                title="Saisine prealable de l'inspection",
                message="Le differend individuel d'un travailleur encore sous contrat doit passer par l'inspection avant la juridiction competente.",
            )
        )
    if pv_due_at and last_delivered is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        alerts.append(
            schemas.LabourLegalAlertOut(
                code="pv_delivery_deadline",
                severity="high" if pv_due_at < now else "medium",
                title="PV a remettre aux parties",
                message="Le proces-verbal doit etre remis a chaque partie dans un delai d'un mois.",
                due_at=pv_due_at,
            )
        )
    if len(convocation_events) >= 2 and no_show_count < 3:
        alerts.append(
            schemas.LabourLegalAlertOut(
                code="convocation_follow_up",
                severity="medium",
                title="Verifier les comparutions",
                message="Tracer les presences et absences avant emission d'un PV de carence.",
            )
        )

    return schemas.LabourCaseLegalSummaryOut(
        requires_inspection_before_court=requires_inspection_before_court,
        employment_relationship_active=active_relationship,
        convocation_count=len(convocation_events),
        no_show_convocation_count=no_show_count,
        pv_due_at=pv_due_at,
        last_pv_delivered_at=last_delivered,
        eligible_pv_types=eligible_pv_types,
        alerts=alerts,
    )


LABOUR_HELP_TOPICS: list[dict] = [
    {
        "code": "plainte_reclamation",
        "title": "Plainte, reclamation et differend individuel",
        "summary": "Qualifier les faits, identifier les parties, demander les pieces utiles et orienter le dossier vers instruction, conciliation ou cloture.",
        "steps": ["Recevoir la saisine", "Qualifier le type de dossier", "Demander les pieces", "Convoquer si necessaire", "Tracer l'issue"],
    },
    {
        "code": "doleance_collective",
        "title": "Doleances collectives",
        "summary": "Suivre la lettre de doleances, les signataires, la negociation, la mediation et l'arbitrage sans melanger le workflow individuel.",
        "steps": ["Enregistrer la notification", "Tracer la premiere reunion", "Produire le PV de negociation", "Basculer en mediation si echec"],
    },
    {
        "code": "conciliation_pv",
        "title": "Conciliation et proces-verbaux",
        "summary": "L'inspecteur assiste la conciliation, consigne les presences, les accords et les desaccords, puis produit un PV versionne.",
        "steps": ["Planifier", "Convoquer", "Constater presence ou carence", "Rediger le PV", "Suivre l'execution"],
    },
    {
        "code": "sanctions_delegues",
        "title": "Sanctions et salaries proteges",
        "summary": "Le portail aide a verifier la procedure, le reglement interieur et le statut protege sans annoncer une annulation automatique.",
        "steps": ["Verifier les pieces", "Analyser la procedure", "Tracer les observations", "Orienter si besoin vers la juridiction"],
    },
    {
        "code": "confidentialite_ged",
        "title": "Confidentialite, GED et audit",
        "summary": "Les pieces sensibles doivent etre classees, versionnees et consultees avec journalisation des acces.",
        "steps": ["Classer le type de piece", "Renseigner la confidentialite", "Limiter les destinataires", "Consulter le journal d'acces"],
    },
]


def _generate_pv_content(case_item: models.InspectorCase, pv_type: str, claims: list[models.LabourCaseClaim]) -> str:
    claim_lines = "\n".join(
        f"- {claim.claim_type}: {claim.factual_basis[:240]}{'...' if len(claim.factual_basis) > 240 else ''}"
        for claim in claims[:8]
    ) or "- Aucune pretention structuree n'a encore ete saisie."
    normalized_pv_type = (pv_type or "").strip().lower()
    legal_reminder = ""
    if normalized_pv_type in {"conciliation_partielle", "non_conciliation", "carence"}:
        legal_reminder = (
            "\n\nSuite juridique:\n"
            "Les parties sont rappelees de la possibilite de saisir la juridiction competente selon l'etat du contrat et l'issue constatee."
        )
    elif normalized_pv_type == "non_execution":
        legal_reminder = (
            "\n\nSuite juridique:\n"
            "Le present PV constate la non-execution des engagements convenus et peut etre verse au dossier de suite contentieuse."
        )
    return (
        f"Proces-verbal {pv_type}\n"
        f"Dossier: {case_item.case_number}\n"
        f"Objet: {case_item.subject}\n"
        f"Type: {case_item.case_type} / {case_item.sub_type or case_item.category or 'non precise'}\n\n"
        f"Faits declares:\n{case_item.description}\n\n"
        f"Pretentions et demandes:\n{claim_lines}\n\n"
        "Constat et observations de l'inspection:\n"
        "A completer par l'inspecteur selon les echanges, les pieces communiquees et la position des parties.\n\n"
        "Note de prudence: ce document structure le dossier et la conciliation. Il ne vaut pas attribution automatique de dommages et interets par le systeme."
        f"{legal_reminder}"
    )


def _assistant_response_for_case(case_item: models.InspectorCase | None, payload: schemas.LabourChatbotRequest) -> dict[str, object]:
    intent = (payload.intent or "general").strip().lower()
    role_context = (payload.role_context or "inspecteur").strip().lower()
    subject = case_item.subject if case_item else "le dossier"
    common_caution = "Assistance administrative uniquement: l'outil ne juge pas, n'attribue pas automatiquement de dommages et interets et ne remplace pas l'inspecteur ni la juridiction competente."

    if role_context == "employe":
        steps = ["Decrire les faits chronologiquement", "Joindre les pieces disponibles", "Preciser la demande", "Suivre les messages et convocations"]
        documents = ["contrat", "bulletins de paie", "courriers", "preuves de paiement ou d'absence", "sanction ecrite si applicable"]
    elif role_context == "employeur":
        steps = ["Repondre factuellement", "Joindre les pieces RH utiles", "Proposer une solution amiable si possible", "Confirmer la convocation"]
        documents = ["contrat", "bulletins", "reglement interieur", "lettres de sanction", "preuves d'execution", "registre ou pointage utile"]
    else:
        steps = ["Qualifier le dossier", "Identifier les pieces manquantes", "Tracer une demande ou convocation", "Preparer la conciliation", "Produire le PV adapte"]
        documents = ["contrat", "bulletins de paie", "pointage", "conges/absences", "sanctions", "reglement interieur", "preuves d'execution"]

    if "sanction" in intent:
        checklist = ["Sanction pecuniaire interdite", "Reglement interieur applicable", "Notification ecrite", "Droit a la defense", "Delais", "Statut protege"]
    elif "doleance" in intent or "collective" in intent:
        checklist = ["Lettre de doleances", "Signataires", "Notification employeur", "Premiere reunion", "PV de negociation", "Mediation/arbitrage si echec"]
    elif "pv" in intent or "conciliation" in intent:
        checklist = ["Presences", "Points discutes", "Accords", "Desaccords", "Mesures a executer", "Date limite d'execution"]
    else:
        checklist = ["Type de dossier", "Parties concernees", "Faits", "Demandes", "Pieces", "Delais", "Confidentialite"]

    return {
        "mode": "fallback_template",
        "role_context": role_context,
        "intent": intent,
        "case_hint": subject,
        "summary": f"Proposition de traitement structure pour {subject}.",
        "next_steps": steps,
        "documents_to_request": documents,
        "checklist": checklist,
        "draft": f"Bonjour, dans le cadre du dossier {case_item.case_number if case_item else ''}, merci de communiquer les pieces utiles et vos observations factuelles.",
        "caution": common_caution,
    }


def _case_related_payload(db: Session, case_item: models.InspectorCase) -> dict[str, object]:
    employer = case_item.employer
    worker = case_item.worker
    contract = case_item.contract
    sanctions = []
    if worker:
        sanctions = (
            db.query(models.DisciplinaryCase)
            .filter(models.DisciplinaryCase.worker_id == worker.id)
            .order_by(models.DisciplinaryCase.updated_at.desc())
            .limit(5)
            .all()
        )
    return {
        "employer": {
            "id": employer.id,
            "raison_sociale": employer.raison_sociale,
            "secteur": employer.activite,
            "adresse": employer.adresse or employer.ville,
        } if employer else None,
        "worker": {
            "id": worker.id,
            "matricule": worker.matricule,
            "nom": worker.nom,
            "prenoms": getattr(worker, "prenoms", None) or getattr(worker, "prenom", None),
            "departement": worker.departement,
            "service": worker.service,
        } if worker else None,
        "contract": {
            "id": contract.id,
            "status": getattr(contract, "status", None),
            "type": getattr(contract, "type_contrat", None),
        } if contract else None,
        "sanctions": [
            {
                "id": item.id,
                "subject": item.subject,
                "status": item.status,
                "sanction_type": item.sanction_type,
                "monetary_sanction_flag": item.monetary_sanction_flag,
            }
            for item in sanctions
        ],
    }


def _default_direction(source_role: str) -> str:
    if source_role == "inspecteur":
        return "inspector_to_employee"
    if source_role == "employeur":
        return "employer_to_inspector"
    if source_role in {"judge_readonly", "court_clerk_readonly"}:
        return "judicial_observation"
    return "employee_to_inspector"


def _effective_sender_role(db: Session, user: models.AppUser) -> str:
    priority = ["inspecteur", "judge_readonly", "court_clerk_readonly", "employeur", "rh", "juridique", "direction", "manager", "employe", "admin"]
    for role_code in priority:
        if user_has_any_role(db, user, role_code):
            return role_code
    return (user.role_code or "employe").strip().lower() or "employe"


def _auto_assign_case_to_inspector(db: Session, case_item: models.InspectorCase) -> None:
    inspector_user = pick_auto_assigned_inspector(db, case_item.employer_id)
    if not inspector_user:
        return

    case_item.assigned_inspector_user_id = inspector_user.id
    assignment = (
        db.query(models.InspectorCaseAssignment)
        .filter(
            models.InspectorCaseAssignment.case_id == case_item.id,
            models.InspectorCaseAssignment.inspector_user_id == inspector_user.id,
        )
        .first()
    )
    if assignment:
        assignment.status = "active"
        assignment.scope = "lead"
        assignment.revoked_at = None
        assignment.notes = "auto_dispatch"
        assignment.assigned_at = datetime.now(timezone.utc)
    else:
        db.add(
            models.InspectorCaseAssignment(
                case_id=case_item.id,
                inspector_user_id=inspector_user.id,
                assigned_by_user_id=None,
                scope="lead",
                status="active",
                notes="auto_dispatch",
            )
        )


def _create_case_opening_message(
    db: Session,
    *,
    case_item: models.InspectorCase,
    user: models.AppUser,
    body: str,
    attachments: list[dict] | list,
    sender_role: str,
) -> None:
    normalized_body = (body or "").strip()
    normalized_attachments = attachments or []
    if not normalized_body and not normalized_attachments:
        return
    db.add(
        models.InspectorMessage(
            case_id=case_item.id,
            employer_id=case_item.employer_id,
            author_user_id=user.id,
            sender_role=sender_role,
            direction=_default_direction(sender_role),
            message_type="opening_statement",
            visibility="case_parties",
            body=normalized_body or "Ouverture du dossier inspection.",
            attachments_json=json_dump(normalized_attachments),
            status="sent",
        )
    )
    case_item.last_response_at = datetime.now(timezone.utc)


@router.get("/inspectors", response_model=list[schemas.AppUserLightOut])
def list_inspectors(
    employer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "juridique", "direction", "audit", "inspecteur")),
):
    if employer_id is not None:
        _assert_employer_scope(db, user, employer_id)
    query = db.query(models.AppUser).filter(models.AppUser.is_active.is_(True))
    if employer_id is not None:
        query = query.filter(
            (models.AppUser.employer_id == employer_id) | (models.AppUser.employer_id.is_(None))
        )
    users = query.order_by(models.AppUser.full_name.asc(), models.AppUser.username.asc()).all()
    return [schemas.AppUserLightOut.model_validate(item) for item in users if user_has_any_role(db, item, "inspecteur")]


@router.get("/dashboard", response_model=schemas.EmployeePortalDashboardOut)
def get_portal_dashboard(
    worker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    target_worker_id = worker_id or user.worker_id
    if not target_worker_id:
        raise HTTPException(status_code=400, detail="worker_id is required for this profile")
    worker = _get_worker_or_404(db, target_worker_id)
    _assert_worker_scope(db, user, worker)
    payload = build_portal_dashboard(db, worker)
    return schemas.EmployeePortalDashboardOut(
        worker=payload["worker"],
        requests=[_serialize_request(item) for item in payload["requests"]],
        inspector_cases=[_serialize_case(item) for item in payload["inspector_cases"]],
        contracts=payload["contracts"],
        performance_reviews=payload["performance_reviews"],
        training_plan_items=payload["training_plan_items"],
        notifications=payload["notifications"],
    )


@router.get("/worker-flow/{worker_id}", response_model=schemas.EmployeeFlowOut)
def get_worker_flow(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    worker = _get_worker_or_404(db, worker_id)
    _assert_worker_scope(db, user, worker)
    return build_employee_flow(db, worker)


@router.get("/me/hr-dossier", response_model=schemas.HrDossierViewOut)
def get_my_hr_dossier(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    if not user.worker_id:
        raise HTTPException(status_code=404, detail="No worker linked to this account")
    worker = _get_worker_or_404(db, user.worker_id)
    _assert_worker_scope(db, user, worker)
    try:
        from ..services.hr_dossier_service import build_hr_dossier_view

        return build_hr_dossier_view(db, worker=worker, user=user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None


@router.get("/me/payslips", response_model=list[schemas.PayrollArchiveOut])
def get_my_payslips(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    if not user.worker_id:
        raise HTTPException(status_code=404, detail="No worker linked to this account")
    worker = _get_worker_or_404(db, user.worker_id)
    _assert_worker_scope(db, user, worker)
    return (
        db.query(models.PayrollArchive)
        .filter(models.PayrollArchive.worker_id == worker.id)
        .order_by(models.PayrollArchive.year.desc(), models.PayrollArchive.month.desc(), models.PayrollArchive.id.desc())
        .all()
    )


@router.get("/me/payslips/{archive_id}/download")
def download_my_payslip(
    archive_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    if not user.worker_id:
        raise HTTPException(status_code=404, detail="No worker linked to this account")
    archive = (
        db.query(models.PayrollArchive)
        .filter(models.PayrollArchive.id == archive_id, models.PayrollArchive.worker_id == user.worker_id)
        .first()
    )
    if not archive:
        raise HTTPException(status_code=404, detail="Payslip archive not found")
    worker = _get_worker_or_404(db, archive.worker_id)
    _assert_worker_scope(db, user, worker)
    preview = {
        "lines": json_load(archive.lines_json, []),
        "totaux": json_load(
            archive.totals_json,
            {
                "brut": archive.brut,
                "cotisations_salariales": archive.cotisations_salariales,
                "cotisations_patronales": archive.cotisations_patronales,
                "irsa": archive.irsa,
                "net": archive.net,
            },
        ),
    }
    worker_name = archive.worker_full_name or f"{worker.prenom or ''} {worker.nom or ''}".strip() or f"Travailleur {worker.id}"
    pdf_bytes = build_payslip_pdf(preview, worker_name, archive.period)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bulletin_{archive.worker_matricule or worker.id}_{archive.period}.pdf"'},
    )


@router.get("/requests", response_model=list[schemas.EmployeePortalRequestOut])
def list_portal_requests(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    destination: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.EmployeePortalRequest)
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.EmployeePortalRequest.worker_id == worker_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.EmployeePortalRequest.worker_id == user.worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.EmployeePortalRequest.employer_id == employer_id)
    elif user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.EmployeePortalRequest.employer_id == user.employer_id)

    if destination:
        query = query.filter(models.EmployeePortalRequest.destination == destination)
    return [_serialize_request(item) for item in query.order_by(models.EmployeePortalRequest.updated_at.desc()).all()]


@router.post("/requests", response_model=schemas.EmployeePortalRequestOut)
def create_portal_request(
    payload: schemas.EmployeePortalRequestCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_REQUEST_ROLES)),
):
    _assert_employer_scope(db, user, payload.employer_id)
    worker = None
    worker_id = payload.worker_id or user.worker_id
    if worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)

    item = models.EmployeePortalRequest(
        employer_id=payload.employer_id,
        worker_id=worker.id if worker else None,
        created_by_user_id=user.id,
        request_type=payload.request_type,
        destination=payload.destination,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        confidentiality=payload.confidentiality,
        case_number=next_request_number(db, payload.employer_id),
        attachments_json=json_dump(payload.attachments),
        history_json=append_history("[]", actor=user, status="submitted", note="Demande creee"),
    )
    db.add(item)
    db.flush()

    if payload.destination == "inspection" or payload.request_type in {"inspection_filing", "inspection_claim"}:
        actor_role = _effective_sender_role(db, user)
        case_item = models.InspectorCase(
            case_number=next_inspector_case_number(db, payload.employer_id),
            employer_id=payload.employer_id,
            worker_id=worker.id if worker else None,
            portal_request_id=item.id,
            filed_by_user_id=user.id,
            case_type="inspection_claim",
            source_party="employee" if actor_role == "employe" else actor_role,
            subject=payload.title,
            description=payload.description,
            category=payload.request_type,
            urgency="high" if payload.priority in {"high", "urgent"} else "normal",
            status="received",
            confidentiality=payload.confidentiality,
            amicable_attempt_status="documented",
            current_stage="filing",
            received_at=datetime.now(timezone.utc),
            is_sensitive=payload.confidentiality in {"restricted", "confidential", "sensitive"},
            attachments_json=json_dump(payload.attachments),
            tags_json=json_dump(["portal_request"]),
        )
        db.add(case_item)
        db.flush()
        _auto_assign_case_to_inspector(db, case_item)
        _create_case_opening_message(
            db,
            case_item=case_item,
            user=user,
            body=payload.description,
            attachments=payload.attachments,
            sender_role=actor_role,
        )

    record_audit(
        db,
        actor=user,
        action="employee_portal.request.create",
        entity_type="employee_portal_request",
        entity_id=item.id,
        route="/employee-portal/requests",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_request(item)


@router.patch("/requests/{request_id}/status", response_model=schemas.EmployeePortalRequestOut)
def update_portal_request_status(
    request_id: int,
    payload: schemas.EmployeePortalRequestStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "manager", "audit")),
):
    item = _get_request_or_404(db, request_id)
    if item.worker_id:
        worker = _get_worker_or_404(db, item.worker_id)
        _assert_worker_scope(db, user, worker)
    else:
        _assert_employer_scope(db, user, item.employer_id)
    before = {"status": item.status}
    item.status = payload.status
    item.history_json = append_history(item.history_json, actor=user, status=payload.status, note=payload.note)
    record_audit(
        db,
        actor=user,
        action="employee_portal.request.status",
        entity_type="employee_portal_request",
        entity_id=item.id,
        route=f"/employee-portal/requests/{request_id}/status",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_request(item)


@router.get("/inspection-cases", response_model=list[schemas.InspectorCaseOut])
def list_inspector_cases(
    employer_id: Optional[int] = Query(None),
    worker_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    confidentiality: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    assigned_inspector_user_id: Optional[int] = Query(None),
    has_documents: Optional[bool] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    query = db.query(models.InspectorCase)
    if user_has_any_role(db, user, *JUDICIAL_READ_ROLES):
        pass
    elif user_has_any_role(db, user, "inspecteur"):
        assigned_case_ids = (
            db.query(models.InspectorCaseAssignment.case_id)
            .filter(
                models.InspectorCaseAssignment.inspector_user_id == user.id,
                models.InspectorCaseAssignment.status == "active",
            )
        )
        visibility_filters = [
            models.InspectorCase.assigned_inspector_user_id == user.id,
            models.InspectorCase.id.in_(assigned_case_ids),
        ]
        query = query.filter(or_(*visibility_filters))
    elif worker_id:
        worker = _get_worker_or_404(db, worker_id)
        _assert_worker_scope(db, user, worker)
        query = query.filter(models.InspectorCase.worker_id == worker_id)
    elif user_has_any_role(db, user, "employe") and user.worker_id:
        query = query.filter(models.InspectorCase.worker_id == user.worker_id)
    elif employer_id:
        _assert_employer_scope(db, user, employer_id)
        query = query.filter(models.InspectorCase.employer_id == employer_id)
    elif user_has_any_role(db, user, "employeur") and user.employer_id:
        query = query.filter(models.InspectorCase.employer_id == user.employer_id)

    if isinstance(employer_id, int) and user_has_any_role(db, user, "inspecteur"):
        query = query.filter(models.InspectorCase.employer_id == employer_id)
    if isinstance(status, str) and status:
        query = query.filter(models.InspectorCase.status == status)
    if isinstance(case_type, str) and case_type:
        query = query.filter(models.InspectorCase.case_type == case_type)
    if isinstance(urgency, str) and urgency:
        query = query.filter(models.InspectorCase.urgency == urgency)
    if isinstance(confidentiality, str) and confidentiality:
        query = query.filter(models.InspectorCase.confidentiality == confidentiality)
    if isinstance(district, str) and district:
        query = query.filter(models.InspectorCase.district.ilike(f"%{district.strip()}%"))
    if isinstance(assigned_inspector_user_id, int):
        query = query.filter(models.InspectorCase.assigned_inspector_user_id == assigned_inspector_user_id)
    if isinstance(has_documents, bool):
        document_case_ids = db.query(models.InspectionDocument.case_id).distinct()
        query = query.filter(models.InspectorCase.id.in_(document_case_ids) if has_documents else ~models.InspectorCase.id.in_(document_case_ids))
    if isinstance(date_from, datetime):
        query = query.filter(models.InspectorCase.created_at >= date_from)
    if isinstance(date_to, datetime):
        query = query.filter(models.InspectorCase.created_at <= date_to)
    items = query.order_by(models.InspectorCase.updated_at.desc()).all()
    if user_has_any_role(db, user, *JUDICIAL_READ_ROLES):
        items = [item for item in items if _is_judicial_case_visible(item)]
    return [_serialize_case(item) for item in items]


@router.post("/inspection-cases", response_model=schemas.InspectorCaseOut)
def create_inspector_case(
    payload: schemas.InspectorCaseCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction")),
):
    _assert_employer_scope(db, user, payload.employer_id)
    worker = None
    if payload.worker_id:
        worker = _get_worker_or_404(db, payload.worker_id)
        _assert_worker_scope(db, user, worker)

    item = models.InspectorCase(
        case_number=next_inspector_case_number(db, payload.employer_id),
        employer_id=payload.employer_id,
        worker_id=payload.worker_id,
        contract_id=payload.contract_id,
        portal_request_id=payload.portal_request_id,
        filed_by_user_id=user.id,
        case_type=payload.case_type,
        sub_type=payload.sub_type,
        source_party=payload.source_party,
        subject=payload.subject,
        description=payload.description,
        category=payload.category,
        district=payload.district,
        urgency=payload.urgency,
        status="received",
        confidentiality=payload.confidentiality,
        amicable_attempt_status=payload.amicable_attempt_status,
        current_stage=payload.current_stage,
        outcome_summary=payload.outcome_summary,
        resolution_type=payload.resolution_type,
        due_at=payload.due_at,
        received_at=payload.received_at or datetime.now(timezone.utc),
        is_sensitive=payload.is_sensitive,
        attachments_json=json_dump(payload.attachments),
        tags_json=json_dump(payload.tags),
    )
    db.add(item)
    db.flush()
    actor_role = _effective_sender_role(db, user)
    _auto_assign_case_to_inspector(db, item)
    _create_case_opening_message(
        db,
        case_item=item,
        user=user,
        body=payload.description,
        attachments=payload.attachments,
        sender_role=actor_role,
    )
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspector_case.create",
        entity_type="inspector_case",
        entity_id=item.id,
        route="/employee-portal/inspection-cases",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_case(item)


@router.post("/inspection-cases/{case_id}/withdraw", response_model=schemas.InspectorCaseOut)
def withdraw_inspector_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("employe")),
):
    item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, item)
    if not user.worker_id or item.worker_id != user.worker_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if item.status not in EMPLOYEE_WITHDRAW_PENDING_STATUSES:
        raise HTTPException(status_code=400, detail="Case can no longer be withdrawn")

    before = {"status": item.status, "current_stage": item.current_stage}
    item.status = "RETIREE"
    item.current_stage = "withdrawn"
    item.closed_at = datetime.now(timezone.utc)
    item.last_response_at = item.closed_at
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspector_case.withdraw",
        entity_type="inspector_case",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/withdraw",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after={"status": item.status, "current_stage": item.current_stage},
    )
    db.commit()
    db.refresh(item)
    return _serialize_case(item)


@router.patch("/inspection-cases/{case_id}/status", response_model=schemas.InspectorCaseOut)
def update_inspector_case_status(
    case_id: int,
    payload: schemas.InspectorCaseStatusUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*CASE_MANAGE_ROLES)),
):
    item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, item)
    before = {
        "status": item.status,
        "current_stage": item.current_stage,
        "outcome_summary": item.outcome_summary,
        "resolution_type": item.resolution_type,
    }
    item.status = payload.status
    if payload.current_stage:
        item.current_stage = payload.current_stage
    if payload.outcome_summary is not None:
        item.outcome_summary = payload.outcome_summary
    if payload.resolution_type is not None:
        item.resolution_type = payload.resolution_type
    if payload.status in {"closed", "archived"}:
        item.closed_at = datetime.now(timezone.utc)
    item.last_response_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspector_case.status",
        entity_type="inspector_case",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/status",
        employer_id=item.employer_id,
        worker_id=item.worker_id,
        before=before,
        after=item,
    )
    db.commit()
    db.refresh(item)
    return _serialize_case(item)


@router.get("/inspection-cases/{case_id}/assignments", response_model=list[schemas.InspectorCaseAssignmentOut])
def list_inspector_case_assignments(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    items = (
        db.query(models.InspectorCaseAssignment)
        .filter(models.InspectorCaseAssignment.case_id == case_id)
        .order_by(models.InspectorCaseAssignment.assigned_at.desc())
        .all()
    )
    return [_serialize_assignment(item) for item in items]


@router.post("/inspection-cases/{case_id}/assignments", response_model=schemas.InspectorCaseAssignmentOut)
def create_inspector_case_assignment(
    case_id: int,
    payload: schemas.InspectorCaseAssignmentCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*ASSIGNMENT_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_employer_scope(db, user, case_item.employer_id)
    inspector_user = db.query(models.AppUser).filter(
        models.AppUser.id == payload.inspector_user_id,
        models.AppUser.is_active.is_(True),
    ).first()
    if inspector_user and not user_has_any_role(db, inspector_user, "inspecteur"):
        inspector_user = None
    if not inspector_user:
        raise HTTPException(status_code=404, detail="Inspector user not found")

    item = (
        db.query(models.InspectorCaseAssignment)
        .filter(
            models.InspectorCaseAssignment.case_id == case_id,
            models.InspectorCaseAssignment.inspector_user_id == payload.inspector_user_id,
        )
        .first()
    )
    if item:
        before = {"status": item.status, "scope": item.scope}
        item.status = "active"
        item.scope = payload.scope
        item.notes = payload.notes
        item.assigned_by_user_id = user.id
        item.assigned_at = datetime.now(timezone.utc)
        item.revoked_at = None
    else:
        before = None
        item = models.InspectorCaseAssignment(
            case_id=case_id,
            inspector_user_id=payload.inspector_user_id,
            assigned_by_user_id=user.id,
            scope=payload.scope,
            status="active",
            notes=payload.notes,
        )
        db.add(item)

    case_item.assigned_inspector_user_id = payload.inspector_user_id
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspector_case.assignment",
        entity_type="inspector_case_assignment",
        entity_id=f"{case_id}:{payload.inspector_user_id}",
        route=f"/employee-portal/inspection-cases/{case_id}/assignments",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        before=before,
        after={"case_id": case_id, "inspector_user_id": payload.inspector_user_id, "scope": payload.scope, "status": "active"},
    )
    db.commit()
    db.refresh(item)
    return _serialize_assignment(item)


@router.patch("/inspection-cases/{case_id}/assignments/{assignment_id}", response_model=schemas.InspectorCaseAssignmentOut)
def update_inspector_case_assignment(
    case_id: int,
    assignment_id: int,
    payload: schemas.InspectorCaseAssignmentUpdate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*ASSIGNMENT_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_employer_scope(db, user, case_item.employer_id)
    item = (
        db.query(models.InspectorCaseAssignment)
        .filter(
            models.InspectorCaseAssignment.id == assignment_id,
            models.InspectorCaseAssignment.case_id == case_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Inspector assignment not found")

    before = {"status": item.status, "notes": item.notes}
    item.status = payload.status
    item.notes = payload.notes
    if payload.status != "active":
        item.revoked_at = datetime.now(timezone.utc)
        if case_item.assigned_inspector_user_id == item.inspector_user_id:
            next_active = (
                db.query(models.InspectorCaseAssignment)
                .filter(
                    models.InspectorCaseAssignment.case_id == case_id,
                    models.InspectorCaseAssignment.status == "active",
                    models.InspectorCaseAssignment.id != item.id,
                )
                .order_by(models.InspectorCaseAssignment.assigned_at.desc())
                .first()
            )
            case_item.assigned_inspector_user_id = next_active.inspector_user_id if next_active else None
    else:
        item.revoked_at = None
        case_item.assigned_inspector_user_id = item.inspector_user_id

    record_audit(
        db,
        actor=user,
        action="employee_portal.inspector_case.assignment.status",
        entity_type="inspector_case_assignment",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/assignments/{assignment_id}",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        before=before,
        after={"status": item.status, "notes": item.notes},
    )
    db.commit()
    db.refresh(item)
    return _serialize_assignment(item)


@router.get("/inspection-cases/{case_id}/messages", response_model=list[schemas.InspectorMessageOut])
def list_inspector_messages(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    items = (
        db.query(models.InspectorMessage)
        .filter(models.InspectorMessage.case_id == case_id)
        .order_by(models.InspectorMessage.created_at.asc())
        .all()
    )
    return [_serialize_message(item) for item in items]


@router.post("/inspection-cases/{case_id}/messages", response_model=schemas.InspectorMessageOut)
def create_inspector_message(
    case_id: int,
    payload: schemas.InspectorMessageCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*MESSAGE_WRITE_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    actor_role = _effective_sender_role(db, user)
    message_visibility = payload.visibility
    message_type = payload.message_type
    if user_has_any_role(db, user, "judge_readonly"):
        message_visibility = "internal"
        message_type = "observation"

    item = models.InspectorMessage(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        author_user_id=user.id,
        sender_role=payload.sender_role or actor_role,
        direction=payload.direction or _default_direction(actor_role),
        message_type=message_type,
        visibility=message_visibility,
        body=payload.body,
        attachments_json=json_dump(payload.attachments),
        status="sent",
    )
    db.add(item)
    case_item.last_response_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspector_message.create",
        entity_type="inspector_message",
        entity_id=f"pending:{case_id}",
        route=f"/employee-portal/inspection-cases/{case_id}/messages",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        after={"message_type": payload.message_type, "direction": payload.direction},
    )
    db.commit()
    db.refresh(item)
    return _serialize_message(item)


@router.post("/inspection-cases/{case_id}/messages/upload", response_model=schemas.InspectorMessageOut)
async def create_inspector_message_upload(
    case_id: int,
    body: str = Form(...),
    sender_role: str = Form("employee"),
    direction: str = Form("employee_to_inspector"),
    message_type: str = Form("message"),
    visibility: str = Form("case_parties"),
    attachments: Optional[list[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction")),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    actor_role = _effective_sender_role(db, user)

    uploaded_attachments = []
    for attachment in attachments or []:
        safe_name = sanitize_filename_part(Path(attachment.filename or "piece_jointe").name)
        storage_name = (
            f"inspection_cases/{case_item.case_number}/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{safe_name}"
        )
        save_upload_file(attachment.file, filename=storage_name)
        uploaded_attachments.append(
            {
                "name": attachment.filename,
                "content_type": attachment.content_type,
                "path": storage_name,
            }
        )

    item = models.InspectorMessage(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        author_user_id=user.id,
        sender_role=sender_role or actor_role,
        direction=direction or _default_direction(actor_role),
        message_type=message_type,
        visibility=visibility,
        body=body,
        attachments_json=json_dump(uploaded_attachments),
        status="sent",
    )
    db.add(item)
    case_item.last_response_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _serialize_message(item)


@router.get("/inspection-cases/{case_id}/documents", response_model=list[schemas.InspectionDocumentOut])
def list_inspection_documents(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    items = (
        db.query(models.InspectionDocument)
        .filter(models.InspectionDocument.case_id == case_id)
        .order_by(models.InspectionDocument.updated_at.desc())
        .all()
    )
    return [_serialize_document(item) for item in items]


@router.post("/inspection-cases/{case_id}/documents/upload", response_model=schemas.InspectionDocumentOut)
async def create_inspection_document(
    case_id: int,
    title: str = Form(...),
    document_type: str = Form("supporting_document"),
    description: str = Form(""),
    visibility: str = Form("case_parties"),
    confidentiality: str = Form("restricted"),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*DOCUMENT_WRITE_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)

    document = models.InspectionDocument(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        uploaded_by_user_id=user.id,
        document_type=document_type,
        title=title,
        description=description or None,
        visibility=visibility,
        confidentiality=confidentiality,
        status="active",
        current_version_number=0,
        tags_json=json_dump([]),
    )
    db.add(document)
    db.flush()

    version_number = next_inspection_document_version(db, document.id)
    stored = store_inspection_upload(upload=file, case_number=case_item.case_number, document_id=document.id, version_number=version_number)
    version = models.InspectionDocumentVersion(
        document_id=document.id,
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        uploaded_by_user_id=user.id,
        version_number=version_number,
        file_name=stored["file_name"],
        original_name=stored["original_name"],
        storage_path=stored["storage_path"],
        static_url=stored["static_url"],
        content_type=stored["content_type"],
        file_size=stored["file_size"],
        checksum=stored["checksum"],
        notes=notes or None,
    )
    document.current_version_number = version_number
    db.add(version)
    log_inspection_document_access(
        db,
        document=document,
        user=user,
        action="upload",
        metadata={"version_number": version_number, "document_type": document_type},
    )
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspection_document.create",
        entity_type="inspection_document",
        entity_id=document.id,
        route=f"/employee-portal/inspection-cases/{case_id}/documents/upload",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        after={"title": title, "document_type": document_type, "version_number": version_number},
    )
    db.commit()
    db.refresh(document)
    return _serialize_document(document)


@router.post("/inspection-documents/{document_id}/versions/upload", response_model=schemas.InspectionDocumentOut)
async def add_inspection_document_version(
    document_id: int,
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*DOCUMENT_WRITE_ROLES)),
):
    document = _get_document_or_404(db, document_id)
    case_item = _get_case_or_404(db, document.case_id)
    _assert_case_scope(db, user, case_item)

    version_number = next_inspection_document_version(db, document.id)
    stored = store_inspection_upload(upload=file, case_number=case_item.case_number, document_id=document.id, version_number=version_number)
    version = models.InspectionDocumentVersion(
        document_id=document.id,
        case_id=document.case_id,
        employer_id=document.employer_id,
        uploaded_by_user_id=user.id,
        version_number=version_number,
        file_name=stored["file_name"],
        original_name=stored["original_name"],
        storage_path=stored["storage_path"],
        static_url=stored["static_url"],
        content_type=stored["content_type"],
        file_size=stored["file_size"],
        checksum=stored["checksum"],
        notes=notes or None,
    )
    document.current_version_number = version_number
    document.updated_at = datetime.now(timezone.utc)
    db.add(version)
    db.flush()
    log_inspection_document_access(
        db,
        document=document,
        user=user,
        action="upload_version",
        version_id=version.id,
        metadata={"version_number": version_number},
    )
    record_audit(
        db,
        actor=user,
        action="employee_portal.inspection_document.version",
        entity_type="inspection_document",
        entity_id=document.id,
        route=f"/employee-portal/inspection-documents/{document_id}/versions/upload",
        employer_id=document.employer_id,
        worker_id=case_item.worker_id,
        after={"version_number": version_number},
    )
    db.commit()
    db.refresh(document)
    return _serialize_document(document)


@router.get("/inspection-documents/{document_id}", response_model=schemas.InspectionDocumentOut)
def get_inspection_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    document = _get_document_or_404(db, document_id)
    case_item = _get_case_or_404(db, document.case_id)
    _assert_case_scope(db, user, case_item)
    latest_version = max(document.versions, key=lambda item: item.version_number, default=None)
    log_inspection_document_access(
        db,
        document=document,
        user=user,
        action="view",
        version_id=latest_version.id if latest_version else None,
    )
    db.commit()
    return _serialize_document(document)


@router.get("/inspection-documents/{document_id}/access-logs", response_model=list[schemas.InspectionDocumentAccessLogOut])
def list_inspection_document_access_logs(
    document_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "inspecteur", "juridique", "direction", "audit")),
):
    document = _get_document_or_404(db, document_id)
    case_item = _get_case_or_404(db, document.case_id)
    _assert_case_scope(db, user, case_item)
    items = (
        db.query(models.InspectionDocumentAccessLog)
        .filter(models.InspectionDocumentAccessLog.document_id == document_id)
        .order_by(models.InspectionDocumentAccessLog.created_at.desc())
        .all()
    )
    return [_serialize_document_access_log(item) for item in items]


@router.get("/inspection-help")
def list_inspection_help(
    role_context: Optional[str] = Query(None),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    return {
        "role_context": role_context or user.role_code,
        "topics": LABOUR_HELP_TOPICS,
        "principles": [
            "Le systeme assiste et trace, il ne juge pas a la place de l'inspecteur ou du tribunal.",
            "Les dommages et interets sont des pretentions ou objets de conciliation, pas une attribution automatique.",
            "Les dossiers sensibles doivent rester cloisonnes et les pieces doivent etre classees en GED inspection.",
        ],
    }


@router.get("/inspection-cases/{case_id}/workspace", response_model=schemas.LabourCaseWorkspaceOut)
def get_inspection_case_workspace(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    claims = (
        db.query(models.LabourCaseClaim)
        .filter(models.LabourCaseClaim.case_id == case_id)
        .order_by(models.LabourCaseClaim.updated_at.desc())
        .all()
    )
    events = (
        db.query(models.LabourCaseEvent)
        .filter(models.LabourCaseEvent.case_id == case_id)
        .order_by(models.LabourCaseEvent.scheduled_at.asc().nullslast(), models.LabourCaseEvent.created_at.asc())
        .all()
    )
    pv_records = (
        db.query(models.LabourPV)
        .filter(models.LabourPV.case_id == case_id)
        .order_by(models.LabourPV.updated_at.desc())
        .all()
    )
    messages = (
        db.query(models.InspectorMessage)
        .filter(models.InspectorMessage.case_id == case_id)
        .order_by(models.InspectorMessage.created_at.asc())
        .all()
    )
    documents = (
        db.query(models.InspectionDocument)
        .filter(models.InspectionDocument.case_id == case_id)
        .order_by(models.InspectionDocument.updated_at.desc())
        .all()
    )
    document_ids = [item.id for item in documents]
    access_logs = []
    if document_ids:
        access_logs = (
            db.query(models.InspectionDocumentAccessLog)
            .filter(models.InspectionDocumentAccessLog.document_id.in_(document_ids))
            .order_by(models.InspectionDocumentAccessLog.created_at.desc())
            .limit(30)
            .all()
        )
    visible_pv_records = _filter_pv_records_for_user(db, user, pv_records)
    legal_summary = _build_labour_case_legal_summary(case_item, events, pv_records)
    return schemas.LabourCaseWorkspaceOut(
        case=_serialize_case(case_item),
        claims=[_serialize_claim(item) for item in claims],
        events=[_serialize_event(item) for item in events],
        pv_records=[_serialize_pv(item) for item in visible_pv_records],
        messages=[_serialize_message(item) for item in messages],
        documents=[_serialize_document(item) for item in documents],
        document_access_logs=[_serialize_document_access_log(item) for item in access_logs],
        related=_case_related_payload(db, case_item),
        help_topics=LABOUR_HELP_TOPICS,
        legal_summary=legal_summary,
    )


@router.get("/inspection-cases/{case_id}/claims", response_model=list[schemas.LabourCaseClaimOut])
def list_labour_case_claims(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    items = (
        db.query(models.LabourCaseClaim)
        .filter(models.LabourCaseClaim.case_id == case_id)
        .order_by(models.LabourCaseClaim.updated_at.desc())
        .all()
    )
    return [_serialize_claim(item) for item in items]


@router.post("/inspection-cases/{case_id}/claims", response_model=schemas.LabourCaseClaimOut)
def create_labour_case_claim(
    case_id: int,
    payload: schemas.LabourCaseClaimCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction")),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    item = models.LabourCaseClaim(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        created_by_user_id=user.id,
        claim_type=payload.claim_type,
        claimant_party=payload.claimant_party,
        factual_basis=payload.factual_basis,
        amount_requested=payload.amount_requested,
        status=payload.status,
        conciliation_outcome=payload.conciliation_outcome,
        inspector_observations=payload.inspector_observations,
        metadata_json=json_dump(payload.metadata),
    )
    db.add(item)
    db.flush()
    case_item.last_response_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=user,
        action="employee_portal.labour_case_claim.create",
        entity_type="labour_case_claim",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/claims",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        after={"claim_type": payload.claim_type, "claimant_party": payload.claimant_party, "amount_requested": payload.amount_requested},
    )
    db.commit()
    db.refresh(item)
    return _serialize_claim(item)


@router.get("/inspection-cases/{case_id}/events", response_model=list[schemas.LabourCaseEventOut])
def list_labour_case_events(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    items = (
        db.query(models.LabourCaseEvent)
        .filter(models.LabourCaseEvent.case_id == case_id)
        .order_by(models.LabourCaseEvent.scheduled_at.asc().nullslast(), models.LabourCaseEvent.created_at.asc())
        .all()
    )
    return [_serialize_event(item) for item in items]


@router.post("/inspection-cases/{case_id}/events", response_model=schemas.LabourCaseEventOut)
def create_labour_case_event(
    case_id: int,
    payload: schemas.LabourCaseEventCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction")),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    event_type = payload.event_type.strip().lower()
    item = models.LabourCaseEvent(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        created_by_user_id=user.id,
        event_type=event_type,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
        completed_at=payload.completed_at,
        participants_json=json_dump(payload.participants),
        metadata_json=json_dump(payload.metadata),
    )
    db.add(item)
    db.flush()
    if event_type in {"conciliation", "convocation"} and case_item.status in {"received", "in_review", "A_QUALIFIER", "EN_ATTENTE_PIECES"}:
        case_item.status = "EN_CONCILIATION" if event_type == "conciliation" else "EN_ATTENTE_EMPLOYEUR"
        case_item.current_stage = event_type
    case_item.last_response_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=user,
        action="employee_portal.labour_case_event.create",
        entity_type="labour_case_event",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/events",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        after={"event_type": event_type, "status": payload.status, "scheduled_at": payload.scheduled_at},
    )
    db.commit()
    db.refresh(item)
    return _serialize_event(item)


@router.get("/inspection-cases/{case_id}/pv", response_model=list[schemas.LabourPVOut])
def list_labour_case_pv(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    if not _can_view_pv_records(db, user):
        raise HTTPException(status_code=403, detail="Forbidden")
    items = (
        db.query(models.LabourPV)
        .filter(models.LabourPV.case_id == case_id)
        .order_by(models.LabourPV.updated_at.desc())
        .all()
    )
    items = _filter_pv_records_for_user(db, user, items)
    return [_serialize_pv(item) for item in items]


@router.post("/inspection-cases/{case_id}/pv", response_model=schemas.LabourPVOut)
def create_labour_case_pv(
    case_id: int,
    payload: schemas.LabourPVCreate,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "inspecteur", "juridique", "direction")),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    events = (
        db.query(models.LabourCaseEvent)
        .filter(models.LabourCaseEvent.case_id == case_id)
        .order_by(models.LabourCaseEvent.scheduled_at.asc().nullslast(), models.LabourCaseEvent.created_at.asc())
        .all()
    )
    existing_pv_records = (
        db.query(models.LabourPV)
        .filter(models.LabourPV.case_id == case_id)
        .order_by(models.LabourPV.updated_at.desc())
        .all()
    )
    legal_summary = _build_labour_case_legal_summary(case_item, events, existing_pv_records)
    normalized_pv_type = (payload.pv_type or "").strip().lower()
    if normalized_pv_type not in legal_summary.eligible_pv_types:
        raise HTTPException(
            status_code=400,
            detail=f"PV type '{normalized_pv_type}' is not yet eligible for this case chronology",
        )
    claims = (
        db.query(models.LabourCaseClaim)
        .filter(models.LabourCaseClaim.case_id == case_id)
        .order_by(models.LabourCaseClaim.created_at.asc())
        .all()
    )
    last_version = (
        db.query(models.LabourPV.version_number)
        .filter(models.LabourPV.case_id == case_id, models.LabourPV.pv_type == payload.pv_type)
        .order_by(models.LabourPV.version_number.desc())
        .first()
    )
    version_number = (last_version[0] + 1) if last_version else 1
    title = payload.title or f"PV {normalized_pv_type} - {case_item.case_number}"
    delivered_to_parties_at = payload.delivered_to_parties_at
    if payload.status in {"issued", "PV_EMIS", "sent"} and delivered_to_parties_at is None:
        delivered_to_parties_at = datetime.now(timezone.utc)
    item = models.LabourPV(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        generated_by_user_id=user.id,
        pv_number=_next_labour_pv_number(db, case_item.employer_id),
        pv_type=normalized_pv_type,
        title=title,
        content=payload.content or _generate_pv_content(case_item, normalized_pv_type, claims),
        status=payload.status,
        version_number=version_number,
        measures_to_execute=payload.measures_to_execute,
        execution_deadline=payload.execution_deadline,
        delivered_to_parties_at=delivered_to_parties_at,
        metadata_json=json_dump(
            {
                **payload.metadata,
                "legal_summary": legal_summary.model_dump(mode="json"),
            }
        ),
    )
    db.add(item)
    db.flush()
    case_item.status = "PV_EMIS" if payload.status in {"issued", "PV_EMIS", "sent"} else "PV_A_EMETTRE"
    case_item.current_stage = "pv"
    case_item.last_response_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=user,
        action="employee_portal.labour_pv.create",
        entity_type="labour_pv",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/pv",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        after={"pv_type": normalized_pv_type, "status": payload.status, "version_number": version_number},
    )
    db.commit()
    db.refresh(item)
    return _serialize_pv(item)


@router.get("/inspection-cases/{case_id}/pv/{pv_id}/download")
def download_labour_case_pv(
    case_id: int,
    pv_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_ROLES)),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    if not _can_view_pv_records(db, user):
        raise HTTPException(status_code=403, detail="Forbidden")
    pv_item = (
        db.query(models.LabourPV)
        .filter(models.LabourPV.id == pv_id, models.LabourPV.case_id == case_id)
        .first()
    )
    if not pv_item:
        raise HTTPException(status_code=404, detail="PV not found")
    if pv_item not in _filter_pv_records_for_user(db, user, [pv_item]):
        raise HTTPException(status_code=403, detail="Forbidden")
    employer_name = case_item.employer.raison_sociale if case_item.employer else f"Employeur {case_item.employer_id}"
    worker_name = None
    if case_item.worker:
        worker_name = " ".join(part for part in [case_item.worker.prenom, case_item.worker.nom] if part).strip() or case_item.worker.matricule
    delivered_at = pv_item.delivered_to_parties_at.isoformat() if pv_item.delivered_to_parties_at else None
    pdf_bytes = build_labour_pv_pdf(
        pv_number=pv_item.pv_number,
        title=pv_item.title,
        content=pv_item.content,
        case_number=case_item.case_number,
        employer_name=employer_name,
        worker_name=worker_name,
        delivered_at=delivered_at,
    )
    filename = f"{pv_item.pv_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/inspection-cases/{case_id}/assistant", response_model=schemas.LabourChatbotOut)
def run_labour_case_assistant(
    case_id: int,
    payload: schemas.LabourChatbotRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin", "rh", "employeur", "employe", "inspecteur", "juridique", "direction")),
):
    case_item = _get_case_or_404(db, case_id)
    _assert_case_scope(db, user, case_item)
    response_payload = _assistant_response_for_case(case_item if payload.include_case_summary else None, payload)
    item = models.LabourChatbotLog(
        case_id=case_item.id,
        employer_id=case_item.employer_id,
        created_by_user_id=user.id,
        role_context=payload.role_context,
        intent=payload.intent,
        prompt_excerpt=payload.prompt[:500],
        response_json=json_dump(response_payload),
        fallback_used=True,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor=user,
        action="employee_portal.labour_assistant.fallback",
        entity_type="labour_chatbot_log",
        entity_id=item.id,
        route=f"/employee-portal/inspection-cases/{case_id}/assistant",
        employer_id=case_item.employer_id,
        worker_id=case_item.worker_id,
        after={"role_context": payload.role_context, "intent": payload.intent, "fallback_used": True},
    )
    db.commit()
    db.refresh(item)
    return schemas.LabourChatbotOut(
        id=item.id,
        case_id=item.case_id,
        employer_id=item.employer_id,
        role_context=item.role_context,
        intent=item.intent,
        response=json_load(item.response_json, {}),
        fallback_used=item.fallback_used,
        created_at=item.created_at,
    )


