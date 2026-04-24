import { useState, useEffect, useMemo } from "react";
import { api } from "../api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Dialog } from "@headlessui/react";
import { useNavigate } from "react-router-dom";
import WorkCertificate from "../components/WorkCertificate";
import EmploymentAttestation from "../components/EmploymentAttestation";
import EmploymentContract from "../components/EmploymentContract";
import ImportWorkersDialog from "../components/ImportWorkersDialog";
import { CascadingOrganizationalSelect } from "../components/CascadingOrganizationalSelect";
import type { CascadingSelectValue } from "../components/CascadingOrganizationalSelection";
import { Skeleton } from "../components/ui/Skeleton";
import { useAuth } from "../contexts/AuthContext";
import { useWorkerData } from "../hooks/useConstants";
import { hasModulePermission, sessionHasRole } from "../rbac";
import { formatAriary } from "../utils/ariary";
// ❌ SYSTÈME MATRICULE SUSPENDU - Ne pas utiliser
// import { MatriculeWorkerSelect } from "../components/MatriculeWorkerSelect";
import {
  PlusIcon,
  UserIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  PencilIcon,
  TrashIcon,
  BriefcaseIcon,
  CurrencyDollarIcon,
  ClockIcon,
  IdentificationIcon,
  TagIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  ArrowPathIcon,
  BuildingOfficeIcon
} from "@heroicons/react/24/outline";

type TypeRegime = {
  id: number;
  code: string;
  label: string;
  vhm: number;
};

type Employer = {
  id: number;
  raison_sociale: string;
};

type WorkerValidationError = {
  loc?: Array<string | number>;
  msg?: string;
};

type WorkerApiError = {
  response?: {
    data?: {
      detail?: string | WorkerValidationError[];
      message?: string;
    };
  };
  message?: string;
};

type WorkerPositionHistory = {
  id: number;
  poste?: string | null;
  organizational_unit_id?: number | null;
  start_date?: string | null;
};

type WorkerRecord = {
  id: number;
  employer_id: number;
  is_active?: boolean;
  deleted_at?: string | null;
  matricule: string;
  nom: string;
  prenom: string;
  sexe?: string | null;
  situation_familiale?: string | null;
  date_naissance?: string | null;
  lieu_naissance?: string | null;
  adresse?: string | null;
  telephone?: string | null;
  email?: string | null;
  cin?: string | null;
  cin_delivre_le?: string | null;
  cin_lieu?: string | null;
  cnaps_num?: string | null;
  nombre_enfant?: number | string | null;
  date_embauche?: string | null;
  nature_contrat?: string | null;
  duree_essai_jours?: number | null;
  date_fin_essai?: string | null;
  etablissement?: string | null;
  departement?: string | null;
  service?: string | null;
  unite?: string | null;
  organizational_unit_id?: number | null;
  indice?: string | null;
  valeur_point?: number | null;
  secteur?: string | null;
  mode_paiement?: string | null;
  rib?: string | null;
  code_banque?: string | null;
  code_guichet?: string | null;
  compte_num?: string | null;
  cle_rib?: string | null;
  nom_guichet?: string | null;
  banque?: string | null;
  bic?: string | null;
  categorie_prof?: string | null;
  poste?: string | null;
  date_debauche?: string | null;
  type_sortie?: string | null;
  groupe_preavis?: number | null;
  jours_preavis_deja_faits?: number | null;
  type_regime_id?: number | null;
  salaire_base?: number | null;
  salaire_horaire?: number | null;
  vhm?: number | null;
  horaire_hebdo?: number | null;
  avantage_vehicule?: number | null;
  avantage_logement?: number | null;
  avantage_telephone?: number | null;
  avantage_autres?: number | null;
  taux_sal_cnaps_override?: number | null;
  taux_sal_smie_override?: number | null;
  taux_pat_cnaps_override?: number | null;
  taux_pat_smie_override?: number | null;
  taux_pat_fmfp_override?: number | null;
  solde_conge_initial?: number | null;
  position_history?: WorkerPositionHistory[];
};

