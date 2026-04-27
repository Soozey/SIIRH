# app/services/organizational_service.py
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models import OrganizationalUnit, Worker, Employer, ORGANIZATIONAL_LEVELS, OrgUnitEvent
from ..config.config import get_db
from .master_data_service import build_worker_reporting_payload, sync_worker_master_data
from .recruitment_assistant_service import json_dump

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
    def _collect_parent_chain_ids(
        db: Session,
        *,
        employer_id: int,
        start_parent_id: Optional[int],
    ) -> List[int]:
        chain: List[int] = []
        current_parent_id = start_parent_id
        visited: set[int] = set()

        while current_parent_id is not None:
            if current_parent_id in visited:
                raise ValueError("Cycle hiérarchique détecté dans les unités organisationnelles")
            visited.add(current_parent_id)
            chain.append(current_parent_id)

            parent = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.id == current_parent_id,
                OrganizationalUnit.employer_id == employer_id,
            ).first()
            if not parent:
                raise ValueError(f"Parent unit {current_parent_id} not found for employer {employer_id}")
            current_parent_id = parent.parent_id

        return chain

    @staticmethod
    def validate_parent_assignment(
        db: Session,
        *,
        employer_id: int,
        unit_id: Optional[int],
        parent_id: Optional[int],
        level: str,
    ) -> Optional[OrganizationalUnit]:
        if parent_id is None:
            if level != 'etablissement':
                raise ValueError("Seul un établissement peut être créé ou déplacé à la racine")
            return None

        if unit_id is not None and parent_id == unit_id:
            raise ValueError("Une unité ne peut pas être son propre parent")

        parent_unit = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == parent_id,
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.is_active == True,
        ).first()
        if not parent_unit:
            raise ValueError(f"Parent unit {parent_id} not found for employer {employer_id}")

        if not OrganizationalService.validate_hierarchy_order(parent_unit, level):
            raise ValueError(
                f"Invalid hierarchy order. Level '{level}' cannot be child of '{parent_unit.level}'."
            )

        if unit_id is not None:
            ancestor_ids = OrganizationalService._collect_parent_chain_ids(
                db,
                employer_id=employer_id,
                start_parent_id=parent_id,
            )
            if unit_id in ancestor_ids:
                raise ValueError("Déplacement impossible: cela créerait un cycle hiérarchique")

        return parent_unit
    
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
    def detect_cyclic_units(db: Session, employer_id: int) -> List[int]:
        units = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.is_active == True,
        ).all()
        by_id = {unit.id: unit for unit in units}
        cyclic_ids: set[int] = set()

        for unit in units:
            visited_in_chain: set[int] = set()
            current = unit
            while current is not None:
                if current.id in visited_in_chain:
                    cyclic_ids.update(visited_in_chain)
                    break
                visited_in_chain.add(current.id)
                current = by_id.get(current.parent_id) if current.parent_id is not None else None

        return sorted(cyclic_ids)

    @staticmethod
    def resolve_unit_snapshot(unit: Optional[OrganizationalUnit]) -> Dict[str, Optional[str]]:
        snapshot = {
            "etablissement": None,
            "departement": None,
            "service": None,
            "unite": None,
        }
        current = unit
        visited: set[int] = set()
        while current:
            if current.id in visited:
                logger.warning("Cycle détecté pendant resolve_unit_snapshot pour l'unité %s", current.id)
                break
            visited.add(current.id)
            if current.level in snapshot:
                snapshot[current.level] = current.name
            current = current.parent
        return snapshot

    @staticmethod
    def apply_unit_snapshot_to_worker(worker: Worker, unit: Optional[OrganizationalUnit]) -> Worker:
        snapshot = OrganizationalService.resolve_unit_snapshot(unit)
        worker.organizational_unit_id = unit.id if unit else None
        worker.etablissement = snapshot["etablissement"]
        worker.departement = snapshot["departement"]
        worker.service = snapshot["service"]
        worker.unite = snapshot["unite"]
        return worker

    @staticmethod
    def resolve_unit_reference(
        db: Session,
        *,
        employer_id: int,
        raw_value: Any,
        level: Optional[str] = None,
    ) -> Optional[OrganizationalUnit]:
        if raw_value in (None, "", 0, "0"):
            return None
        query = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.is_active == True,
        )
        if level:
            query = query.filter(OrganizationalUnit.level == level)
        text = str(raw_value).strip()
        if text.isdigit():
            return query.filter(OrganizationalUnit.id == int(text)).first()
        return query.filter(OrganizationalUnit.name == text).first()

    @staticmethod
    def resolve_selected_unit(
        db: Session,
        *,
        employer_id: int,
        organizational_unit_id: Any = None,
        etablissement: Any = None,
        departement: Any = None,
        service: Any = None,
        unite: Any = None,
    ) -> Optional[OrganizationalUnit]:
        references = [
            ("unite", unite),
            ("service", service),
            ("departement", departement),
            ("etablissement", etablissement),
        ]
        if organizational_unit_id not in (None, "", 0, "0"):
            unit = OrganizationalService.resolve_unit_reference(
                db,
                employer_id=employer_id,
                raw_value=organizational_unit_id,
            )
            if not unit:
                raise ValueError("Unité organisationnelle introuvable")
            return unit
        for level, raw_value in references:
            unit = OrganizationalService.resolve_unit_reference(
                db,
                employer_id=employer_id,
                raw_value=raw_value,
                level=level,
            )
            if unit:
                return unit
        return None

    @staticmethod
    def synchronize_worker_organization(db: Session, worker: Worker) -> Worker:
        unit = None
        if worker.organizational_unit_id:
            unit = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.id == worker.organizational_unit_id,
                OrganizationalUnit.employer_id == worker.employer_id,
            ).first()
        OrganizationalService.apply_unit_snapshot_to_worker(worker, unit)
        sync_worker_master_data(db, worker)
        return worker

    @staticmethod
    def get_descendant_unit_ids(db: Session, root_unit_id: int) -> List[int]:
        units = db.query(OrganizationalUnit).all()
        by_parent: Dict[Optional[int], List[OrganizationalUnit]] = {}
        for unit in units:
            by_parent.setdefault(unit.parent_id, []).append(unit)
        collected: List[int] = [root_unit_id]
        stack = [root_unit_id]
        visited: set[int] = {root_unit_id}
        while stack:
            current = stack.pop()
            for child in by_parent.get(current, []):
                if child.id in visited:
                    logger.warning("Cycle détecté pendant get_descendant_unit_ids: root=%s child=%s", root_unit_id, child.id)
                    continue
                visited.add(child.id)
                collected.append(child.id)
                stack.append(child.id)
        return collected

    @staticmethod
    def refresh_org_references(
        db: Session,
        *,
        employer_id: int,
        root_unit_id: Optional[int],
        event_type: str,
        triggered_by_user_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        unit_ids: List[int] = []
        if root_unit_id:
            unit_ids = OrganizationalService.get_descendant_unit_ids(db, root_unit_id)
            workers = db.query(Worker).filter(
                Worker.employer_id == employer_id,
                Worker.organizational_unit_id.in_(unit_ids),
            ).all()
            for worker in workers:
                OrganizationalService.synchronize_worker_organization(db, worker)
        else:
            workers = db.query(Worker).filter(Worker.employer_id == employer_id).all()
            for worker in workers:
                OrganizationalService.synchronize_worker_organization(db, worker)
        db.add(
            OrgUnitEvent(
                employer_id=employer_id,
                org_unit_id=root_unit_id,
                event_type=event_type,
                payload_json=json_dump(payload or {"affected_worker_count": len(workers), "affected_unit_ids": unit_ids}),
                triggered_by_user_id=triggered_by_user_id,
            )
        )
        db.flush()
        return len(workers)
    
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
        visited: set[int] = set()
        
        def collect_ordered_descendants(parent_id: int, current_level_order: int):
            if parent_id in visited:
                logger.warning("Cycle détecté pendant get_ordered_descendants pour le parent %s", parent_id)
                return
            visited.add(parent_id)
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
            direct_worker_payloads = {worker.id: build_worker_reporting_payload(db, worker) for worker in direct_workers}
            
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
                        "matricule": direct_worker_payloads[w.id].get("matricule"),
                        "nom": direct_worker_payloads[w.id].get("nom"),
                        "prenom": direct_worker_payloads[w.id].get("prenom"),
                        "poste": direct_worker_payloads[w.id].get("poste"),
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

        OrganizationalService.apply_unit_snapshot_to_worker(worker, unit if unit_id else None)
        sync_worker_master_data(db, worker)
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

    @staticmethod
    def validate_parent_assignment(
        db: Session,
        *,
        employer_id: int,
        unit_id: Optional[int],
        parent_id: Optional[int],
        level: str,
    ) -> Optional[OrganizationalUnit]:
        if parent_id is None:
            if level != 'etablissement':
                raise ValueError("Seul un établissement peut être créé ou déplacé à la racine")
            return None

        if unit_id is not None and parent_id == unit_id:
            raise ValueError("Une unité ne peut pas être son propre parent")

        parent_unit = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.id == parent_id,
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.is_active == True,
        ).first()
        if not parent_unit:
            raise ValueError(f"Parent unit {parent_id} not found for employer {employer_id}")

        if not OrganizationalService.validate_hierarchy_order(parent_unit, level):
            raise ValueError(
                f"Invalid hierarchy order. Level '{level}' cannot be child of '{parent_unit.level}'."
            )

        visited: set[int] = set()
        current = parent_unit
        while current is not None:
            if current.id in visited:
                raise ValueError("Cycle hiérarchique détecté dans les unités organisationnelles")
            if unit_id is not None and current.id == unit_id:
                raise ValueError("Déplacement impossible: cela créerait un cycle hiérarchique")
            visited.add(current.id)
            current = current.parent

        return parent_unit

    @staticmethod
    def detect_cyclic_units(db: Session, employer_id: int) -> List[int]:
        units = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.is_active == True,
        ).all()
        by_id = {unit.id: unit for unit in units}
        cyclic_ids: set[int] = set()

        for unit in units:
            path: set[int] = set()
            current = unit
            while current is not None:
                if current.id in path:
                    cyclic_ids.update(path)
                    break
                path.add(current.id)
                current = by_id.get(current.parent_id) if current.parent_id is not None else None

        return sorted(cyclic_ids)

    @staticmethod
    def resolve_unit_snapshot(unit: Optional[OrganizationalUnit]) -> Dict[str, Optional[str]]:
        snapshot = {
            "etablissement": None,
            "departement": None,
            "service": None,
            "unite": None,
        }
        current = unit
        visited: set[int] = set()
        while current:
            if current.id in visited:
                logger.warning("Cycle détecté pendant resolve_unit_snapshot pour l'unité %s", current.id)
                break
            visited.add(current.id)
            if current.level in snapshot:
                snapshot[current.level] = current.name
            current = current.parent
        return snapshot

    @staticmethod
    def get_descendant_unit_ids(db: Session, root_unit_id: int) -> List[int]:
        units = db.query(OrganizationalUnit).all()
        by_parent: Dict[Optional[int], List[OrganizationalUnit]] = {}
        for unit in units:
            by_parent.setdefault(unit.parent_id, []).append(unit)

        collected: List[int] = [root_unit_id]
        stack = [root_unit_id]
        visited: set[int] = {root_unit_id}
        while stack:
            current = stack.pop()
            for child in by_parent.get(current, []):
                if child.id in visited:
                    logger.warning("Cycle détecté pendant get_descendant_unit_ids: root=%s child=%s", root_unit_id, child.id)
                    continue
                visited.add(child.id)
                collected.append(child.id)
                stack.append(child.id)
        return collected

    @staticmethod
    def get_ordered_descendants(db: Session, unit_id: int) -> List[OrganizationalUnit]:
        descendants: List[OrganizationalUnit] = []
        visited: set[int] = set()

        def collect_ordered_descendants(parent_id: int, current_level_order: int):
            if parent_id in visited:
                logger.warning("Cycle détecté pendant get_ordered_descendants pour le parent %s", parent_id)
                return
            visited.add(parent_id)
            children = db.query(OrganizationalUnit).filter(
                OrganizationalUnit.parent_id == parent_id,
                OrganizationalUnit.level_order == current_level_order + 1
            ).order_by(OrganizationalUnit.name).all()

            for child in children:
                descendants.append(child)
                collect_ordered_descendants(child.id, child.level_order)

        unit = db.query(OrganizationalUnit).get(unit_id)
        if unit:
            collect_ordered_descendants(unit_id, unit.level_order)

        return descendants

    @staticmethod
    def get_organization_tree(db: Session, employer_id: int) -> Dict[str, Any]:
        active_units = db.query(OrganizationalUnit).filter(
            OrganizationalUnit.employer_id == employer_id,
            OrganizationalUnit.is_active == True,
        ).order_by(OrganizationalUnit.level_order, OrganizationalUnit.name, OrganizationalUnit.id).all()
        units_by_id = {unit.id: unit for unit in active_units}
        children_by_parent: Dict[Optional[int], List[OrganizationalUnit]] = {}
        for unit in active_units:
            children_by_parent.setdefault(unit.parent_id, []).append(unit)
        for children in children_by_parent.values():
            children.sort(key=lambda item: (item.level_order, item.name or "", item.id))

        cyclic_unit_ids = set(OrganizationalService.detect_cyclic_units(db, employer_id))
        if cyclic_unit_ids:
            logger.warning("Cycles hiérarchiques détectés pour l'employeur %s: %s", employer_id, sorted(cyclic_unit_ids))

        def build_tree_node(unit: OrganizationalUnit, path: set[int], depth: int = 0) -> Dict[str, Any]:
            if depth > 12 or unit.id in path:
                logger.warning("Branche hiérarchique coupée pour l'unité %s", unit.id)
                return {
                    "id": unit.id,
                    "name": unit.name,
                    "code": unit.code,
                    "level": unit.level,
                    "level_order": unit.level_order,
                    "description": unit.description,
                    "direct_workers": [],
                    "children": [],
                    "total_workers": 0,
                }

            direct_workers = db.query(Worker).filter(Worker.organizational_unit_id == unit.id).all()
            direct_worker_payloads = {worker.id: build_worker_reporting_payload(db, worker) for worker in direct_workers}

            next_path = set(path)
            next_path.add(unit.id)
            children: List[Dict[str, Any]] = []
            for child in children_by_parent.get(unit.id, []):
                if child.id in next_path:
                    logger.warning("Lien cyclique ignoré: parent=%s child=%s", unit.id, child.id)
                    continue
                children.append(build_tree_node(child, next_path, depth + 1))

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
                        "matricule": direct_worker_payloads[w.id].get("matricule"),
                        "nom": direct_worker_payloads[w.id].get("nom"),
                        "prenom": direct_worker_payloads[w.id].get("prenom"),
                        "poste": direct_worker_payloads[w.id].get("poste"),
                    } for w in direct_workers
                ],
                "children": children,
                "total_workers": len(direct_workers) + sum(child["total_workers"] for child in children)
            }

        referenced_child_ids = {
            unit.id
            for unit in active_units
            if unit.parent_id is not None and unit.parent_id in units_by_id and unit.id not in cyclic_unit_ids
        }
        root_units = [
            unit
            for unit in active_units
            if unit.parent_id is None
            or unit.parent_id not in units_by_id
            or unit.id in cyclic_unit_ids
            or unit.id not in referenced_child_ids
        ]

        unique_root_units: List[OrganizationalUnit] = []
        seen_root_ids: set[int] = set()
        for unit in root_units:
            if unit.id in seen_root_ids:
                continue
            seen_root_ids.add(unit.id)
            unique_root_units.append(unit)

        orphan_workers = db.query(Worker).filter(
            Worker.employer_id == employer_id,
            Worker.organizational_unit_id.is_(None)
        ).all()
        root_nodes = [build_tree_node(unit, set()) for unit in unique_root_units]
        return {
            "employer_id": employer_id,
            "root_units": root_nodes,
            "orphan_workers": [
                {
                    "id": w.id,
                    "matricule": w.matricule,
                    "nom": w.nom,
                    "prenom": w.prenom,
                    "poste": w.poste,
                } for w in orphan_workers
            ],
            "total_workers": sum(unit["total_workers"] for unit in root_nodes) + len(orphan_workers),
        }
