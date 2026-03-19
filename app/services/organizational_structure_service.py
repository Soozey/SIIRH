"""
OrganizationalStructureService - Service for managing hierarchical organizational structures

This service provides all operations for managing the hierarchical organizational structure,
including CRUD operations, hierarchy validation, path generation, and cascading choices.

**Feature: hierarchical-organizational-structure**
**Validates: Requirements 7.1, 7.3, 6.4**
"""

from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from ..models import OrganizationalUnit, Employer, Worker
from ..schemas import (
    OrganizationalUnitOut, 
    CreateOrganizationalUnitRequest,
    UpdateOrganizationalUnitRequest,
    OrganizationalTreeResponse,
    CascadingChoicesResponse,
    ValidationResult
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrganizationalStructureService:
    """Service for managing hierarchical organizational structures"""
    
    # Level hierarchy constants
    LEVEL_HIERARCHY = {
        'etablissement': 1,
        'departement': 2,
        'service': 3,
        'unite': 4
    }
    
    LEVEL_NAMES = {
        1: 'etablissement',
        2: 'departement', 
        3: 'service',
        4: 'unite'
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_tree(self, employer_id: int) -> Dict[str, Any]:
        """
        Get the complete organizational tree for an employer.
        
        Returns a hierarchical tree structure with all organizational units.
        """
        logger.info(f"Getting organizational tree for employer {employer_id}")
        
        # Get all organizational units for this employer
        units = self.db.query(OrganizationalUnit).filter(
            and_(
                OrganizationalUnit.employer_id == employer_id,
                OrganizationalUnit.is_active == True
            )
        ).order_by(
            OrganizationalUnit.level_order,
            OrganizationalUnit.name
        ).all()
        
        if not units:
            return {
                "employer_id": employer_id,
                "tree": [],
                "total_units": 0,
                "levels_present": []
            }
        
        # Build the tree structure
        tree = self._build_tree_structure(units)
        
        # Get statistics
        levels_present = list(set(unit.level for unit in units))
        
        return {
            "employer_id": employer_id,
            "tree": tree,
            "total_units": len(units),
            "levels_present": sorted(levels_present, key=lambda x: self.LEVEL_HIERARCHY[x])
        }
    
    def get_children(self, parent_id: Optional[int], employer_id: int) -> List[OrganizationalUnit]:
        """
        Get direct children of a specific organizational unit.
        If parent_id is None, returns root units (establishments).
        """
        logger.info(f"Getting children for parent {parent_id} in employer {employer_id}")
        
        query = self.db.query(OrganizationalUnit).filter(
            and_(
                OrganizationalUnit.employer_id == employer_id,
                OrganizationalUnit.parent_id == parent_id,
                OrganizationalUnit.is_active == True
            )
        ).order_by(OrganizationalUnit.name)
        
        return query.all()
    
    def create_entity(self, data: CreateOrganizationalUnitRequest) -> OrganizationalUnit:
        """
        Create a new organizational unit with proper hierarchy validation.
        """
        logger.info(f"Creating organizational unit: {data.name} (level: {data.level})")
        
        # Validate the creation request
        validation_result = self._validate_creation(data)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid organizational unit creation: {validation_result.message}")
        
        # Determine level_order
        level_order = self.LEVEL_HIERARCHY.get(data.level)
        if not level_order:
            raise ValueError(f"Invalid level: {data.level}")
        
        # Create the unit
        unit = OrganizationalUnit(
            employer_id=data.employer_id,
            parent_id=data.parent_id,
            level=data.level,
            level_order=level_order,
            code=data.code,
            name=data.name,
            description=data.description,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(unit)
        self.db.commit()
        self.db.refresh(unit)
        
        logger.info(f"Created organizational unit {unit.id}: {unit.name}")
        return unit
    
    def update_entity(self, unit_id: int, data: UpdateOrganizationalUnitRequest) -> OrganizationalUnit:
        """
        Update an existing organizational unit with validation.
        Automatically synchronizes worker assignments if name changes.
        """
        logger.info(f"Updating organizational unit {unit_id}")
        
        unit = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == unit_id
        ).first()
        
        if not unit:
            raise ValueError(f"Organizational unit {unit_id} not found")

        # Store old name for synchronization
        old_name = unit.name
        name_changed = False
        
        # Validate the update
        validation_result = self._validate_update(unit, data)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid organizational unit update: {validation_result.message}")
        
        # Update fields
        if data.name is not None and data.name != unit.name:
            unit.name = data.name
            name_changed = True
        if data.code is not None:
            unit.code = data.code
        if data.description is not None:
            unit.description = data.description
        if data.is_active is not None:
            unit.is_active = data.is_active
        
        unit.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(unit)
        
        # Automatic synchronization if name changed
        if name_changed:
            logger.info(f"Name changed from '{old_name}' to '{unit.name}', triggering automatic synchronization")
            try:
                from .organizational_sync_service import get_sync_service
                sync_service = get_sync_service(self.db)
                sync_result = sync_service.sync_worker_assignments_after_structure_change(
                    employer_id=unit.employer_id,
                    old_name=old_name,
                    new_name=unit.name,
                    structure_type=unit.level
                )
                logger.info(f"Automatic sync completed: {sync_result['updated_workers_count']} workers updated")
            except Exception as e:
                logger.error(f"Automatic synchronization failed: {e}")
                # Don't fail the update if sync fails, just log the error
        
        logger.info(f"Updated organizational unit {unit.id}: {unit.name}")
        return unit
    
    def delete_entity(self, unit_id: int, force: bool = False) -> bool:
        """
        Delete an organizational unit with proper constraint checking.
        
        Args:
            unit_id: ID of the unit to delete
            force: If True, will reassign children and workers before deletion
        
        Returns:
            True if deletion was successful
        """
        logger.info(f"Deleting organizational unit {unit_id} (force={force})")
        
        unit = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == unit_id
        ).first()
        
        if not unit:
            raise ValueError(f"Organizational unit {unit_id} not found")
        
        # Check for children
        children_count = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.parent_id == unit_id
        ).count()
        
        # Check for assigned workers (direct assignment)
        direct_workers_count = self.db.query(Worker).filter(
            Worker.organizational_unit_id == unit_id
        ).count()
        
        # Check for workers in descendant units (recursive check)
        descendant_workers_count = self._count_workers_in_descendants(unit_id)
        total_workers_count = direct_workers_count + descendant_workers_count
        
        if children_count > 0 and not force:
            raise ValueError(f"Cannot delete unit {unit.name}: has {children_count} children units. Use force=True to reassign.")
        
        if total_workers_count > 0 and not force:
            if direct_workers_count > 0 and descendant_workers_count > 0:
                raise ValueError(f"Cannot delete unit {unit.name}: has {direct_workers_count} directly assigned workers and {descendant_workers_count} workers in sub-units. Use force=True to reassign.")
            elif direct_workers_count > 0:
                raise ValueError(f"Cannot delete unit {unit.name}: has {direct_workers_count} assigned workers. Use force=True to reassign.")
            else:
                raise ValueError(f"Cannot delete unit {unit.name}: has {descendant_workers_count} workers in sub-units. Use force=True to reassign.")
        
        if force:
            # Reassign children to parent
            if children_count > 0:
                self.db.query(OrganizationalUnit).filter(
                    OrganizationalUnit.parent_id == unit_id
                ).update({"parent_id": unit.parent_id})
                logger.info(f"Reassigned {children_count} children to parent {unit.parent_id}")
            
            # Unassign direct workers
            if direct_workers_count > 0:
                self.db.query(Worker).filter(
                    Worker.organizational_unit_id == unit_id
                ).update({"organizational_unit_id": None})
                logger.info(f"Unassigned {direct_workers_count} direct workers")
        
        # Delete the unit
        self.db.delete(unit)
        self.db.commit()
        
        logger.info(f"Deleted organizational unit {unit_id}: {unit.name}")
        return True
    
    def validate_hierarchy(self, employer_id: int) -> ValidationResult:
        """
        Validate the complete hierarchy for an employer.
        
        Checks for:
        - Orphaned nodes
        - Circular references
        - Level consistency
        - Proper root nodes
        """
        logger.info(f"Validating hierarchy for employer {employer_id}")
        
        units = self.db.query(OrganizationalUnit).filter(
            and_(
                OrganizationalUnit.employer_id == employer_id,
                OrganizationalUnit.is_active == True
            )
        ).all()
        
        if not units:
            return ValidationResult(is_valid=True, message="No organizational units to validate")
        
        # Check for orphaned nodes
        unit_ids = {unit.id for unit in units}
        orphaned = []
        
        for unit in units:
            if unit.parent_id is not None and unit.parent_id not in unit_ids:
                orphaned.append(unit)
        
        if orphaned:
            orphan_names = [f"{unit.name} (ID:{unit.id})" for unit in orphaned]
            return ValidationResult(
                is_valid=False,
                message=f"Orphaned units found: {orphan_names}"
            )
        
        # Check level consistency
        units_by_id = {unit.id: unit for unit in units}
        
        for unit in units:
            # Root nodes must be establishments
            if unit.parent_id is None:
                if unit.level != 'etablissement':
                    return ValidationResult(
                        is_valid=False,
                        message=f"Root unit {unit.name} must be 'etablissement', got '{unit.level}'"
                    )
            else:
                # Child level must be parent level + 1
                parent = units_by_id.get(unit.parent_id)
                if parent:
                    expected_level_order = parent.level_order + 1
                    if unit.level_order != expected_level_order:
                        return ValidationResult(
                            is_valid=False,
                            message=f"Unit {unit.name} has invalid level progression. "
                                   f"Expected level_order={expected_level_order}, got {unit.level_order}"
                        )
        
        # Check for cycles (simplified check)
        visited = set()
        
        def has_cycle(unit_id: int, path: set) -> bool:
            if unit_id in path:
                return True
            if unit_id in visited:
                return False
            
            visited.add(unit_id)
            path.add(unit_id)
            
            unit = units_by_id.get(unit_id)
            if unit and unit.parent_id:
                if has_cycle(unit.parent_id, path):
                    return True
            
            path.remove(unit_id)
            return False
        
        for unit in units:
            if has_cycle(unit.id, set()):
                return ValidationResult(
                    is_valid=False,
                    message=f"Circular reference detected involving unit {unit.name}"
                )
        
        return ValidationResult(
            is_valid=True,
            message=f"Hierarchy validation passed for {len(units)} units"
        )
    
    def get_path(self, unit_id: int) -> str:
        """
        Get the hierarchical path for a unit (breadcrumb).
        Returns path like: "Establishment / Department / Service / Unit"
        """
        unit = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == unit_id
        ).first()
        
        if not unit:
            raise ValueError(f"Organizational unit {unit_id} not found")
        
        path_parts = []
        current = unit
        
        while current:
            path_parts.insert(0, current.name)
            if current.parent_id:
                current = self.db.query(OrganizationalUnit).filter(
                    OrganizationalUnit.id == current.parent_id
                ).first()
            else:
                current = None
        
        return " / ".join(path_parts)
    
    def get_available_choices(self, parent_id: Optional[int], level: str, employer_id: int) -> List[Dict[str, Any]]:
        """
        Get available choices for a specific level based on parent selection.
        Used for cascading dropdowns.
        """
        logger.info(f"Getting available choices for level {level}, parent {parent_id}, employer {employer_id}")
        
        # Validate level
        if level not in self.LEVEL_HIERARCHY:
            raise ValueError(f"Invalid level: {level}")
        
        expected_level_order = self.LEVEL_HIERARCHY[level]
        
        # If requesting establishments, parent_id should be None
        if level == 'etablissement':
            if parent_id is not None:
                raise ValueError("Establishments cannot have a parent")
            parent_id = None
        else:
            # Validate parent exists and has correct level
            if parent_id is None:
                raise ValueError(f"Level {level} requires a parent")
            
            parent = self.db.query(OrganizationalUnit).filter(
                OrganizationalUnit.id == parent_id
            ).first()
            
            if not parent:
                raise ValueError(f"Parent unit {parent_id} not found")
            
            if parent.level_order != expected_level_order - 1:
                raise ValueError(f"Invalid parent level for {level}")
        
        # Get available units
        units = self.db.query(OrganizationalUnit).filter(
            and_(
                OrganizationalUnit.employer_id == employer_id,
                OrganizationalUnit.parent_id == parent_id,
                OrganizationalUnit.level == level,
                OrganizationalUnit.is_active == True
            )
        ).order_by(OrganizationalUnit.name).all()
        
        return [
            {
                "id": unit.id,
                "name": unit.name,
                "code": unit.code,
                "level": unit.level,
                "level_order": unit.level_order,
                "worker_count": self._get_unit_worker_count(unit.id)
            }
            for unit in units
        ]
    
    def validate_combination(self, employer_id: int, establishment_id: Optional[int] = None,
                           department_id: Optional[int] = None, service_id: Optional[int] = None,
                           unit_id: Optional[int] = None) -> ValidationResult:
        """
        Validate that a combination of organizational units forms a valid hierarchy path.
        """
        logger.info(f"Validating combination for employer {employer_id}")
        
        # Collect the units
        units = {}
        unit_ids = [establishment_id, department_id, service_id, unit_id]
        levels = ['etablissement', 'departement', 'service', 'unite']
        
        for unit_id, level in zip(unit_ids, levels):
            if unit_id is not None:
                unit = self.db.query(OrganizationalUnit).filter(
                    and_(
                        OrganizationalUnit.id == unit_id,
                        OrganizationalUnit.employer_id == employer_id,
                        OrganizationalUnit.is_active == True
                    )
                ).first()
                
                if not unit:
                    return ValidationResult(
                        is_valid=False,
                        message=f"Unit {unit_id} not found or not active"
                    )
                
                if unit.level != level:
                    return ValidationResult(
                        is_valid=False,
                        message=f"Unit {unit.name} is level {unit.level}, expected {level}"
                    )
                
                units[level] = unit
        
        # Validate hierarchy relationships
        if 'departement' in units and 'etablissement' not in units:
            return ValidationResult(
                is_valid=False,
                message="Department requires an establishment"
            )
        
        if 'service' in units and 'departement' not in units:
            return ValidationResult(
                is_valid=False,
                message="Service requires a department"
            )
        
        if 'unite' in units and 'service' not in units:
            return ValidationResult(
                is_valid=False,
                message="Unit requires a service"
            )
        
        # Validate parent-child relationships
        if 'departement' in units and 'etablissement' in units:
            if units['departement'].parent_id != units['etablissement'].id:
                return ValidationResult(
                    is_valid=False,
                    message=f"Department {units['departement'].name} is not a child of establishment {units['etablissement'].name}"
                )
        
        if 'service' in units and 'departement' in units:
            if units['service'].parent_id != units['departement'].id:
                return ValidationResult(
                    is_valid=False,
                    message=f"Service {units['service'].name} is not a child of department {units['departement'].name}"
                )
        
        if 'unite' in units and 'service' in units:
            if units['unite'].parent_id != units['service'].id:
                return ValidationResult(
                    is_valid=False,
                    message=f"Unit {units['unite'].name} is not a child of service {units['service'].name}"
                )
        
        return ValidationResult(
            is_valid=True,
            message="Valid organizational combination"
        )
    
    def _build_tree_structure(self, units: List[OrganizationalUnit]) -> List[Dict[str, Any]]:
        """Build a nested tree structure from flat list of units"""
        units_by_id = {unit.id: unit for unit in units}
        units_by_parent = {}
        
        # Group units by parent
        for unit in units:
            parent_id = unit.parent_id
            if parent_id not in units_by_parent:
                units_by_parent[parent_id] = []
            units_by_parent[parent_id].append(unit)
        
        def build_node(unit: OrganizationalUnit) -> Dict[str, Any]:
            children = units_by_parent.get(unit.id, [])
            return {
                "id": unit.id,
                "name": unit.name,
                "code": unit.code,
                "level": unit.level,
                "level_order": unit.level_order,
                "description": unit.description,
                "worker_count": self._get_unit_worker_count(unit.id),
                "children": [build_node(child) for child in sorted(children, key=lambda x: x.name)]
            }
        
        # Build tree starting from roots (parent_id = None)
        roots = units_by_parent.get(None, [])
        return [build_node(root) for root in sorted(roots, key=lambda x: x.name)]
    
    def _get_unit_worker_count(self, unit_id: int) -> int:
        """Get the number of workers assigned to this unit"""
        return self.db.query(Worker).filter(
            Worker.organizational_unit_id == unit_id
        ).count()
    
    def _count_workers_in_descendants(self, unit_id: int) -> int:
        """
        Count workers in all descendant units recursively.
        This helps prevent deletion of units that have workers in sub-units.
        """
        # Get all descendant units recursively
        descendant_ids = self._get_all_descendant_ids(unit_id)
        
        if not descendant_ids:
            return 0
        
        # Count workers in all descendant units
        return self.db.query(Worker).filter(
            Worker.organizational_unit_id.in_(descendant_ids)
        ).count()
    
    def _get_all_descendant_ids(self, unit_id: int) -> List[int]:
        """
        Get all descendant unit IDs recursively.
        """
        descendant_ids = []
        
        # Get direct children
        children = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.parent_id == unit_id
        ).all()
        
        for child in children:
            descendant_ids.append(child.id)
            # Recursively get descendants of this child
            descendant_ids.extend(self._get_all_descendant_ids(child.id))
        
        return descendant_ids
    
    def can_delete_unit(self, unit_id: int) -> Dict[str, Any]:
        """
        Check if a unit can be deleted and provide detailed information.
        
        Returns:
            Dict with deletion status and detailed information about constraints
        """
        unit = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == unit_id
        ).first()
        
        if not unit:
            return {
                "can_delete": False,
                "reason": "Unit not found",
                "unit_name": None,
                "children_count": 0,
                "direct_workers_count": 0,
                "descendant_workers_count": 0,
                "total_workers_count": 0,
                "children": [],
                "workers": []
            }
        
        # Count children
        children = self.db.query(OrganizationalUnit).filter(
            OrganizationalUnit.parent_id == unit_id
        ).all()
        children_count = len(children)
        
        # Count direct workers
        direct_workers = self.db.query(Worker).filter(
            Worker.organizational_unit_id == unit_id
        ).all()
        direct_workers_count = len(direct_workers)
        
        # Count workers in descendants
        descendant_workers_count = self._count_workers_in_descendants(unit_id)
        total_workers_count = direct_workers_count + descendant_workers_count
        
        # Determine if deletion is possible
        can_delete = children_count == 0 and total_workers_count == 0
        
        # Build reason message
        reasons = []
        if children_count > 0:
            reasons.append(f"{children_count} sous-structures")
        if direct_workers_count > 0:
            reasons.append(f"{direct_workers_count} salariés directement assignés")
        if descendant_workers_count > 0:
            reasons.append(f"{descendant_workers_count} salariés dans les sous-structures")
        
        reason = None if can_delete else f"Contient: {', '.join(reasons)}"
        
        return {
            "can_delete": can_delete,
            "reason": reason,
            "unit_name": unit.name,
            "unit_level": unit.level,
            "children_count": children_count,
            "direct_workers_count": direct_workers_count,
            "descendant_workers_count": descendant_workers_count,
            "total_workers_count": total_workers_count,
            "children": [{"id": child.id, "name": child.name, "level": child.level} for child in children],
            "workers": [{"id": worker.id, "nom": worker.nom, "prenom": worker.prenom, "matricule": worker.matricule} for worker in direct_workers]
        }
    
    def _validate_creation(self, data: CreateOrganizationalUnitRequest) -> ValidationResult:
        """Validate organizational unit creation request"""
        
        # Check if employer exists
        employer = self.db.query(Employer).filter(
            Employer.id == data.employer_id
        ).first()
        
        if not employer:
            return ValidationResult(
                is_valid=False,
                message=f"Employer {data.employer_id} not found"
            )
        
        # Validate level
        if data.level not in self.LEVEL_HIERARCHY:
            return ValidationResult(
                is_valid=False,
                message=f"Invalid level: {data.level}"
            )
        
        # Validate parent relationship
        if data.level == 'etablissement':
            if data.parent_id is not None:
                return ValidationResult(
                    is_valid=False,
                    message="Establishments cannot have a parent"
                )
        else:
            if data.parent_id is None:
                return ValidationResult(
                    is_valid=False,
                    message=f"Level {data.level} requires a parent"
                )
            
            # Check parent exists and has correct level
            parent = self.db.query(OrganizationalUnit).filter(
                OrganizationalUnit.id == data.parent_id
            ).first()
            
            if not parent:
                return ValidationResult(
                    is_valid=False,
                    message=f"Parent unit {data.parent_id} not found"
                )
            
            expected_parent_level_order = self.LEVEL_HIERARCHY[data.level] - 1
            if parent.level_order != expected_parent_level_order:
                return ValidationResult(
                    is_valid=False,
                    message=f"Invalid parent level for {data.level}. Parent has level {parent.level}"
                )
        
        # Check for duplicate code within same parent
        existing = self.db.query(OrganizationalUnit).filter(
            and_(
                OrganizationalUnit.employer_id == data.employer_id,
                OrganizationalUnit.parent_id == data.parent_id,
                OrganizationalUnit.code == data.code,
                OrganizationalUnit.is_active == True
            )
        ).first()
        
        if existing:
            return ValidationResult(
                is_valid=False,
                message=f"Code {data.code} already exists in this parent scope"
            )
        
        return ValidationResult(is_valid=True, message="Valid creation request")
    
    def _validate_update(self, unit: OrganizationalUnit, data: UpdateOrganizationalUnitRequest) -> ValidationResult:
        """Validate organizational unit update request"""
        
        # Check for duplicate code if code is being changed
        if data.code is not None and data.code != unit.code:
            existing = self.db.query(OrganizationalUnit).filter(
                and_(
                    OrganizationalUnit.employer_id == unit.employer_id,
                    OrganizationalUnit.parent_id == unit.parent_id,
                    OrganizationalUnit.code == data.code,
                    OrganizationalUnit.id != unit.id,
                    OrganizationalUnit.is_active == True
                )
            ).first()
            
            if existing:
                return ValidationResult(
                    is_valid=False,
                    message=f"Code {data.code} already exists in this parent scope"
                )
        
        return ValidationResult(is_valid=True, message="Valid update request")