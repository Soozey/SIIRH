import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, updateEmployer, deleteEmployer } from "../api";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import HierarchicalOrganizationTree from "../components/HierarchicalOrganizationTreeFinal";
import { useAuth } from "../contexts/AuthContext";
import { hasModulePermission, sessionHasRole } from "../rbac";
import {
  PlusIcon,
  BuildingOfficeIcon,
  AcademicCapIcon,
  TruckIcon,
  BuildingStorefrontIcon,
  PencilIcon,
  TrashIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  IdentificationIcon
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
  adresse?: string;
  cnaps_num?: string;
  type_etab: "general" | "scolaire";
  taux_pat_cnaps: number;
  plafond_cnaps_base: number;
  taux_sal_smie: number;
  taux_pat_smie: number;
  plafond_smie: number;
  logo_path?: string;
  type_regime_id: number | null;
  type_regime?: TypeRegime;
  // SME
  sm_embauche?: number;
  nif?: string;
  stat?: string;
  representant?: string;
  rep_date_naissance?: string;
  rep_cin_num?: string;
  rep_cin_date?: string;
  rep_cin_lieu?: string;
  rep_adresse?: string;
  rep_fonction?: string;
  // Organizational lists
  etablissements?: string[];
  departements?: string[];
  services?: string[];
  unites?: string[];
};

type EmployerForm = {
  raison_sociale: string;
  adresse: string;
  cnaps_num: string;
  type_etab: "general" | "scolaire";
  taux_pat_cnaps: number;
  plafond_cnaps_base: number;
  taux_sal_smie: number;
  taux_pat_smie: number;
  plafond_smie: number;
  logo_path: string;
  type_regime_id: number;
  sm_embauche: number;
  nif: string;
  stat: string;
  representant: string;
  rep_date_naissance: string | null;
  rep_cin_num: string;
  rep_cin_date: string | null;
  rep_cin_lieu: string;
  rep_adresse: string;
  rep_fonction: string;
  etablissements: string[];
  departements: string[];
  services: string[];
  unites: string[];
};

