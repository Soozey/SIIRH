/**
 * Modale de filtrage organisationnel contextuelle avec sélection d'employeur
 * S'ouvre après clic sur les boutons d'action pour proposer un filtrage optionnel
 */
import { useState, useEffect } from 'react';
import { api } from '../api';
import { 
  BuildingOfficeIcon, 
  FunnelIcon,
  XMarkIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  UserGroupIcon
} from '@heroicons/react/24/outline';

export interface OrganizationalFilters {
  etablissement?: string;
  departement?: string;
  service?: string;
  unite?: string;
}

interface OrganizationalFilterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (employerId: number, filters: OrganizationalFilters | null) => void;
  defaultEmployerId?: number;
  actionTitle: string;
  actionDescription: string;
  actionIcon?: React.ReactNode;
}

interface OrganizationalData {
  etablissements: string[];
  departements: string[];
  services: string[];
  unites: string[];
}

interface Employer {
  id: number;
  raison_sociale: string;
}

export const OrganizationalFilterModal: React.FC<OrganizationalFilterModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  defaultEmployerId,
  actionTitle,
  actionDescription,
  actionIcon
}) => {
  const [selectedEmployerId, setSelectedEmployerId] = useState<number>(defaultEmployerId || 0);
  const [filters, setFilters] = useState<OrganizationalFilters>({});
  const [orgData, setOrgData] = useState<OrganizationalData>({
    etablissements: [],
    departements: [],
    services: [],
    unites: []
  });
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [useFilters, setUseFilters] = useState(false);

  // Charger la liste des employeurs
  useEffect(() => {
    if (!isOpen) return;
    
    const fetchEmployers = async () => {
      try {
        const response = await api.get('/employers');
        setEmployers(response.data);
        
        // Si pas d'employeur par défaut, sélectionner le premier
        if (!defaultEmployerId && response.data.length > 0) {
          setSelectedEmployerId(response.data[0].id);
        }
      } catch (error) {
        console.error('Erreur chargement employeurs:', error);
      }
    };

    fetchEmployers();
  }, [isOpen, defaultEmployerId]);

  // Charger les données organisationnelles quand l'employeur change
  useEffect(() => {
    if (!isOpen || !selectedEmployerId) return;
    
    const fetchOrgData = async () => {
      setIsLoading(true);
      try {
        // Essayer d'abord les données hiérarchiques (nouvelles structures)
        let response = await api.get(`/employers/${selectedEmployerId}/organizational-data/hierarchical`);
        let orgData = response.data;
        
        // Si aucune donnée hiérarchique, utiliser les données des salariés (fallback)
        const hasHierarchicalData = Object.values(orgData).some((arr) => (arr as string[]).length > 0);
        
        if (!hasHierarchicalData) {
          console.log('Aucune structure hiérarchique trouvée, utilisation des données des salariés');
          response = await api.get(`/employers/${selectedEmployerId}/organizational-data/workers`);
          orgData = response.data;
        }
        
        setOrgData(orgData);
      } catch (error) {
        console.error('Erreur chargement données organisationnelles:', error);
        // Réinitialiser les données en cas d'erreur
        setOrgData({
          etablissements: [],
          departements: [],
          services: [],
          unites: []
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrgData();
  }, [isOpen, selectedEmployerId]);

  // Charger les données filtrées quand les filtres changent (filtrage en cascade)
  useEffect(() => {
    if (!isOpen || !selectedEmployerId) return;
    
    const fetchFilteredData = async () => {
      try {
        const params: any = {};
        if (filters.etablissement) params.etablissement = filters.etablissement;
        if (filters.departement) params.departement = filters.departement;
        if (filters.service) params.service = filters.service;
        
        // Essayer d'abord l'endpoint hiérarchique filtré
        let response = await api.get(`/employers/${selectedEmployerId}/organizational-data/hierarchical-filtered`, {
          params
        });
        
        let filteredData = response.data;
        
        // Si aucune donnée hiérarchique filtrée, utiliser l'ancien endpoint (fallback)
        const hasFilteredData = Object.values(filteredData).some((arr) => (arr as string[]).length > 0);
        
        if (!hasFilteredData) {
          console.log('Aucune donnée hiérarchique filtrée, utilisation du filtrage des salariés');
          response = await api.get(`/employers/${selectedEmployerId}/organizational-data/filtered`, {
            params
          });
          filteredData = response.data;
        }
        
        // Mettre à jour seulement les niveaux inférieurs selon la logique de cascade
        setOrgData(prevData => ({
          etablissements: prevData.etablissements, // Garder la liste complète des établissements
          departements: filters.etablissement ? filteredData.departements : prevData.departements,
          services: (filters.etablissement || filters.departement) ? filteredData.services : prevData.services,
          unites: (filters.etablissement || filters.departement || filters.service) ? filteredData.unites : prevData.unites
        }));
      } catch (error) {
        console.error('Erreur chargement données filtrées:', error);
      }
    };

    // Déclencher le filtrage seulement si au moins un filtre est appliqué
    if (filters.etablissement || filters.departement || filters.service) {
      fetchFilteredData();
    }
  }, [isOpen, selectedEmployerId, filters.etablissement, filters.departement, filters.service]);

  // Réinitialiser l'état à l'ouverture
  useEffect(() => {
    if (isOpen) {
      setFilters({});
      setUseFilters(false);
      if (defaultEmployerId) {
        setSelectedEmployerId(defaultEmployerId);
      }
    }
  }, [isOpen, defaultEmployerId]);

  // Réinitialiser les filtres quand l'employeur change
  useEffect(() => {
    setFilters({});
  }, [selectedEmployerId]);

  const handleFilterChange = (field: keyof OrganizationalFilters, value: string) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      
      // Mettre à jour le champ sélectionné
      newFilters[field] = value || undefined;
      
      // Réinitialiser les filtres inférieurs quand un filtre supérieur change
      if (field === 'etablissement') {
        // Si l'établissement change, réinitialiser département, service et unité
        newFilters.departement = undefined;
        newFilters.service = undefined;
        newFilters.unite = undefined;
      } else if (field === 'departement') {
        // Si le département change, réinitialiser service et unité
        newFilters.service = undefined;
        newFilters.unite = undefined;
      } else if (field === 'service') {
        // Si le service change, réinitialiser unité
        newFilters.unite = undefined;
      }
      
      return newFilters;
    });
  };

  const handleConfirmAll = () => {
    onConfirm(selectedEmployerId, null); // null = pas de filtres, traiter tout
    onClose();
  };

  const handleConfirmFiltered = () => {
    const activeFilters = Object.fromEntries(
      Object.entries(filters).filter(([_, value]) => value && value !== '')
    );
    onConfirm(selectedEmployerId, activeFilters);
    onClose();
  };

  const hasActiveFilters = Object.values(filters).some(value => value && value !== '');
  const activeFiltersCount = Object.values(filters).filter(value => value && value !== '').length;
  const selectedEmployer = employers.find(emp => emp.id === selectedEmployerId);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-zoom-in">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            {actionIcon && <div className="text-primary-500">{actionIcon}</div>}
            <div>
              <h2 className="text-xl font-bold text-slate-800">
                {actionTitle}
              </h2>
              <p className="text-slate-500 text-sm mt-1">
                {actionDescription}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white rounded-full transition-colors text-slate-400 hover:text-red-500 shadow-sm"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
              <span className="ml-3 text-slate-600">Chargement des données...</span>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Sélection de l'employeur */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2 mb-3">
                  <UserGroupIcon className="h-5 w-5 text-blue-500" />
                  Sélection de l'employeur
                </h3>
                <select
                  value={selectedEmployerId}
                  onChange={(e) => setSelectedEmployerId(Number(e.target.value))}
                  className="w-full px-4 py-3 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-medium"
                >
                  {employers.map((employer) => (
                    <option key={employer.id} value={employer.id}>
                      {employer.raison_sociale}
                    </option>
                  ))}
                </select>
                {selectedEmployer && (
                  <p className="text-sm text-blue-600 mt-2 font-medium">
                    ✓ Employeur sélectionné : {selectedEmployer.raison_sociale}
                  </p>
                )}
              </div>

              {/* Section de synchronisation - SUPPRIMÉE pour simplifier */}

              {/* Options de traitement */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                  <FunnelIcon className="h-5 w-5 text-primary-500" />
                  Choisissez le périmètre de traitement
                </h3>

                {/* Option 1: Traiter tout */}
                <div className="border border-slate-200 rounded-xl p-4 hover:border-primary-300 transition-colors">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="filterOption"
                      checked={!useFilters}
                      onChange={() => setUseFilters(false)}
                      className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                    />
                    <div>
                      <div className="font-semibold text-slate-800 flex items-center gap-2">
                        <ExclamationTriangleIcon className="h-4 w-4 text-amber-500" />
                        Traiter TOUS les salariés de {selectedEmployer?.raison_sociale || 'cet employeur'}
                      </div>
                      <p className="text-sm text-slate-600 mt-1">
                        Aucun filtre appliqué. Tous les salariés de l'employeur sélectionné seront inclus dans le traitement.
                      </p>
                    </div>
                  </label>
                </div>

                {/* Option 2: Appliquer des filtres */}
                <div className="border border-slate-200 rounded-xl p-4 hover:border-primary-300 transition-colors">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="filterOption"
                      checked={useFilters}
                      onChange={() => setUseFilters(true)}
                      className="mt-1 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                    />
                    <div className="flex-1">
                      <div className="font-semibold text-slate-800 flex items-center gap-2">
                        <BuildingOfficeIcon className="h-4 w-4 text-primary-500" />
                        Appliquer des filtres organisationnels
                        {hasActiveFilters && (
                          <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
                            {activeFiltersCount} actif{activeFiltersCount > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-600 mt-1 mb-4">
                        Limitez le traitement à une structure organisationnelle spécifique de {selectedEmployer?.raison_sociale || 'cet employeur'}.
                      </p>

                      {/* Filtres organisationnels */}
                      {useFilters && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 p-4 bg-slate-50 rounded-lg">
                          {/* Établissement */}
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Établissement
                            </label>
                            <select
                              value={filters.etablissement || ''}
                              onChange={(e) => handleFilterChange('etablissement', e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                            >
                              <option value="">Tous les établissements</option>
                              {orgData.etablissements.map((item, index) => (
                                <option key={index} value={item}>
                                  {item}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Département */}
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Département
                              {filters.etablissement && (
                                <span className="text-xs text-blue-600 ml-1">
                                  (filtré par {filters.etablissement})
                                </span>
                              )}
                            </label>
                            <select
                              value={filters.departement || ''}
                              onChange={(e) => handleFilterChange('departement', e.target.value)}
                              disabled={!filters.etablissement}
                              className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm ${
                                !filters.etablissement ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                              }`}
                            >
                              <option value="">
                                {!filters.etablissement 
                                  ? 'Sélectionnez d\'abord un établissement' 
                                  : 'Tous les départements'
                                }
                              </option>
                              {orgData.departements.map((item, index) => (
                                <option key={index} value={item}>
                                  {item}
                                </option>
                              ))}
                            </select>
                            {!filters.etablissement && (
                              <p className="text-xs text-gray-500 mt-1">
                                Sélectionnez un établissement pour voir les départements disponibles
                              </p>
                            )}
                          </div>

                          {/* Service */}
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Service
                              {(filters.etablissement || filters.departement) && (
                                <span className="text-xs text-blue-600 ml-1">
                                  (filtré par {[filters.etablissement, filters.departement].filter(Boolean).join(' → ')})
                                </span>
                              )}
                            </label>
                            <select
                              value={filters.service || ''}
                              onChange={(e) => handleFilterChange('service', e.target.value)}
                              disabled={!filters.etablissement && !filters.departement}
                              className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm ${
                                !filters.etablissement && !filters.departement ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                              }`}
                            >
                              <option value="">
                                {!filters.etablissement && !filters.departement
                                  ? 'Sélectionnez d\'abord un établissement ou département' 
                                  : 'Tous les services'
                                }
                              </option>
                              {orgData.services.map((item, index) => (
                                <option key={index} value={item}>
                                  {item}
                                </option>
                              ))}
                            </select>
                            {!filters.etablissement && !filters.departement && (
                              <p className="text-xs text-gray-500 mt-1">
                                Sélectionnez un niveau supérieur pour voir les services disponibles
                              </p>
                            )}
                          </div>

                          {/* Unité */}
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Unité
                              {(filters.etablissement || filters.departement || filters.service) && (
                                <span className="text-xs text-blue-600 ml-1">
                                  (filtré par {[filters.etablissement, filters.departement, filters.service].filter(Boolean).join(' → ')})
                                </span>
                              )}
                            </label>
                            <select
                              value={filters.unite || ''}
                              onChange={(e) => handleFilterChange('unite', e.target.value)}
                              disabled={!filters.etablissement && !filters.departement && !filters.service}
                              className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm ${
                                !filters.etablissement && !filters.departement && !filters.service ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                              }`}
                            >
                              <option value="">
                                {!filters.etablissement && !filters.departement && !filters.service
                                  ? 'Sélectionnez d\'abord un niveau supérieur' 
                                  : 'Toutes les unités'
                                }
                              </option>
                              {orgData.unites.map((item, index) => (
                                <option key={index} value={item}>
                                  {item}
                                </option>
                              ))}
                            </select>
                            {!filters.etablissement && !filters.departement && !filters.service && (
                              <p className="text-xs text-gray-500 mt-1">
                                Sélectionnez un niveau supérieur pour voir les unités disponibles
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end gap-4">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-slate-600 font-semibold hover:bg-white rounded-xl transition-all"
          >
            Annuler
          </button>
          
          {!useFilters ? (
            <button
              onClick={handleConfirmAll}
              className="px-8 py-2.5 bg-amber-600 text-white font-bold rounded-xl hover:bg-amber-700 transition-all shadow-lg flex items-center gap-2"
            >
              <ExclamationTriangleIcon className="h-5 w-5" />
              Traiter TOUT ({selectedEmployer?.raison_sociale})
            </button>
          ) : (
            <button
              onClick={handleConfirmFiltered}
              disabled={!hasActiveFilters}
              className="px-8 py-2.5 bg-primary-600 text-white font-bold rounded-xl hover:bg-primary-700 transition-all shadow-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckIcon className="h-5 w-5" />
              {hasActiveFilters ? `Traiter avec filtres (${activeFiltersCount})` : 'Sélectionnez des filtres'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrganizationalFilterModal;