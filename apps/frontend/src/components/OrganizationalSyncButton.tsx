import React, { useState } from 'react';
import { api } from '../api';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

interface SyncDetailItem {
  worker_name?: string;
  old_value?: string | null;
  new_value?: string | null;
  status?: string;
  available_options?: string[];
}

interface SyncResult {
  success: boolean;
  total_updated: number;
  total_invalid_detected?: number;
  message?: string;
  details: {
    etablissements: SyncDetailItem[];
    departements: SyncDetailItem[];
    services: SyncDetailItem[];
    unites: SyncDetailItem[];
  };
}

interface OrganizationalSyncButtonProps {
  employerId: number;
  onSyncComplete?: (result: SyncResult) => void;
  className?: string;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

const EMPTY_SYNC_DETAILS: SyncResult['details'] = {
  etablissements: [],
  departements: [],
  services: [],
  unites: [],
};

const getApiErrorMessage = (error: unknown, fallback: string) => {
  const apiError = error as ApiErrorPayload;
  return apiError.response?.data?.detail || apiError.message || fallback;
};

export const OrganizationalSyncButton: React.FC<OrganizationalSyncButtonProps> = ({
  employerId,
  onSyncComplete,
  className = "",
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState<SyncResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showForceConfirm, setShowForceConfirm] = useState(false);

  const handleValidate = async () => {
    setIsLoading(true);
    try {
      const response = await api.post(`/organizational-structure/${employerId}/sync-workers`);
      const result = response.data as SyncResult;
      setLastResult(result);

      if (onSyncComplete) {
        onSyncComplete(result);
      }

      if (result.total_invalid_detected && result.total_invalid_detected > 0) {
        setShowDetails(true);
      }
    } catch (error) {
      setLastResult({
        success: false,
        total_updated: 0,
        message: getApiErrorMessage(error, 'Erreur lors de la validation'),
        details: EMPTY_SYNC_DETAILS,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleForceSync = async () => {
    setIsLoading(true);
    try {
      const response = await api.post(`/organizational-structure/${employerId}/force-sync-workers`);
      const result = response.data as SyncResult;

      setLastResult(result);
      setShowForceConfirm(false);

      if (onSyncComplete) {
        onSyncComplete(result);
      }

      if (result.total_updated > 0) {
        setShowDetails(true);
        setTimeout(() => setShowDetails(false), 5000);
      }
    } catch (error) {
      setLastResult({
        success: false,
        total_updated: 0,
        message: getApiErrorMessage(error, 'Erreur lors de la synchronisation forcee'),
        details: EMPTY_SYNC_DETAILS,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex gap-2">
        <button
          onClick={handleValidate}
          disabled={isLoading}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all flex-1
            ${isLoading
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg'
            }
          `}
        >
          <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Validation...' : 'Valider les affectations'}
        </button>

        {lastResult && lastResult.total_invalid_detected && lastResult.total_invalid_detected > 0 && (
          <button
            onClick={() => setShowForceConfirm(true)}
            disabled={isLoading}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-all font-medium"
          >
            Corriger
          </button>
        )}
      </div>

      {showForceConfirm && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <span className="font-medium text-red-800">Attention !</span>
          </div>
          <p className="text-sm text-red-700 mb-3">
            Cette action va modifier les affectations des salaries pour les faire correspondre aux structures organisationnelles.
            Les affectations actuelles seront remplacees.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleForceSync}
              disabled={isLoading}
              className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-all"
            >
              Confirmer la correction
            </button>
            <button
              onClick={() => setShowForceConfirm(false)}
              className="px-3 py-1 bg-gray-300 text-gray-700 text-sm rounded hover:bg-gray-400 transition-all"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {lastResult && !isLoading && (
        <div
          className={`
          p-3 rounded-lg border-l-4 text-sm
          ${lastResult.success
            ? (lastResult.total_updated > 0
                ? 'bg-green-50 border-green-400 text-green-800'
                : (lastResult.total_invalid_detected && lastResult.total_invalid_detected > 0
                    ? 'bg-amber-50 border-amber-400 text-amber-800'
                    : 'bg-blue-50 border-blue-400 text-blue-800'
                  )
              )
            : 'bg-red-50 border-red-400 text-red-800'
          }
        `}
        >
          <div className="flex items-center gap-2">
            {lastResult.success ? (
              lastResult.total_updated > 0 ? (
                <CheckCircleIcon className="h-5 w-5 text-green-600" />
              ) : (
                lastResult.total_invalid_detected && lastResult.total_invalid_detected > 0 ? (
                  <ExclamationTriangleIcon className="h-5 w-5 text-amber-600" />
                ) : (
                  <InformationCircleIcon className="h-5 w-5 text-blue-600" />
                )
              )
            ) : (
              <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            )}

            <span className="font-medium">
              {lastResult.success
                ? (lastResult.total_updated > 0
                    ? `${lastResult.total_updated} salarie(s) synchronise(s)`
                    : (lastResult.total_invalid_detected && lastResult.total_invalid_detected > 0
                        ? `${lastResult.total_invalid_detected} affectation(s) invalide(s) detectee(s)`
                        : 'Toutes les affectations sont valides'
                      )
                  )
                : 'Erreur de validation'
              }
            </span>

            {((lastResult.total_updated > 0) || (lastResult.total_invalid_detected && lastResult.total_invalid_detected > 0)) && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs underline hover:no-underline"
              >
                {showDetails ? 'Masquer' : 'Details'}
              </button>
            )}
          </div>

          {lastResult.message && (
            <p className="text-xs mt-1 opacity-80">{lastResult.message}</p>
          )}
        </div>
      )}

      {showDetails && lastResult && ((lastResult.total_updated > 0) || (lastResult.total_invalid_detected && lastResult.total_invalid_detected > 0)) && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <h4 className="font-medium text-gray-900">
            {lastResult.total_updated > 0 ? 'Details des synchronisations :' : 'Affectations invalides detectees :'}
          </h4>

          {Object.entries(lastResult.details).map(([structureType, updates]) => {
            if (updates.length === 0) return null;

            return (
              <div key={structureType} className="space-y-2">
                <h5 className="text-sm font-medium text-gray-700 capitalize">
                  {structureType} ({updates.length})
                </h5>
                <div className="space-y-1">
                  {updates.map((update, index: number) => (
                    <div key={index} className="text-xs text-gray-600 pl-4">
                      <span className="font-medium">{update.worker_name}</span>
                      <span className="text-gray-500 mx-2">:</span>
                      <span className={lastResult.total_updated > 0 ? "line-through text-red-500" : "text-red-600"}>
                        {update.old_value}
                      </span>
                      {lastResult.total_updated > 0 && update.new_value && (
                        <>
                          <span className="mx-2">→</span>
                          <span className="text-green-600">{update.new_value}</span>
                        </>
                      )}
                      {update.status === 'invalid_assignment_detected' && (
                        <div className="text-xs text-amber-600 mt-1 pl-4">
                          Options disponibles: {update.available_options?.join(', ') || 'Aucune'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="text-xs text-gray-500">
        <InformationCircleIcon className="h-4 w-4 inline mr-1" />
        Validez d'abord les affectations pour detecter les problemes sans modifier les donnees.
      </div>
    </div>
  );
};

export default OrganizationalSyncButton;
