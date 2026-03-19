
import React, { useState, useEffect } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, PencilIcon, TrashIcon, CheckIcon } from "@heroicons/react/24/outline";
import { getPrimeValues, updatePrimeValues, resetBulkPrimeValues, getEmployer } from "../api";
import type { PrimeValuesOut } from "../api";

interface PrimesManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
    payrollRunId: number;
    employerId: number;
}

const PrimesManagerModal: React.FC<PrimesManagerModalProps> = ({
    isOpen,
    onClose,
    payrollRunId,
    employerId,
}) => {
    const [rows, setRows] = useState<PrimeValuesOut[]>([]);
    const [loading, setLoading] = useState(false);
    const [editingWorkerId, setEditingWorkerId] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<PrimeValuesOut | null>(null);
    const [employer, setEmployer] = useState<any>(null);
    const [selectedWorkerIds, setSelectedWorkerIds] = useState<number[]>([]);

    // Charger données
    useEffect(() => {
        if (isOpen && payrollRunId) {
            if (employerId) {
                getEmployer(employerId).then(setEmployer).catch(err => console.error("Err charge employeur", err));
            }
            loadData();
        }
    }, [isOpen, payrollRunId, employerId]);

    const loadData = async () => {
        setLoading(true);
        try {
            const data = await getPrimeValues(payrollRunId);
            // Trier par nom ?
            data.sort((a: any, b: any) => a.nom.localeCompare(b.nom));
            setRows(data);
        } catch (err) {
            console.error("Erreur chargement valeurs primes", err);
        } finally {
            setLoading(false);
        }
    };

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

        // Warning about method change
        const confirmed = window.confirm(
            "⚠️ ATTENTION : La saisie manuelle va écraser toutes les données importées précédemment pour ce salarié.\n\n" +
            "Voulez-vous continuer ?"
        );

        if (!confirmed) return;

        try {
            await updatePrimeValues(payrollRunId, editForm.worker_id, editForm);
            setEditingWorkerId(null);
            setEditForm(null);
            loadData();
        } catch (err) {
            console.error(err);
            alert("Erreur lors de la sauvegarde");
        }
    };

    const handleChange = (field: keyof PrimeValuesOut, value: string) => {
        if (!editForm) return;
        setEditForm({ ...editForm, [field]: parseFloat(value) || 0 });
    };

    // Bulk selection
    const toggleSelectAll = () => {
        if (selectedWorkerIds.length === rows.length) {
            setSelectedWorkerIds([]);
        } else {
            setSelectedWorkerIds(rows.map(r => r.worker_id));
        }
    };

    const toggleSelection = (workerId: number) => {
        if (selectedWorkerIds.includes(workerId)) {
            setSelectedWorkerIds(selectedWorkerIds.filter(id => id !== workerId));
        } else {
            setSelectedWorkerIds([...selectedWorkerIds, workerId]);
        }
    };

    const handleBulkReset = async () => {
        if (selectedWorkerIds.length === 0) return;
        if (!window.confirm(`Voulez-vous vraiment remettre à zéro les primes (Variable de Paie) pour les ${selectedWorkerIds.length} salariés sélectionnés ?`)) return;
        setLoading(true);
        try {
            await resetBulkPrimeValues(payrollRunId, selectedWorkerIds);
            setSelectedWorkerIds([]);
            loadData();
        } catch (err) {
            console.error(err);
            alert("Erreur lors de la réinitialisation en masse.");
        } finally {
            setLoading(false);
        }
    };

    // Dynamic Labels from Employer
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
                <Dialog.Panel className="mx-auto max-w-6xl w-full bg-white rounded-2xl shadow-xl overflow-hidden max-h-[90vh] flex flex-col">
                    <div className="p-6 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                        <Dialog.Title className="text-xl font-bold text-gray-900">
                            Gestion des Primes (Valeurs du Mois)
                        </Dialog.Title>
                        <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-200 transition">
                            <XMarkIcon className="w-6 h-6 text-gray-500" />
                        </button>
                    </div>

                    {/* Bulk Actions Bar */}
                    {rows.length > 0 && (
                        <div className="bg-gray-100 px-6 py-2 border-b border-gray-200 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-gray-600">
                                    {selectedWorkerIds.length} sélectionné(s)
                                </span>
                            </div>
                            {selectedWorkerIds.length > 0 && (
                                <button
                                    onClick={handleBulkReset}
                                    className="text-sm bg-red-50 text-red-600 px-3 py-1 rounded border border-red-200 hover:bg-red-100 flex items-center gap-1"
                                >
                                    <TrashIcon className="w-4 h-4" />
                                    Réinitialiser la sélection
                                </button>
                            )}
                        </div>
                    )}

                    <div className="p-6 overflow-auto flex-1">
                        {loading && rows.length === 0 ? (
                            <div className="flex justify-center py-10">
                                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
                            </div>
                        ) : rows.length === 0 ? (
                            <div className="text-center py-10 text-gray-500">
                                Aucun salarié trouvé.
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200 text-sm">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-3 py-3 w-10">
                                            <input
                                                type="checkbox"
                                                checked={rows.length > 0 && selectedWorkerIds.length === rows.length}
                                                onChange={toggleSelectAll}
                                                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                            />
                                        </th>
                                        <th className="px-3 py-3 text-left font-medium text-gray-500">Matricule</th>
                                        <th className="px-3 py-3 text-left font-medium text-gray-500">Nom</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">13ème Mois</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">{getLabel("prime1")} (MGA)</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">{getLabel("prime2")} (MGA)</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">{getLabel("prime3")} (MGA)</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">{getLabel("prime4")} (MGA)</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">{getLabel("prime5")} (MGA)</th>
                                        <th className="px-3 py-3 text-right font-medium text-gray-500">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 bg-white">
                                    {rows.map((row) => {
                                        const isEditing = editingWorkerId === row.worker_id;
                                        const displayData = isEditing && editForm ? editForm : row;

                                        return (
                                            <tr key={row.worker_id} className={isEditing ? "bg-blue-50" : "hover:bg-gray-50"}>
                                                <td className="px-3 py-3 text-center">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedWorkerIds.includes(row.worker_id)}
                                                        onChange={() => toggleSelection(row.worker_id)}
                                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                                    />
                                                </td>
                                                <td className="px-3 py-3 text-gray-900 font-medium">{row.matricule}</td>
                                                <td className="px-3 py-3 text-gray-500">{row.nom} {row.prenom}</td>

                                                {/* Editables */}
                                                {(['prime_13', 'prime1', 'prime2', 'prime3', 'prime4', 'prime5'] as const).map(field => (
                                                    <td key={field} className="px-2 py-3 text-center">
                                                        {isEditing ? (
                                                            <input
                                                                type="number"
                                                                value={displayData[field]}
                                                                onChange={(e) => handleChange(field, e.target.value)}
                                                                className="w-20 p-1 text-center border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                                                            />
                                                        ) : (
                                                            <span className={displayData[field] > 0 ? "font-bold text-gray-900" : "text-gray-300"}>
                                                                {displayData[field] > 0 ? displayData[field].toLocaleString() : "-"}
                                                            </span>
                                                        )}
                                                    </td>
                                                ))}

                                                <td className="px-3 py-3 text-right whitespace-nowrap">
                                                    {isEditing ? (
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button onClick={handleSave} className="p-1 text-green-600 hover:bg-green-100 rounded">
                                                                <CheckIcon className="w-5 h-5" />
                                                            </button>
                                                            <button onClick={handleCancelEdit} className="p-1 text-gray-400 hover:bg-gray-100 rounded">
                                                                <XMarkIcon className="w-5 h-5" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button onClick={() => handleEdit(row)} className="p-1 text-blue-600 hover:bg-blue-100 rounded">
                                                                <PencilIcon className="w-4 h-4" />
                                                            </button>
                                                            {/* Delete individual row also possible via setting to 0? Or separate button? 
                                                                Usually Reset for single worker is nice. */}
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
                    <div className="p-4 border-t border-gray-200 bg-gray-50 text-right">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
                        >
                            Fermer
                        </button>
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    );
};

export default PrimesManagerModal;
