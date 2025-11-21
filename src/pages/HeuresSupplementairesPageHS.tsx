import React, { useState } from "react";
import { calculateHSBackendHS } from "../api";

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
  worker_id_HS: number;
  mois_HS: string;
  total_HSNI_130_heures_HS: number;
  total_HSI_130_heures_HS: number;
  total_HSNI_150_heures_HS: number;
  total_HSI_150_heures_HS: number;
  total_HMNH_30_heures_HS: number;
  total_HMNO_50_heures_HS: number;
  total_HMD_40_heures_HS: number;
  total_HMJF_50_heures_HS: number;
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
    setJoursHS((prev) => prev.filter((_, i) => i !== index));
  };

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
    } catch (err) {
      console.error(err);
      setErrorHS("Erreur lors de l'appel au backend HS.");
    } finally {
      setLoadingHS(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">
            Calcul des Heures Supplémentaires & Majorations (Module HS)
          </h2>

          <form onSubmit={handleSubmitHS} className="space-y-6">
            {/* Informations de base */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Worker ID HS
                </label>
                <input
                  type="number"
                  value={workerIdHS}
                  onChange={(e) => setWorkerIdHS(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Mois HS (YYYY-MM)
                </label>
                <input
                  type="text"
                  value={moisHS}
                  onChange={(e) => setMoisHS(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="2025-07"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Base hebdo (heures) HS
                </label>
                <input
                  type="number"
                  value={baseHebdoHS}
                  onChange={(e) => setBaseHebdoHS(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Tableau des jours HS */}
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-800">Jours HS</h3>
              </div>
              
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date HS
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Type jour HS
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Entrée HS
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Sortie HS
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Type nuit HS
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {joursHS.map((j, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <input
                            type="date"
                            value={j.date_HS}
                            onChange={(e) =>
                              handleJourChangeHS(index, "date_HS", e.target.value)
                            }
                            className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <select
                            value={j.type_jour_HS}
                            onChange={(e) =>
                              handleJourChangeHS(index, "type_jour_HS", e.target.value)
                            }
                            className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            <option value="N">N (Normal)</option>
                            <option value="JF">JF (Jour Férié)</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <input
                            type="time"
                            value={j.entree_HS}
                            onChange={(e) =>
                              handleJourChangeHS(index, "entree_HS", e.target.value)
                            }
                            className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <input
                            type="time"
                            value={j.sortie_HS}
                            onChange={(e) =>
                              handleJourChangeHS(index, "sortie_HS", e.target.value)
                            }
                            className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <select
                            value={j.type_nuit_HS}
                            onChange={(e) =>
                              handleJourChangeHS(index, "type_nuit_HS", e.target.value)
                            }
                            className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            <option value="">(Aucune)</option>
                            <option value="H">H (Habituelle)</option>
                            <option value="O">O (Occasionnelle)</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => handleRemoveRowHS(index)}
                            className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 transition-colors"
                          >
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
            <div className="flex flex-col sm:flex-row gap-3 justify-between">
              <button
                type="button"
                onClick={handleAddRowHS}
                className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
              >
                + Ajouter un jour HS
              </button>
              
              <button
                type="submit"
                disabled={loadingHS}
                className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loadingHS ? "Calcul en cours..." : "Calculer les HS"}
              </button>
            </div>
          </form>

          {/* Messages d'erreur */}
          {errorHS && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-700">{errorHS}</p>
            </div>
          )}

          {/* Résultats */}
          {resultatHS && (
            <div className="mt-8 bg-green-50 rounded-lg border border-green-200 p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">
                Résultat HS (heures décimales)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HSNI 130% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HSNI_130_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HSI 130% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HSI_130_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HSNI 150% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HSNI_150_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HSI 150% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HSI_150_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HMNH 30% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HMNH_30_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HMNO 50% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HMNO_50_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HMD 40% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HMD_40_heures_HS.toFixed(2)} h
                  </p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="text-sm text-gray-600">HMJF 50% HS</p>
                  <p className="text-lg font-semibold text-gray-800">
                    {resultatHS.total_HMJF_50_heures_HS.toFixed(2)} h
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HeuresSupplementairesPageHS;