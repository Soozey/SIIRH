# app/routers/organization.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from ..config.config import get_db

logger = logging.getLogger(__name__)
from ..models import OrganizationalUnit, Worker, Employer, OrgUnitEvent
from ..schemas import (
    OrganizationalUnitCreate, 
    OrganizationalUnitUpdate, 
    OrganizationalUnitOut,
    OrgUnitEventOut,
    WorkerAssignment,
    OrganizationTree,
    MigrationResult
)
from ..services.organizational_service import OrganizationalService
from ..services.master_data_service import build_worker_reporting_payload
from ..security import (
    READ_PAYROLL_ROLES,
    WRITE_RH_ROLES,
    can_access_employer,
    can_manage_worker,
    require_roles,
)

router = APIRouter(prefix="/organization", tags=["Organization"])


def _ensure_employer_scope(db: Session, user, employer_id: int):
    if not can_access_employer(db, user, employer_id):
        raise HTTPException(status_code=403, detail="Forbidden")


def _get_unit_or_404(db: Session, unit_id: int) -> OrganizationalUnit:
    unit = db.query(OrganizationalUnit).filter(OrganizationalUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="UnitÃ© organisationnelle non trouvÃ©e")
    return unit


def _get_unit_for_user(db: Session, user, unit_id: int, active_only: bool = False) -> OrganizationalUnit:
    query = db.query(OrganizationalUnit).filter(OrganizationalUnit.id == unit_id)
    if active_only:
        query = query.filter(OrganizationalUnit.is_active == True)
    unit = query.first()
    if not unit:
        raise HTTPException(status_code=404, detail="UnitÃ© organisationnelle non trouvÃ©e")
    _ensure_employer_scope(db, user, unit.employer_id)
    return unit


@router.post("/employers/{employer_id}/units", response_model=OrganizationalUnitOut)
def create_organizational_unit(
    employer_id: int,
    unit_data: OrganizationalUnitCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Crée une nouvelle unité organisationnelle avec validation de l'ordre hiérarchique
    """
    try:
        # Vérifier que l'employeur existe
        _ensure_employer_scope(db, user, employer_id)
        employer = db.query(Employer).get(employer_id)
        if not employer:
            raise HTTPException(status_code=404, detail="Employeur non trouvé")
        
        unit = OrganizationalService.create_organizational_unit(
            db=db,
            employer_id=employer_id,
            level=unit_data.level,
            name=unit_data.name,
            code=unit_data.code,
            parent_id=unit_data.parent_id,
            description=unit_data.description
        )
        OrganizationalService.refresh_org_references(
            db,
            employer_id=employer_id,
            root_unit_id=unit.id,
            event_type="org.created",
            triggered_by_user_id=getattr(user, "id", None),
            payload={"name": unit.name, "code": unit.code, "level": unit.level},
        )
        db.commit()
        db.refresh(unit)
        return unit
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employers/{employer_id}/units", response_model=List[OrganizationalUnitOut])
def get_organizational_units(
    employer_id: int,
    level: Optional[str] = Query(None, description="Filter by level"),
    parent_id: Optional[int] = Query(None, description="Filter by parent ID"),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Récupère les unités organisationnelles d'un employeur
    """
    _ensure_employer_scope(db, user, employer_id)
    query = db.query(OrganizationalUnit).filter(
        OrganizationalUnit.employer_id == employer_id,
        OrganizationalUnit.is_active == True
    )
    
    if level:
        query = query.filter(OrganizationalUnit.level == level)
    
    if parent_id is not None:
        query = query.filter(OrganizationalUnit.parent_id == parent_id)
    
    units = query.order_by(OrganizationalUnit.level_order, OrganizationalUnit.name).all()
    return units


@router.get("/units/{unit_id}", response_model=OrganizationalUnitOut)
def get_organizational_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Récupère une unité organisationnelle par son ID (seulement si active)
    """
    unit = _get_unit_for_user(db, user, unit_id, active_only=True)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    return unit


@router.put("/units/{unit_id}", response_model=OrganizationalUnitOut)
def update_organizational_unit(
    unit_id: int,
    unit_data: OrganizationalUnitUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Met à jour une unité organisationnelle
    """
    unit = _get_unit_for_user(db, user, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    # Vérifier l'unicité du code si modifié
    target_parent_id = unit_data.parent_id if "parent_id" in unit_data.dict(exclude_unset=True) else unit.parent_id

    if unit_data.code and unit_data.code != unit.code:
        existing = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == unit.employer_id,
            OrganizationalUnit.parent_id == target_parent_id,
            OrganizationalUnit.code == unit_data.code,
            OrganizationalUnit.id != unit_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Le code '{unit_data.code}' existe déjà à ce niveau")
    
    if "parent_id" in unit_data.dict(exclude_unset=True):
        try:
            OrganizationalService.validate_parent_assignment(
                db,
                employer_id=unit.employer_id,
                unit_id=unit.id,
                parent_id=unit_data.parent_id,
                level=unit.level,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # Appliquer les modifications
    for field, value in unit_data.dict(exclude_unset=True).items():
        setattr(unit, field, value)

    db.flush()
    OrganizationalService.refresh_org_references(
        db,
        employer_id=unit.employer_id,
        root_unit_id=unit.id,
        event_type="org.updated",
        triggered_by_user_id=getattr(user, "id", None),
        payload={"name": unit.name, "code": unit.code, "level": unit.level},
    )
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}")
def delete_organizational_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Supprime une unité organisationnelle (soft delete)
    """
    unit = _get_unit_for_user(db, user, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    # Vérifier qu'il n'y a pas de salariés attachés
    workers_count = db.query(Worker).filter(Worker.organizational_unit_id == unit_id).count()
    if workers_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer l'unité avec {workers_count} salarié(s) assigné(s). Veuillez d'abord les réassigner."
        )
    
    # Vérifier qu'il n'y a pas d'unités enfants actives
    children_count = db.query(OrganizationalUnit).filter(
        OrganizationalUnit.parent_id == unit_id,
        OrganizationalUnit.is_active == True
    ).count()
    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de supprimer l'unité avec {children_count} sous-unité(s). Veuillez d'abord les supprimer."
        )
    
    unit.is_active = False
    OrganizationalService.refresh_org_references(
        db,
        employer_id=unit.employer_id,
        root_unit_id=unit.id,
        event_type="org.deleted",
        triggered_by_user_id=getattr(user, "id", None),
        payload={"name": unit.name, "code": unit.code, "level": unit.level, "is_active": False},
    )
    db.commit()
    return {"message": "Unité organisationnelle supprimée avec succès"}


@router.get("/employers/{employer_id}/tree", response_model=OrganizationTree)
def get_organization_tree(
    employer_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Retourne l'arbre organisationnel complet avec les salariés
    """
    # Vérifier que l'employeur existe
    _ensure_employer_scope(db, user, employer_id)
    employer = db.query(Employer).get(employer_id)
    if not employer:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
    
    tree = OrganizationalService.get_organization_tree(db, employer_id)
    return tree


@router.get("/employers/{employer_id}/events", response_model=List[OrgUnitEventOut])
def list_org_unit_events(
    employer_id: int,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    _ensure_employer_scope(db, user, employer_id)
    return (
        db.query(OrgUnitEvent)
        .filter(OrgUnitEvent.employer_id == employer_id)
        .order_by(OrgUnitEvent.created_at.desc(), OrgUnitEvent.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/units/{unit_id}/available-workers")
async def get_available_workers_for_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """Récupérer les salariés disponibles pour assignation à une unité"""
    try:
        # Récupérer l'unité pour vérifier qu'elle existe
        unit = _get_unit_for_user(db, user, unit_id, active_only=True)
        
        if not unit:
            raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
        
        # Récupérer tous les salariés de cet employeur qui ne sont PAS déjà assignés à cette unité
        # Inclure : salariés non assignés (NULL) + salariés assignés à d'autres unités
        workers = db.query(Worker).filter(
            Worker.employer_id == unit.employer_id,
            or_(
                Worker.organizational_unit_id.is_(None),  # Salariés non assignés
                Worker.organizational_unit_id != unit_id  # Salariés assignés à d'autres unités
            )
        ).all()
        
        logger.info(f"Salariés disponibles pour l'unité {unit_id}: {len(workers)} trouvés")
        
        # Formater les données
        workers_data = []
        for worker in workers:
            canonical = build_worker_reporting_payload(db, worker)
            workers_data.append({
                "id": worker.id,
                "matricule": canonical.get("matricule"),
                "nom": canonical.get("nom"),
                "prenom": canonical.get("prenom"),
                "poste": canonical.get("poste"),
                "current_unit_id": worker.organizational_unit_id,
                "is_unassigned": worker.organizational_unit_id is None
            })
        
        return {"workers": workers_data}
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des salariés disponibles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des salariés disponibles: {str(e)}")


def get_workers_in_unit(
    unit_id: int,
    include_descendants: bool = Query(True, description="Include workers from descendant units"),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les salariés d'une unité organisationnelle
    """
    try:
        workers = OrganizationalService.get_workers_in_hierarchy(
            db=db,
            unit_id=unit_id,
            include_descendants=include_descendants
        )
        
        return {
            "unit_id": unit_id,
            "include_descendants": include_descendants,
            "workers": [
                {
                    "id": w.id,
                    "matricule": build_worker_reporting_payload(db, w).get("matricule"),
                    "nom": build_worker_reporting_payload(db, w).get("nom"),
                    "prenom": build_worker_reporting_payload(db, w).get("prenom"),
                    "poste": build_worker_reporting_payload(db, w).get("poste"),
                    "organizational_unit_id": w.organizational_unit_id
                } for w in workers
            ],
            "total_count": len(workers)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/units/{unit_id}/possible-children")
def get_possible_child_levels(
    unit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Retourne les niveaux possibles pour créer des unités enfants
    """
    unit = _get_unit_for_user(db, user, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    possible_levels = OrganizationalService.get_possible_child_levels(db, unit_id)
    return {
        "unit_id": unit_id,
        "current_level": unit.level,
        "possible_child_levels": possible_levels
    }


@router.get("/employers/{employer_id}/possible-root-levels")
def get_possible_root_levels(
    employer_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Retourne les niveaux possibles pour créer des unités racines
    """
    # Vérifier que l'employeur existe
    _ensure_employer_scope(db, user, employer_id)
    employer = db.query(Employer).get(employer_id)
    if not employer:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
    
    possible_levels = OrganizationalService.get_possible_child_levels(db, None)
    return {
        "employer_id": employer_id,
        "possible_root_levels": possible_levels
    }


@router.post("/workers/assign")
def assign_worker_to_unit(
    assignment: WorkerAssignment,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Assigne un salarié à une unité organisationnelle
    """
    try:
        worker = db.query(Worker).filter(Worker.id == assignment.worker_id).first()
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        if not can_manage_worker(db, user, worker=worker):
            raise HTTPException(status_code=403, detail="Forbidden")
        _get_unit_for_user(db, user, assignment.organizational_unit_id)

        worker = OrganizationalService.assign_worker_to_unit(
            db=db,
            worker_id=assignment.worker_id,
            unit_id=assignment.organizational_unit_id
        )
        
        return {
            "message": "Salarié assigné avec succès",
            "worker_id": worker.id,
            "organizational_unit_id": worker.organizational_unit_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/employers/{employer_id}/migrate", response_model=MigrationResult)
def migrate_existing_data(
    employer_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Migre les données textuelles existantes vers la structure organisationnelle
    """
    # Vérifier que l'employeur existe
    _ensure_employer_scope(db, user, employer_id)
    employer = db.query(Employer).get(employer_id)
    if not employer:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
    
    try:
        migrated_count = OrganizationalService.migrate_existing_data(db, employer_id)
        OrganizationalService.refresh_org_references(
            db,
            employer_id=employer_id,
            root_unit_id=None,
            event_type="org.migrated",
            triggered_by_user_id=getattr(user, "id", None),
            payload={"migrated_workers": migrated_count},
        )
        db.commit()
        return MigrationResult(
            migrated_count=migrated_count,
            message=f"Migration réussie : {migrated_count} salariés migrés vers la structure organisationnelle"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec de la migration : {str(e)}")


@router.get("/units/{unit_id}/hierarchy")
def get_unit_hierarchy(
    unit_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*READ_PAYROLL_ROLES)),
):
    """
    Retourne le chemin hiérarchique complet d'une unité
    """
    unit = _get_unit_for_user(db, user, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    hierarchy_path = unit.get_hierarchy_path()
    
    return {
        "unit_id": unit_id,
        "hierarchy_path": [
            {
                "id": u.id,
                "name": u.name,
                "code": u.code,
                "level": u.level,
                "level_order": u.level_order
            } for u in hierarchy_path
        ]
    }