export default function Employers() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { session } = useAuth();
  const isInspector = sessionHasRole(session, ["inspecteur", "inspection_travail", "labor_inspector", "labor_inspector_supervisor"]);
  const canWriteWorkforce = hasModulePermission(session, "workforce", "write") && !isInspector;

  // États pour les données
  const { data: employers, isLoading, error } = useQuery({
    queryKey: ["employers"],
    queryFn: async () => (await api.get("/employers")).data as Employer[],
  });

  const { data: typeRegimes } = useQuery({
    queryKey: ["typeRegimes"],
    queryFn: async () => (await api.get("/type_regimes")).data as TypeRegime[],
  });

  // État du formulaire
  const initialFormState: EmployerForm = {
    raison_sociale: "",
    adresse: "",
    cnaps_num: "",
    type_etab: "general" as "general" | "scolaire",
    taux_pat_cnaps: 13,
    plafond_cnaps_base: 0,
    taux_sal_smie: 0,
    taux_pat_smie: 0,
    plafond_smie: 0,
    logo_path: "",
    type_regime_id: 1,
    // SME
    sm_embauche: 0,
    nif: "",
    stat: "",
    representant: "",
    rep_date_naissance: "",
    rep_cin_num: "",
    rep_cin_date: "",
    rep_cin_lieu: "",
    rep_adresse: "",
    rep_fonction: "",
    // Organizational lists
    etablissements: [] as string[],
    departements: [] as string[],
    services: [] as string[],
    unites: [] as string[],
  };

  const [form, setForm] = useState<EmployerForm>(initialFormState);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [repModalOpen, setRepModalOpen] = useState(false);
  // const [logoFile, setLogoFile] = useState<File | null>(null); // Unused for now

  const extractErrorMessage = (error: unknown, fallback: string): string => {
    if (!error || typeof error !== "object") {
      return fallback;
    }
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const maybeMessage = (error as { message?: string }).message;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (detail !== undefined) {
      return JSON.stringify(detail);
    }
    if (typeof maybeMessage === "string" && maybeMessage.trim()) {
      return maybeMessage;
    }
    return fallback;
  };

  // Trouver le type de régime sélectionné pour l'aperçu VHM
  const selectedTypeRegime = useMemo(() => {
    return typeRegimes?.find(regime => regime.id === form.type_regime_id);
  }, [form.type_regime_id, typeRegimes]);

  // Calcul de la VHM basé sur le type de régime sélectionné
  const vhmPreview = useMemo(
    () => selectedTypeRegime?.vhm || 0,
    [selectedTypeRegime]
  );

  // Mutation pour créer un employeur
  const create = useMutation({
    mutationFn: async () => (await api.post("/employers", cleanFormData(form))).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employers"] });
      resetForm();
    },
    onError: (error: unknown) => {
      alert(`Erreur lors de la création: ${extractErrorMessage(error, "Erreur inconnue")}`);
    }
  });

  // Mutation pour mettre à jour
  const update = useMutation({
    mutationFn: async () => {
      return await updateEmployer(editingId!, cleanFormData(form));
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employers"] });
      resetForm();
    },
    onError: (error: unknown) => {
      console.error("Erreur complète:", error);
      const responseData = typeof error === "object" && error !== null && "response" in error
        ? (error as { response?: { data?: unknown } }).response?.data
        : undefined;
      console.error("Response data:", responseData);
      console.error("Form data:", form);

      alert(`Erreur lors de la modification: ${extractErrorMessage(error, "Erreur inconnue")}`);
    }
  });

  // Mutation pour supprimer
  const remove = useMutation({
    mutationFn: async (id: number) => await deleteEmployer(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employers"] });
    },
    onError: (error: unknown) => {
      alert(`Erreur lors de la suppression: ${extractErrorMessage(error, "Erreur inconnue")}`);
    }
  });

  const resetForm = () => {
    setForm({
      raison_sociale: "",
      adresse: "",
      cnaps_num: "",
      type_etab: "general",
      taux_pat_cnaps: 13,
      plafond_cnaps_base: 0,
      taux_sal_smie: 0,
      taux_pat_smie: 0,
      plafond_smie: 0,
      logo_path: "",
      type_regime_id: typeRegimes?.[0]?.id || 1,
      // SME
      sm_embauche: 0,
      nif: "",
      stat: "",
      representant: "",
      rep_date_naissance: "",
      rep_cin_num: "",
      rep_cin_date: "",
      rep_cin_lieu: "",
      rep_adresse: "",
      rep_fonction: "",
      // Organizational lists
      etablissements: [],
      departements: [],
      services: [],
      unites: [],
    });
    setEditingId(null);
    setShowForm(false);
    // setLogoFile(null); // Unused
  }

  const openCanonicalOrganizationView = (employerId: number) => {
    navigate(`/organization?employer_id=${employerId}&tab=0`);
  };

  // Fonction pour nettoyer les données avant l'envoi
  const cleanFormData = (formData: EmployerForm): EmployerForm => {
    const cleaned = { ...formData };
    
    // Convertir les chaînes vides en null pour les champs de date
    if (cleaned.rep_date_naissance === "") {
      cleaned.rep_date_naissance = null;
    }
    if (cleaned.rep_cin_date === "") {
      cleaned.rep_cin_date = null;
    }
    
    return cleaned;
  };

  const handleEdit = (employer: Employer) => {
    setEditingId(employer.id);
    setForm({
      raison_sociale: employer.raison_sociale,
      adresse: employer.adresse || "",
      cnaps_num: employer.cnaps_num || "",
      type_etab: employer.type_etab,
      taux_pat_cnaps: employer.taux_pat_cnaps,
      plafond_cnaps_base: employer.plafond_cnaps_base || 0,
      taux_sal_smie: employer.taux_sal_smie || 0,
      taux_pat_smie: employer.taux_pat_smie,
      plafond_smie: employer.plafond_smie || 0,
      logo_path: employer.logo_path || "",
      type_regime_id: employer.type_regime_id || (typeRegimes?.[0]?.id || 1),
      sm_embauche: employer.sm_embauche || 0,
      nif: employer.nif || "",
      stat: employer.stat || "",
      representant: employer.representant || "",
      rep_date_naissance: employer.rep_date_naissance || "",
      rep_cin_num: employer.rep_cin_num || "",
      rep_cin_date: employer.rep_cin_date || "",
      rep_cin_lieu: employer.rep_cin_lieu || "",
      rep_adresse: employer.rep_adresse || "",
      rep_fonction: employer.rep_fonction || "",
      // Organizational lists - ensure they are arrays of strings
      etablissements: Array.isArray(employer.etablissements) ? employer.etablissements : [],
      departements: Array.isArray(employer.departements) ? employer.departements : [],
      services: Array.isArray(employer.services) ? employer.services : [],
      unites: Array.isArray(employer.unites) ? employer.unites : [],
    });
    setShowForm(true);
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (id: number) => {
    if (confirm("Êtes-vous sûr de vouloir supprimer cet employeur ?")) {
      remove.mutate(id);
    }
  };

  const handleChangeTypeEtab = (value: "general" | "scolaire") => {
    setForm((f) => ({
      ...f,
      type_etab: value,
      taux_pat_cnaps: value === "general" ? 13 : 8,
    }));
  };

  const handleChangeTypeRegime = (regimeId: number) => {
    if (editingId) {
      const originalEmp = employers?.find(e => e.id === editingId);
      if (originalEmp && originalEmp.type_regime_id !== regimeId) {
        const confirmed = confirm(
          "ATTENTION : Changement de Régime détecté !\n\n" +
          "Cette action va modifier la VHM et le salaire horaire de TOUS les salariés liés.\n" +
          "C'est une décision structurante qui relève de la hiérarchie compétente.\n\n" +
          "Êtes-vous certain de vouloir procéder à ce changement ?"
        );
        if (!confirmed) return;
      }
    }
    setForm((f) => ({ ...f, type_regime_id: regimeId }));
  };

  const setField = <K extends keyof EmployerForm>(key: K, val: EmployerForm[K]) =>
    setForm((f) => ({ ...f, [key]: val }));

  const getTypeEtabIcon = (type: "general" | "scolaire") => {
    return type === "scolaire" ? AcademicCapIcon : BuildingStorefrontIcon;
  };

  const getTypeEtabColor = (type: "general" | "scolaire") => {
    return type === "scolaire"
      ? "bg-purple-100 text-purple-800 border-purple-200"
      : "bg-blue-100 text-blue-800 border-blue-200";
  };

  const getRegimeColor = (code: string) => {
    return code === "agricole"
      ? "bg-green-100 text-green-800 border-green-200"
      : "bg-orange-100 text-orange-800 border-orange-200";
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Gestion des Employeurs
          </h1>
          <p className="text-lg text-gray-600 mb-6">
            Gérez vos établissements et leurs paramètres
          </p>

          {/* Bouton d'ajout */}
          {!showForm && canWriteWorkforce && (
            <button
              onClick={() => {
                resetForm();
                setShowForm(true);
              }}
              className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold shadow-lg transition-all duration-200 hover:shadow-xl transform hover:-translate-y-0.5"
            >
              <PlusIcon className="h-5 w-5" />
              Nouvel Employeur
            </button>
          )}
        </div>

        {/* Formulaire */}
        {showForm && canWriteWorkforce && (
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 mb-8 overflow-hidden">
            <div className="border-b border-gray-200 p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {editingId ? "Modifier l'Employeur" : "Nouvel Employeur"}
                  </h2>
                  <p className="text-gray-600 text-sm mt-1">
                    {editingId ? "Modifier les informations de l'employeur" : "Ajouter un nouvel employeur au système"}
                  </p>
                </div>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (editingId) {
                  update.mutate();
                } else {
                  create.mutate();
                }
              }}
              className="p-6"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-slate-900">
                {/* Raison sociale */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Raison sociale
                  </label>
                  <input
                    type="text"
                    value={form.raison_sociale}
                    onChange={(e) => setField("raison_sociale", e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Entrez la raison sociale"
                    required
                  />
                </div>

                {/* Adresse */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Adresse
                  </label>
                  <input
                    type="text"
                    value={form.adresse}
                    onChange={(e) => setField("adresse", e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Adresse complète de l'employeur"
                  />
                </div>

                {/* Numéro CNaPS */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Numéro CNaPS
                  </label>
                  <input
                    type="text"
                    value={form.cnaps_num}
                    onChange={(e) => setField("cnaps_num", e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Ex: 123456789"
                  />
                </div>

                {/* NIF */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    NIF
                  </label>
                  <input
                    type="text"
                    value={form.nif}
                    onChange={(e) => setField("nif", e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Numéro d'Identification Fiscale"
                  />
                </div>

                {/* STAT */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    STAT
                  </label>
                  <input
                    type="text"
                    value={form.stat}
                    onChange={(e) => setField("stat", e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Numéro Statistique"
                  />
                </div>

                {/* Représentant */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Représentant
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={form.representant}
                      onChange={(e) => setField("representant", e.target.value)}
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors bg-gray-50"
                      placeholder="Nom du représentant légal"
                      readOnly
                    />
                    <button
                      type="button"
                      onClick={() => setRepModalOpen(true)}
                      className="px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 rounded-xl font-medium transition-colors flex items-center gap-2"
                    >
                      <IdentificationIcon className="h-5 w-5" />
                      Détails complets
                    </button>
                  </div>
                </div>

                {/* Logo Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Logo de l'entreprise
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (file && editingId) {
                        const formData = new FormData();
                        formData.append("file", file);
                        try {
                          const res = await api.post(`/employers/${editingId}/logo`, formData, {
                            headers: { "Content-Type": "multipart/form-data" }
                          });
                          setField("logo_path", res.data.logo_path);
                          alert("Logo uploadé avec succès!");
                        } catch (error: unknown) {
                          alert(`Erreur lors de l'upload: ${extractErrorMessage(error, "Erreur inconnue")}`);
                        }
                      } else if (file) {
                        // setLogoFile(file); // Unused
                      }
                    }}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  />
                  {form.logo_path && (
                    <p className="text-xs text-green-600 mt-1">Logo actuel: {form.logo_path}</p>
                  )}
                </div>

                {/* Type établissement */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Type d'établissement
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => handleChangeTypeEtab("general")}
                      className={`p-4 border-2 rounded-xl text-left transition-all duration-200 ${form.type_etab === "general"
                        ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                        : "border-gray-200 hover:border-gray-300"
                        }`}
                    >
                      <BuildingStorefrontIcon className={`h-6 w-6 mb-2 ${form.type_etab === "general" ? "text-blue-600" : "text-gray-400"
                        }`} />
                      <div className="font-medium text-gray-900">Général</div>
                      <div className="text-sm text-gray-600 mt-1">Taux CNaPS: 13%</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleChangeTypeEtab("scolaire")}
                      className={`p-4 border-2 rounded-xl text-left transition-all duration-200 ${form.type_etab === "scolaire"
                        ? "border-purple-500 bg-purple-50 ring-2 ring-purple-200"
                        : "border-gray-200 hover:border-gray-300"
                        }`}
                    >
                      <AcademicCapIcon className={`h-6 w-6 mb-2 ${form.type_etab === "scolaire" ? "text-purple-600" : "text-gray-400"
                        }`} />
                      <div className="font-medium text-gray-900">Scolaire</div>
                      <div className="text-sm text-gray-600 mt-1">Taux CNaPS: 8%</div>
                    </button>
                  </div>
                </div>

                {/* Type régime */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Type de régime
                  </label>
                  <select
                    value={form.type_regime_id}
                    onChange={(e) => handleChangeTypeRegime(Number(e.target.value))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  >
                    {typeRegimes?.map((regime) => (
                      <option key={regime.id} value={regime.id}>
                        {regime.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Taux CNaPS */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Taux patronal CNaPS (%)
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <ChartBarIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.taux_pat_cnaps}
                      onChange={(e) => setField("taux_pat_cnaps", +e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Auto: {form.type_etab === "general" ? "13%" : "8%"} selon le type
                  </p>
                </div>

                {/* Plafond CNaPS Base */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Plafond CNaPS (Base)
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.plafond_cnaps_base}
                      onChange={(e) => setField("plafond_cnaps_base", +e.target.value)}
                      placeholder="0 = Automatique (8 x SME)"
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Laissez à 0 pour utiliser le calcul automatique (8 x SME)
                  </p>
                </div>

                {/* Paramètres SMIE */}
                <div className="md:col-span-2 rounded-xl border border-blue-100 bg-blue-50/70 p-4">
                  <h3 className="mb-4 text-sm font-semibold text-blue-900">Paramètres SMIE</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Taux salarié SMIE (%)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                        </div>
                        <input
                          type="number"
                          step="0.01"
                          value={form.taux_sal_smie}
                          onChange={(e) => setField("taux_sal_smie", +e.target.value)}
                          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                        />
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        Part salariale retenue sur le bulletin.
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Taux patronal SMIE (%)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                        </div>
                        <input
                          type="number"
                          step="0.01"
                          value={form.taux_pat_smie}
                          onChange={(e) => setField("taux_pat_smie", +e.target.value)}
                          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Plafond SMIE (Ar)
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                        </div>
                        <input
                          type="number"
                          value={form.plafond_smie}
                          onChange={(e) => setField("plafond_smie", +e.target.value)}
                          placeholder="Laissez à 0 pour utiliser le Brut"
                          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                        />
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        Laissez à 0 pour utiliser le Brut
                      </p>
                    </div>
                  </div>
                </div>

                {/* SME */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    SME (Salaire Min. Embauche)
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.sm_embauche}
                      onChange={(e) => setField("sm_embauche", +e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Utilisé dans la constante SME
                  </p>
                </div>
              </div>

              {/* Hierarchical Organizational Structure Section */}
              <div className="mt-8 p-6 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-green-900 flex items-center gap-2">
                    <BuildingOfficeIcon className="h-6 w-6" />
                    Hiérarchie Organisationnelle
                  </h3>
                  {editingId && (
                    <button
                      type="button"
                      onClick={() => openCanonicalOrganizationView(editingId)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      Gérer la Hiérarchie
                    </button>
                  )}
                </div>
                
                <p className="text-green-700 mb-6">
                  Définissez la structure hiérarchique de votre organisation avec des relations parent-enfant.
                  Cette structure sera utilisée pour le filtrage en cascade dans tous les formulaires.
                </p>
                
                {/* Aperçu de la hiérarchie */}
                {editingId ? (
                  <div className="bg-white rounded-lg p-4 border border-green-200">
                    <h4 className="font-medium text-gray-900 mb-3">Aperçu de la hiérarchie actuelle :</h4>
                    <HierarchicalOrganizationTree employerId={editingId} readonly />
                  </div>
                ) : (
                  <div className="bg-white rounded-lg p-4 border border-green-200 text-center text-gray-500">
                    <BuildingOfficeIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>Sélectionnez un employeur pour voir sa hiérarchie organisationnelle.</p>
                  </div>
                )}
              </div>





              {/* Aperçu VHM */}
              <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
                  <div>
                    <h3 className="text-lg font-semibold text-blue-900 mb-2">
                      Valeur Horaire Moyenne (VHM)
                    </h3>
                    <p className="text-blue-700">
                      {selectedTypeRegime
                        ? `${selectedTypeRegime.label} → VHM = ${selectedTypeRegime.vhm}`
                        : "Sélectionnez un type de régime"
                      }
                    </p>
                  </div>
                  <div>
                    <div className="relative">
                      <input
                        type="text"
                        value={vhmPreview}
                        readOnly
                        className="w-full px-4 py-3 bg-white border border-blue-300 rounded-xl text-blue-600 font-semibold text-lg text-center"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <CurrencyDollarIcon className="h-5 w-5 text-blue-500" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6 pt-6 border-t border-gray-200">
                <button
                  type="submit"
                  disabled={create.isPending || update.isPending || !form.raison_sociale}
                  className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-xl font-medium transition-colors"
                >
                  {create.isPending || update.isPending ? (
                    <>
                      <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      {editingId ? "Modification..." : "Création..."}
                    </>
                  ) : (
                    <>
                      <PlusIcon className="h-5 w-5" />
                      {editingId ? "Mettre à jour" : "Enregistrer"}
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-3 border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-xl font-medium transition-colors"
                >
                  Annuler
                </button>
              </div>
            </form>
          </div>
        )
        }

        {/* Liste des employeurs */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Liste des Employeurs
            </h2>
            <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
              {employers?.length || 0} employeur(s)
            </span>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6">
              Erreur lors du chargement des données
            </div>
          )}

          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Chargement des employeurs...</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {(employers ?? []).map((employer: Employer) => {
                const TypeEtabIcon = getTypeEtabIcon(employer.type_etab);
                return (
                  <div
                    key={employer.id}
                    className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-lg transition-all duration-200 hover:border-blue-300"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex-1">
                        {/* Header avec nom et badges */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3 flex-wrap">
                            <h3 className="text-xl font-semibold text-gray-900">
                              {employer.raison_sociale}
                            </h3>
                            <div className="flex gap-2 flex-wrap">
                              <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border ${getTypeEtabColor(employer.type_etab)}`}>
                                <TypeEtabIcon className="h-3 w-3" />
                                {employer.type_etab === "scolaire" ? "Scolaire" : "Général"}
                              </span>
                              {employer.type_regime && (
                                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border ${getRegimeColor(employer.type_regime.code)}`}>
                                  <TruckIcon className="h-3 w-3" />
                                  {employer.type_regime.label}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <a
                              href={`/employers/${employer.id}/primes`}
                              className="p-2 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                              title="Gérer les Primes"
                            >
                              <CurrencyDollarIcon className="h-4 w-4" />
                            </a>

                            {canWriteWorkforce ? (
                              <>
                                <button
                                  onClick={() => handleEdit(employer)}
                                  className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                  title="Modifier"
                                >
                                  <PencilIcon className="h-4 w-4" />
                                </button>
                                <button
                                  onClick={() => handleDelete(employer.id)}
                                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                  title="Supprimer"
                                >
                                  <TrashIcon className="h-4 w-4" />
                                </button>
                              </>
                            ) : null}
                          </div>
                        </div>

                        {/* Détails */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mt-4">
                          <div className="flex items-center gap-2 text-gray-600">
                            <ChartBarIcon className="h-4 w-4" />
                            <span><strong>CNaPS:</strong> {employer.taux_pat_cnaps}%</span>
                          </div>
                          {((employer.taux_sal_smie || 0) > 0 || employer.taux_pat_smie > 0) && (
                            <div className="flex items-center gap-2 text-gray-600">
                              <CurrencyDollarIcon className="h-4 w-4" />
                              <span><strong>SMIE:</strong> Sal. {employer.taux_sal_smie || 0}% / Pat. {employer.taux_pat_smie}%</span>
                            </div>
                          )}
                          {employer.type_regime && (
                            <div className="flex items-center gap-2 text-gray-600">
                              <IdentificationIcon className="h-4 w-4" />
                              <span><strong>VHM:</strong> {employer.type_regime.vhm}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-2 text-gray-600">
                            <strong>NIF:</strong> {employer.nif || "-"}
                          </div>
                          <div className="flex items-center gap-2 text-gray-600">
                            <strong>STAT:</strong> {employer.stat || "-"}
                          </div>
                          <div className="flex items-center gap-2 text-gray-600">
                            <strong>Représentant:</strong> {employer.representant || "-"}
                          </div>
                        </div>
                      </div>

                      {/* ID */}
                      <div className="flex-shrink-0">
                        <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm font-medium border border-gray-200">
                          ID: {employer.id}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {(employers ?? []).length === 0 && !isLoading && (
            <div className="text-center py-16 bg-white rounded-2xl border border-gray-200">
              <BuildingOfficeIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Aucun employeur enregistré
              </h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                Commencez par ajouter votre premier employeur pour gérer vos établissements et leurs paramètres.
              </p>
              {canWriteWorkforce ? (
                <button
                  onClick={() => {
                    resetForm();
                    setShowForm(true);
                  }}
                  className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 px-6 py-3 rounded-xl font-medium transition-colors"
                >
                  <PlusIcon className="h-5 w-5" />
                  Ajouter un employeur
                </button>
              ) : null}
            </div>
          )}
        </div>

      </div >

      {/* Modal Représentant */}
      {repModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-[60] backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center bg-slate-50">
              <div className="flex items-center gap-3">
                <IdentificationIcon className="h-6 w-6 text-blue-600" />
                <h3 className="text-xl font-bold text-gray-900">Détails du Représentant</h3>
              </div>
              <button onClick={() => setRepModalOpen(false)} className="text-gray-400 hover:text-gray-600 transition-colors">
                <PlusIcon className="h-6 w-6 rotate-45" />
              </button>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Nom Complet</label>
                <input
                  type="text"
                  value={form.representant}
                  onChange={(e) => setField("representant", e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="NOM et Prénoms"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date de naissance</label>
                <input
                  type="date"
                  value={form.rep_date_naissance || ""}
                  onChange={(e) => setField("rep_date_naissance", e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fonction / Titre</label>
                <input
                  type="text"
                  value={form.rep_fonction}
                  onChange={(e) => setField("rep_fonction", e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="ex: Gérant, DRH..."
                />
              </div>
              <div className="md:col-span-2 border-t border-gray-100 pt-4 mt-2">
                <h4 className="font-semibold text-slate-800 text-sm mb-3">Informations CIN</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2 md:col-span-1">
                    <label className="block text-xs text-gray-500 mb-1">Numéro CIN</label>
                    <input
                      type="text"
                      value={form.rep_cin_num}
                      onChange={(e) => setField("rep_cin_num", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Délivré le</label>
                    <input
                      type="date"
                      value={form.rep_cin_date || ""}
                      onChange={(e) => setField("rep_cin_date", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-gray-500 mb-1">Lieu de délivrance</label>
                    <input
                      type="text"
                      value={form.rep_cin_lieu}
                      onChange={(e) => setField("rep_cin_lieu", e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
              <div className="md:col-span-2 border-t border-gray-100 pt-4 mt-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Adresse Personnelle</label>
                <input
                  type="text"
                  value={form.rep_adresse}
                  onChange={(e) => setField("rep_adresse", e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Adresse complète"
                />
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setRepModalOpen(false)}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-colors"
              >
                Terminer
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

