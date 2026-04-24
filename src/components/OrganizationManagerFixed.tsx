import React, { useCallback, useState } from 'react';
import { 
  BuildingOfficeIcon, 
  UsersIcon, 
  PlusIcon, 
  ChevronRightIcon,
  ChevronDownIcon,
  ArrowPathIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/24/outline';
import { useOrganization, type OrganizationTreeNode, type CreateUnitData } from '../hooks/useOrganization';
import { api } from '../api';
import { useWorkerData } from '../hooks/useConstants';

interface OrganizationManagerProps {
  employerId: number;
}

interface Worker {
  id: number;
  matricule: string;
  nom: string;
  prenom: string;
  poste: string;
  current_unit_id?: number | null;
  is_unassigned?: boolean;
}

const getWorkerDisplayName = (worker: Pick<Worker, 'nom' | 'prenom'>) =>
  `${worker.nom || ''} ${worker.prenom || ''}`.trim() || 'Salarie';

interface RawWorkerResponse {
  id: number;
  matricule?: string;
  nom?: string;
  prenom?: string;
  poste?: string;
  organizational_unit_id?: number | null;
}

const WorkerDisplayRow: React.FC<{ worker: Worker; tone?: "neutral" | "warning" }> = ({ worker, tone = "neutral" }) => {
  const { data: workerData } = useWorkerData(worker.id);
  const label = `${workerData?.nom || worker.nom} ${workerData?.prenom || worker.prenom}`.trim() || getWorkerDisplayName(worker);
  const meta = [
    workerData?.matricule || worker.matricule || 'Sans matricule',
    workerData?.poste || worker.poste || 'Poste non renseigne',
    workerData?.departement,
  ]
    .filter(Boolean)
    .join(' - ');
  return (
    <div className={tone === "warning" ? "text-sm text-amber-700 bg-amber-100 px-2 py-1 rounded" : "text-sm text-slate-600 bg-slate-50 px-2 py-1 rounded"}>
      {meta} ({label})
    </div>
  );
};

const LEVEL_LABELS = {
  etablissement: 'Établissement',
  departement: 'Département', 
  service: 'Service',
  unite: 'Unité'
};

const LEVEL_ICONS = {
  etablissement: '🏢',
  departement: '🏬', 
  service: '🏪',
  unite: '🏠'
};

// Composant d'arbre simplifié (non récursif pour éviter les problèmes)
const OrganizationTreeDisplay: React.FC<{
  nodes: OrganizationTreeNode[];
  onCreateChild: (parentId: number) => void;
  onEditUnit: (unitId: number, unitData: OrganizationTreeNode) => void;
  onDeleteUnit: (unitId: number, unitName: string) => void;
  onAssignWorker: (unitId: number) => void;
  level?: number;
  visitedNodeIds?: Set<number>;
}> = ({ nodes, onCreateChild, onEditUnit, onDeleteUnit, onAssignWorker, level = 0, visitedNodeIds }) => {
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const currentVisited = visitedNodeIds ?? new Set<number>();

  const toggleExpanded = (nodeId: number) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  return (
    <div className={level > 0 ? "ml-6 border-l-2 border-slate-200 pl-4" : ""}>
      {nodes.map(node => (
        currentVisited.has(node.id) ? (
          <div key={`cycle-${node.id}`} className="mb-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            Cycle détecté sur l&apos;unité {node.name}. La branche a été interrompue pour éviter une boucle infinie.
          </div>
        ) : (
        <div key={node.id} className="mb-2">
          <div className="flex items-center justify-between p-3 bg-white rounded-lg shadow-sm border border-slate-100">
            <div className="flex items-center gap-3">
              {node.children.length > 0 && (
                <button
                  onClick={() => toggleExpanded(node.id)}
                  className="p-1 hover:bg-slate-100 rounded"
                >
                  {expandedNodes.has(node.id) ? (
                    <ChevronDownIcon className="h-4 w-4 text-slate-500" />
                  ) : (
                    <ChevronRightIcon className="h-4 w-4 text-slate-500" />
                  )}
                </button>
              )}
              
              <div className="flex items-center gap-2">
                <span className="text-lg">{LEVEL_ICONS[node.level as keyof typeof LEVEL_ICONS]}</span>
                <div>
                  <h4 className="font-semibold text-slate-800">{node.name}</h4>
                  <p className="text-xs text-slate-500">
                    {LEVEL_LABELS[node.level as keyof typeof LEVEL_LABELS]} • {node.code}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 text-sm text-slate-600">
                <UsersIcon className="h-4 w-4" />
                <span>{node.direct_workers.length}</span>
                {node.total_workers > node.direct_workers.length && (
                  <span className="text-slate-400">({node.total_workers} total)</span>
                )}
              </div>
              
              <button
                onClick={() => onCreateChild(node.id)}
                className="p-1 text-primary-600 hover:bg-primary-50 rounded"
                title="Ajouter une sous-unité"
              >
                <PlusIcon className="h-4 w-4" />
              </button>
              
              <button
                onClick={() => onEditUnit(node.id, node)}
                className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                title="Modifier cette unité"
              >
                <PencilIcon className="h-4 w-4" />
              </button>
              
              <button
                onClick={() => onDeleteUnit(node.id, node.name)}
                className="p-1 text-red-600 hover:bg-red-50 rounded"
                title="Supprimer cette unité"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
              
              <button
                onClick={() => onAssignWorker(node.id)}
                className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                title="Assigner des salariés"
              >
                <UsersIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Salariés directs */}
          {node.direct_workers.length > 0 && (
            <div className="ml-6 mb-2">
              <div className="text-xs font-medium text-slate-500 mb-1">Salariés :</div>
              <div className="grid grid-cols-1 gap-1">
                {node.direct_workers.map(worker => (
                  <WorkerDisplayRow key={worker.id} worker={worker} />
                ))}
              </div>
            </div>
          )}

          {/* Enfants (rendu conditionnel, pas récursif) */}
          {expandedNodes.has(node.id) && node.children.length > 0 && level < 12 && (
            <OrganizationTreeDisplay
              nodes={node.children}
              onCreateChild={onCreateChild}
              onEditUnit={onEditUnit}
              onDeleteUnit={onDeleteUnit}
              onAssignWorker={onAssignWorker}
              level={level + 1}
              visitedNodeIds={new Set([...currentVisited, node.id])}
            />
          )}
          {expandedNodes.has(node.id) && node.children.length > 0 && level >= 12 && (
            <div className="ml-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Profondeur maximale atteinte. La branche a été tronquée pour préserver la stabilité.
            </div>
          )}
        </div>
        )
      ))}
    </div>
  );
};

