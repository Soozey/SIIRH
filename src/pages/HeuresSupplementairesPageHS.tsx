import React, { useState, useEffect } from "react";
import { calculateHSBackendHS, getAllHSCalculationsHS } from "../api";

// Type d'une ligne "jour HS"
type JourHS = {
  date_HS: string;
  type_jour_HS: string;
  entree_HS: string;
  sortie_HS: string;
  type_nuit_HS: string;
};

// Type du résultat renvoyé par l'API backend HS
type HSResult = {
  id_HS: number;
  worker_id_HS: number;
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

const HeuresSupplementairesPageHS: React.FC = () => {
  const [workerIdHS, setWorkerIdHS] = useState<number>(1);
  const [moisHS, setMoisHS] = useState<string>("2025-07");
  const [baseHebdoHS, setBaseHebdoHS] = useState<number>(40);

  const [joursHS, setJoursHS] = useState<JourHS[]>([
    {
      date_HS: "2025-07-28",
      type_jour_HS: "N",
      entree_HS: "08:00",
      sortie_HS: "18:00",
      type_nuit_HS: "O",
    },
  ]);

  const [resultatHS, setResultatHS] = useState<HSResult | null>(null);
  const [loadingHS, setLoadingHS] = useState<boolean>(false);
  const [errorHS, setErrorHS] = useState<string | null>(null);

  const [historiqueHS, setHistoriqueHS] = useState<HSResult[]>([]);
  const [loadingHistoriqueHS, setLoadingHistoriqueHS] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"calcul" | "historique">("calcul");

  const handleJourChangeHS = (
    index: number,
    field: keyof JourHS,
    value: string
  ) => {
    const copie = [...joursHS];
    copie[index] = { ...copie[index], [field]: value };
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
        type_nuit_HS: "",
      },
    ]);
  };

  const handleRemoveRowHS = (index: number) => {
    if (joursHS.length > 1) {
      setJoursHS((prev) => prev.filter((_, i) => i !== index));
    }
  };

  const loadHistoriqueHS = async () => {
    try {
      setLoadingHistoriqueHS(true);
      const data: HSResult[] = await getAllHSCalculationsHS();
      setHistoriqueHS(data);
    } catch (err) {
      console.error("Erreur lors du chargement de l'historique HS :", err);
    } finally {
      setLoadingHistoriqueHS(false);
    }
  };

  useEffect(() => {
    loadHistoriqueHS();
  }, []);

  const handleSubmitHS = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoadingHS(true);
    setErrorHS(null);
    setResultatHS(null);

    try {
      const payloadHS = {
        worker_id_HS: Number(workerIdHS),
        mois_HS: moisHS,
        base_hebdo_heures_HS: Number(baseHebdoHS),
        jours_HS: joursHS.map((j) => ({
          date_HS: j.date_HS,
          type_jour_HS: j.type_jour_HS || "N",
          entree_HS: j.entree_HS,
          sortie_HS: j.sortie_HS,
          type_nuit_HS: j.type_nuit_HS || null,
        })),
      };

      const res: HSResult = await calculateHSBackendHS(payloadHS);
      setResultatHS(res);
      await loadHistoriqueHS();
      setActiveTab("historique");
    } catch (err) {
      console.error(err);
      setErrorHS("Erreur lors du calcul des heures supplémentaires.");
    } finally {
      setLoadingHS(false);
    }
  };

  const getTypeJourLabel = (type: string) => {
    switch (type) {
      case "N": return "Normal";
      case "JF": return "Jour Férié";
      default: return type;
    }
  };

  const getTypeNuitLabel = (type: string) => {
    switch (type) {
      case "H": return "Habituelle";
      case "O": return "Occasionnelle";
      case "": return "Aucune";
      default: return type;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Calcul des Heures Supplémentaires
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Générez et consultez les calculs d'heures supplémentaires avec les majorations applicables
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-xl shadow-sm mb-8">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab("calcul")}
                className={`flex-1 py-4 px-6 text-center font-medium text-sm transition-colors ${
                  activeTab === "calcul"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  Nouveau Calcul
                </div>
              </button>
              <button
                onClick={() => setActiveTab("historique")}
                className={`flex-1 py-4 px-6 text-center font-medium text-sm transition-colors ${
                  activeTab === "historique"
                    ? "border-b-2 border-blue-500 text-blue-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Historique
                </div>
              </button>
            </nav>
          </div>

          <div className="p-6">
            {/* Tab Content - Calcul */}
            {activeTab === "calcul" && (
              <div className="space-y-6">
                <form onSubmit={handleSubmitHS} className="space-y-6">
                  {/* Informations de base */}
                  <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl p-6 text-white">
                    <h3 className="text-xl font-semibold mb-4">Informations de base</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2 opacity-90">
                          ID Salarié
                        </label>
                        <input
                          type="number"
                          value={workerIdHS}
                          onChange={(e) => setWorkerIdHS(Number(e.target.value))}
                          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:outline-none focus:ring-2 focus:ring-white/50 text-white placeholder-white/70"
                          placeholder="Ex: 123"
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
                  </div>

                  {/* Tableau des jours */}
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-gray-900">Plannings des jours</h3>
                      <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                        {joursHS.length} jour(s)
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Date
                            </th>
                            <th className="px-4 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Type de Jour
                            </th>
                            <th className="px-4 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Heure d'Entrée
                            </th>
                            <th className="px-4 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Heure de Sortie
                            </th>
                            <th className="px-4 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Travail de Nuit
                            </th>
                            <th className="px-4 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Actions
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {joursHS.map((jour, index) => (
                            <tr key={index} className="hover:bg-gray-50 transition-colors">
                              <td className="px-4 py-4 whitespace-nowrap">
                                <input
                                  type="date"
                                  value={jour.date_HS}
                                  onChange={(e) =>
                                    handleJourChangeHS(index, "date_HS", e.target.value)
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                                />
                              </td>
                              <td className="px-4 py-4 whitespace-nowrap">
                                <select
                                  value={jour.type_jour_HS}
                                  onChange={(e) =>
                                    handleJourChangeHS(index, "type_jour_HS", e.target.value)
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                                >
                                  <option value="N">🟢 Normal</option>
                                  <option value="JF">🔴 Jour Férié</option>
                                </select>
                              </td>
                              <td className="px-4 py-4 whitespace-nowrap">
                                <input
                                  type="time"
                                  value={jour.entree_HS}
                                  onChange={(e) =>
                                    handleJourChangeHS(index, "entree_HS", e.target.value)
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                                />
                              </td>
                              <td className="px-4 py-4 whitespace-nowrap">
                                <input
                                  type="time"
                                  value={jour.sortie_HS}
                                  onChange={(e) =>
                                    handleJourChangeHS(index, "sortie_HS", e.target.value)
                                  }
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                                />
                              </td>
                              <td className="px-4 py-4 whitespace-nowrap">
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
                              <td className="px-4 py-4 whitespace-nowrap">
                                <button
                                  type="button"
                                  onClick={() => handleRemoveRowHS(index)}
                                  disabled={joursHS.length === 1}
                                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                  Supprimer
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Boutons d'action */}
                  <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
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
                      type="submit"
                      disabled={loadingHS}
                      className="px-8 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 shadow-lg flex items-center gap-2"
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

                {/* Messages d'erreur */}
                {errorHS && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
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
                  <div className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-2xl border border-green-200 p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold text-gray-900">
                        🎉 Calcul terminé avec succès
                      </h3>
                      <span className="px-3 py-1 bg-green-500 text-white text-sm rounded-full font-medium">
                        ID: {resultatHS.id_HS}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600 mb-6">
                      Calcul effectué le {new Date(resultatHS.created_at_HS).toLocaleString('fr-FR')}
                    </p>

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
                        <div key={index} className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
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
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">Historique des calculs</h3>
                    <p className="text-gray-600 mt-1">
                      Consultez l'ensemble des calculs d'heures supplémentaires
                    </p>
                  </div>
                  <button
                    onClick={loadHistoriqueHS}
                    disabled={loadingHistoriqueHS}
                    className="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 transition-colors flex items-center gap-2"
                  >
                    <svg className={`w-5 h-5 ${loadingHistoriqueHS ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {loadingHistoriqueHS ? "Chargement..." : "Rafraîchir"}
                  </button>
                </div>

                {loadingHistoriqueHS ? (
                  <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                  </div>
                ) : historiqueHS.length === 0 ? (
                  <div className="text-center py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-4 text-lg font-medium text-gray-900">Aucun calcul</h3>
                    <p className="mt-2 text-gray-500">
                      Aucun calcul d'heures supplémentaires n'a été enregistré pour le moment.
                    </p>
                  </div>
                ) : (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Détails
                            </th>
                            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Période
                            </th>
                            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Heures Majorées
                            </th>
                            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                              Date
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {historiqueHS.map((h) => (
                            <tr key={h.id_HS} className="hover:bg-gray-50 transition-colors">
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div>
                                  <p className="text-sm font-medium text-gray-900">
                                    Salarié #{h.worker_id_HS}
                                  </p>
                                  <p className="text-sm text-gray-500">
                                    Base: {h.base_hebdo_heures_HS}h/semaine
                                  </p>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full font-medium">
                                  {h.mois_HS}
                                </span>
                              </td>
                              <td className="px-6 py-4">
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  <div className="text-gray-600">HSNI 130%:</div>
                                  <div className="font-medium">{h.total_HSNI_130_heures_HS.toFixed(2)}h</div>
                                  <div className="text-gray-600">HSNI 150%:</div>
                                  <div className="font-medium">{h.total_HSNI_150_heures_HS.toFixed(2)}h</div>
                                  <div className="text-gray-600">HMNH 30%:</div>
                                  <div className="font-medium">{h.total_HMNH_30_heures_HS.toFixed(2)}h</div>
                                  <div className="text-gray-600">HMJF 50%:</div>
                                  <div className="font-medium">{h.total_HMJF_50_heures_HS.toFixed(2)}h</div>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {new Date(h.created_at_HS).toLocaleDateString('fr-FR')}
                                <br />
                                <span className="text-gray-400">
                                  {new Date(h.created_at_HS).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                                </span>
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
    </div>
  );
};

export default HeuresSupplementairesPageHS;