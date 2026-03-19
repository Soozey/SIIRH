import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import {
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  UserGroupIcon,
  CubeIcon
} from '@heroicons/react/24/outline';

interface OrganizationalOption {
  id: number;
  parent_id: number | null;
  level: number;
  level_name: string;
  name: string;
  code: string | null;
  description: string | null;
  is_active: boolean;
  has_children: boolean;
}

interface CascadingSelectValue {
  etablissement?: number;
  departement?: number;
  service?: number;
  unite?: number;
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
  1: BuildingOfficeIcon,
  2: BuildingStorefrontIcon,
  3: UserGroupIcon,
  4: CubeIcon
};

const LEVEL_LABELS = {
  1: 'Établissement',
  2: 'Département',
  3: 'Service',
  4: 'Unité'
};

export const CascadingOrganizationalSelect: React.FC<CascadingOrganizationalSelectProps> = ({
  employerId,
  value,
  onChange,
  required = {},
  disabled = false,
  showLabels = true,
  size = 'md'
}) => {
  // Fetch establishments (level 1, no parent)
  const { data: etablissements = [] } = useQuery({
    queryKey: ['cascading-options', employerId, null],
    queryFn: async () => {
      const response = await api.get(`/employers/${employerId}/hierarchical-organization/cascading-options`);
      return response.data as OrganizationalOption[];
    },
    enabled: !!employerId
  });

  // Fetch departments (level 2, parent = selected establishment)
  const { data: departements = [] } = useQuery({
    queryKey: ['cascading-options', employerId, value.etablissement],
    queryFn: async () => {
      const response = await api.get(`/employers/${employerId}/hierarchical-organization/cascading-options`, {
        params: { parent_id: value.etablissement }
      });
      return response.data as OrganizationalOption[];
    },
    enabled: !!employerId && !!value.etablissement
  });

  // Fetch services (level 3, parent = selected department)
  const { data: services = [] } = useQuery({
    queryKey: ['cascading-options', employerId, value.departement],
    queryFn: async () => {
      const response = await api.get(`/employers/${employerId}/hierarchical-organization/cascading-options`, {
        params: { parent_id: value.departement }
      });
      return response.data as OrganizationalOption[];
    },
    enabled: !!employerId && !!value.departement
  });

  // Fetch units (level 4, parent = selected service)
  const { data: unites = [] } = useQuery({
    queryKey: ['cascading-options', employerId, value.service],
    queryFn: async () => {
      const response = await api.get(`/employers/${employerId}/hierarchical-organization/cascading-options`, {
        params: { parent_id: value.service }
      });
      return response.data as OrganizationalOption[];
    },
    enabled: !!employerId && !!value.service
  });

  const handleEtablissementChange = (etablissementId: string) => {
    const newValue: CascadingSelectValue = {
      etablissement: etablissementId ? Number(etablissementId) : undefined,
      // Reset all dependent levels
      departement: undefined,
      service: undefined,
      unite: undefined
    };
    onChange(newValue);
  };

  const handleDepartementChange = (departementId: string) => {
    const newValue: CascadingSelectValue = {
      ...value,
      departement: departementId ? Number(departementId) : undefined,
      // Reset dependent levels
      service: undefined,
      unite: undefined
    };
    onChange(newValue);
  };

  const handleServiceChange = (serviceId: string) => {
    const newValue: CascadingSelectValue = {
      ...value,
      service: serviceId ? Number(serviceId) : undefined,
      // Reset dependent levels
      unite: undefined
    };
    onChange(newValue);
  };

  const handleUniteChange = (uniteId: string) => {
    const newValue: CascadingSelectValue = {
      ...value,
      unite: uniteId ? Number(uniteId) : undefined
    };
    onChange(newValue);
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
    level: number,
    options: OrganizationalOption[],
    selectedValue: number | undefined,
    onChangeHandler: (value: string) => void,
    isEnabled: boolean = true
  ) => {
    const IconComponent = LEVEL_ICONS[level as keyof typeof LEVEL_ICONS];
    const levelLabel = LEVEL_LABELS[level as keyof typeof LEVEL_LABELS];
    const isRequired = required[level === 1 ? 'etablissement' : level === 2 ? 'departement' : level === 3 ? 'service' : 'unite' as keyof typeof required];
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
              ? `Sélectionnez d'abord ${level === 2 ? 'un établissement' : 
                  level === 3 ? 'un département' : 'un service'}`
              : !hasOptions
                ? `Aucun${level === 4 ? 'e' : ''} ${levelLabel.toLowerCase()} disponible`
                : `Sélectionner ${level === 1 || level === 3 ? 'un' : level === 4 ? 'une' : 'un'} ${levelLabel.toLowerCase()}`
            }
          </option>
          {options.map(option => (
            <option key={option.id} value={option.id}>
              {option.name}
              {option.code && ` (${option.code})`}
              {option.has_children && ' •'}
            </option>
          ))}
        </select>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Établissement */}
      {renderSelect(
        1,
        etablissements,
        value.etablissement,
        handleEtablissementChange,
        true
      )}

      {/* Département */}
      {value.etablissement && renderSelect(
        2,
        departements,
        value.departement,
        handleDepartementChange,
        !!value.etablissement
      )}

      {/* Service */}
      {value.departement && renderSelect(
        3,
        services,
        value.service,
        handleServiceChange,
        !!value.departement
      )}

      {/* Unité */}
      {value.service && renderSelect(
        4,
        unites,
        value.unite,
        handleUniteChange,
        !!value.service
      )}

      {/* Validation Summary */}
      {(required.etablissement || required.departement || required.service || required.unite) && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Sélection actuelle :</h4>
          <div className="space-y-1 text-sm text-blue-800">
            {value.etablissement && (
              <div className="flex items-center gap-2">
                <BuildingOfficeIcon className="h-4 w-4" />
                <span>
                  {etablissements.find(e => e.id === value.etablissement)?.name || 'Établissement sélectionné'}
                </span>
              </div>
            )}
            {value.departement && (
              <div className="flex items-center gap-2 ml-4">
                <BuildingStorefrontIcon className="h-4 w-4" />
                <span>
                  {departements.find(d => d.id === value.departement)?.name || 'Département sélectionné'}
                </span>
              </div>
            )}
            {value.service && (
              <div className="flex items-center gap-2 ml-8">
                <UserGroupIcon className="h-4 w-4" />
                <span>
                  {services.find(s => s.id === value.service)?.name || 'Service sélectionné'}
                </span>
              </div>
            )}
            {value.unite && (
              <div className="flex items-center gap-2 ml-12">
                <CubeIcon className="h-4 w-4" />
                <span>
                  {unites.find(u => u.id === value.unite)?.name || 'Unité sélectionnée'}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Utility hook for easier integration
export const useOrganizationalSelection = (initialValue: CascadingSelectValue = {}) => {
  const [value, setValue] = React.useState<CascadingSelectValue>(initialValue);

  const reset = () => setValue({});
  
  const setEtablissement = (etablissementId: number | undefined) => {
    setValue({
      etablissement: etablissementId,
      departement: undefined,
      service: undefined,
      unite: undefined
    });
  };

  const setDepartement = (departementId: number | undefined) => {
    setValue(prev => ({
      ...prev,
      departement: departementId,
      service: undefined,
      unite: undefined
    }));
  };

  const setService = (serviceId: number | undefined) => {
    setValue(prev => ({
      ...prev,
      service: serviceId,
      unite: undefined
    }));
  };

  const setUnite = (uniteId: number | undefined) => {
    setValue(prev => ({
      ...prev,
      unite: uniteId
    }));
  };

  const isComplete = (requiredLevels: (keyof CascadingSelectValue)[] = []) => {
    return requiredLevels.every(level => value[level] !== undefined);
  };

  const getPath = () => {
    const parts = [];
    if (value.etablissement) parts.push('etablissement');
    if (value.departement) parts.push('departement');
    if (value.service) parts.push('service');
    if (value.unite) parts.push('unite');
    return parts;
  };

  return {
    value,
    setValue,
    reset,
    setEtablissement,
    setDepartement,
    setService,
    setUnite,
    isComplete,
    getPath
  };
};