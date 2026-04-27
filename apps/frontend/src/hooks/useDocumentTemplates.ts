/**
 * Hook pour gérer les templates de documents globaux
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export interface DocumentTemplate {
  id: number;
  employer_id?: number;
  name: string;
  description?: string;
  template_type: string;
  content: string;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentTemplateInput {
  employer_id?: number;
  name: string;
  description?: string;
  template_type: string;
  content: string;
  is_active?: boolean;
}

export interface DocumentTemplateUpdate {
  name?: string;
  description?: string;
  content?: string;
  is_active?: boolean;
}

export interface AppliedTemplate {
  template_id: number;
  template_name: string;
  worker_id: number;
  worker_name: string;
  content: string;
  original_content: string;
}

// Hook pour récupérer les templates
export const useDocumentTemplates = (employerId?: number, templateType?: string) => {
  return useQuery({
    queryKey: ['document-templates', employerId, templateType],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (employerId) {
        params.append('employer_id', employerId.toString());
      }
      if (templateType) {
        params.append('template_type', templateType);
      }
      
      const response = await api.get(`/document-templates/?${params}`);
      return response.data as DocumentTemplate[];
    },
  });
};

// Hook pour récupérer un template par son ID
export const useDocumentTemplate = (templateId: number) => {
  return useQuery({
    queryKey: ['document-template', templateId],
    queryFn: async () => {
      const response = await api.get(`/document-templates/${templateId}`);
      return response.data as DocumentTemplate;
    },
    enabled: !!templateId,
  });
};

// Hook pour créer un template
export const useCreateDocumentTemplate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (templateData: DocumentTemplateInput) => {
      const response = await api.post('/document-templates/', templateData);
      return response.data as DocumentTemplate;
    },
    onSuccess: () => {
      // Invalider TOUS les caches de templates pour forcer le rechargement
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
      // Forcer le rechargement immédiat
      queryClient.refetchQueries({ queryKey: ['document-templates'] });
    },
  });
};

// Hook pour mettre à jour un template
export const useUpdateDocumentTemplate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ templateId, updates }: { templateId: number; updates: DocumentTemplateUpdate }) => {
      const response = await api.put(`/document-templates/${templateId}`, updates);
      return response.data as DocumentTemplate;
    },
    onSuccess: (data) => {
      // Invalider les caches liés
      queryClient.invalidateQueries({ queryKey: ['document-template', data.id] });
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
    },
  });
};

// Hook pour supprimer un template
export const useDeleteDocumentTemplate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (templateId: number) => {
      await api.delete(`/document-templates/${templateId}`);
      return templateId;
    },
    onSuccess: () => {
      // Invalider tous les caches de templates
      queryClient.invalidateQueries({ queryKey: ['document-templates'] });
      queryClient.invalidateQueries({ queryKey: ['document-template'] });
    },
  });
};

// Hook pour appliquer un template à un travailleur
export const useApplyTemplate = () => {
  return useMutation({
    mutationFn: async ({ templateId, workerId }: { templateId: number; workerId: number }) => {
      const response = await api.post(`/document-templates/${templateId}/apply/${workerId}`);
      return response.data as AppliedTemplate;
    },
  });
};
