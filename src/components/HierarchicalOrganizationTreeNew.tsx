import React, { useState, useMemo, useCallback } from 'react';
import { 
  ChevronRightIcon, 
  ChevronDownIcon, 
  PlusIcon, 
  PencilIcon, 
  TrashIcon,
  MagnifyingGlassIcon,
  BuildingOfficeIcon,
  BuildingOffice2Icon,
  CubeIcon,
  Squares2X2Icon
} from '@heroicons/react/24/outline';

// Types pour la hiérarchie organisationnelle
interface OrganizationalNode {
  id: number;
  employer_id: number;
  parent_id: number | null;
  level: 'etablissement' | 'departement' | 'service' | 'unite';
  name: string;
  code?: string;
  description?: string;
  path?: string;
  sort_order: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  children?: OrganizationalNode[];
}

interface HierarchicalTreeProps {
  employerId: number;
  nodes: OrganizationalNode[];
  onNodeAdd: (parentId: number | null, level: OrganizationalNode['level']) => void;
  onNodeEdit: (nodeId: number, data: Partial<OrganizationalNode>) => void;
  onNodeDelete: (nodeId: number) => void;
  onNodeMove: (nodeId: number, newParentId: number | null) => void;
  onSelectionChange?: (selectedNodes: number[]) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  readonly?: boolean;
  showSearch?: boolean;
  maxHeight?: string;
}

interface TreeNodeProps {
  node: OrganizationalNode;
  level: number;
  expandedNodes: Set<number>;
  selectedNodes: Set<number>;
  onToggleExpand: (nodeId: number) => void;
  onSelect: (nodeId: number, multiSelect: boolean) => void;
  onAdd: (parentId: number | null, level: OrganizationalNode['level']) => void;
  onEdit: (nodeId: number, data: Partial<OrganizationalNode>) => void;
  onDelete: (nodeId: number) => void;
  onDragStart: (nodeId: number) => void;
  onDragOver: (e: React.DragEvent, nodeId: number) => void;
  onDrop: (e: React.DragEvent, targetNodeId: number) => void;
  readonly: boolean;
  searchQuery?: string;
}

// Icônes par niveau hiérarchique
const getLevelIcon = (level: OrganizationalNode['level'], className: string = "h-4 w-4") => {
  switch (level) {
    case 'etablissement':
      return <BuildingOfficeIcon className={className} />;
    case 'departement':
      return <BuildingOffice2Icon className={className} />;
    case 'service':
      return <Squares2X2Icon className={className} />;
    case 'unite':
      return <CubeIcon className={className} />;
    default:
      return <CubeIcon className={className} />;
  }
};

// Couleurs par niveau hiérarchique
const getLevelColors = (level: OrganizationalNode['level']) => {
  switch (level) {
    case 'etablissement':
      return {
        bg: 'bg-blue-50 hover:bg-blue-100',
        border: 'border-blue-200',
        text: 'text-blue-900',
        icon: 'text-blue-600'
      };
    case 'departement':
      return {
        bg: 'bg-green-50 hover:bg-green-100',
        border: 'border-green-200',
        text: 'text-green-900',
        icon: 'text-green-600'
      };
    case 'service':
      return {
        bg: 'bg-yellow-50 hover:bg-yellow-100',
        border: 'border-yellow-200',
        text: 'text-yellow-900',
        icon: 'text-yellow-600'
      };
    case 'unite':
      return {
        bg: 'bg-purple-50 hover:bg-purple-100',
        border: 'border-purple-200',
        text: 'text-purple-900',
        icon: 'text-purple-600'
      };
    default:
      return {
        bg: 'bg-gray-50 hover:bg-gray-100',
        border: 'border-gray-200',
        text: 'text-gray-900',
        icon: 'text-gray-600'
      };
  }
};

// Noms des niveaux en français
const getLevelName = (level: OrganizationalNode['level']) => {
  switch (level) {
    case 'etablissement':
      return 'Établissement';
    case 'departement':
      return 'Département';
    case 'service':
      return 'Service';
    case 'unite':
      return 'Unité';
    default:
      return level;
  }
};

