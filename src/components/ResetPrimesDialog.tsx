import { useState } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import { api } from "../api";

interface ResetPrimesDialogProps {
    isOpen: boolean;
    onClose: () => void;
    period: string;
    employerId: number;
    onSuccess?: () => void;
}

export default function ResetPrimesDialog({
    isOpen,
    onClose,
    period,
    employerId,
    onSuccess,
}: ResetPrimesDialogProps) {
    const [isResetting, setIsResetting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleReset = async () => {
        // Confirmation is already done via the Dialog itself
        // if (!window.confirm(...)) return;

        setIsResetting(true);
        setError(null);

        try {
            const response = await api.post(`/primes/reset-overrides?period=${period}&employer_id=${employerId}`);

            alert(`✅ ${response.data.message}`);

            if (onSuccess) {
                onSuccess();
            }

            onClose();
        } catch (err: any) {
            console.error("Reset error:", err);
            const msg = err.response?.data?.detail || "Une erreur est survenue lors de la réinitialisation.";
            setError(msg);
        } finally {
            setIsResetting(false);
        }
    };

    return (
        <Dialog open={isOpen} onClose={onClose} className="relative z-50">
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl">
                    <div className="flex items-center justify-between mb-4">
                        <Dialog.Title className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
                            Réinitialiser les primes
                        </Dialog.Title>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                        >
                            <XMarkIcon className="h-6 w-6" />
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                            <p className="text-sm text-red-800">
                                <strong>Cette action va :</strong>
                            </p>
                            <ul className="mt-2 text-sm text-red-700 list-disc list-inside space-y-1">
                                <li>Supprimer toutes les valeurs de primes importées via Excel</li>
                                <li>Restaurer les formules par défaut (Gestion des Primes)</li>
                                <li>Affecter tous les salariés de cette période</li>
                            </ul>
                        </div>

                        {error && (
                            <div className="bg-red-100 border border-red-300 rounded-lg p-3">
                                <p className="text-sm text-red-800">{error}</p>
                            </div>
                        )}

                        <div className="flex gap-3 justify-end mt-6">
                            <button
                                onClick={onClose}
                                disabled={isResetting}
                                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50"
                            >
                                Annuler
                            </button>
                            <button
                                onClick={handleReset}
                                disabled={isResetting}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50 flex items-center gap-2"
                            >
                                {isResetting ? (
                                    <>
                                        <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        Réinitialisation...
                                    </>
                                ) : (
                                    "Réinitialiser"
                                )}
                            </button>
                        </div>
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    );
}
