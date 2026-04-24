import { useEffect, useRef, useState } from 'react';
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

interface ApiErrorPayload {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

const getApiErrorMessage = (error: unknown, fallback: string) => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.detail || apiError.message || fallback;
};

export const useOrganization = (employerId?: number) => {
  const [organizationTree, setOrganizationTree] = useState<OrganizationTree | null>(null);
  const [units, setUnits] = useState<OrganizationalUnit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const organizationCacheRef = useRef<Record<number, OrganizationTree>>({});

  const fetchOrganizationTree = async (empId: number, options?: { force?: boolean }) => {
    const cachedTree = organizationCacheRef.current[empId];
    if (cachedTree && !options?.force) {
      setOrganizationTree(cachedTree);
      setError(null);
      return cachedTree;
    }

    try {
      if (!cachedTree) {
        setLoading(true);
      }
      setError(null);
      const response = await api.get(`/organization/employers/${empId}/tree`);
      const tree = response.data as OrganizationTree;
      organizationCacheRef.current[empId] = tree;
      setOrganizationTree(tree);
      return tree;
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Erreur lors du chargement de l'organisation"));
      return null;
    } finally {
      if (!cachedTree) {
        setLoading(false);
      }
    }
  };

  const fetchUnits = async (empId: number, level?: string, parentId?: number) => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (level) params.append('level', level);
      if (parentId !== undefined) params.append('parent_id', parentId.toString());

      const response = await api.get(`/organization/employers/${empId}/units?${params}`);
      setUnits(response.data as OrganizationalUnit[]);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Erreur lors du chargement des unites'));
    } finally {
      setLoading(false);
    }
  };

  const createUnit = async (empId: number, unitData: CreateUnitData): Promise<OrganizationalUnit | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post(`/organization/employers/${empId}/units`, unitData);
      delete organizationCacheRef.current[empId];
      await fetchOrganizationTree(empId, { force: true });
      return response.data as OrganizationalUnit;
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Erreur lors de la creation de l'unite"));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const updateUnit = async (
    unitId: number,
    unitData: Partial<CreateUnitData>,
  ): Promise<OrganizationalUnit | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.put(`/organization/units/${unitId}`, unitData);
      if (employerId) {
        delete organizationCacheRef.current[employerId];
        await fetchOrganizationTree(employerId, { force: true });
      }
      return response.data as OrganizationalUnit;
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Erreur lors de la mise a jour de l'unite"));
      return null;
    } finally {
      setLoading(false);
    }
  };

  const deleteUnit = async (unitId: number): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await api.delete(`/organization/units/${unitId}`);
      if (employerId) {
        delete organizationCacheRef.current[employerId];
        await fetchOrganizationTree(employerId, { force: true });
      }
      return true;
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Erreur lors de la suppression de l'unite"));
      return false;
    } finally {
      setLoading(false);
    }
  };

  const getPossibleChildLevels = async (unitId?: number): Promise<string[]> => {
    try {
      const url = unitId
        ? `/organization/units/${unitId}/possible-children`
        : `/organization/employers/${employerId}/possible-root-levels`;

      const response = await api.get(url);
      return unitId
        ? (response.data.possible_child_levels as string[])
        : (response.data.possible_root_levels as string[]);
    } catch {
      return [];
    }
  };

  const assignWorkerToUnit = async (workerId: number, unitId?: number): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await api.post('/organization/workers/assign', {
        worker_id: workerId,
        organizational_unit_id: unitId,
      });
      if (employerId) {
        delete organizationCacheRef.current[employerId];
        await fetchOrganizationTree(employerId, { force: true });
      }
      return true;
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Erreur lors de l'assignation du salarie"));
      return false;
    } finally {
      setLoading(false);
    }
  };

  const migrateExistingData = async (
    empId: number,
  ): Promise<{ migrated_count: number; message: string } | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post(`/organization/employers/${empId}/migrate`);
      delete organizationCacheRef.current[empId];
      await fetchOrganizationTree(empId, { force: true });
      return response.data as { migrated_count: number; message: string };
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Erreur lors de la migration'));
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employerId) {
      const cachedTree = organizationCacheRef.current[employerId];
      if (cachedTree) {
        setOrganizationTree(cachedTree);
        setError(null);
        return;
      }
      void fetchOrganizationTree(employerId);
      return;
    }
    setOrganizationTree(null);
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
