import React, { useCallback, useEffect, useState } from "react";
import {
  api,
  downloadAbsencesTemplate,
  importAbsencesFile,
  type TabularImportReport,
} from "../api";
import WorkerSearchSelect from "../components/WorkerSearchSelect";
import { useTheme } from "../contexts/ThemeContext";
import { useWorkerData } from "../hooks/useConstants";

type AbsenceInput = {
  worker_id: number;           // ID du salarié
  salaire_base: number;
  salaire_horaire: number;
  ABSM_J: number;
  ABSM_H: number;
  ABSNR_J: number;
  ABSNR_H: number;
  ABSMP: number;
  ABS1_J: number;
  ABS1_H: number;
  ABS2_J: number;
  ABS2_H: number;
};

type AbsenceRubriqueResult = {
  code: string;
  label: string;
  unite: "jour" | "heure";
  nombre: number;
  base: number;
  montant_salarial: number;
};

type AbsenceCalculationResult = {
  salaire_journalier: number;
  salaire_horaire: number;
  rubriques: AbsenceRubriqueResult[];
  total_retenues_absence: number;
};

type AbsenceHistoryItem = {
  id: number;
  worker_id: number;
  employer_id?: number | null;
  worker_matricule?: string | null;
  worker_nom?: string | null;
  worker_prenom?: string | null;
  mois: string;
  ABSM_J: number;
  ABSM_H: number;
  ABSNR_J: number;
  ABSNR_H: number;
  ABSMP: number;
  ABS1_J: number;
  ABS1_H: number;
  ABS2_J: number;
  ABS2_H: number;
};

// 🔹 Adapté exactement à ton JSON /workers/{id}
type Worker = {
  id: number;
  employer_id: number;
  matricule: string;
  nom: string;
  prenom: string;
  adresse: string;
  nombre_enfant: number;
  type_regime_id: number;
  salaire_base: number;
  salaire_horaire: number;
  vhm: number;
  horaire_hebdo: number;
};

type Employer = {
  id: number;
  raison_sociale: string;
};

const initialForm: AbsenceInput = {
  worker_id: 0,
  salaire_base: 0,
  salaire_horaire: 0,
  ABSM_J: 0,
  ABSM_H: 0,
  ABSNR_J: 0,
  ABSNR_H: 0,
  ABSMP: 0,
  ABS1_J: 0,
  ABS1_H: 0,
  ABS2_J: 0,
  ABS2_H: 0,
};

const ABSENCE_VALUE_FIELDS: Array<keyof Pick<
  AbsenceInput,
  "ABSM_J" | "ABSM_H" | "ABSNR_J" | "ABSNR_H" | "ABSMP" | "ABS1_J" | "ABS1_H" | "ABS2_J" | "ABS2_H"
>> = ["ABSM_J", "ABSM_H", "ABSNR_J", "ABSNR_H", "ABSMP", "ABS1_J", "ABS1_H", "ABS2_J", "ABS2_H"];

