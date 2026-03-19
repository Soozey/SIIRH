import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

interface HierarchicalTreeProps {
  employerId: number;
  readonly?: boolean;
  onNodeSelect?: (nodeId: number | null) => void;
  selectedNodeId?: number | null;
}

const HierarchicalOrganizationTreeFinal: React.FC<HierarchicalTreeProps> = ({
  employerId,
  readonly = false,
  onNodeSelect,
  selectedNodeId
}) => {
  const [expandedNodes, setExpandedNodes] = React.useState<Set<number>>(new Set());

  const { data: treeData, isLoading, error } = useQuery({
    queryKey: ['organizational-tree-final', employerId],
    queryFn: async () => {
      if (!employerId) {
        throw new Error('No employer ID provided');
      }
      const response = await api.get(`/organizational-structure/${employerId}/tree`);
      return response.data;
    },
    enabled: !!employerId && employerId > 0
  });

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

  const renderNode = (node: any, depth: number = 0): React.ReactNode => {
    if (!node || !node.id) return null;

    const hasChildren = Array.isArray(node.children) && node.children.length > 0;
    const isExpanded = expandedNodes.has(node.id);
    const isSelected = selectedNodeId === node.id;

    return (
      <div key={`node-${node.id}`} className="select-none">
        <div
          className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors border ${
            isSelected 
              ? 'bg-blue-100 border-blue-300 shadow-sm' 
              : 'hover:bg-gray-50 border-transparent'
          } ${getLevelColor(node.level)}`}
          style={{ marginLeft: `${depth * 20}px` }}
          onClick={() => {
            if (hasChildren) {
              toggleNode(node.id);
            }
            if (onNodeSelect) {
              onNodeSelect(node.id);
            }
          }}
        >
          {/* Expand/Collapse Icon */}
          <div className="w-4 h-4 flex items-center justify-center">
            {hasChildren ? (
              <span className="text-gray-500 text-sm">
                {isExpanded ? '▼' : '▶'}
              </span>
            ) : (
              <div className="w-4 h-4" />
            )}
          </div>

          {/* Level Icon */}
          <span className="text-lg">
            {getLevelIcon(node.level)}
          </span>

          {/* Node Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">
                {node.name || 'Sans nom'}
              </span>
              <span className="text-xs bg-white px-2 py-1 rounded border">
                {node.code || ''}
              </span>
            </div>
            {node.description && (
              <p className="text-xs mt-1 truncate opacity-75">
                {node.description}
              </p>
            )}
          </div>

          {/* Worker Count and Deletion Status */}
          <div className="flex items-center gap-2 text-xs">
            <div className="flex items-center gap-1">
              <span>👥</span>
              <span>{node.worker_count || 0}</span>
            </div>
            
            {/* Deletion Status Indicator */}
            {(node.worker_count === 0 && (!node.children || node.children.length === 0)) ? (
              <span 
                className="text-green-600 bg-green-100 px-1 py-0.5 rounded text-xs"
                title="Structure vide - Peut être supprimée"
              >
                ✓ Supprimable
              </span>
            ) : (
              <span 
                className="text-orange-600 bg-orange-100 px-1 py-0.5 rounded text-xs"
                title={
                  node.worker_count > 0 
                    ? `Contient ${node.worker_count} salarié(s) - Suppression forcée requise`
                    : "Contient des sous-structures - Suppression forcée requise"
                }
              >
                ⚠ Occupée
              </span>
            )}
          </div>
        </div>

        {/* Children */}
        {hasChildren && isExpanded && (
          <div className="mt-1">
            {node.children.map((child: any) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Chargement de la hiérarchie...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">Erreur lors du chargement de la hiérarchie.</p>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : 'Erreur inconnue'}
        </p>
      </div>
    );
  }

  const tree = Array.isArray(treeData?.tree) ? treeData.tree : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          🌳 Hiérarchie Organisationnelle
        </h3>
        {tree.length > 0 && (
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {tree.length} établissement{tree.length > 1 ? 's' : ''} | {treeData?.total_units || 0} unités
          </span>
        )}
      </div>

      <div className="space-y-1 max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-2">
        {tree.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-4">🏢</div>
            <p>Aucune structure organisationnelle définie.</p>
            {!readonly && (
              <p className="text-sm mt-2">Utilisez le gestionnaire de hiérarchie pour créer votre structure.</p>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {tree.map((node: any) => renderNode(node, 0))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HierarchicalOrganizationTreeFinal;