"""
Organizational Structure Router - API endpoints for hierarchical organizational management

This router provides endpoints for managing the hierarchical organizational structure,
including CRUD operations, tree retrieval, and cascading choices.

**Feature: hierarchical-organizational-structure**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 3.1, 3.2, 3.3**
"""

from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..config.config import get_db
from ..models import OrganizationalUnit, Employer
from ..schemas import (
    CreateOrganizationalUnitRequest,
    UpdateOrganizationalUnitRequest,
    OrganizationalUnitOut,
    OrganizationalTreeResponse,
    CascadingChoicesResponse,
    ValidationResult
)
from ..services.organizational_structure_service import OrganizationalStructureService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizational-structure", tags=["Organizational Structure"])


@router.get("/{employer_id}/tree")
async def get_organizational_tree(
    employer_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the complete organizational tree for an employer.
    
    Returns a hierarchical tree structure with all organizational units.
    """
    logger.info(f"Getting organizational tree for employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    service = OrganizationalStructureService(db)
    tree_data = service.get_tree(employer_id)
    
    return tree_data


@router.get("/{employer_id}/choices")
async def get_cascading_choices(
    employer_id: int,
    level: str = Query(..., description="Level to get choices for"),
    parent_id: Optional[int] = Query(None, description="Parent ID for filtering"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get available choices for a specific level based on parent selection.
    Used for cascading dropdowns.
    """
    logger.info(f"Getting cascading choices for employer {employer_id}, level {level}, parent {parent_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    try:
        service = OrganizationalStructureService(db)
        choices = service.get_available_choices(parent_id, level, employer_id)
        return choices
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create")
async def create_organizational_unit(
    data: CreateOrganizationalUnitRequest,
    db: Session = Depends(get_db)
) -> OrganizationalUnitOut:
    """
    Create a new organizational unit with proper hierarchy validation.
    """
    logger.info(f"Creating organizational unit: {data.name} (level: {data.level})")
    
    try:
        service = OrganizationalStructureService(db)
        unit = service.create_entity(data)
        
        return OrganizationalUnitOut(
            id=unit.id,
            employer_id=unit.employer_id,
            parent_id=unit.parent_id,
            level=unit.level,
            level_order=unit.level_order,
            code=unit.code,
            name=unit.name,
            description=unit.description,
            is_active=unit.is_active,
            created_at=unit.created_at,
            updated_at=unit.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{unit_id}")
async def update_organizational_unit(
    unit_id: int,
    data: UpdateOrganizationalUnitRequest,
    db: Session = Depends(get_db)
) -> OrganizationalUnitOut:
    """
    Update an existing organizational unit with validation.
    """
    logger.info(f"Updating organizational unit {unit_id}")
    
    try:
        service = OrganizationalStructureService(db)
        unit = service.update_entity(unit_id, data)
        
        return OrganizationalUnitOut(
            id=unit.id,
            employer_id=unit.employer_id,
            parent_id=unit.parent_id,
            level=unit.level,
            level_order=unit.level_order,
            code=unit.code,
            name=unit.name,
            description=unit.description,
            is_active=unit.is_active,
            created_at=unit.created_at,
            updated_at=unit.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{unit_id}")
async def delete_organizational_unit(
    unit_id: int,
    force: bool = Query(False, description="Force deletion by reassigning children and workers"),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete an organizational unit with proper constraint checking.
    """
    logger.info(f"Deleting organizational unit {unit_id} (force={force})")
    
    try:
        service = OrganizationalStructureService(db)
        success = service.delete_entity(unit_id, force)
        
        if success:
            return {"message": "Organizational unit deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete organizational unit")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{unit_id}/can-delete")
async def check_deletion_constraints(
    unit_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if an organizational unit can be deleted and get detailed constraint information.
    
    Returns detailed information about what prevents deletion (children, workers, etc.)
    """
    logger.info(f"Checking deletion constraints for unit {unit_id}")
    
    service = OrganizationalStructureService(db)
    result = service.can_delete_unit(unit_id)
    
    if not result["can_delete"] and result["reason"] == "Unit not found":
        raise HTTPException(status_code=404, detail="Organizational unit not found")
    
    return result


@router.get("/{employer_id}/validate")
async def validate_hierarchy(
    employer_id: int,
    db: Session = Depends(get_db)
) -> ValidationResult:
    """
    Validate the complete hierarchy for an employer.
    """
    logger.info(f"Validating hierarchy for employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    service = OrganizationalStructureService(db)
    validation_result = service.validate_hierarchy(employer_id)
    
    return validation_result


@router.get("/unit/{unit_id}/path")
async def get_unit_path(
    unit_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Get the hierarchical path for a unit (breadcrumb).
    """
    logger.info(f"Getting path for unit {unit_id}")
    
    try:
        service = OrganizationalStructureService(db)
        path = service.get_path(unit_id)
        
        return {"unit_id": unit_id, "path": path}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/validate-combination")
async def validate_organizational_combination(
    employer_id: int,
    establishment_id: Optional[int] = None,
    department_id: Optional[int] = None,
    service_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> ValidationResult:
    """
    Validate that a combination of organizational units forms a valid hierarchy path.
    """
    logger.info(f"Validating combination for employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    service = OrganizationalStructureService(db)
    validation_result = service.validate_combination(
        employer_id, establishment_id, department_id, service_id, unit_id
    )
    
    return validation_result


@router.get("/{employer_id}/children")
async def get_children(
    employer_id: int,
    parent_id: Optional[int] = Query(None, description="Parent ID (null for root units)"),
    db: Session = Depends(get_db)
) -> List[OrganizationalUnitOut]:
    """
    Get direct children of a specific organizational unit.
    If parent_id is None, returns root units (establishments).
    """
    logger.info(f"Getting children for parent {parent_id} in employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    service = OrganizationalStructureService(db)
    children = service.get_children(parent_id, employer_id)
    
    return [
        OrganizationalUnitOut(
            id=unit.id,
            employer_id=unit.employer_id,
            parent_id=unit.parent_id,
            level=unit.level,
            level_order=unit.level_order,
            code=unit.code,
            name=unit.name,
            description=unit.description,
            is_active=unit.is_active,
            created_at=unit.created_at,
            updated_at=unit.updated_at
        )
        for unit in children
    ]


# Nouveaux endpoints pour la synchronisation organisationnelle
@router.post("/{employer_id}/sync-workers")
async def sync_all_workers_to_structures(
    employer_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Valide les affectations des salariés d'un employeur sans les modifier.
    Identifie les désynchronisations entre structures et affectations.
    """
    logger.info(f"Validating worker assignments for employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    from ..services.organizational_sync_service import get_sync_service
    sync_service = get_sync_service(db)
    
    try:
        result = sync_service.sync_all_workers_to_hierarchical_structures(employer_id)
        return result
    except Exception as e:
        logger.error(f"Error validating assignments for employer {employer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/{employer_id}/force-sync-workers")
async def force_sync_all_workers_to_structures(
    employer_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    FORCE la synchronisation de tous les salariés d'un employeur vers les structures hiérarchiques.
    ⚠️ ATTENTION: Modifie les affectations existantes. À utiliser avec précaution.
    """
    logger.warning(f"FORCE synchronizing all workers for employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    from ..services.organizational_sync_service import get_sync_service
    sync_service = get_sync_service(db)
    
    try:
        result = sync_service.force_sync_all_workers_to_hierarchical_structures(employer_id)
        return result
    except Exception as e:
        logger.error(f"Error force syncing workers for employer {employer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Force synchronization failed: {str(e)}")


@router.get("/{employer_id}/validate-assignments")
async def validate_worker_assignments(
    employer_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Valide que toutes les affectations des salariés correspondent aux structures existantes.
    Identifie les désynchronisations entre structures et affectations.
    """
    logger.info(f"Validating worker assignments for employer {employer_id}")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    from ..services.organizational_sync_service import get_sync_service
    sync_service = get_sync_service(db)
    
    try:
        result = sync_service.validate_worker_assignments(employer_id)
        return result
    except Exception as e:
        logger.error(f"Error validating assignments for employer {employer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/{employer_id}/sync-structure-change")
async def sync_structure_change(
    employer_id: int,
    old_name: str = Query(..., description="Ancien nom de la structure"),
    new_name: str = Query(..., description="Nouveau nom de la structure"),
    structure_type: str = Query(..., description="Type de structure (etablissement, departement, service, unite)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Synchronise les affectations des salariés après un changement de nom de structure.
    Utilisé automatiquement lors des modifications de structures.
    """
    logger.info(f"Syncing structure change for employer {employer_id}: '{old_name}' → '{new_name}' ({structure_type})")
    
    # Verify employer exists
    employer = db.query(Employer).filter(Employer.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    
    # Validate structure type
    valid_types = ['etablissement', 'departement', 'service', 'unite']
    if structure_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid structure type. Must be one of: {', '.join(valid_types)}"
        )
    
    from ..services.organizational_sync_service import get_sync_service
    sync_service = get_sync_service(db)
    
    try:
        result = sync_service.sync_worker_assignments_after_structure_change(
            employer_id=employer_id,
            old_name=old_name,
            new_name=new_name,
            structure_type=structure_type
        )
        return result
    except Exception as e:
        logger.error(f"Error syncing structure change for employer {employer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")