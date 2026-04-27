import React, { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, createPrime, deletePrime, getPrimes, getWorkers, updatePrime } from "../api";
import type { Prime } from "../api";

const formulaVariables = ["SALDBASE", "SALHORAI", "SALJOURN", "ANCIENAN", "NOMBRENF", "DAYSWORK", "SME"];

const fieldInputClass =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white p-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20";

type WorkerOption = {
  id: number;
  matricule: string;
  nom: string;
  prenom: string;
};

type UnitOption = {
  id: number;
  name: string;
  level: string;
  path: string;
  depth: number;
};

type HierarchyNode = {
  id: number;
  name: string;
  level: string;
  path?: string;
  children?: HierarchyNode[];
};

const targetModeLabels: Record<Prime["target_mode"], string> = {
  global: "Globale - tous les salaries",
  segment: "Segmentee - structure organisationnelle",
  individual: "Individuelle - salaries selectionnes",
};

const levelLabels: Record<string, string> = {
  etablissement: "Etablissement",
  departement: "Departement",
  service: "Service",
  unite: "Unite",
};

const emptyPrime = (): Partial<Prime> => ({
  target_mode: "global",
  target_worker_ids: [],
  excluded_worker_ids: [],
  target_organizational_node_ids: [],
  target_organizational_unit_ids: [],
  is_active: true,
  is_cotisable: true,
  is_imposable: true,
  operation_1: "*",
  operation_2: "*",
});

