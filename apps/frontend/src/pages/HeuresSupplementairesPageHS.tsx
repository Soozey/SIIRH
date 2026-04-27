import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  calculateHSBackendHS,
  getAllHSCalculationsHS,
  deleteHSCalculationHS,
  exportHSCalculationToPayroll,
  downloadHsImportTemplate,
  previewHsImport,
} from "../api";
import WorkerSearchSelect from "../components/WorkerSearchSelect";

// Type d'une ligne "jour HS"
type JourHS = {
  date_HS: string;
  type_jour_HS: string;
  entree_HS: string;
  sortie_HS: string;
  type_nuit_HS: string;
  duree_pause_minutes_HS: number; // Durée de la pause en minutes
};

// Type du résultat renvoyé par l'API backend HS
type HSResult = {
  id_HS: number;
  worker_id_HS: number;
  worker_matricule_HS?: string | null;
  worker_nom_HS?: string | null;
  worker_prenom_HS?: string | null;
  worker_display_name_HS?: string | null;
  mois_HS: string;
  base_hebdo_heures_HS: number;
  total_HSNI_130_heures_HS: number;
  total_HSI_130_heures_HS: number;
  total_HSNI_150_heures_HS: number;
  total_HSI_150_heures_HS: number;
  total_HMNH_30_heures_HS: number;
  total_HMNO_50_heures_HS: number;
  total_HMD_40_heures_HS: number;
  total_HMJF_50_heures_HS: number;
  created_at_HS: string;
  updated_at_HS: string;
};

type HSMajoratedHoursKeyHS =
  | "total_HSNI_130_heures_HS"
  | "total_HSI_130_heures_HS"
  | "total_HSNI_150_heures_HS"
  | "total_HSI_150_heures_HS"
  | "total_HMNH_30_heures_HS"
  | "total_HMNO_50_heures_HS"
  | "total_HMD_40_heures_HS"
  | "total_HMJF_50_heures_HS";

type ApiValidationIssue = {
  loc?: Array<string | number>;
  msg?: string;
};

type GlobalNightMode = "NONE" | "H" | "O";

type HSExportRates = {
  taux_hs130: number;
  taux_hs150: number;
  taux_hmnh: number;
  taux_hmno: number;
  taux_hmd: number;
  taux_hmjf: number;
};

type WeeklyWorkSummaryHS = {
  totalHours: number;
  startDate: string;
  endDate: string;
  isPartial: boolean;
};

type Employer = {
  id: number;
  raison_sociale: string;
};

const dayFormatterHS = new Intl.DateTimeFormat("fr-FR", { weekday: "long" });
const shortDateFormatterHS = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit" });
const majoratedHoursColumnsHS: Array<{ key: HSMajoratedHoursKeyHS; label: string }> = [
  { key: "total_HSNI_130_heures_HS", label: "HSNI 130%" },
  { key: "total_HSI_130_heures_HS", label: "HSI 130%" },
  { key: "total_HSNI_150_heures_HS", label: "HSNI 150%" },
  { key: "total_HSI_150_heures_HS", label: "HSI 150%" },
  { key: "total_HMNH_30_heures_HS", label: "HMNH 30%" },
  { key: "total_HMNO_50_heures_HS", label: "HMNO 50%" },
  { key: "total_HMD_40_heures_HS", label: "HMD 40%" },
  { key: "total_HMJF_50_heures_HS", label: "HMJF 50%" },
];

const parseLocalDateHS = (value: string): Date | null => {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  const date = new Date(year, month - 1, day);
  return Number.isNaN(date.getTime()) ? null : date;
};

const getDayNameHS = (value: string) => {
  const date = parseLocalDateHS(value);
  return date ? dayFormatterHS.format(date) : "";
};

const formatShortDateHS = (value: string) => {
  const date = parseLocalDateHS(value);
  return date ? shortDateFormatterHS.format(date) : value;
};

const getDayOfWeekHS = (value: string) => parseLocalDateHS(value)?.getDay();

const getWorkerLabelHS = (row: HSResult) => {
  const displayName = (
    row.worker_display_name_HS ||
    [row.worker_nom_HS, row.worker_prenom_HS].filter(Boolean).join(" ")
  ).trim();
  const matricule = row.worker_matricule_HS?.trim();
  if (displayName && matricule) return `${matricule} - ${displayName}`;
  if (displayName) return displayName;
  if (matricule) return matricule;
  return `ID salarié ${row.worker_id_HS}`;
};

const formatHoursHS = (value: number) => `${(Number(value) || 0).toFixed(2)} h`;

