import React, { useCallback, useEffect, useState } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, PencilIcon, TrashIcon, CheckIcon } from "@heroicons/react/24/outline";
import {
  getAllHsHmForPayroll,
  type PayrollOrganizationFilters,
  updateWorkerHsHm,
  deleteWorkerHsHm,
  getWorkers,
  resetBulkHsHm,
} from "../api";

interface HsHmManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  payrollRunId: number;
  employerId: number;
  employerLabel?: string | null;
  organizationFilters?: PayrollOrganizationFilters | null;
  period: string;
}

interface WorkerSimple {
  id: number;
  matricule: string;
  nom: string;
  prenom: string;
}

interface HsHmEntry {
  id: number | null;
  worker_id: number;
  hsni_130_heures: number;
  hsi_130_heures: number;
  hsni_150_heures: number;
  hsi_150_heures: number;
  hmnh_heures: number;
  hmno_heures: number;
  hmd_heures: number;
  hmjf_heures: number;
  hsni_130_montant: number;
  hsi_130_montant: number;
  ABSM_J: number;
  ABSM_H: number;
  ABSNR_J: number;
  ABSNR_H: number;
  ABSMP: number;
  ABS1_J: number;
  ABS1_H: number;
  ABS2_J: number;
  ABS2_H: number;
  avance: number;
  autre_ded1: number;
  autre_ded2: number;
  autre_ded3: number;
  autre_ded4: number;
  avantage_vehicule: number;
  avantage_logement: number;
  avantage_telephone: number;
  avantage_autres: number;
}

type CombinedRow = { worker: WorkerSimple; entry: HsHmEntry };

const createEmptyEntry = (workerId: number): HsHmEntry => ({
  id: null,
  worker_id: workerId,
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
  ABSM_J: 0,
  ABSM_H: 0,
  ABSNR_J: 0,
  ABSNR_H: 0,
  ABSMP: 0,
  ABS1_J: 0,
  ABS1_H: 0,
  ABS2_J: 0,
  ABS2_H: 0,
  avance: 0,
  autre_ded1: 0,
  autre_ded2: 0,
  autre_ded3: 0,
  autre_ded4: 0,
  avantage_vehicule: 0,
  avantage_logement: 0,
  avantage_telephone: 0,
  avantage_autres: 0,
});

const editableFields: Array<keyof HsHmEntry> = [
  "hsni_130_heures",
  "hsi_130_heures",
  "hsni_150_heures",
  "hsi_150_heures",
  "hmnh_heures",
  "hmno_heures",
  "hmd_heures",
  "hmjf_heures",
  "ABSM_J",
  "ABSM_H",
  "ABSNR_J",
  "ABSNR_H",
  "ABSMP",
  "ABS1_J",
  "ABS1_H",
  "ABS2_J",
  "ABS2_H",
  "avance",
  "autre_ded1",
  "autre_ded2",
  "autre_ded3",
  "autre_ded4",
  "avantage_vehicule",
  "avantage_logement",
  "avantage_telephone",
  "avantage_autres",
];

