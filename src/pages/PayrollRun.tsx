import { useState, useEffect } from "react";
import { api } from "../api";
import { Link, useNavigate } from "react-router-dom";
import {
  DocumentTextIcon,
  CalendarIcon,
  EyeIcon,
  ArrowPathIcon,
  ArrowUpTrayIcon,
  SparklesIcon,
  ClockIcon,
  PrinterIcon,
  CalendarDaysIcon,
  TableCellsIcon,
  XMarkIcon,
  CalculatorIcon
} from "@heroicons/react/24/outline";
import WorkCalendar from "../components/WorkCalendar";
import HelpTooltip from "../components/help/HelpTooltip";
import ImportHsHmDialog from "../components/ImportHsHmDialog";
import ImportPrimesDialog from "../components/ImportPrimesDialog";
import HsHmManagerModal from "../components/HsHmManagerModal";
import ResetPrimesDialog from "../components/ResetPrimesDialog";
import PayslipDocument, { type PayslipData } from "../components/PayslipDocument";
import ErrorBoundary from "../components/ErrorBoundary";
import { CurrencyDollarIcon } from "@heroicons/react/24/outline";
import WorkerSearchSelect from "../components/WorkerSearchSelect";
import { OrganizationalFilterModalOptimized, type OrganizationalFilters } from "../components/OrganizationalFilterModalOptimized";
import { getContextHelp } from "../help/helpContent";

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

type JournalRow = Record<string, unknown>;
type ApiLikeError = {
  response?: {
    data?: {
      detail?: string;
    };
  };
};

type SalarySimulationResult = {
  target_net: number;
  calculated_base_salary: number;
  actual_net: number;
  difference: number;
  original_base_salary: number;
  iterations: number;
};

type PayrollRunSummary = {
  id: number;
  employer_id: number;
  period: string;
};

type EmployerOption = {
  id: number;
  raison_sociale: string;
  numero_contribuable?: string | null;
};

