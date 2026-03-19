"""
Service de synchronisation organisationnelle
Maintient la cohérence entre les structures hiérarchiques et les affectations des salariés
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from .. import models
import logging

logger = logging.getLogger(__name__)

class OrganizationalSyncService:
    """Service de synchronisation des données organisationnelles"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_worker_assignments_after_structure_change(
        self, 
        employer_id: int, 
        old_name: str, 
        new_name: str, 
        structure_type: str
    ) -> Dict[str, any]:
        """
        Synchronise les affectations des salariés après un changement de structure
        
        Args:
            employer_id: ID de l'employeur
            old_name: Ancien nom de la structure
            new_name: Nouveau nom de la structure
            structure_type: Type de structure ('etablissement', 'departement', 'service', 'unite')
        
        Returns:
            Dict avec le résumé des modifications
        """
        logger.info(f"Synchronisation {structure_type}: '{old_name}' → '{new_name}' pour employeur {employer_id}")
        
        # Récupérer tous les salariés de l'employeur
        workers = self.db.query(models.Worker).filter(
            models.Worker.employer_id == employer_id
        ).all()
        
        updated_workers = []
        
        # Mettre à jour les salariés concernés
        for worker in workers:
            current_value = getattr(worker, structure_type, None)
            
            if current_value == old_name:
                # Mettre à jour avec le nouveau nom
                setattr(worker, structure_type, new_name)
                updated_workers.append({
                    'id': worker.id,
                    'name': f"{worker.prenom} {worker.nom}",
                    'old_value': old_name,
                    'new_value': new_name
                })
                
                logger.info(f"Salarié {worker.prenom} {worker.nom}: {structure_type} '{old_name}' → '{new_name}'")
        
        # Sauvegarder les modifications
        if updated_workers:
            self.db.commit()
            logger.info(f"Synchronisation terminée: {len(updated_workers)} salarié(s) mis à jour")
        else:
            logger.info("Aucun salarié à synchroniser")
        
        return {
            'success': True,
            'structure_type': structure_type,
            'old_name': old_name,
            'new_name': new_name,
            'updated_workers_count': len(updated_workers),
            'updated_workers': updated_workers
        }
    
    def sync_all_workers_to_hierarchical_structures(self, employer_id: int) -> Dict[str, any]:
        """
        Synchronise SEULEMENT les salariés avec des affectations INVALIDES vers les structures hiérarchiques existantes
        PRÉSERVE les affectations valides existantes
        """
        logger.info(f"Synchronisation complète pour employeur {employer_id}")
        
        # Récupérer les structures hiérarchiques
        hierarchical_structures = self._get_hierarchical_structures(employer_id)
        
        # Récupérer tous les salariés
        workers = self.db.query(models.Worker).filter(
            models.Worker.employer_id == employer_id
        ).all()
        
        sync_results = {
            'etablissements': [],
            'departements': [],
            'services': [],
            'unites': []
        }
        
        # Synchroniser chaque type de structure
        for structure_type in ['etablissement', 'departement', 'service', 'unite']:
            available_structures = hierarchical_structures.get(f"{structure_type}s", [])
            
            for worker in workers:
                current_value = getattr(worker, structure_type, None)
                
                # SEULEMENT si le salarié a une valeur qui n'existe pas dans les structures hiérarchiques
                if current_value and current_value not in available_structures:
                    logger.warning(f"Affectation invalide détectée: {worker.prenom} {worker.nom} - {structure_type} = '{current_value}'")
                    logger.warning(f"Structures disponibles: {available_structures}")
                    
                    # NE PAS modifier automatiquement - laisser l'utilisateur décider
                    # Ou proposer une correspondance intelligente
                    
                    # Pour l'instant, on signale juste le problème sans modifier
                    sync_results[f"{structure_type}s"].append({
                        'worker_id': worker.id,
                        'worker_name': f"{worker.prenom} {worker.nom}",
                        'old_value': current_value,
                        'new_value': None,  # Pas de modification automatique
                        'status': 'invalid_assignment_detected',
                        'available_options': available_structures
                    })
                    
                    logger.info(f"Salarié {worker.prenom} {worker.nom}: {structure_type} '{current_value}' - AFFECTATION INVALIDE DÉTECTÉE")
        
        # NE PAS sauvegarder automatiquement - préserver les données existantes
        # self.db.commit()  # SUPPRIMÉ
        
        total_detected = sum(len(updates) for updates in sync_results.values())
        logger.info(f"Validation terminée: {total_detected} affectation(s) invalide(s) détectée(s) (AUCUNE MODIFICATION APPLIQUÉE)")
        
        return {
            'success': True,
            'employer_id': employer_id,
            'total_updated': 0,  # Aucune modification appliquée
            'total_invalid_detected': total_detected,
            'details': sync_results,
            'message': 'Validation effectuée - aucune modification automatique appliquée pour préserver les données existantes'
        }
    
    def force_sync_all_workers_to_hierarchical_structures(self, employer_id: int) -> Dict[str, any]:
        """
        FORCE la synchronisation de TOUS les salariés vers les structures hiérarchiques existantes
        ⚠️ ATTENTION: Cette méthode modifie les affectations existantes
        À utiliser seulement quand l'utilisateur confirme explicitement
        """
        logger.warning(f"SYNCHRONISATION FORCÉE pour employeur {employer_id}")
        
        # Récupérer les structures hiérarchiques
        hierarchical_structures = self._get_hierarchical_structures(employer_id)
        
        # Récupérer tous les salariés
        workers = self.db.query(models.Worker).filter(
            models.Worker.employer_id == employer_id
        ).all()
        
        sync_results = {
            'etablissements': [],
            'departements': [],
            'services': [],
            'unites': []
        }
        
        # Synchroniser chaque type de structure
        for structure_type in ['etablissement', 'departement', 'service', 'unite']:
            available_structures = hierarchical_structures.get(f"{structure_type}s", [])
            
            for worker in workers:
                current_value = getattr(worker, structure_type, None)
                
                # SEULEMENT si le salarié a une valeur qui n'existe pas dans les structures hiérarchiques
                if current_value and current_value not in available_structures:
                    logger.warning(f"Affectation invalide détectée: {worker.prenom} {worker.nom} - {structure_type} = '{current_value}'")
                    logger.warning(f"Structures disponibles: {available_structures}")
                    
                    # Essayer de trouver une correspondance intelligente
                    new_value = None
                    
                    # 1. Chercher une correspondance partielle (contient le nom)
                    for structure in available_structures:
                        if current_value.lower() in structure.lower() or structure.lower() in current_value.lower():
                            new_value = structure
                            logger.info(f"Correspondance trouvée: '{current_value}' → '{new_value}'")
                            break
                    
                    # 2. Si aucune correspondance, utiliser la première disponible
                    if not new_value and available_structures:
                        new_value = available_structures[0]
                        logger.warning(f"Aucune correspondance, utilisation de la première: '{current_value}' → '{new_value}'")
                    
                    # 3. Appliquer la modification seulement si on a trouvé une valeur
                    if new_value:
                        setattr(worker, structure_type, new_value)
                        
                        sync_results[f"{structure_type}s"].append({
                            'worker_id': worker.id,
                            'worker_name': f"{worker.prenom} {worker.nom}",
                            'old_value': current_value,
                            'new_value': new_value
                        })
                        
                        logger.warning(f"FORCÉ: Salarié {worker.prenom} {worker.nom}: {structure_type} '{current_value}' → '{new_value}'")
                    else:
                        logger.error(f"Impossible de synchroniser {worker.prenom} {worker.nom}: aucune structure {structure_type} disponible")
                else:
                    # L'affectation est valide, ne pas la modifier
                    if current_value:
                        logger.info(f"Affectation valide préservée: {worker.prenom} {worker.nom} - {structure_type} = '{current_value}'")
        
        # Sauvegarder les modifications
        self.db.commit()
        
        total_updated = sum(len(updates) for updates in sync_results.values())
        logger.warning(f"Synchronisation forcée terminée: {total_updated} mise(s) à jour")
        
        return {
            'success': True,
            'employer_id': employer_id,
            'total_updated': total_updated,
            'details': sync_results,
            'message': f'Synchronisation forcée appliquée: {total_updated} affectation(s) modifiée(s)'
        }
    
    def _get_hierarchical_structures(self, employer_id: int) -> Dict[str, List[str]]:
        """Récupère les structures hiérarchiques pour un employeur"""
        structures = self.db.query(models.OrganizationalUnit).filter(
            models.OrganizationalUnit.employer_id == employer_id
        ).all()
        
        result = {
            'etablissements': [],
            'departements': [],
            'services': [],
            'unites': []
        }
        
        for structure in structures:
            structure_type = structure.level.lower()
            if structure_type in ['etablissement', 'departement', 'service', 'unite']:
                key = f"{structure_type}s"
                if structure.name not in result[key]:
                    result[key].append(structure.name)
        
        return result
    
    def validate_worker_assignments(self, employer_id: int) -> Dict[str, any]:
        """
        Valide que toutes les affectations des salariés correspondent aux structures existantes
        """
        logger.info(f"Validation des affectations pour employeur {employer_id}")
        
        hierarchical_structures = self._get_hierarchical_structures(employer_id)
        workers = self.db.query(models.Worker).filter(
            models.Worker.employer_id == employer_id
        ).all()
        
        validation_errors = []
        
        for worker in workers:
            worker_name = f"{worker.prenom} {worker.nom}"
            
            # Vérifier chaque type de structure
            for structure_type in ['etablissement', 'departement', 'service', 'unite']:
                current_value = getattr(worker, structure_type, None)
                available_structures = hierarchical_structures.get(f"{structure_type}s", [])
                
                if current_value and current_value not in available_structures:
                    validation_errors.append({
                        'worker_id': worker.id,
                        'worker_name': worker_name,
                        'structure_type': structure_type,
                        'current_value': current_value,
                        'available_values': available_structures
                    })
        
        return {
            'is_valid': len(validation_errors) == 0,
            'errors_count': len(validation_errors),
            'errors': validation_errors,
            'hierarchical_structures': hierarchical_structures
        }

def get_sync_service(db: Session) -> OrganizationalSyncService:
    """Factory function pour créer le service de synchronisation"""
    return OrganizationalSyncService(db)