/**
 * Composant de démonstration pour tester les constantes
 */
import { useState } from 'react';
import {
  BeakerIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { useAllConstants } from '../hooks/useConstants';

export const ConstantsDemo: React.FC = () => {
  const [selectedTest, setSelectedTest] = useState<string>('payroll');
  
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

  const tests = [
    {
      id: 'payroll',
      name: 'Constantes de Paie',
      data: payroll.data,
      description: 'Taux de cotisations, majorations HS, formules'
    },
    {
      id: 'business',
      name: 'Constantes Métier',
      data: business.data,
      description: 'Contrats, paiements, catégories professionnelles'
    },
    {
      id: 'documents',
      name: 'Champs de Documents',
      data: documentFields.data,
      description: '29 champs disponibles pour les documents'
    },
    {
      id: 'categories',
      name: 'Catégories de Champs',
      data: fieldCategories.data,
      description: 'Champs organisés par catégorie'
    },
    {
      id: 'validation',
      name: 'Règles de Validation',
      data: validation.data,
      description: 'Listes déroulantes et règles de validation'
    }
  ];

  const renderTestResult = (test: any) => {
    if (isLoading) {
      return (
        <div className="flex items-center space-x-2 text-blue-600">
          <ClockIcon className="w-5 h-5 animate-spin" />
          <span>Chargement...</span>
        </div>
      );
    }

    if (isError) {
      return (
        <div className="flex items-center space-x-2 text-red-600">
          <XCircleIcon className="w-5 h-5" />
          <span>Erreur: {error?.message}</span>
        </div>
      );
    }

    if (test.data) {
      const dataSize = JSON.stringify(test.data).length;
      const itemCount = typeof test.data === 'object' 
        ? Object.keys(test.data).length 
        : Array.isArray(test.data) ? test.data.length : 1;

      return (
        <div className="space-y-3">
          <div className="flex items-center space-x-2 text-green-600">
            <CheckCircleIcon className="w-5 h-5" />
            <span>Données chargées avec succès</span>
          </div>
          
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600 space-y-1">
              <div>📊 Éléments: {itemCount}</div>
              <div>💾 Taille: {dataSize} caractères</div>
              <div>🔗 Type: {Array.isArray(test.data) ? 'Array' : 'Object'}</div>
            </div>
          </div>

          <div className="bg-white border rounded p-3 max-h-64 overflow-y-auto">
            <pre className="text-xs text-gray-700">
              {JSON.stringify(test.data, null, 2)}
            </pre>
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <XCircleIcon className="w-5 h-5" />
        <span>Aucune donnée disponible</span>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <BeakerIcon className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Test des Constantes SIIRH
              </h1>
              <p className="text-gray-600">
                Vérifiez que toutes les constantes sont bien chargées depuis l'API
              </p>
            </div>
          </div>
        </div>

        {/* Navigation des tests */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex flex-wrap gap-2">
            {tests.map((test) => (
              <button
                key={test.id}
                onClick={() => setSelectedTest(test.id)}
                className={`
                  px-4 py-2 rounded-lg font-medium transition-colors duration-200
                  ${selectedTest === test.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                {test.name}
              </button>
            ))}
          </div>
        </div>

        {/* Contenu du test */}
        <div className="p-6">
          {tests.map((test) => (
            selectedTest === test.id && (
              <div key={test.id} className="space-y-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {test.name}
                  </h2>
                  <p className="text-gray-600 mt-1">
                    {test.description}
                  </p>
                </div>

                {renderTestResult(test)}
              </div>
            )
          ))}
        </div>

        {/* Footer avec informations */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 rounded-b-lg">
          <div className="text-sm text-gray-600">
            💡 <strong>Comment utiliser :</strong> Sélectionnez un type de constantes ci-dessus pour voir les données chargées depuis l'API.
            Les constantes sont automatiquement mises en cache pour optimiser les performances.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConstantsDemo;