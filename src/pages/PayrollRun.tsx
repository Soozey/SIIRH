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
  XMarkIcon
} from "@heroicons/react/24/outline";
import WorkCalendar from "../components/WorkCalendar";
import ImportHsHmDialog from "../components/ImportHsHmDialog";
import ImportPrimesDialog from "../components/ImportPrimesDialog";
import HsHmManagerModal from "../components/HsHmManagerModal";
import ResetPrimesDialog from "../components/ResetPrimesDialog";
import PayslipDocument from "../components/PayslipDocument";
import ErrorBoundary from "../components/ErrorBoundary";
import { CurrencyDollarIcon } from "@heroicons/react/24/outline";
import WorkerSearchSelect from "../components/WorkerSearchSelect";
import { OrganizationalFilterModalOptimized, type OrganizationalFilters } from "../components/OrganizationalFilterModalOptimized";

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

export default function PayrollRun() {
  // Force rebuild comment
  const [workersList, setWorkersList] = useState<Worker[]>([]);
  const [workerId, setWorkerId] = useState<number | string>(""); // string allowed for empty selection
  const [period, setPeriod] = useState<string>(new Date().toISOString().substring(0, 7));
  const [preview, setPreview] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloadingJournal, setIsDownloadingJournal] = useState(false);
  const [isJournalModalOpen, setIsJournalModalOpen] = useState(false);
  const [journalData, setJournalData] = useState<any[]>([]);
  const [journalColumns, setJournalColumns] = useState<string[]>([]);
  const [isGeneratingJournal, setIsGeneratingJournal] = useState(false);
  
  // États pour les modales de filtrage
  const [isBulkPrintModalOpen, setIsBulkPrintModalOpen] = useState(false);
  const [isJournalPreviewModalOpen, setIsJournalPreviewModalOpen] = useState(false);
  const [isJournalExportModalOpen, setIsJournalExportModalOpen] = useState(false);

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

  // 1️⃣ Charger la liste des salariés au montage
  useEffect(() => {
    const fetchWorkers = async () => {
      try {
        const res = await api.get<Worker[]>("/workers");
        setWorkersList(res.data);
        if (res.data.length > 0) {
          setWorkerId(res.data[0].id); // Sélectionner le premier par défaut
        }
      } catch (err) {
        console.error("Erreur chargement workers:", err);
      }
    };
    fetchWorkers();
  }, []);

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

  // Gestion modale Import
  const handleOpenImport = async () => {
    if (!worker) {
      alert("Veuillez sélectionner un salarié pour identifier l'employeur.");
      return;
    }
    try {
      const run = await api.post(`/payroll/get-or-create-run`, null, {
        params: { employer_id: worker.employer_id, period }
      });
      setCurrentPayrollRunId(run.data.id);
      setIsImportDialogOpen(true);
    } catch (e) {
      console.error("Erreur récupération PayrollRun:", e);
      alert("Impossible de récupérer le run de paie.");
    }
  };

  const handleOpenManager = async () => {
    if (!worker) {
      alert("Veuillez sélectionner un salarié pour identifier l'employeur.");
      return;
    }
    try {
      const run = await api.post(`/payroll/get-or-create-run`, null, {
        params: { employer_id: worker.employer_id, period }
      });
      setCurrentPayrollRunId(run.data.id);
      setIsHsHmManagerOpen(true);
    } catch (e) {
      console.error("Erreur récupération PayrollRun:", e);
      alert("Impossible de récupérer le run de paie.");
    }
  };


  const handleOpenPrimesManager = async () => {
    if (!worker) {
      alert("Veuillez sélectionner un salarié pour identifier l'employeur.");
      return;
    }
    try {
      const run = await api.post(`/payroll/get-or-create-run`, null, {
        params: { employer_id: worker.employer_id, period }
      });
      setCurrentPayrollRunId(run.data.id);
      setIsPrimesManagerOpen(true);
    } catch (e) {
      console.error("Erreur récupération PayrollRun:", e);
      alert("Impossible de récupérer le run de paie.");
    }
  };

  const load = async () => {
    if (!workerId || !period) return;
    setIsLoading(true);
    setWorkerError(null);

    try {
      const r = await api.get(`/payroll/preview`, {
        params: { worker_id: workerId, period },
      });
      setPreview(r.data);
    } catch (error: any) {
      console.error("Erreur lors du chargement:", error);
      const msg = error.response?.data?.detail || "Erreur lors du calcul du bulletin. Vérifiez les données.";
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

  const formatCellValue = (value: any, columnId: string, row: any) => {
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
      return `${row.nom || ''} ${row.prenom || ''}`.trim();
    }
    
    return value;
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
    if (!worker) {
      alert("Veuillez sélectionner un salarié pour identifier l'employeur.");
      return;
    }
    if (worker && period) {
      setIsBulkPrintModalOpen(true);
    }
  };

  const handleBulkPrintConfirm = (employerId: number, filters: OrganizationalFilters | null) => {
    if (period) {
      // Construire l'URL avec les filtres organisationnels
      const searchParams = new URLSearchParams();
      if (filters?.etablissement) searchParams.set('etablissement', filters.etablissement);
      if (filters?.departement) searchParams.set('departement', filters.departement);
      if (filters?.service) searchParams.set('service', filters.service);
      if (filters?.unite) searchParams.set('unite', filters.unite);
      
      const queryString = searchParams.toString();
      const url = `/payslip-bulk/${employerId}/${period}${queryString ? `?${queryString}` : ''}`;
      
      navigate(url);
    }
  };

  const handlePreviewJournal = async () => {
    if (!worker || !period) return;
    setIsJournalPreviewModalOpen(true);
  };

  const handleJournalPreviewConfirm = async (employerId: number, filters: OrganizationalFilters | null) => {
    if (!period) return;
    setIsGeneratingJournal(true);
    try {
      // Récupérer les colonnes dynamiques pour cet employeur
      const columnsRes = await api.get(`/reporting/journal-columns/${employerId}`);
      const dynamicColumns = columnsRes.data.columns;
      
      // Stocker les colonnes pour l'affichage
      setJournalColumns(dynamicColumns);
      
      // Générer l'aperçu avec toutes les colonnes dynamiques et les filtres organisationnels
      const requestData = {
        employer_id: employerId,
        start_period: period,
        end_period: period,
        columns: dynamicColumns,
        ...(filters || {}) // Ajouter les filtres organisationnels si présents
      };
      
      const res = await api.post(`/reporting/generate`, requestData);
      setJournalData(res.data);
      setIsJournalModalOpen(true);
    } catch (error) {
      console.error("Erreur génération aperçu journal:", error);
      alert("Erreur lors de la génération de l'aperçu.");
    } finally {
      setIsGeneratingJournal(false);
    }
  };

  const handleDownloadJournal = async () => {
    if (!worker || !period) return;
    setIsJournalExportModalOpen(true);
  };

  const handleJournalExportConfirm = async (employerId: number, filters: OrganizationalFilters | null) => {
    if (!period) return;
    setIsDownloadingJournal(true);
    try {
      const params = { 
        employer_id: employerId, 
        period,
        ...(filters || {}) // Ajouter les filtres organisationnels si présents
      };
      
      const response = await api.get(`/reporting/export-journal`, {
        params,
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Nom de fichier avec filtres
      let filename = `Etat_de_Paie_${period}`;
      if (filters?.etablissement) filename += `_${filters.etablissement}`;
      if (filters?.departement) filename += `_${filters.departement}`;
      if (filters?.service) filename += `_${filters.service}`;
      if (filters?.unite) filename += `_${filters.unite}`;
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

  return (
    <div className="min-h-screen p-6 md:p-10 max-w-7xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary-600 to-indigo-600 p-8 shadow-2xl shadow-primary-500/30">
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
              {/* Salarié Selection */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Salarié
                </label>
                <WorkerSearchSelect
                  selectedId={workerId}
                  onSelect={(id) => setWorkerId(id)}
                />
              </div>

              {/* Période */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Période
                </label>
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
              </div>

              {/* Calendrier Button */}
              {worker && (
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
                disabled={!period}
                className="w-full py-3 bg-slate-800 text-white font-semibold rounded-xl hover:bg-slate-700 transition-colors flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                title={!period ? "Sélectionnez une période" : "Imprimer les bulletins de paie"}
              >
                <PrinterIcon className="h-5 w-5" />
                Imprimer tous les bulletins
              </button>

              <button
                onClick={handlePreviewJournal}
                disabled={isGeneratingJournal || !period}
                className="w-full py-3 bg-white border-2 border-emerald-500 text-emerald-600 font-bold rounded-xl hover:bg-emerald-50 transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                title="Aperçu de l'état de paie"
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
                disabled={isDownloadingJournal || !period}
                className="w-full py-3 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                title="Exporter l'état de paie en Excel"
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
                    if (!worker) {
                      alert("Veuillez sélectionner un salarié pour identifier l'employeur.");
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
                  key={preview?.computed_at || Date.now()}
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
            employerId={worker?.employer_id || 0}
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
            employerId={worker?.employer_id || 0}
          />
        </ErrorBoundary>
      )}

      {currentPayrollRunId && isPrimesManagerOpen && (
        <ErrorBoundary>
          <ResetPrimesDialog
            isOpen={true}
            onClose={() => setIsPrimesManagerOpen(false)}
            period={period}
            employerId={worker?.employer_id || 0}
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

      {worker && (
        <WorkCalendar
          isOpen={isCalendarOpen}
          onClose={() => setIsCalendarOpen(false)}
          employerId={worker.employer_id}
          initialPeriod={period}
        />
      )}

      {/* Modales de filtrage organisationnel optimisées */}
      <>
        <OrganizationalFilterModalOptimized
          isOpen={isBulkPrintModalOpen}
          onClose={() => setIsBulkPrintModalOpen(false)}
          onConfirm={handleBulkPrintConfirm}
          defaultEmployerId={worker?.employer_id}
          actionTitle="Impression des Bulletins"
          actionDescription="Choisissez l'employeur et si vous voulez imprimer tous les bulletins ou seulement ceux d'une structure organisationnelle spécifique."
          actionIcon={<PrinterIcon className="h-6 w-6" />}
        />

        <OrganizationalFilterModalOptimized
          isOpen={isJournalPreviewModalOpen}
          onClose={() => setIsJournalPreviewModalOpen(false)}
          onConfirm={handleJournalPreviewConfirm}
          defaultEmployerId={worker?.employer_id}
          actionTitle="Aperçu de l'État de Paie"
          actionDescription="Sélectionnez l'employeur et prévisualisez l'état de paie complet ou filtré par structure organisationnelle."
          actionIcon={<EyeIcon className="h-6 w-6" />}
        />

        <OrganizationalFilterModalOptimized
          isOpen={isJournalExportModalOpen}
          onClose={() => setIsJournalExportModalOpen(false)}
          onConfirm={handleJournalExportConfirm}
          defaultEmployerId={worker?.employer_id}
          actionTitle="Export de l'État de Paie"
          actionDescription="Choisissez l'employeur et exportez l'état de paie en Excel, avec ou sans filtrage organisationnel."
          actionIcon={<TableCellsIcon className="h-6 w-6" />}
        />
      </>
    </div>
  );
}
