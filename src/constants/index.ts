/**
 * Référentiel centralisé de constantes côté client
 */

// Types pour les constantes
export interface DropdownOption {
  value: string | number;
  label: string;
}

export interface DocumentField {
  label: string;
  type: 'text' | 'date' | 'currency' | 'computed';
  category: string;
  description: string;
  format?: string;
  formula?: string;
}

export interface ValidationRule {
  required: boolean;
  type: string;
  min_length?: number;
  max_length?: number;
  min?: number;
  max?: number;
  pattern?: string;
  message: string;
}

export interface PayrollConstants {
  cotisations: any;
  majorations: any;
  calculs: any;
  formules: Record<string, string>;
  variables: Record<string, string>;
}

export interface BusinessConstants {
  contrats: any;
  paiements: any;
  famille: any;
  sexe: any;
  regimes: any;
  preavis: any;
  categories: any;
  etablissements: any;
  postes: string[];
  banques: any[];
}

// Constantes locales (non dépendantes de l'API)
export const LOCAL_CONSTANTS = {
  // Formats d'affichage
  FORMATS: {
    DATE: 'dd/MM/yyyy',
    DATETIME: 'dd/MM/yyyy HH:mm',
    CURRENCY: '0,0 Ar',
    PERCENTAGE: '0.00%',
    NUMBER: '0,0',
    DECIMAL: '0,0.00'
  },
  
  // Couleurs pour les catégories de champs
  FIELD_COLORS: {
    'Employeur': 'bg-blue-100 text-blue-800 border-blue-200',
    'Travailleur': 'bg-green-100 text-green-800 border-green-200',
    'Paie': 'bg-purple-100 text-purple-800 border-purple-200',
    'Système': 'bg-gray-100 text-gray-800 border-gray-200'
  },
  
  // Icônes pour les types de champs
  FIELD_ICONS: {
    'text': 'document-text',
    'date': 'calendar',
    'currency': 'currency-dollar',
    'computed': 'calculator'
  },
  
  // Messages par défaut
  MESSAGES: {
    LOADING: 'Chargement...',
    ERROR: 'Une erreur est survenue',
    SUCCESS: 'Opération réussie',
    CONFIRM_DELETE: 'Êtes-vous sûr de vouloir supprimer cet élément ?',
    NO_DATA: 'Aucune donnée disponible'
  }
};

// Cache pour les constantes API
let constantsCache: {
  payroll?: PayrollConstants;
  business?: BusinessConstants;
  documentFields?: Record<string, Record<string, DocumentField>>;
  validation?: any;
  lastFetch?: number;
} = {};

// Export des constantes avec cache
export const getConstants = () => constantsCache;
export const setCacheTimestamp = () => {
  constantsCache.lastFetch = Date.now();
};
export const updateCache = (key: string, data: any) => {
  (constantsCache as any)[key] = data;
  setCacheTimestamp();
};