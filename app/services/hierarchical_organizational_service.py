"""
Service pour la gestion hiérarchique organisationnelle en cascade.
Implémente toutes les opérations CRUD avec validation des contraintes hiérarchiques.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from datetime import datetime
import logging

from ..models import OrganizationalNode, Employer, Worker

logger = logging.getLogger(__name__)


class HierarchicalOrganizationalService:
    """Service pour la gestion de la hiérarchie organisationnelle"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================
    # MÉTHODES PRINCIPALES CRUD
    # ==========================================
    
    def get_organizational_tree(self, employer_id: int) -> List[Dict[str, Any]]:
        """
        Récupère l'arbre hiérarchique complet pour un employeur.
        
        Args:
            employer_id: ID de l'employeur
            
        Returns:
            Liste des nœuds organisationnels structurés en arbre
        """
        try:
            # Récupérer tous les nœuds actifs pour cet employeur
            nodes = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.employer_id == employer_id,
                OrganizationalNode.is_active == True
            ).order_by(
                OrganizationalNode.level,
                OrganizationalNode.sort_order,
                OrganizationalNode.name
            ).all()
            
            logger.info(f"Récupération de {len(nodes)} nœuds pour l'employeur {employer_id}")
            
            # Construire la structure arborescente
            return self._build_tree_structure(nodes)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'arbre organisationnel: {e}")
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
        Crée un nouveau nœud organisationnel avec validation hiérarchique.
        
        Args:
            employer_id: ID de l'employeur
            parent_id: ID du parent (None pour établissement)
            level: Niveau hiérarchique ('etablissement', 'departement', 'service', 'unite')
            name: Nom du nœud
            code: Code optionnel
            description: Description optionnelle
            sort_order: Ordre de tri
            user_id: ID de l'utilisateur créateur
            
        Returns:
            Le nœud créé
            
        Raises:
            ValueError: Si la validation hiérarchique échoue
        """
        try:
            # Validation hiérarchique
            self._validate_hierarchy(employer_id, parent_id, level)
            
            # Vérification d'unicité du nom
            self._check_name_uniqueness(employer_id, parent_id, name)
            
            # Création du nœud
            node = OrganizationalNode(
                employer_id=employer_id,
                parent_id=parent_id,
                level=level,
                name=name.strip(),
                code=code.strip() if code else None,
                description=description.strip() if description else None,
                sort_order=sort_order,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(node)
            self.db.flush()  # Pour obtenir l'ID
            
            # Calculer et mettre à jour le chemin hiérarchique
            node.path = self._calculate_path(node.id)
            
            self.db.commit()
            
            logger.info(f"Nœud créé: {node.name} (ID: {node.id}, Level: {node.level})")
            
            return node
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de la création du nœud: {e}")
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
        Met à jour un nœud organisationnel.
        
        Args:
            node_id: ID du nœud à mettre à jour
            name: Nouveau nom (optionnel)
            code: Nouveau code (optionnel)
            description: Nouvelle description (optionnelle)
            sort_order: Nouvel ordre de tri (optionnel)
            user_id: ID de l'utilisateur modificateur
            
        Returns:
            Le nœud mis à jour
            
        Raises:
            ValueError: Si le nœud n'existe pas
        """
        try:
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"Nœud {node_id} introuvable")
            
            # Mise à jour des champs modifiés
            if name is not None:
                # Vérifier l'unicité si le nom change
                if name.strip() != node.name:
                    self._check_name_uniqueness(node.employer_id, node.parent_id, name.strip(), exclude_id=node_id)
                node.name = name.strip()
            
            if code is not None:
                node.code = code.strip() if code else None
            
            if description is not None:
                node.description = description.strip() if description else None
            
            if sort_order is not None:
                node.sort_order = sort_order
            
            node.updated_at = datetime.utcnow()
            
            # Recalculer le chemin si le nom a changé
            if name is not None and name.strip() != node.name:
                node.path = self._calculate_path(node.id)
                # Mettre à jour les chemins des enfants
                self._update_children_paths(node.id)
            
            self.db.commit()
            
            logger.info(f"Nœud mis à jour: {node.name} (ID: {node.id})")
            
            return node
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de la mise à jour du nœud: {e}")
            raise
    
    def delete_node(
        self, 
        node_id: int, 
        force: bool = False,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Supprime un nœud organisationnel (suppression logique).
        
        Args:
            node_id: ID du nœud à supprimer
            force: Si True, supprime même avec des enfants
            user_id: ID de l'utilisateur suppresseur
            
        Returns:
            True si la suppression a réussi
            
        Raises:
            ValueError: Si le nœud a des enfants et force=False
        """
        try:
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"Nœud {node_id} introuvable")
            
            # Vérifier les enfants
            children_count = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.parent_id == node_id,
                OrganizationalNode.is_active == True
            ).count()
            
            if children_count > 0 and not force:
                raise ValueError(f"Impossible de supprimer le nœud: il a {children_count} enfant(s)")
            
            # Vérifier les affectations de salariés
            workers_count = self._count_assigned_workers(node_id)
            if workers_count > 0 and not force:
                raise ValueError(f"Impossible de supprimer le nœud: {workers_count} salarié(s) y sont affectés")
            
            if force and children_count > 0:
                # Suppression en cascade des enfants
                self._deactivate_children_recursive(node_id)
            
            # Suppression logique
            node.is_active = False
            node.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Nœud supprimé: {node.name} (ID: {node.id})")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors de la suppression du nœud: {e}")
            raise
    
    def move_node(
        self, 
        node_id: int, 
        new_parent_id: Optional[int],
        user_id: Optional[int] = None
    ) -> OrganizationalNode:
        """
        Déplace un nœud vers un nouveau parent.
        
        Args:
            node_id: ID du nœud à déplacer
            new_parent_id: ID du nouveau parent (None pour racine)
            user_id: ID de l'utilisateur
            
        Returns:
            Le nœud déplacé
            
        Raises:
            ValueError: Si le déplacement crée un cycle
        """
        try:
            # Validation du déplacement
            self._validate_move(node_id, new_parent_id)
            
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"Nœud {node_id} introuvable")
            
            old_parent_id = node.parent_id
            
            # Déterminer le nouveau niveau
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
                    raise ValueError(f"Impossible de créer un enfant pour le niveau {parent.level}")
            
            # Mise à jour du nœud
            node.parent_id = new_parent_id
            node.level = new_level
            node.updated_at = datetime.utcnow()
            
            # Recalculer les chemins
            node.path = self._calculate_path(node.id)
            self._update_children_paths(node.id)
            
            self.db.commit()
            
            logger.info(f"Nœud déplacé: {node.name} de {old_parent_id} vers {new_parent_id}")
            
            return node
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur lors du déplacement du nœud: {e}")
            raise
    
    # ==========================================
    # MÉTHODES DE FILTRAGE EN CASCADE
    # ==========================================
    
    def get_cascading_options(
        self, 
        employer_id: int, 
        parent_id: Optional[int] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les options pour le filtrage en cascade.
        
        Args:
            employer_id: ID de l'employeur
            parent_id: ID du parent (None pour les établissements)
            level: Niveau souhaité (optionnel, déduit du parent)
            
        Returns:
            Liste des options disponibles
        """
        try:
            if parent_id is None:
                # Retourner les établissements (niveau racine)
                target_level = 'etablissement'
            else:
                # Déterminer le niveau des enfants
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
            
            # Si un niveau spécifique est demandé, l'utiliser
            if level:
                target_level = level
            
            # Récupérer les nœuds
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
            logger.error(f"Erreur lors de la récupération des options en cascade: {e}")
            return []
    
    # ==========================================
    # MÉTHODES DE VALIDATION
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
        Valide qu'un chemin organisationnel est cohérent hiérarchiquement.
        
        Args:
            employer_id: ID de l'employeur
            etablissement_id: ID de l'établissement
            departement_id: ID du département
            service_id: ID du service
            unite_id: ID de l'unité
            
        Returns:
            Tuple (is_valid, errors)
        """
        errors = []
        
        try:
            # Vérifier que tous les nœuds appartiennent au bon employeur
            node_ids = [id for id in [etablissement_id, departement_id, service_id, unite_id] if id is not None]
            
            if node_ids:
                nodes = self.db.query(OrganizationalNode).filter(
                    OrganizationalNode.id.in_(node_ids),
                    OrganizationalNode.employer_id == employer_id,
                    OrganizationalNode.is_active == True
                ).all()
                
                if len(nodes) != len(node_ids):
                    errors.append("Un ou plusieurs nœuds n'existent pas ou n'appartiennent pas à cet employeur")
                    return False, errors
                
                # Créer un mapping pour validation
                nodes_by_id = {node.id: node for node in nodes}
                
                # Validation hiérarchique
                if departement_id and etablissement_id:
                    dept = nodes_by_id.get(departement_id)
                    if dept and dept.parent_id != etablissement_id:
                        errors.append("Le département ne correspond pas à l'établissement")
                
                if service_id and departement_id:
                    service = nodes_by_id.get(service_id)
                    if service and service.parent_id != departement_id:
                        errors.append("Le service ne correspond pas au département")
                
                if unite_id and service_id:
                    unite = nodes_by_id.get(unite_id)
                    if unite and unite.parent_id != service_id:
                        errors.append("L'unité ne correspond pas au service")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation du chemin organisationnel: {e}")
            return False, [f"Erreur de validation: {str(e)}"]
    
    # ==========================================
    # MÉTHODES PRIVÉES
    # ==========================================
    
    def _build_tree_structure(self, nodes: List[OrganizationalNode]) -> List[Dict[str, Any]]:
        """Construit la structure arborescente à partir d'une liste de nœuds"""
        # Créer un mapping des nœuds par ID
        nodes_by_id = {node.id: self._node_to_dict(node) for node in nodes}
        
        # Ajouter les enfants à chaque nœud
        for node in nodes:
            node_dict = nodes_by_id[node.id]
            node_dict['children'] = []
        
        # Construire les relations parent-enfant
        root_nodes = []
        for node in nodes:
            node_dict = nodes_by_id[node.id]
            
            if node.parent_id is None:
                # Nœud racine
                root_nodes.append(node_dict)
            else:
                # Nœud enfant
                parent = nodes_by_id.get(node.parent_id)
                if parent:
                    parent['children'].append(node_dict)
        
        return root_nodes
    
    def _node_to_dict(self, node: OrganizationalNode) -> Dict[str, Any]:
        """Convertit un nœud en dictionnaire"""
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
        """Valide la cohérence hiérarchique"""
        # Vérifier que le niveau est valide
        valid_levels = ['etablissement', 'departement', 'service', 'unite']
        if level not in valid_levels:
            raise ValueError(f"Niveau invalide: {level}")
        
        # Règles hiérarchiques
        if level == 'etablissement' and parent_id is not None:
            raise ValueError("Un établissement ne peut pas avoir de parent")
        
        if level != 'etablissement' and parent_id is None:
            raise ValueError(f"Un {level} doit avoir un parent")
        
        if parent_id is not None:
            # Vérifier que le parent existe et appartient au bon employeur
            parent = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == parent_id,
                OrganizationalNode.employer_id == employer_id,
                OrganizationalNode.is_active == True
            ).first()
            
            if not parent:
                raise ValueError("Parent introuvable ou inactif")
            
            # Vérifier la cohérence des niveaux
            expected_parent_levels = {
                'departement': 'etablissement',
                'service': 'departement',
                'unite': 'service'
            }
            
            expected_parent_level = expected_parent_levels.get(level)
            if expected_parent_level and parent.level != expected_parent_level:
                raise ValueError(f"Un {level} doit avoir un parent de niveau {expected_parent_level}")
    
    def _check_name_uniqueness(self, employer_id: int, parent_id: Optional[int], name: str, exclude_id: Optional[int] = None):
        """Vérifie l'unicité du nom dans le contexte parent"""
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
            raise ValueError(f"Un nœud avec le nom '{name}' existe déjà sous {parent_name}")
    
    def _validate_move(self, node_id: int, new_parent_id: Optional[int]):
        """Valide qu'un déplacement ne crée pas de cycle"""
        if new_parent_id is None:
            return  # Déplacement vers la racine, pas de cycle possible
        
        # Vérifier qu'on ne déplace pas un nœud vers un de ses descendants
        current_parent_id = new_parent_id
        visited = set()
        
        while current_parent_id is not None:
            if current_parent_id == node_id:
                raise ValueError("Déplacement impossible: cela créerait un cycle")
            
            if current_parent_id in visited:
                # Cycle détecté dans la structure existante
                break
            
            visited.add(current_parent_id)
            
            parent = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == current_parent_id
            ).first()
            
            if not parent:
                break
            
            current_parent_id = parent.parent_id
    
    def _calculate_path(self, node_id: int) -> str:
        """Calcule le chemin hiérarchique complet d'un nœud"""
        path_parts = []
        current_id = node_id
        visited = set()
        
        while current_id is not None:
            if current_id in visited:
                # Cycle détecté
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
        """Met à jour récursivement les chemins des enfants"""
        children = self.db.query(OrganizationalNode).filter(
            OrganizationalNode.parent_id == parent_id,
            OrganizationalNode.is_active == True
        ).all()
        
        for child in children:
            child.path = self._calculate_path(child.id)
            child.updated_at = datetime.utcnow()
            # Récursion pour les petits-enfants
            self._update_children_paths(child.id)
    
    def get_node_deletion_info(self, node_id: int) -> Dict[str, Any]:
        """
        Récupère les informations nécessaires pour la suppression d'un nœud.
        
        Args:
            node_id: ID du nœud
            
        Returns:
            Dictionnaire avec les informations de suppression
        """
        try:
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                raise ValueError(f"Nœud {node_id} introuvable")
            
            # Compter les enfants
            children_count = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.parent_id == node_id,
                OrganizationalNode.is_active == True
            ).count()
            
            # Compter les salariés affectés
            workers_count = self._count_assigned_workers(node_id)
            
            # Déterminer si la suppression est possible
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
            logger.error(f"Erreur lors de la récupération des infos de suppression: {e}")
            raise
    
    def _get_deletion_warnings(self, children_count: int, workers_count: int) -> List[str]:
        """Génère les avertissements pour la suppression"""
        warnings = []
        
        if children_count > 0:
            warnings.append(f"Cette structure contient {children_count} sous-structure(s)")
        
        if workers_count > 0:
            warnings.append(f"{workers_count} salarié(s) sont affectés à cette structure")
        
        if not warnings:
            warnings.append("Cette structure peut être supprimée en toute sécurité")
        
        return warnings
    
    def _count_assigned_workers(self, node_id: int) -> int:
        """Compte les salariés affectés à ce nœud organisationnel"""
        try:
            # Récupérer le nœud pour connaître son niveau
            node = self.db.query(OrganizationalNode).filter(
                OrganizationalNode.id == node_id
            ).first()
            
            if not node:
                return 0
            
            # Compter les salariés selon le niveau du nœud
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
            logger.error(f"Erreur lors du comptage des salariés: {e}")
            return 0
    
    def _deactivate_children_recursive(self, parent_id: int):
        """Désactive récursivement tous les enfants d'un nœud"""
        children = self.db.query(OrganizationalNode).filter(
            OrganizationalNode.parent_id == parent_id,
            OrganizationalNode.is_active == True
        ).all()
        
        for child in children:
            child.is_active = False
            child.updated_at = datetime.utcnow()
            # Récursion pour les petits-enfants
            self._deactivate_children_recursive(child.id)