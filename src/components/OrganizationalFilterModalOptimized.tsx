/**
 * Modal de Filtrage Organisationnel Optimisé
 * Version professionnelle avec intégration du référentiel hiérarchique
 */
import { useState, useEffect } from 'react';
import { api } from '../api';
import { 
  BuildingOfficeIcon, 
  FunnelIcon,
  XMarkIcon,
  CheckIcon,
  UserGroupIcon,
  ChevronRightIcon,
  InformationCircleIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { useQuery, useQueryClient } from '@tanstack/react-query';

export interface OrganizationalFilters {
  etablissement?: string;
  departement?: string;
  service?: string;
  unite?: string;
}

interface OrganizationalFilterModalOptimizedProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (employerId: number, filters: OrganizationalFilters | null) => void;
  defaultEmployerId?: number;
  actionTitle: string;
  actionDescription: string;
  actionIcon?: React.ReactNode;
}

interface Employer {
  id: number;
  raison_sociale: string;
}

interface CascadingOption {
  id: number;
  name: string;
  code?: string;
  level: string;
  parent_id?: number | null;
  path?: string;
}

export const OrganizationalFilterModalOptimized: React.FC<OrganizationalFilterModalOptimizedProps> = ({
  isOpen,
  onClose,
  onConfirm,
  defaultEmployerId,
  actionTitle,
  actionDescription,
  actionIcon
}) => {
  const [selectedEmployerId, setSelectedEmployerId] = useState<number>(defaultEmployerId || 0);
  const [selectedEtablissement, setSelectedEtablissement] = useState<number | null>(null);
  const [selectedDepartement, setSelectedDepartement] = useState<number | null>(null);
  const [selectedService, setSelectedService] = useState<number | null>(null);
  const [selectedUnite, setSelectedUnite] = useState<number | null>(null);
  const [useFilters, setUseFilters] = useState(false);

  // Accès au client React Query pour invalider le cache
  const queryClient = useQueryClient();

  // Charger la liste des employeurs
  const { data: employers = [] } = useQuery<Employer[]>({
    queryKey: ['employers'],
    queryFn: async () => {
      const response = await api.get('/employers');
      return response.data;
    },
    enabled: isOpen,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false
  });

  // Charger les établissements (niveau racine)
  const { data: etablissements = [], isLoading: loadingEtablissements } = useQuery<CascadingOption[]>({
    queryKey: ['cascading-options', selectedEmployerId, null],
    queryFn: async () => {
      console.log(`[MODAL DEBUG] Fetching établissements for employer ${selectedEmployerId}`);
      const response = await api.get(
        `/employers/${selectedEmployerId}/hierarchical-organization/cascading-options`,
        { params: { parent_id: null } }
      );
      console.log(`[MODAL DEBUG] Received ${response.data.length} établissements for employer ${selectedEmployerId}:`, response.data);
      return response.data;
    },
    enabled: isOpen && !!selectedEmployerId && useFilters,
    staleTime: 0, // Toujours considérer les données comme périmées
    gcTime: 0, // Ne pas garder en cache après démontage
    refetchOnMount: 'always', // Toujours refetch au montage
    refetchOnWindowFocus: false // Pas de refetch au focus
  });

  // Charger les départements (enfants de l'établissement sélectionné)
  const { data: departements = [], isLoading: loadingDepartements } = useQuery<CascadingOption[]>({
    queryKey: ['cascading-options', selectedEmployerId, selectedEtablissement],
    queryFn: async () => {
      const response = await api.get(
        `/employers/${selectedEmployerId}/hierarchical-organization/cascading-options`,
        { params: { parent_id: selectedEtablissement } }
      );
      return response.data;
    },
    enabled: isOpen && !!selectedEmployerId && !!selectedEtablissement && useFilters,
    staleTime: 0,
    gcTime: 0
  });

  // Charger les services (enfants du département sélectionné)
  const { data: services = [], isLoading: loadingServices } = useQuery<CascadingOption[]>({
    queryKey: ['cascading-options', selectedEmployerId, selectedDepartement],
    queryFn: async () => {
      const response = await api.get(
        `/employers/${selectedEmployerId}/hierarchical-organization/cascading-options`,
        { params: { parent_id: selectedDepartement } }
      );
      return response.data;
    },
    enabled: isOpen && !!selectedEmployerId && !!selectedDepartement && useFilters,
    staleTime: 0,
    gcTime: 0
  });

  // Charger les unités (enfants du service sélectionné)
  const { data: unites = [], isLoading: loadingUnites } = useQuery<CascadingOption[]>({
    queryKey: ['cascading-options', selectedEmployerId, selectedService],
    queryFn: async () => {
      const response = await api.get(
        `/employers/${selectedEmployerId}/hierarchical-organization/cascading-options`,
        { params: { parent_id: selectedService } }
      );
      return response.data;
    },
    enabled: isOpen && !!selectedEmployerId && !!selectedService && useFilters,
    staleTime: 0,
    gcTime: 0
  });

  // Initialiser l'employeur sélectionné UNIQUEMENT à l'ouverture
  useEffect(() => {
    if (isOpen && employers.length > 0) {
      // N'initialiser que si selectedEmployerId n'est pas déjà défini ou est invalide
      if (!selectedEmployerId || selectedEmployerId === 0) {
        if (defaultEmployerId && defaultEmployerId > 0) {
          setSelectedEmployerId(defaultEmployerId);
        } else {
          setSelectedEmployerId(employers[0].id);
        }
      }
    }
  }, [isOpen, employers]); // Retirer defaultEmployerId et selectedEmployerId des dépendances

  // Réinitialiser les filtres à l'ouverture/fermeture
  useEffect(() => {
    if (isOpen) {
      console.log(`[MODAL DEBUG] Modal opened with employer ${selectedEmployerId}`);
      setSelectedEtablissement(null);
      setSelectedDepartement(null);
      setSelectedService(null);
      setSelectedUnite(null);
      setUseFilters(false);
    } else {
      console.log(`[MODAL DEBUG] Modal closed, clearing cache`);
      // Quand le modal se ferme, invalider le cache pour garantir des données fraîches à la prochaine ouverture
      queryClient.removeQueries({ 
        queryKey: ['cascading-options'],
        exact: false 
      });
      // Réinitialiser l'employeur sélectionné pour la prochaine ouverture
      if (defaultEmployerId && defaultEmployerId > 0) {
        setSelectedEmployerId(defaultEmployerId);
      } else if (employers.length > 0) {
        setSelectedEmployerId(employers[0].id);
      }
    }
  }, [isOpen, queryClient, defaultEmployerId, employers]);

  // Réinitialiser les filtres quand l'employeur change
  useEffect(() => {
    console.log(`[MODAL DEBUG] Employer changed to: ${selectedEmployerId}`);
    
    // Réinitialiser les sélections
    setSelectedEtablissement(null);
    setSelectedDepartement(null);
    setSelectedService(null);
    setSelectedUnite(null);
    
    // CRITIQUE: Invalider tout le cache des options en cascade pour éviter les fuites de données
    // Cela garantit que les données de l'employeur précédent ne sont pas réutilisées
    console.log(`[MODAL DEBUG] Removing all cascading-options queries from cache`);
    queryClient.removeQueries({ 
      queryKey: ['cascading-options'],
      exact: false 
    });
    
    // Force également la réinitialisation des données
    queryClient.setQueryData(['cascading-options', selectedEmployerId, null], []);
    
    console.log(`[MODAL DEBUG] Cache cleared for employer ${selectedEmployerId}`);
  }, [selectedEmployerId, queryClient]);

  // Réinitialiser les niveaux inférieurs quand un niveau supérieur change
  useEffect(() => {
    setSelectedDepartement(null);
    setSelectedService(null);
    setSelectedUnite(null);
  }, [selectedEtablissement]);

  useEffect(() => {
    setSelectedService(null);
    setSelectedUnite(null);
  }, [selectedDepartement]);

  useEffect(() => {
    setSelectedUnite(null);
  }, [selectedService]);

  // Logger quand useFilters change
  useEffect(() => {
    console.log(`[MODAL DEBUG] useFilters changed to: ${useFilters}, employer: ${selectedEmployerId}`);
  }, [useFilters, selectedEmployerId]);

  const handleConfirmAll = () => {
    onConfirm(selectedEmployerId, null);
    onClose();
  };

  const handleConfirmFiltered = () => {
    const filters: OrganizationalFilters = {};
    
    if (selectedEtablissement) filters.etablissement = String(selectedEtablissement);
    if (selectedDepartement) filters.departement = String(selectedDepartement);
    if (selectedService) filters.service = String(selectedService);
    if (selectedUnite) filters.unite = String(selectedUnite);
    
    onConfirm(selectedEmployerId, filters);
    onClose();
  };

  const hasActiveFilters = selectedEtablissement || selectedDepartement || selectedService || selectedUnite;
  const activeFiltersCount = [selectedEtablissement, selectedDepartement, selectedService, selectedUnite]
    .filter(Boolean).length;
  
  const selectedEmployer = employers.find(emp => emp.id === selectedEmployerId);
  const selectedEtablissementData = etablissements.find(e => e.id === selectedEtablissement);
  const selectedDepartementData = departements.find(d => d.id === selectedDepartement);
  const selectedServiceData = services.find(s => s.id === selectedService);
  const selectedUniteData = unites.find(u => u.id === selectedUnite);

  // DEBUG: Log l'état au moment du rendu
  if (isOpen && useFilters) {
    console.log(`[MODAL DEBUG RENDER] Employer: ${selectedEmployerId}, Établissements: ${etablissements.length}`, etablissements);
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-gradient-to-br from-slate-900/70 to-slate-800/70 backdrop-blur-md animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-zoom-in border border-slate-200">
        {/* Header avec gradient */}
        <div className="relative p-6 bg-gradient-to-r from-primary-600 to-primary-700 text-white overflow-hidden">
          <div className="absolute inset-0 bg-grid-white/10"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-4">
              {actionIcon && (
                <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                  {actionIcon}
                </div>
              )}
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  {actionTitle}
                  <SparklesIcon className="h-5 w-5 text-primary-200" />
                </h2>
                <p className="text-primary-100 text-sm mt-1">
                  {actionDescription}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-xl transition-all text-white"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 bg-slate-50">
          <div className="space-y-6">
            {/* Sélection de l'employeur */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <UserGroupIcon className="h-5 w-5 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">
                  Employeur
                </h3>
              </div>
              <select
                value={selectedEmployerId}
                onChange={(e) => setSelectedEmployerId(Number(e.target.value))}
                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm font-medium bg-white shadow-sm transition-all"
              >
                {employers.map((employer) => (
                  <option key={employer.id} value={employer.id}>
                    {employer.raison_sociale}
                  </option>
                ))}
              </select>
              {selectedEmployer && (
                <div className="mt-3 flex items-center gap-2 text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                  <CheckIcon className="h-4 w-4" />
                  <span className="font-medium">{selectedEmployer.raison_sociale}</span>
                </div>
              )}
            </div>

            {/* Options de traitement */}
            <div className="space-y-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-primary-100 rounded-lg">
                  <FunnelIcon className="h-5 w-5 text-primary-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">
                  Périmètre de traitement
                </h3>
              </div>

              {/* Option 1: Traiter tout */}
              <div 
                className={`border-2 rounded-xl p-5 cursor-pointer transition-all ${
                  !useFilters 
                    ? 'border-primary-500 bg-primary-50 shadow-md' 
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
                onClick={() => setUseFilters(false)}
              >
                <label className="flex items-start gap-4 cursor-pointer">
                  <input
                    type="radio"
                    name="filterOption"
                    checked={!useFilters}
                    onChange={() => setUseFilters(false)}
                    className="mt-1 h-5 w-5 text-primary-600 focus:ring-primary-500 border-gray-300"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-slate-800 flex items-center gap-2 text-lg">
                      <BuildingOfficeIcon className="h-5 w-5 text-primary-600" />
                      Tous les salariés
                    </div>
                    <p className="text-sm text-slate-600 mt-2">
                      Traiter l'ensemble des salariés de <strong>{selectedEmployer?.raison_sociale || 'cet employeur'}</strong> sans restriction.
                    </p>
                  </div>
                </label>
              </div>

              {/* Option 2: Appliquer des filtres */}
              <div 
                className={`border-2 rounded-xl p-5 cursor-pointer transition-all ${
                  useFilters 
                    ? 'border-primary-500 bg-primary-50 shadow-md' 
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
                onClick={() => setUseFilters(true)}
              >
                <label className="flex items-start gap-4 cursor-pointer">
                  <input
                    type="radio"
                    name="filterOption"
                    checked={useFilters}
                    onChange={() => setUseFilters(true)}
                    className="mt-1 h-5 w-5 text-primary-600 focus:ring-primary-500 border-gray-300"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-slate-800 flex items-center gap-2 text-lg">
                      <FunnelIcon className="h-5 w-5 text-primary-600" />
                      Filtrage par structure organisationnelle
                      {hasActiveFilters && (
                        <span className="px-3 py-1 bg-primary-600 text-white text-xs font-bold rounded-full">
                          {activeFiltersCount} filtre{activeFiltersCount > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 mt-2 mb-4">
                      Sélectionnez une ou plusieurs structures organisationnelles pour cibler précisément le traitement.
                    </p>

                    {/* Filtres hiérarchiques en cascade */}
                    {useFilters && (
                      <div className="space-y-4 mt-4 p-5 bg-white rounded-xl border border-slate-200">
                        {/* Info sur le filtrage en cascade */}
                        <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                          <div className="text-sm text-blue-800">
                            <p className="font-medium">Filtrage en cascade</p>
                            <p className="text-blue-600 mt-1">
                              Les options se filtrent automatiquement selon votre sélection hiérarchique.
                            </p>
                          </div>
                        </div>

                        {/* Chemin hiérarchique sélectionné */}
                        {hasActiveFilters && (
                          <div className="p-4 bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg border border-primary-200">
                            <p className="text-xs font-medium text-slate-600 mb-2">SÉLECTION ACTUELLE</p>
                            <div className="flex items-center gap-2 flex-wrap text-sm font-medium text-slate-800">
                              {selectedEtablissementData && (
                                <>
                                  <span className="px-3 py-1 bg-white rounded-lg shadow-sm border border-slate-200">
                                    🏢 {selectedEtablissementData.name}
                                  </span>
                                  {selectedDepartementData && <ChevronRightIcon className="h-4 w-4 text-slate-400" />}
                                </>
                              )}
                              {selectedDepartementData && (
                                <>
                                  <span className="px-3 py-1 bg-white rounded-lg shadow-sm border border-slate-200">
                                    🏬 {selectedDepartementData.name}
                                  </span>
                                  {selectedServiceData && <ChevronRightIcon className="h-4 w-4 text-slate-400" />}
                                </>
                              )}
                              {selectedServiceData && (
                                <>
                                  <span className="px-3 py-1 bg-white rounded-lg shadow-sm border border-slate-200">
                                    👥 {selectedServiceData.name}
                                  </span>
                                  {selectedUniteData && <ChevronRightIcon className="h-4 w-4 text-slate-400" />}
                                </>
                              )}
                              {selectedUniteData && (
                                <span className="px-3 py-1 bg-white rounded-lg shadow-sm border border-slate-200">
                                  📦 {selectedUniteData.name}
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Grille de sélection */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Établissement */}
                          <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                              <span className="text-lg">🏢</span>
                              Établissement
                              {/* DEBUG: Afficher le nombre d'établissements */}
                              <span className="text-xs text-gray-500">
                                ({etablissements.length} disponible{etablissements.length > 1 ? 's' : ''})
                              </span>
                            </label>
                            <select
                              key={`etablissement-${selectedEmployerId}`}
                              value={selectedEtablissement || ''}
                              onChange={(e) => {
                                console.log(`[MODAL DEBUG] Établissement selected: ${e.target.value}`);
                                setSelectedEtablissement(e.target.value ? Number(e.target.value) : null);
                              }}
                              disabled={loadingEtablissements}
                              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm bg-white shadow-sm transition-all disabled:bg-slate-100 disabled:cursor-not-allowed"
                            >
                              <option value="">Tous les établissements</option>
                              {etablissements.map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.name} {item.code && `(${item.code})`}
                                </option>
                              ))}
                            </select>
                            {loadingEtablissements && (
                              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                                <div className="animate-spin h-3 w-3 border-2 border-primary-500 border-t-transparent rounded-full"></div>
                                Chargement...
                              </p>
                            )}
                          </div>

                          {/* Département */}
                          <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                              <span className="text-lg">🏬</span>
                              Département
                              {selectedEtablissement && (
                                <span className="text-xs text-blue-600 font-normal">
                                  (filtré)
                                </span>
                              )}
                            </label>
                            <select
                              value={selectedDepartement || ''}
                              onChange={(e) => setSelectedDepartement(e.target.value ? Number(e.target.value) : null)}
                              disabled={!selectedEtablissement || loadingDepartements}
                              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm bg-white shadow-sm transition-all disabled:bg-slate-100 disabled:cursor-not-allowed"
                            >
                              <option value="">
                                {!selectedEtablissement 
                                  ? 'Sélectionnez un établissement' 
                                  : 'Tous les départements'
                                }
                              </option>
                              {departements.map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.name} {item.code && `(${item.code})`}
                                </option>
                              ))}
                            </select>
                            {loadingDepartements && (
                              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                                <div className="animate-spin h-3 w-3 border-2 border-primary-500 border-t-transparent rounded-full"></div>
                                Chargement...
                              </p>
                            )}
                          </div>

                          {/* Service */}
                          <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                              <span className="text-lg">👥</span>
                              Service
                              {selectedDepartement && (
                                <span className="text-xs text-blue-600 font-normal">
                                  (filtré)
                                </span>
                              )}
                            </label>
                            <select
                              value={selectedService || ''}
                              onChange={(e) => setSelectedService(e.target.value ? Number(e.target.value) : null)}
                              disabled={!selectedDepartement || loadingServices}
                              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm bg-white shadow-sm transition-all disabled:bg-slate-100 disabled:cursor-not-allowed"
                            >
                              <option value="">
                                {!selectedDepartement 
                                  ? 'Sélectionnez un département' 
                                  : 'Tous les services'
                                }
                              </option>
                              {services.map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.name} {item.code && `(${item.code})`}
                                </option>
                              ))}
                            </select>
                            {loadingServices && (
                              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                                <div className="animate-spin h-3 w-3 border-2 border-primary-500 border-t-transparent rounded-full"></div>
                                Chargement...
                              </p>
                            )}
                          </div>

                          {/* Unité */}
                          <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                              <span className="text-lg">📦</span>
                              Unité
                              {selectedService && (
                                <span className="text-xs text-blue-600 font-normal">
                                  (filtré)
                                </span>
                              )}
                            </label>
                            <select
                              value={selectedUnite || ''}
                              onChange={(e) => setSelectedUnite(e.target.value ? Number(e.target.value) : null)}
                              disabled={!selectedService || loadingUnites}
                              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm bg-white shadow-sm transition-all disabled:bg-slate-100 disabled:cursor-not-allowed"
                            >
                              <option value="">
                                {!selectedService 
                                  ? 'Sélectionnez un service' 
                                  : 'Toutes les unités'
                                }
                              </option>
                              {unites.map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.name} {item.code && `(${item.code})`}
                                </option>
                              ))}
                            </select>
                            {loadingUnites && (
                              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                                <div className="animate-spin h-3 w-3 border-2 border-primary-500 border-t-transparent rounded-full"></div>
                                Chargement...
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Footer avec actions */}
        <div className="p-6 bg-white border-t border-slate-200 flex justify-between items-center">
          <button
            onClick={onClose}
            className="px-6 py-3 text-slate-600 font-semibold hover:bg-slate-100 rounded-xl transition-all"
          >
            Annuler
          </button>
          
          <div className="flex gap-3">
            {!useFilters ? (
              <button
                onClick={handleConfirmAll}
                className="px-8 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white font-bold rounded-xl hover:from-primary-700 hover:to-primary-800 transition-all shadow-lg flex items-center gap-2"
              >
                <CheckIcon className="h-5 w-5" />
                Traiter tous les salariés
              </button>
            ) : (
              <button
                onClick={handleConfirmFiltered}
                disabled={!hasActiveFilters}
                className="px-8 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white font-bold rounded-xl hover:from-primary-700 hover:to-primary-800 transition-all shadow-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:from-slate-400 disabled:to-slate-500"
              >
                <FunnelIcon className="h-5 w-5" />
                {hasActiveFilters 
                  ? `Appliquer ${activeFiltersCount} filtre${activeFiltersCount > 1 ? 's' : ''}` 
                  : 'Sélectionnez au moins un filtre'
                }
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrganizationalFilterModalOptimized;