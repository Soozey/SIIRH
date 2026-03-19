import { useState, useEffect } from 'react';
import { Tabs, Tab, Box } from '@mui/material';
import { OrganizationManagerFixed } from '../components/OrganizationManagerFixed';
import SimpleOrganizationalUnitManager from '../components/SimpleOrganizationalUnitManager';
import { api } from '../api';

interface Employer {
  id: number;
  raison_sociale: string;
  nif: string;
}

export default function Organization() {
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    const fetchEmployers = async () => {
      try {
        const response = await api.get('/employers');
        setEmployers(response.data);
        
        // Sélectionner automatiquement le premier employeur s'il n'y en a qu'un
        if (response.data.length === 1) {
          setSelectedEmployerId(response.data[0].id);
        }
      } catch (error) {
        console.error('Erreur lors du chargement des employeurs:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEmployers();
  }, []);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const tabItems = [
    {
      label: 'Gestion Classique',
      content: selectedEmployerId ? (
        <OrganizationManagerFixed 
          key={`legacy-${refreshKey}`}
          employerId={selectedEmployerId} 
        />
      ) : (
        <div className="text-center py-8 text-gray-500">
          Sélectionnez un employeur pour gérer l'organisation
        </div>
      )
    },
    {
      label: 'Gestion Hiérarchique avec Suppression',
      content: selectedEmployerId ? (
        <SimpleOrganizationalUnitManager 
          key={`hierarchical-${refreshKey}`}
          employerId={selectedEmployerId}
          onRefresh={handleRefresh}
        />
      ) : (
        <div className="text-center py-8 text-gray-500">
          Sélectionnez un employeur pour gérer la hiérarchie organisationnelle
        </div>
      )
    }
  ];

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
      
      {/* Sélection de l'employeur */}
      {employers.length > 1 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sélectionner un employeur
          </label>
          <select
            value={selectedEmployerId || ''}
            onChange={(e) => setSelectedEmployerId(Number(e.target.value))}
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

      {/* Onglets de gestion */}
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
              : "Veuillez sélectionner un employeur pour gérer sa structure organisationnelle."
            }
          </div>
        </div>
      )}
    </div>
  );
}