import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import {
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  UserGroupIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';
import type { CascadingSelectValue } from './CascadingOrganizationalSelection';

interface OrganizationalOption {
  id: number;
  employer_id: number;
  parent_id: number | null;
  level: 'etablissement' | 'departement' | 'service' | 'unite';
  level_order: number;
  name: string;
  code: string;
  description: string | null;
  is_active: boolean;
}

interface CascadingOrganizationalSelectProps {
  employerId: number;
  value: CascadingSelectValue;
  onChange: (value: CascadingSelectValue) => void;
  required?: {
    etablissement?: boolean;
    departement?: boolean;
    service?: boolean;
    unite?: boolean;
  };
  disabled?: boolean;
  showLabels?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const LEVEL_ICONS = {
  etablissement: BuildingOfficeIcon,
  departement: BuildingStorefrontIcon,
  service: UserGroupIcon,
  unite: CubeIcon,
};

const LEVEL_LABELS = {
  etablissement: 'Établissement',
  departement: 'Département',
  service: 'Service',
  unite: 'Unité',
};

const emptyValue = (): CascadingSelectValue => ({
  etablissement: undefined,
  departement: undefined,
  service: undefined,
  unite: undefined,
});

const valuesEqual = (left: CascadingSelectValue, right: CascadingSelectValue) =>
  left.etablissement === right.etablissement &&
  left.departement === right.departement &&
  left.service === right.service &&
  left.unite === right.unite;

export const CascadingOrganizationalSelect: React.FC<CascadingOrganizationalSelectProps> = ({
  employerId,
  value,
  onChange,
  required = {},
  disabled = false,
  showLabels = true,
  size = 'md',
}) => {
  const [resolvedValue, setResolvedValue] = React.useState<CascadingSelectValue>(value);
  const valueSignature = `${value.etablissement ?? ''}:${value.departement ?? ''}:${value.service ?? ''}:${value.unite ?? ''}`;
  const resolvedValueSignature = `${resolvedValue.etablissement ?? ''}:${resolvedValue.departement ?? ''}:${resolvedValue.service ?? ''}:${resolvedValue.unite ?? ''}`;

  const fetchUnits = async (level: OrganizationalOption['level'], parentId?: number) => {
    const response = await api.get(`/organization/employers/${employerId}/units`, {
      params: {
        level,
        ...(parentId !== undefined ? { parent_id: parentId } : {}),
      },
    });
    return response.data as OrganizationalOption[];
  };

  React.useEffect(() => {
    if (!valuesEqual(resolvedValue, value)) {
      setResolvedValue(value);
    }
  }, [resolvedValue, value, valueSignature]);

  React.useEffect(() => {
    const deepestSelectedId = value.unite ?? value.service ?? value.departement ?? value.etablissement;
    if (!employerId || !deepestSelectedId) {
      if (!deepestSelectedId && !valuesEqual(resolvedValue, emptyValue())) {
        setResolvedValue(emptyValue());
      }
      return;
    }

    const hasCompleteHierarchy =
      value.unite !== undefined ||
      (value.service !== undefined && value.departement !== undefined && value.etablissement !== undefined) ||
      (value.departement !== undefined && value.etablissement !== undefined) ||
      value.etablissement !== undefined;

    if (hasCompleteHierarchy && !(
      value.unite !== undefined && (value.service === undefined || value.departement === undefined || value.etablissement === undefined)
    )) {
      return;
    }

    let isCancelled = false;

    const hydrateHierarchy = async () => {
      try {
        const nextValue = emptyValue();
        let currentUnitId: number | null = deepestSelectedId;
        const visited = new Set<number>();

        while (currentUnitId) {
          if (visited.has(currentUnitId)) {
            break;
          }
          visited.add(currentUnitId);

          const response: { data: OrganizationalOption } = await api.get(
            `/organization/units/${currentUnitId}`,
          );
          const unit: OrganizationalOption = response.data;

          if (unit.level === 'etablissement') nextValue.etablissement = unit.id;
          if (unit.level === 'departement') nextValue.departement = unit.id;
          if (unit.level === 'service') nextValue.service = unit.id;
          if (unit.level === 'unite') nextValue.unite = unit.id;

          currentUnitId = unit.parent_id ?? null;
        }

        if (!isCancelled && !valuesEqual(nextValue, resolvedValue)) {
          setResolvedValue(nextValue);
        }
      } catch (error) {
        console.error('Erreur lors de la reconstruction de la hiérarchie organisationnelle:', error);
      }
    };

    void hydrateHierarchy();

    return () => {
      isCancelled = true;
    };
  }, [
    employerId,
    resolvedValue,
    resolvedValueSignature,
    value.departement,
    value.etablissement,
    value.service,
    value.unite,
    valueSignature,
  ]);

  const { data: etablissements = [] } = useQuery({
    queryKey: ['org-units', employerId, 'etablissement', null],
    queryFn: async () => fetchUnits('etablissement'),
    enabled: !!employerId,
  });

  const { data: departements = [] } = useQuery({
    queryKey: ['org-units', employerId, 'departement', resolvedValue.etablissement],
    queryFn: async () => fetchUnits('departement', resolvedValue.etablissement),
    enabled: !!employerId && !!resolvedValue.etablissement,
  });

  const { data: services = [] } = useQuery({
    queryKey: ['org-units', employerId, 'service', resolvedValue.departement],
    queryFn: async () => fetchUnits('service', resolvedValue.departement),
    enabled: !!employerId && !!resolvedValue.departement,
  });

  const { data: unites = [] } = useQuery({
    queryKey: ['org-units', employerId, 'unite', resolvedValue.service],
    queryFn: async () => fetchUnits('unite', resolvedValue.service),
    enabled: !!employerId && !!resolvedValue.service,
  });

  const commitValue = (nextValue: CascadingSelectValue) => {
    setResolvedValue(nextValue);
    onChange(nextValue);
  };

  const handleEtablissementChange = (etablissementId: string) => {
    commitValue({
      etablissement: etablissementId ? Number(etablissementId) : undefined,
      departement: undefined,
      service: undefined,
      unite: undefined,
    });
  };

  const handleDepartementChange = (departementId: string) => {
    commitValue({
      ...resolvedValue,
      departement: departementId ? Number(departementId) : undefined,
      service: undefined,
      unite: undefined,
    });
  };

  const handleServiceChange = (serviceId: string) => {
    commitValue({
      ...resolvedValue,
      service: serviceId ? Number(serviceId) : undefined,
      unite: undefined,
    });
  };

  const handleUniteChange = (uniteId: string) => {
    commitValue({
      ...resolvedValue,
      unite: uniteId ? Number(uniteId) : undefined,
    });
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-2 py-1 text-sm';
      case 'lg':
        return 'px-4 py-3 text-lg';
      default:
        return 'px-3 py-2';
    }
  };

  const renderSelect = (
    level: OrganizationalOption['level'],
    options: OrganizationalOption[],
    selectedValue: number | undefined,
    onChangeHandler: (value: string) => void,
    isEnabled: boolean = true,
  ) => {
    const IconComponent = LEVEL_ICONS[level];
    const levelLabel = LEVEL_LABELS[level];
    const isRequired = required[level];
    const hasOptions = options.length > 0;

    return (
      <div className="space-y-2">
        {showLabels && (
          <label className="block text-sm font-medium text-gray-700">
            <div className="flex items-center gap-2">
              <IconComponent className="h-4 w-4" />
              {levelLabel}
              {isRequired && <span className="text-red-500">*</span>}
            </div>
          </label>
        )}
        <select
          value={selectedValue || ''}
          onChange={(e) => onChangeHandler(e.target.value)}
          disabled={disabled || !isEnabled || !hasOptions}
          required={isRequired}
          className={`
            w-full border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500
            ${getSizeClasses()}
            ${disabled || !isEnabled || !hasOptions
              ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
              : 'bg-white text-gray-900'
            }
          `}
        >
          <option value="">
            {!isEnabled
              ? `Sélectionnez d'abord ${level === 'departement' ? 'un établissement' : level === 'service' ? 'un département' : 'un service'}`
              : !hasOptions
                ? `Aucun${level === 'unite' ? 'e' : ''} ${levelLabel.toLowerCase()} disponible`
                : `Sélectionner ${level === 'etablissement' || level === 'service' ? 'un' : level === 'unite' ? 'une' : 'un'} ${levelLabel.toLowerCase()}`
            }
          </option>
          {options.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name}{option.code ? ` (${option.code})` : ''}
            </option>
          ))}
        </select>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {renderSelect('etablissement', etablissements, resolvedValue.etablissement, handleEtablissementChange, true)}
      {resolvedValue.etablissement && renderSelect('departement', departements, resolvedValue.departement, handleDepartementChange, !!resolvedValue.etablissement)}
      {resolvedValue.departement && renderSelect('service', services, resolvedValue.service, handleServiceChange, !!resolvedValue.departement)}
      {resolvedValue.service && renderSelect('unite', unites, resolvedValue.unite, handleUniteChange, !!resolvedValue.service)}

      {(required.etablissement || required.departement || required.service || required.unite) && (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <h4 className="mb-2 text-sm font-medium text-blue-900">Sélection actuelle :</h4>
          <div className="space-y-1 text-sm text-blue-800">
            {resolvedValue.etablissement && (
              <div className="flex items-center gap-2">
                <BuildingOfficeIcon className="h-4 w-4" />
                <span>{etablissements.find((item) => item.id === resolvedValue.etablissement)?.name || 'Établissement sélectionné'}</span>
              </div>
            )}
            {resolvedValue.departement && (
              <div className="ml-4 flex items-center gap-2">
                <BuildingStorefrontIcon className="h-4 w-4" />
                <span>{departements.find((item) => item.id === resolvedValue.departement)?.name || 'Département sélectionné'}</span>
              </div>
            )}
            {resolvedValue.service && (
              <div className="ml-8 flex items-center gap-2">
                <UserGroupIcon className="h-4 w-4" />
                <span>{services.find((item) => item.id === resolvedValue.service)?.name || 'Service sélectionné'}</span>
              </div>
            )}
            {resolvedValue.unite && (
              <div className="ml-12 flex items-center gap-2">
                <CubeIcon className="h-4 w-4" />
                <span>{unites.find((item) => item.id === resolvedValue.unite)?.name || 'Unité sélectionnée'}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
