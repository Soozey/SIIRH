import React, { useState } from 'react';
import HierarchicalOrganizationTreeFinal from './HierarchicalOrganizationTreeFinal';
import SimpleOrganizationalDeleteModal from './SimpleOrganizationalDeleteModal';
import HierarchyManagerModal from './HierarchyManagerModal';

interface SimpleOrganizationalUnitManagerProps {
  employerId: number;
  onRefresh?: () => void;
}

const SimpleOrganizationalUnitManager: React.FC<SimpleOrganizationalUnitManagerProps> = ({
  employerId,
  onRefresh
}) => {
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [hierarchyModalOpen, setHierarchyModalOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);

  const handleNodeSelect = (nodeId: number | null) => {
    setSelectedUnitId(nodeId);
  };

  const handleDeleteClick = () => {
    if (selectedUnitId) {
      setDeleteModalOpen(true);
    }
  };

  const handleDeleteSuccess = () => {
    setDeleteModalOpen(false);
    setSelectedUnitId(null);
    if (onRefresh) {
      onRefresh();
    }
  };

  const handleCreateClick = () => {
    setEditMode(false);
    setHierarchyModalOpen(true);
  };

  const handleEditClick = () => {
    if (selectedUnitId) {
      setEditMode(true);
      setHierarchyModalOpen(true);
    }
  };

  const handleHierarchyModalSuccess = () => {
    setHierarchyModalOpen(false);
    setSelectedUnitId(null);
    if (onRefresh) {
      onRefresh();
    }
  };

  return (
    <div className="space-y-6">
      {/* Actions Bar */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-semibold text-gray-900">
              Gestion des Structures Organisationnelles
            </h3>
            {selectedUnitId && (
              <span className="text-sm text-blue-600 bg-blue-100 px-2 py-1 rounded">
                Unité sélectionnée
              </span>
            )}
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={handleCreateClick}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
            >
              ➕ Créer une structure
            </button>
            
            <button
              onClick={handleEditClick}
              disabled={!selectedUnitId}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              title={selectedUnitId ? "Modifier la structure sélectionnée" : "Sélectionnez une structure à modifier"}
            >
              ✏️ Modifier
            </button>
            
            <button
              onClick={handleDeleteClick}
              disabled={!selectedUnitId}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              title={selectedUnitId ? "Supprimer la structure sélectionnée" : "Sélectionnez une structure à supprimer"}
            >
              🗑️ Supprimer
            </button>
          </div>
        </div>
      </div>

      {/* Tree View */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <HierarchicalOrganizationTreeFinal
          employerId={employerId}
          onNodeSelect={handleNodeSelect}
          selectedNodeId={selectedUnitId}
        />
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">Instructions :</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Cliquez sur une structure dans l'arbre pour la sélectionner</li>
          <li>• Utilisez "Créer" pour ajouter une nouvelle structure organisationnelle</li>
          <li>• Utilisez "Modifier" pour éditer la structure sélectionnée</li>
          <li>• Utilisez "Supprimer" pour supprimer une structure vide (sans salariés)</li>
          <li>• Les structures contenant des salariés ou des sous-structures nécessitent une suppression forcée</li>
        </ul>
      </div>

      {/* Delete Modal */}
      <SimpleOrganizationalDeleteModal
        isOpen={deleteModalOpen}
        unitId={selectedUnitId}
        onClose={() => setDeleteModalOpen(false)}
        onSuccess={handleDeleteSuccess}
      />

      {/* Hierarchy Manager Modal */}
      <HierarchyManagerModal
        visible={hierarchyModalOpen}
        employerId={employerId}
        editUnitId={editMode ? selectedUnitId : null}
        onCancel={() => setHierarchyModalOpen(false)}
        onSuccess={handleHierarchyModalSuccess}
      />
    </div>
  );
};

export default SimpleOrganizationalUnitManager;