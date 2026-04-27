from datetime import datetime, timezone
import logging
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..config.config import get_db
from .. import models, schemas
from ..security import (
    READ_PAYROLL_ROLES,
    WRITE_RH_ROLES,
    can_access_worker,
    can_manage_worker,
    get_user_active_role_codes,
    get_inspector_assigned_employer_ids,
    get_current_user,
    get_user_effective_base_roles,
    require_roles,
)
from ..services.audit_service import record_audit
from ..services.master_data_service import sync_worker_master_data
from ..services.organizational_filters import apply_worker_hierarchy_filters
from ..services.organizational_service import OrganizationalService

router = APIRouter(prefix="/workers", tags=["workers"])
logger = logging.getLogger(__name__)

from typing import Optional

from sqlalchemy import or_, func


def _apply_worker_search(query, q: Optional[str]):
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            or_(
                models.Worker.matricule.ilike(search_filter),
                models.Worker.nom.ilike(search_filter),
                models.Worker.prenom.ilike(search_filter),
                func.concat(models.Worker.nom, ' ', models.Worker.prenom).ilike(search_filter),
                func.concat(models.Worker.prenom, ' ', models.Worker.nom).ilike(search_filter)
            )
        )
    return query


def _apply_worker_scope(query, db: Session, user: models.AppUser):
    effective_roles = get_user_effective_base_roles(db, user)
    if effective_roles.intersection({"admin", "rh", "comptable", "audit"}):
        return query
    if "inspecteur" in effective_roles:
        employer_ids = get_inspector_assigned_employer_ids(db, user)
        if employer_ids:
            return query.filter(models.Worker.employer_id.in_(sorted(employer_ids)))
    if effective_roles.intersection({"employeur", "direction", "juridique", "recrutement"}) and user.employer_id:
        return query.filter(models.Worker.employer_id == user.employer_id)
    if "employe" in effective_roles and user.worker_id:
        return query.filter(models.Worker.id == user.worker_id)
    if effective_roles.intersection({"manager", "departement"}) and user.worker_id:
        manager_worker = db.query(models.Worker).filter(models.Worker.id == user.worker_id).first()
        if manager_worker and manager_worker.organizational_unit_id:
            return query.filter(models.Worker.organizational_unit_id == manager_worker.organizational_unit_id)
    return query.filter(models.Worker.id == -1)


def _ensure_admin(user: models.AppUser, db: Session) -> None:
    if "admin" not in get_user_effective_base_roles(db, user):
        raise HTTPException(status_code=403, detail="Action réservée à l'administrateur")


def _ensure_worker_delete_role(user: models.AppUser, db: Session) -> None:
    allowed_roles = {"drh", "rh"}
    active_roles = {role.strip().lower() for role in get_user_active_role_codes(db, user)}
    primary_role = (user.role_code or "").strip().lower()
    if primary_role:
        active_roles.add(primary_role)
    if not active_roles.intersection(allowed_roles):
        raise HTTPException(status_code=403, detail="Suppression autorisée uniquement pour DRH et Gestionnaire RH.")


def _soft_delete_worker(db: Session, worker: models.Worker, user: models.AppUser) -> None:
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    worker.is_active = False
    worker.deleted_at = timestamp
    worker.deleted_by_user_id = user.id if user else None
    linked_users = db.query(models.AppUser).filter(models.AppUser.worker_id == worker.id).all()
    for linked_user in linked_users:
        linked_user.is_active = False
    db.query(models.AuthSession).filter(
        models.AuthSession.user_id.in_([item.id for item in linked_users])
    ).update({"revoked_at": timestamp}, synchronize_session=False)


