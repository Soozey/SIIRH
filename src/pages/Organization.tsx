import { useEffect, useMemo, useRef, useState } from 'react';
import { Tabs, Tab, Box } from '@mui/material';
import { useSearchParams } from 'react-router-dom';
import { OrganizationManagerFixed } from '../components/OrganizationManagerFixed';
import SimpleOrganizationalUnitManager from '../components/SimpleOrganizationalUnitManager';
import { api } from '../api';

interface Employer {
  id: number;
  raison_sociale: string;
  nif: string;
}

export default function Organization() {
  const [searchParams] = useSearchParams();
  const initialEmployerIdRef = useRef<number | null>(null);
  const initialTabRef = useRef<number>(0);

  if (initialEmployerIdRef.current === null) {
    const employerValue = Number(searchParams.get('employer_id'));
    initialEmployerIdRef.current = Number.isFinite(employerValue) && employerValue > 0 ? employerValue : null;
    const tabValue = Number(searchParams.get('tab'));
    initialTabRef.current = tabValue === 1 ? 1 : 0;
  }

  const [employers, setEmployers] = useState<Employer[]>([]);
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(initialEmployerIdRef.current);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState(initialTabRef.current);
  const didResolveInitialEmployerRef = useRef(false);

  useEffect(() => {
    let isMounted = true;

    const fetchEmployers = async () => {
      try {
        const response = await api.get('/employers');
        if (!isMounted) {
          return;
        }
        setEmployers(response.data as Employer[]);
      } catch (error) {
        console.error('Erreur lors du chargement des employeurs:', error);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchEmployers();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (didResolveInitialEmployerRef.current || employers.length === 0) {
      return;
    }

    const initialEmployerId = initialEmployerIdRef.current;
    const matchedEmployer = initialEmployerId
      ? employers.find((employer) => employer.id === initialEmployerId)
      : null;

    if (matchedEmployer) {
      setSelectedEmployerId(matchedEmployer.id);
    } else if (employers.length === 1) {
      setSelectedEmployerId(employers[0].id);
    } else if (selectedEmployerId !== null && employers.some((employer) => employer.id === selectedEmployerId)) {
      setSelectedEmployerId(selectedEmployerId);
    } else {
      setSelectedEmployerId(null);
    }

    didResolveInitialEmployerRef.current = true;
  }, [employers, selectedEmployerId]);

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    const nextTab = newValue === 1 ? 1 : 0;
    if (nextTab !== activeTab) {
      setActiveTab(nextTab);
    }
  };

  const tabItems = useMemo(() => [
    {
      label: 'Gestion Classique',
      content: selectedEmployerId ? (
        <OrganizationManagerFixed employerId={selectedEmployerId} />
      ) : (
        <div className="text-center py-8 text-gray-500">
          Sélectionnez un employeur pour gérer l&apos;organisation.
        </div>
      ),
    },
    {
      label: 'Gestion Hiérarchique avec Suppression',
      content: selectedEmployerId ? (
        <SimpleOrganizationalUnitManager
          employerId={selectedEmployerId}
          onRefresh={handleRefresh}
        />
      ) : (
        <div className="text-center py-8 text-gray-500">
          Sélectionnez un employeur pour gérer la hiérarchie organisationnelle.
        </div>
      ),
    },
  ], [refreshKey, selectedEmployerId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-4">Gestion Organisationnelle</h1>
      <div className="mb-6 rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
        Les salariés affichés dans l&apos;organisation priorisent désormais la vue maître canonique quand elle existe, afin que les changements d&apos;identité, poste ou département se reflètent plus uniformément dans les portails.
      </div>

      {employers.length > 1 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sélectionner un employeur
          </label>
          <select
            value={selectedEmployerId || ''}
            onChange={(e) => {
              const nextEmployerId = e.target.value ? Number(e.target.value) : null;
              if (nextEmployerId === selectedEmployerId) {
                return;
              }
              setSelectedEmployerId(nextEmployerId);
            }}
            className="block w-full max-w-md px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">-- Choisir un employeur --</option>
            {employers.map((employer) => (
              <option key={employer.id} value={employer.id}>
                {employer.raison_sociale} ({employer.nif})
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedEmployerId ? (
        <Box sx={{ width: '100%' }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={activeTab} onChange={handleTabChange} aria-label="Organisation tabs">
              {tabItems.map((item, index) => (
                <Tab key={index} label={item.label} />
              ))}
            </Tabs>
          </Box>
          <Box sx={{ mt: 3 }}>
            {tabItems[activeTab]?.content}
          </Box>
        </Box>
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-500">
            {employers.length === 0
              ? "Aucun employeur trouvé. Veuillez d'abord créer un employeur."
              : "Veuillez sélectionner un employeur pour gérer sa structure organisationnelle."}
          </div>
        </div>
      )}
    </div>
  );
}
