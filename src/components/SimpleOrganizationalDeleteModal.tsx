import React, { useState, useEffect } from 'react';
import { api } from '../api';

interface Worker {
  id: number;
  nom: string;
  prenom: string;
  matricule: string;
}

interface Child {
  id: number;
  name: string;
  level: string;
}

interface DeletionConstraints {
  can_delete: boolean;
  reason: string | null;
  unit_name: string;
  unit_level: string;
  children_count: number;
  direct_workers_count: number;
  descendant_workers_count: number;
  total_workers_count: number;
  children: Child[];
  workers: Worker[];
}

interface SimpleOrganizationalDeleteModalProps {
  isOpen: boolean;
  unitId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}

const SimpleOrganizationalDeleteModal: React.FC<SimpleOrganizationalDeleteModalProps> = ({
  isOpen,
  unitId,
  onClose,
  onSuccess
}) => {
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [constraints, setConstraints] = useState<DeletionConstraints | null>(null);
  const [showForceOption, setShowForceOption] = useState(false);

  useEffect(() => {
    if (isOpen && unitId) {
      checkDeletionConstraints();
    } else {
      setConstraints(null);
      setShowForceOption(false);
    }
  }, [isOpen, unitId]);

  const checkDeletionConstraints = async () => {
    if (!unitId) return;

    setLoading(true);
    try {
      const response = await api.get(`/organizational-structure/${unitId}/can-delete`);
      setConstraints(response.data);
    } catch (error) {
      console.error('Error checking deletion constraints:', error);
      alert('Impossible de vérifier les contraintes de suppression.');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (force: boolean = false) => {
    if (!unitId) return;

    setDeleting(true);
    try {
      await api.delete(`/organizational-structure/${unitId}?force=${force}`);
      
      alert(`La structure organisationnelle "${constraints?.unit_name}" a été supprimée avec succès.`);
      onSuccess();
    } catch (error: any) {
      console.error('Error deleting unit:', error);
      
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression';
      alert(`Erreur de suppression: ${errorMessage}`);
    } finally {
      setDeleting(false);
    }
  };

  const getLevelDisplayName = (level: string) => {
    const levelNames = {
      'etablissement': 'Établissement',
      'departement': 'Département',
      'service': 'Service',
      'unite': 'Unité'
    };
    return levelNames[level as keyof typeof levelNames] || level;
  };

  if (!isOpen) return null;

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4">Vérification des contraintes de suppression...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!constraints) return null;

  const constraintChildren = constraints.children ?? [];
  const constraintWorkers = constraints.workers ?? [];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center mb-4">
          <span className="text-yellow-500 text-xl mr-2">⚠️</span>
          <h2 className="text-xl font-semibold">Supprimer la structure organisationnelle</h2>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-medium">
            {constraints.unit_name} ({getLevelDisplayName(constraints.unit_level)})
          </h3>
        </div>

        {constraints.can_delete ? (
          <div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <span className="text-green-500 text-lg mr-2">✅</span>
                <div>
                  <h4 className="font-medium text-green-800">Suppression possible</h4>
                  <p className="text-green-700 text-sm">
                    Cette structure organisationnelle ne contient aucun salarié ni sous-structure et peut être supprimée en toute sécurité.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              <button 
                onClick={() => handleDelete(false)}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center"
              >
                {deleting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Suppression...
                  </>
                ) : (
                  <>
                    🗑️ Supprimer
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <span className="text-red-500 text-lg mr-2">❌</span>
                <div>
                  <h4 className="font-medium text-red-800">Suppression impossible</h4>
                  <p className="text-red-700 text-sm">{constraints.reason}</p>
                </div>
              </div>
            </div>

            {/* Détails des contraintes */}
            {constraintChildren.length > 0 && (
              <div className="mb-4">
                <h5 className="font-medium mb-2">Sous-structures ({constraintChildren.length}) :</h5>
                <div className="bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
                  {constraintChildren.map((child) => (
                    <div key={child.id} className="text-sm py-1">
                      {child.name} ({getLevelDisplayName(child.level)})
                    </div>
                  ))}
                </div>
              </div>
            )}

            {constraintWorkers.length > 0 && (
              <div className="mb-4">
                <h5 className="font-medium mb-2">Salariés directement assignés ({constraints.direct_workers_count}) :</h5>
                <div className="bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
                  {constraintWorkers.map((worker) => (
                    <div key={worker.id} className="text-sm py-1">
                      {worker.prenom} {worker.nom} ({worker.matricule})
                    </div>
                  ))}
                </div>
              </div>
            )}

            {constraints.descendant_workers_count > 0 && (
              <div className="mb-4">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-yellow-800 text-sm">
                    ⚠️ {constraints.descendant_workers_count} salarié(s) dans les sous-structures
                  </p>
                  <p className="text-yellow-700 text-xs mt-1">
                    Ces salariés sont assignés aux sous-structures de cette unité organisationnelle.
                  </p>
                </div>
              </div>
            )}

            <hr className="my-4" />

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <h5 className="font-medium text-yellow-800 mb-2">Suppression forcée</h5>
              <p className="text-yellow-700 text-sm">
                Vous pouvez forcer la suppression. Cela réassignera automatiquement les sous-structures au niveau parent et désassignera tous les salariés.
              </p>
            </div>

            {!showForceOption ? (
              <div className="flex justify-end space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button 
                  onClick={() => setShowForceOption(true)}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 flex items-center"
                >
                  ⚠️ Voir les options de suppression forcée
                </button>
              </div>
            ) : (
              <div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                  <h5 className="font-medium text-red-800 mb-2">Attention !</h5>
                  <div className="text-red-700 text-sm">
                    <p className="mb-2">La suppression forcée va :</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>Réassigner les {constraints.children_count} sous-structures au niveau parent</li>
                      <li>Désassigner les {constraints.direct_workers_count} salariés directement assignés</li>
                      <li>Les {constraints.descendant_workers_count} salariés des sous-structures ne seront pas affectés</li>
                    </ul>
                    <p className="mt-2 font-medium">Cette action est irréversible.</p>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    Annuler
                  </button>
                  <button 
                    onClick={() => setShowForceOption(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    Retour
                  </button>
                  <button 
                    onClick={() => handleDelete(true)}
                    disabled={deleting}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center"
                  >
                    {deleting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Suppression...
                      </>
                    ) : (
                      <>
                        🗑️ Forcer la suppression
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SimpleOrganizationalDeleteModal;