// Modale de création
const CreateUnitModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateUnitData) => void;
  parentId?: number;
  possibleLevels: string[];
}> = ({ isOpen, onClose, onSubmit, parentId, possibleLevels }) => {
  const [formData, setFormData] = useState<CreateUnitData>({
    level: (possibleLevels[0] as CreateUnitData['level']) || 'etablissement',
    name: '',
    code: '',
    parent_id: parentId,
    description: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
    onClose();
    setFormData({
      level: (possibleLevels[0] as CreateUnitData['level']) || 'etablissement',
      name: '',
      code: '',
      parent_id: parentId,
      description: ''
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-slate-100">
          <h3 className="text-xl font-bold text-slate-800">Créer une nouvelle unité</h3>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Type d'unité
            </label>
            <select
              value={formData.level}
              onChange={(e) => setFormData({ ...formData, level: e.target.value as CreateUnitData['level'] })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            >
              {possibleLevels.map(level => (
                <option key={level} value={level}>
                  {LEVEL_LABELS[level as keyof typeof LEVEL_LABELS]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Nom
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Code
            </label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Description (optionnelle)
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Créer
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Modale d'assignation des salariés
const WorkerAssignmentModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  employerId: number;
  unitId: number;
  unitName: string;
  organizationTree: OrganizationTreeNode[];
  onAssign: (workerId: number, unitId: number | null) => void;
}> = ({ isOpen, onClose, employerId, unitId, unitName, organizationTree, onAssign }) => {
  const [availableWorkers, setAvailableWorkers] = useState<Worker[]>([]);
  const [selectedWorkers, setSelectedWorkers] = useState<number[]>([]);
  const [selectedTargetUnit, setSelectedTargetUnit] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // Collecter toutes les unités disponibles pour la réassignation
  const [allUnits, setAllUnits] = useState<{id: number, name: string, level: string}[]>([]);

  React.useEffect(() => {
    if (isOpen && unitId === 0) {
      // Collecter toutes les unités pour la réassignation
      const units: {id: number, name: string, level: string}[] = [];
      
      const collectUnits = (nodes: OrganizationTreeNode[]) => {
        for (const node of nodes) {
          units.push({
            id: node.id,
            name: node.name,
            level: node.level
          });
          collectUnits(node.children);
        }
      };
      
      collectUnits(organizationTree);
      setAllUnits(units);
    }
  }, [isOpen, unitId, organizationTree]);

  const loadAvailableWorkers = useCallback(async () => {
    try {
      setLoading(true);

      if (unitId === 0) {
        const response = await api.get(`/organization/employers/${employerId}/tree`);
        const treeData = response.data as { orphan_workers?: RawWorkerResponse[] };
        const orphanWorkers = treeData.orphan_workers || [];

        const formattedWorkers = orphanWorkers.map((worker: RawWorkerResponse) => ({
          id: worker.id,
          matricule: worker.matricule || '',
          nom: worker.nom || '',
          prenom: worker.prenom || '',
          poste: worker.poste || '',
          current_unit_id: null,
          is_unassigned: true,
        }));

        setAvailableWorkers(formattedWorkers);
      } else {
        const response = await api.get(`/organization/units/${unitId}/available-workers`);
        setAvailableWorkers((response.data.workers || []) as Worker[]);
      }
    } catch {
      try {
        const response = await api.get('/workers');
        const allWorkers = (response.data || []) as RawWorkerResponse[];

        const formattedWorkers = allWorkers.map((worker: RawWorkerResponse) => ({
          id: worker.id,
          matricule: worker.matricule || '',
          nom: worker.nom || '',
          prenom: worker.prenom || '',
          poste: worker.poste || '',
          current_unit_id: worker.organizational_unit_id ?? null,
          is_unassigned: worker.organizational_unit_id == null,
        }));

        setAvailableWorkers(formattedWorkers);
      } catch {
        setAvailableWorkers([]);
      }
    } finally {
      setLoading(false);
    }
  }, [employerId, unitId]);

  React.useEffect(() => {
    if (isOpen) {
      void loadAvailableWorkers();
    }
  }, [isOpen, loadAvailableWorkers]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedWorkers.length === 0) {
      alert('Veuillez sélectionner au moins un salarié');
      return;
    }

    // Pour la réassignation des orphelins, vérifier qu'une unité cible est sélectionnée
    if (unitId === 0 && !selectedTargetUnit) {
      alert('Veuillez sélectionner une unité de destination');
      return;
    }

    // Assigner tous les salariés sélectionnés
    const targetUnitId = unitId === 0 ? selectedTargetUnit : unitId;
    const assignmentPromises = selectedWorkers.map(workerId => {
      return onAssign(workerId, targetUnitId);
    });

    // Attendre que toutes les assignations soient terminées
    Promise.all(assignmentPromises).then(() => {
      // Réinitialiser et fermer automatiquement
      setSelectedWorkers([]);
      setSelectedTargetUnit(null);
      // La modale sera fermée par le parent après rafraîchissement
    });
  };

  const toggleWorkerSelection = (workerId: number) => {
    setSelectedWorkers(prev => 
      prev.includes(workerId) 
        ? prev.filter(id => id !== workerId)
        : [...prev, workerId]
    );
  };

  const selectAllWorkers = () => {
    setSelectedWorkers(availableWorkers.map(w => w.id));
  };

  const clearSelection = () => {
    setSelectedWorkers([]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-slate-100">
          <h3 className="text-xl font-bold text-slate-800">
            {unitId === 0 ? 'Réassigner les salariés orphelins' : 'Assigner des salariés'}
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            {unitId === 0 
              ? 'Sélectionnez les salariés non assignés à réassigner à une unité'
              : `Unité : ${unitName}`
            }
          </p>
        </div>
        
        {loading ? (
          <div className="p-8 text-center">
            <ArrowPathIcon className="h-8 w-8 animate-spin text-primary-600 mx-auto mb-2" />
            <p>Chargement des salariés...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col h-full">
            <div className="flex-1 p-6 overflow-y-auto">
              {/* Sélection de l'unité de destination pour les orphelins */}
              {unitId === 0 && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Unité de destination
                  </label>
                  <select
                    value={selectedTargetUnit || ''}
                    onChange={(e) => setSelectedTargetUnit(Number(e.target.value) || null)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    required
                  >
                    <option value="">-- Sélectionner une unité --</option>
                    {allUnits.map(unit => (
                      <option key={unit.id} value={unit.id}>
                        {unit.name} ({unit.level})
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-slate-500 mt-1">
                    Choisissez l'unité où assigner les salariés sélectionnés
                  </p>
                </div>
              )}
              
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-slate-700">
                  {unitId === 0 
                    ? `Salariés non assignés (${availableWorkers.length})`
                    : `Salariés disponibles (${availableWorkers.length})`
                  }
                  <span className="text-sm font-normal text-slate-500 ml-2">
                    {unitId === 0 
                      ? '(Salariés sans unité organisationnelle)'
                      : '(Exclut les salariés déjà assignés à cette unité)'
                    }
                  </span>
                </h4>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={selectAllWorkers}
                    className="text-xs px-2 py-1 text-primary-600 hover:bg-primary-50 rounded"
                  >
                    Tout sélectionner
                  </button>
                  <button
                    type="button"
                    onClick={clearSelection}
                    className="text-xs px-2 py-1 text-slate-600 hover:bg-slate-100 rounded"
                  >
                    Tout désélectionner
                  </button>
                </div>
              </div>
              
              {availableWorkers.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  Aucun salarié disponible
                </div>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto border border-slate-200 rounded-lg p-3">
                  {availableWorkers.map(worker => (
                    <label
                      key={worker.id}
                      className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedWorkers.includes(worker.id)}
                        onChange={() => toggleWorkerSelection(worker.id)}
                        className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="flex-1">
                        <div className="font-medium text-slate-800">
                          {getWorkerDisplayName(worker)}
                        </div>
                        <div className="text-sm text-slate-500">
                          <span className="block"><WorkerDisplayRow worker={worker} /></span>
                          {worker.current_unit_id ? (
                            <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                              Assigné à une autre unité
                            </span>
                          ) : (
                            <span className="ml-2 px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs">
                              Non assigné
                            </span>
                          )}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-between items-center p-6 border-t border-slate-100 bg-slate-50">
              <div className="text-sm text-slate-600">
                {selectedWorkers.length} salarié(s) sélectionné(s)
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={selectedWorkers.length === 0}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {unitId === 0 
                    ? `Réassigner (${selectedWorkers.length})`
                    : `Assigner (${selectedWorkers.length})`
                  }
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

// Modale d'édition
const EditUnitModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<CreateUnitData>) => void;
  unitData: OrganizationTreeNode | null;
}> = ({ isOpen, onClose, onSubmit, unitData }) => {
  const [formData, setFormData] = useState<Partial<CreateUnitData>>({
    name: '',
    code: '',
    description: ''
  });

  React.useEffect(() => {
    if (unitData) {
      setFormData({
        name: unitData.name,
        code: unitData.code,
        description: unitData.description || ''
      });
    }
  }, [unitData]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
    onClose();
  };

  if (!isOpen || !unitData) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-slate-100">
          <h3 className="text-xl font-bold text-slate-800">Modifier l'unité</h3>
          <p className="text-sm text-slate-500 mt-1">
            {LEVEL_LABELS[unitData.level as keyof typeof LEVEL_LABELS]}
          </p>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Nom
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Code
            </label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Description (optionnelle)
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Modifier
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const OrganizationManagerFixed: React.FC<OrganizationManagerProps> = ({ employerId }) => {
  const {
    organizationTree,
    loading,
    error,
    createUnit,
    updateUnit,
    deleteUnit,
    fetchOrganizationTree,
    getPossibleChildLevels,
    assignWorkerToUnit
  } = useOrganization(employerId);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<number | undefined>();
  const [selectedUnitForEdit, setSelectedUnitForEdit] = useState<OrganizationTreeNode | null>(null);
  const [selectedUnitForAssign, setSelectedUnitForAssign] = useState<{id: number, name: string} | null>(null);
  const [possibleLevels, setPossibleLevels] = useState<string[]>([]);
  const currentTreeMatchesEmployer = organizationTree?.employer_id === employerId;

  React.useEffect(() => {
    setIsCreateModalOpen(false);
    setIsEditModalOpen(false);
    setIsAssignModalOpen(false);
    setSelectedParentId(undefined);
    setSelectedUnitForEdit(null);
    setSelectedUnitForAssign(null);
    setPossibleLevels([]);
  }, [employerId]);

  const handleCreateUnit = async (parentId?: number) => {
    const levels = await getPossibleChildLevels(parentId);
    if (levels.length === 0) {
      alert('Aucun niveau supplémentaire ne peut être créé à ce niveau.');
      return;
    }
    
    setPossibleLevels(levels);
    setSelectedParentId(parentId);
    setIsCreateModalOpen(true);
  };

  const handleSubmitUnit = async (data: CreateUnitData) => {
    const result = await createUnit(employerId, data);
    if (result) {
      alert('Unité créée avec succès !');
      // Rafraîchir automatiquement l'arbre après création
      await fetchOrganizationTree(employerId);
    }
  };

  const handleEditUnit = (_unitId: number, unitData: OrganizationTreeNode) => {
    setSelectedUnitForEdit(unitData);
    setIsEditModalOpen(true);
  };

  const handleSubmitEditUnit = async (data: Partial<CreateUnitData>) => {
    if (!selectedUnitForEdit) return;
    
    const result = await updateUnit(selectedUnitForEdit.id, data);
    if (result) {
      alert('Unité modifiée avec succès !');
      setSelectedUnitForEdit(null);
    }
  };

  const handleDeleteUnit = async (unitId: number, unitName: string) => {
    if (confirm(`Êtes-vous sûr de vouloir supprimer l'unité "${unitName}" ?\n\nCette action est irréversible et ne peut être effectuée que si l'unité ne contient aucun salarié ni sous-unité.`)) {
      const result = await deleteUnit(unitId);
      if (result) {
        alert('Unité supprimée avec succès !');
        await fetchOrganizationTree(employerId);
      }
    }
  };

  const handleAssignWorker = async (unitId: number) => {
    // Trouver l'unité dans l'arbre pour obtenir son nom
    const findUnit = (nodes: OrganizationTreeNode[], id: number): OrganizationTreeNode | null => {
      for (const node of nodes) {
        if (node.id === id) return node;
        const found = findUnit(node.children, id);
        if (found) return found;
      }
      return null;
    };

    const unit = findUnit(organizationTree?.root_units || [], unitId);
    if (unit) {
      setSelectedUnitForAssign({ id: unitId, name: unit.name });
      setIsAssignModalOpen(true);
    } else {
      alert('Unité non trouvée');
    }
  };

  const handleWorkerAssignment = async (workerId: number, unitId: number | null) => {
    const result = await assignWorkerToUnit(workerId, unitId || undefined);
    if (result) {
      // Rafraîchissement immédiat et forcé de l'arbre organisationnel
      await fetchOrganizationTree(employerId);
      alert('Salarié assigné avec succès !');
      
      // Fermer la modale pour forcer un rechargement propre
      setIsAssignModalOpen(false);
      setSelectedUnitForAssign(null);
    }
  };

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BuildingOfficeIcon className="h-8 w-8 text-primary-600" />
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Structure Organisationnelle</h2>
            <p className="text-slate-600">
              {organizationTree?.total_workers || 0} salariés au total
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {loading && (
            <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">
              <ArrowPathIcon className="h-4 w-4 animate-spin text-primary-600" />
              Chargement...
            </div>
          )}
          <button
            onClick={() => handleCreateUnit()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
          >
            <PlusIcon className="h-4 w-4" />
            Créer une unité racine
          </button>
        </div>
      </div>

      {/* Arbre organisationnel */}
      <div className="bg-slate-50 rounded-xl p-6">
        {!currentTreeMatchesEmployer && loading ? (
          <div className="py-16">
            <div className="mx-auto flex max-w-md items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-6 text-slate-600 shadow-sm">
              <ArrowPathIcon className="h-6 w-6 animate-spin text-primary-600" />
              Chargement de la structure organisationnelle...
            </div>
          </div>
        ) : !organizationTree || (organizationTree.root_units.length === 0 && organizationTree.orphan_workers.length === 0) ? (
          <div className="text-center py-12">
            <BuildingOfficeIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-600 mb-2">
              Aucune structure organisationnelle
            </h3>
            <p className="text-slate-500 mb-4">
              Commencez par créer un établissement.
            </p>
            <button
              onClick={() => handleCreateUnit()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Créer le premier établissement
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Unités organisées */}
            {organizationTree.root_units.length > 0 && (
              <OrganizationTreeDisplay
                nodes={organizationTree.root_units}
                onCreateChild={handleCreateUnit}
                onEditUnit={handleEditUnit}
                onDeleteUnit={handleDeleteUnit}
                onAssignWorker={handleAssignWorker}
              />
            )}

            {/* Salariés orphelins */}
            {organizationTree.orphan_workers && organizationTree.orphan_workers.length > 0 && (
              <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <h4 className="font-semibold text-amber-800 mb-2">
                  Salariés non assignés ({organizationTree.orphan_workers.length})
                </h4>
                <div className="grid grid-cols-1 gap-2">
                  {organizationTree.orphan_workers.map(worker => (
                    <WorkerDisplayRow key={worker.id} worker={worker} tone="warning" />
                  ))}
                </div>
                <button
                  onClick={() => {
                    // Créer une unité fictive pour les orphelins
                    setSelectedUnitForAssign({ id: 0, name: 'Salariés non assignés' });
                    setIsAssignModalOpen(true);
                  }}
                  className="mt-3 px-3 py-1 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 transition-colors"
                >
                  Réassigner ces salariés
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal de création */}
      <CreateUnitModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleSubmitUnit}
        parentId={selectedParentId}
        possibleLevels={possibleLevels}
      />

      {/* Modal d'édition */}
      <EditUnitModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedUnitForEdit(null);
        }}
        onSubmit={handleSubmitEditUnit}
        unitData={selectedUnitForEdit}
      />

      {/* Modal d'assignation des salariés */}
      {selectedUnitForAssign && (
        <WorkerAssignmentModal
          isOpen={isAssignModalOpen}
          onClose={() => {
            setIsAssignModalOpen(false);
            setSelectedUnitForAssign(null);
          }}
          employerId={employerId}
          unitId={selectedUnitForAssign.id}
          unitName={selectedUnitForAssign.name}
          organizationTree={organizationTree?.root_units || []}
          onAssign={handleWorkerAssignment}
        />
      )}
    </div>
  );
};
