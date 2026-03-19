/**
 * Hook pour accéder au référentiel centralisé de constantes
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { 
  PayrollConstants, 
  BusinessConstants, 
  DocumentField
} from '../constants';

// Hook pour les constantes de paie
export const usePayrollConstants = () => {
  return useQuery({
    queryKey: ['constants', 'payroll'],
    queryFn: async (): Promise<PayrollConstants> => {
      const response = await api.get('/constants/payroll');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Hook pour les constantes métier
export const useBusinessConstants = () => {
  return useQuery({
    queryKey: ['constants', 'business'],
    queryFn: async (): Promise<BusinessConstants> => {
      const response = await api.get('/constants/business');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

// Hook pour les champs de documents
export const useDocumentFields = () => {
  return useQuery({
    queryKey: ['constants', 'document-fields'],
    queryFn: async (): Promise<Record<string, Record<string, DocumentField>>> => {
      const response = await api.get('/constants/document-fields');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

// Hook pour les templates de documents
export const useDocumentTemplates = () => {
  return useQuery({
    queryKey: ['constants', 'document-templates'],
    queryFn: async () => {
      const response = await api.get('/constants/document-templates');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

// Hook pour les constantes de validation
export const useValidationConstants = () => {
  return useQuery({
    queryKey: ['constants', 'validation'],
    queryFn: async () => {
      const response = await api.get('/constants/validation');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

// Hook pour les champs par catégorie (pour l'interface glisser-déposer)
export const useFieldCategories = () => {
  return useQuery({
    queryKey: ['constants', 'field-categories'],
    queryFn: async () => {
      const response = await api.get('/constants/field-categories');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

// Hook pour les options d'une liste déroulante spécifique
export const useDropdownOptions = (fieldName: string) => {
  return useQuery({
    queryKey: ['constants', 'dropdown', fieldName],
    queryFn: async () => {
      const response = await api.get(`/constants/dropdowns/${fieldName}`);
      return response.data;
    },
    enabled: !!fieldName,
    staleTime: 10 * 60 * 1000, // Plus long car ces données changent rarement
    gcTime: 30 * 60 * 1000,
  });
};

// Hook pour les données d'un travailleur formatées
export const useWorkerData = (workerId: number) => {
  return useQuery({
    queryKey: ['constants', 'worker-data', workerId],
    queryFn: async () => {
      const response = await api.get(`/constants/worker-data/${workerId}`);
      return response.data;
    },
    enabled: !!workerId,
    staleTime: 2 * 60 * 1000, // Plus court car ces données peuvent changer
    gcTime: 5 * 60 * 1000,
  });
};

// Hook pour les données d'un employeur formatées
export const useEmployerData = (employerId: number) => {
  return useQuery({
    queryKey: ['constants', 'employer-data', employerId],
    queryFn: async () => {
      const response = await api.get(`/constants/employer-data/${employerId}`);
      return response.data;
    },
    enabled: !!employerId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

// Hook pour les données système
export const useSystemData = () => {
  return useQuery({
    queryKey: ['constants', 'system-data'],
    queryFn: async () => {
      const response = await api.get('/constants/system-data');
      return response.data;
    },
    staleTime: 60 * 1000, // 1 minute (pour la date courante)
    gcTime: 2 * 60 * 1000,
  });
};

// Hook combiné pour toutes les constantes (utile pour l'initialisation)
export const useAllConstants = () => {
  const payroll = usePayrollConstants();
  const business = useBusinessConstants();
  const documentFields = useDocumentFields();
  const validation = useValidationConstants();
  const fieldCategories = useFieldCategories();
  
  return {
    payroll,
    business,
    documentFields,
    validation,
    fieldCategories,
    isLoading: payroll.isLoading || business.isLoading || documentFields.isLoading || validation.isLoading,
    isError: payroll.isError || business.isError || documentFields.isError || validation.isError,
    error: payroll.error || business.error || documentFields.error || validation.error
  };
};