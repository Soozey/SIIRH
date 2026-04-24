import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '../api';
import {
  BuildingOfficeIcon,
  FunnelIcon,
  XMarkIcon,
  CheckIcon,
  UserGroupIcon,
  ChevronRightIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';

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
  fixedEmployerId?: number;
  hideEmployerSelector?: boolean;
  initialFilters?: OrganizationalFilters | null;
  actionTitle: string;
  actionDescription: string;
  actionIcon?: ReactNode;
}

interface Employer {
  id: number;
  raison_sociale: string;
}

interface OrganizationalUnitOption {
  id: number;
  name: string;
  code?: string;
  level: 'etablissement' | 'departement' | 'service' | 'unite';
  parent_id?: number | null;
}

const fetchOrganizationalUnits = async (
  employerId: number,
  level: OrganizationalUnitOption['level'],
  parentId?: number | null,
): Promise<OrganizationalUnitOption[]> => {
  const response = await api.get(`/organization/employers/${employerId}/units`, {
    params: {
      level,
      ...(parentId !== undefined ? { parent_id: parentId } : {}),
    },
  });

  return response.data as OrganizationalUnitOption[];
};

export const OrganizationalFilterModalOptimized: React.FC<OrganizationalFilterModalOptimizedProps> = ({
  isOpen,
  onClose,
  onConfirm,
  defaultEmployerId,
  fixedEmployerId,
  hideEmployerSelector = false,
  initialFilters,
  actionTitle,
  actionDescription,
  actionIcon,
}) => {
  const initialEmployerId = fixedEmployerId && fixedEmployerId > 0
    ? fixedEmployerId
    : defaultEmployerId && defaultEmployerId > 0
      ? defaultEmployerId
      : 0;
  const [selectedEmployerId, setSelectedEmployerId] = useState<number>(initialEmployerId);
  const [selectedEtablissement, setSelectedEtablissement] = useState<number | null>(null);
  const [selectedDepartement, setSelectedDepartement] = useState<number | null>(null);
  const [selectedService, setSelectedService] = useState<number | null>(null);
  const [selectedUnite, setSelectedUnite] = useState<number | null>(null);
  const [useFilters, setUseFilters] = useState(false);

  const { data: employers = [] } = useQuery<Employer[]>({
    queryKey: ['employers'],
    queryFn: async () => (await api.get('/employers')).data,
    enabled: isOpen,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const resolvedEmployerId =
    selectedEmployerId ||
    (defaultEmployerId && defaultEmployerId > 0 ? defaultEmployerId : employers[0]?.id || 0);

  const clearHierarchySelection = () => {
    setSelectedEtablissement(null);
    setSelectedDepartement(null);
    setSelectedService(null);
    setSelectedUnite(null);
  };

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    setSelectedEtablissement(initialFilters?.etablissement ? Number(initialFilters.etablissement) : null);
    setSelectedDepartement(initialFilters?.departement ? Number(initialFilters.departement) : null);
    setSelectedService(initialFilters?.service ? Number(initialFilters.service) : null);
    setSelectedUnite(initialFilters?.unite ? Number(initialFilters.unite) : null);
    setUseFilters(Boolean(initialFilters && Object.keys(initialFilters).length > 0));
    setSelectedEmployerId(initialEmployerId);
  }, [initialEmployerId, initialFilters, isOpen]);

  const { data: etablissements = [], isLoading: loadingEtablissements } = useQuery<OrganizationalUnitOption[]>({
    queryKey: ['organization-filter-options', resolvedEmployerId, 'etablissement', null],
    queryFn: async () => fetchOrganizationalUnits(resolvedEmployerId, 'etablissement'),
    enabled: isOpen && !!resolvedEmployerId && useFilters,
    staleTime: 60_000,
    retry: false,
  });

  const { data: departements = [], isLoading: loadingDepartements } = useQuery<OrganizationalUnitOption[]>({
    queryKey: ['organization-filter-options', resolvedEmployerId, 'departement', selectedEtablissement],
    queryFn: async () => fetchOrganizationalUnits(resolvedEmployerId, 'departement', selectedEtablissement),
    enabled: isOpen && !!resolvedEmployerId && !!selectedEtablissement && useFilters,
    staleTime: 60_000,
    retry: false,
  });

  const { data: services = [], isLoading: loadingServices } = useQuery<OrganizationalUnitOption[]>({
    queryKey: ['organization-filter-options', resolvedEmployerId, 'service', selectedDepartement],
    queryFn: async () => fetchOrganizationalUnits(resolvedEmployerId, 'service', selectedDepartement),
    enabled: isOpen && !!resolvedEmployerId && !!selectedDepartement && useFilters,
    staleTime: 60_000,
    retry: false,
  });

  const { data: unites = [], isLoading: loadingUnites } = useQuery<OrganizationalUnitOption[]>({
    queryKey: ['organization-filter-options', resolvedEmployerId, 'unite', selectedService],
    queryFn: async () => fetchOrganizationalUnits(resolvedEmployerId, 'unite', selectedService),
    enabled: isOpen && !!resolvedEmployerId && !!selectedService && useFilters,
    staleTime: 60_000,
    retry: false,
  });

  const handleEmployerChange = (nextEmployerId: number) => {
    if (fixedEmployerId && fixedEmployerId > 0) {
      return;
    }
    setSelectedEmployerId(nextEmployerId);
    clearHierarchySelection();
  };

  const handleClose = () => {
    clearHierarchySelection();
    setUseFilters(Boolean(initialFilters && Object.keys(initialFilters).length > 0));
    setSelectedEmployerId(initialEmployerId);
    onClose();
  };

  const handleConfirmAll = () => {
    onConfirm(resolvedEmployerId, null);
    handleClose();
  };

  const handleConfirmFiltered = () => {
    const filters: OrganizationalFilters = {};
    if (selectedEtablissement) filters.etablissement = String(selectedEtablissement);
    if (selectedDepartement) filters.departement = String(selectedDepartement);
    if (selectedService) filters.service = String(selectedService);
    if (selectedUnite) filters.unite = String(selectedUnite);
    onConfirm(resolvedEmployerId, filters);
    handleClose();
  };

  const hasActiveFilters = [selectedEtablissement, selectedDepartement, selectedService, selectedUnite].some(Boolean);
  const activeFiltersCount = [selectedEtablissement, selectedDepartement, selectedService, selectedUnite].filter(Boolean).length;
  const selectedEmployer = employers.find((item) => item.id === resolvedEmployerId);
  const selectedEtablissementData = etablissements.find((item) => item.id === selectedEtablissement);
  const selectedDepartementData = departements.find((item) => item.id === selectedDepartement);
  const selectedServiceData = services.find((item) => item.id === selectedService);
  const selectedUniteData = unites.find((item) => item.id === selectedUnite);

  const canConfirmFiltered = useFilters && hasActiveFilters;
  const anyLoading = loadingEtablissements || loadingDepartements || loadingServices || loadingUnites;

  const breadcrumb = useMemo(() => {
    return [
      selectedEtablissementData ? `Etablissement: ${selectedEtablissementData.name}` : null,
      selectedDepartementData ? `Departement: ${selectedDepartementData.name}` : null,
      selectedServiceData ? `Service: ${selectedServiceData.name}` : null,
      selectedUniteData ? `Unite: ${selectedUniteData.name}` : null,
    ].filter(Boolean) as string[];
  }, [selectedDepartementData, selectedEtablissementData, selectedServiceData, selectedUniteData]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 shadow-2xl shadow-slate-950/60">
        <div className="border-b border-slate-800 bg-gradient-to-r from-primary-700 via-primary-600 to-indigo-600 p-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-start gap-4">
              {actionIcon ? (
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15">
                  {actionIcon}
                </div>
              ) : null}
              <div className="min-w-0">
                <h2 className="text-2xl font-bold">{actionTitle}</h2>
                <p className="mt-1 text-sm text-primary-100">{actionDescription}</p>
              </div>
            </div>
            <button onClick={handleClose} className="rounded-xl p-2 hover:bg-white/15">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-slate-950/90 p-6">
          <div className="space-y-6">
            {!hideEmployerSelector ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/15">
                  <UserGroupIcon className="h-5 w-5 text-blue-300" />
                </div>
                <h3 className="text-lg font-semibold text-slate-100">Employeur</h3>
              </div>
              <select
                value={resolvedEmployerId}
                onChange={(e) => handleEmployerChange(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-medium text-slate-100 focus:border-transparent focus:ring-2 focus:ring-primary-500"
              >
                {employers.map((employer) => (
                  <option key={employer.id} value={employer.id}>
                    {employer.raison_sociale}
                  </option>
                ))}
              </select>
              {selectedEmployer ? (
                <div className="mt-3 flex items-center gap-2 rounded-xl border border-blue-500/20 bg-blue-500/10 px-3 py-2 text-sm text-blue-100">
                  <CheckIcon className="h-4 w-4" />
                  <span>{selectedEmployer.raison_sociale}</span>
                </div>
              ) : null}
            </div>
            ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="mb-2 text-sm font-semibold text-slate-100">Employeur cible</div>
              <div className="flex items-center gap-2 rounded-xl border border-blue-500/20 bg-blue-500/10 px-3 py-3 text-sm text-blue-100">
                <CheckIcon className="h-4 w-4" />
                <span>{selectedEmployer?.raison_sociale || `Employeur #${resolvedEmployerId}`}</span>
              </div>
            </div>
            )}

            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/15">
                  <FunnelIcon className="h-5 w-5 text-primary-300" />
                </div>
                <h3 className="text-lg font-semibold text-slate-100">Périmètre</h3>
              </div>

              <div className="space-y-3">
                <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <input
                    type="radio"
                    checked={!useFilters}
                    onChange={() => {
                      setUseFilters(false);
                      clearHierarchySelection();
                    }}
                    className="mt-1"
                  />
                  <div>
                    <div className="font-semibold text-slate-100">Traiter tout l&apos;employeur</div>
                    <div className="mt-1 text-sm text-slate-400">Aucun filtre organisationnel appliqué.</div>
                  </div>
                </label>

                <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <input
                    type="radio"
                    checked={useFilters}
                    onChange={() => setUseFilters(true)}
                    className="mt-1"
                  />
                  <div>
                    <div className="font-semibold text-slate-100">Appliquer un filtre organisationnel</div>
                    <div className="mt-1 text-sm text-slate-400">Source canonique: unités de l&apos;organisation maître.</div>
                  </div>
                </label>
              </div>
            </div>

            {useFilters ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15">
                    <BuildingOfficeIcon className="h-5 w-5 text-emerald-300" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100">Filtre hiérarchique</h3>
                </div>

                {breadcrumb.length > 0 ? (
                  <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-primary-500/20 bg-primary-500/10 px-3 py-2 text-sm text-primary-100">
                    {breadcrumb.map((item, index) => (
                      <div key={item} className="flex items-center gap-2">
                        {index > 0 ? <ChevronRightIcon className="h-4 w-4 text-slate-500" /> : null}
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-200">Etablissement</label>
                    <select
                      value={selectedEtablissement || ''}
                      onChange={(e) => {
                        setSelectedEtablissement(e.target.value ? Number(e.target.value) : null);
                        setSelectedDepartement(null);
                        setSelectedService(null);
                        setSelectedUnite(null);
                      }}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 focus:border-transparent focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">{loadingEtablissements ? 'Chargement...' : 'Tous les établissements'}</option>
                      {etablissements.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}{item.code ? ` (${item.code})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-200">Département</label>
                    <select
                      value={selectedDepartement || ''}
                      onChange={(e) => {
                        setSelectedDepartement(e.target.value ? Number(e.target.value) : null);
                        setSelectedService(null);
                        setSelectedUnite(null);
                      }}
                      disabled={!selectedEtablissement || loadingDepartements}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 disabled:opacity-50"
                    >
                      <option value="">{!selectedEtablissement ? 'Choisir d’abord un établissement' : loadingDepartements ? 'Chargement...' : 'Tous les départements'}</option>
                      {departements.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}{item.code ? ` (${item.code})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-200">Service</label>
                    <select
                      value={selectedService || ''}
                      onChange={(e) => {
                        setSelectedService(e.target.value ? Number(e.target.value) : null);
                        setSelectedUnite(null);
                      }}
                      disabled={!selectedDepartement || loadingServices}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 disabled:opacity-50"
                    >
                      <option value="">{!selectedDepartement ? 'Choisir d’abord un département' : loadingServices ? 'Chargement...' : 'Tous les services'}</option>
                      {services.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}{item.code ? ` (${item.code})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-200">Unité</label>
                    <select
                      value={selectedUnite || ''}
                      onChange={(e) => setSelectedUnite(e.target.value ? Number(e.target.value) : null)}
                      disabled={!selectedService || loadingUnites}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 disabled:opacity-50"
                    >
                      <option value="">{!selectedService ? 'Choisir d’abord un service' : loadingUnites ? 'Chargement...' : 'Toutes les unités'}</option>
                      {unites.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}{item.code ? ` (${item.code})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="mt-4 flex items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-3 text-sm text-slate-400">
                  <InformationCircleIcon className="mt-0.5 h-5 w-5 shrink-0 text-primary-300" />
                  <span>Les valeurs sélectionnées utilisent directement les identifiants des unités organisationnelles actives.</span>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="border-t border-slate-800 bg-slate-900/90 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-slate-400">
              {useFilters
                ? `${activeFiltersCount} filtre(s) actif(s)${anyLoading ? ' - chargement en cours' : ''}`
                : 'Aucun filtre appliqué'}
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                onClick={handleClose}
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
              >
                Annuler
              </button>
              <button
                onClick={handleConfirmAll}
                className="rounded-xl border border-primary-500/40 bg-primary-500/15 px-4 py-2 text-sm font-semibold text-primary-100 hover:bg-primary-500/25"
              >
                Tout traiter
              </button>
              <button
                onClick={handleConfirmFiltered}
                disabled={!canConfirmFiltered}
                className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Confirmer le filtre
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrganizationalFilterModalOptimized;
