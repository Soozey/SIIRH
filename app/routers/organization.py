# app/routers/organization.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from ..config.config import get_db

logger = logging.getLogger(__name__)
from ..models import OrganizationalUnit, Worker, Employer
from ..schemas import (
    OrganizationalUnitCreate, 
    OrganizationalUnitUpdate, 
    OrganizationalUnitOut,
    WorkerAssignment,
    OrganizationTree,
    MigrationResult
)
from ..services.organizational_service import OrganizationalService

router = APIRouter(prefix="/organization", tags=["Organization"])


@router.post("/employers/{employer_id}/units", response_model=OrganizationalUnitOut)
def create_organizational_unit(
    employer_id: int,
    unit_data: OrganizationalUnitCreate,
    db: Session = Depends(get_db)
):
    """
    Crée une nouvelle unité organisationnelle avec validation de l'ordre hiérarchique
    """
    try:
        # Vérifier que l'employeur existe
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
        return unit
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employers/{employer_id}/units", response_model=List[OrganizationalUnitOut])
def get_organizational_units(
    employer_id: int,
    level: Optional[str] = Query(None, description="Filter by level"),
    parent_id: Optional[int] = Query(None, description="Filter by parent ID"),
    db: Session = Depends(get_db)
):
    """
    Récupère les unités organisationnelles d'un employeur
    """
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
def get_organizational_unit(unit_id: int, db: Session = Depends(get_db)):
    """
    Récupère une unité organisationnelle par son ID (seulement si active)
    """
    unit = db.query(OrganizationalUnit).filter(
        OrganizationalUnit.id == unit_id,
        OrganizationalUnit.is_active == True
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    return unit


@router.put("/units/{unit_id}", response_model=OrganizationalUnitOut)
def update_organizational_unit(
    unit_id: int,
    unit_data: OrganizationalUnitUpdate,
    db: Session = Depends(get_db)
):
    """
    Met à jour une unité organisationnelle
    """
    unit = db.query(OrganizationalUnit).get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    # Vérifier l'unicité du code si modifié
    if unit_data.code and unit_data.code != unit.code:
        existing = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == unit.employer_id,
            OrganizationalUnit.parent_id == unit.parent_id,
            OrganizationalUnit.code == unit_data.code,
            OrganizationalUnit.id != unit_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Le code '{unit_data.code}' existe déjà à ce niveau")
    
    # Appliquer les modifications
    for field, value in unit_data.dict(exclude_unset=True).items():
        setattr(unit, field, value)
    
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}")
def delete_organizational_unit(unit_id: int, db: Session = Depends(get_db)):
    """
    Supprime une unité organisationnelle (soft delete)
    """
    unit = db.query(OrganizationalUnit).get(unit_id)
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
    db.commit()
    return {"message": "Unité organisationnelle supprimée avec succès"}


@router.get("/employers/{employer_id}/tree", response_model=OrganizationTree)
def get_organization_tree(employer_id: int, db: Session = Depends(get_db)):
    """
    Retourne l'arbre organisationnel complet avec les salariés
    """
    # Vérifier que l'employeur existe
    employer = db.query(Employer).get(employer_id)
    if not employer:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
    
    tree = OrganizationalService.get_organization_tree(db, employer_id)
    return tree


@router.get("/units/{unit_id}/available-workers")
async def get_available_workers_for_unit(
    unit_id: int,
    db: Session = Depends(get_db)
):
    """Récupérer les salariés disponibles pour assignation à une unité"""
    try:
        # Récupérer l'unité pour vérifier qu'elle existe
        unit = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == unit_id,
            OrganizationalUnit.is_active == True
        ).first()
        
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
            workers_data.append({
                "id": worker.id,
                "matricule": worker.matricule,
                "nom": worker.nom,
                "prenom": worker.prenom,
                "poste": worker.poste,
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
                    "matricule": w.matricule,
                    "nom": w.nom,
                    "prenom": w.prenom,
                    "poste": w.poste,
                    "organizational_unit_id": w.organizational_unit_id
                } for w in workers
            ],
            "total_count": len(workers)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/units/{unit_id}/possible-children")
def get_possible_child_levels(unit_id: int, db: Session = Depends(get_db)):
    """
    Retourne les niveaux possibles pour créer des unités enfants
    """
    unit = db.query(OrganizationalUnit).get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    possible_levels = OrganizationalService.get_possible_child_levels(db, unit_id)
    return {
        "unit_id": unit_id,
        "current_level": unit.level,
        "possible_child_levels": possible_levels
    }


@router.get("/employers/{employer_id}/possible-root-levels")
def get_possible_root_levels(employer_id: int, db: Session = Depends(get_db)):
    """
    Retourne les niveaux possibles pour créer des unités racines
    """
    # Vérifier que l'employeur existe
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
    db: Session = Depends(get_db)
):
    """
    Assigne un salarié à une unité organisationnelle
    """
    try:
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
def migrate_existing_data(employer_id: int, db: Session = Depends(get_db)):
    """
    Migre les données textuelles existantes vers la structure organisationnelle
    """
    # Vérifier que l'employeur existe
    employer = db.query(Employer).get(employer_id)
    if not employer:
        raise HTTPException(status_code=404, detail="Employeur non trouvé")
    
    try:
        migrated_count = OrganizationalService.migrate_existing_data(db, employer_id)
        return MigrationResult(
            migrated_count=migrated_count,
            message=f"Migration réussie : {migrated_count} salariés migrés vers la structure organisationnelle"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec de la migration : {str(e)}")


@router.get("/units/{unit_id}/hierarchy")
def get_unit_hierarchy(unit_id: int, db: Session = Depends(get_db)):
    """
    Retourne le chemin hiérarchique complet d'une unité
    """
    unit = db.query(OrganizationalUnit).get(unit_id)
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