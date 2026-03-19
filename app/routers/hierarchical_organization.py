"""
Router pour la gestion hiérarchique organisationnelle en cascade.
Fournit tous les endpoints pour les opérations CRUD et le filtrage en cascade.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..config.config import get_db
from ..services.hierarchical_organizational_service import HierarchicalOrganizationalService
from ..schemas import (
    OrganizationalNodeOut, 
    OrganizationalNodeCreate, 
    OrganizationalNodeUpdate,
    OrganizationalTreeOut,
    CascadingOptionsOut,
    OrganizationalPathValidation,
    OrganizationalPathValidationResult,
    OrganizationalMoveRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employers/{employer_id}/hierarchical-organization", 
    tags=["hierarchical-organization"]
)


@router.get("/tree")
def get_organizational_tree(
    employer_id: int = Path(..., description="ID de l'employeur"),
    db: Session = Depends(get_db)
):
    """
    Récupère l'arbre hiérarchique complet pour un employeur.
    
    Retourne tous les nœuds organisationnels structurés en arbre hiérarchique
    avec les relations parent-enfant.
    """
    try:
        service = HierarchicalOrganizationalService(db)
        tree = service.get_organizational_tree(employer_id)
        
        # Compter le nombre total de nœuds dans l'arbre
        def count_nodes(nodes):
            count = len(nodes)
            for node in nodes:
                if 'children' in node and node['children']:
                    count += count_nodes(node['children'])
            return count
        
        total_units = count_nodes(tree)
        
        return {
            "tree": tree,
            "total_units": total_units
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'arbre organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cascading-options", response_model=List[CascadingOptionsOut])
def get_cascading_options(
    employer_id: int = Path(..., description="ID de l'employeur"),
    parent_id: Optional[int] = Query(None, description="ID du parent (None pour les établissements)"),
    level: Optional[str] = Query(None, description="Niveau souhaité (optionnel)"),
    db: Session = Depends(get_db)
):
    """
    Récupère les options pour le filtrage en cascade.
    
    - Si parent_id est None, retourne les établissements
    - Sinon, retourne les enfants directs du parent spécifié
    """
    try:
        service = HierarchicalOrganizationalService(db)
        options = service.get_cascading_options(employer_id, parent_id, level)
        
        return [CascadingOptionsOut(**option) for option in options]
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des options en cascade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nodes", response_model=OrganizationalNodeOut)
def create_organizational_node(
    employer_id: int = Path(..., description="ID de l'employeur"),
    data: OrganizationalNodeCreate = ...,
    db: Session = Depends(get_db)
):
    """
    Crée un nouveau nœud organisationnel.
    
    Valide automatiquement la cohérence hiérarchique et l'unicité du nom.
    """
    try:
        service = HierarchicalOrganizationalService(db)
        node = service.create_node(
            employer_id=employer_id,
            parent_id=data.parent_id,
            level=data.level,
            name=data.name,
            code=data.code,
            description=data.description,
            sort_order=data.sort_order
        )
        
        return OrganizationalNodeOut.from_orm(node)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la création du nœud organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nodes/{node_id}", response_model=OrganizationalNodeOut)
def update_organizational_node(
    employer_id: int = Path(..., description="ID de l'employeur"),
    node_id: int = Path(..., description="ID du nœud à mettre à jour"),
    data: OrganizationalNodeUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Met à jour un nœud organisationnel.
    
    Seuls les champs fournis sont mis à jour. Valide l'unicité du nom si modifié.
    """
    try:
        service = HierarchicalOrganizationalService(db)
        node = service.update_node(
            node_id=node_id,
            name=data.name,
            code=data.code,
            description=data.description,
            sort_order=data.sort_order
        )
        
        return OrganizationalNodeOut.from_orm(node)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du nœud organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nodes/{node_id}")
def delete_organizational_node(
    employer_id: int = Path(..., description="ID de l'employeur"),
    node_id: int = Path(..., description="ID du nœud à supprimer"),
    force: bool = Query(False, description="Forcer la suppression même avec des enfants ou salariés"),
    db: Session = Depends(get_db)
):
    """
    Supprime un nœud organisationnel (suppression logique).
    
    - Par défaut, refuse de supprimer un nœud avec des enfants ou des salariés affectés
    - Avec force=True, supprime récursivement tous les enfants (les salariés seront désaffectés)
    
    Règles de gestion:
    - Interdit la suppression si la structure contient des sous-structures (sauf force=True)
    - Interdit la suppression si des salariés y sont rattachés (sauf force=True)
    """
    try:
        service = HierarchicalOrganizationalService(db)
        success = service.delete_node(node_id=node_id, force=force)
        
        if success:
            return {"message": "Nœud supprimé avec succès"}
        else:
            raise HTTPException(status_code=500, detail="Échec de la suppression")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du nœud organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}/deletion-info")