const parseTimeToMinutesHS = (value: string) => {
  if (!/^\d{2}:\d{2}$/.test(value)) return null;
  const [hours, minutes] = value.split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null;
  return hours * 60 + minutes;
};

const calculateWorkDurationHoursHS = (jour: JourHS) => {
  const entreeMinutes = parseTimeToMinutesHS(jour.entree_HS);
  let sortieMinutes = parseTimeToMinutesHS(jour.sortie_HS);
  if (entreeMinutes === null || sortieMinutes === null) return 0;
  if (sortieMinutes < entreeMinutes) {
    sortieMinutes += 24 * 60;
  }
  const pauseMinutes = Math.max(0, Number(jour.duree_pause_minutes_HS) || 0);
  return Math.max(0, sortieMinutes - entreeMinutes - pauseMinutes) / 60;
};

const buildWeeklyWorkSummariesHS = (jours: JourHS[]) => {
  const summaries = new Map<number, WeeklyWorkSummaryHS>();
  let totalHours = 0;
  let startDate = "";

  jours.forEach((jour, index) => {
    if (!startDate) {
      startDate = jour.date_HS;
    }
    totalHours += calculateWorkDurationHoursHS(jour);

    const isSunday = getDayOfWeekHS(jour.date_HS) === 0;
    const isLastRow = index === jours.length - 1;
    if (isSunday || isLastRow) {
      summaries.set(index, {
        totalHours,
        startDate,
        endDate: jour.date_HS,
        isPartial: !isSunday,
      });
      totalHours = 0;
      startDate = "";
    }
  });

  return summaries;
};

