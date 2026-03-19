"""
OrganizationalMigrationService - Service for migrating flat organizational data to hierarchical structure

This service handles the migration from the old flat organizational structure (text fields in workers)
to the new hierarchical structure using the organizational_units table.

**Feature: hierarchical-organizational-structure**
**Validates: Requirements 5.1, 5.2, 5.3, 10.2**
"""

from typing import List, Dict, Optional, Tuple, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from ..models import OrganizationalUnit, Employer, Worker
from ..schemas import ValidationResult
from .organizational_structure_service import OrganizationalStructureService
from datetime import datetime
import logging
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class MigrationAnalysis:
    """Analysis result for migration planning"""
    employer_id: int
    employer_name: str
    total_workers: int
    unique_combinations: int
    conflicts: List[Dict[str, Any]]
    proposed_hierarchy: Dict[str, Any]
    migration_feasible: bool
    recommendations: List[str]


@dataclass
class MigrationResult:
    """Result of migration operation"""
    success: bool
    employer_id: int
    units_created: int
    workers_migrated: int
    errors: List[str]
    warnings: List[str]
    rollback_data: Optional[Dict[str, Any]] = None


class OrganizationalMigrationService:
    """Service for migrating organizational data from flat to hierarchical structure"""
    
    def __init__(self, db: Session):
        self.db = db
        self.org_service = OrganizationalStructureService(db)
    
    def analyze_existing_data(self, employer_id: int) -> MigrationAnalysis:
        """
        Analyze existing organizational data for an employer to plan migration.
        
        This method examines:
        - Current worker organizational assignments
        - Employer's organizational lists (JSON fields)
        - Potential conflicts and inconsistencies
        - Proposed hierarchical structure
        """
        logger.info(f"Analyzing existing organizational data for employer {employer_id}")
        
        # Get employer
        employer = self.db.query(Employer).filter(Employer.id == employer_id).first()
        if not employer:
            raise ValueError(f"Employer {employer_id} not found")
        
        # Get all workers for this employer
        workers = self.db.query(Worker).filter(Worker.employer_id == employer_id).all()
        
        # Parse employer's organizational lists
        try:
            etablissements = json.loads(employer.etablissements or "[]")
            departements = json.loads(employer.departements or "[]")
            services = json.loads(employer.services or "[]")
            unites = json.loads(employer.unites or "[]")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing organizational lists for employer {employer_id}: {e}")
            etablissements = departements = services = unites = []
        
        # Analyze worker assignments
        worker_combinations = []
        for worker in workers:
            combination = {
                'worker_id': worker.id,
                'worker_name': f"{worker.prenom} {worker.nom}",
                'etablissement': worker.etablissement,
                'departement': worker.departement,
                'service': worker.service,
                'unite': worker.unite
            }
            worker_combinations.append(combination)
        
        # Find unique combinations
        unique_combinations = []
        combination_counts = {}
        
        for combo in worker_combinations:
            key = (combo['etablissement'], combo['departement'], combo['service'], combo['unite'])
            if key not in combination_counts:
                combination_counts[key] = []
                unique_combinations.append(combo)
            combination_counts[key].append(combo['worker_id'])
        
        # Detect conflicts
        conflicts = []
        
        # Check for unused values in employer lists
        used_etablissements = set(combo['etablissement'] for combo in worker_combinations if combo['etablissement'])
        used_departements = set(combo['departement'] for combo in worker_combinations if combo['departement'])
        used_services = set(combo['service'] for combo in worker_combinations if combo['service'])
        used_unites = set(combo['unite'] for combo in worker_combinations if combo['unite'])
        
        unused_etablissements = set(etablissements) - used_etablissements
        unused_departements = set(departements) - used_departements
        unused_services = set(services) - used_services
        unused_unites = set(unites) - used_unites
        
        if unused_etablissements:
            conflicts.append({
                'type': 'unused_values',
                'level': 'etablissement',
                'message': f"Établissements définis mais jamais utilisés: {unused_etablissements}"
            })
        
        if unused_departements:
            conflicts.append({
                'type': 'unused_values',
                'level': 'departement',
                'message': f"Départements définis mais jamais utilisés: {unused_departements}"
            })
        
        if unused_services:
            conflicts.append({
                'type': 'unused_values',
                'level': 'service',
                'message': f"Services définis mais jamais utilisés: {unused_services}"
            })
        
        if unused_unites:
            conflicts.append({
                'type': 'unused_values',
                'level': 'unite',
                'message': f"Unités définies mais jamais utilisées: {unused_unites}"
            })
        
        # Check for hierarchical inconsistencies
        for combo in unique_combinations:
            # If a lower level is specified, all higher levels should be specified
            if combo['departement'] and not combo['etablissement']:
                conflicts.append({
                    'type': 'missing_parent',
                    'level': 'departement',
                    'message': f"Département '{combo['departement']}' sans établissement parent"
                })
            
            if combo['service'] and not combo['departement']:
                conflicts.append({
                    'type': 'missing_parent',
                    'level': 'service',
                    'message': f"Service '{combo['service']}' sans département parent"
                })
            
            if combo['unite'] and not combo['service']:
                conflicts.append({
                    'type': 'missing_parent',
                    'level': 'unite',
                    'message': f"Unité '{combo['unite']}' sans service parent"
                })
        
        # Generate proposed hierarchy
        proposed_hierarchy = self._generate_proposed_hierarchy(unique_combinations, combination_counts)
        
        # Determine if migration is feasible
        critical_conflicts = [c for c in conflicts if c['type'] == 'missing_parent']
        migration_feasible = len(critical_conflicts) == 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(conflicts, unique_combinations, employer)
        
        return MigrationAnalysis(
            employer_id=employer_id,
            employer_name=employer.raison_sociale,
            total_workers=len(workers),
            unique_combinations=len(unique_combinations),
            conflicts=conflicts,
            proposed_hierarchy=proposed_hierarchy,
            migration_feasible=migration_feasible,
            recommendations=recommendations
        )
    
    def create_hierarchy_from_workers(self, employer_id: int, dry_run: bool = False) -> MigrationResult:
        """
        Create hierarchical structure from existing worker assignments.
        
        Args:
            employer_id: ID of the employer
            dry_run: If True, only simulate the migration without making changes
        
        Returns:
            MigrationResult with details of the operation
        """
        logger.info(f"Creating hierarchy from workers for employer {employer_id} (dry_run={dry_run})")
        
        # Analyze first
        analysis = self.analyze_existing_data(employer_id)
        
        if not analysis.migration_feasible:
            return MigrationResult(
                success=False,
                employer_id=employer_id,
                units_created=0,
                workers_migrated=0,
                errors=[f"Migration not feasible due to conflicts: {[c['message'] for c in analysis.conflicts]}"],
                warnings=[]
            )
        
        errors = []
        warnings = []
        units_created = 0
        created_units = {}  # Map of (level, name, parent_key) -> unit_id
        
        try:
            if not dry_run:
                # Start transaction
                self.db.begin()
            
            # Get unique combinations
            workers = self.db.query(Worker).filter(Worker.employer_id == employer_id).all()
            unique_combinations = self._get_unique_combinations(workers)
            
            # Create organizational units level by level
            for combo in unique_combinations:
                try:
                    self._create_units_for_combination(
                        employer_id, combo, created_units, dry_run
                    )
                    units_created += self._count_units_in_combination(combo)
                except Exception as e:
                    error_msg = f"Error creating units for combination {combo}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if not dry_run and not errors:
                self.db.commit()
                logger.info(f"Successfully created {units_created} organizational units")
            elif not dry_run:
                self.db.rollback()
                logger.error("Rolled back due to errors")
            
        except Exception as e:
            if not dry_run:
                self.db.rollback()
            error_msg = f"Critical error during hierarchy creation: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return MigrationResult(
            success=len(errors) == 0,
            employer_id=employer_id,
            units_created=units_created,
            workers_migrated=0,  # Workers not migrated yet
            errors=errors,
            warnings=warnings
        )
    
    def migrate_worker_references(self, employer_id: int, dry_run: bool = False) -> MigrationResult:
        """
        Migrate worker organizational references from text fields to hierarchical structure.
        
        This should be called after create_hierarchy_from_workers.
        """
        logger.info(f"Migrating worker references for employer {employer_id} (dry_run={dry_run})")
        
        errors = []
        warnings = []
        workers_migrated = 0
        rollback_data = {}
        
        try:
            if not dry_run:
                self.db.begin()
            
            # Get all workers for this employer
            workers = self.db.query(Worker).filter(Worker.employer_id == employer_id).all()
            
            # Get all organizational units for this employer
            units = self.db.query(OrganizationalUnit).filter(
                and_(
                    OrganizationalUnit.employer_id == employer_id,
                    OrganizationalUnit.is_active == True
                )
            ).all()
            
            # Create lookup maps
            units_by_path = {}
            for unit in units:
                path_parts = []
                current = unit
                while current:
                    path_parts.insert(0, current.name)
                    if current.parent_id:
                        current = next((u for u in units if u.id == current.parent_id), None)
                    else:
                        current = None
                units_by_path[tuple(path_parts)] = unit
            
            # Migrate each worker
            for worker in workers:
                try:
                    # Store original values for rollback
                    if not dry_run:
                        rollback_data[worker.id] = {
                            'organizational_unit_id': worker.organizational_unit_id
                        }
                    
                    # Find matching organizational unit
                    path_parts = []
                    if worker.etablissement:
                        path_parts.append(worker.etablissement)
                    if worker.departement:
                        path_parts.append(worker.departement)
                    if worker.service:
                        path_parts.append(worker.service)
                    if worker.unite:
                        path_parts.append(worker.unite)
                    
                    if path_parts:
                        path_tuple = tuple(path_parts)
                        matching_unit = units_by_path.get(path_tuple)
                        
                        if matching_unit:
                            if not dry_run:
                                worker.organizational_unit_id = matching_unit.id
                            workers_migrated += 1
                            logger.debug(f"Migrated worker {worker.id} to unit {matching_unit.id}")
                        else:
                            warning_msg = f"No matching unit found for worker {worker.id} with path {path_parts}"
                            warnings.append(warning_msg)
                            logger.warning(warning_msg)
                    else:
                        # Worker has no organizational assignment
                        if not dry_run:
                            worker.organizational_unit_id = None
                        logger.debug(f"Worker {worker.id} has no organizational assignment")
                
                except Exception as e:
                    error_msg = f"Error migrating worker {worker.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if not dry_run and not errors:
                self.db.commit()
                logger.info(f"Successfully migrated {workers_migrated} workers")
            elif not dry_run:
                self.db.rollback()
                logger.error("Rolled back worker migration due to errors")
        
        except Exception as e:
            if not dry_run:
                self.db.rollback()
            error_msg = f"Critical error during worker migration: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return MigrationResult(
            success=len(errors) == 0,
            employer_id=employer_id,
            units_created=0,
            workers_migrated=workers_migrated,
            errors=errors,
            warnings=warnings,
            rollback_data=rollback_data if not dry_run else None
        )
    
    def validate_migration(self, employer_id: int) -> ValidationResult:
        """
        Validate that the migration was successful and data is consistent.
        """
        logger.info(f"Validating migration for employer {employer_id}")
        
        try:
            # Validate hierarchy integrity
            hierarchy_result = self.org_service.validate_hierarchy(employer_id)
            if not hierarchy_result.is_valid:
                return ValidationResult(
                    is_valid=False,
                    message=f"Hierarchy validation failed: {hierarchy_result.message}"
                )
            
            # Check that all workers with organizational assignments have valid references
            workers = self.db.query(Worker).filter(Worker.employer_id == employer_id).all()
            invalid_references = []
            
            for worker in workers:
                if worker.organizational_unit_id:
                    unit = self.db.query(OrganizationalUnit).filter(
                        OrganizationalUnit.id == worker.organizational_unit_id
                    ).first()
                    
                    if not unit:
                        invalid_references.append(f"Worker {worker.id} references non-existent unit {worker.organizational_unit_id}")
                    elif unit.employer_id != employer_id:
                        invalid_references.append(f"Worker {worker.id} references unit from different employer")
            
            if invalid_references:
                return ValidationResult(
                    is_valid=False,
                    message=f"Invalid worker references found: {invalid_references}"
                )
            
            # Count migrated workers
            migrated_count = self.db.query(Worker).filter(
                and_(
                    Worker.employer_id == employer_id,
                    Worker.organizational_unit_id.isnot(None)
                )
            ).count()
            
            total_count = len(workers)
            
            return ValidationResult(
                is_valid=True,
                message=f"Migration validation passed. {migrated_count}/{total_count} workers have organizational assignments."
            )
        
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                message=f"Validation error: {str(e)}"
            )
    
    def rollback_migration(self, employer_id: int, rollback_data: Dict[str, Any]) -> bool:
        """
        Rollback a migration using the provided rollback data.
        """
        logger.info(f"Rolling back migration for employer {employer_id}")
        
        try:
            self.db.begin()
            
            # Restore worker organizational_unit_id values
            if 'workers' in rollback_data:
                for worker_id, original_values in rollback_data['workers'].items():
                    worker = self.db.query(Worker).filter(Worker.id == int(worker_id)).first()
                    if worker:
                        worker.organizational_unit_id = original_values.get('organizational_unit_id')
            
            # Delete created organizational units
            if 'created_units' in rollback_data:
                unit_ids = rollback_data['created_units']
                self.db.query(OrganizationalUnit).filter(
                    OrganizationalUnit.id.in_(unit_ids)
                ).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"Successfully rolled back migration for employer {employer_id}")
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rolling back migration: {str(e)}")
            return False
    
    def _get_unique_combinations(self, workers: List[Worker]) -> List[Dict[str, Any]]:
        """Get unique organizational combinations from workers"""
        combinations = []
        seen = set()
        
        for worker in workers:
            combo_key = (worker.etablissement, worker.departement, worker.service, worker.unite)
            if combo_key not in seen:
                seen.add(combo_key)
                combinations.append({
                    'etablissement': worker.etablissement,
                    'departement': worker.departement,
                    'service': worker.service,
                    'unite': worker.unite
                })
        
        return combinations
    
    def _create_units_for_combination(self, employer_id: int, combo: Dict[str, Any], 
                                    created_units: Dict[str, int], dry_run: bool):
        """Create organizational units for a specific combination"""
        
        # Create establishment if needed
        if combo['etablissement']:
            est_key = ('etablissement', combo['etablissement'], None)
            if est_key not in created_units:
                if not dry_run:
                    unit = OrganizationalUnit(
                        employer_id=employer_id,
                        parent_id=None,
                        level='etablissement',
                        level_order=1,
                        code=combo['etablissement'][:50],  # Truncate if needed
                        name=combo['etablissement'],
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    self.db.add(unit)
                    self.db.flush()  # Get the ID
                    created_units[est_key] = unit.id
                else:
                    created_units[est_key] = -1  # Placeholder for dry run
        
        # Create department if needed
        if combo['departement'] and combo['etablissement']:
            est_key = ('etablissement', combo['etablissement'], None)
            dept_key = ('departement', combo['departement'], est_key)
            
            if dept_key not in created_units:
                parent_id = created_units[est_key] if not dry_run else None
                if not dry_run:
                    unit = OrganizationalUnit(
                        employer_id=employer_id,
                        parent_id=parent_id,
                        level='departement',
                        level_order=2,
                        code=combo['departement'][:50],
                        name=combo['departement'],
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    self.db.add(unit)
                    self.db.flush()
                    created_units[dept_key] = unit.id
                else:
                    created_units[dept_key] = -1
        
        # Create service if needed
        if combo['service'] and combo['departement'] and combo['etablissement']:
            est_key = ('etablissement', combo['etablissement'], None)
            dept_key = ('departement', combo['departement'], est_key)
            serv_key = ('service', combo['service'], dept_key)
            
            if serv_key not in created_units:
                parent_id = created_units[dept_key] if not dry_run else None
                if not dry_run:
                    unit = OrganizationalUnit(
                        employer_id=employer_id,
                        parent_id=parent_id,
                        level='service',
                        level_order=3,
                        code=combo['service'][:50],
                        name=combo['service'],
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    self.db.add(unit)
                    self.db.flush()
                    created_units[serv_key] = unit.id
                else:
                    created_units[serv_key] = -1
        
        # Create unit if needed
        if combo['unite'] and combo['service'] and combo['departement'] and combo['etablissement']:
            est_key = ('etablissement', combo['etablissement'], None)
            dept_key = ('departement', combo['departement'], est_key)
            serv_key = ('service', combo['service'], dept_key)
            unit_key = ('unite', combo['unite'], serv_key)
            
            if unit_key not in created_units:
                parent_id = created_units[serv_key] if not dry_run else None
                if not dry_run:
                    unit = OrganizationalUnit(
                        employer_id=employer_id,
                        parent_id=parent_id,
                        level='unite',
                        level_order=4,
                        code=combo['unite'][:50],
                        name=combo['unite'],
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    self.db.add(unit)
                    self.db.flush()
                    created_units[unit_key] = unit.id
                else:
                    created_units[unit_key] = -1
    
    def _count_units_in_combination(self, combo: Dict[str, Any]) -> int:
        """Count how many units would be created for a combination"""
        count = 0
        if combo['etablissement']:
            count += 1
        if combo['departement']:
            count += 1
        if combo['service']:
            count += 1
        if combo['unite']:
            count += 1
        return count
    
    def _generate_proposed_hierarchy(self, unique_combinations: List[Dict[str, Any]], 
                                   combination_counts: Dict[Tuple, List[int]]) -> Dict[str, Any]:
        """Generate a proposed hierarchy structure from combinations"""
        hierarchy = {
            'total_nodes': 0,
            'max_depth': 0,
            'tree': {}
        }
        
        for combo in unique_combinations:
            worker_count = len(combination_counts.get(
                (combo['etablissement'], combo['departement'], combo['service'], combo['unite']), 
                []
            ))
            
            # Build tree structure
            current_level = hierarchy['tree']
            depth = 0
            
            if combo['etablissement']:
                depth += 1
                if combo['etablissement'] not in current_level:
                    current_level[combo['etablissement']] = {
                        'level': 'etablissement',
                        'worker_count': 0,
                        'children': {}
                    }
                current_level[combo['etablissement']]['worker_count'] += worker_count
                current_level = current_level[combo['etablissement']]['children']
            
            if combo['departement']:
                depth += 1
                if combo['departement'] not in current_level:
                    current_level[combo['departement']] = {
                        'level': 'departement',
                        'worker_count': 0,
                        'children': {}
                    }
                current_level[combo['departement']]['worker_count'] += worker_count
                current_level = current_level[combo['departement']]['children']
            
            if combo['service']:
                depth += 1
                if combo['service'] not in current_level:
                    current_level[combo['service']] = {
                        'level': 'service',
                        'worker_count': 0,
                        'children': {}
                    }
                current_level[combo['service']]['worker_count'] += worker_count
                current_level = current_level[combo['service']]['children']
            
            if combo['unite']:
                depth += 1
                if combo['unite'] not in current_level:
                    current_level[combo['unite']] = {
                        'level': 'unite',
                        'worker_count': 0,
                        'children': {}
                    }
                current_level[combo['unite']]['worker_count'] += worker_count
            
            hierarchy['max_depth'] = max(hierarchy['max_depth'], depth)
        
        # Count total nodes
        def count_nodes(tree_dict):
            count = len(tree_dict)
            for node in tree_dict.values():
                count += count_nodes(node.get('children', {}))
            return count
        
        hierarchy['total_nodes'] = count_nodes(hierarchy['tree'])
        
        return hierarchy
    
    def _generate_recommendations(self, conflicts: List[Dict[str, Any]], 
                                unique_combinations: List[Dict[str, Any]], 
                                employer: Employer) -> List[str]:
        """Generate migration recommendations based on analysis"""
        recommendations = []
        
        if not conflicts:
            recommendations.append("✅ Aucun conflit détecté. Migration recommandée.")
        else:
            recommendations.append("⚠️ Conflits détectés nécessitant une attention:")
            
            for conflict in conflicts:
                if conflict['type'] == 'unused_values':
                    recommendations.append(
                        f"- Nettoyer les valeurs non utilisées dans {conflict['level']}"
                    )
                elif conflict['type'] == 'missing_parent':
                    recommendations.append(
                        f"- Corriger les relations hiérarchiques manquantes"
                    )
        
        if len(unique_combinations) > 50:
            recommendations.append("⚠️ Structure complexe détectée. Considérer une migration par phases.")
        
        recommendations.append("📋 Étapes recommandées:")
        recommendations.append("1. Résoudre les conflits identifiés")
        recommendations.append("2. Tester la migration en mode dry-run")
        recommendations.append("3. Sauvegarder les données avant migration")
        recommendations.append("4. Exécuter la migration en production")
        recommendations.append("5. Valider l'intégrité post-migration")
        
        return recommendations