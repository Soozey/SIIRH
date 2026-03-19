import React, { useState, useEffect } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, PencilIcon, TrashIcon, CheckIcon } from "@heroicons/react/24/outline";
import { getAllHsHmForPayroll, updateWorkerHsHm, deleteWorkerHsHm, getWorkers, resetBulkHsHm } from "../api";

interface HsHmManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
    payrollRunId: number;
    employerId: number;
}

interface WorkerSimple {
    id: number;
    matricule: string;
    nom: string;
    prenom: string;
}

interface HsHmEntry {
    id: number | null; // null for new entries
    worker_id: number;
    hsni_130_heures: number;
    hsi_130_heures: number;
    hsni_150_heures: number;
    hsi_150_heures: number;
    hmnh_heures: number;
    hmno_heures: number;
    hmd_heures: number;
    hmjf_heures: number;
    // Montants pour info
    hsni_130_montant: number;
    hsi_130_montant: number;
    // Absences
    ABSM_J: number;
    ABSM_H: number;
    ABSNR_J: number;
    ABSNR_H: number;
    ABSMP: number;
    ABS1_J: number;
    ABS1_H: number;
    ABS2_J: number;
    ABS2_H: number;
    // Avance
    avance: number;
    // Autre déductions
    autre_ded1: number;
    autre_ded2: number;
    autre_ded3: number;
    autre_ded4: number;
    // Avantages
    avantage_vehicule: number;
    avantage_logement: number;
    avantage_telephone: number;
    avantage_autres: number;

}

