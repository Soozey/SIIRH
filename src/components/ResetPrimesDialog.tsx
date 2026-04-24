import { useEffect, useState } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import { api } from "../api";
import type { PayrollOrganizationFilters } from "../api";
import { useTheme } from "../contexts/ThemeContext";

interface ResetPrimesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  period: string;
  employerId: number;
  employerLabel?: string | null;
  organizationFilters?: PayrollOrganizationFilters | null;
  onSuccess?: () => void;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

export default function ResetPrimesDialog({
  isOpen,
  onClose,
  period,
  employerId,
  employerLabel,
  organizationFilters,
  onSuccess,
}: ResetPrimesDialogProps) {
  const { theme } = useTheme();
  const [isResetting, setIsResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    setError(null);
  }, [employerId, isOpen]);

  const handleReset = async () => {
    if (!employerId) {
      setError("Veuillez sélectionner un employeur sur la page paie avant la réinitialisation.");
      return;
    }

    setIsResetting(true);
    setError(null);

    try {
      const response = await api.post(
        `/primes/reset-overrides?period=${encodeURIComponent(period)}&employer_id=${employerId}`
        + `${organizationFilters?.etablissement ? `&etablissement=${encodeURIComponent(organizationFilters.etablissement)}` : ""}`
        + `${organizationFilters?.departement ? `&departement=${encodeURIComponent(organizationFilters.departement)}` : ""}`
        + `${organizationFilters?.service ? `&service=${encodeURIComponent(organizationFilters.service)}` : ""}`
        + `${organizationFilters?.unite ? `&unite=${encodeURIComponent(organizationFilters.unite)}` : ""}`
      );

      alert(`OK ${response.data.message}`);

      if (onSuccess) {
        onSuccess();
      }

      onClose();
    } catch (err: unknown) {
      const apiError = err as ApiErrorPayload;
      const msg =
        apiError.response?.data?.detail ||
        apiError.message ||
        "Une erreur est survenue lors de la reinitialisation.";
      setError(msg);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className={`mx-auto max-w-md rounded-2xl p-6 shadow-xl ${theme === "light" ? "bg-white" : "border border-slate-700 bg-slate-900 text-slate-100"}`}>
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className={`flex items-center gap-2 text-lg font-bold ${theme === "light" ? "text-gray-900" : "text-slate-100"}`}>
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
              Reinitialiser les primes
            </Dialog.Title>
            <button
              onClick={onClose}
              className={`transition-colors ${theme === "light" ? "text-gray-400 hover:text-gray-600" : "text-slate-400 hover:text-slate-200"}`}
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          <div className="space-y-4">
            <div className={`rounded-xl px-4 py-3 text-sm ${theme === "light" ? "border border-slate-200 bg-slate-50 text-slate-600" : "border border-slate-700 bg-slate-800 text-slate-300"}`}>
              Employeur actif de la page paie: <span className={`font-semibold ${theme === "light" ? "text-slate-900" : "text-slate-100"}`}>{employerLabel || employerId || "-"}</span>
            </div>

            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-sm text-red-800">
                <strong>Cette action va :</strong>
              </p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-red-700">
                <li>Supprimer toutes les valeurs de primes importees via Excel</li>
                <li>Restaurer les formules par defaut du paramétrage de primes</li>
                <li>Affecter tous les salaries de cette periode pour l'employeur selectionne</li>
              </ul>
            </div>

            {error ? (
              <div className="rounded-lg border border-red-300 bg-red-100 p-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            ) : null}

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={onClose}
                disabled={isResetting}
                className={`rounded-lg px-4 py-2 font-medium transition-colors disabled:opacity-50 ${theme === "light" ? "border border-gray-300 text-gray-700 hover:bg-gray-50" : "border border-slate-600 text-slate-200 hover:bg-slate-800"}`}
              >
                Annuler
              </button>
              <button
                onClick={handleReset}
                disabled={isResetting || !employerId}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                {isResetting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Reinitialisation...
                  </>
                ) : (
                  "Reinitialiser"
                )}
              </button>
            </div>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
}
