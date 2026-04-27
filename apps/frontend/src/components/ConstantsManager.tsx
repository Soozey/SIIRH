/**
 * Gestionnaire du référentiel centralisé de constantes
 */
import { useState } from 'react';
import {
  Cog6ToothIcon,
  DocumentTextIcon,
  BanknotesIcon,
  BuildingOfficeIcon,
  UserGroupIcon,
  ListBulletIcon,
  CalculatorIcon
} from '@heroicons/react/24/outline';
import { useAllConstants } from '../hooks/useConstants';

interface ConstantsManagerProps {
  onClose?: () => void;
}

// Composant pour afficher une section de constantes
const ConstantsSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  data: unknown;
  type: 'object' | 'array' | 'simple';
}> = ({ title, icon, data, type }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const itemCount = Array.isArray(data) ? data.length : 0;
  const propertyCount = data && typeof data === "object" && !Array.isArray(data) ? Object.keys(data).length : 0;

  const renderValue = (value: unknown) => {
    if (typeof value === 'object' && value !== null) {
      if (Array.isArray(value)) {
        return (
          <div className="space-y-1">
            {value.map((item, index) => (
              <div key={index} className="text-sm text-gray-600 pl-4 border-l-2 border-gray-200">
                {typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item)}
              </div>
            ))}
          </div>
        );
      } else {
        return (
          <div className="space-y-2">
            {Object.entries(value).map(([subKey, subValue]) => (
              <div key={subKey} className="border-l-2 border-gray-200 pl-4">
                <div className="font-medium text-gray-700">{subKey}</div>
                <div className="text-sm text-gray-600">
                  {typeof subValue === 'object' ? JSON.stringify(subValue, null, 2) : String(subValue)}
                </div>
              </div>
            ))}
          </div>
        );
      }
    }
    return <span className="text-gray-600">{String(value)}</span>;
  };

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left font-medium text-gray-900 bg-gray-50 hover:bg-gray-100 rounded-t-lg flex items-center justify-between"
      >
        <div className="flex items-center space-x-3">
          {icon}
          <span>{title}</span>
        </div>
        <span className="text-sm text-gray-500">
          {type === 'array' ? `${itemCount} éléments` :
           type === 'object' ? `${propertyCount} propriétés` :
           'Valeur simple'}
        </span>
      </button>
      
      {isExpanded && (
        <div className="p-4 max-h-96 overflow-y-auto">
          {type === 'simple' ? (
            renderValue(data)
          ) : type === 'array' ? (
            <div className="space-y-3">
              {Array.isArray(data) && data.map((item: unknown, index: number) => (
                <div key={index} className="p-3 bg-gray-50 rounded border">
                  {renderValue(item)}
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {Object.entries(data && typeof data === "object" && !Array.isArray(data) ? data : {}).map(([key, value]) => (
                <div key={key} className="p-3 bg-gray-50 rounded border">
                  <div className="font-medium text-gray-800 mb-2">{key}</div>
                  {renderValue(value)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Composant principal
export const ConstantsManager: React.FC<ConstantsManagerProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<'payroll' | 'business' | 'documents' | 'validation'>('payroll');
  
  const {
    payroll,
    business,
    documentFields,
    validation,
    fieldCategories,
    isLoading,
    isError,
    error
  } = useAllConstants();

  const tabs = [
    {
      id: 'payroll' as const,
      label: 'Paie',
      icon: <BanknotesIcon className="w-5 h-5" />,
      description: 'Constantes de calcul de paie'
    },
    {
      id: 'business' as const,
      label: 'Métier',
      icon: <BuildingOfficeIcon className="w-5 h-5" />,
      description: 'Constantes métier et référentiels'
    },
    {
      id: 'documents' as const,
      label: 'Documents',
      icon: <DocumentTextIcon className="w-5 h-5" />,
      description: 'Champs et templates de documents'
    },
    {
      id: 'validation' as const,
      label: 'Validation',
      icon: <ListBulletIcon className="w-5 h-5" />,
      description: 'Règles de validation et listes'
    }
  ];

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span>Chargement des constantes...</span>
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md">
          <div className="text-red-600 mb-4">
            <h3 className="text-lg font-semibold">Erreur de chargement</h3>
            <p className="text-sm mt-2">{error?.message || 'Impossible de charger les constantes'}</p>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Fermer
          </button>
        </div>
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'payroll':
        return (
          <div className="space-y-4">
            <ConstantsSection
              title="Taux de cotisations"
              icon={<CalculatorIcon className="w-5 h-5" />}
              data={payroll.data?.cotisations || {}}
              type="object"
            />
            <ConstantsSection
              title="Majorations heures supplémentaires"
              icon={<CalculatorIcon className="w-5 h-5" />}
              data={payroll.data?.majorations || {}}
              type="object"
            />
            <ConstantsSection
              title="Constantes de calcul"
              icon={<CalculatorIcon className="w-5 h-5" />}
              data={payroll.data?.calculs || {}}
              type="object"
            />
            <ConstantsSection
              title="Formules prédéfinies"
              icon={<CalculatorIcon className="w-5 h-5" />}
              data={payroll.data?.formules || {}}
              type="object"
            />
            <ConstantsSection
              title="Variables disponibles"
              icon={<CalculatorIcon className="w-5 h-5" />}
              data={payroll.data?.variables || {}}
              type="object"
            />
          </div>
        );

      case 'business':
        return (
          <div className="space-y-4">
            <ConstantsSection
              title="Types de contrats"
              icon={<DocumentTextIcon className="w-5 h-5" />}
              data={business.data?.contrats || {}}
              type="object"
            />
            <ConstantsSection
              title="Modes de paiement"
              icon={<BanknotesIcon className="w-5 h-5" />}
              data={business.data?.paiements || {}}
              type="object"
            />
            <ConstantsSection
              title="Situations familiales"
              icon={<UserGroupIcon className="w-5 h-5" />}
              data={business.data?.famille || {}}
              type="object"
            />
            <ConstantsSection
              title="Types de régimes"
              icon={<BuildingOfficeIcon className="w-5 h-5" />}
              data={business.data?.regimes || {}}
              type="object"
            />
            <ConstantsSection
              title="Catégories professionnelles"
              icon={<UserGroupIcon className="w-5 h-5" />}
              data={business.data?.categories || {}}
              type="object"
            />
            <ConstantsSection
              title="Postes courants"
              icon={<ListBulletIcon className="w-5 h-5" />}
              data={business.data?.postes || []}
              type="array"
            />
            <ConstantsSection
              title="Banques courantes"
              icon={<BuildingOfficeIcon className="w-5 h-5" />}
              data={business.data?.banques || []}
              type="array"
            />
          </div>
        );

      case 'documents':
        return (
          <div className="space-y-4">
            <ConstantsSection
              title="Champs par catégorie"
              icon={<DocumentTextIcon className="w-5 h-5" />}
              data={fieldCategories.data || {}}
              type="object"
            />
            <ConstantsSection
              title="Tous les champs disponibles"
              icon={<ListBulletIcon className="w-5 h-5" />}
              data={documentFields.data || {}}
              type="object"
            />
          </div>
        );

      case 'validation':
        return (
          <div className="space-y-4">
            <ConstantsSection
              title="Options des listes déroulantes"
              icon={<ListBulletIcon className="w-5 h-5" />}
              data={validation.data?.dropdowns || {}}
              type="object"
            />
            <ConstantsSection
              title="Règles de validation"
              icon={<Cog6ToothIcon className="w-5 h-5" />}
              data={validation.data?.rules || {}}
              type="object"
            />
            <ConstantsSection
              title="Messages d'erreur"
              icon={<DocumentTextIcon className="w-5 h-5" />}
              data={validation.data?.messages || {}}
              type="object"
            />
            <ConstantsSection
              title="Champs obligatoires par contexte"
              icon={<ListBulletIcon className="w-5 h-5" />}
              data={validation.data?.required || {}}
              type="object"
            />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Référentiel de Constantes</h2>
            <p className="text-sm text-gray-600 mt-1">
              Gestion centralisée des données de référence du système SIIRH
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 py-4 border-b border-gray-200">
          <nav className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderTabContent()}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              💡 Ces constantes sont utilisées dans tout le système pour assurer la cohérence des données
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors duration-200"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConstantsManager;
