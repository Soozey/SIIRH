/**
 * Palette flottante de constantes avec glisser-déposer
 */
import { useState } from 'react';
import {
  ListBulletIcon,
  XMarkIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  CalendarIcon,
  BanknotesIcon,
  BuildingOfficeIcon,
  UserIcon
} from '@heroicons/react/24/outline';
import { useFieldCategories, useWorkerData, useEmployerData, useSystemData } from '../hooks/useConstants';

interface ConstantsPaletteProps {
  workerId?: number;
  employerId?: number;
  isOpen: boolean;
  onClose: () => void;
  onInsertConstant: (constant: string, value: string) => void;
}

export const ConstantsPalette: React.FC<ConstantsPaletteProps> = ({
  workerId,
  employerId,
  isOpen,
  onClose,
  onInsertConstant
}) => {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['Travailleur', 'Employeur', 'Structure Organisationnelle']));
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  
  // Charger les données
  const { data: categories, isLoading } = useFieldCategories();
  const { data: workerData } = useWorkerData(workerId || 0);
  const { data: employerData } = useEmployerData(employerId || 0);
  const { data: systemData } = useSystemData();

  // Combiner toutes les données
  const allData = {
    ...(workerData || {}),
    ...(employerData || {}),
    ...(systemData || {})
  };

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Employeur': return <BuildingOfficeIcon className="w-4 h-4" />;
      case 'Travailleur': return <UserIcon className="w-4 h-4" />;
      case 'Structure Organisationnelle': return <BuildingOfficeIcon className="w-4 h-4" />;
      case 'Paie': return <BanknotesIcon className="w-4 h-4" />;
      case 'Système': return <CalendarIcon className="w-4 h-4" />;
      default: return <DocumentTextIcon className="w-4 h-4" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Employeur': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'Travailleur': return 'bg-green-50 border-green-200 text-green-800';
      case 'Structure Organisationnelle': return 'bg-orange-50 border-orange-200 text-orange-800';
      case 'Paie': return 'bg-purple-50 border-purple-200 text-purple-800';
      case 'Système': return 'bg-gray-50 border-gray-200 text-gray-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const handleDragStart = (e: React.DragEvent, fieldKey: string, fieldLabel: string) => {
    setDraggedItem(fieldKey);
    e.dataTransfer.setData('text/plain', fieldKey);
    e.dataTransfer.setData('application/json', JSON.stringify({
      key: fieldKey,
      label: fieldLabel,
      value: `{{${fieldKey}}}` // Toujours insérer un placeholder
    }));
  };

  const handleDragEnd = () => {
    setDraggedItem(null);
  };

  const handleClick = (fieldKey: string) => {
    const placeholder = `{{${fieldKey}}}`;
    onInsertConstant(fieldKey, placeholder);
  };

  // Fonction pour extraire la vraie clé des données (après le point)
  const getRealKey = (fieldKey: string) => {
    if (fieldKey.includes('.')) {
      return fieldKey.split('.', 2)[1]; // worker.nom → nom
    }
    return fieldKey;
  };

  // Fonction pour obtenir la valeur d'un champ
  const getFieldValue = (fieldKey: string) => {
    const realKey = getRealKey(fieldKey);
    return allData[realKey];
  };

  if (!isOpen) return null;

  return (
    <div className="fixed top-20 right-4 w-80 max-h-[calc(100vh-6rem)] bg-white border border-gray-200 rounded-lg shadow-xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <ListBulletIcon className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900">Palette de Constantes</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded"
        >
          <XMarkIcon className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Instructions */}
      <div className="p-3 bg-blue-50 border-b border-blue-200">
        <p className="text-xs text-blue-800">
          💡 <strong>Glissez-déposez</strong> ou <strong>cliquez</strong> sur un champ pour l'insérer dans le contrat
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="text-center py-8 text-gray-500">
            Chargement des constantes...
          </div>
        ) : categories ? (
          <div className="space-y-3">
            {Object.entries(categories).map(([category, fields]) => {
              const fieldsArray = Array.isArray(fields) ? fields : [];
              const isExpanded = expandedCategories.has(category);
              
              return (
                <div key={category} className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleCategory(category)}
                    className={`w-full px-3 py-2 text-left font-medium rounded-t-lg flex items-center justify-between hover:bg-gray-50 ${getCategoryColor(category)}`}
                  >
                    <div className="flex items-center space-x-2">
                      {getCategoryIcon(category)}
                      <span>{category}</span>
                      <span className="text-xs opacity-75">({fieldsArray.length})</span>
                    </div>
                    {isExpanded ? (
                      <ChevronDownIcon className="w-4 h-4" />
                    ) : (
                      <ChevronRightIcon className="w-4 h-4" />
                    )}
                  </button>
                  
                  {isExpanded && (
                    <div className="p-2 space-y-1 max-h-48 overflow-y-auto">
                      {fieldsArray.map((field: any) => {
                        const currentValue = getFieldValue(field.key); // Utiliser la nouvelle fonction
                        const isDragging = draggedItem === field.key;
                        
                        return (
                          <div
                            key={field.key}
                            draggable
                            onDragStart={(e) => handleDragStart(e, field.key, field.label)}
                            onDragEnd={handleDragEnd}
                            onClick={() => handleClick(field.key)}
                            className={`
                              p-2 rounded border cursor-move transition-all duration-200 hover:shadow-md
                              ${isDragging ? 'opacity-50 scale-95' : 'hover:bg-gray-50'}
                              ${currentValue ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'}
                            `}
                            title={`${field.description}\nValeur actuelle: ${currentValue || 'Non définie'}`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium text-gray-900 truncate">
                                  {field.label}
                                </div>
                                <div className="text-xs text-gray-500 truncate">
                                  {field.key}
                                </div>
                                {currentValue && (
                                  <div className="text-xs text-green-600 truncate mt-1">
                                    📄 {String(currentValue).substring(0, 30)}
                                    {String(currentValue).length > 30 ? '...' : ''}
                                  </div>
                                )}
                              </div>
                              <div className="ml-2 text-gray-400">
                                ⋮⋮
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            Aucune constante disponible
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
        <div className="text-xs text-gray-600">
          🎯 <strong>{Object.keys(allData).length}</strong> constantes chargées
        </div>
      </div>
    </div>
  );
};

export default ConstantsPalette;
