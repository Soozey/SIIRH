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
import { BanknotesIcon, CheckCircleIcon, ExclamationTriangleIcon, UserGroupIcon } from "@heroicons/react/24/outline";
import WorkerSearchSelect from "../components/WorkerSearchSelect";
import { OrganizationalFilterModalOptimized, type OrganizationalFilters } from "../components/OrganizationalFilterModalOptimized";
import { getContextHelp } from "../help/helpContent";
import {
  CorporatePageHeader,
  CorporateStatCard,
  CorporateStatusBadge,
} from "../components/corporate/CorporateUI";
import { formatAriary } from "../utils/ariary";

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

const payrollPanelClass =
  "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm";
const payrollInputClass =
  "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-[15px] font-medium text-slate-950 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100";
const payrollPrimaryButtonClass =
  "w-full rounded-xl bg-[#002147] px-4 py-3 text-[15px] font-semibold text-white shadow-sm transition hover:bg-[#07315f] disabled:cursor-not-allowed disabled:opacity-55";
const payrollSecondaryButtonClass =
  "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-[15px] font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-55";

const JOURNAL_NUMERIC_COLUMNS = [
  "salaire_base", "Salaire de base", "brut_total",
  "HS Non Imposable 130%", "HS Imposable 130%", "HS Non Imposable 150%", "HS Imposable 150%",
  "Heures Majorées Nuit Hab. 30%", "Heures Majorées Nuit Occ. 50%",
  "Heures Majorées Dimanche 40%", "Heures Majorées Jours Fériés 50%",
  "Avantage en nature véhicule", "Avantage en nature logement", "Avantage en nature téléphone",
  "Cotisation CNaPS", "CNaPS Sal.", "CNaPS Salarial", "CNaPS Patronal", "Total CNaPS",
  "cnaps_salarial", "cotisation_cnaps", "cotisation_cnaps_salariale",
  "Cotisation SMIE", "SMIE Patronal", "Total SMIE",
  "FMFP", "FMFP Patronal", "Cotisation FMFP", "fmfp", "fmfp_patronal", "cotisation_fmfp",
  "Charges salariales", "Charges patronales",
  "IRSA", "Avance sur salaire", "Avance sur salaire (quinzaine)", "Autres Déductions",
  "net_a_payer", "cout_total_employeur"
];

const isJournalNumericColumn = (columnId: string) =>
  JOURNAL_NUMERIC_COLUMNS.includes(columnId) ||
  columnId.includes("Prime") ||
  columnId.includes("13ème") ||
  columnId.includes("Avantage");

const isJournalSummableColumn = (columnId: string) => {
  const normalized = columnId
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  const identifierTokens = [
    "matricule",
    "cin",
    "cnaps_num",
    "numero cnaps",
    "n cnaps",
    "n° cnaps",
    "num cnaps",
    "numero cna",
  ];
  if (identifierTokens.some((token) => normalized.includes(token))) {
    return false;
  }
  return isJournalNumericColumn(columnId);
};

const isNumericLikeValue = (value: unknown) => {
  if (value === null || value === undefined || value === "") return false;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value !== "string") return false;
  const normalized = value.replace(/\s/g, "").replace(",", ".");
  return normalized !== "" && Number.isFinite(Number(normalized));
};

const toJournalNumber = (value: unknown) => {
  const numeric = typeof value === "string"
    ? Number(value.replace(/\s/g, "").replace(",", "."))
    : Number(value);
  return Number.isFinite(numeric) ? Math.abs(numeric) : 0;
};