def _purge_worker_dependencies(db: Session, worker_ids: list[int]) -> None:
    if not worker_ids:
        return

    contract_ids = [
        item[0]
        for item in db.query(models.CustomContract.id).filter(models.CustomContract.worker_id.in_(worker_ids)).all()
    ]
    contract_version_ids = [
        item[0]
        for item in db.query(models.ContractVersion.id).filter(models.ContractVersion.worker_id.in_(worker_ids)).all()
    ]
    portal_request_ids = [
        item[0]
        for item in db.query(models.EmployeePortalRequest.id).filter(models.EmployeePortalRequest.worker_id.in_(worker_ids)).all()
    ]
    leave_request_ids = [
        item[0]
        for item in db.query(models.LeaveRequest.id).filter(models.LeaveRequest.worker_id.in_(worker_ids)).all()
    ]
    training_need_ids = [
        item[0]
        for item in db.query(models.TrainingNeed.id).filter(models.TrainingNeed.worker_id.in_(worker_ids)).all()
    ]
    inspector_case_ids = {
        item[0]
        for item in db.query(models.InspectorCase.id).filter(models.InspectorCase.worker_id.in_(worker_ids)).all()
    }
    if portal_request_ids:
        inspector_case_ids.update(
            item[0]
            for item in db.query(models.InspectorCase.id).filter(models.InspectorCase.portal_request_id.in_(portal_request_ids)).all()
        )
    if contract_ids:
        inspector_case_ids.update(
            item[0]
            for item in db.query(models.InspectorCase.id).filter(models.InspectorCase.contract_id.in_(contract_ids)).all()
        )

    db.query(models.IamUserRole).filter(models.IamUserRole.worker_id.in_(worker_ids)).update(
        {"worker_id": None, "is_active": False}, synchronize_session=False
    )
    linked_user_ids = [
        item[0]
        for item in db.query(models.AppUser.id).filter(models.AppUser.worker_id.in_(worker_ids)).all()
    ]
    if linked_user_ids:
        db.query(models.AuthSession).filter(models.AuthSession.user_id.in_(linked_user_ids)).delete(synchronize_session=False)
        db.query(models.AppUser).filter(models.AppUser.id.in_(linked_user_ids)).update(
            {"worker_id": None, "is_active": False}, synchronize_session=False
        )

    if leave_request_ids:
        db.query(models.AttendanceLeaveReconciliation).filter(
            models.AttendanceLeaveReconciliation.leave_request_id.in_(leave_request_ids)
        ).delete(synchronize_session=False)
        db.query(models.LeaveRequestHistory).filter(
            models.LeaveRequestHistory.leave_request_id.in_(leave_request_ids)
        ).delete(synchronize_session=False)
        db.query(models.LeaveRequestApproval).filter(
            models.LeaveRequestApproval.leave_request_id.in_(leave_request_ids)
        ).delete(synchronize_session=False)
        db.query(models.LeaveRequest).filter(models.LeaveRequest.id.in_(leave_request_ids)).delete(synchronize_session=False)

    if inspector_case_ids:
        db.query(models.TerminationWorkflow).filter(
            models.TerminationWorkflow.inspection_case_id.in_(inspector_case_ids)
        ).delete(synchronize_session=False)
        db.query(models.DisciplinaryCase).filter(
            models.DisciplinaryCase.inspection_case_id.in_(inspector_case_ids)
        ).delete(synchronize_session=False)

    if portal_request_ids:
        db.query(models.InspectorCase).filter(models.InspectorCase.portal_request_id.in_(portal_request_ids)).delete(synchronize_session=False)
    db.query(models.EmployeePortalRequest).filter(models.EmployeePortalRequest.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.LeavePlanningProposal).filter(models.LeavePlanningProposal.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.InspectorCase).filter(models.InspectorCase.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.ComplianceReview).filter(models.ComplianceReview.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.DisciplinaryCase).filter(models.DisciplinaryCase.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.TrainingEvaluation).filter(models.TrainingEvaluation.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.TrainingPlanItem).filter(models.TrainingPlanItem.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    if training_need_ids:
        db.query(models.TrainingPlanItem).filter(models.TrainingPlanItem.need_id.in_(training_need_ids)).delete(synchronize_session=False)
    db.query(models.TrainingNeed).filter(models.TrainingNeed.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.PerformanceReview).filter(models.PerformanceReview.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.TalentEmployeeSkill).filter(models.TalentEmployeeSkill.worker_id.in_(worker_ids)).delete(synchronize_session=False)

    if contract_version_ids:
        db.query(models.ComplianceReview).filter(models.ComplianceReview.contract_version_id.in_(contract_version_ids)).delete(synchronize_session=False)
        db.query(models.EmployerRegisterEntry).filter(models.EmployerRegisterEntry.contract_version_id.in_(contract_version_ids)).delete(synchronize_session=False)
        db.query(models.ContractVersion).filter(models.ContractVersion.id.in_(contract_version_ids)).delete(synchronize_session=False)
    if contract_ids:
        db.query(models.ComplianceReview).filter(models.ComplianceReview.contract_id.in_(contract_ids)).delete(synchronize_session=False)
        db.query(models.EmployerRegisterEntry).filter(models.EmployerRegisterEntry.contract_id.in_(contract_ids)).delete(synchronize_session=False)
        db.query(models.TerminationWorkflow).filter(models.TerminationWorkflow.contract_id.in_(contract_ids)).delete(synchronize_session=False)
        db.query(models.InspectorCase).filter(models.InspectorCase.contract_id.in_(contract_ids)).delete(synchronize_session=False)
        db.query(models.CustomContract).filter(models.CustomContract.id.in_(contract_ids)).delete(synchronize_session=False)

    db.query(models.EmployerRegisterEntry).filter(models.EmployerRegisterEntry.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.OrganizationAssignmentRecord).filter(models.OrganizationAssignmentRecord.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.CompensationMasterRecord).filter(models.CompensationMasterRecord.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.EmploymentMasterRecord).filter(models.EmploymentMasterRecord.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.EmployeeMasterRecord).filter(models.EmployeeMasterRecord.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.HrEmployeeDocumentVersion).filter(models.HrEmployeeDocumentVersion.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.HrEmployeeDocument).filter(models.HrEmployeeDocument.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.HrEmployeeEvent).filter(models.HrEmployeeEvent.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.HrEmployeeFile).filter(models.HrEmployeeFile.worker_id.in_(worker_ids)).delete(synchronize_session=False)

    db.query(models.HSJourHS).filter(
        models.HSJourHS.calculation_id_HS.in_(
            db.query(models.HSCalculationHS.id_HS).filter(models.HSCalculationHS.worker_id_HS.in_(worker_ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.PayrollHsHm).filter(models.PayrollHsHm.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.HSCalculationHS).filter(models.HSCalculationHS.worker_id_HS.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.PayrollPrime).filter(models.PayrollPrime.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.WorkerPrimeLink).filter(models.WorkerPrimeLink.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.WorkerPrime).filter(models.WorkerPrime.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.PayVar).filter(models.PayVar.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.Absence).filter(models.Absence.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.Avance).filter(models.Avance.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.Leave).filter(models.Leave.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.Permission).filter(models.Permission.worker_id.in_(worker_ids)).delete(synchronize_session=False)
    db.query(models.WorkerPositionHistory).filter(models.WorkerPositionHistory.worker_id.in_(worker_ids)).delete(synchronize_session=False)

@router.get("", response_model=List[schemas.WorkerOut])
def list_workers(
    employer_id: Optional[int] = None,
    etablissement: Optional[str] = None,
    departement: Optional[str] = None,
    service: Optional[str] = None,
    unite: Optional[str] = None,
    q: Optional[str] = None,
    include_inactive: bool = Query(False),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = _apply_worker_scope(db.query(models.Worker), db, user)
    if employer_id:
        query = query.filter(models.Worker.employer_id == employer_id)
        query = apply_worker_hierarchy_filters(
            query,
            db,
            employer_id=employer_id,
            filters={
                "etablissement": etablissement,
                "departement": departement,
                "service": service,
                "unite": unite,
            },
        )
    if not include_inactive:
        query = query.filter(models.Worker.is_active.is_(True))
    query = _apply_worker_search(query, q)
    query = query.order_by(models.Worker.nom.asc(), models.Worker.prenom.asc())
    if page and page_size:
        query = query.offset((page - 1) * page_size).limit(page_size)
    return query.all()


@router.get("/paginated", response_model=schemas.PaginatedWorkersOut)
def list_workers_paginated(
    employer_id: Optional[int] = None,
    q: Optional[str] = None,
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    query = _apply_worker_scope(db.query(models.Worker), db, user)
    if employer_id:
        query = query.filter(models.Worker.employer_id == employer_id)
    if not include_inactive:
        query = query.filter(models.Worker.is_active.is_(True))
    query = _apply_worker_search(query, q)
    total = query.count()
    items = query.order_by(models.Worker.nom.asc(), models.Worker.prenom.asc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = ceil(total / page_size) if total else 1
    return schemas.PaginatedWorkersOut(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)

@router.get("/{worker_id}", response_model=schemas.WorkerOut)
def get_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    w = db.get(models.Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_access_worker(db, user, w):
        raise HTTPException(403, "Forbidden")
    return w

@router.post("", response_model=schemas.WorkerOut)
def create_worker(
    data: schemas.WorkerIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    if not can_manage_worker(db, user, employer_id=data.employer_id):
        raise HTTPException(403, "Forbidden")
    # Ajuste auto VHM/Hebdo si secteur fourni
    vhm = data.vhm
    hebdo = data.horaire_hebdo
    # if data.secteur == "agricole":
    #     vhm, hebdo = 173.33, 40.0
    # elif data.secteur == "non_agricole":
    #     vhm, hebdo = 200.0, 46.0

    selected_unit = OrganizationalService.resolve_selected_unit(
        db,
        employer_id=data.employer_id,
        organizational_unit_id=data.organizational_unit_id,
        etablissement=data.etablissement,
        departement=data.departement,
        service=data.service,
        unite=data.unite,
    )

    obj = models.Worker(
        employer_id=data.employer_id,
        matricule=data.matricule,
        nom=data.nom, prenom=data.prenom,
        type_regime_id=data.type_regime_id,
        adresse=data.adresse,
        nombre_enfant=data.nombre_enfant,
        salaire_base=data.salaire_base,
        salaire_horaire=data.salaire_horaire or (data.salaire_base / vhm if vhm else 0),
        vhm=vhm,
        horaire_hebdo=hebdo,
        nature_contrat=data.nature_contrat,
        categorie_prof=data.categorie_prof,
        poste=data.poste,
        avantage_vehicule=data.avantage_vehicule,
        avantage_logement=data.avantage_logement,
        avantage_telephone=data.avantage_telephone,
        avantage_autres=data.avantage_autres,
        
        # Champs organisationnels
        etablissement=data.etablissement,
        departement=data.departement,
        service=data.service,
        unite=data.unite,
        organizational_unit_id=selected_unit.id if selected_unit else None,
        
        # Débauche
        date_debauche=data.date_debauche,
        type_sortie=data.type_sortie,
        groupe_preavis=data.groupe_preavis,
        jours_preavis_deja_faits=data.jours_preavis_deja_faits,
    )
    OrganizationalService.apply_unit_snapshot_to_worker(obj, selected_unit)
    db.add(obj)
    db.flush()
    sync_worker_master_data(db, obj)
    record_audit(
        db,
        actor=user,
        action="worker.create",
        entity_type="worker",
        entity_id=obj.id,
        route="/workers",
        employer_id=obj.employer_id,
        worker_id=obj.id,
        after=obj,
    )
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/{worker_id}", response_model=schemas.WorkerOut)
def update_worker(
    worker_id: int,
    data: schemas.WorkerIn,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    w = db.get(models.Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")
    before = {
        "salaire_base": w.salaire_base,
        "poste": w.poste,
        "categorie_prof": w.categorie_prof,
        "organizational_unit_id": w.organizational_unit_id,
    }

    # Mise à jour basique
    selected_unit = OrganizationalService.resolve_selected_unit(
        db,
        employer_id=w.employer_id,
        organizational_unit_id=data.organizational_unit_id,
        etablissement=data.etablissement,
        departement=data.departement,
        service=data.service,
        unite=data.unite,
    )

    for k, v in data.dict().items():
        setattr(w, k, v)

    OrganizationalService.apply_unit_snapshot_to_worker(w, selected_unit)

    if not w.salaire_horaire and w.vhm:
        w.salaire_horaire = w.salaire_base / w.vhm
    sync_worker_master_data(db, w)

    record_audit(
        db,
        actor=user,
        action="worker.update",
        entity_type="worker",
        entity_id=w.id,
        route=f"/workers/{worker_id}",
        employer_id=w.employer_id,
        worker_id=w.id,
        before=before,
        after=w,
    )
    db.commit()
    db.refresh(w)
    return w

@router.patch("/{worker_id}/organizational", response_model=schemas.WorkerOut)
def update_worker_organizational(
    worker_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    """Mise à jour des données organisationnelles d'un salarié"""
    w = db.get(models.Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")
    before = {
        "organizational_unit_id": w.organizational_unit_id,
        "etablissement": w.etablissement,
        "departement": w.departement,
        "service": w.service,
        "unite": w.unite,
    }

    # Mise à jour seulement des champs organisationnels fournis
    if any(field in data for field in ("etablissement", "departement", "service", "unite")) and "organizational_unit_id" not in data:
        raise HTTPException(400, "Utilisez organizational_unit_id; la saisie libre locale est bloquée.")
    selected_unit = OrganizationalService.resolve_selected_unit(
        db,
        employer_id=w.employer_id,
        organizational_unit_id=data.get("organizational_unit_id"),
    )
    OrganizationalService.apply_unit_snapshot_to_worker(w, selected_unit)
    sync_worker_master_data(db, w)

    record_audit(
        db,
        actor=user,
        action="worker.organizational.update",
        entity_type="worker",
        entity_id=w.id,
        route=f"/workers/{worker_id}/organizational",
        employer_id=w.employer_id,
        worker_id=w.id,
        before=before,
        after=w,
    )
    db.commit()
    db.refresh(w)
    return w

@router.patch("/{worker_id}", response_model=schemas.WorkerOut)
def patch_worker(
    worker_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    w = db.get(models.Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")
    before = {"salaire_base": w.salaire_base, "solde_conge_initial": w.solde_conge_initial}

    for k, v in data.items():
        if hasattr(w, k):
            setattr(w, k, v)

    if w.vhm and w.vhm > 0:
        w.salaire_horaire = w.salaire_base / w.vhm
    sync_worker_master_data(db, w)

    record_audit(
        db,
        actor=user,
        action="worker.patch",
        entity_type="worker",
        entity_id=w.id,
        route=f"/workers/{worker_id}",
        employer_id=w.employer_id,
        worker_id=w.id,
        before=before,
        after=w,
    )
    db.commit()
    db.refresh(w)
    return w


@router.delete("/all")
def delete_all_workers_legacy():
    raise HTTPException(
        status_code=410,
        detail="Endpoint obsolète. Utilisez POST /workers/reset pour une réinitialisation sécurisée.",
    )


@router.delete("/{worker_id}")
def delete_worker(
    worker_id: int,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    _ensure_worker_delete_role(user, db)
    w = db.get(models.Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if not can_manage_worker(db, user, worker=w):
        raise HTTPException(403, "Forbidden")

    before = {
        "id": w.id,
        "matricule": w.matricule,
        "nom": w.nom,
        "prenom": w.prenom,
        "is_active": w.is_active,
    }

    try:
        if hard_delete:
            _ensure_admin(user, db)
            _purge_worker_dependencies(db, [worker_id])
            db.delete(w)
            action = "worker.delete.hard"
            message = "Travailleur supprimé définitivement."
        else:
            _soft_delete_worker(db, w, user)
            action = "worker.delete.soft"
            message = "Travailleur désactivé avec succès."

        record_audit(
            db,
            actor=user,
            action=action,
            entity_type="worker",
            entity_id=worker_id,
            route=f"/workers/{worker_id}",
            employer_id=w.employer_id,
            worker_id=w.id,
            before=before,
            after=None if hard_delete else w,
        )
        db.commit()
        return {"ok": True, "mode": "hard" if hard_delete else "soft", "message": message}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        operation = "suppression définitive" if hard_delete else "désactivation"
        raise HTTPException(status_code=500, detail=f"Echec de la {operation} du travailleur: {e}")


@router.post("/delete_batch")
def delete_workers_batch(
    data: schemas.WorkerListDelete,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(get_current_user),
):
    """
    Désactive plusieurs travailleurs en une seule requête (par liste d'IDs).
    """
    _ensure_worker_delete_role(user, db)
    try:
        if not data.ids:
            return {"message": "Aucun ID fourni", "count": 0}

        workers_to_delete = db.query(models.Worker).filter(models.Worker.id.in_(data.ids)).all()
        count = len(workers_to_delete)

        for w in workers_to_delete:
            if not can_manage_worker(db, user, worker=w):
                raise HTTPException(403, "Forbidden")
            _soft_delete_worker(db, w, user)
            record_audit(
                db,
                actor=user,
                action="worker.delete.batch.soft",
                entity_type="worker",
                entity_id=w.id,
                route="/workers/delete_batch",
                employer_id=w.employer_id,
                worker_id=w.id,
                before={"id": w.id, "matricule": w.matricule, "nom": w.nom, "prenom": w.prenom, "is_active": True},
                after=w,
            )

        db.commit()
        return {"message": f"{count} travailleurs désactivés", "count": count, "mode": "soft"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Echec de la désactivation groupée: {e}")


@router.post("/reset", response_model=schemas.WorkerResetResult)
def reset_employees(
    data: schemas.WorkerResetRequest,
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles("admin")),
):
    logger.info(
        "workers.reset requested user_id=%s role=%s mode=%s employer_id=%s",
        getattr(user, "id", None),
        getattr(user, "role_code", None),
        data.mode,
        data.employer_id,
    )
    _ensure_admin(user, db)
    confirmation_text = (data.confirmation_text or "").strip()
    if not confirmation_text:
        logger.warning("workers.reset rejected missing_confirmation user_id=%s", getattr(user, "id", None))
        raise HTTPException(status_code=400, detail="Confirmation obligatoire pour réinitialiser les employés.")

    expected_confirmation = "RESET EMPLOYEES HARD" if data.mode == "hard" else "RESET EMPLOYEES"
    if confirmation_text.upper() != expected_confirmation:
        logger.warning(
            "workers.reset rejected bad_confirmation user_id=%s expected=%s received=%s",
            getattr(user, "id", None),
            expected_confirmation,
            confirmation_text,
        )
        raise HTTPException(status_code=400, detail=f"Texte de confirmation invalide. Attendu: {expected_confirmation}")

    query = db.query(models.Worker)
    if data.employer_id:
        query = query.filter(models.Worker.employer_id == data.employer_id)

    workers = query.all()
    logger.info("workers.reset scope_resolved user_id=%s count=%s", getattr(user, "id", None), len(workers))
    for worker in workers:
        if not can_manage_worker(db, user, worker=worker):
            logger.warning(
                "workers.reset forbidden_scope user_id=%s worker_id=%s employer_id=%s",
                getattr(user, "id", None),
                worker.id,
                worker.employer_id,
            )
            raise HTTPException(status_code=403, detail="Forbidden")

    count = len(workers)
    if count == 0:
        return schemas.WorkerResetResult(
            ok=True,
            mode=data.mode,
            count=0,
            message="Aucun travailleur à réinitialiser.",
        )

    try:
        if data.mode == "hard":
            worker_ids = [worker.id for worker in workers]
            _purge_worker_dependencies(db, worker_ids)
            for worker in workers:
                db.delete(worker)
            action = "worker.reset.hard"
            message = f"{count} travailleurs supprimés définitivement."
        else:
            for worker in workers:
                _soft_delete_worker(db, worker, user)
            action = "worker.reset.soft"
            message = f"{count} travailleurs désactivés."

        record_audit(
            db,
            actor=user,
            action=action,
            entity_type="worker",
            entity_id=None,
            route="/workers/reset",
            employer_id=data.employer_id,
            before={"count": count, "mode": data.mode, "employer_id": data.employer_id},
            after={"count": count, "mode": data.mode, "scope": "employer" if data.employer_id else "global"},
        )
        db.commit()
        logger.info(
            "workers.reset completed user_id=%s mode=%s count=%s",
            getattr(user, "id", None),
            data.mode,
            count,
        )
        return schemas.WorkerResetResult(ok=True, mode=data.mode, count=count, message=message)
    except HTTPException:
        db.rollback()
        logger.exception("workers.reset http_exception user_id=%s mode=%s", getattr(user, "id", None), data.mode)
        raise
    except Exception as e:
        db.rollback()
        logger.exception("workers.reset failed user_id=%s mode=%s", getattr(user, "id", None), data.mode)
        raise HTTPException(status_code=500, detail=f"Echec de la réinitialisation des employés: {e}")


# ==========================================
# GESTION DES PRIMES PERSONNALISÉES (WORKER)
# ==========================================

@router.post("/{worker_id}/primes", response_model=schemas.WorkerPrimeOut)
def create_worker_prime(worker_id: int, prime: schemas.WorkerPrimeIn, db: Session = Depends(get_db)):
    worker = db.query(models.Worker).get(worker_id)
    if not worker:
        raise HTTPException(404, "Salarié non trouvé")
        
    db_prime = models.WorkerPrime(**prime.dict(), worker_id=worker_id)
    db.add(db_prime)
    db.commit()
    db.refresh(db_prime)
    return db_prime

@router.put("/{worker_id}/primes/{prime_id}", response_model=schemas.WorkerPrimeOut)
def update_worker_prime(worker_id: int, prime_id: int, prime_data: schemas.WorkerPrimeIn, db: Session = Depends(get_db)):
    db_prime = db.query(models.WorkerPrime).filter(
        models.WorkerPrime.id == prime_id,
        models.WorkerPrime.worker_id == worker_id
    ).first()
    
    if not db_prime:
        raise HTTPException(404, "Prime non trouvée")
        
    for key, value in prime_data.dict().items():
        setattr(db_prime, key, value)
        
    db.commit()
    db.refresh(db_prime)
    return db_prime

@router.delete("/{worker_id}/primes/{prime_id}", status_code=204)
def delete_worker_prime(worker_id: int, prime_id: int, db: Session = Depends(get_db)):
    db_prime = db.query(models.WorkerPrime).filter(
        models.WorkerPrime.id == prime_id,
        models.WorkerPrime.worker_id == worker_id
    ).first()
    
    if not db_prime:
        raise HTTPException(404, "Prime non trouvée")
        
    db.delete(db_prime)
    db.commit()
    return None


# ==========================
# GESTION HISTORIQUE POSTES
# ==========================

@router.post("/{worker_id}/history", response_model=schemas.WorkerPositionHistoryOut)
def create_worker_history(worker_id: int, history: schemas.WorkerPositionHistoryIn, db: Session = Depends(get_db)):
    worker = db.query(models.Worker).get(worker_id)
    if not worker:
        raise HTTPException(404, "Salarié non trouvé")
        
    db_hist = models.WorkerPositionHistory(**history.dict(), worker_id=worker_id)
    db.add(db_hist)
    db.commit()
    db.refresh(db_hist)
    return db_hist

@router.delete("/{worker_id}/history/{history_id}", status_code=204)
def delete_worker_history(worker_id: int, history_id: int, db: Session = Depends(get_db)):
    db_hist = db.query(models.WorkerPositionHistory).filter(
        models.WorkerPositionHistory.id == history_id,
        models.WorkerPositionHistory.worker_id == worker_id
    ).first()
    
    if not db_hist:
        raise HTTPException(404, "Entrée d'historique non trouvée")
        
    db.delete(db_hist)
    db.commit()
    return None