export default function PayrollRun() {
  // Force rebuild comment
  const [employers, setEmployers] = useState<EmployerOption[]>([]);
  const [selectedEmployerId, setSelectedEmployerId] = useState<number>(0);
  const [organizationFilters, setOrganizationFilters] = useState<OrganizationalFilters | null>(null);
  const [workersList, setWorkersList] = useState<Worker[]>([]);
  const [workerId, setWorkerId] = useState<number | string>(""); // string allowed for empty selection
  const [period, setPeriod] = useState<string>(new Date().toISOString().substring(0, 7));
  const [preview, setPreview] = useState<PayslipData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloadingJournal, setIsDownloadingJournal] = useState(false);
  const [isJournalModalOpen, setIsJournalModalOpen] = useState(false);
  const [journalData, setJournalData] = useState<JournalRow[]>([]);
  const [journalColumns, setJournalColumns] = useState<string[]>([]);
  const [isGeneratingJournal, setIsGeneratingJournal] = useState(false);
  
  // États pour les modales de filtrage
  const [isPayrollFilterModalOpen, setIsPayrollFilterModalOpen] = useState(false);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);
  const [targetNet, setTargetNet] = useState<string>("");
  const [simulationResult, setSimulationResult] = useState<SalarySimulationResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isPreparingPeriodRun, setIsPreparingPeriodRun] = useState(false);
  const [periodRunMessage, setPeriodRunMessage] = useState<string | null>(null);

  // Infos du salarié sélectionné
  const [worker, setWorker] = useState<Worker | null>(null);
  const [workerError, setWorkerError] = useState<string | null>(null);

  // Modales
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);

  const [isImportPrimesOpen, setIsImportPrimesOpen] = useState(false);
  const [isHsHmManagerOpen, setIsHsHmManagerOpen] = useState(false);
  const [isPrimesManagerOpen, setIsPrimesManagerOpen] = useState(false);
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [currentPayrollRunId, setCurrentPayrollRunId] = useState<number | null>(null);

  const navigate = useNavigate();
  const payrollPeriodHelp = getContextHelp("payroll", "period");

  useEffect(() => {
    let isMounted = true;
    const fetchEmployers = async () => {
      try {
        const res = await api.get<EmployerOption[]>("/employers");
        if (!isMounted) return;
        const items = Array.isArray(res.data) ? res.data : [];
        setEmployers(items);
        setSelectedEmployerId((current) =>
          current > 0 && items.some((item) => item.id === current) ? current : items[0]?.id || 0
        );
      } catch (err) {
        console.error("Erreur chargement employeurs:", err);
      }
    };
    void fetchEmployers();
    return () => {
      isMounted = false;
    };
  }, []);

  // 1️⃣ Charger la liste des salariés au montage
  useEffect(() => {
    const fetchWorkers = async () => {
      if (!selectedEmployerId) {
        setWorkersList([]);
        setWorkerId("");
        return;
      }
      try {
        const res = await api.get<Worker[]>("/workers", {
          params: { employer_id: selectedEmployerId },
        });
        setWorkersList(res.data);
        setWorkerId((current) => {
          if (current && res.data.some((item) => item.id === Number(current))) {
            return current;
          }
          return res.data[0]?.id || "";
        });
      } catch (err) {
        console.error("Erreur chargement workers:", err);
      }
    };
    void fetchWorkers();
  }, [selectedEmployerId]);

  // 2️⃣ Mettre à jour l'objet worker quand l'ID change
  useEffect(() => {
    if (!workerId) {
      setWorker(null);
      return;
    }
    const w = workersList.find((w) => w.id === Number(workerId));
    if (w) {
      setWorker(w);
      setWorkerError(null);
    } else {
      // Cas peu probable si on utilise le select, mais possible si old state
      setWorker(null);
    }
  }, [workerId, workersList]);

  const ensurePayrollRun = async (showAlerts: boolean = true): Promise<PayrollRunSummary | null> => {
    if (!selectedEmployerId) {
      if (showAlerts) {
        alert("Veuillez sélectionner un employeur.");
      }
      return null;
    }

    try {
      const run = await api.post<PayrollRunSummary>(`/payroll/get-or-create-run`, null, {
        params: { employer_id: selectedEmployerId, period }
      });
      setCurrentPayrollRunId(run.data.id);
      return run.data;
    } catch (e) {
      console.error("Erreur rÃ©cupÃ©ration PayrollRun:", e);
      if (showAlerts) {
        alert("Impossible de rÃ©cupÃ©rer le run de paie.");
      }
      return null;
    }
  };

  useEffect(() => {
    setCurrentPayrollRunId(null);
    setPeriodRunMessage(null);
  }, [period, selectedEmployerId]);

  const handlePreparePeriodRun = async () => {
    if (!period) {
      alert("Veuillez sÃ©lectionner une pÃ©riode.");
      return;
    }

    setIsPreparingPeriodRun(true);
    setPeriodRunMessage(null);
    try {
      const run = await ensurePayrollRun(false);
      if (!run) {
        alert("Impossible de prÃ©parer la pÃ©riode de paie.");
        return;
      }
      setPeriodRunMessage(`PÃ©riode prÃªte : run #${run.id} (${run.period}).`);
    } finally {
      setIsPreparingPeriodRun(false);
    }
  };

  // Gestion modale Import
  const handleOpenImport = async () => {
    const run = await ensurePayrollRun();
    if (!run) return;
    setIsImportDialogOpen(true);
  };

  const handleOpenManager = async () => {
    const run = await ensurePayrollRun();
    if (!run) return;
    setIsHsHmManagerOpen(true);
  };


  const handleOpenPrimesManager = async () => {
    const run = await ensurePayrollRun();
    if (!run) return;
    setIsPrimesManagerOpen(true);
  };

  const load = async () => {
    if (!workerId || !period) return;
    setIsLoading(true);
    setWorkerError(null);

    try {
      const r = await api.get<PayslipData>(`/payroll/preview`, {
        params: { worker_id: workerId, period },
      });
      setPreview(r.data);
    } catch (error: unknown) {
      console.error("Erreur lors du chargement:", error);
      const msg = (error as ApiLikeError)?.response?.data?.detail || "Erreur lors du calcul du bulletin. Vérifiez les données.";
      setWorkerError(msg);
      setPreview(null);
    } finally {
      setIsLoading(false);
    }
  };

  const formatPeriod = (period: string) => {
    if (!period) return "-";
    const [year, month] = period.split("-");
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
  };

  const formatColumnName = (columnId: string) => {
    // Mapping des noms de colonnes pour l'affichage
    const columnMapping: { [key: string]: string } = {
      'matricule': 'Matricule',
      'nom': 'Nom',
      'prenom': 'Prénom', 
      'cin': 'CIN',
      'cnaps_num': 'N° CNaPS',
      'poste': 'Poste',
      'categorie_prof': 'Catégorie',
      'mode_paiement': 'Mode Paie',
      'nombre_enfant': 'Nb Enfants',
      'salaire_base': 'Salaire Base',
      'Salaire de base': 'Sal. Base Calc.',
      'HS Non Imposable 130%': 'HSNI 130%',
      'HS Imposable 130%': 'HSI 130%',
      'HS Non Imposable 150%': 'HSNI 150%',
      'HS Imposable 150%': 'HSI 150%',
      'Heures Majorées Nuit Hab. 30%': 'Maj. Nuit 30%',
      'Heures Majorées Nuit Occ. 50%': 'Maj. Nuit 50%',
      'Heures Majorées Dimanche 40%': 'Maj. Dim. 40%',
      'Heures Majorées Jours Fériés 50%': 'Maj. JF 50%',
      'Avantage en nature véhicule': 'Av. Véhicule',
      'Avantage en nature logement': 'Av. Logement',
      'Avantage en nature téléphone': 'Av. Téléphone',
      'brut_total': 'Total Brut',
      'Cotisation CNaPS': 'CNaPS Sal.',
      'CNaPS Patronal': 'CNaPS Pat.',
      'Total CNaPS': 'Total CNaPS',
      'Cotisation SMIE': 'SMIE Sal.',
      'SMIE Patronal': 'SMIE Pat.',
      'Total SMIE': 'Total SMIE',
      'Charges salariales': 'Charges Sal.',
      'Charges patronales': 'Charges Pat.',
      'IRSA': 'IRSA',
      'Avance sur salaire': 'Avances',
      'net_a_payer': 'Net à payer',
      'cout_total_employeur': 'Coût Total'
    };
    
    return columnMapping[columnId] || columnId;
  };

  const formatCellValue = (value: unknown, columnId: string, row: JournalRow) => {
    if (value === null || value === undefined || value === '') return '-';
    
    // Colonnes numériques (montants)
    const numericColumns = [
      'salaire_base', 'Salaire de base', 'brut_total', 
      'HS Non Imposable 130%', 'HS Imposable 130%', 'HS Non Imposable 150%', 'HS Imposable 150%',
      'Heures Majorées Nuit Hab. 30%', 'Heures Majorées Nuit Occ. 50%',
      'Heures Majorées Dimanche 40%', 'Heures Majorées Jours Fériés 50%',
      'Avantage en nature véhicule', 'Avantage en nature logement', 'Avantage en nature téléphone',
      'Cotisation CNaPS', 'CNaPS Patronal', 'Total CNaPS',
      'Cotisation SMIE', 'SMIE Patronal', 'Total SMIE', 
      'Charges salariales', 'Charges patronales',
      'IRSA', 'Avance sur salaire', 'net_a_payer', 'cout_total_employeur'
    ];
    
    if (numericColumns.includes(columnId) || columnId.includes('Prime') || columnId.includes('13ème') || columnId.includes('Avantage')) {
      const numValue = Math.abs(Number(value) || 0);
      
      // Formatage spécial pour l'IRSA : forcer l'affichage avec ,00 si c'est un entier
      if (columnId === 'IRSA') {
        // Si la valeur est un entier (pas de décimales réelles), forcer ,00
        if (Number.isInteger(numValue)) {
          return new Intl.NumberFormat('fr-FR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          }).format(numValue);
        }
      }
      
      return new Intl.NumberFormat('fr-FR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(numValue);
    }
    
    // Colonnes spéciales
    if (columnId === 'nom') {
      const nom = typeof row.nom === "string" ? row.nom : "";
      const prenom = typeof row.prenom === "string" ? row.prenom : "";
      return `${nom} ${prenom}`.trim();
    }
    
    if (typeof value === "string" || typeof value === "number") {
      return value;
    }
    if (typeof value === "boolean") {
      return value ? "Oui" : "Non";
    }
    return String(value);
  };

  const getCellStyle = (columnId: string) => {
    const numericColumns = [
      'salaire_base', 'Salaire de base', 'brut_total',
      'HS Non Imposable 130%', 'HS Imposable 130%', 'HS Non Imposable 150%', 'HS Imposable 150%',
      'Heures Majorées Nuit Hab. 30%', 'Heures Majorées Nuit Occ. 50%',
      'Heures Majorées Dimanche 40%', 'Heures Majorées Jours Fériés 50%',
      'Avantage en nature véhicule', 'Avantage en nature logement', 'Avantage en nature téléphone',
      'Cotisation CNaPS', 'CNaPS Patronal', 'Total CNaPS',
      'Cotisation SMIE', 'SMIE Patronal', 'Total SMIE', 
      'Charges salariales', 'Charges patronales',
      'IRSA', 'Avance sur salaire', 'net_a_payer', 'cout_total_employeur'
    ];
    
    if (numericColumns.includes(columnId) || columnId.includes('Prime') || columnId.includes('13ème') || columnId.includes('Avantage')) {
      if (columnId === 'net_a_payer') {
        return 'px-4 py-3 whitespace-nowrap text-xs font-bold text-indigo-600 text-right';
      } else if (columnId === 'brut_total') {
        return 'px-4 py-3 whitespace-nowrap text-xs font-bold text-emerald-600 text-right';
      } else if (columnId.includes('CNaPS') || columnId.includes('SMIE') || columnId.includes('IRSA') || columnId.includes('Avance') || columnId.includes('Charges')) {
        return 'px-4 py-3 whitespace-nowrap text-xs text-red-500 text-right';
      } else {
        return 'px-4 py-3 whitespace-nowrap text-xs text-slate-600 text-right';
      }
    }
    
    if (columnId === 'matricule') {
      return 'px-4 py-3 whitespace-nowrap text-xs font-bold text-slate-900';
    } else if (columnId === 'nombre_enfant') {
      return 'px-4 py-3 whitespace-nowrap text-xs text-slate-600 text-center';
    } else {
      return 'px-4 py-3 whitespace-nowrap text-xs text-slate-600';
    }
  };

  const handleViewBulk = () => {
    if (!selectedEmployerId || !period) {
      alert("Veuillez sélectionner un employeur et une période.");
      return;
    }
    const searchParams = new URLSearchParams();
    if (organizationFilters?.etablissement) searchParams.set('etablissement', organizationFilters.etablissement);
    if (organizationFilters?.departement) searchParams.set('departement', organizationFilters.departement);
    if (organizationFilters?.service) searchParams.set('service', organizationFilters.service);
    if (organizationFilters?.unite) searchParams.set('unite', organizationFilters.unite);
    const queryString = searchParams.toString();
    const url = `/payslip-bulk/${selectedEmployerId}/${period}${queryString ? `?${queryString}` : ''}`;
    navigate(url);
  };

  const handlePreviewJournal = async () => {
    if (!selectedEmployerId || !period) return;
    setIsGeneratingJournal(true);
    try {
      const columnsRes = await api.get<{ columns?: string[] }>(`/reporting/journal-columns/${selectedEmployerId}`);
      const dynamicColumns = Array.isArray(columnsRes.data?.columns) ? columnsRes.data.columns : [];
      setJournalColumns(dynamicColumns);
      const requestData = {
        employer_id: selectedEmployerId,
        start_period: period,
        end_period: period,
        columns: dynamicColumns,
        ...(organizationFilters || {})
      };
      const res = await api.post<JournalRow[]>(`/reporting/generate`, requestData);
      setJournalData(Array.isArray(res.data) ? res.data : []);
      setIsJournalModalOpen(true);
    } catch (error) {
      console.error("Erreur génération aperçu journal:", error);
      alert("Erreur lors de la génération de l'aperçu.");
    } finally {
      setIsGeneratingJournal(false);
    }
  };

  const handleDownloadJournal = async () => {
    if (!selectedEmployerId || !period) return;
    setIsDownloadingJournal(true);
    try {
      const params = {
        employer_id: selectedEmployerId,
        period,
        ...(organizationFilters || {})
      };
      const response = await api.get(`/reporting/export-journal`, {
        params,
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      let filename = `Etat_de_Paie_${period}`;
      if (organizationFilters?.etablissement) filename += `_${organizationFilters.etablissement}`;
      if (organizationFilters?.departement) filename += `_${organizationFilters.departement}`;
      if (organizationFilters?.service) filename += `_${organizationFilters.service}`;
      if (organizationFilters?.unite) filename += `_${organizationFilters.unite}`;
      filename += '.xlsx';

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error("Erreur téléchargement journal:", error);
      alert("Erreur lors du téléchargement de l'état de paie.");
    } finally {
      setIsDownloadingJournal(false);
    }
  };

  const handleReverseCalculation = async () => {
    if (!worker || !period || !targetNet) return;

    const targetNetValue = Number(targetNet);
    if (!Number.isFinite(targetNetValue) || targetNetValue <= 0) {
      alert("Veuillez saisir un montant net valide.");
      return;
    }

    setIsCalculating(true);
    try {
      const response = await api.get<SalarySimulationResult>("/payroll/reverse-calculate", {
        params: {
          worker_id: worker.id,
          period,
          target_net: targetNetValue,
        },
      });
      setSimulationResult(response.data);
    } catch (error) {
      console.error("Erreur calcul inverse:", error);
      alert("Erreur lors du calcul inverse du salaire.");
    } finally {
      setIsCalculating(false);
    }
  };

  const selectedEmployerLabel = employers.find((item) => item.id === selectedEmployerId)?.raison_sociale || null;
  const activeOrganizationFilterEntries = Object.entries(organizationFilters || {}).filter(([, value]) => Boolean(value));

  return (
    <div className="siirh-page min-h-screen w-full flex flex-col">
      <div className="flex-1 w-full max-w-7xl mx-auto p-6 md:p-10 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-900 p-8 shadow-xl shadow-slate-900/20">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-white/20 backdrop-blur-md rounded-2xl shadow-inner border border-white/10">
              <DocumentTextIcon className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
                Gestion des Bulletins
              </h1>
              <p className="text-primary-100 mt-2 text-lg font-medium">
                Prévisualisation, édition et impression en masse
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Formulaire de configuration */}
        <div className="lg:col-span-1">
          <div className="glass-card p-6 sticky top-6 max-h-[calc(100vh-2rem)] overflow-y-auto custom-scrollbar">
            <h2 className="text-xl font-bold text-slate-800 mb-6 flex items-center gap-2">
              <SparklesIcon className="h-6 w-6 text-primary-500" />
              Paramètres
            </h2>

            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="mb-4">
                  <h3 className="text-sm font-bold text-slate-700">Périmètre centralisé</h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Tous les boutons de paie utilisent cet employeur et ce filtre organisationnel.
                  </p>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-slate-700">Employeur</label>
                    <select
                      value={selectedEmployerId || ""}
                      onChange={(e) => {
                        setSelectedEmployerId(Number(e.target.value));
                        setOrganizationFilters(null);
                        setPreview(null);
                        setWorkerError(null);
                      }}
                      className="glass-input w-full px-4 py-3 text-slate-700"
                    >
                      <option value="">Choisir un employeur</option>
                      {employers.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.raison_sociale}
                          {item.numero_contribuable ? ` (${item.numero_contribuable})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-slate-700">Filtre organisationnel</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {activeOrganizationFilterEntries.length > 0
                            ? activeOrganizationFilterEntries.map(([key, value]) => `${key}: ${value}`).join(" | ")
                            : "Aucun filtre actif. Toutes les structures de l'employeur sont prises en compte."}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsPayrollFilterModalOpen(true)}
                        disabled={!selectedEmployerId}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      >
                        {activeOrganizationFilterEntries.length > 0 ? "Modifier filtre" : "Définir filtre"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Salarié Selection */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Salarié
                </label>
                <WorkerSearchSelect
                  selectedId={workerId}
                  employerId={selectedEmployerId || undefined}
                  onSelect={(id) => setWorkerId(id)}
                />
              </div>

              {/* Période */}
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <label className="block text-sm font-semibold text-slate-700">
                    Période
                  </label>
                  <HelpTooltip item={payrollPeriodHelp} role="rh" compact />
                </div>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <CalendarIcon className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="month"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                    className="glass-input w-full pl-10 pr-4 py-3 text-slate-700"
                  />
                </div>
                {period && (
                  <p className="text-xs text-primary-600 mt-2 font-medium text-right capitalize">
                    {formatPeriod(period)}
                  </p>
                )}
                <button
                  onClick={handlePreparePeriodRun}
                  disabled={!selectedEmployerId || !period || isPreparingPeriodRun}
                  className="mt-3 w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-blue-600 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isPreparingPeriodRun ? (
                    <>
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      Preparation...
                    </>
                  ) : (
                    <>
                      <CalendarDaysIcon className="h-4 w-4" />
                      Nouvelle periode
                    </>
                  )}
                </button>
                {periodRunMessage ? (
                  <p className="mt-2 text-xs font-semibold text-emerald-700">
                    {periodRunMessage}
                  </p>
                ) : null}
              </div>

              {/* Calendrier Button */}
              {selectedEmployerId > 0 && (
                <button
                  onClick={() => setIsCalendarOpen(true)}
                  className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-white border border-slate-200 text-slate-700 font-semibold rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm group"
                >
                  <CalendarDaysIcon className="h-5 w-5 text-slate-400 group-hover:text-primary-500 transition-colors" />
                  Calendrier de Travail
                </button>
              )}

              {/* Bouton Prévisualiser */}
              <button
                onClick={load}
                disabled={isLoading || !workerId || !period}
                className="w-full btn-primary py-3.5 rounded-xl font-semibold text-lg flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                    Calcul en cours...
                  </>
                ) : (
                  <>
                    <EyeIcon className="h-5 w-5" />
                    Prévisualiser ce bulletin
                  </>
                )}
              </button>

              {/* Bouton Bulk */}
              <button
                onClick={handleViewBulk}
                disabled={!selectedEmployerId || !period}
                className="w-full py-3 bg-slate-800 text-white font-semibold rounded-xl hover:bg-slate-700 transition-colors flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                title={!selectedEmployerId ? "Sélectionnez un employeur" : !period ? "Sélectionnez une période" : "Imprimer les bulletins de paie"}
              >
                <PrinterIcon className="h-5 w-5" />
                Imprimer tous les bulletins
              </button>

              <button
                onClick={() => {
                  setIsSimulatorOpen(true);
                  setSimulationResult(null);
                }}
                disabled={!worker || !period}
                className="w-full py-3 bg-teal-500 text-white font-bold rounded-xl hover:bg-teal-600 transition-colors flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                title={!worker ? "SÃ©lectionnez un salariÃ©" : !period ? "SÃ©lectionnez une pÃ©riode" : "Calculer le salaire de base Ã  partir du net souhaitÃ©"}
              >
                <CalculatorIcon className="h-5 w-5" />
                Simulateur de Salaire
              </button>

              <button
                onClick={handlePreviewJournal}
                disabled={isGeneratingJournal || !selectedEmployerId || !period}
                className="w-full py-3 bg-white border-2 border-emerald-500 text-emerald-600 font-bold rounded-xl hover:bg-emerald-50 transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                title={!selectedEmployerId ? "Sélectionnez un employeur" : "Aperçu de l'état de paie"}
              >
                {isGeneratingJournal ? (
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
                Aperçu de l'État de Paie
              </button>

              <button
                onClick={handleDownloadJournal}
                disabled={isDownloadingJournal || !selectedEmployerId || !period}
                className="w-full py-3 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                title={!selectedEmployerId ? "Sélectionnez un employeur" : "Exporter l'état de paie en Excel"}
              >
                {isDownloadingJournal ? (
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <TableCellsIcon className="h-5 w-5" />
                )}
                Exporter l'État de paie
              </button>

              {/* Erreur worker */}
              {workerError && (
                <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 font-medium">
                  {workerError}
                </div>
              )}

              {/* Section Imports */}
              <div className="pt-6 border-t border-slate-200">
                <h3 className="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2">
                  <ArrowUpTrayIcon className="h-5 w-5 text-indigo-500" />
                  Gestion Données Variables
                </h3>
                <button
                  onClick={() => {
                    if (!selectedEmployerId) {
                      alert("Veuillez sélectionner un employeur.");
                      return;
                    }
                    setIsImportPrimesOpen(true);
                  }}
                  className="w-full py-3 bg-fuchsia-50 border border-fuchsia-200 text-fuchsia-700 font-semibold rounded-xl hover:bg-fuchsia-100 transition-colors flex items-center justify-center gap-2 mb-2"
                >
                  <CurrencyDollarIcon className="h-5 w-5" />
                  Import Variables Primes
                </button>
                <button
                  onClick={handleOpenPrimesManager}
                  className="w-full py-3 bg-fuchsia-50 border border-fuchsia-200 text-fuchsia-700 font-semibold rounded-xl hover:bg-fuchsia-100 transition-colors flex items-center justify-center gap-2 mb-2"
                  title="Supprimer les valeurs importées et restaurer les formules"
                >
                  <ArrowPathIcon className="h-5 w-5" />
                  Réinitialiser les primes
                </button>
                <button
                  onClick={handleOpenImport}
                  className="w-full py-3 bg-indigo-50 border border-indigo-200 text-indigo-700 font-semibold rounded-xl hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2 mb-2"
                >
                  Import Variables HS HM Absences
                </button>
                <button
                  onClick={handleOpenManager}
                  className="w-full py-3 bg-indigo-50 border border-indigo-200 text-indigo-700 font-semibold rounded-xl hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2"
                >
                  <ClockIcon className="h-5 w-5" />
                  Gérer HS/HM & Absences
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Zone de Prévisualisation */}
        <div className="lg:col-span-2">
          {preview ? (
            <div className="animate-slide-up space-y-6">
              <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                <h3 className="font-bold text-slate-700">Aperçu du document</h3>
                <Link
                  to={`/payslip/${workerId}/${period}`}
                  className="text-sm text-primary-600 hover:text-primary-800 font-medium underline"
                >
                  Ouvrir en mode page entière
                </Link>
              </div>

              {/* Visualisation du composant bulletin */}
              <ErrorBoundary>
                <PayslipDocument
                  key={`${workerId}-${period}`}
                  data={preview}
                />
              </ErrorBoundary>
            </div>
          ) : (
            /* État vide */
            <div className="glass-card p-12 text-center flex flex-col items-center justify-center h-full min-h-[400px]">
              <div className="w-24 h-24 bg-slate-50 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <DocumentTextIcon className="h-10 w-10 text-slate-300" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">
                Aucun bulletin affiché
              </h3>
              <p className="text-slate-500 mb-8 max-w-md mx-auto leading-relaxed">
                Sélectionnez un salarié et cliquez sur <span className="font-semibold text-primary-600">Prévisualiser</span> pour voir son bulletin.<br />
                Ou cliquez sur <span className="font-bold text-slate-700">Imprimer TOUS</span> pour voir l'ensemble des bulletins de l'employeur.
              </p>
            </div>
          )}
        </div>
      </div>

      {isImportPrimesOpen && (
        <ErrorBoundary>
          <ImportPrimesDialog
            isOpen={true}
            onClose={() => setIsImportPrimesOpen(false)}
            period={period}
            employerId={selectedEmployerId || 0}
            employerLabel={selectedEmployerLabel}
            organizationFilters={organizationFilters}
            onSuccess={() => {
              if (workerId) load();
            }}
          />
        </ErrorBoundary>
      )}

      {currentPayrollRunId && isImportDialogOpen && (
        <ErrorBoundary>
          <ImportHsHmDialog
            isOpen={true}
            onClose={() => setIsImportDialogOpen(false)}
            payrollRunId={currentPayrollRunId}
            employerId={selectedEmployerId || 0}
            employerLabel={selectedEmployerLabel}
            organizationFilters={organizationFilters}
            period={period}
            onSuccess={() => {
              if (workerId) load();
            }}
          />
        </ErrorBoundary>
      )}

      {currentPayrollRunId && isHsHmManagerOpen && (
        <ErrorBoundary>
          <HsHmManagerModal
            isOpen={true}
            onClose={() => setIsHsHmManagerOpen(false)}
            payrollRunId={currentPayrollRunId}
            employerId={selectedEmployerId || 0}
            employerLabel={selectedEmployerLabel}
            organizationFilters={organizationFilters}
            period={period}
          />
        </ErrorBoundary>
      )}

      {currentPayrollRunId && isPrimesManagerOpen && (
        <ErrorBoundary>
          <ResetPrimesDialog
            isOpen={true}
            onClose={() => setIsPrimesManagerOpen(false)}
            period={period}
            employerId={selectedEmployerId || 0}
            employerLabel={selectedEmployerLabel}
            organizationFilters={organizationFilters}
            onSuccess={() => {
              if (workerId) load();
            }}
          />
        </ErrorBoundary>
      )}
      {/* Modal Aperçu État de Paie */}
      {isJournalModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden animate-zoom-in">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div>
                <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
                  <TableCellsIcon className="h-7 w-7 text-emerald-500" />
                  Aperçu de l'État de Paie - {formatPeriod(period)}
                </h2>
                <p className="text-slate-500 text-sm mt-1">
                  Vérifiez les montants globaux avant l'export Excel. L'aperçu affiche toutes les colonnes disponibles, identique au contenu de l'export Excel.
                </p>
              </div>
              <button
                onClick={() => setIsJournalModalOpen(false)}
                className="p-2 hover:bg-white rounded-full transition-colors text-slate-400 hover:text-red-500 shadow-sm"
              >
                <XMarkIcon className="h-7 w-7" />
              </button>
            </div>

            {/* Modal Content - Table */}
            <div className="flex-1 overflow-auto p-6 custom-scrollbar">
              <div className="min-w-full inline-block align-middle">
                <div className="overflow-hidden border border-slate-200 rounded-2xl shadow-sm">
                  <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50 sticky top-0">
                      <tr>
                        {journalColumns.map((columnId) => (
                          <th key={columnId} className="px-4 py-3 text-left text-[10px] font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                            {formatColumnName(columnId)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-100">
                      {journalData.length > 0 ? (
                        journalData.map((row, idx) => (
                          <tr key={idx} className="hover:bg-slate-50 transition-colors">
                            {journalColumns.map((columnId) => (
                              <td key={columnId} className={getCellStyle(columnId)}>
                                {formatCellValue(row[columnId], columnId, row)}
                              </td>
                            ))}
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={journalColumns.length} className="px-6 py-12 text-center text-slate-400 italic">
                            Aucune donnée disponible pour cette période.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end gap-4">
              <button
                onClick={() => setIsJournalModalOpen(false)}
                className="px-6 py-2.5 text-slate-600 font-semibold hover:bg-white rounded-xl transition-all"
              >
                Fermer
              </button>
              <button
                onClick={() => {
                  setIsJournalModalOpen(false);
                  handleDownloadJournal();
                }}
                disabled={journalData.length === 0}
                className="px-8 py-2.5 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-200 flex items-center gap-2"
              >
                <TableCellsIcon className="h-5 w-5" />
                Confirmer l'Export Excel
              </button>
            </div>
          </div>
        </div>
      )}

      {isSimulatorOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-4 text-white">
              <div className="flex items-center gap-3">
                <CalculatorIcon className="h-6 w-6" />
                <div>
                  <h2 className="text-xl font-bold">Simulateur de Salaire</h2>
                  <p className="text-sm text-purple-100">Calcul inverse : du net vers le brut</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsSimulatorOpen(false);
                  setSimulationResult(null);
                  setTargetNet("");
                }}
                className="rounded-full p-2 transition hover:bg-white/20"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <div className="space-y-5 p-6">
              <div className="rounded-xl bg-slate-50 p-4">
                <h3 className="mb-2 font-semibold text-slate-800">Salarie selectionne</h3>
                <div className="grid grid-cols-1 gap-2 text-sm text-slate-700 md:grid-cols-2">
                  <p>Nom: <span className="font-medium">{worker?.nom} {worker?.prenom}</span></p>
                  <p>Matricule: <span className="font-medium">{worker?.matricule}</span></p>
                  <p>Salaire actuel: <span className="font-medium">{(worker?.salaire_base || 0).toLocaleString("fr-FR")} Ar</span></p>
                  <p>Periode: <span className="font-medium">{period}</span></p>
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Net souhaite (Ariary)</label>
                <input
                  type="number"
                  value={targetNet}
                  onChange={(e) => setTargetNet(e.target.value)}
                  placeholder="Ex: 1500000"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-lg focus:border-transparent focus:ring-2 focus:ring-purple-500"
                  disabled={isCalculating}
                />
              </div>

              <button
                onClick={handleReverseCalculation}
                disabled={isCalculating || !targetNet}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 py-3 font-bold text-white transition hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50"
              >
                {isCalculating ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <CalculatorIcon className="h-5 w-5" />}
                {isCalculating ? "Calcul en cours..." : "Calculer le Salaire de Base"}
              </button>

              {simulationResult && (
                <div className="rounded-xl border border-green-200 bg-gradient-to-r from-green-50 to-emerald-50 p-4">
                  <h3 className="mb-3 flex items-center gap-2 font-bold text-green-800">
                    <SparklesIcon className="h-5 w-5" />
                    Resultats de la Simulation
                  </h3>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="rounded-lg border border-green-200 bg-white p-3">
                      <p className="text-xs font-medium text-green-600">Net souhaite</p>
                      <p className="text-lg font-bold text-green-800">{simulationResult.target_net.toLocaleString("fr-FR")} Ar</p>
                    </div>
                    <div className="rounded-lg border border-green-200 bg-white p-3">
                      <p className="text-xs font-medium text-green-600">Salaire de base calcule</p>
                      <p className="text-lg font-bold text-green-800">{simulationResult.calculated_base_salary.toLocaleString("fr-FR")} Ar</p>
                    </div>
                    <div className="rounded-lg border border-green-200 bg-white p-3">
                      <p className="text-xs font-medium text-green-600">Net reel obtenu</p>
                      <p className="text-lg font-bold text-green-800">{simulationResult.actual_net.toLocaleString("fr-FR")} Ar</p>
                    </div>
                    <div className="rounded-lg border border-green-200 bg-white p-3">
                      <p className="text-xs font-medium text-green-600">Ecart</p>
                      <p className={`text-lg font-bold ${Math.abs(simulationResult.difference) <= 10 ? "text-green-800" : "text-orange-600"}`}>
                        {simulationResult.difference > 0 ? "+" : ""}{simulationResult.difference.toLocaleString("fr-FR")} Ar
                      </p>
                    </div>
                  </div>
                  <p className="mt-3 rounded-lg bg-green-100 p-2 text-xs text-green-700">
                    Calcul effectue en {simulationResult.iterations} iteration(s).
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">
              <button
                onClick={() => {
                  setIsSimulatorOpen(false);
                  setSimulationResult(null);
                  setTargetNet("");
                }}
                className="rounded-xl px-6 py-2 font-semibold text-slate-600 transition hover:bg-white"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedEmployerId > 0 && (
        <WorkCalendar
          isOpen={isCalendarOpen}
          onClose={() => setIsCalendarOpen(false)}
          employerId={selectedEmployerId}
          initialPeriod={period}
        />
      )}

      <OrganizationalFilterModalOptimized
        isOpen={isPayrollFilterModalOpen}
        onClose={() => setIsPayrollFilterModalOpen(false)}
        onConfirm={(_, filters) => setOrganizationFilters(filters)}
        defaultEmployerId={selectedEmployerId || undefined}
        fixedEmployerId={selectedEmployerId || undefined}
        hideEmployerSelector
        initialFilters={organizationFilters}
        actionTitle="Filtre organisationnel de paie"
        actionDescription="Définissez une seule fois le périmètre organisationnel à appliquer à l'impression, à l'aperçu et à l'export de l'état de paie."
        actionIcon={<TableCellsIcon className="h-6 w-6" />}
      />
      </div>
      <div className="flex-1" />
    </div>
  );
}