const formatJournalAmount = (value: number) =>
  new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);

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
      console.error("Erreur récupération PayrollRun:", e);
      if (showAlerts) {
        alert("Impossible de récupérer le run de paie.");
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
      alert("Veuillez sélectionner une période.");
      return;
    }

    setIsPreparingPeriodRun(true);
    setPeriodRunMessage(null);
    try {
      const run = await ensurePayrollRun(false);
      if (!run) {
        alert("Impossible de préparer la période de paie.");
        return;
      }
      setPeriodRunMessage(`Période prête : run #${run.id} (${run.period}).`);
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
    
    if (numericColumns.includes(columnId) || isJournalNumericColumn(columnId)) {
      const numValue = toJournalNumber(value);
      
      // Formatage spécial pour l'IRSA : forcer l'affichage avec ,00 si c'est un entier
      if (columnId === 'IRSA') {
        // Si la valeur est un entier (pas de décimales réelles), forcer ,00
        if (Number.isInteger(numValue)) {
          return formatJournalAmount(numValue);
        }
      }
      
      return formatJournalAmount(numValue);
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
    
    if (numericColumns.includes(columnId) || isJournalNumericColumn(columnId)) {
      if (columnId === 'net_a_payer') {
        return 'px-4 py-3 whitespace-nowrap text-[13px] font-bold text-indigo-700 text-right';
      } else if (columnId === 'brut_total') {
        return 'px-4 py-3 whitespace-nowrap text-[13px] font-bold text-emerald-700 text-right';
      } else if (columnId.includes('CNaPS') || columnId.includes('SMIE') || columnId.includes('IRSA') || columnId.includes('Avance') || columnId.includes('Charges')) {
        return 'px-4 py-3 whitespace-nowrap text-[13px] font-bold text-red-700 text-right';
      } else {
        return 'px-4 py-3 whitespace-nowrap text-[13px] font-semibold text-slate-900 text-right';
      }
    }
    
    if (columnId === 'matricule') {
      return 'px-4 py-3 whitespace-nowrap text-[13px] font-bold text-slate-950';
    } else if (columnId === 'nombre_enfant') {
      return 'px-4 py-3 whitespace-nowrap text-[13px] font-medium text-slate-800 text-center';
    } else {
      return 'px-4 py-3 whitespace-nowrap text-[13px] font-medium text-slate-800';
    }
  };

  const getJournalColumnTotal = (columnId: string) => {
    if (!isJournalSummableColumn(columnId)) return null;
    const values = journalData
      .map((row) => row[columnId])
      .filter((value) => value !== null && value !== undefined && value !== "");
    const hasNumericValues = values.some(isNumericLikeValue);
    if (!hasNumericValues) return null;
    return journalData.reduce((sum, row) => sum + toJournalNumber(row[columnId]), 0);
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
  const estimatedPayrollBase = workersList.reduce((sum, item) => sum + (Number(item.salaire_base) || 0), 0);
  const journalNetTotal = journalColumns.includes("net_a_payer") ? getJournalColumnTotal("net_a_payer") : null;
  const journalGrossTotal = journalColumns.includes("brut_total") ? getJournalColumnTotal("brut_total") : null;

  return (
    <div className="payroll-light-scope min-h-screen w-full bg-slate-50 text-slate-950">
      <div className="mx-auto w-full max-w-7xl space-y-6 p-5 md:p-8">
      <CorporatePageHeader
        eyebrow="Paie Madagascar"
        title="Tableau de bord de paie"
        subtitle={`${formatPeriod(period)} · ${selectedEmployerLabel || "Aucun employeur sélectionné"} · montants affichés en Ariary lorsque les données sont disponibles.`}
        actions={
          <>
            <button type="button" onClick={handlePreviewJournal} disabled={!selectedEmployerId || !period || isGeneratingJournal} className="siirh-btn-secondary">
              Aperçu état de paie
            </button>
            <button type="button" onClick={handleDownloadJournal} disabled={!selectedEmployerId || !period || isDownloadingJournal} className="siirh-btn-primary">
              Exporter Excel
            </button>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CorporateStatCard
          label="Masse salariale"
          value={journalGrossTotal !== null ? `${formatJournalAmount(journalGrossTotal)} Ar` : formatAriary(estimatedPayrollBase)}
          hint={journalGrossTotal !== null ? "Total brut de l'état de paie" : "Base estimée depuis les salariés chargés"}
          icon={BanknotesIcon}
          tone="emerald"
        />
        <CorporateStatCard
          label="Effectif paie"
          value={workersList.length}
          hint="Salariés de l'employeur courant"
          icon={UserGroupIcon}
          tone="navy"
        />
        <CorporateStatCard
          label="Net à payer"
          value={journalNetTotal !== null ? `${formatJournalAmount(journalNetTotal)} Ar` : "À générer"}
          hint="Disponible après aperçu de l'état de paie"
          icon={CheckCircleIcon}
          tone={journalNetTotal !== null ? "blue" : "slate"}
        />
        <CorporateStatCard
          label="Période"
          value={period || "-"}
          hint={currentPayrollRunId ? `Run #${currentPayrollRunId}` : "Run non préparé"}
          icon={ExclamationTriangleIcon}
          tone={currentPayrollRunId ? "emerald" : "amber"}
        />
      </section>

      <div className="flex flex-wrap gap-2">
        <CorporateStatusBadge tone="info">IRSA</CorporateStatusBadge>
        <CorporateStatusBadge tone="info">CNaPS</CorporateStatusBadge>
        <CorporateStatusBadge tone="info">OSTIE / SMIE</CorporateStatusBadge>
        <CorporateStatusBadge tone="info">FMFP</CorporateStatusBadge>
        <CorporateStatusBadge tone="success">Ariary</CorporateStatusBadge>
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        {/* Formulaire de configuration */}
        <div className="lg:col-span-1">
          <div className={`${payrollPanelClass} sticky top-4 max-h-[calc(100vh-2rem)] overflow-y-auto`}>
            <h2 className="mb-5 flex items-center gap-2 text-xl font-bold text-slate-950">
              <SparklesIcon className="h-6 w-6 text-sky-600" />
              Paramètres
            </h2>

            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="mb-4">
                  <h3 className="text-sm font-bold text-slate-700">Périmètre centralisé</h3>
                  <p className="mt-1 text-sm text-slate-600">
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
                      className={payrollInputClass}
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
                        <div className="mt-1 text-sm text-slate-600">
                          {activeOrganizationFilterEntries.length > 0
                            ? activeOrganizationFilterEntries.map(([key, value]) => `${key}: ${value}`).join(" | ")
                            : "Aucun filtre actif. Toutes les structures de l'employeur sont prises en compte."}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsPayrollFilterModalOpen(true)}
                        disabled={!selectedEmployerId}
                        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50"
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
                    className={`${payrollInputClass} pl-10`}
                  />
                </div>
                {period && (
                  <p className="mt-2 text-right text-sm font-semibold capitalize text-sky-700">
                    {formatPeriod(period)}
                  </p>
                )}
                <button
                  onClick={handlePreparePeriodRun}
                  disabled={!selectedEmployerId || !period || isPreparingPeriodRun}
                  className={`${payrollSecondaryButtonClass} mt-3 flex items-center justify-center gap-2`}
                >
                  {isPreparingPeriodRun ? (
                    <>
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      Préparation...
                    </>
                  ) : (
                    <>
                      <CalendarDaysIcon className="h-4 w-4" />
                      Nouvelle période
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
                  className={`${payrollSecondaryButtonClass} flex items-center justify-center gap-2`}
                >
                  <CalendarDaysIcon className="h-5 w-5 text-slate-400 group-hover:text-primary-500 transition-colors" />
                  Calendrier de travail
                </button>
              )}

              {/* Bouton Prévisualiser */}
              <button
                onClick={load}
                disabled={isLoading || !workerId || !period}
                className={`${payrollPrimaryButtonClass} flex items-center justify-center gap-2`}
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
                className={`${payrollSecondaryButtonClass} flex items-center justify-center gap-2`}
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
                className={`${payrollSecondaryButtonClass} flex items-center justify-center gap-2`}
                title={!worker ? "Sélectionnez un salarié" : !period ? "Sélectionnez une période" : "Calculer le salaire de base à partir du net souhaité"}
              >
                <CalculatorIcon className="h-5 w-5" />
                Simulateur de salaire
              </button>

              <button
                onClick={handlePreviewJournal}
                disabled={isGeneratingJournal || !selectedEmployerId || !period}
                className={`${payrollSecondaryButtonClass} flex items-center justify-center gap-2 border-emerald-500 text-emerald-700 hover:bg-emerald-50`}
                title={!selectedEmployerId ? "Sélectionnez un employeur" : "Aperçu de l'état de paie"}
              >
                {isGeneratingJournal ? (
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
                Aperçu de l'état de paie
              </button>

              <button
                onClick={handleDownloadJournal}
                disabled={isDownloadingJournal || !selectedEmployerId || !period}
                className={`${payrollPrimaryButtonClass} flex items-center justify-center gap-2 bg-emerald-700 hover:bg-emerald-800`}
                title={!selectedEmployerId ? "Sélectionnez un employeur" : "Exporter l'état de paie en Excel"}
              >
                {isDownloadingJournal ? (
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <TableCellsIcon className="h-5 w-5" />
                )}
                Exporter l'état de paie
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
                  <BanknotesIcon className="h-5 w-5" />
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
            <div className="flex min-h-[420px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-sm">
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
                <p className="mt-1 text-sm font-medium text-slate-700">
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
              {journalData.length > 0 ? (
                <div className="mb-4 grid gap-3 md:grid-cols-4">
                  {[
                    { label: "Total brut", columnId: "brut_total" },
                    { label: "Charges salariales", columnId: "Charges salariales" },
                    { label: "Net à payer", columnId: "net_a_payer" },
                    { label: "Coût employeur", columnId: "cout_total_employeur" },
                  ].map((item) => {
                    const total = getJournalColumnTotal(item.columnId) ?? 0;
                    return (
                      <div key={item.columnId} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                        <div className="text-[12px] font-bold uppercase tracking-wide text-slate-700">{item.label}</div>
                        <div className="mt-2 text-lg font-black text-slate-900">{formatJournalAmount(total)} Ar</div>
                      </div>
                    );
                  })}
                </div>
              ) : null}
              <div className="min-w-full inline-block align-middle">
                <div className="overflow-auto border border-slate-200 rounded-2xl shadow-sm max-h-[58vh]">
                  <table className="min-w-full divide-y divide-slate-200">
                    <thead>
                      <tr>
                        {journalColumns.map((columnId) => (
                          <th
                            key={columnId}
                            className="sticky top-0 z-20 bg-slate-50 px-4 py-3 text-left text-[12px] font-bold text-slate-800 uppercase tracking-wide whitespace-nowrap shadow-[inset_0_-1px_0_rgb(226,232,240)]"
                          >
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
                          <td colSpan={journalColumns.length} className="px-6 py-12 text-center text-sm font-medium text-slate-700">
                            Aucune donnée disponible pour cette période.
                          </td>
                        </tr>
                      )}
                    </tbody>
                    {journalData.length > 0 ? (
                      <tfoot className="sticky bottom-0 bg-slate-900 text-white shadow-[0_-6px_18px_rgba(15,23,42,0.14)]">
                        <tr>
                          {journalColumns.map((columnId, index) => {
                            const total = getJournalColumnTotal(columnId);
                            return (
                              <td key={columnId} className={`px-4 py-3 whitespace-nowrap text-[13px] font-bold ${total !== null ? "text-right" : "text-left"}`}>
                                {total !== null ? formatJournalAmount(total) : index === 0 ? `TOTAL (${journalData.length})` : ""}
                              </td>
                            );
                          })}
                        </tr>
                      </tfoot>
                    ) : null}
                  </table>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end gap-4">
              <button
                onClick={() => setIsJournalModalOpen(false)}
                className="rounded-xl px-6 py-2.5 font-semibold text-slate-800 transition-all hover:bg-white"
              >
                Fermer
              </button>
              <button
                onClick={() => {
                  setIsJournalModalOpen(false);
                  handleDownloadJournal();
                }}
                disabled={journalData.length === 0}
                className="flex items-center gap-2 rounded-xl bg-emerald-700 px-8 py-2.5 font-bold text-white transition-all hover:bg-emerald-800 disabled:opacity-50"
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
            <div className="flex items-center justify-between bg-[#002147] px-6 py-4 text-white">
              <div className="flex items-center gap-3">
                <CalculatorIcon className="h-6 w-6" />
                <div>
                  <h2 className="text-xl font-bold">Simulateur de Salaire</h2>
                  <p className="text-sm text-slate-200">Calcul inverse : du net vers le brut</p>
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
                className={`${payrollPrimaryButtonClass} flex items-center justify-center gap-2`}
              >
                {isCalculating ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <CalculatorIcon className="h-5 w-5" />}
                {isCalculating ? "Calcul en cours..." : "Calculer le Salaire de Base"}
              </button>

              {simulationResult && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
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



