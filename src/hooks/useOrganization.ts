import { useState, useEffect } from 'react';
import { api } from '../api';

export interface OrganizationalUnit {
  id: number;
  employer_id: number;
  parent_id?: number;
  level: string;
  level_order: number;
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrganizationTreeNode {
  id: number;
  name: string;
  code: string;
  level: string;
  level_order: number;
  description?: string;
  direct_workers: Array<{
    id: number;
    matricule: string;
    nom: string;
    prenom: string;
    poste: string;
  }>;
  children: OrganizationTreeNode[];
  total_workers: number;
}

export interface OrganizationTree {
  employer_id: number;
  root_units: OrganizationTreeNode[];
  orphan_workers: Array<{
    id: number;
    matricule: string;
    nom: string;
    prenom: string;
    poste: string;
  }>;
  total_workers: number;
}

export interface CreateUnitData {
  level: 'etablissement' | 'departement' | 'service' | 'unite';
  name: string;
  code: string;
  parent_id?: number;
  description?: string;
}

export const useOrganization = (employerId?: number) => {
  const [organizationTree, setOrganizationTree] = useState<OrganizationTree | null>(null);
  const [units, setUnits] = useState<OrganizationalUnit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Récupérer l'arbre organisationnel
  const fetchOrganizationTree = async (empId: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/organization/employers/${empId}/tree`);
      setOrganizationTree(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement de l\'organisation');
    } finally {
      setLoading(false);
    }
  };

  // Récupérer les unités organisationnelles
  const fetchUnits = async (empId: number, level?: string, parentId?: number) => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (level) params.append('level', level);
      if (parentId !== undefined) params.append('parent_id', parentId.toString());
      
      const response = await api.get(`/organization/employers/${empId}/units?${params}`);
      setUnits(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des unités');
    } finally {
      setLoading(false);
    }
  };

  // Créer une nouvelle unité
  const createUnit = async (empId: number, unitData: CreateUnitData): Promise<OrganizationalUnit | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post(`/organization/employers/${empId}/units`, unitData);
      
      // Rafraîchir les données
      await fetchOrganizationTree(empId);
      
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la création de l\'unité');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Mettre à jour une unité
  const updateUnit = async (unitId: number, unitData: Partial<CreateUnitData>): Promise<OrganizationalUnit | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.put(`/organization/units/${unitId}`, unitData);
      
      // Rafraîchir les données si on a un employeur
      if (employerId) {
        await fetchOrganizationTree(employerId);
      }
      
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la mise à jour de l\'unité');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Supprimer une unité
  const deleteUnit = async (unitId: number): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await api.delete(`/organization/units/${unitId}`);
      
      // Rafraîchir les données si on a un employeur
      if (employerId) {
        await fetchOrganizationTree(employerId);
      }
      
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la suppression de l\'unité');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Obtenir les niveaux possibles pour un parent
  const getPossibleChildLevels = async (unitId?: number): Promise<string[]> => {
    try {
      const url = unitId 
        ? `/organization/units/${unitId}/possible-children`
        : `/organization/employers/${employerId}/possible-root-levels`;
      
      const response = await api.get(url);
      return unitId 
        ? response.data.possible_child_levels 
        : response.data.possible_root_levels;
    } catch (err: any) {
      console.error('Erreur lors de la récupération des niveaux possibles:', err);
      return [];
    }
  };

  // Assigner un salarié à une unité
  const assignWorkerToUnit = async (workerId: number, unitId?: number): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await api.post('/organization/workers/assign', {
        worker_id: workerId,
        organizational_unit_id: unitId
      });
      
      // Rafraîchir les données si on a un employeur
      if (employerId) {
        await fetchOrganizationTree(employerId);
      }
      
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'assignation du salarié');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Migrer les données existantes
  const migrateExistingData = async (empId: number): Promise<{ migrated_count: number; message: string } | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post(`/organization/employers/${empId}/migrate`);
      
      // Rafraîchir les données
      await fetchOrganizationTree(empId);
      
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la migration');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Charger automatiquement l'arbre si employerId est fourni
  useEffect(() => {
    if (employerId) {
      fetchOrganizationTree(employerId);
    }
  }, [employerId]);

  return {
    organizationTree,
    units,
    loading,
    error,
    fetchOrganizationTree,
    fetchUnits,
    createUnit,
    updateUnit,
    deleteUnit,
    getPossibleChildLevels,
    assignWorkerToUnit,
    migrateExistingData,
  };
};