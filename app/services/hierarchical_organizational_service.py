"""
Service pour la gestion hiÃ©rarchique organisationnelle en cascade.
ImplÃ©mente toutes les opÃ©rations CRUD avec validation des contraintes hiÃ©rarchiques.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from datetime import datetime, timezone
import logging

from ..models import OrganizationalNode, Employer, Worker

logger = logging.getLogger(__name__)


class HierarchicalOrganizationalService:
    """Service pour la gestion de la hiÃ©rarchie organisationnelle"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================
    # MÃ‰THODES PRINCIPALES CRUD
    # ==========================================
    
    def get_organizational_tree(self, employer_id: int) -> List[Dict[str, Any]]:
        """
        RÃ©cupÃ¨re l'arbre hiÃ©rarchique complet pour un employeur.
        
        Args:
            employer_id: ID de l'employeur
            
        Returns:
            Liste des nÅ“uds organisationnels structurÃ©s en arbre
        """
        try:
            # RÃ©cupÃ©rer tous les nÅ“uds actifs pour cet employeur
            nodes = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.employer_id == employer_id,
                OrganizationalNode.is_active == True
            ).order_by(
                OrganizationalNode.level,
                OrganizationalNode.sort_order,
                OrganizationalNode.name
            ).all()
            
            logger.info(f"RÃ©cupÃ©ration de {len(nodes)} nÅ“uds pour l'employeur {employer_id}")
            
            # Construire la structure arborescente
            return self._build_tree_structure(nodes)
            
        except Exception as e:
            logger.error(f"Erreur lors de la rÃ©cupÃ©ration de l'arbre organisationnel: {e}")
            raise
    
    def create_node(
        self, 
        employer_id: int, 
        parent_id: Optional[int],
        level: str,
        name: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: int = 0,
        user_id: Optional[int] = None
    ) -> OrganizationalNode:
        """
        CrÃ©e un nouveau nÅ“ud organisationnel avec validation hiÃ©rarchique.
        
        Args:
            employer_id: ID de l'employeur
            parent_id: ID du parent (None pour Ã©tablissement)
            level: Niveau hiÃ©rarchique ('etablissement', 'departement', 'service', 'unite')
            name: Nom du nÅ“ud
            code: Code optionnel
            description: Description optionnelle
            sort_order: Ordre de tri
            user_id: ID de l'utilisateur crÃ©ateur
            
        Returns:
            Le nÅ“ud crÃ©Ã©
            
        Raises:
            ValueError: Si la validation hiÃ©rarchique Ã©choue
        """
        try:
            # Validation hiÃ©rarchique
            self._validate_hierarchy(employer_id, parent_id, level)
            
            # VÃ©rification d'unicitÃ© du nom
            self._check_name_uniqueness(employer_id, parent_id, name)
            
            # CrÃ©ation du nÅ“ud
            node = OrganizationalNode(
                employer_id=employer_id,
                parent_id=parent_id,
                level=level,
                name=name.strip(),
                code=code.strip() if code else None,
                description=description.strip() if description else None,
                sort_order=sort_order,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(node)
            self.db.flush()  # Pour obtenir l'ID
            
            # Calculer et mettre Ã  jour le chemin hiÃ©rarchique
            node.path = self._calculate_path(node.id)
            
            self.db.commit()
            
            logger.info(f"NÅ“ud crÃ©Ã©: {node.name} (ID: {node.id}, Level: {node.level})")
            
            return node
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de la crÃ©ation du nÅ“ud: {e}")
            raise
    
    def update_node(
        self, 
        node_id: int, 
        name: Optional[str] = None,
        code: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> OrganizationalNode:
        """
        Met Ã  jour un nÅ“ud organisationnel.
        
        Args:
            node_id: ID du nÅ“ud Ã  mettre Ã  jour
            name: Nouveau nom (optionnel)
            code: Nouveau code (optionnel)
            description: Nouvelle description (optionnelle)
            sort_order: Nouvel ordre de tri (optionnel)
            user_id: ID de l'utilisateur modificateur
            
        Returns:
            Le nÅ“ud mis Ã  jour
            
        Raises:
            ValueError: Si le nÅ“ud n'existe pas
        """
        try:
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"NÅ“ud {node_id} introuvable")
            
            # Mise Ã  jour des champs modifiÃ©s
            if name is not None:
                # VÃ©rifier l'unicitÃ© si le nom change
                if name.strip() != node.name:
                    self._check_name_uniqueness(node.employer_id, node.parent_id, name.strip(), exclude_id=node_id)
                node.name = name.strip()
            
            if code is not None:
                node.code = code.strip() if code else None
            
            if description is not None:
                node.description = description.strip() if description else None
            
            if sort_order is not None:
                node.sort_order = sort_order
            
            node.updated_at = datetime.now(timezone.utc)
            
            # Recalculer le chemin si le nom a changÃ©
            if name is not None and name.strip() != node.name:
                node.path = self._calculate_path(node.id)
                # Mettre Ã  jour les chemins des enfants
                self._update_children_paths(node.id)
            
            self.db.commit()
            
            logger.info(f"NÅ“ud mis Ã  jour: {node.name} (ID: {node.id})")
            
            return node
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de la mise Ã  jour du nÅ“ud: {e}")
            raise
    
    def delete_node(
        self, 
        node_id: int, 
        force: bool = False,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Supprime un nÅ“ud organisationnel (suppression logique).
        
        Args:
            node_id: ID du nÅ“ud Ã  supprimer
            force: Si True, supprime mÃªme avec des enfants
            user_id: ID de l'utilisateur suppresseur
            
        Returns:
            True si la suppression a rÃ©ussi
            
        Raises:
            ValueError: Si le nÅ“ud a des enfants et force=False
        """
        try:
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"NÅ“ud {node_id} introuvable")
            
            # VÃ©rifier les enfants
            children_count = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.parent_id == node_id,
                OrganizationalNode.is_active == True
            ).count()
            
            if children_count > 0 and not force:
                raise ValueError(f"Impossible de supprimer le nÅ“ud: il a {children_count} enfant(s)")
            
            # VÃ©rifier les affectations de salariÃ©s
            workers_count = self._count_assigned_workers(node_id)
            if workers_count > 0 and not force:
                raise ValueError(f"Impossible de supprimer le nÅ“ud: {workers_count} salariÃ©(s) y sont affectÃ©s")
            
            if force and children_count > 0:
                # Suppression en cascade des enfants
                self._deactivate_children_recursive(node_id)
            
            # Suppression logique
            node.is_active = False
            node.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.info(f"NÅ“ud supprimÃ©: {node.name} (ID: {node.id})")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de la suppression du nÅ“ud: {e}")
            raise
    
    def move_node(
        self, 
        node_id: int, 
        new_parent_id: Optional[int],
        user_id: Optional[int] = None
    ) -> OrganizationalNode:
        """
        DÃ©place un nÅ“ud vers un nouveau parent.
        
        Args:
            node_id: ID du nÅ“ud Ã  dÃ©placer
            new_parent_id: ID du nouveau parent (None pour racine)
            user_id: ID de l'utilisateur
            
        Returns:
            Le nÅ“ud dÃ©placÃ©
            
        Raises:
            ValueError: Si le dÃ©placement crÃ©e un cycle
        """
        try:
            # Validation du dÃ©placement
            self._validate_move(node_id, new_parent_id)
            
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"NÅ“ud {node_id} introuvable")
            
            old_parent_id = node.parent_id
            
            # DÃ©terminer le nouveau niveau
            if new_parent_id is None:
                new_level = 'etablissement'
            else:
                parent = self.db.query(OrganizationalNode).filter(
                    OrganizationalNode.id == new_parent_id
                ).first()
                if not parent:
                    raise ValueError(f"Parent {new_parent_id} introuvable")
                
                level_hierarchy = {
                    'etablissement': 'departement',
                    'departement': 'service',
                    'service': 'unite'
                }
                new_level = level_hierarchy.get(parent.level)
                if not new_level:
                    raise ValueError(f"Impossible de crÃ©er un enfant pour le niveau {parent.level}")
            
            # Mise Ã  jour du nÅ“ud
            node.parent_id = new_parent_id
            node.level = new_level
            node.updated_at = datetime.now(timezone.utc)
            
            # Recalculer les chemins
            node.path = self._calculate_path(node.id)
            self._update_children_paths(node.id)
            
            self.db.commit()
            
            logger.info(f"NÅ“ud dÃ©placÃ©: {node.name} de {old_parent_id} vers {new_parent_id}")
            
            return node
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors du dÃ©placement du nÅ“ud: {e}")
            raise
    
    # ==========================================
    # MÃ‰THODES DE FILTRAGE EN CASCADE
    # ==========================================
    
    def get_cascading_options(
        self, 
        employer_id: int, 
        parent_id: Optional[int] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        RÃ©cupÃ¨re les options pour le filtrage en cascade.
        
        Args:
            employer_id: ID de l'employeur
            parent_id: ID du parent (None pour les Ã©tablissements)
            level: Niveau souhaitÃ© (optionnel, dÃ©duit du parent)
            
        Returns:
            Liste des options disponibles
        """
        try:
            if parent_id is None:
                # Retourner les Ã©tablissements (niveau racine)
                target_level = 'etablissement'
            else:
                # DÃ©terminer le niveau des enfants
                parent = self.db.query(OrganizationalNode).filter(
                    OrganizationalNode.id == parent_id
                ).first()
                if not parent:
                    return []
                
                level_hierarchy = {
                    'etablissement': 'departement',
                    'departement': 'service',
                    'service': 'unite'
                }
                target_level = level_hierarchy.get(parent.level)
                if not target_level:
                    return []
            
            # Si un niveau spÃ©cifique est demandÃ©, l'utiliser
            if level:
                target_level = level
            
            # RÃ©cupÃ©rer les nÅ“uds
            nodes = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.employer_id == employer_id,
                OrganizationalNode.parent_id == parent_id,
                OrganizationalNode.level == target_level,
                OrganizationalNode.is_active == True
            ).order_by(
                OrganizationalNode.sort_order,
                OrganizationalNode.name
            ).all()
            
            return [
                {
                    'id': node.id,
                    'name': node.name,
                    'code': node.code,
                    'level': node.level,
                    'parent_id': node.parent_id,
                    'path': node.path
                }
                for node in nodes
            ]
            
        except Exception as e:
            logger.error(f"Erreur lors de la rÃ©cupÃ©ration des options en cascade: {e}")
            return []
    
    # ==========================================
    # MÃ‰THODES DE VALIDATION
    # ==========================================
    
    def validate_organizational_path(
        self, 
        employer_id: int,
        etablissement_id: Optional[int] = None,
        departement_id: Optional[int] = None,
        service_id: Optional[int] = None,
        unite_id: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Valide qu'un chemin organisationnel est cohÃ©rent hiÃ©rarchiquement.
        
        Args:
            employer_id: ID de l'employeur
            etablissement_id: ID de l'Ã©tablissement
            departement_id: ID du dÃ©partement
            service_id: ID du service
            unite_id: ID de l'unitÃ©
            
        Returns:
            Tuple (is_valid, errors)
        """
        errors = []
        
        try:
            # VÃ©rifier que tous les nÅ“uds appartiennent au bon employeur
            node_ids = [id for id in [etablissement_id, departement_id, service_id, unite_id] if id is not None]
            
            if node_ids:
                nodes = self.db.query(OrganizationalNode).filter(
                    OrganizationalNode.id.in_(node_ids),
                    OrganizationalNode.employer_id == employer_id,
                    OrganizationalNode.is_active == True
                ).all()
                
                if len(nodes) != len(node_ids):
                    errors.append("Un ou plusieurs nÅ“uds n'existent pas ou n'appartiennent pas Ã  cet employeur")
                    return False, errors
                
                # CrÃ©er un mapping pour validation
                nodes_by_id = {node.id: node for node in nodes}
                
                # Validation hiÃ©rarchique
                if departement_id and etablissement_id:
                    dept = nodes_by_id.get(departement_id)
                    if dept and dept.parent_id != etablissement_id:
                        errors.append("Le dÃ©partement ne correspond pas Ã  l'Ã©tablissement")
                
                if service_id and departement_id:
                    service = nodes_by_id.get(service_id)
                    if service and service.parent_id != departement_id:
                        errors.append("Le service ne correspond pas au dÃ©partement")
                
                if unite_id and service_id:
                    unite = nodes_by_id.get(unite_id)
                    if unite and unite.parent_id != service_id:
                        errors.append("L'unitÃ© ne correspond pas au service")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation du chemin organisationnel: {e}")
            return False, [f"Erreur de validation: {str(e)}"]
    
    # ==========================================
    # MÃ‰THODES PRIVÃ‰ES
    # ==========================================
    
    def _build_tree_structure(self, nodes: List[OrganizationalNode]) -> List[Dict[str, Any]]:
        """Construit la structure arborescente Ã  partir d'une liste de nÅ“uds"""
        # CrÃ©er un mapping des nÅ“uds par ID
        nodes_by_id = {node.id: self._node_to_dict(node) for node in nodes}
        
        # Ajouter les enfants Ã  chaque nÅ“ud
        for node in nodes:
            node_dict = nodes_by_id[node.id]
            node_dict['children'] = []
        
        # Construire les relations parent-enfant
        root_nodes = []
        for node in nodes:
            node_dict = nodes_by_id[node.id]
            
            if node.parent_id is None:
                # NÅ“ud racine
                root_nodes.append(node_dict)
            else:
                # NÅ“ud enfant
                parent = nodes_by_id.get(node.parent_id)
                if parent:
                    parent['children'].append(node_dict)
        
        return root_nodes
    
    def _node_to_dict(self, node: OrganizationalNode) -> Dict[str, Any]:
        """Convertit un nÅ“ud en dictionnaire"""
        return {
            'id': node.id,
            'employer_id': node.employer_id,
            'parent_id': node.parent_id,
            'level': node.level,
            'name': node.name,
            'code': node.code,
            'description': node.description,
            'path': node.path,
            'sort_order': node.sort_order,
            'is_active': node.is_active,
            'created_at': node.created_at.isoformat() if node.created_at else None,
            'updated_at': node.updated_at.isoformat() if node.updated_at else None,
            'children': []  # Sera rempli par _build_tree_structure
        }
    
    def _validate_hierarchy(self, employer_id: int, parent_id: Optional[int], level: str):
        """Valide la cohÃ©rence hiÃ©rarchique"""
        # VÃ©rifier que le niveau est valide
        valid_levels = ['etablissement', 'departement', 'service', 'unite']
        if level not in valid_levels:
            raise ValueError(f"Niveau invalide: {level}")
        
        # RÃ¨gles hiÃ©rarchiques
        if level == 'etablissement' and parent_id is not None:
            raise ValueError("Un Ã©tablissement ne peut pas avoir de parent")
        
        if level != 'etablissement' and parent_id is None:
            raise ValueError(f"Un {level} doit avoir un parent")
        
        if parent_id is not None:
            # VÃ©rifier que le parent existe et appartient au bon employeur
            parent = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == parent_id,
                OrganizationalNode.employer_id == employer_id,
                OrganizationalNode.is_active == True
            ).first()
            
            if not parent:
                raise ValueError("Parent introuvable ou inactif")
            
            # VÃ©rifier la cohÃ©rence des niveaux
            expected_parent_levels = {
                'departement': 'etablissement',
                'service': 'departement',
                'unite': 'service'
            }
            
            expected_parent_level = expected_parent_levels.get(level)
            if expected_parent_level and parent.level != expected_parent_level:
                raise ValueError(f"Un {level} doit avoir un parent de niveau {expected_parent_level}")
    
    def _check_name_uniqueness(self, employer_id: int, parent_id: Optional[int], name: str, exclude_id: Optional[int] = None):
        """VÃ©rifie l'unicitÃ© du nom dans le contexte parent"""
        query = self.db.query(OrganizationalNode).filter(
            OrganizationalNode.employer_id == employer_id,
            OrganizationalNode.parent_id == parent_id,
            OrganizationalNode.name == name,
            OrganizationalNode.is_active == True
        )
        
        if exclude_id:
            query = query.filter(OrganizationalNode.id != exclude_id)
        
        existing = query.first()
        if existing:
            parent_name = "racine" if parent_id is None else f"parent {parent_id}"
            raise ValueError(f"Un nÅ“ud avec le nom '{name}' existe dÃ©jÃ  sous {parent_name}")
    
    def _validate_move(self, node_id: int, new_parent_id: Optional[int]):
        """Valide qu'un dÃ©placement ne crÃ©e pas de cycle"""
        if new_parent_id is None:
            return  # DÃ©placement vers la racine, pas de cycle possible
        
        # VÃ©rifier qu'on ne dÃ©place pas un nÅ“ud vers un de ses descendants
        current_parent_id = new_parent_id
        visited = set()
        
        while current_parent_id is not None:
            if current_parent_id == node_id:
                raise ValueError("DÃ©placement impossible: cela crÃ©erait un cycle")
            
            if current_parent_id in visited:
                # Cycle dÃ©tectÃ© dans la structure existante
                break
            
            visited.add(current_parent_id)
            
            parent = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == current_parent_id
            ).first()
            
            if not parent:
                break
            
            current_parent_id = parent.parent_id
    
    def _calculate_path(self, node_id: int) -> str:
        """Calcule le chemin hiÃ©rarchique complet d'un nÅ“ud"""
        path_parts = []
        current_id = node_id
        visited = set()
        
        while current_id is not None:
            if current_id in visited:
                # Cycle dÃ©tectÃ©
                break
            
            visited.add(current_id)
            
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == current_id
            ).first()
            
            if not node:
                break
            
            path_parts.insert(0, node.name)
            current_id = node.parent_id
        
        return " > ".join(path_parts)
    
    def _update_children_paths(self, parent_id: int):
        """Met Ã  jour rÃ©cursivement les chemins des enfants"""
        children = self.db.query(OrganizationalNode).filter(
            OrganizationalNode.parent_id == parent_id,
            OrganizationalNode.is_active == True
        ).all()
        
        for child in children:
            child.path = self._calculate_path(child.id)
            child.updated_at = datetime.now(timezone.utc)
            # RÃ©cursion pour les petits-enfants
            self._update_children_paths(child.id)
    
    def get_node_deletion_info(self, node_id: int) -> Dict[str, Any]:
        """
        RÃ©cupÃ¨re les informations nÃ©cessaires pour la suppression d'un nÅ“ud.
        
        Args:
            node_id: ID du nÅ“ud
            
        Returns:
            Dictionnaire avec les informations de suppression
        """
        try:
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"NÅ“ud {node_id} introuvable")
            
            # Compter les enfants
            children_count = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.parent_id == node_id,
                OrganizationalNode.is_active == True
            ).count()
            
            # Compter les salariÃ©s affectÃ©s
            workers_count = self._count_assigned_workers(node_id)
            
            # DÃ©terminer si la suppression est possible
            can_delete = children_count == 0 and workers_count == 0
            
            return {
                'node_id': node_id,
                'node_name': node.name,
                'node_level': node.level,
                'children_count': children_count,
                'workers_count': workers_count,
                'can_delete': can_delete,
                'requires_force': not can_delete,
                'warnings': self._get_deletion_warnings(children_count, workers_count)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la rÃ©cupÃ©ration des infos de suppression: {e}")
            raise
    
    def _get_deletion_warnings(self, children_count: int, workers_count: int) -> List[str]:
        """GÃ©nÃ¨re les avertissements pour la suppression"""
        warnings = []
        
        if children_count > 0:
            warnings.append(f"Cette structure contient {children_count} sous-structure(s)")
        
        if workers_count > 0:
            warnings.append(f"{workers_count} salariÃ©(s) sont affectÃ©s Ã  cette structure")
        
        if not warnings:
            warnings.append("Cette structure peut Ãªtre supprimÃ©e en toute sÃ©curitÃ©")
        
        return warnings
    
    def _count_assigned_workers(self, node_id: int) -> int:
        """Compte les salariÃ©s affectÃ©s Ã  ce nÅ“ud organisationnel"""
        try:
            # RÃ©cupÃ©rer le nÅ“ud pour connaÃ®tre son niveau
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                return 0
            
            # Compter les salariÃ©s selon le niveau du nÅ“ud
            count = 0
            
            if node.level == 'etablissement':
                count = self.db.query(Worker).filter(
                    Worker.etablissement == str(node_id)
                ).count()
            elif node.level == 'departement':
                count = self.db.query(Worker).filter(
                    Worker.departement == str(node_id)
                ).count()
            elif node.level == 'service':
                count = self.db.query(Worker).filter(
                    Worker.service == str(node_id)
                ).count()
            elif node.level == 'unite':
                count = self.db.query(Worker).filter(
                    Worker.unite == str(node_id)
                ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Erreur lors du comptage des salariÃ©s: {e}")
            return 0
    
    def _deactivate_children_recursive(self, parent_id: int):
        """DÃ©sactive rÃ©cursivement tous les enfants d'un nÅ“ud"""
        children = self.db.query(OrganizationalNode).filter(
            OrganizationalNode.parent_id == parent_id,
            OrganizationalNode.is_active == True
        ).all()
        
        for child in children:
            child.is_active = False
            child.updated_at = datetime.now(timezone.utc)
            # RÃ©cursion pour les petits-enfants
            self._deactivate_children_recursive(child.id)