const Absences: React.FC = () => {
  const { theme } = useTheme();
  const currentMonth = new Date().toISOString().slice(0, 7);
  const [form, setForm] = useState<AbsenceInput>(initialForm);
  const [absenceMois, setAbsenceMois] = useState<string>(currentMonth);
  const [result, setResult] = useState<AbsenceCalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [worker, setWorker] = useState<Worker | null>(null);
  const [workerLoading, setWorkerLoading] = useState(false);
  const [workerError, setWorkerError] = useState<string | null>(null);
  const [history, setHistory] = useState<AbsenceHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyMonthFilter, setHistoryMonthFilter] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"new" | "history">("new");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importUpdateExisting, setImportUpdateExisting] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importReport, setImportReport] = useState<TabularImportReport | null>(null);
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const { data: workerData } = useWorkerData(form.worker_id || 0);
  const pageClass = theme === "light" ? "siirh-page min-h-screen py-8 px-4" : "siirh-page min-h-screen py-8 px-4 text-slate-100";
  const cardClass = theme === "light" ? "siirh-panel" : "siirh-panel bg-slate-900";
  const titleClass = theme === "light" ? "text-gray-900" : "text-slate-100";
  const mutedTextClass = theme === "light" ? "text-gray-500" : "text-slate-400";
  const inputClass = theme === "light"
    ? "siirh-input"
    : "siirh-input bg-slate-800 text-slate-100";
  const secondaryButtonClass = theme === "light"
    ? "siirh-btn-secondary"
    : "siirh-btn-secondary border-slate-600 bg-slate-900 text-slate-200 hover:bg-slate-800";

  const resetAbsenceValues = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      ABSM_J: 0,
      ABSM_H: 0,
      ABSNR_J: 0,
      ABSNR_H: 0,
      ABSMP: 0,
      ABS1_J: 0,
      ABS1_H: 0,
      ABS2_J: 0,
      ABS2_H: 0,
    }));
  }, []);

  const applyHistoryToForm = useCallback((item: AbsenceHistoryItem) => {
    setForm((prev) => ({
      ...prev,
      worker_id: item.worker_id,
      ABSM_J: item.ABSM_J ?? 0,
      ABSM_H: item.ABSM_H ?? 0,
      ABSNR_J: item.ABSNR_J ?? 0,
      ABSNR_H: item.ABSNR_H ?? 0,
      ABSMP: item.ABSMP ?? 0,
      ABS1_J: item.ABS1_J ?? 0,
      ABS1_H: item.ABS1_H ?? 0,
      ABS2_J: item.ABS2_J ?? 0,
      ABS2_H: item.ABS2_H ?? 0,
    }));
    setAbsenceMois(item.mois || currentMonth);
  }, [currentMonth]);

  useEffect(() => {
    let cancelled = false;
    const loadEmployers = async () => {
      try {
        const response = await api.get<Employer[]>("/employers");
        if (cancelled) return;
        setEmployers(response.data);
        setSelectedEmployerId((current) => current ?? response.data[0]?.id ?? null);
      } catch (err) {
        console.error(err);
      }
    };
    void loadEmployers();
    return () => {
      cancelled = true;
    };
  }, []);

  // 🔹 Quand on modifie un input numérique (y compris worker_id)
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value === "" ? 0 : Number(value),
    }));
  };

  // 🔹 Récupérer les infos d'un salarié à partir du worker_id
  const fetchWorker = async (id: number) => {
    if (!id || id <= 0) return;
    setWorkerLoading(true);
    setWorkerError(null);

    try {
      const response = await api.get<Worker>(`/workers/${id}`);
      const data = response.data;
      setWorker(data);

      // Pré-remplissage salaire_base et salaire_horaire si dispo
      setForm((prev) => ({
        ...prev,
        salaire_base: data.salaire_base ?? prev.salaire_base,
        salaire_horaire: data.salaire_horaire ?? prev.salaire_horaire,
      }));
      setSelectedEmployerId(data.employer_id ?? null);
    } catch (err) {
      console.error(err);
      setWorker(null);
      setWorkerError("Impossible de récupérer le salarié (vérifie l'ID).");
    } finally {
      setWorkerLoading(false);
    }
  };

  const loadHistory = useCallback(async () => {
    try {
      setHistoryLoading(true);
      setHistoryError(null);
      const params: Record<string, string | number> = {};
      if (selectedEmployerId) params.employer_id = selectedEmployerId;
      if (activeTab !== "history" && form.worker_id > 0) params.worker_id = form.worker_id;
      if (historyMonthFilter) params.mois = historyMonthFilter;
      const response = await api.get<AbsenceHistoryItem[]>("/absences/all", { params });
      setHistory(response.data);
      return response.data;
    } catch (err) {
      console.error(err);
      setHistoryError("Impossible de charger l'historique des absences.");
      return [];
    } finally {
      setHistoryLoading(false);
    }
  }, [activeTab, form.worker_id, historyMonthFilter, selectedEmployerId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleDownloadTemplate = async (prefilled: boolean) => {
    try {
      await downloadAbsencesTemplate({
        employerId: selectedEmployerId ?? worker?.employer_id,
        prefilled,
        format: "xlsx",
      });
    } catch (err) {
      console.error(err);
      setImportError("Impossible de telecharger le modele d'absences.");
    }
  };

  const handleImportAbsences = async () => {
    if (!importFile) {
      setImportError("Selectionnez un fichier a importer.");
      return;
    }
    setIsImporting(true);
    setImportError(null);
    setImportReport(null);
    try {
      const report = await importAbsencesFile(importFile, {
        updateExisting: importUpdateExisting,
      });
      setImportReport(report);
      const updatedHistory = await loadHistory();
      if (form.worker_id > 0) {
        const currentWorkerItem = updatedHistory.find((item) => item.worker_id === form.worker_id);
        if (currentWorkerItem) {
          applyHistoryToForm(currentWorkerItem);
        } else {
          const latestWorkerItem = await loadWorkerLatestAbsence(form.worker_id, absenceMois);
          if (latestWorkerItem) {
            applyHistoryToForm(latestWorkerItem);
          }
        }
      }
    } catch (err: unknown) {
      console.error(err);
      const apiDetail =
        typeof err === "object" &&
        err !== null &&
        "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      const message = typeof apiDetail === "string" ? apiDetail : "Erreur lors de l'import des absences.";
      setImportError(message);
    } finally {
      setIsImporting(false);
    }
  };


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await api.post<AbsenceCalculationResult>("/absences/calcul", form);
      setResult(response.data);
      await api.post("/absences/calculate-and-save", form, {
        params: { mois: absenceMois },
      });
      await loadHistory();
    } catch (err) {
      console.error(err);
      setError("Erreur lors du calcul des absences.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setForm(initialForm);
    setAbsenceMois(currentMonth);
    setResult(null);
    setError(null);
    setWorker(null);
    setWorkerError(null);
  };

  const loadWorkerLatestAbsence = useCallback(async (workerId: number, preferredMonth?: string) => {
    if (!workerId || workerId <= 0) {
      return null;
    }
    const response = await api.get<AbsenceHistoryItem[]>("/absences/all", {
      params: { worker_id: workerId },
    });
    const allRows = response.data;
    if (!allRows.length) {
      return null;
    }
    if (preferredMonth) {
      const exactMatch = allRows.find((item) => item.mois === preferredMonth);
      if (exactMatch) {
        return exactMatch;
      }
    }
    return allRows[0];
  }, []);

  const handleEmployerChange = async (nextEmployerId: number | null) => {
    setSelectedEmployerId(nextEmployerId);
    setImportError(null);
    if (!nextEmployerId) {
      setForm((prev) => ({ ...prev, worker_id: 0 }));
      setWorker(null);
      resetAbsenceValues();
      return;
    }
    if (worker?.employer_id && worker.employer_id !== nextEmployerId) {
      setForm((prev) => ({ ...prev, worker_id: 0 }));
      setWorker(null);
      resetAbsenceValues();
    }
  };

  const handleWorkerSelect = useCallback(async (workerId: number) => {
    setForm((prev) => ({ ...prev, worker_id: workerId }));
    setResult(null);

    if (!workerId || workerId <= 0) {
      setWorker(null);
      resetAbsenceValues();
      return;
    }

    await fetchWorker(workerId);
    try {
      const item = await loadWorkerLatestAbsence(workerId, absenceMois);
      if (item) {
        applyHistoryToForm(item);
      } else {
        setForm((prev) => ({
          ...prev,
          worker_id: workerId,
          ...Object.fromEntries(ABSENCE_VALUE_FIELDS.map((field) => [field, 0])),
        }));
      }
    } catch (err) {
      console.error(err);
      resetAbsenceValues();
    }
  }, [absenceMois, applyHistoryToForm, loadWorkerLatestAbsence, resetAbsenceValues, worker?.employer_id]);

  const displayWorker = worker
    ? {
        ...worker,
        nom: workerData?.nom || worker.nom,
        prenom: workerData?.prenom || worker.prenom,
        matricule: workerData?.matricule || worker.matricule,
        adresse: workerData?.adresse || worker.adresse,
        salaire_base: typeof workerData?.salaire_base === "number" ? workerData.salaire_base : worker.salaire_base,
        salaire_horaire: typeof workerData?.salaire_horaire === "number" ? workerData.salaire_horaire : worker.salaire_horaire,
        horaire_hebdo: typeof workerData?.horaire_hebdo === "number" ? workerData.horaire_hebdo : worker.horaire_hebdo,
      }
    : null;

  const handleDeleteHistory = async (absenceId: number) => {
    const ok = window.confirm(`Supprimer l'enregistrement d'absence #${absenceId} ?`);
    if (!ok) return;
    try {
      await api.delete(`/absences/${absenceId}`);
      setHistory((prev) => prev.filter((item) => item.id !== absenceId));
    } catch (err) {
      console.error(err);
      alert("Erreur lors de la suppression.");
    }
  };

  const formatHistoryWorker = (item: AbsenceHistoryItem) => {
    const fullName = `${item.worker_prenom ?? ""} ${item.worker_nom ?? ""}`.trim();
    if (item.worker_matricule && fullName) {
      return `${item.worker_matricule} - ${fullName}`;
    }
    if (fullName) {
      return fullName;
    }
    return item.worker_matricule || String(item.worker_id);
  };

  // Groupes de champs pour une meilleure organisation
  const fieldGroups = [
    {
      title: "Salarié",
      description: "Identification du salarié concerné par ces absences",
      fields: [
        {
          name: "worker_id",
          label: "ID du salarié (worker_id)",
          type: "number",
        },
      ],
    },
    {
      title: "Salaire de base",
      description: "Informations de rémunération de base",
      fields: [
        {
          name: "salaire_base",
          label: "Salaire de base mensuel (Ar)",
          type: "number",
        },
        {
          name: "salaire_horaire",
          label: "Salaire horaire (Ar)",
          type: "number",
        },
      ],
    },
    {
      title: "Absence maladie (informatif)",
      description: "Absences pour maladie (pas de retenue, info bulletin)",
      fields: [
        { name: "ABSM_J", label: "Jours d'absence maladie", type: "number" },
        { name: "ABSM_H", label: "Heures d'absence maladie", type: "number" },
      ],
    },
    {
      title: "Absence non rémunérée",
      description: "Absences non prises en charge (retenues en paie)",
      fields: [
        { name: "ABSNR_J", label: "Jours non rémunérés", type: "number" },
        { name: "ABSNR_H", label: "Heures non rémunérées", type: "number" },
      ],
    },
    {
      title: "Mise à pied & autres absences",
      description: "Autres types d'absences",
      fields: [
        { name: "ABSMP", label: "Jours de mise à pied", type: "number" },
        { name: "ABS1_J", label: "Autre absence 1 (jours)", type: "number" },
        { name: "ABS1_H", label: "Autre absence 1 (heures)", type: "number" },
        { name: "ABS2_J", label: "Autre absence 2 (jours)", type: "number" },
        { name: "ABS2_H", label: "Autre absence 2 (heures)", type: "number" },
      ],
    },
  ];

  return (
    <div className={pageClass}>
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className={`text-3xl font-bold mb-3 ${titleClass}`}>
            Calcul des Absences
          </h1>
          <p className={`${theme === "light" ? "text-gray-600" : "text-slate-300"} max-w-2xl mx-auto`}>
            Saisis l&apos;ID du salarié, récupère automatiquement ses infos, puis
            renseigne les absences pour calculer les retenues sur salaire.
          </p>
        </div>

        <div className="mb-8 flex justify-center">
          <div className={`inline-flex rounded-2xl p-1 shadow-sm ${theme === "light" ? "border border-gray-200 bg-white/80" : "border border-slate-700 bg-slate-900/90"}`}>
            <button
              type="button"
              onClick={() => setActiveTab("new")}
              className={`rounded-xl px-6 py-2.5 text-sm font-semibold transition ${
                activeTab === "new"
                  ? theme === "light" ? "bg-white text-blue-600 shadow-sm" : "bg-slate-800 text-cyan-300 shadow-sm"
                  : theme === "light" ? "text-gray-500 hover:text-gray-700" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Nouveau Calcul
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("history")}
              className={`rounded-xl px-6 py-2.5 text-sm font-semibold transition ${
                activeTab === "history"
                  ? theme === "light" ? "bg-white text-blue-600 shadow-sm" : "bg-slate-800 text-cyan-300 shadow-sm"
                  : theme === "light" ? "text-gray-500 hover:text-gray-700" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Historique
            </button>
          </div>
        </div>

        <div className={activeTab === "new" ? "" : "hidden"}>
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Les absences enregistrÃ©es ici sont reprises automatiquement par le moteur de paie sur la mÃªme pÃ©riode.
        </div>

        <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-blue-900">Import Absences (modèle Excel)</h2>
              <p className="text-xs text-blue-700">
                Choisissez l&apos;employeur, téléchargez le modèle puis importez le fichier rempli.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                value={selectedEmployerId ?? ""}
                onChange={(event) => {
                  void handleEmployerChange(event.target.value ? Number(event.target.value) : null);
                }}
                className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-xs font-medium text-blue-900"
              >
                <option value="">Choisir un employeur</option>
                {employers.map((employer) => (
                  <option key={`absence-employer-${employer.id}`} value={employer.id}>
                    {employer.raison_sociale}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => handleDownloadTemplate(true)}
                className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-100"
              >
                Télécharger modèle
              </button>
            </div>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
            <input
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm"
            />
            <label className="flex items-center gap-2 text-xs text-blue-800">
              <input
                type="checkbox"
                checked={importUpdateExisting}
                onChange={(event) => setImportUpdateExisting(event.target.checked)}
              />
              Mettre a jour l'existant
            </label>
            <button
              type="button"
              onClick={handleImportAbsences}
              disabled={!importFile || isImporting}
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {isImporting ? "Import..." : "Importer fichier"}
            </button>
          </div>

          {importError ? <p className="mt-2 text-xs text-red-700">{importError}</p> : null}

          {importReport ? (
            <div className="mt-3 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs text-blue-900">
              <div>
                Creees: {importReport.created} | Maj: {importReport.updated} | Ignorees: {importReport.skipped} | Echec: {importReport.failed}
              </div>
              {importReport.error_report_csv ? (
                <button
                  type="button"
                  onClick={() => {
                    const blob = new Blob([importReport.error_report_csv ?? ""], { type: "text/csv;charset=utf-8;" });
                    const url = URL.createObjectURL(blob);
                    const anchor = document.createElement("a");
                    anchor.href = url;
                    anchor.download = `absences_import_errors_${absenceMois}.csv`;
                    document.body.appendChild(anchor);
                    anchor.click();
                    document.body.removeChild(anchor);
                    URL.revokeObjectURL(url);
                  }}
                  className="mt-2 rounded border border-blue-200 px-3 py-1 text-xs text-blue-700 hover:bg-blue-50"
                >
                  Telecharger rapport erreurs (CSV)
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Formulaire */}
          <div className="lg:col-span-2">
            <form
              onSubmit={handleSubmit}
              className={cardClass}
            >
              <div className="mb-6">
                <label className={`block text-sm font-medium mb-2 ${theme === "light" ? "text-gray-700" : "text-slate-300"}`}>
                  Période de paie
                </label>
                <input
                  type="month"
                  value={absenceMois}
                  onChange={(e) => setAbsenceMois(e.target.value)}
                  className={`${inputClass} md:w-64`}
                />
              </div>

              {fieldGroups.map((group, groupIndex) => (
                <div
                  key={group.title}
                  className={groupIndex > 0 ? "mt-8" : ""}
                >
                  <div className="mb-4">
                    <h2 className={`text-lg font-semibold ${titleClass}`}>
                      {group.title}
                    </h2>
                    <p className={`text-sm ${mutedTextClass}`}>
                      {group.description}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {group.fields.map((field) => (
                      <div key={field.name}>
                        <label className={`block text-sm font-medium mb-2 ${theme === "light" ? "text-gray-700" : "text-slate-300"}`}>
                          {field.label}
                        </label>
                        {field.name === "worker_id" ? (
                          <WorkerSearchSelect
                            selectedId={form.worker_id || ""}
                            employerId={selectedEmployerId ?? undefined}
                            onSelect={(id) => {
                              void handleWorkerSelect(Number(id));
                            }}
                          />
                        ) : (
                          <input
                            type={field.type}
                            name={field.name}
                            value={form[field.name as keyof AbsenceInput]}
                            onChange={handleChange}
                            className={inputClass}
                            placeholder="0"
                          />
                        )}
                      </div>
                    ))}
                  </div>

                  {groupIndex < fieldGroups.length - 1 && (
                    <hr className={`my-6 ${theme === "light" ? "border-gray-200" : "border-slate-700"}`} />
                  )}
                </div>
              ))}

              {/* Boutons */}
              <div className={`flex flex-col sm:flex-row gap-3 mt-8 pt-6 border-t ${theme === "light" ? "border-gray-200" : "border-slate-700"}`}>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  {loading ? (
                    <span className="flex items-center justify-center">
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Calcul en cours...
                    </span>
                  ) : (
                    "Calculer les retenues"
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleReset}
                  className={theme === "light" ? "px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 focus:ring-4 focus:ring-gray-200 transition-all durée-200" : "px-6 py-3 border border-slate-600 text-slate-200 font-medium rounded-lg hover:bg-slate-800 focus:ring-4 focus:ring-slate-700 transition-all"}
                >
                  Réinitialiser
                </button>
              </div>

              {/* Message d'erreur calcul */}
              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-700 flex items-center">
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {error}
                  </p>
                </div>
              )}
            </form>
          </div>

          {/* Colonne de droite : infos salarié + résultats */}
          <div className="lg:col-span-1 space-y-4">
            {/* Infos salarié */}
            <div className={cardClass}>
              <h2 className={`text-xl font-bold mb-4 ${titleClass}`}>
                Informations du salarié
              </h2>

              {workerLoading && (
                <p className={`text-sm ${mutedTextClass}`}>
                  Chargement des informations du salarié...
                </p>
              )}

              {workerError && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded">
                  <p className="text-sm text-red-700">{workerError}</p>
                </div>
              )}

              {!worker && !workerLoading && !workerError && (
                <p className={`text-sm ${mutedTextClass}`}>
                  Saisis un ID de salarié et quitte le champ pour charger ses
                  informations.
                </p>
              )}

              {displayWorker && (
                <div className={`text-sm space-y-3 ${theme === "light" ? "text-gray-800" : "text-slate-200"}`}>
                  {/* Identité */}
                  <div>
                    <p className={`font-semibold ${titleClass}`}>
                      {displayWorker.prenom} {displayWorker.nom}
                    </p>
                    <p className={mutedTextClass}>
                      Matricule :{" "}
                      <span className="font-medium">{displayWorker.matricule}</span>
                    </p>
                  </div>

                  {/* Coordonnées */}
                  <div>
                    <p>
                      Adresse :{" "}
                      <span className="font-medium">{displayWorker.adresse}</span>
                    </p>
                    <p>
                      Nombre d&apos;enfants :{" "}
                      <span className="font-medium">
                        {displayWorker.nombre_enfant}
                      </span>
                    </p>
                  </div>

                  {/* Données de travail */}
                  <div className={`border-t pt-2 ${theme === "light" ? "border-gray-200" : "border-slate-700"}`}>
                    <p className={`${mutedTextClass} font-medium mb-1`}>
                      Données de travail
                    </p>
                    <p>
                      Horaire hebdomadaire :{" "}
                      <span className="font-semibold">
                        {displayWorker.horaire_hebdo} h / semaine
                      </span>
                    </p>
                    <p>
                      VHM (valeur heure mensuelle) :{" "}
                      <span className="font-semibold">
                        {displayWorker.vhm.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                  </div>

                  {/* Salaire */}
                  <div className={`border-t pt-2 ${theme === "light" ? "border-gray-200" : "border-slate-700"}`}>
                    <p className={`${mutedTextClass} font-medium mb-1`}>
                      Informations salariales
                    </p>
                    <p>
                      Salaire de base :{" "}
                      <span className="font-semibold">
                        {displayWorker.salaire_base.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                    <p>
                      Salaire horaire :{" "}
                      <span className="font-semibold">
                        {displayWorker.salaire_horaire.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                  </div>

                  {/* Infos techniques */}
                  <div className={`border-t pt-2 text-xs ${theme === "light" ? "border-gray-200 text-gray-500" : "border-slate-700 text-slate-400"}`}>
                    <p>
                      ID worker : {displayWorker.id} | Employer ID :{" "}
                      {displayWorker.employer_id} | Régime : {displayWorker.type_regime_id}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Résultats du calcul */}
            {result ? (
              <div className={`${cardClass} sticky top-8`}>
                <h2 className={`text-xl font-bold mb-4 ${titleClass}`}>
                  Résultats du calcul
                </h2>

                {/* Salaire de base */}
                <div className="mb-6">
                  <h3 className={`text-sm font-medium mb-2 ${mutedTextClass}`}>
                    SALAIRE DE BASE
                  </h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className={theme === "light" ? "text-gray-600" : "text-slate-300"}>Journalier</span>
                      <span className="font-semibold">
                        {result.salaire_journalier.toFixed(2)} Ar
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className={theme === "light" ? "text-gray-600" : "text-slate-300"}>Horaire</span>
                      <span className="font-semibold">
                        {result.salaire_horaire.toFixed(2)} Ar
                      </span>
                    </div>
                  </div>
                </div>

                {/* Détail des rubriques */}
                <div className="mb-6">
                  <h3 className={`text-sm font-medium mb-3 ${mutedTextClass}`}>
                    DÉTAIL DES RETENUES
                  </h3>
                  <div className="space-y-3">
                    {result.rubriques.map((rubrique) => (
                      <div
                        key={rubrique.code}
                        className="border-l-4 border-blue-500 pl-3"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <p className={`font-medium ${titleClass}`}>
                              {rubrique.label}
                            </p>
                            <p className={`text-sm ${mutedTextClass}`}>
                              {rubrique.nombre} {rubrique.unite} ×{" "}
                              {rubrique.base.toFixed(2)} Ar
                            </p>
                          </div>
                          <span className="font-semibold text-red-600">
                            {rubrique.montant_salarial.toFixed(2)} Ar
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Total */}
                <div className={`pt-4 border-t ${theme === "light" ? "border-gray-200" : "border-slate-700"}`}>
                  <div className="flex justify-between items-center">
                    <span className={`text-lg font-bold ${titleClass}`}>
                      Total des retenues
                    </span>
                    <span className="text-xl font-bold text-red-600">
                      {result.total_retenues_absence.toFixed(2)} Ar
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className={theme === "light" ? "bg-white rounded-2xl shadow-lg p-8 text-center" : "bg-slate-900 border border-slate-700 rounded-2xl shadow-lg p-8 text-center"}>
                <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 className={`text-lg font-semibold mb-2 ${titleClass}`}>
                  En attente de calcul
                </h3>
                <p className={`text-sm ${mutedTextClass}`}>
                  Les résultats des calculs de retenues s&apos;afficheront ici
                  après validation du formulaire.
                </p>
              </div>
            )}
          </div>
        </div>

        </div>

        <div className={`${activeTab === "history" ? "mt-8" : "hidden"} ${theme === "light" ? "bg-white rounded-2xl shadow-lg p-6" : "bg-slate-900 border border-slate-700 rounded-2xl shadow-lg p-6"}`}>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h2 className={`text-xl font-bold ${titleClass}`}>Historique des absences</h2>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <input
                type="month"
                value={historyMonthFilter}
                onChange={(event) => setHistoryMonthFilter(event.target.value)}
                className={theme === "light" ? "rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white" : "rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 bg-slate-800"}
              />
              <button
                type="button"
                onClick={() => setHistoryMonthFilter("")}
                className={secondaryButtonClass}
              >
                Tous les mois
              </button>
              <button
                type="button"
                onClick={loadHistory}
                className={secondaryButtonClass}
              >
                Rafraîchir
              </button>
            </div>
          </div>

          {historyError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {historyError}
            </div>
          )}

          {historyLoading ? (
            <p className={`text-sm ${mutedTextClass}`}>Chargement de l'historique...</p>
          ) : history.length === 0 ? (
            <p className={`text-sm ${mutedTextClass}`}>Aucun enregistrement pour les filtres courants.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className={`min-w-full ${theme === "light" ? "divide-y divide-gray-200" : "divide-y divide-slate-700"}`}>
                <thead className={theme === "light" ? "bg-gray-50" : "bg-slate-800"}>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Salarié</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Période</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABSM_J</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABSM_H</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABSNR_J</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABSNR_H</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABSMP</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABS1_J</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABS1_H</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABS2_J</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ABS2_H</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {history.map((item) => (
                    <tr key={item.id}>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>#{item.id}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>
                        <button
                          type="button"
                          onClick={() => {
                            setActiveTab("new");
                            void handleWorkerSelect(item.worker_id);
                          }}
                          className="text-left text-blue-700 hover:text-blue-900 hover:underline"
                        >
                          {formatHistoryWorker(item)}
                        </button>
                      </td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.mois}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABSM_J}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABSM_H}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABSNR_J}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABSNR_H}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABSMP}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABS1_J}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABS1_H}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABS2_J}</td>
                      <td className={`px-4 py-3 text-sm ${theme === "light" ? "text-gray-700" : "text-slate-200"}`}>{item.ABS2_H}</td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => handleDeleteHistory(item.id)}
                          className="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm"
                        >
                          Supprimer
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Absences;