const HsHmManagerModal: React.FC<HsHmManagerModalProps> = ({
  isOpen,
  onClose,
  payrollRunId,
  employerId,
  employerLabel,
  organizationFilters,
  period,
}) => {
  const [combinedRows, setCombinedRows] = useState<CombinedRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingWorkerId, setEditingWorkerId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<HsHmEntry | null>(null);
  const [selectedWorkerIds, setSelectedWorkerIds] = useState<number[]>([]);

  const loadData = useCallback(async () => {
    if (!employerId || !payrollRunId) {
      setCombinedRows([]);
      return;
    }

    setLoading(true);
    try {
      const workersData = await getWorkers(employerId, organizationFilters);
      const hsHmData = await getAllHsHmForPayroll(payrollRunId, organizationFilters);

      const hsHmMap: Record<number, HsHmEntry> = {};
      hsHmData.forEach((entry: HsHmEntry) => {
        hsHmMap[entry.worker_id] = entry;
      });

      const rows: CombinedRow[] = (workersData as WorkerSimple[]).map((worker) => ({
        worker,
        entry: hsHmMap[worker.id] || createEmptyEntry(worker.id),
      }));

      setCombinedRows(rows);
    } catch (err) {
      console.error("Erreur chargement HS/HM + Workers", err);
      setCombinedRows([]);
    } finally {
      setLoading(false);
    }
  }, [employerId, payrollRunId, organizationFilters]);

  useEffect(() => {
    if (isOpen && payrollRunId && employerId) {
      void loadData();
    }
  }, [isOpen, payrollRunId, employerId, loadData]);

  useEffect(() => {
    setEditingWorkerId(null);
    setEditForm(null);
    setSelectedWorkerIds([]);
  }, [payrollRunId, employerId]);

  const handleEdit = (row: CombinedRow) => {
    setEditingWorkerId(row.worker.id);
    setEditForm({ ...row.entry });
  };

  const handleCancelEdit = () => {
    setEditingWorkerId(null);
    setEditForm(null);
  };

  const handleSave = async () => {
    if (!editForm || !payrollRunId) return;
    try {
      await updateWorkerHsHm(payrollRunId, editForm.worker_id, editForm);
      setEditingWorkerId(null);
      setEditForm(null);
      void loadData();
    } catch {
      alert("Erreur lors de la sauvegarde");
    }
  };

  const handleDelete = async (workerId: number) => {
    if (!payrollRunId) return;
    if (!window.confirm("Etes-vous sur de vouloir supprimer ces HS/HM et absences ?")) return;
    try {
      await deleteWorkerHsHm(payrollRunId, workerId);
      void loadData();
    } catch {
      alert("Erreur lors de la suppression");
    }
  };

  const handleChange = (field: keyof HsHmEntry, value: string) => {
    if (!editForm) return;
    setEditForm({ ...editForm, [field]: parseFloat(value) || 0 });
  };

  const toggleSelectAll = () => {
    if (selectedWorkerIds.length === combinedRows.length) {
      setSelectedWorkerIds([]);
    } else {
      setSelectedWorkerIds(combinedRows.map((row) => row.worker.id));
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
    if (!payrollRunId || selectedWorkerIds.length === 0) return;
    if (!window.confirm(`Voulez-vous vraiment reinitialiser les HS/HM/Absences pour les ${selectedWorkerIds.length} salaries selectionnes ?`)) {
      return;
    }
    setLoading(true);
    try {
      await resetBulkHsHm(payrollRunId, selectedWorkerIds);
      setSelectedWorkerIds([]);
      await loadData();
    } catch {
      alert("Erreur lors de la reinitialisation en masse.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="mx-auto flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 p-6">
            <div>
              <Dialog.Title className="text-xl font-bold text-gray-900">
                Gérer HS/HM & Absences
              </Dialog.Title>
              <p className="mt-1 text-sm text-gray-500">
                Les données affichées utilisent {employerLabel || "l'employeur actif de la page paie"} pour la période {period}.
              </p>
            </div>
            <button onClick={onClose} className="rounded-full p-2 transition hover:bg-gray-200">
              <XMarkIcon className="h-6 w-6 text-gray-500" />
            </button>
          </div>

          {combinedRows.length > 0 && (
            <div className="flex items-center justify-between border-b border-gray-200 bg-gray-100 px-6 py-2">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">{selectedWorkerIds.length} selectionne(s)</span>
              </div>
              {selectedWorkerIds.length > 0 && (
                <button
                  onClick={handleBulkReset}
                  className="flex items-center gap-1 rounded border border-red-200 bg-red-50 px-3 py-1 text-sm text-red-600 hover:bg-red-100"
                >
                  <TrashIcon className="h-4 w-4" />
                  Reinitialiser la selection
                </button>
              )}
            </div>
          )}

          <div className="flex-1 overflow-auto p-6">
            {loading && combinedRows.length === 0 ? (
              <div className="flex justify-center py-10">
                <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-blue-500"></div>
              </div>
            ) : combinedRows.length === 0 ? (
              <div className="py-10 text-center text-gray-500">
                Aucun salarié trouvé pour cet employeur.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="w-10 px-3 py-3">
                      <input
                        type="checkbox"
                        checked={combinedRows.length > 0 && selectedWorkerIds.length === combinedRows.length}
                        onChange={toggleSelectAll}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
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
                    <th className="border-l border-gray-200 px-2 py-3 text-center font-medium text-gray-500">Ab. Mal J</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Ab. Mal H</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Ab. NR J</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Ab. NR H</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Mise Pied</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 1 J</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 1 H</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 2 J</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Autre 2 H</th>
                    <th className="min-w-[120px] border-l border-gray-200 px-4 py-3 text-center font-medium text-gray-500">Avance</th>
                    <th className="border-l border-gray-200 px-2 py-3 text-center font-medium text-gray-500">Ded 1</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Ded 2</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Ded 3</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Ded 4</th>
                    <th className="border-l border-gray-200 px-2 py-3 text-center font-medium text-gray-500">Av. Veh</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Av. Log</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Av. Tel</th>
                    <th className="px-2 py-3 text-center font-medium text-gray-500">Av. Aut</th>
                    <th className="min-w-[100px] px-3 py-3 text-right font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {combinedRows.map((row) => {
                    const isEditing = editingWorkerId === row.worker.id;
                    const displayData = isEditing && editForm ? editForm : row.entry;
                    const hasData = row.entry.id !== null;

                    return (
                      <tr key={row.worker.id} className={isEditing ? "bg-blue-50" : "hover:bg-gray-50"}>
                        <td className="px-3 py-3 text-center">
                          <input
                            type="checkbox"
                            checked={selectedWorkerIds.includes(row.worker.id)}
                            onChange={() => toggleSelection(row.worker.id)}
                            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-3 py-3 font-medium text-gray-900">{row.worker.matricule}</td>
                        <td className="px-3 py-3 text-gray-500">{row.worker.nom} {row.worker.prenom}</td>

                        {editableFields.map((field) => (
                          <td key={field} className="px-2 py-3 text-center">
                            {isEditing ? (
                              <input
                                type="number"
                                step={field === "avance" ? "100" : "0.5"}
                                min="0"
                                value={displayData[field] as number}
                                onChange={(event) => handleChange(field, event.target.value)}
                                className={`${field === "avance" ? "w-24" : "w-16"} rounded border border-blue-300 p-1 text-center outline-none focus:ring-2 focus:ring-blue-500`}
                              />
                            ) : (
                              <span className={Number(displayData[field] ?? 0) > 0 ? "font-bold text-gray-900" : "text-gray-300"}>
                                {Number(displayData[field] ?? 0) > 0 ? Number(displayData[field] ?? 0) : "-"}
                              </span>
                            )}
                          </td>
                        ))}

                        <td className="whitespace-nowrap px-3 py-3 text-right">
                          {isEditing ? (
                            <div className="flex items-center justify-end gap-2">
                              <button onClick={handleSave} className="rounded p-1 text-green-600 hover:bg-green-100" title="Sauvegarder">
                                <CheckIcon className="h-5 w-5" />
                              </button>
                              <button onClick={handleCancelEdit} className="rounded p-1 text-gray-400 hover:bg-gray-100" title="Annuler">
                                <XMarkIcon className="h-5 w-5" />
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleEdit(row)}
                                className="rounded p-1 text-blue-600 hover:bg-blue-100"
                                title={hasData ? "Modifier" : "Ajouter des HS"}
                              >
                                <PencilIcon className="h-4 w-4" />
                              </button>
                              {hasData && (
                                <button
                                  onClick={() => handleDelete(row.worker.id)}
                                  className="rounded p-1 text-red-600 hover:bg-red-100"
                                  title="Supprimer"
                                >
                                  <TrashIcon className="h-4 w-4" />
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
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default HsHmManagerModal;
