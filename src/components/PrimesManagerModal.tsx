import React, { useCallback, useEffect, useState } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, PencilIcon, TrashIcon, CheckIcon } from "@heroicons/react/24/outline";
import { getPrimeValues, updatePrimeValues, resetBulkPrimeValues, getEmployer } from "../api";
import type { PrimeValuesOut } from "../api";
import { useTheme } from "../contexts/ThemeContext";

interface PrimesManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
    payrollRunId: number;
    employerId: number;
}

interface EmployerPrimeLabels {
    label_prime1?: string;
    label_prime2?: string;
    label_prime3?: string;
    label_prime4?: string;
    label_prime5?: string;
}

const PrimesManagerModal: React.FC<PrimesManagerModalProps> = ({
    isOpen,
    onClose,
    payrollRunId,
    employerId,
}) => {
    const { theme } = useTheme();
    const [rows, setRows] = useState<PrimeValuesOut[]>([]);
    const [loading, setLoading] = useState(false);
    const [editingWorkerId, setEditingWorkerId] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<PrimeValuesOut | null>(null);
    const [employer, setEmployer] = useState<EmployerPrimeLabels | null>(null);
    const [selectedWorkerIds, setSelectedWorkerIds] = useState<number[]>([]);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await getPrimeValues(payrollRunId);
            data.sort((a: PrimeValuesOut, b: PrimeValuesOut) => `${a.nom || ""}`.localeCompare(`${b.nom || ""}`));
            setRows(data);
        } catch {
            setRows([]);
        } finally {
            setLoading(false);
        }
    }, [payrollRunId]);

    useEffect(() => {
        if (isOpen && payrollRunId) {
            if (employerId) {
                getEmployer(employerId)
                    .then((data) => setEmployer(data as EmployerPrimeLabels))
                    .catch(() => setEmployer(null));
            }
            void loadData();
        }
    }, [isOpen, payrollRunId, employerId, loadData]);

    const handleEdit = (row: PrimeValuesOut) => {
        setEditingWorkerId(row.worker_id);
        setEditForm({ ...row });
    };

    const handleCancelEdit = () => {
        setEditingWorkerId(null);
        setEditForm(null);
    };

    const handleSave = async () => {
        if (!editForm) return;

        const confirmed = window.confirm(
            "ATTENTION : La saisie manuelle va ecraser toutes les donnees importees precedemment pour ce salarie.\n\n" +
            "Voulez-vous continuer ?"
        );

        if (!confirmed) return;

        try {
            await updatePrimeValues(payrollRunId, editForm.worker_id, editForm);
            setEditingWorkerId(null);
            setEditForm(null);
            void loadData();
        } catch {
            alert("Erreur lors de la sauvegarde");
        }
    };

    const handleChange = (field: keyof PrimeValuesOut, value: string) => {
        if (!editForm) return;
        setEditForm({ ...editForm, [field]: parseFloat(value) || 0 });
    };

    const toggleSelectAll = () => {
        if (selectedWorkerIds.length === rows.length) {
            setSelectedWorkerIds([]);
        } else {
            setSelectedWorkerIds(rows.map((r) => r.worker_id));
        }
    };

    const toggleSelection = (workerId: number) => {
        if (selectedWorkerIds.includes(workerId)) {
            setSelectedWorkerIds(selectedWorkerIds.filter((id) => id !== workerId));
        } else {
            setSelectedWorkerIds([...selectedWorkerIds, workerId]);
        }
    };

    const handleBulkReset = async () => {
        if (selectedWorkerIds.length === 0) return;
        if (!window.confirm(`Voulez-vous vraiment remettre a zero les primes pour les ${selectedWorkerIds.length} salaries selectionnes ?`)) return;
        setLoading(true);
        try {
            await resetBulkPrimeValues(payrollRunId, selectedWorkerIds);
            setSelectedWorkerIds([]);
            void loadData();
        } catch {
            alert("Erreur lors de la reinitialisation en masse.");
        } finally {
            setLoading(false);
        }
    };

    const getLabel = (key: string) => {
        if (!employer) return key;
        if (key === "prime1") return employer.label_prime1 || "Prime 1";
        if (key === "prime2") return employer.label_prime2 || "Prime 2";
        if (key === "prime3") return employer.label_prime3 || "Prime 3";
        if (key === "prime4") return employer.label_prime4 || "Prime 4";
        if (key === "prime5") return employer.label_prime5 || "Prime 5";
        return key;
    };

    return (
        <Dialog open={isOpen} onClose={onClose} className="relative z-50">
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className={`mx-auto max-w-6xl w-full rounded-2xl shadow-xl overflow-hidden max-h-[90vh] flex flex-col ${theme === "light" ? "bg-white" : "border border-slate-700 bg-slate-900 text-slate-100"}`}>
                    <div className={`p-6 border-b flex justify-between items-center ${theme === "light" ? "border-gray-200 bg-gray-50" : "border-slate-700 bg-slate-800"}`}>
                        <Dialog.Title className={`text-xl font-bold ${theme === "light" ? "text-gray-900" : "text-slate-100"}`}>
                            Gestion des Primes (Valeurs du Mois)
                        </Dialog.Title>
                        <button onClick={onClose} className={`p-2 rounded-full transition ${theme === "light" ? "hover:bg-gray-200" : "hover:bg-slate-700"}`}>
                            <XMarkIcon className={`w-6 h-6 ${theme === "light" ? "text-gray-500" : "text-slate-400"}`} />
                        </button>
                    </div>

                    {rows.length > 0 && (
                        <div className={`px-6 py-2 border-b flex items-center justify-between ${theme === "light" ? "bg-gray-100 border-gray-200" : "bg-slate-800 border-slate-700"}`}>
                            <div className="flex items-center gap-2">
                                <span className={`text-sm ${theme === "light" ? "text-gray-600" : "text-slate-300"}`}>
                                    {selectedWorkerIds.length} selectionne(s)
                                </span>
                            </div>
                            {selectedWorkerIds.length > 0 && (
                                <button
                                    onClick={handleBulkReset}
                                    className="text-sm bg-red-50 text-red-600 px-3 py-1 rounded border border-red-200 hover:bg-red-100 flex items-center gap-1"
                                >
                                    <TrashIcon className="w-4 h-4" />
                                    Reinitialiser la selection
                                </button>
                            )}
                        </div>
                    )}

                    <div className="p-6 overflow-auto flex-1">
                        {loading && rows.length === 0 ? (
                            <div className="flex justify-center py-10">
                                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
                            </div>
                        ) : rows.length === 0 ? (
                            <div className={`text-center py-10 ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>
                                Aucun salarie trouve.
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200 text-sm">
                                <thead className={theme === "light" ? "bg-gray-50" : "bg-slate-800"}>
                                    <tr>
                                        <th className="px-3 py-3 w-10">
                                            <input
                                                type="checkbox"
                                                checked={rows.length > 0 && selectedWorkerIds.length === rows.length}
                                                onChange={toggleSelectAll}
                                                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                            />
                                        </th>
                                        <th className={`px-3 py-3 text-left font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>Matricule</th>
                                        <th className={`px-3 py-3 text-left font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>Nom</th>
                                        <th className={`px-2 py-3 text-center font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>13eme Mois</th>
                                        <th className={`px-2 py-3 text-center font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>{getLabel("prime1")} (Ar)</th>
                                        <th className={`px-2 py-3 text-center font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>{getLabel("prime2")} (Ar)</th>
                                        <th className={`px-2 py-3 text-center font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>{getLabel("prime3")} (Ar)</th>
                                        <th className={`px-2 py-3 text-center font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>{getLabel("prime4")} (Ar)</th>
                                        <th className={`px-2 py-3 text-center font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>{getLabel("prime5")} (Ar)</th>
                                        <th className={`px-3 py-3 text-right font-medium ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody className={`divide-y ${theme === "light" ? "divide-gray-200 bg-white" : "divide-slate-700 bg-slate-900"}`}>
                                    {rows.map((row) => {
                                        const isEditing = editingWorkerId === row.worker_id;
                                        const displayData = isEditing && editForm ? editForm : row;

                                        return (
                                            <tr key={row.worker_id} className={isEditing ? "bg-blue-50" : theme === "light" ? "hover:bg-gray-50" : "hover:bg-slate-800"}>
                                                <td className="px-3 py-3 text-center">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedWorkerIds.includes(row.worker_id)}
                                                        onChange={() => toggleSelection(row.worker_id)}
                                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                                    />
                                                </td>
                                                <td className={`px-3 py-3 font-medium ${theme === "light" ? "text-gray-900" : "text-slate-100"}`}>{row.matricule}</td>
                                                <td className={`px-3 py-3 ${theme === "light" ? "text-gray-500" : "text-slate-300"}`}>{row.nom} {row.prenom}</td>

                                                {(['prime_13', 'prime1', 'prime2', 'prime3', 'prime4', 'prime5'] as const).map((field) => (
                                                    <td key={field} className="px-2 py-3 text-center">
                                                        {isEditing ? (
                                                            <input
                                                                type="number"
                                                                step="100"
                                                                min="0"
                                                                value={Number(displayData[field] ?? 0)}
                                                                onChange={(e) => handleChange(field, e.target.value)}
                                                                className={`w-24 p-1 text-center rounded focus:ring-2 focus:ring-blue-500 outline-none ${theme === "light" ? "border border-blue-300 bg-white text-gray-900" : "border border-slate-600 bg-slate-800 text-slate-100"}`}
                                                            />
                                                        ) : (
                                                            <span className={Number(displayData[field] ?? 0) > 0 ? (theme === "light" ? "font-bold text-gray-900" : "font-bold text-slate-100") : (theme === "light" ? "text-gray-300" : "text-slate-600")}>
                                                                {Number(displayData[field] ?? 0) > 0 ? Number(displayData[field] ?? 0) : "-"}
                                                            </span>
                                                        )}
                                                    </td>
                                                ))}

                                                <td className="px-3 py-3 text-right whitespace-nowrap">
                                                    {isEditing ? (
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button onClick={handleSave} className="p-1 text-green-600 hover:bg-green-100 rounded" title="Sauvegarder">
                                                                <CheckIcon className="w-5 h-5" />
                                                            </button>
                                                            <button onClick={handleCancelEdit} className={`p-1 rounded ${theme === "light" ? "text-gray-400 hover:bg-gray-100" : "text-slate-400 hover:bg-slate-800"}`} title="Annuler">
                                                                <XMarkIcon className="w-5 h-5" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button onClick={() => handleEdit(row)} className="p-1 text-blue-600 hover:bg-blue-100 rounded" title="Modifier">
                                                                <PencilIcon className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        )}
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    );
};

export default PrimesManagerModal;
