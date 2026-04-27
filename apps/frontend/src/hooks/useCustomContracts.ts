/**
 * Hook pour gérer les contrats personnalisés
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export interface CustomContract {
  id: number;
  worker_id: number;
  employer_id: number;
  title: string;
  content: string;
  template_type: string;
  is_default: boolean;
  validation_status: string;
  inspection_status: string;
  inspection_comment?: string | null;
  active_version_number?: number;
  last_published_at?: string | null;
  last_reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomContractInput {
  worker_id: number;
  employer_id: number;
  title: string;
  content: string;
  template_type?: string;
  is_default?: boolean;
  validation_status?: string;
  inspection_status?: string;
  inspection_comment?: string | null;
}

export interface CustomContractUpdate {
  title?: string;
  content?: string;
  is_default?: boolean;
  validation_status?: string;
  inspection_status?: string;
  inspection_comment?: string | null;
}

// Hook pour récupérer les contrats d'un travailleur
export const useWorkerContracts = (workerId: number, templateType?: string) => {
  return useQuery({
    queryKey: ['worker-contracts', workerId, templateType],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (templateType) {
        params.append('template_type', templateType);
      }
      
      const response = await api.get(`/custom-contracts/worker/${workerId}?${params}`);
      return response.data as CustomContract[];
    },
    enabled: !!workerId,
  });
};

// Hook pour récupérer le contrat par défaut d'un travailleur
export const useWorkerDefaultContract = (workerId: number, templateType: string = 'employment_contract') => {
  return useQuery({
    queryKey: ['worker-default-contract', workerId, templateType],
    queryFn: async () => {
      const response = await api.get(`/custom-contracts/worker/${workerId}/default?template_type=${templateType}`);
      return response.data as CustomContract;
    },
    enabled: !!workerId,
  });
};

// Hook pour récupérer un contrat par son ID
export const useCustomContract = (contractId: number) => {
  return useQuery({
    queryKey: ['custom-contract', contractId],
    queryFn: async () => {
      const response = await api.get(`/custom-contracts/${contractId}`);
      return response.data as CustomContract;
    },
    enabled: !!contractId,
  });
};

// Hook pour créer un contrat personnalisé
export const useCreateCustomContract = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (contractData: CustomContractInput) => {
      const response = await api.post('/custom-contracts/', contractData);
      return response.data as CustomContract;
    },
    onSuccess: (data) => {
      // Invalider les caches liés
      queryClient.invalidateQueries({ queryKey: ['worker-contracts', data.worker_id] });
      queryClient.invalidateQueries({ queryKey: ['worker-default-contract', data.worker_id] });
    },
  });
};

// Hook pour mettre à jour un contrat personnalisé
export const useUpdateCustomContract = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ contractId, updates }: { contractId: number; updates: CustomContractUpdate }) => {
      const response = await api.put(`/custom-contracts/${contractId}`, updates);
      return response.data as CustomContract;
    },
    onSuccess: (data) => {
      // Invalider les caches liés
      queryClient.invalidateQueries({ queryKey: ['custom-contract', data.id] });
      queryClient.invalidateQueries({ queryKey: ['worker-contracts', data.worker_id] });
      queryClient.invalidateQueries({ queryKey: ['worker-default-contract', data.worker_id] });
    },
  });
};

// Hook pour supprimer un contrat personnalisé
export const useDeleteCustomContract = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (contractId: number) => {
      await api.delete(`/custom-contracts/${contractId}`);
      return contractId;
    },
    onSuccess: () => {
      // Invalider tous les caches de contrats
      queryClient.invalidateQueries({ queryKey: ['custom-contract'] });
      queryClient.invalidateQueries({ queryKey: ['worker-contracts'] });
      queryClient.invalidateQueries({ queryKey: ['worker-default-contract'] });
    },
  });
};

// Hook pour définir un contrat comme défaut
export const useSetDefaultContract = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (contractId: number) => {
      const response = await api.post(`/custom-contracts/${contractId}/set-default`);
      return response.data as CustomContract;
    },
    onSuccess: (data) => {
      // Invalider les caches liés
      queryClient.invalidateQueries({ queryKey: ['worker-contracts', data.worker_id] });
      queryClient.invalidateQueries({ queryKey: ['worker-default-contract', data.worker_id] });
    },
  });
};
