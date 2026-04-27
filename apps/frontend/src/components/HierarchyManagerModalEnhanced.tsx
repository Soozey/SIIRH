import React, { useState } from 'react';
import { 
  XMarkIcon, 
  PlusIcon, 
  TrashIcon, 
  PencilIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

interface HierarchyManagerModalEnhancedProps {
  employerId: number;
  isOpen: boolean;
  onClose: () => void;
  onSave?: () => void;
}

interface OrganizationalNode {
  id: number;
  name: string;
  code?: string;
  level: string;
  parent_id?: number | null;
  description?: string;
  children?: OrganizationalNode[];
  worker_count?: number;
}

interface CreateNodeForm {
  name: string;
  code: string;
  level: 'etablissement' | 'departement' | 'service' | 'unite';
  parent_id: number | null;
  description: string;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

const getApiErrorMessage = (error: unknown, fallback: string) => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.detail || apiError.message || fallback;
};

export const HierarchyManagerModalEnhanced: React.FC<HierarchyManagerModalEnhancedProps> = ({
  employerId,
  isOpen,
  onClose,
  onSave
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editingNode, setEditingNode] = useState<OrganizationalNode | null>(null);
  
  const [createForm, setCreateForm] = useState<CreateNodeForm>({
    name: '',
    code: '',
    level: 'etablissement',
    parent_id: null,
    description: ''
  });

  const queryClient = useQueryClient();

  // Charger l'arbre hiérarchique
  const { data: treeData, isLoading } = useQuery({
    queryKey: ['organizational-tree', employerId],
    queryFn: async () => {
      const response = await api.get(`/employers/${employerId}/hierarchical-organization/tree`);
      return response.data;
    },
    enabled: isOpen && !!employerId
  });

  // Charger les infos de suppression pour le nœud sélectionné
  const { data: deletionInfo } = useQuery({
    queryKey: ['deletion-info', selectedNodeId],
    queryFn: async () => {
      if (!selectedNodeId) return null;
      const response = await api.get(
        `/employers/${employerId}/hierarchical-organization/nodes/${selectedNodeId}/deletion-info`
      );
      return response.data;
    },
    enabled: !!selectedNodeId && showDeleteConfirm
  });

  // Mutation pour créer un nœud
  const createMutation = useMutation({
    mutationFn: async (data: CreateNodeForm) => {
      const response = await api.post(
        `/employers/${employerId}/hierarchical-organization/nodes`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizational-tree', employerId] });
      queryClient.invalidateQueries({ queryKey: ['cascading-options', employerId] });
      setShowCreateForm(false);
      resetCreateForm();
      alert('Structure créée avec succès!');
    },
    onError: (error: unknown) => {
      alert(`Erreur: ${getApiErrorMessage(error, 'Erreur lors de la creation du noeud')}`);
    }
  });

  // Mutation pour mettre à jour un nœud
  const updateMutation = useMutation({
    mutationFn: async (data: { id: number; name: string; code?: string; description?: string }) => {
      const response = await api.put(
        `/employers/${employerId}/hierarchical-organization/nodes/${data.id}`,
        {
          name: data.name,
          code: data.code,
          description: data.description
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizational-tree', employerId] });
      queryClient.invalidateQueries({ queryKey: ['cascading-options', employerId] });
      setEditingNode(null);
      alert('Structure modifiée avec succès!');
    },
    onError: (error: unknown) => {
      alert(`Erreur: ${getApiErrorMessage(error, 'Erreur lors de la mise a jour du noeud')}`);
    }
  });

  // Mutation pour supprimer un nœud
  const deleteMutation = useMutation({
    mutationFn: async ({ nodeId, force }: { nodeId: number; force: boolean }) => {
      const response = await api.delete(
        `/employers/${employerId}/hierarchical-organization/nodes/${nodeId}`,
        { params: { force } }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizational-tree', employerId] });
      queryClient.invalidateQueries({ queryKey: ['cascading-options', employerId] });
      setShowDeleteConfirm(false);
      setSelectedNodeId(null);
      alert('Structure supprimée avec succès!');
    },
    onError: (error: unknown) => {
      alert(`Erreur: ${getApiErrorMessage(error, 'Erreur lors de la suppression du noeud')}`);
    }
  });

  const resetCreateForm = () => {
    setCreateForm({
      name: '',
      code: '',
      level: 'etablissement',
      parent_id: null,
      description: ''
    });
  };

  const handleCreateNode = () => {
    if (!createForm.name.trim()) {
      alert('Le nom est obligatoire');
      return;
    }
    createMutation.mutate(createForm);
  };

  const handleUpdateNode = () => {
    if (!editingNode) return;
    updateMutation.mutate({
      id: editingNode.id,
      name: editingNode.name,
      code: editingNode.code,
      description: editingNode.description
    });
  };

  const handleDeleteNode = (force: boolean = false) => {
    if (!selectedNodeId) return;
    deleteMutation.mutate({ nodeId: selectedNodeId, force });
  };

  const toggleNode = (nodeId: number) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'etablissement': return '🏢';
      case 'departement': return '🏬';
      case 'service': return '👥';
      case 'unite': return '📦';
      default: return '🏢';
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'etablissement': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'departement': return 'bg-green-50 border-green-200 text-green-800';
      case 'service': return 'bg-purple-50 border-purple-200 text-purple-800';
      case 'unite': return 'bg-orange-50 border-orange-200 text-orange-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const getLevelLabel = (level: string) => {
    switch (level) {
      case 'etablissement': return 'Établissement';
      case 'departement': return 'Département';
      case 'service': return 'Service';
      case 'unite': return 'Unité';
      default: return level;
    }
  };

  const getNextLevel = (currentLevel: string): 'departement' | 'service' | 'unite' | null => {
    const hierarchy: Record<string, 'departement' | 'service' | 'unite' | null> = {
      'etablissement': 'departement',
      'departement': 'service',
      'service': 'unite',
      'unite': null
    };
    return hierarchy[currentLevel] || null;
  };

  const renderNode = (node: OrganizationalNode, depth: number = 0): React.ReactNode => {
    if (!node || !node.id) return null;

    const hasChildren = Array.isArray(node.children) && node.children.length > 0;
    const isExpanded = expandedNodes.has(node.id);
    const isSelected = selectedNodeId === node.id;

    return (
      <div key={`node-${node.id}`} className="select-none">
        <div
          className={`flex items-center gap-2 p-2 rounded-lg border transition-colors ${
            isSelected 
              ? 'bg-blue-100 border-blue-300 shadow-sm' 
              : 'hover:bg-gray-50 border-transparent cursor-pointer'
          } ${getLevelColor(node.level)}`}
          style={{ marginLeft: `${depth * 20}px` }}
          onClick={() => {
            if (hasChildren) {
              toggleNode(node.id);
            }
            setSelectedNodeId(node.id);
          }}
        >
          <div className="w-4 h-4 flex items-center justify-center">
            {hasChildren ? (
              <span className="text-gray-500 text-sm">
                {isExpanded ? '▼' : '▶'}
              </span>
            ) : (
              <div className="w-4 h-4" />
            )}
          </div>

          <span className="text-lg">{getLevelIcon(node.level)}</span>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">{node.name || 'Sans nom'}</span>
              {node.code && (
                <span className="text-xs bg-white px-2 py-1 rounded border">
                  {node.code}
                </span>
              )}
            </div>
            {node.description && (
              <p className="text-xs mt-1 truncate opacity-75">{node.description}</p>
            )}
          </div>

          <div className="flex items-center gap-1 text-xs">
            <span>👥</span>
            <span>{node.worker_count || 0}</span>
          </div>

          {isSelected && (
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              {getNextLevel(node.level) && (
                <button
                  onClick={() => {
                    setCreateForm({
                      ...createForm,
                      level: getNextLevel(node.level)!,
                      parent_id: node.id
                    });
                    setShowCreateForm(true);
                  }}
                  className="p-1 hover:bg-green-200 rounded transition-colors"
                  title="Ajouter une sous-structure"
                >
                  <PlusIcon className="h-4 w-4 text-green-600" />
                </button>
              )}
              <button
                onClick={() => setEditingNode(node)}
                className="p-1 hover:bg-blue-200 rounded transition-colors"
                title="Modifier"
              >
                <PencilIcon className="h-4 w-4 text-blue-600" />
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-1 hover:bg-red-200 rounded transition-colors"
                title="Supprimer"
              >
                <TrashIcon className="h-4 w-4 text-red-600" />
              </button>
            </div>
          )}
        </div>

        {hasChildren && isExpanded && (
          <div className="mt-1">
            {node.children!.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (!isOpen) return null;

  const tree = Array.isArray(treeData?.tree) ? treeData.tree : [];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={() => !showCreateForm && !editingNode && !showDeleteConfirm && onClose()}
        />

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  Gestion de la Hiérarchie Organisationnelle
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Créez, modifiez et supprimez les structures organisationnelles
                </p>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setCreateForm({
                      name: '',
                      code: '',
                      level: 'etablissement',
                      parent_id: null,
                      description: ''
                    });
                    setShowCreateForm(true);
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <PlusIcon className="h-5 w-5" />
                  Nouvel Établissement
                </button>
                
                <button
                  onClick={onClose}
                  className="bg-white rounded-md text-gray-400 hover:text-gray-600 focus:outline-none"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
            </div>

            <div className="border border-gray-200 rounded-lg bg-gray-50 p-4 max-h-96 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center p-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <span className="ml-2">Chargement...</span>
                </div>
              ) : tree.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-4">🏢</div>
                  <p>Aucune structure organisationnelle définie.</p>
                  <p className="text-sm mt-2">Cliquez sur "Nouvel Établissement" pour commencer.</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {tree.map((node: OrganizationalNode) => renderNode(node, 0))}
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={() => {
                onSave?.();
                onClose();
              }}
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>

      {(showCreateForm || editingNode) && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h4 className="text-lg font-semibold mb-4">
              {editingNode ? 'Modifier la structure' : 'Créer une nouvelle structure'}
            </h4>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom *
                </label>
                <input
                  type="text"
                  value={editingNode ? editingNode.name : createForm.name}
                  onChange={(e) => {
                    if (editingNode) {
                      setEditingNode({ ...editingNode, name: e.target.value });
                    } else {
                      setCreateForm({ ...createForm, name: e.target.value });
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Nom de la structure"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Code
                </label>
                <input
                  type="text"
                  value={editingNode ? (editingNode.code || '') : createForm.code}
                  onChange={(e) => {
                    if (editingNode) {
                      setEditingNode({ ...editingNode, code: e.target.value });
                    } else {
                      setCreateForm({ ...createForm, code: e.target.value });
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Code (optionnel)"
                />
              </div>

              {!editingNode && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Niveau
                  </label>
                  <input
                    type="text"
                    value={getLevelLabel(createForm.level)}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={editingNode ? (editingNode.description || '') : createForm.description}
                  onChange={(e) => {
                    if (editingNode) {
                      setEditingNode({ ...editingNode, description: e.target.value });
                    } else {
                      setCreateForm({ ...createForm, description: e.target.value });
                    }
                  }}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Description (optionnelle)"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowCreateForm(false);
                  setEditingNode(null);
                  resetCreateForm();
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={editingNode ? handleUpdateNode : handleCreateNode}
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {editingNode ? 'Modifier' : 'Créer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && deletionInfo && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              {deletionInfo.can_delete ? (
                <CheckCircleIcon className="h-8 w-8 text-green-500" />
              ) : (
                <ExclamationTriangleIcon className="h-8 w-8 text-orange-500" />
              )}
              <h4 className="text-lg font-semibold">
                Confirmer la suppression
              </h4>
            </div>
            
            <p className="text-gray-700 mb-4">
              Voulez-vous supprimer <strong>{deletionInfo.node_name}</strong> ?
            </p>

            <div className="bg-gray-50 rounded-lg p-4 mb-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Sous-structures:</span>
                <span className="font-medium">{deletionInfo.children_count}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Salariés affectés:</span>
                <span className="font-medium">{deletionInfo.workers_count}</span>
              </div>
            </div>

            {(deletionInfo.warnings ?? []).length > 0 && (
              <div className="mb-4">
                {(deletionInfo.warnings ?? []).map((warning: string, index: number) => (
                  <div key={index} className={`flex items-start gap-2 text-sm p-2 rounded ${
                    deletionInfo.can_delete ? 'bg-green-50 text-green-800' : 'bg-orange-50 text-orange-800'
                  }`}>
                    <span>{deletionInfo.can_delete ? '✓' : '⚠️'}</span>
                    <span>{warning}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              {deletionInfo.can_delete ? (
                <button
                  onClick={() => handleDeleteNode(false)}
                  disabled={deleteMutation.isPending}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  Supprimer
                </button>
              ) : (
                <button
                  onClick={() => {
                    if (confirm('⚠️ ATTENTION: Cette suppression forcée supprimera toutes les sous-structures et désaffectera les salariés. Continuer?')) {
                      handleDeleteNode(true);
                    }
                  }}
                  disabled={deleteMutation.isPending}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  Suppression Forcée
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HierarchyManagerModalEnhanced;
