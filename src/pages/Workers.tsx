import { useState } from "react";
import { api } from "../api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  PlusIcon,
  UserIcon,
  BuildingOfficeIcon,
  PencilIcon,
  TrashIcon,
  BriefcaseIcon,
  CurrencyDollarIcon,
  ClockIcon,
  IdentificationIcon,
  TagIcon
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

export default function Workers() {
  const qc = useQueryClient();
  const [openModal, setOpenModal] = useState(false);

  const { data: employers = [] } = useQuery({
    queryKey: ["employers"],
    queryFn: async () => (await api.get("/employers")).data as Employer[]
  });

  const { data: typeRegimes = [] } = useQuery({
    queryKey: ["typeRegimes"],
    queryFn: async () => (await api.get("/type_regimes")).data as TypeRegime[]
  });

  const { data: workers = [] } = useQuery({
    queryKey: ["workers"],
    queryFn: async () => (await api.get("/workers")).data
  });

  const [form, setForm] = useState({
    employer_id: employers[0]?.id || 1,
    matricule: "",
    nom: "",
    prenom: "",
    adresse: "",
    nombre_enfant: "",
    type_regime_id: typeRegimes[0]?.id || 1, // Utilise type_regime_id au lieu de secteur
    salaire_base: 0,
    salaire_horaire: 0,
    vhm: typeRegimes[0]?.vhm || 200, // VHM basée sur le type de régime
    horaire_hebdo: 46
  });

  // Trouver le type de régime sélectionné
  const selectedTypeRegime = typeRegimes.find(regime => regime.id === form.type_regime_id);

  // Mettre à jour la VHM quand le type de régime change
  const handleTypeRegimeChange = (typeRegimeId: number) => {
    const selectedRegime = typeRegimes.find(regime => regime.id === typeRegimeId);
    setForm(f => ({
      ...f,
      type_regime_id: typeRegimeId,
      vhm: selectedRegime?.vhm || 200
    }));
  };

  const create = useMutation({
    mutationFn: async () => (await api.post("/workers", form)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workers"] });
      setOpenModal(false);
      setForm({
        employer_id: employers[0]?.id || 1,
        matricule: "",
        nom: "",
        prenom: "",
        adresse: "",
        nombre_enfant: "",
        type_regime_id: typeRegimes[0]?.id || 1,
        salaire_base: 0,
        salaire_horaire: 0,
        vhm: typeRegimes[0]?.vhm || 200,
        horaire_hebdo: 46
      });
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

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-MG', {
      style: 'currency',
      currency: 'MGA'
    }).format(amount);
  };

  const getInitials = (prenom: string, nom: string) => {
    return `${prenom?.[0] || ''}${nom?.[0] || ''}`.toUpperCase();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl p-6 mb-6 shadow-lg">
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
                {workers.length} travailleur(s) enregistré(s)
              </p>
            </div>
          </div>
          <button
            onClick={() => setOpenModal(true)}
            className="inline-flex items-center gap-2 bg-white text-blue-600 hover:bg-gray-50 px-6 py-3 rounded-xl font-semibold shadow-lg transition-all duration-200 hover:shadow-xl transform hover:-translate-y-0.5"
          >
            <PlusIcon className="h-5 w-5" />
            Nouveau Travailleur
          </button>
        </div>
      </div>

      {/* Modal */}
      {openModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="border-b border-gray-200 p-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <UserIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    Nouveau Travailleur
                  </h2>
                  <p className="text-gray-600 text-sm mt-1">
                    Ajouter un nouveau travailleur au système
                  </p>
                </div>
              </div>
            </div>

            {/* Form */}
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Employer Select */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Employeur
                  </label>
                  <select
                    value={form.employer_id}
                    onChange={(e) => setForm(f => ({ ...f, employer_id: Number(e.target.value) }))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  >
                    {employers.map((employer) => (
                      <option key={employer.id} value={employer.id}>
                        {employer.id} - {employer.raison_sociale}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Matricule */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Matricule
                  </label>
                  <input
                    type="text"
                    value={form.matricule}
                    onChange={e => setForm(f => ({ ...f, matricule: e.target.value }))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Entrez le matricule"
                  />
                </div>

                {/* Type Régime (remplace Secteur) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Type de Régime
                  </label>
                  <select
                    value={form.type_regime_id}
                    onChange={(e) => handleTypeRegimeChange(Number(e.target.value))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  >
                    {typeRegimes.map((regime) => (
                      <option key={regime.id} value={regime.id}>
                        {regime.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Nom */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nom
                  </label>
                  <input
                    type="text"
                    value={form.nom}
                    onChange={e => setForm(f => ({ ...f, nom: e.target.value }))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Entrez le nom"
                  />
                </div>

                {/* Prénom */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Prénom
                  </label>
                  <input
                    type="text"
                    value={form.prenom}
                    onChange={e => setForm(f => ({ ...f, prenom: e.target.value }))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Entrez le prénom"
                  />
                </div>

                {/* Adresse */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Adresse
                  </label>
                  <input
                    type="text"
                    value={form.adresse}
                    onChange={e => setForm(f => ({ ...f, adresse: e.target.value }))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Adresse"
                  />
                </div>

                {/* Nombre enfant */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nombre enfant
                  </label>
                  <input
                    type="number"
                    value={form.nombre_enfant}
                    onChange={e => setForm(f => ({ ...f, nombre_enfant: e.target.value }))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Nombre enfant"
                  />
                </div>

                {/* VHM (lecture seule) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Valeur Horaire Mensuelle (VHM)
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.vhm}
                      readOnly
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 bg-gray-50 rounded-xl text-gray-700"
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Basé sur le type de régime sélectionné
                  </p>
                </div>

                {/* Salaire de base */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Salaire de base
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.salaire_base}
                      onChange={e => setForm(f => ({ ...f, salaire_base: +e.target.value }))}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                </div>

                {/* Salaire horaire */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Salaire horaire
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.salaire_horaire}
                      onChange={e => setForm(f => ({ ...f, salaire_horaire: +e.target.value }))}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                </div>

                {/* Horaire hebdo */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Horaire hebdomadaire
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <ClockIcon className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="number"
                      value={form.horaire_hebdo}
                      onChange={e => setForm(f => ({ ...f, horaire_hebdo: +e.target.value }))}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    />
                  </div>
                </div>
              </div>

              {/* Aperçu du type de régime sélectionné */}
              {selectedTypeRegime && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-xl">
                  <div className="flex items-center gap-2">
                    <TagIcon className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium text-blue-800">
                      Régime sélectionné: <strong>{selectedTypeRegime.label}</strong> 
                      (VHM: {formatCurrency(selectedTypeRegime.vhm)})
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="border-t border-gray-200 p-6 bg-gray-50 rounded-b-2xl">
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setOpenModal(false)}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium"
                >
                  Annuler
                </button>
                <button
                  onClick={() => create.mutate()}
                  disabled={create.isPending}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium"
                >
                  {create.isPending ? (
                    <>
                      <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Création...
                    </>
                  ) : (
                    <>
                      <PlusIcon className="h-5 w-5" />
                      Créer le travailleur
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Workers List */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        {/* List Header */}
        <div className="border-b border-gray-200 p-6">
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

        {/* List Content */}
        <div className="p-6">
          {workers.length === 0 ? (
            <div className="text-center py-12">
              <UserIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Aucun travailleur
              </h3>
              <p className="text-gray-600 mb-6">
                Commencez par ajouter votre premier travailleur au système.
              </p>
              <button
                onClick={() => setOpenModal(true)}
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors font-medium"
              >
                <PlusIcon className="h-5 w-5" />
                Ajouter un travailleur
              </button>
            </div>
          ) : (
            <div className="grid gap-4">
              {workers.map((worker: any) => (
                <div
                  key={worker.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-center gap-4 flex-1">
                    {/* Avatar */}
                    <div className="flex-shrink-0">
                      <div className="h-12 w-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center text-white font-semibold text-sm">
                        {getInitials(worker.prenom, worker.nom)}
                      </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <h3 className="text-lg font-semibold text-gray-900 truncate">
                          {worker.prenom} {worker.nom}
                        </h3>
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border ${getSecteurColor(worker.type_regime_id)}`}>
                          <span className={`h-2 w-2 rounded-full ${getSecteurDot(worker.type_regime_id)}`}></span>
                          {getSecteurLabel(worker.type_regime_id)}
                        </span>
                      </div>
                      
                      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <IdentificationIcon className="h-4 w-4" />
                          <span>Matricule: {worker.matricule}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <CurrencyDollarIcon className="h-4 w-4" />
                          <span>Base: {formatCurrency(worker.salaire_base)}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <ClockIcon className="h-4 w-4" />
                          <span>Horaire: {worker.horaire_hebdo}h/semaine</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <TagIcon className="h-4 w-4" />
                          <span>VHM: {formatCurrency(worker.vhm)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                    <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}