const PrimesManagement: React.FC = () => {
  const { employerId } = useParams<{ employerId: string }>();

  const [primes, setPrimes] = useState<Prime[]>([]);
  const [workers, setWorkers] = useState<WorkerOption[]>([]);
  const [units, setUnits] = useState<UnitOption[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPrime, setEditingPrime] = useState<Partial<Prime>>(emptyPrime());
  const [activeField, setActiveField] = useState<string | null>(null);

  const fetchPrimes = useCallback(async (): Promise<Prime[]> => {
    if (!employerId) return [];
    try {
      const data = await getPrimes(parseInt(employerId, 10));
      setPrimes(data);
      return data;
    } catch (error) {
      console.error("Failed to fetch primes", error);
      return [];
    }
  }, [employerId]);

  const fetchTargetOptions = useCallback(async (): Promise<UnitOption[]> => {
    if (!employerId) return [];
    try {
      const [workerRows, unitResponse] = await Promise.all([
        getWorkers(parseInt(employerId, 10)),
        api.get(`/organization/employers/${employerId}/tree`, { params: { _: Date.now() } }),
      ]);
      setWorkers(workerRows);
      const flattenNodes = (nodes: HierarchyNode[], acc: UnitOption[] = [], depth = 0, parentPath = ""): UnitOption[] => {
        nodes.forEach((node) => {
          const path = node.path || (parentPath ? `${parentPath} > ${node.name}` : node.name);
          acc.push({ id: node.id, name: node.name, level: node.level, path, depth });
          if (node.children?.length) flattenNodes(node.children, acc, depth + 1, path);
        });
        return acc;
      };
      const flattenedUnits = flattenNodes(unitResponse.data?.root_units || unitResponse.data?.tree || []);
      setUnits(flattenedUnits);
      return flattenedUnits;
    } catch (error) {
      console.error("Failed to fetch targeting options", error);
      return [];
    }
  }, [employerId]);

  useEffect(() => {
    if (!employerId) return;
    const loadInitialData = async () => {
      await Promise.all([fetchPrimes(), fetchTargetOptions()]);
    };
    void loadInitialData();
  }, [employerId, fetchPrimes, fetchTargetOptions]);

  const normalizePrime = (prime: Partial<Prime>): Partial<Prime> => ({
    ...emptyPrime(),
    ...prime,
    target_mode: prime.target_mode || "global",
    target_worker_ids: prime.target_worker_ids || [],
    excluded_worker_ids: prime.excluded_worker_ids || [],
    target_organizational_node_ids: prime.target_organizational_node_ids || [],
    target_organizational_unit_ids: prime.target_organizational_unit_ids || [],
  });

  const normalizePrimeForUnits = (prime: Partial<Prime>, availableUnits: UnitOption[]): Partial<Prime> => {
    const normalizedPrime = normalizePrime(prime);
    if (normalizedPrime.target_mode !== "segment") {
      return normalizedPrime;
    }
    const validNodeIds = new Set(availableUnits.map((unit) => unit.id));
    return {
      ...normalizedPrime,
      target_organizational_unit_ids: ((normalizedPrime.target_organizational_unit_ids as number[] | undefined) || []).filter((unitId) => validNodeIds.has(unitId)),
      target_organizational_node_ids: [],
    };
  };

  const refreshTargetOptionsForEditingPrime = async () => {
    const latestUnits = await fetchTargetOptions();
    setEditingPrime((prev) => normalizePrimeForUnits(prev, latestUnits));
  };

  const handleSave = async () => {
    if (!employerId) return;
    const normalizedPrime = normalizePrime(editingPrime);
    const targetMode = normalizedPrime.target_mode || "global";
    const availableUnits = targetMode === "segment" ? await fetchTargetOptions() : units;
    const validUnitIds = new Set(availableUnits.map((unit) => unit.id));
    const rawSelectedUnitIds = (normalizedPrime.target_organizational_unit_ids as number[] | undefined) || [];
    const selectedUnitIds = rawSelectedUnitIds.filter((unitId) => validUnitIds.has(unitId));

    if (targetMode === "segment" && !selectedUnitIds.length) {
      setEditingPrime(normalizePrimeForUnits(normalizedPrime, availableUnits));
      alert("Veuillez selectionner au moins un segment de la hierarchie organisationnelle.");
      return;
    }
    if (targetMode === "individual" && !((normalizedPrime.target_worker_ids as number[] | undefined) || []).length) {
      alert("Veuillez selectionner au moins un salarie beneficiaire.");
      return;
    }

    try {
      const payload = {
        ...normalizedPrime,
        employer_id: parseInt(employerId, 10),
        target_organizational_node_ids: [],
        target_organizational_unit_ids: targetMode === "segment" ? selectedUnitIds : [],
        target_worker_ids: targetMode === "individual" ? normalizedPrime.target_worker_ids || [] : [],
        excluded_worker_ids: targetMode === "global" ? normalizedPrime.excluded_worker_ids || [] : [],
      };
      if (editingPrime.id) {
        await updatePrime(editingPrime.id, payload);
      } else {
        await createPrime(payload);
      }
      setIsModalOpen(false);
      setEditingPrime(emptyPrime());
      setActiveField(null);
      await fetchPrimes();
    } catch (error: unknown) {
      const message =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Erreur lors de l'enregistrement";
      alert(message);
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm("Supprimer cette prime ? Les salaries affectes perdront cette configuration.")) {
      try {
        await deletePrime(id);
        await fetchPrimes();
      } catch {
        alert("Erreur suppression");
      }
    }
  };

  const openCreateModal = async () => {
    await fetchTargetOptions();
    setEditingPrime(emptyPrime());
    setActiveField(null);
    setIsModalOpen(true);
  };

  const openEditModal = async (prime: Prime) => {
    const [latestUnits, latestPrimes] = await Promise.all([fetchTargetOptions(), fetchPrimes()]);
    const latestPrime = latestPrimes.find((item) => item.id === prime.id) || prime;
    setEditingPrime(normalizePrimeForUnits(latestPrime, latestUnits));
    setActiveField(null);
    setIsModalOpen(true);
  };

  const insertVariable = (variable: string) => {
    if (!activeField) {
      alert("Veuillez cliquer d'abord dans un champ de formule (Nombre, Base ou Taux).");
      return;
    }

    setEditingPrime((prev) => ({
      ...prev,
      [activeField]: `${String(prev[activeField as keyof Prime] ?? "")}${variable}`,
    }));
  };

  const toggleSelection = (
    field: "target_worker_ids" | "excluded_worker_ids" | "target_organizational_unit_ids",
    value: number
  ) => {
    const currentValues = (editingPrime[field] as number[] | undefined) || [];
    const nextValues = currentValues.includes(value)
      ? currentValues.filter((item) => item !== value)
      : [...currentValues, value];
    setEditingPrime((prev) => ({ ...prev, [field]: nextValues }));
  };

  const getTargetSummary = (prime: Prime) => {
    if (prime.target_mode === "global") {
      return prime.excluded_worker_ids.length > 0
        ? `Tous sauf ${prime.excluded_worker_ids.length} exclusion(s)`
        : "Tous les salaries";
    }
    if (prime.target_mode === "segment") {
      const selectedUnitIds = prime.target_organizational_unit_ids || [];
      const names = selectedUnitIds
        .map((unitId) => units.find((unit) => unit.id === unitId))
        .filter(Boolean)
        .map((unit) => `${unit?.name} (${levelLabels[unit?.level || ""] || unit?.level})`);
      return names.length ? `Segmentee: ${names.slice(0, 3).join(", ")}${names.length > 3 ? ` +${names.length - 3}` : ""}` : `${selectedUnitIds.length} segment(s)`;
    }
    return `${prime.target_worker_ids.length} salarie(s)`;
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-100">Gestion des Primes</h1>
        <button
          onClick={() => void openCreateModal()}
          className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white shadow-sm transition-colors hover:bg-blue-700"
        >
          + Nouvelle Prime
        </button>
      </div>

      <div className="rounded-2xl bg-white p-4 text-slate-900 shadow-xl shadow-slate-950/10 ring-1 ring-slate-200">
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-100/90">
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">Libelle</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">Formule</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">Cible</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">Active</th>
              <th className="px-4 py-3 text-right text-sm font-semibold text-slate-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {primes
              .sort((a, b) => a.label.localeCompare(b.label))
              .map((prime) => (
                <tr key={prime.id} className="border-b border-slate-200 transition-colors hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold text-slate-900">{prime.label}</td>
                  <td className="px-4 py-3 text-sm font-medium text-slate-600">
                    {(prime.formula_nombre || "0")} {prime.operation_1} {(prime.formula_base || "0")} {prime.operation_2} {(prime.formula_taux || "0")}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-slate-600">{getTargetSummary(prime)}</td>
                  <td className="px-4 py-3">
                    {prime.is_active ? (
                      <span className="font-semibold text-emerald-600">Oui</span>
                    ) : (
                      <span className="font-semibold text-red-500">Non</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <button
                      onClick={() => void openEditModal(prime)}
                      className="font-semibold text-blue-600 transition-colors hover:text-blue-700 hover:underline"
                    >
                      Modifier
                    </button>
                    <button
                      onClick={() => handleDelete(prime.id)}
                      className="font-semibold text-red-600 transition-colors hover:text-red-700 hover:underline"
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            {primes.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-sm font-medium text-slate-500">
                  Aucune prime definie.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-2xl bg-white p-6 text-slate-900 shadow-2xl shadow-slate-950/30 ring-1 ring-slate-200">
            <h2 className="mb-4 text-xl font-bold text-slate-900">{editingPrime.id ? "Modifier Prime" : "Nouvelle Prime"}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700">Libelle</label>
                <input
                  type="text"
                  className={fieldInputClass}
                  value={editingPrime.label || ""}
                  onChange={(e) => setEditingPrime({ ...editingPrime, label: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-slate-500">Formule Nombre</label>
                  <input
                    type="text"
                    placeholder="ex: 1, ANCIENAN..."
                    className={fieldInputClass}
                    value={editingPrime.formula_nombre || ""}
                    onChange={(e) => setEditingPrime({ ...editingPrime, formula_nombre: e.target.value })}
                    onFocus={() => setActiveField("formula_nombre")}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-slate-500">Operateur 1</label>
                  <select
                    className={fieldInputClass}
                    value={editingPrime.operation_1 || "*"}
                    onChange={(e) => setEditingPrime({ ...editingPrime, operation_1: e.target.value })}
                  >
                    <option value="*">*</option>
                    <option value="/">/</option>
                    <option value="+">+</option>
                    <option value="-">-</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-slate-500">Formule Base</label>
                  <input
                    type="text"
                    placeholder="ex: SALDBASE, 5000..."
                    className={fieldInputClass}
                    value={editingPrime.formula_base || ""}
                    onChange={(e) => setEditingPrime({ ...editingPrime, formula_base: e.target.value })}
                    onFocus={() => setActiveField("formula_base")}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-slate-500">Operateur 2</label>
                  <select
                    className={fieldInputClass}
                    value={editingPrime.operation_2 || "*"}
                    onChange={(e) => setEditingPrime({ ...editingPrime, operation_2: e.target.value })}
                  >
                    <option value="*">*</option>
                    <option value="/">/</option>
                    <option value="+">+</option>
                    <option value="-">-</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-slate-500">Formule Taux</label>
                  <input
                    type="text"
                    placeholder="ex: 100, 5..."
                    className={fieldInputClass}
                    value={editingPrime.formula_taux || ""}
                    onChange={(e) => setEditingPrime({ ...editingPrime, formula_taux: e.target.value })}
                    onFocus={() => setActiveField("formula_taux")}
                  />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={editingPrime.is_active !== false}
                    onChange={(e) => setEditingPrime({ ...editingPrime, is_active: e.target.checked })}
                  />
                  Active
                </label>
              </div>

              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700">Cible de la prime</label>
                  <select
                    className={fieldInputClass}
                    value={editingPrime.target_mode || "global"}
                    onChange={(e) => {
                      const nextTargetMode = e.target.value as Prime["target_mode"];
                      if (nextTargetMode === "segment") {
                        void refreshTargetOptionsForEditingPrime();
                      }
                      setEditingPrime({
                        ...editingPrime,
                        target_mode: nextTargetMode,
                        target_worker_ids: nextTargetMode === "individual" ? editingPrime.target_worker_ids || [] : [],
                        excluded_worker_ids: nextTargetMode === "global" ? editingPrime.excluded_worker_ids || [] : [],
                        target_organizational_node_ids: [],
                        target_organizational_unit_ids:
                          nextTargetMode === "segment" ? editingPrime.target_organizational_unit_ids || [] : [],
                      });
                    }}
                  >
                    <option value="global">{targetModeLabels.global}</option>
                    <option value="segment">{targetModeLabels.segment}</option>
                    <option value="individual">{targetModeLabels.individual}</option>
                  </select>
                  <p className="mt-2 text-xs leading-relaxed text-slate-500">
                    Le mode Segmentee applique la prime aux salaries rattaches a une unite de la page Organisation, ainsi qu'a ses niveaux enfants si leur affectation remonte a cette unite.
                  </p>
                </div>

                {editingPrime.target_mode === "segment" && (
                  <div>
                    <div className="flex items-center justify-between gap-3">
                      <label className="block text-sm font-semibold text-slate-700">Structure Organisationnelle cible</label>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => void refreshTargetOptionsForEditingPrime()}
                          className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-blue-700 transition-colors hover:bg-blue-50"
                        >
                          Rafraichir la structure
                        </button>
                        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                          {((editingPrime.target_organizational_unit_ids as number[] | undefined) || []).length} segment(s)
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 max-h-64 space-y-1 overflow-auto rounded-lg border border-slate-200 bg-white p-3">
                      {units.map((unit) => (
                        <label key={unit.id} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-700 transition-colors hover:bg-blue-50" style={{ paddingLeft: `${8 + unit.depth * 18}px` }}>
                          <input
                            type="checkbox"
                            checked={((editingPrime.target_organizational_unit_ids as number[] | undefined) || []).includes(unit.id)}
                            onChange={() => toggleSelection("target_organizational_unit_ids", unit.id)}
                          />
                          <span className="font-medium">{unit.name}</span>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-500">{levelLabels[unit.level] || unit.level}</span>
                          <span className="truncate text-xs text-slate-400">{unit.path}</span>
                        </label>
                      ))}
                      {units.length === 0 && (
                        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                          Aucune structure organisationnelle n'est disponible pour cet employeur. Creez d'abord la structure dans la page Organisation.
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {editingPrime.target_mode === "individual" && (
                  <div>
                    <label className="block text-sm font-semibold text-slate-700">Salaries beneficiaires</label>
                    <div className="mt-2 max-h-44 space-y-2 overflow-auto rounded-lg border border-slate-200 bg-white p-3">
                      {workers.map((worker) => (
                        <label key={worker.id} className="flex items-center gap-2 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={((editingPrime.target_worker_ids as number[] | undefined) || []).includes(worker.id)}
                            onChange={() => toggleSelection("target_worker_ids", worker.id)}
                          />
                          <span>{worker.matricule} - {worker.nom} {worker.prenom}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {editingPrime.target_mode === "global" && (
                  <div>
                    <label className="block text-sm font-semibold text-slate-700">Exclusions individuelles</label>
                    <div className="mt-2 max-h-44 space-y-2 overflow-auto rounded-lg border border-slate-200 bg-white p-3">
                      {workers.map((worker) => (
                        <label key={worker.id} className="flex items-center gap-2 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={((editingPrime.excluded_worker_ids as number[] | undefined) || []).includes(worker.id)}
                            onChange={() => toggleSelection("excluded_worker_ids", worker.id)}
                          />
                          <span>{worker.matricule} - {worker.nom} {worker.prenom}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="rounded-xl bg-blue-50 p-3 text-xs text-blue-900 ring-1 ring-blue-100">
                <div className="mb-2 font-bold">Variables disponibles (cliquez pour inserer) :</div>
                <div className="flex flex-wrap gap-2">
                  {formulaVariables.map((variable) => (
                    <button
                      key={variable}
                      type="button"
                      onClick={() => insertVariable(variable)}
                      className="rounded-md border border-blue-200 bg-white px-2 py-1 font-semibold text-blue-700 transition-colors hover:bg-blue-100"
                    >
                      {variable}
                    </button>
                  ))}
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-blue-800">
                  `DAYSWORK` est deja activee dans le moteur de paie. Elle correspond au nombre de jours marques comme
                  travailles dans le calendrier employeur pour la periode du bulletin.
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg px-4 py-2 font-semibold text-slate-600 transition-colors hover:bg-slate-100"
              >
                Annuler
              </button>
              <button
                onClick={handleSave}
                className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white shadow-sm transition-colors hover:bg-blue-700"
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrimesManagement;