// Niveau enfant suivant
const getChildLevel = (level: OrganizationalNode['level']): OrganizationalNode['level'] | null => {
  switch (level) {
    case 'etablissement':
      return 'departement';
    case 'departement':
      return 'service';
    case 'service':
      return 'unite';
    case 'unite':
      return null;
    default:
      return null;
  }
};

// Composant pour un nœud de l'arbre
const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  level,
  expandedNodes,
  selectedNodes,
  onToggleExpand,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  onDragStart,
  onDragOver,
  onDrop,
  readonly,
  searchQuery
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(node.name);
  const [editCode, setEditCode] = useState(node.code || '');

  const isExpanded = expandedNodes.has(node.id);
  const isSelected = selectedNodes.has(node.id);
  const hasChildren = node.children && node.children.length > 0;
  const colors = getLevelColors(node.level);
  const childLevel = getChildLevel(node.level);

  // Mise en évidence de la recherche
  const highlightText = (text: string, query?: string) => {
    if (!query || !text) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <span key={index} className="bg-yellow-200 font-semibold">
          {part}
        </span>
      ) : part
    );
  };

  const handleSaveEdit = () => {
    if (editName.trim() !== node.name || editCode !== (node.code || '')) {
      onEdit(node.id, {
        name: editName.trim(),
        code: editCode.trim() || undefined
      });
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditName(node.name);
    setEditCode(node.code || '');
    setIsEditing(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div className="select-none">
      {/* Nœud principal */}
      <div
        className={`
          flex items-center gap-2 p-2 rounded-lg border transition-all duration-200
          ${colors.bg} ${colors.border}
          ${isSelected ? 'ring-2 ring-blue-500 ring-opacity-50' : ''}
          ${!readonly ? 'cursor-pointer' : ''}
        `}
        style={{ marginLeft: `${level * 20}px` }}
        onClick={(e) => {
          if (!isEditing) {
            onSelect(node.id, e.ctrlKey || e.metaKey);
          }
        }}
        draggable={!readonly && !isEditing}
        onDragStart={() => !readonly && onDragStart(node.id)}
        onDragOver={(e) => !readonly && onDragOver(e, node.id)}
        onDrop={(e) => !readonly && onDrop(e, node.id)}
      >
        {/* Bouton d'expansion */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) {
              onToggleExpand(node.id);
            }
          }}
          className="flex-shrink-0 p-1 hover:bg-white hover:bg-opacity-50 rounded"
          disabled={!hasChildren}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDownIcon className="h-4 w-4 text-gray-600" />
            ) : (
              <ChevronRightIcon className="h-4 w-4 text-gray-600" />
            )
          ) : (
            <div className="h-4 w-4" />
          )}
        </button>

        {/* Icône du niveau */}
        <div className={`flex-shrink-0 ${colors.icon}`}>
          {getLevelIcon(node.level)}
        </div>

        {/* Contenu du nœud */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={handleKeyPress}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Nom"
                autoFocus
              />
              <input
                type="text"
                value={editCode}
                onChange={(e) => setEditCode(e.target.value)}
                onKeyDown={handleKeyPress}
                className="w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Code"
              />
              <button
                onClick={handleSaveEdit}
                className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
              >
                ✓
              </button>
              <button
                onClick={handleCancelEdit}
                className="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                ✕
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <div className={`font-medium truncate ${colors.text}`}>
                  {highlightText(node.name, searchQuery)}
                </div>
                {node.code && (
                  <div className="text-xs text-gray-500 truncate">
                    Code: {highlightText(node.code, searchQuery)}
                  </div>
                )}
                {node.path && (
                  <div className="text-xs text-gray-400 truncate">
                    {node.path}
                  </div>
                )}
              </div>

              {/* Badge du niveau */}
              <span className={`
                px-2 py-1 text-xs font-medium rounded-full
                ${colors.bg} ${colors.text} ${colors.border} border
              `}>
                {getLevelName(node.level)}
              </span>
            </div>
          )}
        </div>

        {/* Actions */}
        {!readonly && !isEditing && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {childLevel && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAdd(node.id, childLevel);
                }}
                className="p-1 text-green-600 hover:bg-green-100 rounded"
                title={`Ajouter ${getLevelName(childLevel)}`}
              >
                <PlusIcon className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
              className="p-1 text-blue-600 hover:bg-blue-100 rounded"
              title="Modifier"
            >
              <PencilIcon className="h-4 w-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`Êtes-vous sûr de vouloir supprimer "${node.name}" ?`)) {
                  onDelete(node.id);
                }
              }}
              className="p-1 text-red-600 hover:bg-red-100 rounded"
              title="Supprimer"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Enfants */}
      {isExpanded && hasChildren && (
        <div className="mt-1">
          {node.children!.map(child => (
            <TreeNode
              key={child.id}
              node={child}
              level={level + 1}
              expandedNodes={expandedNodes}
              selectedNodes={selectedNodes}
              onToggleExpand={onToggleExpand}
              onSelect={onSelect}
              onAdd={onAdd}
              onEdit={onEdit}
              onDelete={onDelete}
              onDragStart={onDragStart}
              onDragOver={onDragOver}
              onDrop={onDrop}
              readonly={readonly}
              searchQuery={searchQuery}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Composant principal de l'arbre hiérarchique
export const HierarchicalOrganizationTree: React.FC<HierarchicalTreeProps> = ({
  employerId,
  nodes,
  onNodeAdd,
  onNodeEdit,
  onNodeDelete,
  onNodeMove,
  onSelectionChange,
  searchQuery = '',
  onSearchChange,
  readonly = false,
  showSearch = true,
  maxHeight = '600px'
}) => {
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [selectedNodes, setSelectedNodes] = useState<Set<number>>(new Set());
  const [draggedNode, setDraggedNode] = useState<number | null>(null);
  const [internalSearchQuery, setInternalSearchQuery] = useState('');

  // Utiliser la recherche interne si pas de contrôle externe
  const effectiveSearchQuery = onSearchChange ? searchQuery : internalSearchQuery;
  const handleSearchChange = onSearchChange || setInternalSearchQuery;

  // Filtrage des nœuds selon la recherche
  const filteredNodes = useMemo(() => {
    if (!effectiveSearchQuery.trim()) return nodes;

    const filterNodeRecursive = (node: OrganizationalNode): OrganizationalNode | null => {
      const matchesSearch = 
        node.name.toLowerCase().includes(effectiveSearchQuery.toLowerCase()) ||
        (node.code && node.code.toLowerCase().includes(effectiveSearchQuery.toLowerCase()));

      const filteredChildren = node.children
        ?.map(child => filterNodeRecursive(child))
        .filter(Boolean) as OrganizationalNode[] || [];

      if (matchesSearch || filteredChildren.length > 0) {
        return {
          ...node,
          children: filteredChildren
        };
      }

      return null;
    };

    return nodes
      .map(node => filterNodeRecursive(node))
      .filter(Boolean) as OrganizationalNode[];
  }, [nodes, effectiveSearchQuery]);

  // Construction de l'arbre hiérarchique
  const treeData = useMemo(() => {
    return buildTreeStructure(filteredNodes);
  }, [filteredNodes]);

  // Gestion de l'expansion
  const handleToggleExpand = useCallback((nodeId: number) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  }, []);

  // Gestion de la sélection
  const handleNodeSelect = useCallback((nodeId: number, multiSelect: boolean) => {
    setSelectedNodes(prev => {
      const newSet = new Set(prev);
      
      if (multiSelect) {
        if (newSet.has(nodeId)) {
          newSet.delete(nodeId);
        } else {
          newSet.add(nodeId);
        }
      } else {
        newSet.clear();
        newSet.add(nodeId);
      }
      
      onSelectionChange?.(Array.from(newSet));
      return newSet;
    });
  }, [onSelectionChange]);

  // Gestion du drag & drop
  const handleDragStart = useCallback((nodeId: number) => {
    setDraggedNode(nodeId);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, nodeId: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetNodeId: number) => {
    e.preventDefault();
    
    if (draggedNode && draggedNode !== targetNodeId) {
      onNodeMove(draggedNode, targetNodeId);
    }
    
    setDraggedNode(null);
  }, [draggedNode, onNodeMove]);

  // Expansion automatique lors de la recherche
  React.useEffect(() => {
    if (effectiveSearchQuery.trim()) {
      // Étendre tous les nœuds qui ont des résultats
      const nodesToExpand = new Set<number>();
      
      const collectExpandableNodes = (nodes: OrganizationalNode[]) => {
        nodes.forEach(node => {
          if (node.children && node.children.length > 0) {
            nodesToExpand.add(node.id);
            collectExpandableNodes(node.children);
          }
        });
      };
      
      collectExpandableNodes(filteredNodes);
      setExpandedNodes(nodesToExpand);
    }
  }, [effectiveSearchQuery, filteredNodes]);

  return (
    <div className="hierarchical-tree">
      {/* En-tête */}
      <div className="flex items-center justify-between mb-4 p-4 bg-gray-50 rounded-lg border">
        <div className="flex items-center gap-2">
          <BuildingOfficeIcon className="h-6 w-6 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Structure Organisationnelle
          </h3>
          <span className="text-sm text-gray-500">
            ({nodes.length} nœud{nodes.length > 1 ? 's' : ''})
          </span>
        </div>

        <div className="flex items-center gap-2">
          {!readonly && (
            <button
              onClick={() => onNodeAdd(null, 'etablissement')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Ajouter Établissement
            </button>
          )}
        </div>
      </div>

      {/* Barre de recherche */}
      {showSearch && (
        <div className="mb-4">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher dans la hiérarchie..."
              value={effectiveSearchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      )}

      {/* Contenu de l'arbre */}
      <div 
        className="tree-content overflow-auto border border-gray-200 rounded-lg bg-white"
        style={{ maxHeight }}
      >
        {treeData.length > 0 ? (
          <div className="p-4 space-y-2">
            {treeData.map(node => (
              <TreeNode
                key={node.id}
                node={node}
                level={0}
                expandedNodes={expandedNodes}
                selectedNodes={selectedNodes}
                onToggleExpand={handleToggleExpand}
                onSelect={handleNodeSelect}
                onAdd={onNodeAdd}
                onEdit={onNodeEdit}
                onDelete={onNodeDelete}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                readonly={readonly}
                searchQuery={effectiveSearchQuery}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <BuildingOfficeIcon className="h-12 w-12 mb-4 text-gray-300" />
            <p className="text-lg font-medium mb-2">Aucune structure organisationnelle</p>
            <p className="text-sm text-center mb-4">
              {effectiveSearchQuery.trim() 
                ? `Aucun résultat pour "${effectiveSearchQuery}"`
                : "Commencez par créer un établissement"
              }
            </p>
            {!readonly && !effectiveSearchQuery.trim() && (
              <button
                onClick={() => onNodeAdd(null, 'etablissement')}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                Créer le premier établissement
              </button>
            )}
          </div>
        )}
      </div>

      {/* Informations sur la sélection */}
      {selectedNodes.size > 0 && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            {selectedNodes.size} élément{selectedNodes.size > 1 ? 's' : ''} sélectionné{selectedNodes.size > 1 ? 's' : ''}
          </p>
        </div>
      )}
    </div>
  );
};

// Fonction utilitaire pour construire la structure arborescente
function buildTreeStructure(nodes: OrganizationalNode[]): OrganizationalNode[] {
  // Créer un mapping des nœuds par ID
  const nodeMap = new Map<number, OrganizationalNode>();
  const rootNodes: OrganizationalNode[] = [];

  // Première passe : créer le mapping
  nodes.forEach(node => {
    nodeMap.set(node.id, { ...node, children: [] });
  });

  // Deuxième passe : construire les relations parent-enfant
  nodes.forEach(node => {
    const nodeWithChildren = nodeMap.get(node.id)!;
    
    if (node.parent_id === null) {
      // Nœud racine
      rootNodes.push(nodeWithChildren);
    } else {
      // Nœud enfant
      const parent = nodeMap.get(node.parent_id);
      if (parent) {
        parent.children = parent.children || [];
        parent.children.push(nodeWithChildren);
      }
    }
  });

  // Trier les nœuds par sort_order puis par nom
  const sortNodes = (nodes: OrganizationalNode[]) => {
    nodes.sort((a, b) => {
      if (a.sort_order !== b.sort_order) {
        return a.sort_order - b.sort_order;
      }
      return a.name.localeCompare(b.name);
    });
    
    nodes.forEach(node => {
      if (node.children && node.children.length > 0) {
        sortNodes(node.children);
      }
    });
  };

  sortNodes(rootNodes);
  return rootNodes;
}

export default HierarchicalOrganizationTree;