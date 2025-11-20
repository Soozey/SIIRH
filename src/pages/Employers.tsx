import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { useMemo, useState } from "react";
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
  type_etab: "general" | "scolaire";
  taux_pat_cnaps: number;
  taux_pat_smie: number;
  type_regime_id: number | null;
  type_regime?: TypeRegime;
};

export default function Employers() {
  const qc = useQueryClient();
  
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
  const [form, setForm] = useState({
    raison_sociale: "",
    type_etab: "general" as "general" | "scolaire",
    taux_pat_cnaps: 13,
    taux_pat_smie: 0,
    type_regime_id: typeRegimes?.[0]?.id || 1,
  });

  const [showForm, setShowForm] = useState(false);

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
    mutationFn: async () => (await api.post("/employers", form)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["employers"] });
      setForm({
        raison_sociale: "",
        type_etab: "general",
        taux_pat_cnaps: 13,
        taux_pat_smie: 0,
        type_regime_id: typeRegimes?.[0]?.id || 1,
      });
      setShowForm(false);
    },
  });

  // Handlers
  const handleChangeTypeEtab = (value: "general" | "scolaire") => {
    setForm((f) => ({
      ...f,
      type_etab: value,
      taux_pat_cnaps: value === "general" ? 13 : 8,
    }));
  };

  const handleChangeTypeRegime = (regimeId: number) => {
    setForm((f) => ({ ...f, type_regime_id: regimeId }));
  };

  const setField = (key: keyof typeof form, val: any) =>
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
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold shadow-lg transition-all duration-200 hover:shadow-xl transform hover:-translate-y-0.5"
            >
              <PlusIcon className="h-5 w-5" />
              Nouvel Employeur
            </button>
          )}
        </div>

        {/* Formulaire */}
        {showForm && (
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 mb-8 overflow-hidden">
            <div className="border-b border-gray-200 p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <BuildingOfficeIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    Nouvel Employeur
                  </h2>
                  <p className="text-gray-600 text-sm mt-1">
                    Ajouter un nouvel employeur au système
                  </p>
                </div>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                create.mutate();
              }}
              className="p-6"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

                {/* Type établissement */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Type d'établissement
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => handleChangeTypeEtab("general")}
                      className={`p-4 border-2 rounded-xl text-left transition-all duration-200 ${
                        form.type_etab === "general"
                          ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <BuildingStorefrontIcon className={`h-6 w-6 mb-2 ${
                        form.type_etab === "general" ? "text-blue-600" : "text-gray-400"
                      }`} />
                      <div className="font-medium text-gray-900">Général</div>
                      <div className="text-sm text-gray-600 mt-1">Taux CNaPS: 13%</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleChangeTypeEtab("scolaire")}
                      className={`p-4 border-2 rounded-xl text-left transition-all duration-200 ${
                        form.type_etab === "scolaire"
                          ? "border-purple-500 bg-purple-50 ring-2 ring-purple-200"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <AcademicCapIcon className={`h-6 w-6 mb-2 ${
                        form.type_etab === "scolaire" ? "text-purple-600" : "text-gray-400"
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

                {/* Taux SMIE */}
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
                      value={form.taux_pat_smie}
                      onChange={(e) => setField("taux_pat_smie", +e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                </div>
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
                  disabled={create.isPending || !form.raison_sociale}
                  className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-xl font-medium transition-colors"
                >
                  {create.isPending ? (
                    <>
                      <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Création...
                    </>
                  ) : (
                    <>
                      <PlusIcon className="h-5 w-5" />
                      Enregistrer
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-6 py-3 border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-xl font-medium transition-colors"
                >
                  Annuler
                </button>
              </div>
            </form>
          </div>
        )}

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
                            <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                              <PencilIcon className="h-4 w-4" />
                            </button>
                            <button className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>

                        {/* Détails */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                          <div className="flex items-center gap-2 text-gray-600">
                            <ChartBarIcon className="h-4 w-4" />
                            <span><strong>CNaPS:</strong> {employer.taux_pat_cnaps}%</span>
                          </div>
                          {employer.taux_pat_smie > 0 && (
                            <div className="flex items-center gap-2 text-gray-600">
                              <CurrencyDollarIcon className="h-4 w-4" />
                              <span><strong>SMIE:</strong> {employer.taux_pat_smie}%</span>
                            </div>
                          )}
                          {employer.type_regime && (
                            <div className="flex items-center gap-2 text-gray-600">
                              <IdentificationIcon className="h-4 w-4" />
                              <span><strong>VHM:</strong> {employer.type_regime.vhm}</span>
                            </div>
                          )}
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
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 px-6 py-3 rounded-xl font-medium transition-colors"
              >
                <PlusIcon className="h-5 w-5" />
                Ajouter un employeur
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}