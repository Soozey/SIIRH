# app/services/organizational_service.py
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models import OrganizationalUnit, Worker, Employer, ORGANIZATIONAL_LEVELS
from ..config.config import get_db

logger = logging.getLogger(__name__)


class OrganizationalService:
    """
    Service pour gérer la structure organisationnelle hiérarchique
    """
    
    @staticmethod
    def validate_hierarchy_order(parent_unit: Optional[OrganizationalUnit], child_level: str) -> bool:
        """
        Valide que l'ordre hiérarchique est respecté
        Ordre strict : etablissement(1) → departement(2) → service(3) → unite(4)
        """
        if not parent_unit:
            # Seul 'etablissement' peut être créé sans parent
            return child_level == 'etablissement'
        
        parent_order = ORGANIZATIONAL_LEVELS[parent_unit.level]
        child_order = ORGANIZATIONAL_LEVELS[child_level]
        
        # Le niveau enfant doit être immédiatement supérieur au parent
        return child_order == parent_order + 1
    
    @staticmethod
    def create_organizational_unit(
        db: Session,
        employer_id: int,
        level: str,
        name: str,
        code: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> OrganizationalUnit:
        """
        Crée une unité organisationnelle avec validation de l'ordre hiérarchique
        """
        
        # Validation du niveau
        if level not in ORGANIZATIONAL_LEVELS:
            raise ValueError(f"Invalid level '{level}'. Must be one of: {list(ORGANIZATIONAL_LEVELS.keys())}")
        
        # Récupération du parent si spécifié
        parent_unit = None
        if parent_id:
            parent_unit = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.id == parent_id,
                OrganizationalUnit.employer_id == employer_id
            ).first()
            if not parent_unit:
                raise ValueError(f"Parent unit {parent_id} not found for employer {employer_id}")
        
        # Validation de l'ordre hiérarchique
        if not OrganizationalService.validate_hierarchy_order(parent_unit, level):
            expected_levels = []
            if parent_unit:
                parent_order = ORGANIZATIONAL_LEVELS[parent_unit.level]
                expected_level = next(
                    (k for k, v in ORGANIZATIONAL_LEVELS.items() if v == parent_order + 1),
                    None
                )
                if expected_level:
                    expected_levels.append(expected_level)
            else:
                expected_levels.append('etablissement')
            
            raise ValueError(
                f"Invalid hierarchy order. Level '{level}' cannot be child of "
                f"'{parent_unit.level if parent_unit else 'employer'}'. "
                f"Expected: {expected_levels}"
            )
        
        # Vérification de l'unicité du code
        existing = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.parent_id == parent_id,
            OrganizationalUnit.code == code
        ).first()
        
        if existing:
            raise ValueError(f"Code '{code}' already exists at this level")
        
        # Création de l'unité
        unit = OrganizationalUnit(
            employer_id=employer_id,
            parent_id=parent_id,
            level=level,
            level_order=ORGANIZATIONAL_LEVELS[level],
            code=code,
            name=name,
            description=description
        )
        
        db.add(unit)
        db.commit()
        db.refresh(unit)
        return unit
    
    @staticmethod
    def get_workers_in_hierarchy(
        db: Session,
        unit_id: Optional[int] = None,
        employer_id: Optional[int] = None,
        include_descendants: bool = True
    ) -> List[Worker]:
        """
        Récupère les salariés en respectant la hiérarchie stricte
        """
        
        if unit_id:
            unit = db.query(OrganizationalUnit).get(unit_id)
            if not unit:
                raise ValueError(f"Unit {unit_id} not found")
            
            # Salariés directement attachés à cette unité
            direct_workers = db.query(Worker).filter(
                Worker.organizational_unit_id == unit_id
            ).all()
            
            if include_descendants:
                # Récupérer tous les descendants dans l'ordre hiérarchique
                descendant_workers = []
                descendants = OrganizationalService.get_ordered_descendants(db, unit_id)
                
                for descendant in descendants:
                    workers = db.query(Worker).filter(
                        Worker.organizational_unit_id == descendant.id
                    ).all()
                    descendant_workers.extend(workers)
                
                return direct_workers + descendant_workers
            else:
                return direct_workers
                
        elif employer_id:
            # Tous les salariés de l'employeur (y compris ceux sans unité organisationnelle)
            return db.query(Worker).filter(
                Worker.employer_id == employer_id
            ).all()
        
        return []
    
    @staticmethod
    def get_ordered_descendants(db: Session, unit_id: int) -> List[OrganizationalUnit]:
        """
        Récupère tous les descendants dans l'ordre hiérarchique
        """
        descendants = []
        
        def collect_ordered_descendants(parent_id: int, current_level_order: int):
            # Récupérer les enfants du niveau immédiatement inférieur
            children = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.parent_id == parent_id,
                OrganizationalUnit.level_order == current_level_order + 1
            ).order_by(OrganizationalUnit.name).all()
            
            for child in children:
                descendants.append(child)
                # Récursion pour les petits-enfants
                collect_ordered_descendants(child.id, child.level_order)
        
        unit = db.query(OrganizationalUnit).get(unit_id)
        if unit:
            collect_ordered_descendants(unit_id, unit.level_order)
        
        return descendants
    
    @staticmethod
    def get_possible_child_levels(db: Session, unit_id: Optional[int] = None) -> List[str]:
        """
        Retourne les niveaux possibles pour créer un enfant
        """
        if not unit_id:
            # Pas de parent = seul 'etablissement' possible
            return ['etablissement']
        
        unit = db.query(OrganizationalUnit).get(unit_id)
        if not unit:
            return []
        
        current_order = unit.level_order
        next_order = current_order + 1
        
        # Trouver le niveau correspondant à l'ordre suivant
        next_level = next(
            (level for level, order in ORGANIZATIONAL_LEVELS.items() if order == next_order),
            None
        )
        
        return [next_level] if next_level else []
    
    @staticmethod
    def get_organization_tree(db: Session, employer_id: int) -> Dict[str, Any]:
        """
        Retourne l'arbre organisationnel complet avec les salariés
        """
        
        def build_tree_node(unit: OrganizationalUnit) -> Dict[str, Any]:
            # Salariés directement attachés à cette unité
            direct_workers = db.query(Worker).filter(
                Worker.organizational_unit_id == unit.id
            ).all()
            
            # Enfants de cette unité (dans l'ordre hiérarchique) - seulement les actifs
            children_query = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.parent_id == unit.id,
                OrganizationalUnit.is_active == True
            ).order_by(OrganizationalUnit.level_order, OrganizationalUnit.name)
            
            children = [build_tree_node(child) for child in children_query.all()]
            
            return {
                "id": unit.id,
                "name": unit.name,
                "code": unit.code,
                "level": unit.level,
                "level_order": unit.level_order,
                "description": unit.description,
                "direct_workers": [
                    {
                        "id": w.id,
                        "matricule": w.matricule,
                        "nom": w.nom,
                        "prenom": w.prenom,
                        "poste": w.poste
                    } for w in direct_workers
                ],
                "children": children,
                "total_workers": len(direct_workers) + sum(child["total_workers"] for child in children)
            }
        
        # Récupérer toutes les unités racines (établissements) - seulement les actifs
        root_units = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.parent_id.is_(None),
            OrganizationalUnit.is_active == True
        ).order_by(OrganizationalUnit.name).all()
        
        # Salariés "orphelins" (directement sous l'employeur)
        orphan_workers = db.query(Worker).filter(
            Worker.employer_id == employer_id,
            Worker.organizational_unit_id.is_(None)
        ).all()
        
        tree = {
            "employer_id": employer_id,
            "root_units": [build_tree_node(unit) for unit in root_units],
            "orphan_workers": [
                {
                    "id": w.id,
                    "matricule": w.matricule,
                    "nom": w.nom,
                    "prenom": w.prenom,
                    "poste": w.poste
                } for w in orphan_workers
            ],
            "total_workers": sum(unit["total_workers"] for unit in [build_tree_node(u) for u in root_units]) + len(orphan_workers)
        }
        
        return tree
    
    @staticmethod
    def assign_worker_to_unit(db: Session, worker_id: int, unit_id: Optional[int] = None):
        """
        Assigne un salarié à une unité organisationnelle (ou le détache si unit_id=None)
        """
        worker = db.query(Worker).get(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")
        
        # Traçage pour l'intégrité
        old_unit_id = worker.organizational_unit_id
        logger.info(f"ASSIGNATION SALARIÉ - ID: {worker.id}, Matricule: {worker.matricule}, "
                   f"Ancien: {old_unit_id}, Nouveau: {unit_id}")
        
        if unit_id:
            unit = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.id == unit_id,
                OrganizationalUnit.employer_id == worker.employer_id
            ).first()
            if not unit:
                raise ValueError(f"Unit {unit_id} not found for this employer")
        
        worker.organizational_unit_id = unit_id
        db.commit()
        db.refresh(worker)
        
        logger.info(f"ASSIGNATION RÉUSSIE - Salarié {worker.matricule} assigné à l'unité {unit_id}")
        return worker
    
    @staticmethod
    def migrate_existing_data(db: Session, employer_id: Optional[int] = None):
        """
        Migre les données textuelles existantes vers la structure organisationnelle
        """
        
        def get_or_create_unit(employer_id: int, parent_id: Optional[int], level: str, name: str) -> OrganizationalUnit:
            """Récupère ou crée une unité organisationnelle"""
            if not name or name.strip() == "":
                return None
                
            # Chercher une unité existante
            existing = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.employer_id == employer_id,
                OrganizationalUnit.parent_id == parent_id,
                OrganizationalUnit.level == level,
                OrganizationalUnit.name == name.strip()
            ).first()
            
            if existing:
                return existing
            
            # Créer une nouvelle unité
            try:
                return OrganizationalService.create_organizational_unit(
                    db=db,
                    employer_id=employer_id,
                    level=level,
                    name=name.strip(),
                    code=name.strip().upper().replace(" ", "_")[:20],  # Code généré
                    parent_id=parent_id
                )
            except ValueError:
                # En cas d'erreur (ordre hiérarchique), ignorer
                return None
        
        # Filtrer par employeur si spécifié
        query = db.query(Worker)
        if employer_id:
            query = query.filter(Worker.employer_id == employer_id)
        
        workers = query.all()
        
        migrated_count = 0
        
        for worker in workers:
            # Ignorer les salariés déjà migrés
            if worker.organizational_unit_id:
                continue
            
            # Analyser la structure existante du salarié
            parent_unit = None
            
            # Créer les niveaux dans l'ordre strict
            if worker.etablissement:
                parent_unit = get_or_create_unit(
                    employer_id=worker.employer_id,
                    parent_id=None,
                    level='etablissement',
                    name=worker.etablissement
                )
            
            if worker.departement and parent_unit:
                parent_unit = get_or_create_unit(
                    employer_id=worker.employer_id,
                    parent_id=parent_unit.id,
                    level='departement',
                    name=worker.departement
                )
            
            if worker.service and parent_unit:
                parent_unit = get_or_create_unit(
                    employer_id=worker.employer_id,
                    parent_id=parent_unit.id,
                    level='service',
                    name=worker.service
                )
            
            # Attacher le salarié au niveau le plus bas créé
            if parent_unit:
                worker.organizational_unit_id = parent_unit.id
                migrated_count += 1
        
        db.commit()
        return migrated_count