def get_node_deletion_info(
    employer_id: int = Path(..., description="ID de l'employeur"),
    node_id: int = Path(..., description="ID du nœud"),
    db: Session = Depends(get_db)
):
    """
    Récupère les informations nécessaires pour la suppression d'un nœud.
    
    Retourne:
    - Nombre de sous-structures
    - Nombre de salariés affectés
    - Si la suppression est possible sans force
    - Avertissements éventuels
    """
    try:
        service = HierarchicalOrganizationalService(db)
        info = service.get_node_deletion_info(node_id)
        return info
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos de suppression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nodes/{node_id}/move", response_model=OrganizationalNodeOut)
def move_organizational_node(
    employer_id: int = Path(..., description="ID de l'employeur"),
    node_id: int = Path(..., description="ID du nœud à déplacer"),
    move_data: OrganizationalMoveRequest = ...,
    db: Session = Depends(get_db)
):
    """
    Déplace un nœud vers un nouveau parent.
    
    Valide automatiquement qu'aucun cycle n'est créé et met à jour
    les niveaux et chemins hiérarchiques.
    """
    try:
        service = HierarchicalOrganizationalService(db)
        node = service.move_node(
            node_id=node_id,
            new_parent_id=move_data.new_parent_id
        )
        
        return OrganizationalNodeOut.from_orm(node)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors du déplacement du nœud organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-path", response_model=OrganizationalPathValidationResult)
def validate_organizational_path(
    employer_id: int = Path(..., description="ID de l'employeur"),
    path_data: OrganizationalPathValidation = ...,
    db: Session = Depends(get_db)
):
    """
    Valide qu'un chemin organisationnel est cohérent hiérarchiquement.
    
    Vérifie que tous les nœuds existent, appartiennent au bon employeur
    et respectent la hiérarchie parent-enfant.
    """
    try:
        service = HierarchicalOrganizationalService(db)
        is_valid, errors = service.validate_organizational_path(
            employer_id=employer_id,
            etablissement_id=path_data.etablissement_id,
            departement_id=path_data.departement_id,
            service_id=path_data.service_id,
            unite_id=path_data.unite_id
        )
        
        return OrganizationalPathValidationResult(
            is_valid=is_valid,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation du chemin organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}", response_model=OrganizationalNodeOut)
def get_organizational_node(
    employer_id: int = Path(..., description="ID de l'employeur"),
    node_id: int = Path(..., description="ID du nœud"),
    db: Session = Depends(get_db)
):
    """
    Récupère un nœud organisationnel spécifique.
    """
    try:
        from ..models import OrganizationalNode
        
        node = db.query(OrganizationalNode).filter(
            OrganizationalNode.id == node_id,
            OrganizationalNode.employer_id == employer_id,
            OrganizationalNode.is_active == True
        ).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="Nœud organisationnel introuvable")
        
        return OrganizationalNodeOut.from_orm(node)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du nœud organisationnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/levels/{level}", response_model=List[CascadingOptionsOut])
def get_nodes_by_level(
    employer_id: int = Path(..., description="ID de l'employeur"),
    level: str = Path(..., description="Niveau hiérarchique"),
    active_only: bool = Query(True, description="Inclure seulement les nœuds actifs"),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les nœuds d'un niveau hiérarchique spécifique.
    
    Utile pour les interfaces de filtrage et de sélection.
    """
    try:
        from ..models import OrganizationalNode
        
        # Valider le niveau
        valid_levels = ['etablissement', 'departement', 'service', 'unite']
        if level not in valid_levels:
            raise HTTPException(status_code=400, detail=f"Niveau invalide. Niveaux valides: {valid_levels}")
        
        query = db.query(OrganizationalNode).filter(
            OrganizationalNode.employer_id == employer_id,
            OrganizationalNode.level == level
        )
        
        if active_only:
            query = query.filter(OrganizationalNode.is_active == True)
        
        nodes = query.order_by(
            OrganizationalNode.sort_order,
            OrganizationalNode.name
        ).all()
        
        return [
            CascadingOptionsOut(
                id=node.id,
                name=node.name,
                code=node.code,
                level=node.level,
                parent_id=node.parent_id,
                path=node.path
            )
            for node in nodes
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des nœuds par niveau: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_organizational_nodes(
    employer_id: int = Path(..., description="ID de l'employeur"),
    query: str = Query(..., min_length=1, description="Terme de recherche"),
    level: Optional[str] = Query(None, description="Filtrer par niveau"),
    active_only: bool = Query(True, description="Inclure seulement les nœuds actifs"),
    db: Session = Depends(get_db)
):
    """
    Recherche dans les nœuds organisationnels par nom ou code.
    
    Supporte la recherche partielle et le filtrage par niveau.
    """
    try:
        from ..models import OrganizationalNode
        from sqlalchemy import or_
        
        db_query = db.query(OrganizationalNode).filter(
            OrganizationalNode.employer_id == employer_id
        )
        
        if active_only:
            db_query = db_query.filter(OrganizationalNode.is_active == True)
        
        if level:
            valid_levels = ['etablissement', 'departement', 'service', 'unite']
            if level not in valid_levels:
                raise HTTPException(status_code=400, detail=f"Niveau invalide. Niveaux valides: {valid_levels}")
            db_query = db_query.filter(OrganizationalNode.level == level)
        
        # Recherche dans le nom et le code
        search_term = f"%{query}%"
        db_query = db_query.filter(
            or_(
                OrganizationalNode.name.ilike(search_term),
                OrganizationalNode.code.ilike(search_term)
            )
        )
        
        nodes = db_query.order_by(
            OrganizationalNode.level,
            OrganizationalNode.sort_order,
            OrganizationalNode.name
        ).limit(50).all()  # Limiter les résultats
        
        return [
            {
                "id": node.id,
                "name": node.name,
                "code": node.code,
                "level": node.level,
                "parent_id": node.parent_id,
                "path": node.path,
                "is_active": node.is_active
            }
            for node in nodes
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la recherche dans les nœuds organisationnels: {e}")
        raise HTTPException(status_code=500, detail=str(e))