const HeuresSupplementairesPageHS: React.FC = () => {
  const currentMonth = new Date().toISOString().slice(0, 7);
  const [workerIdHS, setWorkerIdHS] = useState<number | null>(null);
  const [moisHS, setMoisHS] = useState<string>(currentMonth);
  const [baseHebdoHS, setBaseHebdoHS] = useState<number>(40);
  const [activeTab, setActiveTab] = useState<"calcul" | "historique">("calcul");
  const [historySearchHS, setHistorySearchHS] = useState<string>("");
  const [payrollRunIdHS, setPayrollRunIdHS] = useState<string>("");
  const [globalNightModeHS, setGlobalNightModeHS] = useState<GlobalNightMode>("O");
  const [importInfoHS, setImportInfoHS] = useState<string | null>(null);
  const [loadingImportHS, setLoadingImportHS] = useState(false);
  const [employersHS, setEmployersHS] = useState<Employer[]>([]);
  const [selectedEmployerIdHS, setSelectedEmployerIdHS] = useState<number | null>(null);
  const [ratesHS, setRatesHS] = useState<HSExportRates>({
    taux_hs130: 130,
    taux_hs150: 150,
    taux_hmnh: 30,
    taux_hmno: 50,
    taux_hmd: 40,
    taux_hmjf: 50,
  });
  const importFileRefHS = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loadEmployers = async () => {
      try {
        const response = await api.get<Employer[]>("/employers");
        if (cancelled) return;
        setEmployersHS(response.data);
        setSelectedEmployerIdHS((current) => current ?? response.data[0]?.id ?? null);
      } catch (error) {
        console.error("Erreur chargement employeurs:", error);
      }
    };
    void loadEmployers();
    return () => {
      cancelled = true;
    };
  }, []);

  const [joursHS, setJoursHS] = useState<JourHS[]>([
    {
      date_HS: `${currentMonth}-01`,
      type_jour_HS: "N",
      entree_HS: "08:00",
      sortie_HS: "18:00",
      type_nuit_HS: "O",
      duree_pause_minutes_HS: 60, // 1 heure par défaut
    },
  ]);

  const [resultatHS, setResultatHS] = useState<HSResult | null>(null);
  const [loadingHS, setLoadingHS] = useState<boolean>(false);
  const [errorHS, setErrorHS] = useState<string | null>(null);
  const [historiqueHS, setHistoriqueHS] = useState<HSResult[]>([]);
  const [loadingHistoriqueHS, setLoadingHistoriqueHS] = useState<boolean>(false);
  const weeklyWorkSummariesHS = buildWeeklyWorkSummariesHS(joursHS);

  const handleJourChangeHS = (
    index: number,
    field: keyof JourHS,
    value: string
  ) => {
    const copie = [...joursHS];
    copie[index] = {
      ...copie[index],
      [field]: field === "duree_pause_minutes_HS" ? Number(value) || 0 : value,
    };
    setJoursHS(copie);
  };

  const handleAddRowHS = () => {
    setJoursHS((prev) => [
      ...prev,
      {
        date_HS: moisHS + "-01",
        type_jour_HS: "N",
        entree_HS: "08:00",
        sortie_HS: "17:00",
        type_nuit_HS: globalNightModeHS === "NONE" ? "" : globalNightModeHS,
        duree_pause_minutes_HS: 60, // 1 heure par défaut
      },
    ]);
  };

  const handleAddWeekHS = () => {
    const parseDate = (value: string) => {
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? null : date;
    };

    const sortedDates = joursHS
      .map((row) => parseDate(row.date_HS))
      .filter((row): row is Date => row instanceof Date)
      .sort((a, b) => a.getTime() - b.getTime());

    const startDate = sortedDates.length > 0
      ? new Date(sortedDates[sortedDates.length - 1].getTime())
      : new Date(`${moisHS}-01`);

    if (sortedDates.length > 0) {
      startDate.setDate(startDate.getDate() + 1);
    }

    const generatedWeek: JourHS[] = Array.from({ length: 7 }).map((_, index) => {
      const currentDate = new Date(startDate.getTime());
      currentDate.setDate(startDate.getDate() + index);
      const weekday = currentDate.getDay(); // 0 = dimanche
      const isSunday = weekday === 0;
      return {
        date_HS: currentDate.toISOString().slice(0, 10),
        type_jour_HS: isSunday ? "F" : "N",
        entree_HS: "08:00",
        sortie_HS: "17:00",
        type_nuit_HS: globalNightModeHS === "NONE" ? "" : globalNightModeHS,
        duree_pause_minutes_HS: 60,
      };
    });

    setJoursHS((prev) => [...prev, ...generatedWeek]);
  };

  const handleResetRatesHS = () => {
    setRatesHS({
      taux_hs130: 130,
      taux_hs150: 150,
      taux_hmnh: 30,
      taux_hmno: 50,
      taux_hmd: 40,
      taux_hmjf: 50,
    });
  };

  const handleRemoveRowHS = (index: number) => {
    if (joursHS.length > 1) {
      setJoursHS((prev) => prev.filter((_, i) => i !== index));
    }
  };

  const handleApplyGlobalNightToRowsHS = (forceAll: boolean) => {
    const mode = globalNightModeHS === "NONE" ? "" : globalNightModeHS;
    setJoursHS((prev) =>
      prev.map((row) => {
        if (forceAll || !row.type_nuit_HS) {
          return { ...row, type_nuit_HS: mode };
        }
        return row;
      })
    );
  };

  const handleDownloadHsTemplate = async () => {
    try {
      await downloadHsImportTemplate({ employerId: selectedEmployerIdHS ?? undefined });
    } catch (error) {
      console.error("Erreur telechargement template HS:", error);
      setErrorHS("Impossible de telecharger le modele Excel Heures.");
    }
  };

  const handleImportHsFile = async (file?: File) => {
    if (!file) return;
    setLoadingImportHS(true);
    setImportInfoHS(null);
    setErrorHS(null);
    try {
      const preview = await previewHsImport(file);
      const rows = preview.data ?? [];
      const selectedWorkerRows =
        typeof workerIdHS === "number" && workerIdHS > 0
          ? rows.filter((item) => item.worker_id_HS === workerIdHS)
          : rows;

      let rowsToApply = selectedWorkerRows;
      if ((!workerIdHS || workerIdHS <= 0) && rows.length > 0) {
        const uniqueWorkerIds = Array.from(
          new Set(rows.map((item) => item.worker_id_HS).filter((value): value is number => typeof value === "number"))
        );
        if (uniqueWorkerIds.length === 1) {
          setWorkerIdHS(uniqueWorkerIds[0]);
          rowsToApply = rows.filter((item) => item.worker_id_HS === uniqueWorkerIds[0]);
        } else if (uniqueWorkerIds.length > 1) {
          setErrorHS("Le fichier contient plusieurs salaries. Selectionnez un salarie puis reimportez.");
          return;
        }
      }

      if (rowsToApply.length === 0) {
        setErrorHS("Aucune ligne importable pour le salarie selectionne.");
        return;
      }

      setJoursHS(
        rowsToApply.map((item) => ({
          date_HS: item.date_HS,
          type_jour_HS: item.type_jour_HS || "N",
          entree_HS: item.entree_HS,
          sortie_HS: item.sortie_HS,
          type_nuit_HS:
            item.type_nuit_HS ??
            (globalNightModeHS === "NONE" ? "" : globalNightModeHS),
          duree_pause_minutes_HS: Number(item.duree_pause_minutes_HS) || 60,
        }))
      );
      const firstDate = rowsToApply[0]?.date_HS;
      if (firstDate && firstDate.length >= 7) {
        setMoisHS(firstDate.slice(0, 7));
      }
      const warnings = preview.errors?.length ?? 0;
      setImportInfoHS(
        warnings > 0
          ? `${rowsToApply.length} ligne(s) chargee(s), ${warnings} avertissement(s) detecte(s).`
          : `${rowsToApply.length} ligne(s) chargee(s) depuis le fichier.`
      );
    } catch (error) {
      const detail =
        typeof error === "object" && error !== null && "response" in error
          ? (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
          : undefined;
      setErrorHS(detail ? String(detail) : "Import HS impossible.");
    } finally {
      setLoadingImportHS(false);
      if (importFileRefHS.current) {
        importFileRefHS.current.value = "";
      }
    }
  };

  const loadHistoriqueHS = useCallback(async (useFilters: boolean = false) => {
    try {
      setLoadingHistoriqueHS(true);
      const data: HSResult[] = await getAllHSCalculationsHS(
        useFilters && typeof workerIdHS === "number" && workerIdHS > 0 ? workerIdHS : undefined,
        useFilters ? moisHS : undefined
      );
      setHistoriqueHS(data);
    } catch (err) {
      console.error("Erreur lors du chargement de l'historique HS :", err);
    } finally {
      setLoadingHistoriqueHS(false);
    }
  }, [moisHS, workerIdHS]);

  useEffect(() => {
    loadHistoriqueHS();
  }, [loadHistoriqueHS]);

  const filteredHistoriqueHS = historiqueHS.filter((row) => {
    const query = historySearchHS.trim().toLowerCase();
    if (!query) return true;
    const workerLabel = getWorkerLabelHS(row).toLowerCase();
    return (
      String(row.id_HS).includes(query) ||
      String(row.worker_id_HS).includes(query) ||
      workerLabel.includes(query) ||
      row.mois_HS.toLowerCase().includes(query)
    );
  });

  const handleDeleteHS = async (id_HS: number) => {
    const ok = window.confirm(
      `Êtes-vous sûr de vouloir supprimer le calcul HS #${id_HS} ?`
    );
    if (!ok) return;

    try {
      await deleteHSCalculationHS(id_HS);
      setHistoriqueHS((prev) => prev.filter((h) => h.id_HS !== id_HS));
      setResultatHS((prev) => (prev && prev.id_HS === id_HS ? null : prev));
    } catch (err) {
      console.error("Erreur lors de la suppression HS :", err);
      alert("Erreur lors de la suppression du calcul HS.");
    }
  };

  const handleSubmitHS = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!workerIdHS || workerIdHS <= 0) {
      setErrorHS("Veuillez sélectionner un salarié avant de lancer le calcul.");
      return;
    }

    setLoadingHS(true);
    setErrorHS(null);
    setResultatHS(null);

    try {
      const payloadHS = {
        worker_id_HS: workerIdHS,
        mois_HS: moisHS,
        base_hebdo_heures_HS: Number(baseHebdoHS),
        mode_nuit_HS: globalNightModeHS === "NONE" ? null : globalNightModeHS,
        jours_HS: joursHS.map((j) => ({
          date_HS: j.date_HS,
          type_jour_HS: j.type_jour_HS || "N",
          entree_HS: j.entree_HS,
          sortie_HS: j.sortie_HS,
          type_nuit_HS: j.type_nuit_HS || (globalNightModeHS === "NONE" ? null : globalNightModeHS),
          duree_pause_minutes_HS: Number(j.duree_pause_minutes_HS) || 60, // Passing pause duration
        })),
      };

      const res: HSResult = await calculateHSBackendHS(payloadHS);
      setResultatHS(res);
      await loadHistoriqueHS();
      setActiveTab("historique");
    } catch (error: unknown) {
      console.error("Full error object:", error);
      const responseData = typeof error === "object" && error !== null && "response" in error
        ? (error as { response?: { data?: { detail?: unknown } } }).response?.data
        : undefined;
      console.error("Error response:", responseData);

      let errorMessage = "Erreur lors du calcul des heures supplémentaires.";
      const detail = responseData?.detail;

      if (detail) {
        // Pydantic validation errors are in detail
        if (Array.isArray(detail)) {
          errorMessage = detail.map((entry: unknown) => {
            const issue = entry as ApiValidationIssue;
            return `${issue.loc?.join(" -> ") ?? "champ"}: ${issue.msg ?? "invalide"}`;
          }
          ).join('\n');
        } else {
          errorMessage = String(detail);
        }
      } else if (error instanceof Error && error.message) {
        errorMessage = error.message;
      }

      setErrorHS(errorMessage);
    } finally {
      setLoadingHS(false);
    }
  };

  const handleExportToPayrollHS = async (hsId: number) => {
    const payrollRunId = Number(payrollRunIdHS);
    if (!Number.isFinite(payrollRunId) || payrollRunId <= 0) {
      alert("Renseignez un ID de run de paie valide avant l'export.");
      return;
    }

    try {
      const result = await exportHSCalculationToPayroll(hsId, payrollRunId, ratesHS);
      alert(result?.message ?? "Export vers la paie effectué.");
    } catch (error: unknown) {
      const responseDetail = typeof error === "object" && error !== null && "response" in error
        ? (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
        : undefined;
      const message = responseDetail
        ? String(responseDetail)
        : error instanceof Error && error.message
          ? error.message
          : "Erreur lors de l'export vers la paie.";
      alert(message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-2xl shadow-lg mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Calcul des Heures Supplémentaires
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Générez et gérez les calculs d'heures supplémentaires avec les majorations légales
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 bg-white/80 backdrop-blur-sm rounded-2xl p-1 shadow-sm border border-gray-200 mb-8 max-w-md mx-auto">
          <button
            onClick={() => setActiveTab("calcul")}
            className={`flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all duration-200 ${activeTab === "calcul"
              ? "bg-white text-blue-600 shadow-sm border border-gray-200"
              : "text-gray-500 hover:text-gray-700"
              }`}
          >
            <div className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Nouveau Calcul
            </div>
          </button>
          <button
            onClick={() => setActiveTab("historique")}
            className={`flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all duration-200 ${activeTab === "historique"
              ? "bg-white text-blue-600 shadow-sm border border-gray-200"
              : "text-gray-500 hover:text-gray-700"
              }`}
          >
            <div className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Historique
            </div>
          </button>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">

          {/* Tab Content - Calcul */}
          {activeTab === "calcul" && (
            <div className="p-6 lg:p-8">
              <form onSubmit={handleSubmitHS} className="space-y-8">

                <div className="rounded-2xl border border-indigo-100 bg-indigo-50/70 p-5">
                  <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-indigo-900">Parametrage des taux de majoration</h3>
                      <p className="text-xs text-indigo-700">Convention collective appliquee a l export vers la paie.</p>
                    </div>
                    <button
                      type="button"
                      onClick={handleResetRatesHS}
                      className="rounded-lg px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-white"
                    >
                      Reinitialiser aux taux legaux
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
                    {[
                      { key: "taux_hs130", label: "HS 130%" },
                      { key: "taux_hs150", label: "HS 150%" },
                      { key: "taux_hmnh", label: "HMNH" },
                      { key: "taux_hmno", label: "HMNO" },
                      { key: "taux_hmd", label: "HMD" },
                      { key: "taux_hmjf", label: "HMJF" },
                    ].map((item) => (
                      <label key={item.key} className="text-xs font-semibold text-indigo-900">
                        {(() => {
                          const rateKey = item.key as keyof HSExportRates;
                          return (
                            <>
                              {item.label}
                              <div className="mt-1 flex items-center gap-1">
                                <input
                                  type="number"
                                  min={0}
                                  step={0.1}
                                  value={ratesHS[rateKey]}
                                  onChange={(event) => {
                                    const nextValue = Number(event.target.value);
                                    setRatesHS((prev) => ({
                                      ...prev,
                                      [rateKey]: Number.isFinite(nextValue) ? nextValue : 0,
                                    }));
                                  }}
                                  className="w-full rounded-lg border border-indigo-200 bg-white px-2 py-2 text-sm text-slate-800 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                                />
                                <span className="text-indigo-500">%</span>
                              </div>
                            </>
                          );
                        })()}
                      </label>
                    ))}
                  </div>
                </div>

                {/* Informations de base */}
                <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl p-6 text-white">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-white/20 rounded-lg">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold">Informations du Salarié</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2 opacity-90">
                        Salarié
                      </label>
                      <WorkerSearchSelect
                        selectedId={workerIdHS ?? undefined}
                        onSelect={(id) => setWorkerIdHS(Number(id))}
                        className="text-gray-900"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 opacity-90">
                        Période (Mois)
                      </label>
                      <input
                        type="month"
                        value={moisHS}
                        onChange={(e) => setMoisHS(e.target.value)}
                        className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-white/50 text-white"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 opacity-90">
                        Base Hebdomadaire
                      </label>
                      <input
                        type="number"
                        value={baseHebdoHS}
                        onChange={(e) => setBaseHebdoHS(Number(e.target.value))}
                        className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-white/50 text-white placeholder-white/70"
                        placeholder="Ex: 35 heures"
                      />
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-xl border border-white/20 bg-white/10 p-4">
                      <label className="block text-sm font-medium mb-2 opacity-90">
                        Regle globale travail de nuit
                      </label>
                      <select
                        value={globalNightModeHS}
                        onChange={(event) => setGlobalNightModeHS(event.target.value as GlobalNightMode)}
                        className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-white/50 text-white"
                      >
                        <option className="text-gray-900" value="NONE">Aucune regle globale</option>
                        <option className="text-gray-900" value="H">Nuit habituelle (H)</option>
                        <option className="text-gray-900" value="O">Nuit occasionnelle (O)</option>
                      </select>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => handleApplyGlobalNightToRowsHS(false)}
                          className="px-3 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-xs font-semibold"
                        >
                          Appliquer aux lignes vides
                        </button>
                        <button
                          type="button"
                          onClick={() => handleApplyGlobalNightToRowsHS(true)}
                          className="px-3 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-xs font-semibold"
                        >
                          Forcer toutes les lignes
                        </button>
                      </div>
                    </div>

                    <div className="rounded-xl border border-white/20 bg-white/10 p-4">
                      <div className="text-sm font-medium mb-2 opacity-90">Import / modele Excel</div>
                      <select
                        value={selectedEmployerIdHS ?? ""}
                        onChange={(event) => setSelectedEmployerIdHS(event.target.value ? Number(event.target.value) : null)}
                        className="mb-3 w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-white/50 text-white"
                      >
                        <option className="text-gray-900" value="">Choisir un employeur</option>
                        {employersHS.map((employer) => (
                          <option key={`hs-employer-${employer.id}`} className="text-gray-900" value={employer.id}>
                            {employer.raison_sociale}
                          </option>
                        ))}
                      </select>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={handleDownloadHsTemplate}
                          className="px-3 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-xs font-semibold"
                        >
                          Telecharger modele
                        </button>
                        <button
                          type="button"
                          onClick={() => importFileRefHS.current?.click()}
                          className="px-3 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-xs font-semibold disabled:opacity-60"
                          disabled={loadingImportHS}
                        >
                          {loadingImportHS ? "Import..." : "Importer planning Excel"}
                        </button>
                        <input
                          ref={importFileRefHS}
                          type="file"
                          accept=".xlsx,.xls,.csv"
                          className="hidden"
                          onChange={(event) => {
                            const selectedFile = event.target.files?.[0];
                            void handleImportHsFile(selectedFile);
                          }}
                        />
                      </div>
                      <p className="mt-2 text-xs text-white/80">
                        L import charge les lignes de temps; le calcul paie reste inchange.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Tableau des jours */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200">
                  <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">Plannings des Jours</h3>
                        <p className="text-sm text-gray-500">Saisissez les horaires de travail</p>
                      </div>
                    </div>
                    <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full font-medium">
                      {joursHS.length} jour(s)
                    </span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Date
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Type de Jour
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Heure d'Entrée
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Heure de Sortie
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Durée Pause (min)
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Durée de Travail
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Travail de Nuit
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {joursHS.map((jour, index) => {
                          const durationHoursHS = calculateWorkDurationHoursHS(jour);
                          const weeklySummaryHS = weeklyWorkSummariesHS.get(index);
                          return (
                            <React.Fragment key={index}>
                              <tr className="hover:bg-gray-50 transition-colors group">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <input
                                type="date"
                                value={jour.date_HS}
                                onChange={(e) =>
                                  handleJourChangeHS(index, "date_HS", e.target.value)
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                              />
                              <div className="mt-1 text-xs font-semibold capitalize text-blue-600">
                                {getDayNameHS(jour.date_HS)}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <select
                                value={jour.type_jour_HS}
                                onChange={(e) =>
                                  handleJourChangeHS(index, "type_jour_HS", e.target.value)
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                              >
                                <option value="N">🟢 Normal</option>
                                <option value="JF">🔴 Jour Férié</option>
                                <option value="F">⚪ Fermé</option>
                              </select>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <input
                                type="time"
                                value={jour.entree_HS}
                                onChange={(e) =>
                                  handleJourChangeHS(index, "entree_HS", e.target.value)
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <input
                                type="time"
                                value={jour.sortie_HS}
                                onChange={(e) =>
                                  handleJourChangeHS(index, "sortie_HS", e.target.value)
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <input
                                type="number"
                                min="0"
                                step="15"
                                value={jour.duree_pause_minutes_HS}
                                onChange={(e) =>
                                  handleJourChangeHS(index, "duree_pause_minutes_HS", e.target.value)
                                }
                                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                                placeholder="60"
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-bold text-slate-800">
                                {durationHoursHS.toFixed(2)} h
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <select
                                value={jour.type_nuit_HS}
                                onChange={(e) =>
                                  handleJourChangeHS(index, "type_nuit_HS", e.target.value)
                                }
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                              >
                                <option value="">🌞 Aucune</option>
                                <option value="H">🌙 Habituelle</option>
                                <option value="O">🌚 Occasionnelle</option>
                              </select>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <button
                                type="button"
                                onClick={() => handleRemoveRowHS(index)}
                                disabled={joursHS.length === 1}
                                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                Supprimer
                              </button>
                            </td>
                              </tr>
                              {weeklySummaryHS && (
                                <tr className="bg-blue-50/80">
                                  <td colSpan={5} className="px-6 py-3 text-right text-sm font-bold text-blue-900">
                                    {weeklySummaryHS.isPartial ? "Total semaine en cours" : "Total semaine"} du{" "}
                                    {formatShortDateHS(weeklySummaryHS.startDate)} au{" "}
                                    {formatShortDateHS(weeklySummaryHS.endDate)}
                                  </td>
                                  <td className="px-6 py-3 text-sm font-extrabold text-blue-900">
                                    {weeklySummaryHS.totalHours.toFixed(2)} h
                                  </td>
                                  <td colSpan={2} className="px-6 py-3 text-xs font-medium text-blue-700">
                                    Total calculé sur entrée/sortie moins pause.
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Boutons d'action */}
                <div className="flex flex-col sm:flex-row gap-4 justify-between items-center pt-4">
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <button
                      type="button"
                      onClick={handleAddRowHS}
                      className="px-6 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 transition-colors flex items-center gap-2 shadow-sm"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Ajouter un jour
                    </button>

                    <button
                      type="button"
                      onClick={handleAddWeekHS}
                      className="px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors flex items-center gap-2 shadow-sm"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      Ajouter une semaine
                    </button>
                  </div>

                  <button
                    type="submit"
                    disabled={loadingHS || !workerIdHS}
                    className="px-8 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 shadow-lg flex items-center gap-2 font-semibold"
                  >
                    {loadingHS ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                        Calcul en cours...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Calculer les heures supplémentaires
                      </>
                    )}
                  </button>
                </div>
              </form>

              {importInfoHS && (
                <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3">
                  <div className="flex-shrink-0 w-5 h-5 mt-0.5 text-blue-500">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10A8 8 0 112 10a8 8 0 0116 0zm-7-4a1 1 0 10-2 0v4a1 1 0 102 0V6zm-1 8a1.25 1.25 0 100-2.5A1.25 1.25 0 0010 14z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <p className="text-blue-700">{importInfoHS}</p>
                </div>
              )}

              {/* Messages d'erreur */}
              {errorHS && (
                <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
                  <div className="flex-shrink-0 w-5 h-5 mt-0.5 text-red-500">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <p className="text-red-700">{errorHS}</p>
                </div>
              )}

              {/* Résultats du calcul */}
              {resultatHS && (
                <div className="mt-8 bg-gradient-to-br from-green-50 to-emerald-100 rounded-2xl border border-green-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-500 rounded-lg">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold text-gray-900">
                          Calcul terminé avec succès
                        </h3>
                        <p className="text-sm text-gray-600">
                          Effectué le {new Date(resultatHS.created_at_HS).toLocaleString('fr-FR')}
                        </p>
                      </div>
                    </div>
                    <span className="px-3 py-1 bg-green-500 text-white text-sm rounded-full font-medium">
                      ID: {resultatHS.id_HS}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                      { label: "HSNI 130%", value: resultatHS.total_HSNI_130_heures_HS, color: "blue" },
                      { label: "HSI 130%", value: resultatHS.total_HSI_130_heures_HS, color: "blue" },
                      { label: "HSNI 150%", value: resultatHS.total_HSNI_150_heures_HS, color: "purple" },
                      { label: "HSI 150%", value: resultatHS.total_HSI_150_heures_HS, color: "purple" },
                      { label: "HMNH 30%", value: resultatHS.total_HMNH_30_heures_HS, color: "green" },
                      { label: "HMNO 50%", value: resultatHS.total_HMNO_50_heures_HS, color: "yellow" },
                      { label: "HMD 40%", value: resultatHS.total_HMD_40_heures_HS, color: "indigo" },
                      { label: "HMJF 50%", value: resultatHS.total_HMJF_50_heures_HS, color: "red" },
                    ].map((item, index) => (
                      <div key={index} className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                        <p className="text-sm font-medium text-gray-600 mb-1">{item.label}</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {item.value.toFixed(2)}h
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab Content - Historique */}
          {activeTab === "historique" && (
            <div className="p-6 lg:p-8">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900">Historique des Calculs</h3>
                  </div>
                  <p className="text-gray-600">
                    Consultez l'ensemble des calculs d'heures supplémentaires
                  </p>
                </div>
                <button
                  onClick={() => loadHistoriqueHS(false)}
                  disabled={loadingHistoriqueHS}
                  className="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 transition-colors flex items-center gap-2"
                >
                  <svg className={`w-5 h-5 ${loadingHistoriqueHS ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {loadingHistoriqueHS ? "Chargement..." : "Rafraîchir"}
                </button>
              </div>

              <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-3">
                <input
                  type="text"
                  value={historySearchHS}
                  onChange={(e) => setHistorySearchHS(e.target.value)}
                  placeholder="Recherche (ID calcul, salarié, période)"
                  className="px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="number"
                  min={1}
                  value={payrollRunIdHS}
                  onChange={(e) => setPayrollRunIdHS(e.target.value)}
                  placeholder="ID run paie pour export"
                  className="px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={() => loadHistoriqueHS(true)}
                  className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
                >
                  Filtrer par salarié/période
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setHistorySearchHS("");
                    setPayrollRunIdHS("");
                    loadHistoriqueHS(false);
                  }}
                  className="px-4 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Réinitialiser filtres
                </button>
              </div>

              {loadingHistoriqueHS ? (
                <div className="flex justify-center items-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
              ) : filteredHistoriqueHS.length === 0 ? (
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <h3 className="mt-4 text-lg font-medium text-gray-900">Aucun calcul</h3>
                  <p className="mt-2 text-gray-500">
                    Aucun calcul d'heures supplémentaires ne correspond aux critères.
                  </p>
                </div>
              ) : (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-[1120px] divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th rowSpan={2} className="px-4 py-3 text-left align-middle text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Salarié
                          </th>
                          <th rowSpan={2} className="px-3 py-3 text-left align-middle text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Période
                          </th>
                          <th
                            colSpan={majoratedHoursColumnsHS.length}
                            className="border-b border-gray-200 px-2 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider"
                          >
                            Heures Majorées
                          </th>
                          <th rowSpan={2} className="px-3 py-3 text-left align-middle text-xs font-semibold text-gray-600 uppercase tracking-wider">
                            Date
                          </th>
                          <th rowSpan={2} className="sticky right-0 z-20 bg-gray-50 px-3 py-3 text-left align-middle text-xs font-semibold text-gray-600 uppercase tracking-wider shadow-[-8px_0_12px_-12px_rgba(15,23,42,0.55)]">
                            Actions
                          </th>
                        </tr>
                        <tr>
                          {majoratedHoursColumnsHS.map((column) => (
                            <th
                              key={column.key}
                              className="px-2 py-3 text-right text-[11px] font-semibold text-gray-600 uppercase tracking-wide"
                            >
                              {column.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {filteredHistoriqueHS.map((h) => (
                          <tr key={h.id_HS} className="group hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3 whitespace-nowrap">
                              <div>
                                <p className="text-sm font-medium text-gray-900">
                                  {getWorkerLabelHS(h)}
                                </p>
                                <p className="text-xs text-gray-500">
                                  Base: {h.base_hebdo_heures_HS}h/semaine
                                </p>
                              </div>
                            </td>
                            <td className="px-3 py-3 whitespace-nowrap">
                              <span className="px-2.5 py-1 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
                                {h.mois_HS}
                              </span>
                            </td>
                            {majoratedHoursColumnsHS.map((column) => (
                              <td
                                key={column.key}
                                className="px-2 py-3 whitespace-nowrap text-right text-xs font-semibold text-gray-900"
                              >
                                {formatHoursHS(h[column.key])}
                              </td>
                            ))}
                            <td className="px-3 py-3 whitespace-nowrap text-xs text-gray-500">
                              {new Date(h.created_at_HS).toLocaleDateString('fr-FR')}
                              <br />
                              <span className="text-gray-400">
                                {new Date(h.created_at_HS).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </td>
                            <td className="sticky right-0 z-10 whitespace-nowrap bg-white px-3 py-3 shadow-[-8px_0_12px_-12px_rgba(15,23,42,0.55)] group-hover:bg-gray-50">
                              <div className="flex gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleExportToPayrollHS(h.id_HS)}
                                  disabled={!payrollRunIdHS}
                                  className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                  Export paie
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteHS(h.id_HS)}
                                  className="flex items-center gap-1 rounded-md bg-red-500 px-2.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                                >
                                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                  Supprimer
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HeuresSupplementairesPageHS;