const HsHmManagerModal: React.FC<HsHmManagerModalProps> = ({
    isOpen,
    onClose,
    payrollRunId,
    employerId,
}) => {
    // Liste combinée : Worker + HS/HM data (si existante)
    const [combinedRows, setCombinedRows] = useState<{ worker: WorkerSimple; entry: HsHmEntry }[]>([]);
    const [loading, setLoading] = useState(false);
    const [editingWorkerId, setEditingWorkerId] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<HsHmEntry | null>(null);
    // Employer unused
    const [selectedWorkerIds, setSelectedWorkerIds] = useState<number[]>([]);

    // Charger les données
    useEffect(() => {
        if (isOpen && payrollRunId) {
            // Unused employer fetch removed
            loadData();
        }
    }, [isOpen, payrollRunId, employerId]);

    const loadData = async () => {
        setLoading(true);
        try {
            // 1. Charger tous les workers de l'employeur
            const workersData = await getWorkers(employerId);

            // 2. Charger les HS/HM existants
            const hsHmData = await getAllHsHmForPayroll(payrollRunId);

            // 3. Merger
            // Indexer HS/HM par worker_id
            const hsHmMap: Record<number, any> = {};
            hsHmData.forEach((e: any) => {
                hsHmMap[e.worker_id] = e;
            });

            // Créer la liste combinée
            const rows = workersData.map((w: any) => {
                const entry = hsHmMap[w.id] || {
                    id: null,
                    worker_id: w.id,
                    hsni_130_heures: 0,
                    hsi_130_heures: 0,
                    hsni_150_heures: 0,
                    hsi_150_heures: 0,
                    hmnh_heures: 0,
                    hmno_heures: 0,
                    hmd_heures: 0,
                    hmjf_heures: 0,
                    hsni_130_montant: 0,
                    hsi_130_montant: 0,
                    ABSM_J: 0, ABSM_H: 0,
                    ABSNR_J: 0, ABSNR_H: 0,
                    ABSMP: 0,
                    ABS1_J: 0, ABS1_H: 0,
                    ABS2_J: 0, ABS2_H: 0,
                    avance: 0,
                    autre_ded1: 0, autre_ded2: 0, autre_ded3: 0, autre_ded4: 0,
                    avantage_vehicule: 0, avantage_logement: 0, avantage_telephone: 0, avantage_autres: 0

                };
                return { worker: w, entry };
            });

            setCombinedRows(rows);

        } catch (err) {
            console.error("Erreur chargement HS/HM + Workers", err);
            // alert("Impossible de charger les données");
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (row: { worker: WorkerSimple; entry: HsHmEntry }) => {
        setEditingWorkerId(row.worker.id);
        setEditForm({ ...row.entry });
    };

    const handleCancelEdit = () => {
        setEditingWorkerId(null);
        setEditForm(null);
    };

    const handleSave = async () => {
        if (!editForm) return;
        try {
            // PUT handles creating if not exists (upsert logic in backend or checks)
            // Backend endpoint: @router.put("/{payroll_run_id}/{worker_id}")
            // It creates new if assumes MANUAL source. Perfect.
            await updateWorkerHsHm(payrollRunId, editForm.worker_id, editForm);

            //alert("Enregistré");
            setEditingWorkerId(null);
            setEditForm(null);
            loadData(); // Recharger
        } catch (err) {
            console.error(err);
            alert("Erreur lors de la sauvegarde");
        }
    };

    const handleDelete = async (workerId: number) => {
        if (!window.confirm("Êtes-vous sûr de vouloir supprimer ces HS/HM (remettre à zéro) ?")) return;
        try {
            // Backend delete
            await deleteWorkerHsHm(payrollRunId, workerId);
            loadData();
        } catch (err) {
            console.error(err);
            alert("Erreur lors de la suppression");
        }
    };

    const handleChange = (field: keyof HsHmEntry, value: string) => {
        if (!editForm) return;
        setEditForm({ ...editForm, [field]: parseFloat(value) || 0 });
        setEditForm({ ...editForm, [field]: parseFloat(value) || 0 });
    };

    const toggleSelectAll = () => {
        if (selectedWorkerIds.length === combinedRows.length) {
            setSelectedWorkerIds([]);
        } else {
            setSelectedWorkerIds(combinedRows.map(r => r.worker.id));
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
        if (!window.confirm(`Voulez-vous vraiment réinitialiser les HS/HM/Absences pour les ${selectedWorkerIds.length} salariés sélectionnés ?`)) return;
        setLoading(true);
        try {
            await resetBulkHsHm(payrollRunId, selectedWorkerIds);
            setSelectedWorkerIds([]);
            await loadData();
        } catch (err) {
            console.error(err);
            alert("Erreur lors de la réinitialisation en masse.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onClose={onClose} className="relative z-50">
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="mx-auto max-w-6xl w-full bg-white rounded-2xl shadow-xl overflow-hidden max-h-[90vh] flex flex-col">
                    <div className="p-6 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                        <Dialog.Title className="text-xl font-bold text-gray-900">
                            Gestion des Heures Supplémentaires & Majorées
                        </Dialog.Title>
                        <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-200 transition">
                            <XMarkIcon className="w-6 h-6 text-gray-500" />
                        </button>
                    </div>

                    {/* Bulk Actions Bar */}
                    {combinedRows.length > 0 && (
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
                        {loading && combinedRows.length === 0 ? (
                            <div className="flex justify-center py-10">
                                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
                            </div>
                        ) : combinedRows.length === 0 ? (
                            <div className="text-center py-10 text-gray-500">
                                Aucun salarié trouvé pour cet employeur (ID: {employerId}).
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200 text-sm">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-3 py-3 w-10">
                                            <input
                                                type="checkbox"
                                                checked={combinedRows.length > 0 && selectedWorkerIds.length === combinedRows.length}
                                                onChange={toggleSelectAll}
                                                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                            />
                                        </th>
                                        <th className="px-3 py-3 text-left font-medium text-gray-500">Matricule</th>
                                        <th className="px-3 py-3 text-left font-medium text-gray-500">Nom</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">HSNI 130</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">HSI 130</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">HSNI 150</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">HSI 150</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Nuit 30%</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Nuit 50%</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Dim 40%</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Férié 50%</th>
                                        {/* Absences */}
                                        <th className="px-2 py-3 text-center font-medium text-gray-500 border-l border-gray-200">Ab. Mal J</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Ab. Mal H</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Ab. NR J</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Ab. NR H</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Mise Pied</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 1 J</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 1 H</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 2 J</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 2 H</th>
                                        {/* Avance */}
                                        {/* Avance */}
                                        <th className="px-4 py-3 text-center font-medium text-gray-500 border-l border-gray-200 min-w-[120px]">Avance</th>
                                        {/* Autres Déductions */}
                                        <th className="px-2 py-3 text-center font-medium text-gray-500 border-l border-gray-200">Ded 1</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Ded 2</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Ded 3</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Ded 4</th>
                                        {/* Avantages */}
                                        <th className="px-2 py-3 text-center font-medium text-gray-500 border-l border-gray-200">Av. Véh</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Av. Log</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Av. Tél</th>
                                        <th className="px-2 py-3 text-center font-medium text-gray-500">Av. Aut</th>

                                        {/* Primes */}

                                        <th className="px-3 py-3 text-right font-medium text-gray-500 min-w-[100px]">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 bg-white">
                                    {combinedRows.map((row) => {
                                        const isEditing = editingWorkerId === row.worker.id;
                                        // On affiche les données soit du form (si edit) soit de l'entry
                                        const displayData = isEditing && editForm ? editForm : row.entry;
                                        // Si entry.id est null, c'est que pas encore en base => vide ou 0
                                        const hasData = row.entry.id !== null;

                                        return (

                                            <tr key={row.worker.id} className={isEditing ? "bg-blue-50" : "hover:bg-gray-50"}>
                                                <td className="px-3 py-3 text-center">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedWorkerIds.includes(row.worker.id)}
                                                        onChange={() => toggleSelection(row.worker.id)}
                                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                                    />
                                                </td>
                                                <td className="px-3 py-3 text-gray-900 font-medium">
                                                    {row.worker.matricule}
                                                </td>
                                                <td className="px-3 py-3 text-gray-500">
                                                    {row.worker.nom} {row.worker.prenom}
                                                </td>

                                                {/* Editable Columns */}
                                                {[
                                                    "hsni_130_heures", "hsi_130_heures",
                                                    "hsni_150_heures", "hsi_150_heures",
                                                    "hmnh_heures", "hmno_heures",
                                                    "hmd_heures", "hmjf_heures",
                                                    "ABSM_J", "ABSM_H",
                                                    "ABSNR_J", "ABSNR_H",
                                                    "ABSMP",
                                                    "ABS1_J", "ABS1_H",
                                                    "ABS2_J", "ABS2_H",
                                                    "avance",
                                                    "autre_ded1", "autre_ded2", "autre_ded3", "autre_ded4",
                                                    "avantage_vehicule", "avantage_logement", "avantage_telephone", "avantage_autres"
                                                ].map((field) => (
                                                    <td key={field} className="px-2 py-3 text-center">
                                                        {isEditing ? (
                                                            <input
                                                                type="number"
                                                                step={field === 'avance' ? "100" : "0.5"}
                                                                min="0"
                                                                value={(displayData as any)[field]}
                                                                onChange={(e) => handleChange(field as keyof HsHmEntry, e.target.value)}
                                                                className={`${field === 'avance' ? 'w-24' : 'w-16'} p-1 text-center border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 outline-none`}
                                                            />
                                                        ) : (
                                                            <span className={(displayData as any)[field] > 0 ? "font-bold text-gray-900" : "text-gray-300"}>
                                                                {(displayData as any)[field] > 0 ? (displayData as any)[field] : "-"}
                                                            </span>
                                                        )}
                                                    </td>
                                                ))}

                                                <td className="px-3 py-3 text-right whitespace-nowrap">
                                                    {isEditing ? (
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button
                                                                onClick={handleSave}
                                                                className="p-1 text-green-600 hover:bg-green-100 rounded"
                                                                title="Sauvegarder"
                                                            >
                                                                <CheckIcon className="w-5 h-5" />
                                                            </button>
                                                            <button
                                                                onClick={handleCancelEdit}
                                                                className="p-1 text-gray-400 hover:bg-gray-100 rounded"
                                                                title="Annuler"
                                                            >
                                                                <XMarkIcon className="w-5 h-5" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button
                                                                onClick={() => handleEdit(row)}
                                                                className="p-1 text-blue-600 hover:bg-blue-100 rounded"
                                                                title={hasData ? "Modifier" : "Ajouter des HS"}
                                                            >
                                                                <PencilIcon className="w-4 h-4" />
                                                            </button>
                                                            {hasData && (
                                                                <button
                                                                    onClick={() => handleDelete(row.worker.id)}
                                                                    className="p-1 text-red-600 hover:bg-red-100 rounded"
                                                                    title="Supprimer (Reset)"
                                                                >
                                                                    <TrashIcon className="w-4 h-4" />
                                                                </button>
                                                            )}
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

export default HsHmManagerModal;