type PaginatedWorkersResponse = {
  items: WorkerRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type WorkerResetMode = "soft" | "hard";
type ResetFeedback = { type: "success" | "error"; message: string } | null;

type RecruitmentLibraryItem = {
  id: number;
  category: string;
  label: string;
  description: string | null;
  payload?: Record<string, unknown>;
};

type ClassificationOption = {
  code: string;
  label: string;
  family: string;
  group?: number;
  description: string;
};

function WorkerCanonicalSummary({ worker }: { worker: WorkerRecord }) {
  const { data: workerData } = useWorkerData(worker.id);
  const name = `${workerData?.prenom || worker.prenom} ${workerData?.nom || worker.nom}`.trim();
  const meta = [
    workerData?.matricule || worker.matricule,
    workerData?.poste || worker.poste,
    workerData?.departement,
  ]
    .filter(Boolean)
    .join(" | ");

  return (
    <>
      <h3 className="text-lg font-semibold text-gray-900 truncate flex items-center gap-2">
        {name}
      </h3>
      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-1">
          <IdentificationIcon className="h-4 w-4" />
          <span className="font-medium">Référence: {workerData?.matricule || worker.matricule}</span>
        </div>
        {meta ? (
          <div className="flex items-center gap-1">
            <BriefcaseIcon className="h-4 w-4" />
            <span>{meta}</span>
          </div>
        ) : null}
      </div>
    </>
  );
}

export default function Workers() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { session } = useAuth();
  const isInspector = sessionHasRole(session, ["inspecteur", "inspection_travail", "labor_inspector", "labor_inspector_supervisor"]);
  const canWriteWorkforce = hasModulePermission(session, "workforce", "write") && !isInspector;
  const isAdmin = sessionHasRole(session, ["admin", "system_admin", "super_administrateur_systeme"]);
  const canDeleteWorkers = canWriteWorkforce && sessionHasRole(session, ["drh", "rh"]);
  const [openModal, setOpenModal] = useState(false);
  const [editingWorker, setEditingWorker] = useState<WorkerRecord | null>(null);

  // NEW: Document Modal State
  // NEW: Document Modal State
  const [documentModalOpen, setDocumentModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false); // NEW Import Modal State
  const [selectedDocumentWorker, setSelectedDocumentWorker] = useState<WorkerRecord | null>(null);
  // Type of document to show: 'certificate' | 'attestation' | 'contract'
  const [documentType, setDocumentType] = useState<'certificate' | 'attestation' | 'contract'>('attestation');
  const [bankModalOpen, setBankModalOpen] = useState(false);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetMode, setResetMode] = useState<WorkerResetMode>("soft");
  const [resetConfirmationText, setResetConfirmationText] = useState("");
  const [resetFeedback, setResetFeedback] = useState<ResetFeedback>(null);
  const { data: selectedDocumentWorkerData } = useWorkerData(selectedDocumentWorker?.id || 0);

  const { data: employers = [] } = useQuery({
    queryKey: ["employers"],
    queryFn: async () => (await api.get("/employers")).data as Employer[]
  });

  const { data: typeRegimes = [] } = useQuery({
    queryKey: ["typeRegimes"],
    queryFn: async () => (await api.get("/type_regimes")).data as TypeRegime[]
  });

  // Declare form state BEFORE using it in queries
  const [form, setForm] = useState({
    employer_id: 1, // Fixed default value instead of employers[0]?.id || 1
    matricule: "",
    nom: "",
    prenom: "",
    sexe: "",
    situation_familiale: "",
    date_naissance: "",
    lieu_naissance: "",
    adresse: "",
    telephone: "",
    email: "",
    cin: "",
    cin_delivre_le: "",
    cin_lieu: "",
    cnaps_num: "",
    nombre_enfant: "",
    date_embauche: "",
    nature_contrat: "CDI",
    duree_essai_jours: 0,
    date_fin_essai: "",
    etablissement: "",
    departement: "",
    service: "",
    unite: "",
    organizational_unit_id: null as number | null,
    indice: "",
    valeur_point: 0,
    secteur: "",
    mode_paiement: "",
    rib: "",
    code_banque: "",
    code_guichet: "",
    compte_num: "",
    cle_rib: "",
    nom_guichet: "",
    banque: "",
    bic: "",
    categorie_prof: "",
    poste: "",
    date_debauche: "",
    type_sortie: "L",
    groupe_preavis: 1,
    jours_preavis_deja_faits: 0,
    type_regime_id: 1, // Fixed default value instead of typeRegimes[0]?.id || 1
    salaire_base: 0,
    salaire_horaire: 0,
    vhm: 200, // Fixed default value instead of typeRegimes[0]?.vhm || 200
    horaire_hebdo: 40,
    avantage_vehicule: 0,
    avantage_logement: 0,
    avantage_telephone: 0,
    avantage_autres: 0,
    taux_sal_cnaps_override: null as number | null,
    taux_sal_smie_override: null as number | null,
    taux_pat_cnaps_override: null as number | null,
    taux_pat_smie_override: null as number | null,
    taux_pat_fmfp_override: null as number | null,
    solde_conge_initial: 0 as number | string,
  });
  const [organizationalSelection, setOrganizationalSelection] = useState<CascadingSelectValue>({});

  const { data: classificationLibrary = [] } = useQuery({
    queryKey: ["recruitment-library-classification", form.employer_id],
    enabled: Number(form.employer_id) > 0,
    queryFn: async () =>
      (
        await api.get<RecruitmentLibraryItem[]>("/recruitment/library-items", {
          params: {
            employer_id: form.employer_id,
            category: "professional_classification",
          },
        })
      ).data,
  });

  const classificationOptions = useMemo<ClassificationOption[]>(() => {
    return classificationLibrary.map((item) => {
      const payload = item.payload ?? {};
      const payloadCode = typeof payload.code === "string" ? payload.code.trim() : "";
      const fallbackCode = item.label.includes(" - ") ? item.label.split(" - ")[0].trim() : item.label.trim();
      const code = payloadCode || fallbackCode;
      const label = typeof payload.label === "string" ? payload.label.trim() : item.label.replace(`${code} -`, "").trim();
      const family = typeof payload.family === "string" ? payload.family : "";
      const group = typeof payload.group === "number" ? payload.group : undefined;
      const description = typeof payload.description === "string" ? payload.description : item.description || "";
      return { code, label, family, group, description };
    });
  }, [classificationLibrary]);

  const selectedClassification = useMemo(() => {
    const raw = String(form.categorie_prof || "").trim().toLowerCase();
    if (!raw) return null;
    return (
      classificationOptions.find((option) => option.code.toLowerCase() === raw || `${option.code} - ${option.label}`.toLowerCase() === raw) ||
      null
    );
  }, [classificationOptions, form.categorie_prof]);

  // Fetch organizational data for selected employer - NOUVEAU: Utilisation du système hiérarchique
  // Ancienne requete organization supprimee : non utilisee dans ce composant.
  

  // Search State
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedEmployerFilter, setSelectedEmployerFilter] = useState<number | "all">("all");
  const [page, setPage] = useState(1);
  const pageSize = 25;
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 500);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, selectedEmployerFilter]);

  const { data: workersResponse, isLoading: workersLoading } = useQuery({
    queryKey: ["workers", debouncedSearch, selectedEmployerFilter, page, pageSize],
    queryFn: async () => (
      await api.get("/workers/paginated", {
        params: {
          q: debouncedSearch,
          page,
          page_size: pageSize,
          ...(selectedEmployerFilter !== "all" ? { employer_id: selectedEmployerFilter } : {})
        }
      })
    ).data as PaginatedWorkersResponse
  });
  const workers = workersResponse?.items ?? [];
  const totalWorkers = workersResponse?.total ?? 0;
  const totalPages = workersResponse?.total_pages ?? 1;

  // Multiselect State
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Update form defaults when employers and typeRegimes are loaded
  useEffect(() => {
    if (employers.length > 0 && typeRegimes.length > 0) {
      setForm(prevForm => ({
        ...prevForm,
        employer_id: prevForm.employer_id === 1 ? employers[0].id : prevForm.employer_id,
        type_regime_id: prevForm.type_regime_id === 1 ? typeRegimes[0].id : prevForm.type_regime_id,
        vhm: prevForm.vhm === 200 ? typeRegimes[0].vhm : prevForm.vhm
      }));
    }
  }, [employers, typeRegimes]);

  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === workers.length && workers.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(workers.map((w) => w.id)));
    }
  };







  // Mettre à jour la VHM quand le type de régime change
  const handleTypeRegimeChange = (typeRegimeId: number) => {
    const selectedRegime = typeRegimes.find(regime => regime.id === typeRegimeId);
    setForm(f => ({
      ...f,
      type_regime_id: typeRegimeId,
      vhm: selectedRegime?.vhm || 200
    }));
  };

  const getWorkerErrorMessage = (error: unknown, fallback: string): string => {
    const typedError = error as WorkerApiError;
    if (typedError.response?.data?.detail && Array.isArray(typedError.response.data.detail)) {
      return typedError.response.data.detail
        .map((item) => `${item.loc?.join(".")} : ${item.msg}`)
        .join("\n");
    }
    if (typedError.response?.data?.detail) {
      return String(typedError.response.data.detail);
    }
    if (typedError.response?.data?.message) {
      return typedError.response.data.message;
    }
    if (typedError.message) {
      return typedError.message;
    }
    return fallback;
  };

  const resetConfirmationExpected = resetMode === "hard" ? "RESET EMPLOYEES HARD" : "RESET EMPLOYEES";

  const create = useMutation({
    mutationFn: async () => {
      // Sanitize form data
      const sanitizedData = {
        ...form,
        nombre_enfant: form.nombre_enfant === "" ? 0 : parseInt(String(form.nombre_enfant)) || 0,
        salaire_base: parseFloat(String(form.salaire_base)) || 0,
        salaire_horaire: parseFloat(String(form.salaire_horaire)) || 0,
        vhm: parseFloat(String(form.vhm)) || 200,
        horaire_hebdo: parseFloat(String(form.horaire_hebdo)) || 40,
        valeur_point: parseFloat(String(form.valeur_point)) || 0,
        duree_essai_jours: parseInt(String(form.duree_essai_jours)) || 0,

        // Dates
        date_naissance: form.date_naissance || null,
        date_embauche: form.date_embauche || null,
        date_fin_essai: form.date_fin_essai || null,
        cin_delivre_le: form.cin_delivre_le || null,
        date_debauche: form.date_debauche || null,

        avantage_vehicule: parseFloat(String(form.avantage_vehicule)) || 0,
        avantage_logement: parseFloat(String(form.avantage_logement)) || 0,
        avantage_telephone: parseFloat(String(form.avantage_telephone)) || 0,
        avantage_autres: parseFloat(String(form.avantage_autres)) || 0,

        type_sortie: form.type_sortie,
        groupe_preavis: form.groupe_preavis ? parseInt(String(form.groupe_preavis)) : null,
        jours_preavis_deja_faits: parseInt(String(form.jours_preavis_deja_faits)) || 0,

        taux_sal_cnaps_override: form.taux_sal_cnaps_override !== null ? parseFloat(String(form.taux_sal_cnaps_override)) : null,
        taux_sal_smie_override: form.taux_sal_smie_override !== null ? parseFloat(String(form.taux_sal_smie_override)) : null,
        taux_pat_cnaps_override: form.taux_pat_cnaps_override !== null ? parseFloat(String(form.taux_pat_cnaps_override)) : null,
        taux_pat_smie_override: form.taux_pat_smie_override !== null ? parseFloat(String(form.taux_pat_smie_override)) : null,
        taux_pat_fmfp_override: form.taux_pat_fmfp_override !== null ? parseFloat(String(form.taux_pat_fmfp_override)) : null,
        solde_conge_initial: parseFloat(String(form.solde_conge_initial)) || 0
      };
      return (await api.post("/workers", sanitizedData)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workers"] });
      setOpenModal(false);
      resetForm();
    },
    onError: (error: unknown) => {
      console.error("Erreur lors de la création:", error);

      const errorMessage = getWorkerErrorMessage(
        error,
        "Erreur inconnue lors de la creation du travailleur"
      );

      alert(`Erreur lors de la création du travailleur:\n${errorMessage}`);
    }
  });

  const resetForm = () => {
    setForm({
      employer_id: employers.length > 0 ? employers[0].id : 1,
      matricule: "",
      nom: "",
      prenom: "",
      sexe: "",
      situation_familiale: "",
      date_naissance: "",
      lieu_naissance: "",
      adresse: "",
      telephone: "",
      email: "",
      cin: "",
      cin_delivre_le: "",
      cin_lieu: "",
      cnaps_num: "",
      nombre_enfant: "",
      date_embauche: "",
      nature_contrat: "CDI",
      duree_essai_jours: 0,
      date_fin_essai: "",
      etablissement: "",
      departement: "",
      service: "",
      unite: "",
      organizational_unit_id: null,
      indice: "",
      valeur_point: 0,
      secteur: "",
      mode_paiement: "",
      rib: "",
      code_banque: "",
      code_guichet: "",
      compte_num: "",
      cle_rib: "",
      nom_guichet: "",
      banque: "",
      bic: "",
      categorie_prof: "",
      poste: "",
      date_debauche: "",
      type_sortie: "L",
      groupe_preavis: 1,
      jours_preavis_deja_faits: 0,
      type_regime_id: typeRegimes.length > 0 ? typeRegimes[0].id : 1,
      salaire_base: 0,
      salaire_horaire: 0,
      vhm: typeRegimes.length > 0 ? typeRegimes[0].vhm : 200,
      horaire_hebdo: 40,
      avantage_vehicule: 0,
      avantage_logement: 0,
      avantage_telephone: 0,
      avantage_autres: 0,
      taux_sal_cnaps_override: null,
      taux_sal_smie_override: null,
      taux_pat_cnaps_override: null,
      taux_pat_smie_override: null,
      taux_pat_fmfp_override: null,
      solde_conge_initial: 0
    });
    setOrganizationalSelection({});
    
  };

  const handleOpenDocument = (worker: WorkerRecord) => {
    setSelectedDocumentWorker(worker);
    // Default logic: Terminated -> Certificate, Active -> Attestation
    if (worker.date_debauche) {
      setDocumentType('certificate');
    } else {
      setDocumentType('attestation');
    }
    setDocumentModalOpen(true);
  };


  const deleteWorker = useMutation({
    mutationFn: async (id: number) => (await api.delete<{ message?: string }>(`/workers/${id}`)).data,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["workers"] });
      alert(data.message || "Travailleur désactivé avec succès.");
    },
    onError: (error: unknown) => {
      alert(getWorkerErrorMessage(error, "Erreur lors de la désactivation du travailleur."));
    },
  });

  const deleteBatch = useMutation({
    mutationFn: async (ids: number[]) => (await api.post<{ message?: string }>("/workers/delete_batch", { ids })).data,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["workers"] });
      alert(data.message || "Travailleurs désactivés avec succès.");
      setSelectedIds(new Set()); // Clear selection
    },
    onError: (error: unknown) => {
      alert(getWorkerErrorMessage(error, "Erreur lors de la désactivation de la sélection."));
    }
  });

  const resetWorkers = useMutation({
    mutationFn: async () => {
      const payload = {
        employer_id: selectedEmployerFilter === "all" ? null : selectedEmployerFilter,
        mode: resetMode,
        confirmation_text: resetConfirmationText.trim(),
      };
      console.info("workers.reset submit", payload);
      const response = await api.post<{ message: string; count: number; mode: WorkerResetMode }>("/workers/reset", payload);
      return response.data;
    },
    onSuccess: (data) => {
      console.info("workers.reset success", data);
      qc.invalidateQueries({ queryKey: ["workers"] });
      setSelectedIds(new Set());
      setResetFeedback({ type: "success", message: data.message || "Réinitialisation des employés effectuée." });
      setResetConfirmationText("");
      setTimeout(() => {
        setResetModalOpen(false);
        setResetMode("soft");
        setResetFeedback(null);
      }, 800);
    },
    onError: (error: unknown) => {
      const message = getWorkerErrorMessage(error, "Erreur lors de la réinitialisation des employés.");
      console.error("workers.reset error", error);
      setResetFeedback({ type: "error", message });
    },
  });

  const handleResetSubmit = () => {
    const normalizedConfirmation = resetConfirmationText.trim().toUpperCase();
    if (!normalizedConfirmation) {
      setResetFeedback({ type: "error", message: "Saisissez le texte de confirmation avant de lancer la réinitialisation." });
      return;
    }
    if (normalizedConfirmation !== resetConfirmationExpected) {
      setResetFeedback({ type: "error", message: `Texte invalide. Saisissez exactement: ${resetConfirmationExpected}` });
      return;
    }
    setResetFeedback(null);
    resetWorkers.mutate();
  };

  const handleDeleteSelection = async () => {
    if (selectedIds.size === 0) return;

    if (window.confirm(`Êtes-vous sûr de vouloir désactiver ces ${selectedIds.size} travailleur(s) ?`)) {
      deleteBatch.mutate(Array.from(selectedIds));
    }
  };

  // Bulk Delete replaced by Selection Delete (kept logic if needed but user requested change)
  // const handleDeleteAll = ... (removed/hidden)

  const updateWorker = useMutation({
    mutationFn: async () => {
      if (!editingWorker?.id) {
        throw new Error("Worker ID manquant");
      }

      // Sanitize form data: convert empty strings to proper values
      // Important : Pydantic attend null et non "" pour les champs Optionnels (Date, Int, Float)
      const sanitizedData = {
        ...form,
        nombre_enfant: form.nombre_enfant === "" ? 0 : parseInt(String(form.nombre_enfant)) || 0,
        salaire_base: parseFloat(String(form.salaire_base)) || 0,
        salaire_horaire: parseFloat(String(form.salaire_horaire)) || 0,
        vhm: parseFloat(String(form.vhm)) || 200,
        horaire_hebdo: parseFloat(String(form.horaire_hebdo)) || 40,
        valeur_point: parseFloat(String(form.valeur_point)) || 0,
        duree_essai_jours: parseInt(String(form.duree_essai_jours)) || 0,

        // Dates
        date_naissance: form.date_naissance || null,
        date_embauche: form.date_embauche || null,
        date_fin_essai: form.date_fin_essai || null,
        cin_delivre_le: form.cin_delivre_le || null,
        date_debauche: form.date_debauche || null,

        avantage_vehicule: parseFloat(String(form.avantage_vehicule)) || 0,
        avantage_logement: parseFloat(String(form.avantage_logement)) || 0,
        avantage_telephone: parseFloat(String(form.avantage_telephone)) || 0,
        avantage_autres: parseFloat(String(form.avantage_autres)) || 0,

        taux_sal_cnaps_override: String(form.taux_sal_cnaps_override) === "" ? null : form.taux_sal_cnaps_override,
        taux_sal_smie_override: String(form.taux_sal_smie_override) === "" ? null : form.taux_sal_smie_override,
        taux_pat_cnaps_override: String(form.taux_pat_cnaps_override) === "" ? null : form.taux_pat_cnaps_override,
        taux_pat_smie_override: String(form.taux_pat_smie_override) === "" ? null : form.taux_pat_smie_override,
        taux_pat_fmfp_override: String(form.taux_pat_fmfp_override) === "" ? null : form.taux_pat_fmfp_override,
        solde_conge_initial: parseFloat(String(form.solde_conge_initial)) || 0
      };

      return await api.put(`/workers/${editingWorker.id}`, sanitizedData);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workers"] });
      setOpenModal(false);
      setEditingWorker(null);
      resetForm();
    },
    onError: (error: unknown) => {
      console.error("Erreur lors de la mise à jour:", error);
      console.error("Détails de l'erreur:", JSON.stringify(error, null, 2));
      const errorMessage = getWorkerErrorMessage(error, "Erreur inconnue");
      alert(`Erreur lors de la mise à jour:\n${errorMessage}`);
    }
  });




  const getSecteurColor = (typeRegimeId: number) => {
    const regime = typeRegimes.find(r => r.id === typeRegimeId);
    if (!regime) return "bg-gray-100 text-gray-800 border-gray-200";

    return regime.code === "agricole"
      ? "bg-green-100 text-green-800 border-green-200"
      : "bg-blue-100 text-blue-800 border-blue-200";
  };

  const getSecteurDot = (typeRegimeId: number) => {
    const regime = typeRegimes.find(r => r.id === typeRegimeId);
    if (!regime) return "bg-gray-500";

    return regime.code === "agricole"
      ? "bg-green-500"
      : "bg-blue-500";
  };

  const getSecteurLabel = (typeRegimeId: number) => {
    const regime = typeRegimes.find(r => r.id === typeRegimeId);
    return regime ? regime.label : "Non défini";
  };

  const formatCurrency = (amount: number) => formatAriary(amount);

  const getInitials = (prenom: string, nom: string) => {
    return `${prenom?.[0] || ''}${nom?.[0] || ''}`.toUpperCase();
  };

  // Calcul du préavis légal (JS Logic for Display)
  const calculateLegalNotice = () => {
    if (form.nature_contrat !== "CDI") return 0;

    // Calc seniority
    const start = form.date_embauche ? new Date(form.date_embauche) : null;
    const end = form.date_debauche ? new Date(form.date_debauche) : new Date(); // Use today if no debug date? Or maybe 0.

    if (!start) return 0;

    const diffTime = Math.abs(end.getTime() - start.getTime());
    const seniorityDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    // Note: B68 seems to be simple diff in days.

    const S = seniorityDays;
    const G = form.groupe_preavis;

    if (S <= 0) return 0;

    let days = 0;

    if (G === 1) {
      if (S < 8) days = 1;
      else if (S < 90) days = 3;
      else if (S < 365) days = 8;
      else if (S <= 1825) days = 10 + 2 * Math.floor((S - 365) / 365);
      else days = 30;
    }
    else if (G === 2) {
      if (S < 8) days = 2;
      else if (S < 90) days = 8;
      else if (S < 365) days = 15;
      else if (S <= 1825) days = 30 + 2 * Math.floor((S - 365) / 365);
      else days = 45;
    }
    else if (G === 3) {
      if (S < 8) days = 3;
      else if (S < 90) days = 15;
      else if (S < 365) days = 30;
      else if (S <= 1825) days = 45 + 2 * Math.floor((S - 365) / 365);
      else days = 60;
    }
    else if (G === 4) {
      if (S < 8) days = 4;
      else if (S < 90) days = 30;
      else if (S < 365) days = 45;
      else if (S <= 1825) days = 75 + 2 * Math.floor((S - 365) / 365);
      else days = 90;
    }
    else if (G === 5) {
      if (S < 8) days = 5;
      else if (S < 90) days = 30;
      else if (S < 365) days = 90;
      else if (S <= 1825) days = 120 + 2 * Math.floor((S - 365) / 365);
      else days = 180;
    }

    return days;
  };

  const legalNotice = calculateLegalNotice();
  const noticeBalance = Math.max(0, legalNotice - form.jours_preavis_deja_faits);

  // NEW: Homonym detection for worker list
  const detectHomonyms = (workerList: WorkerRecord[]) => {
    const nameGroups: Record<string, WorkerRecord[]> = {};
    
    workerList.forEach(worker => {
      const fullName = `${worker.prenom} ${worker.nom}`.toLowerCase();
      if (!nameGroups[fullName]) {
        nameGroups[fullName] = [];
      }
      nameGroups[fullName].push(worker);
    });

    return Object.fromEntries(
      Object.entries(nameGroups).filter(([, groupedWorkers]) => groupedWorkers.length > 1)
    );
  };

  const homonymGroups = detectHomonyms(workers);
  const hasHomonyms = Object.keys(homonymGroups).length > 0;

  // Function to check if a worker is a homonym
  const isHomonym = (worker: WorkerRecord) => {
    const fullName = `${worker.prenom} ${worker.nom}`.toLowerCase();
    return homonymGroups[fullName]?.length > 1;
  };

  // --- AUTOMATIC RIB CALCULATION ---
  const calculateRIBKey = (bank: string, branch: string, account: string) => {
    if (!bank || !branch || !account) return "";
    if (bank.length !== 5 || branch.length !== 5 || account.length !== 11) return "";

    const convertToDigits = (s: string) => {
      const map: { [key: string]: string } = {
        'A': '1', 'J': '1',
        'B': '2', 'K': '2', 'S': '2',
        'C': '3', 'L': '3', 'T': '3',
        'D': '4', 'M': '4', 'U': '4',
        'E': '5', 'N': '5', 'V': '5',
        'F': '6', 'O': '6', 'W': '6',
        'G': '7', 'P': '7', 'X': '7',
        'H': '8', 'Q': '8', 'Y': '8',
        'I': '9', 'R': '9', 'Z': '9'
      };
      return s.toUpperCase().replace(/[A-Z]/g, char => map[char] || char);
    };

    try {
      const b = convertToDigits(bank);
      const g = convertToDigits(branch);
      const c = convertToDigits(account);

      // BigInt needed as (89*b + 15*g + 3*c) can be large
      const val = BigInt(b) * 89n + BigInt(g) * 15n + BigInt(c) * 3n;
      const key = 97n - (val % 97n);
      return key.toString().padStart(2, '0');
    } catch {
      return "";
    }
  };

  useEffect(() => {
    if (form.code_banque && form.code_guichet && form.compte_num) {
      const key = calculateRIBKey(form.code_banque, form.code_guichet, form.compte_num);
      if (key && key !== form.cle_rib) {
        setForm(f => ({ ...f, cle_rib: key }));
      }
    }
  }, [form.code_banque, form.code_guichet, form.compte_num, form.cle_rib]);

  return (
    <div className="siirh-page min-h-screen bg-gray-50 p-4 md:p-6">
      <datalist id="workers-professional-classification">
        {classificationOptions.map((option) => (
          <option key={`${option.code}-${option.label}`} value={option.code}>
            {option.label}
            {option.group ? ` | Groupe ${option.group}` : ""}
          </option>
        ))}
      </datalist>
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-900 rounded-2xl p-6 mb-6 shadow-lg print:hidden">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
              <BriefcaseIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white">
                Gestion des Travailleurs
              </h1>
              <p className="text-blue-100 mt-1">
                {totalWorkers} travailleur(s) enregistré(s)
                {hasHomonyms && (
                  <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-100 border border-yellow-400/30">
                    <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                    {Object.keys(homonymGroups).length} groupe(s) d'homonymes détecté(s)
                  </span>
                )}
              </p>
            </div>
            <div className="rounded-xl bg-slate-900 px-4 py-3 text-right">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Volume</div>
              <div className="mt-1 text-lg font-semibold text-white">{totalWorkers}</div>
              <div className="text-xs text-slate-400">page {page} / {totalPages}</div>
            </div>
          </div>

          {/* Search Bar - Enhanced with Matricule Support */}
          <div className="flex-1 w-full md:max-w-md mx-0 md:mx-4">
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-blue-200 group-focus-within:text-white transition-colors" />
              </div>
              <input
                type="text"
                placeholder="Recherche par matricule, nom ou prénom"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 bg-white/10 border border-white/20 rounded-xl leading-5 text-white placeholder-blue-200 focus:outline-none focus:bg-white/20 focus:ring-2 focus:ring-white/50 focus:border-transparent transition-all sm:text-sm backdrop-blur-sm"
              />
            </div>
          </div>
          <div className="flex gap-3 w-full md:w-auto">
            {canWriteWorkforce ? (
              <button
                onClick={() => setImportModalOpen(true)}
                className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white font-medium rounded-xl transition-all backdrop-blur-sm"
              >
                <DocumentTextIcon className="h-5 w-5" />
                Importer Excel
              </button>
            ) : null}
            {isAdmin ? (
              <button
                type="button"
                onClick={() => setResetModalOpen(true)}
                className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white font-medium rounded-xl transition-all shadow-lg"
              >
                <ArrowPathIcon className="h-5 w-5" />
                Réinitialiser employés
              </button>
            ) : null}
            {/* Bouton Supprimer Sélection */}
            {canDeleteWorkers && selectedIds.size > 0 && (
              <button
                onClick={handleDeleteSelection}
                className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-medium rounded-xl transition-all shadow-lg animate-in fade-in zoom-in duration-200"
              >
                <TrashIcon className="h-5 w-5" />
                Désactiver ({selectedIds.size})
              </button>
            )}
            {/* Bouton Tout Supprimer (Discret ou caché) -> Caché car remplacé par sélection */}
            {/* 
            <button
               // ...
            >
               Tout Supprimer
            </button>
            */}
            {canWriteWorkforce ? (
              <button
                onClick={() => {
                  setEditingWorker(null);
                  setOrganizationalSelection({});
                  setForm({
                  employer_id: employers.length > 0 ? employers[0].id : 1,
                  matricule: "",
                  nom: "",
                  prenom: "",
                  sexe: "",
                  situation_familiale: "",
                  date_naissance: "",
                  lieu_naissance: "",
                  adresse: "",
                  telephone: "",
                  email: "",
                  cin: "",
                  cin_delivre_le: "",
                  cin_lieu: "",
                  cnaps_num: "",
                  nombre_enfant: "",
                  date_embauche: "",
                  nature_contrat: "CDI",
                  duree_essai_jours: 0,
                  date_fin_essai: "",
                  etablissement: "",
                  departement: "",
                  service: "",
                  unite: "",
                  organizational_unit_id: null,
                  indice: "",
                  valeur_point: 0,
                  secteur: "",
                  mode_paiement: "",
                  rib: "",
                  banque: "",
                  bic: "",
                  categorie_prof: "",
                  poste: "",
                  date_debauche: "",
                  type_sortie: "L",
                  groupe_preavis: 1,
                  jours_preavis_deja_faits: 0,
                  type_regime_id: typeRegimes.length > 0 ? typeRegimes[0].id : 1,
                  salaire_base: 0,
                  salaire_horaire: 0,
                  vhm: typeRegimes.length > 0 ? typeRegimes[0].vhm : 200,
                  horaire_hebdo: 46,
                  avantage_vehicule: 0,
                  avantage_logement: 0,
                  avantage_telephone: 0,
                  avantage_autres: 0,
                  taux_sal_cnaps_override: null,
                  taux_sal_smie_override: null,
                  taux_pat_cnaps_override: null,
                  taux_pat_smie_override: null,
                  taux_pat_fmfp_override: null,
                  solde_conge_initial: 0,
                  code_banque: "",
                  code_guichet: "",
                  compte_num: "",
                  cle_rib: "",
                  nom_guichet: ""
                });
                  setOpenModal(true);
                }}
                className="inline-flex items-center gap-2 bg-white text-blue-600 hover:bg-gray-50 px-6 py-3 rounded-xl font-semibold shadow-lg transition-all duration-200 hover:shadow-xl transform hover:-translate-y-0.5"
              >
                <PlusIcon className="h-5 w-5" />
                Nouveau Travailleur
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {/* Employer Filter */}
      <div className="bg-white rounded-2xl p-5 mb-6 shadow-sm border border-gray-200 print:hidden">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <BuildingOfficeIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Filtrer par Employeur</h2>
              <p className="text-sm text-gray-600">
                Selectionnez un employeur pour filtrer la liste des travailleurs.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <label htmlFor="workers-employer-filter" className="text-sm font-medium text-gray-700">
              Employeur :
            </label>
            <select
              id="workers-employer-filter"
              value={selectedEmployerFilter}
              onChange={(e) => {
                const value = e.target.value;
                setSelectedEmployerFilter(value === "all" ? "all" : Number(value));
              }}
              className="min-w-[220px] rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            >
              <option value="all">Tous les employeurs</option>
              {employers.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.raison_sociale}
                </option>
              ))}
            </select>
            <span className="text-sm text-gray-500">{totalWorkers} affiche(s)</span>
          </div>
        </div>
      </div>

      {/* Modal */}
      {openModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="border-b border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <UserIcon className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">
                      {editingWorker ? "Modifier Travailleur" : "Nouveau Travailleur"}
                    </h2>
                    <p className="text-gray-600 text-sm mt-1">
                      {editingWorker ? "Modifier les informations du travailleur" : "Ajouter un nouveau travailleur au système"}
                    </p>
                  </div>
                </div>
                <button onClick={() => setOpenModal(false)} className="text-gray-400 hover:text-gray-500">
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
            </div>

            {/* Form */}
            <div className="p-8 bg-slate-50/30">
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Basic Info */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Société Employeur</label>
                      <select
                        value={form.employer_id}
                        onChange={(e) => {
                          const employerId = Number(e.target.value);
                          setForm((f) => ({
                            ...f,
                            employer_id: employerId,
                            etablissement: "",
                            departement: "",
                            service: "",
                            unite: "",
                            organizational_unit_id: null,
                          }));
                          setOrganizationalSelection({});
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      >
                        {employers.map((emp) => (
                          <option key={emp.id} value={emp.id}>{emp.raison_sociale}</option>
                        ))}
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Matricule</label>
                        <input type="text" value={form.matricule} onChange={e => setForm(f => ({ ...f, matricule: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Sexe</label>
                        <select value={form.sexe} onChange={e => setForm(f => ({ ...f, sexe: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                          <option value="">Sélectionner</option>
                          <option value="M">Masculin</option>
                          <option value="F">Féminin</option>
                        </select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Nom</label>
                        <input type="text" value={form.nom} onChange={e => setForm(f => ({ ...f, nom: e.target.value.toUpperCase() }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Prénom</label>
                        <input type="text" value={form.prenom} onChange={e => setForm(f => ({ ...f, prenom: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Date de Naissance</label>
                        <input type="date" value={form.date_naissance} onChange={e => setForm(f => ({ ...f, date_naissance: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Lieu de Naissance</label>
                        <input type="text" value={form.lieu_naissance} onChange={e => setForm(f => ({ ...f, lieu_naissance: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Situation Familiale</label>
                      <select value={form.situation_familiale} onChange={e => setForm(f => ({ ...f, situation_familiale: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        <option value="">Sélectionner</option>
                        <option value="Célibataire">Célibataire</option>
                        <option value="Marié(e)">Marié(e)</option>
                        <option value="Divorcé(e)">Divorcé(e)</option>
                        <option value="Veuf(ve)">Veuf(ve)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Adresse</label>
                      <input type="text" value={form.adresse} onChange={e => setForm(f => ({ ...f, adresse: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Numéro CIN</label>
                        <input type="text" value={form.cin} onChange={e => setForm(f => ({ ...f, cin: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Délivré le</label>
                        <input type="date" value={form.cin_delivre_le} onChange={e => setForm(f => ({ ...f, cin_delivre_le: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Lieu de délivrance CIN</label>
                      <input type="text" value={form.cin_lieu} onChange={e => setForm(f => ({ ...f, cin_lieu: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Numéro CNaPS</label>
                        <input type="text" value={form.cnaps_num} onChange={e => setForm(f => ({ ...f, cnaps_num: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Mode de paiement</label>
                        <select value={form.mode_paiement} onChange={e => setForm(f => ({ ...f, mode_paiement: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                          <option value="Virement">Virement</option>
                          <option value="Espèces">Espèces</option>
                          <option value="Chèque">Chèque</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Contract Info */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Date d'embauche</label>
                      <input type="date" value={form.date_embauche} onChange={e => setForm(f => ({ ...f, date_embauche: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Nature du Contrat</label>
                      <select value={form.nature_contrat} onChange={e => setForm(f => ({ ...f, nature_contrat: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        <option value="CDI">CDI</option>
                        <option value="CDD">CDD</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Durée Essai (jours)</label>
                        <input type="number" value={form.duree_essai_jours} onChange={e => setForm(f => ({ ...f, duree_essai_jours: +e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Fin Essai</label>
                        <input type="date" value={form.date_fin_essai} onChange={e => setForm(f => ({ ...f, date_fin_essai: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Poste</label>
                      <input type="text" value={form.poste} onChange={e => setForm(f => ({ ...f, poste: e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                    </div>
                    
                    {/* Organizational Structure - NOUVEAU: Système hiérarchique avec cascade */}
                    <div className="md:col-span-2">
                      <div className="bg-blue-50 p-4 rounded-xl border border-blue-200">
                        <h4 className="text-sm font-semibold text-blue-800 mb-3 flex items-center gap-2">
                          <BuildingOfficeIcon className="h-4 w-4" />
                          Structure Organisationnelle
                        </h4>
                        <CascadingOrganizationalSelect
                          employerId={form.employer_id}
                          value={organizationalSelection}
                          onChange={(values) => {
                            setOrganizationalSelection(values);
                            setForm(f => ({
                              ...f,
                              etablissement: '',
                              departement: '',
                              service: '',
                              unite: '',
                              organizational_unit_id: values.unite ?? values.service ?? values.departement ?? values.etablissement ?? null
                            }));
                          }}
                        />
                      </div>
                    </div>

                    {/* NEW: Matricule-based Worker Assignment for Organizational Changes */}
                    {editingWorker && (
                      <div className="md:col-span-2">
                        <div className="bg-green-50 p-4 rounded-xl border border-green-200">
                          {/* ❌ SYSTÈME MATRICULE SUSPENDU - Section désactivée
                          <h4 className="text-sm font-semibold text-green-800 mb-3 flex items-center gap-2">
                            <UserIcon className="h-4 w-4" />
                            Affectation Organisationnelle par Matricule
                          </h4>
                          <p className="text-xs text-green-600 mb-3">
                            Utilisez cette section pour affecter ce salarié à une nouvelle structure organisationnelle en utilisant son matricule.
                          </p>
                          <MatriculeWorkerSelect
                            employerId={form.employer_id}
                            value={selectedWorkerMatricule}
                            onChange={(matricule, workerInfo) => {
                              setSelectedWorkerMatricule(matricule);
                              setSelectedWorkerInfo(workerInfo);
                            }}
                            placeholder="Rechercher par matricule ou nom pour affectation..."
                            showMatricule={true}
                            label="Salarié à affecter"
                            className="mb-2"
                          />
                          {selectedWorkerInfo && selectedWorkerInfo.matricule !== form.matricule && (
                            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-md">
                              <p className="text-xs text-yellow-700">
                                <strong>Attention:</strong> Vous avez sélectionné un salarié différent ({selectedWorkerInfo.full_name} - {selectedWorkerInfo.matricule}) 
                                de celui en cours d'édition ({form.prenom} {form.nom} - {form.matricule}).
                              </p>
                            </div>
                          )}
                          */}
                        </div>
                      </div>
                    )}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Catégorie Professionnelle</label>
                      <input
                        type="text"
                        list="workers-professional-classification"
                        value={form.categorie_prof}
                        onChange={e => setForm(f => ({ ...f, categorie_prof: e.target.value }))}
                        onBlur={e => {
                          const raw = e.target.value.trim().toLowerCase();
                          if (!raw) return;
                          const match = classificationOptions.find(
                            (option) =>
                              option.code.toLowerCase() === raw ||
                              `${option.code} - ${option.label}`.toLowerCase() === raw,
                          );
                          if (match && match.code !== e.target.value) {
                            setForm((f) => ({ ...f, categorie_prof: match.code }));
                          }
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="M1, OS2, OP2B, 3A..."
                      />
                      {selectedClassification ? (
                        <p className="mt-1 text-xs text-blue-700">
                          {selectedClassification.family}
                          {selectedClassification.group ? ` | Groupe ${selectedClassification.group}` : ""}
                          {selectedClassification.description ? ` | ${selectedClassification.description}` : ""}
                        </p>
                      ) : (
                        <p className="mt-1 text-xs text-gray-500">Code libre autorisé si non présent dans les suggestions.</p>
                      )}
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Type de Régime</label>
                      <select value={form.type_regime_id} onChange={(e) => handleTypeRegimeChange(Number(e.target.value))} className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        {typeRegimes.map((regime) => (
                          <option key={regime.id} value={regime.id}>{regime.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Salaire de Base</label>
                      <input type="number" value={form.salaire_base} onChange={e => setForm(f => ({ ...f, salaire_base: +e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg font-bold text-blue-600" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">VHM</label>
                        <input type="number" value={form.vhm} readOnly className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-500" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Horaires Hebdo</label>
                        <input type="number" value={form.horaire_hebdo} onChange={e => setForm(f => ({ ...f, horaire_hebdo: +e.target.value }))} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => setBankModalOpen(true)}
                  className="w-full flex items-center justify-center gap-3 py-4 bg-white border-2 border-dashed border-blue-200 text-blue-600 rounded-2xl font-bold hover:bg-blue-50 hover:border-blue-400 transition-all group"
                >
                  <CurrencyDollarIcon className="h-6 w-6" />
                  <span>COORDONNÉES BANCAIRES</span>
                </button>

                {/* --- ADVANCED / OVERRIDES --- */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="bg-amber-50 p-6 rounded-3xl border border-amber-100 flex flex-col gap-5">
                    <h4 className="text-sm font-black text-amber-800 uppercase tracking-widest flex items-center gap-2">Avantages en Nature</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-black text-amber-600 uppercase mb-1">Véhicule</label>
                        <input type="number" value={form.avantage_vehicule} onChange={e => setForm(f => ({ ...f, avantage_vehicule: +e.target.value }))} className="w-full px-3 py-2 bg-white border border-amber-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-amber-600 uppercase mb-1">Logement</label>
                        <input type="number" value={form.avantage_logement} onChange={e => setForm(f => ({ ...f, avantage_logement: +e.target.value }))} className="w-full px-3 py-2 bg-white border border-amber-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-amber-600 uppercase mb-1">Téléphone</label>
                        <input type="number" value={form.avantage_telephone} onChange={e => setForm(f => ({ ...f, avantage_telephone: +e.target.value }))} className="w-full px-3 py-2 bg-white border border-amber-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-amber-600 uppercase mb-1">Autres</label>
                        <input type="number" value={form.avantage_autres} onChange={e => setForm(f => ({ ...f, avantage_autres: +e.target.value }))} className="w-full px-3 py-2 bg-white border border-amber-200 rounded-xl text-sm" />
                      </div>
                    </div>
                  </div>
                  <div className="bg-indigo-50 p-6 rounded-3xl border border-indigo-100 flex flex-col gap-5">
                    <h4 className="text-sm font-black text-indigo-800 uppercase tracking-widest">Surcharges de Taux</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-black text-indigo-400 uppercase mb-1">CNaPS Sal. (%)</label>
                        <input type="number" step="0.1" value={form.taux_sal_cnaps_override ?? ""} onChange={e => setForm(f => ({ ...f, taux_sal_cnaps_override: e.target.value === "" ? null : +e.target.value }))} className="w-full px-3 py-2 bg-white border border-indigo-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-indigo-400 uppercase mb-1">SMIE Sal. (%)</label>
                        <input type="number" step="0.1" value={form.taux_sal_smie_override ?? ""} onChange={e => setForm(f => ({ ...f, taux_sal_smie_override: e.target.value === "" ? null : +e.target.value }))} className="w-full px-3 py-2 bg-white border border-indigo-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-indigo-400 uppercase mb-1">CNaPS Pat. (%)</label>
                        <input type="number" step="0.1" value={form.taux_pat_cnaps_override ?? ""} onChange={e => setForm(f => ({ ...f, taux_pat_cnaps_override: e.target.value === "" ? null : +e.target.value }))} className="w-full px-3 py-2 bg-white border border-indigo-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-indigo-400 uppercase mb-1">SMIE Pat. (%)</label>
                        <input type="number" step="0.1" value={form.taux_pat_smie_override ?? ""} onChange={e => setForm(f => ({ ...f, taux_pat_smie_override: e.target.value === "" ? null : +e.target.value }))} className="w-full px-3 py-2 bg-white border border-indigo-200 rounded-xl text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-indigo-400 uppercase mb-1">FMFP Pat. (%)</label>
                        <input type="number" step="0.1" value={form.taux_pat_fmfp_override ?? ""} onChange={e => setForm(f => ({ ...f, taux_pat_fmfp_override: e.target.value === "" ? null : +e.target.value }))} className="w-full px-3 py-2 bg-white border border-indigo-200 rounded-xl text-sm" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Historique & Sortie */}
                {editingWorker && (
                  <div className="pt-10 border-t-2 border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-10">
                    <div>
                      <h3 className="text-lg font-black text-slate-800 mb-6 flex items-center gap-2">Historique</h3>
                      <div className="space-y-4">
                        {editingWorker.position_history?.map((h) => (
                          <div key={h.id} className="p-4 bg-white rounded-2xl border border-slate-100 flex justify-between items-center group">
                            <div>
                              <p className="font-bold text-slate-700">{h.poste}</p>
                              <p className="text-xs text-slate-400 font-medium">
                                {h.start_date ? new Date(h.start_date).toLocaleDateString() : "-"}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="bg-red-50/50 p-6 rounded-3xl border border-red-100 flex flex-col gap-6">
                      <h3 className="text-lg font-black text-red-800">Clôture de Contrat</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[10px] font-black text-red-400 uppercase mb-1">Date Débauche</label>
                          <input type="date" value={form.date_debauche} onChange={e => setForm(f => ({ ...f, date_debauche: e.target.value }))} className="w-full px-3 py-2 bg-white border border-red-100 rounded-xl" />
                        </div>
                        <div>
                          <label className="block text-[10px] font-black text-red-400 uppercase mb-1">Type de rupture</label>
                          <select value={form.type_sortie} onChange={e => setForm(f => ({ ...f, type_sortie: e.target.value }))} className="w-full px-3 py-2 bg-white border border-red-100 rounded-xl">
                            <option value="L">Licenciement</option>
                            <option value="D">Démission</option>
                            <option value="RC">Rupture Conv.</option>
                          </select>
                        </div>
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-red-400 uppercase mb-1">Groupe de Préavis (1-5)</label>
                        <select value={form.groupe_preavis} onChange={e => setForm(f => ({ ...f, groupe_preavis: +e.target.value }))} className="w-full px-3 py-2 bg-white border border-red-100 rounded-xl">
                          <option value={1}>Groupe 1</option>
                          <option value={2}>Groupe 2</option>
                          <option value={3}>Groupe 3</option>
                          <option value={4}>Groupe 4</option>
                          <option value={5}>Groupe 5</option>
                        </select>
                      </div>
                      <div className="p-4 bg-white/60 rounded-2xl border border-red-100 flex flex-col gap-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-400 font-black uppercase">Préavis Légal :</span>
                          <span className="text-red-600 font-black italic">{legalNotice} Jours</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-400 text-xs font-black uppercase">Solde Préavis :</span>
                          <span className="text-red-700 text-lg font-black">{noticeBalance} Jours</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* --- BANK DETAILS MODAL --- */}
            <Dialog
              open={bankModalOpen}
              onClose={() => setBankModalOpen(false)}
              className="relative z-[60]"
            >
              <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" />
              <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden border border-slate-100">
                  <div className="bg-slate-50 px-8 py-6 border-b border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-600 rounded-xl">
                        <CurrencyDollarIcon className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <Dialog.Title className="text-xl font-black text-slate-800 uppercase tracking-tight">Banque Salarié</Dialog.Title>
                        <p className="text-slate-500 text-xs font-medium">Coordonnées bancaires et RIB du travailleur</p>
                      </div>
                    </div>
                    <button onClick={() => setBankModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                      <XMarkIcon className="h-6 w-6" />
                    </button>
                  </div>

                  <div className="p-8 space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-[10px] font-black text-blue-600 uppercase tracking-widest mb-2">Nom de la Banque</label>
                        <input type="text" value={form.banque} onChange={e => setForm(f => ({ ...f, banque: e.target.value }))} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-blue-500 transition-all font-semibold" placeholder="ex: BNI, BTM..." />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black text-blue-600 uppercase tracking-widest mb-2">BIC / SWIFT</label>
                        <input type="text" value={form.bic} onChange={e => setForm(f => ({ ...f, bic: e.target.value.toUpperCase() }))} className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-blue-500 transition-all font-mono font-bold" placeholder="XXXXXXXX" />
                      </div>
                    </div>

                    <div className="bg-slate-50 p-6 rounded-3xl border border-slate-100">
                      <div className="flex items-center gap-2 mb-6">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-pulse"></span>
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Détails du RIB (Calcul Automatique)</h4>
                      </div>
                      <div className="grid grid-cols-4 gap-4">
                        <div className="col-span-1">
                          <label className="block text-[9px] font-black text-slate-400 uppercase mb-2 text-center">Banque</label>
                          <input type="text" maxLength={5} value={form.code_banque} onChange={e => setForm(f => ({ ...f, code_banque: e.target.value.replace(/\D/g, '') }))} className="w-full text-center py-3 bg-white border border-slate-100 rounded-xl font-mono font-black text-blue-600 text-lg shadow-sm" placeholder="00000" />
                        </div>
                        <div className="col-span-1">
                          <label className="block text-[9px] font-black text-slate-400 uppercase mb-2 text-center">Guichet</label>
                          <input type="text" maxLength={5} value={form.code_guichet} onChange={e => setForm(f => ({ ...f, code_guichet: e.target.value.replace(/\D/g, '') }))} className="w-full text-center py-3 bg-white border border-slate-100 rounded-xl font-mono font-black text-blue-600 text-lg shadow-sm" placeholder="00000" />
                        </div>
                        <div className="col-span-1">
                          <label className="block text-[9px] font-black text-slate-400 uppercase mb-2 text-center">Compte</label>
                          <input type="text" maxLength={11} value={form.compte_num} onChange={e => setForm(f => ({ ...f, compte_num: e.target.value.toUpperCase() }))} className="w-full text-center py-3 bg-white border border-slate-100 rounded-xl font-mono font-black text-blue-600 text-lg shadow-sm" placeholder="XXXXXXXXXXX" />
                        </div>
                        <div className="col-span-1">
                          <label className="block text-[9px] font-black text-slate-400 uppercase mb-2 text-center">Clé</label>
                          <input type="text" readOnly value={form.cle_rib} className="w-full text-center py-3 bg-blue-600 border-none rounded-xl font-mono font-black text-white text-lg shadow-lg shadow-blue-200" placeholder="00" />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-50 px-8 py-6 border-t border-slate-100 flex justify-end">
                    <button
                      onClick={() => setBankModalOpen(false)}
                      className="px-12 py-4 bg-blue-600 text-white rounded-2xl font-black shadow-xl shadow-blue-100 hover:bg-blue-700 hover:-translate-y-1 transition-all active:scale-95"
                    >
                      TERMINER
                    </button>
                  </div>
                </Dialog.Panel>
              </div>
            </Dialog>

            {/* Footer */}
            <div className="p-8 bg-white border-t border-slate-100 flex items-center justify-between sticky bottom-0 z-50 rounded-b-4xl">
              <button onClick={() => setOpenModal(false)} className="px-8 py-3 text-slate-400 font-bold hover:text-slate-600 transition-all uppercase tracking-widest text-xs">
                Annuler
              </button>
              <div className="flex gap-4">
                <button onClick={() => {
                  if (editingWorker) {
                    updateWorker.mutate();
                  } else {
                    create.mutate();
                  }
                }} disabled={create.isPending || updateWorker.isPending} className="px-10 py-4 bg-blue-600 text-white rounded-2xl font-black shadow-2xl shadow-blue-200 hover:bg-blue-700 hover:-translate-y-1 transition-all flex items-center gap-3 disabled:bg-slate-300 disabled:shadow-none">
                  {(create.isPending || updateWorker.isPending) ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <PlusIcon className="h-5 w-5" />}
                  {editingWorker ? "METTRE À JOUR" : "VALIDER L'INSCRIPTION"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Workers List */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden print:hidden">
        {/* List Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <UserIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                Liste des Travailleurs
              </h2>
              <p className="text-gray-600 text-sm mt-1">
                Gérer tous les travailleurs enregistrés
              </p>
            </div>
          </div>
          </div>
        </div>

        {/* Bulk Selection Header */}
        {workers.length > 0 && canDeleteWorkers && (
          <div className="px-6 py-2 bg-gray-50 border-b border-gray-200 flex items-center gap-3">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              checked={workers.length > 0 && selectedIds.size === workers.length}
              onChange={toggleSelectAll}
              id="select-all-workers"
            />
            <label htmlFor="select-all-workers" className="text-sm text-gray-600 font-medium cursor-pointer">
              Tout sélectionner ({selectedIds.size} sélectionné{selectedIds.size > 1 ? 's' : ''})
            </label>
          </div>
        )}

        {/* List Content */}
        <div className="p-6">
          {workersLoading ? (
            <div className="grid gap-4">
              {[...Array(6)].map((_, index) => (
                <div key={index} className="rounded-2xl border border-gray-200 bg-white p-4">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-12 w-12 rounded-xl" />
                    <div className="flex-1 space-y-3">
                      <Skeleton className="h-5 w-48" />
                      <Skeleton className="h-4 w-full max-w-xl" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : workers.length === 0 ? (
            <div className="text-center py-12">
              <UserIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Aucun travailleur
              </h3>
              <p className="text-gray-600 mb-6">
                Commencez par ajouter votre premier travailleur au système.
              </p>
              {canWriteWorkforce ? (
                <button
                  onClick={() => setOpenModal(true)}
                  className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors font-medium"
                >
                  <PlusIcon className="h-5 w-5" />
                  Ajouter un travailleur
                </button>
              ) : null}
            </div>
          ) : (
            <div className="grid gap-4">
              {workers.map((worker) => (
                <div
                  key={worker.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-center gap-4 flex-1">
                    {/* Checkbox */}
                    {canDeleteWorkers ? (
                      <div className="flex-shrink-0">
                        <input
                          type="checkbox"
                          className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          checked={selectedIds.has(worker.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleSelection(worker.id);
                          }}
                        />
                      </div>
                    ) : null}

                    {/* Avatar */}
                    <div className="flex-shrink-0">
                      <div className="h-12 w-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center text-white font-semibold text-sm">
                        {getInitials(worker.prenom, worker.nom)}
                      </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <div className="truncate">
                          <WorkerCanonicalSummary worker={worker} />
                        </div>
                        <div className="flex items-center gap-2">
                          {isHomonym(worker) && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200">
                              <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                              Homonyme
                            </span>
                          )}
                        </div>
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border ${getSecteurColor(worker.type_regime_id ?? 0)}`}>
                          <span className={`h-2 w-2 rounded-full ${getSecteurDot(worker.type_regime_id ?? 0)}`}></span>
                          {getSecteurLabel(worker.type_regime_id ?? 0)}
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <CurrencyDollarIcon className="h-4 w-4" />
                          <span>Base: {formatCurrency(Number(worker.salaire_base || 0))}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <ClockIcon className="h-4 w-4" />
                          <span>Horaire: {worker.horaire_hebdo}h/semaine</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <TagIcon className="h-4 w-4" />
                          <span>VHM: {formatCurrency(Number(worker.vhm || 0))}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                    <button
                      onClick={() => navigate(`/employee-360?employer_id=${worker.employer_id}&worker_id=${worker.id}`)}
                      className="p-2 text-gray-400 hover:text-cyan-600 hover:bg-cyan-50 rounded-lg transition-colors"
                      title="Dossier permanent RH"
                    >
                      <IdentificationIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleOpenDocument(worker)}
                      className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                      title="Documents administratifs"
                    >
                      <DocumentTextIcon className="h-5 w-5" />
                    </button>
                    {canWriteWorkforce ? (
                      <button
                        onClick={() => {
                          setEditingWorker(worker);
                          setForm({
                          employer_id: worker.employer_id || (employers.length > 0 ? employers[0].id : 1),
                          matricule: worker.matricule || "",
                          nom: worker.nom || "",
                          prenom: worker.prenom || "",
                          sexe: worker.sexe || "",
                          situation_familiale: worker.situation_familiale || "",
                          date_naissance: worker.date_naissance || "",
                          lieu_naissance: worker.lieu_naissance || "",
                          adresse: worker.adresse || "",
                          telephone: worker.telephone || "",
                          email: worker.email || "",
                          cin: worker.cin || "",
                          cin_delivre_le: worker.cin_delivre_le || "",
                          cin_lieu: worker.cin_lieu || "",
                          cnaps_num: worker.cnaps_num || "",
                          nombre_enfant: worker.nombre_enfant != null ? String(worker.nombre_enfant) : "",
                          date_embauche: worker.date_embauche || "",
                          nature_contrat: worker.nature_contrat || "CDI",
                          duree_essai_jours: worker.duree_essai_jours || 0,
                          date_fin_essai: worker.date_fin_essai || "",
                          etablissement: worker.etablissement || "",
                          departement: worker.departement || "",
                          service: worker.service || "",
                          unite: worker.unite || "",
                          organizational_unit_id: worker.organizational_unit_id || null,
                          indice: worker.indice || "",
                          valeur_point: worker.valeur_point || 0,
                          secteur: worker.secteur || "",
                          mode_paiement: worker.mode_paiement || "",
                          rib: worker.rib || "",
                          banque: worker.banque || "",
                          bic: worker.bic || "",
                          categorie_prof: worker.categorie_prof || "",
                          poste: worker.poste || "",
                          date_debauche: worker.date_debauche || "",
                          type_sortie: worker.type_sortie || "L",
                          groupe_preavis: worker.groupe_preavis || 1,
                          jours_preavis_deja_faits: worker.jours_preavis_deja_faits || 0,
                          type_regime_id: worker.type_regime_id || (typeRegimes.length > 0 ? typeRegimes[0].id : 1),
                          salaire_base: worker.salaire_base || 0,
                          salaire_horaire: worker.salaire_horaire || 0,
                          vhm: worker.vhm || 200,
                          horaire_hebdo: worker.horaire_hebdo || 46,
                          avantage_vehicule: worker.avantage_vehicule || 0,
                          avantage_logement: worker.avantage_logement || 0,
                          avantage_telephone: worker.avantage_telephone || 0,
                          avantage_autres: worker.avantage_autres || 0,
                          taux_sal_cnaps_override: worker.taux_sal_cnaps_override ?? null,
                          taux_sal_smie_override: worker.taux_sal_smie_override ?? null,
                          taux_pat_cnaps_override: worker.taux_pat_cnaps_override ?? null,
                          taux_pat_smie_override: worker.taux_pat_smie_override ?? null,
                          taux_pat_fmfp_override: worker.taux_pat_fmfp_override ?? null,
                          solde_conge_initial: worker.solde_conge_initial || 0,
                          code_banque: worker.code_banque || "",
                          code_guichet: worker.code_guichet || "",
                          compte_num: worker.compte_num || "",
                          cle_rib: worker.cle_rib || "",
                          nom_guichet: worker.nom_guichet || ""
                        });
                        setOrganizationalSelection(
                          worker.organizational_unit_id
                            ? { unite: worker.organizational_unit_id }
                            : {}
                        );
                          setOpenModal(true);
                        }}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Modifier"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>
                    ) : null}
                    {canDeleteWorkers ? (
                      <button
                        onClick={() => {
                          if (window.confirm(`Êtes-vous sûr de vouloir désactiver ${worker.prenom} ${worker.nom} ?`)) {
                            deleteWorker.mutate(worker.id);
                          }
                        }}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Désactiver"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
          {!workersLoading && totalPages > 1 ? (
            <div className="mt-6 flex flex-col gap-3 border-t border-gray-200 pt-6 text-sm text-gray-600 md:flex-row md:items-center md:justify-between">
              <div>
                Affichage de {(page - 1) * pageSize + 1} à {Math.min(page * pageSize, totalWorkers)} sur {totalWorkers} salariés
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page === 1}
                  className="rounded-xl border border-gray-300 px-4 py-2 font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Précédent
                </button>
                <div className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white">
                  {page} / {totalPages}
                </div>
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={page >= totalPages}
                  className="rounded-xl border border-gray-300 px-4 py-2 font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Suivant
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
      <Dialog
        open={resetModalOpen}
        onClose={() => {
          if (resetWorkers.isPending) return;
          setResetModalOpen(false);
        }}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/40" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-xl rounded-2xl bg-white shadow-2xl">
            <div className="border-b border-gray-200 px-6 py-4">
              <Dialog.Title className="text-lg font-semibold text-gray-900">
                Réinitialiser les employés
              </Dialog.Title>
              <p className="mt-2 text-sm text-gray-600">
                Action réservée aux administrateurs. Le mode soft désactive les employés. Le mode hard purge les données employé dans l'ordre sécurisé.
              </p>
            </div>
            <div className="space-y-5 px-6 py-5">
              <div className="grid gap-3 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setResetMode("soft")}
                  className={`rounded-xl border px-4 py-3 text-left transition ${resetMode === "soft" ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"}`}
                >
                  <div className="font-semibold">Soft reset</div>
                  <div className="mt-1 text-sm">Désactive tous les employés du périmètre sélectionné.</div>
                </button>
                <button
                  type="button"
                  onClick={() => setResetMode("hard")}
                  className={`rounded-xl border px-4 py-3 text-left transition ${resetMode === "hard" ? "border-red-500 bg-red-50 text-red-700" : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"}`}
                >
                  <div className="font-semibold">Hard reset</div>
                  <div className="mt-1 text-sm">Suppression définitive admin only avec purge contrôlée des dépendances.</div>
                </button>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                <div className="font-medium text-gray-900">Périmètre</div>
                <div className="mt-1">
                  {selectedEmployerFilter === "all"
                    ? "Tous les employeurs visibles"
                    : `Employeur ID ${selectedEmployerFilter}`}
                </div>
                <div className="mt-2">
                  Texte attendu: <span className="font-mono text-xs">{resetConfirmationExpected}</span>
                </div>
              </div>
              <div>
                <label htmlFor="reset-confirmation" className="block text-sm font-medium text-gray-700">
                  Confirmation obligatoire
                </label>
                <input
                  id="reset-confirmation"
                  type="text"
                  value={resetConfirmationText}
                  onChange={(e) => {
                    setResetConfirmationText(e.target.value);
                    if (resetFeedback) {
                      setResetFeedback(null);
                    }
                  }}
                  placeholder={resetConfirmationExpected}
                  className="mt-2 block w-full rounded-xl border border-gray-300 px-4 py-3 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                />
              </div>
              {resetFeedback ? (
                <div className={`rounded-xl border px-4 py-3 text-sm ${resetFeedback.type === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-green-200 bg-green-50 text-green-700"}`}>
                  {resetFeedback.message}
                </div>
              ) : null}
              {resetMode === "hard" ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  Le hard reset supprime définitivement les travailleurs et leurs dépendances employé. Utiliser uniquement pour une purge contrôlée.
                </div>
              ) : (
                <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
                  Le soft reset conserve l'historique et retire les employés des listes actives.
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
              <button
                type="button"
                onClick={() => {
                  setResetModalOpen(false);
                  setResetConfirmationText("");
                  setResetMode("soft");
                  setResetFeedback(null);
                }}
                disabled={resetWorkers.isPending}
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={handleResetSubmit}
                disabled={resetWorkers.isPending}
                className={`rounded-xl px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-50 ${resetMode === "hard" ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"}`}
              >
                {resetWorkers.isPending ? "Réinitialisation..." : resetMode === "hard" ? "Lancer le hard reset" : "Lancer le soft reset"}
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
      {/* NEW: DOCUMENT MODAL */}
      <Dialog
        open={documentModalOpen}
        onClose={() => setDocumentModalOpen(false)}
        className="relative z-50"
      >
        {/* Fullscreen backdrop */}
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

        {/* Fullscreen container for centering */}
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-5xl h-[90vh] bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col print:shadow-none print:rounded-none print:h-auto print:overflow-visible print:bg-white print:max-w-none print:w-full">

            {/* Header with Switcher - Hidden on Print */}
            <div className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center flex-shrink-0 print:hidden">
              <Dialog.Title className="text-lg font-bold text-gray-900">
                Documents Administratifs - {selectedDocumentWorkerData?.prenom || selectedDocumentWorker?.prenom} {selectedDocumentWorkerData?.nom || selectedDocumentWorker?.nom}
              </Dialog.Title>

              {/* Document Switcher */}
              <div className="flex bg-gray-100 p-1 rounded-lg">
                <button
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${documentType === 'attestation' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                  onClick={() => setDocumentType('attestation')}
                >
                  Attestation d'Emploi
                </button>
                <button
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${documentType === 'certificate' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                  onClick={() => setDocumentType('certificate')}
                  disabled={!selectedDocumentWorker?.date_debauche}
                  title={!selectedDocumentWorker?.date_debauche ? "Disponible uniquement pour les salariés débauchés" : ""}
                >
                  Certificat de Travail
                  {!selectedDocumentWorker?.date_debauche && <span className="ml-2 text-xs text-gray-400">(N/A)</span>}
                </button>
                <button
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${documentType === 'contract' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                  onClick={() => setDocumentType('contract')}
                >
                  Contrat de Travail
                </button>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setDocumentModalOpen(false)}
                  className="text-gray-400 hover:text-gray-500 p-2"
                >
                  <span className="sr-only">Fermer</span>
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-auto bg-gray-100 p-4 print:bg-white print:p-0 print:overflow-visible">
              {selectedDocumentWorker && (
                <>
                  {(() => {
                    const currentEmployer = employers.find(e => e.id === selectedDocumentWorker.employer_id) || employers[0];
                    if (!currentEmployer) {
                      return null;
                    }
                    return (
                      <>
                        {documentType === 'attestation' && (
                          <EmploymentAttestation
                            worker={selectedDocumentWorker}
                            employer={currentEmployer}
                            onClose={() => setDocumentModalOpen(false)}
                          />
                        )}
                        {documentType === 'certificate' && (
                          <WorkCertificate
                            worker={selectedDocumentWorker}
                            employer={currentEmployer}
                            onClose={() => setDocumentModalOpen(false)}
                          />
                        )}
                        {documentType === 'contract' && (
                          <EmploymentContract
                            worker={selectedDocumentWorker}
                            employer={currentEmployer}
                            onClose={() => setDocumentModalOpen(false)}
                          />
                        )}
                      </>
                    );
                  })()}
                </>
              )}
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
      <ImportWorkersDialog
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
      />
    </div>
  );
}
