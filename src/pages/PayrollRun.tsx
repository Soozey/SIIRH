import { useState } from "react";
import { api } from "../api";
import { Link } from "react-router-dom";
import {
  DocumentTextIcon,
  CalendarIcon,
  UserIcon,
  EyeIcon,
  ArrowPathIcon,
  CurrencyDollarIcon,
  BuildingOfficeIcon,
  ClockIcon,
  ChartBarIcon
} from "@heroicons/react/24/outline";

// 🔹 Type adapté aux données renvoyées par /workers/{id}
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
  const [workerId, setWorkerId] = useState<number>(1);
  const [period, setPeriod] = useState<string>("2025-11");
  const [preview, setPreview] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // 🔹 Nouveau : infos du salarié
  const [worker, setWorker] = useState<Worker | null>(null);
  const [workerError, setWorkerError] = useState<string | null>(null);

  const load = async () => {
    setIsLoading(true);
    setWorkerError(null);

    try {
      // 1️⃣ Récupérer le worker à partir du worker_id
      try {
        const w = await api.get<Worker>(`/workers/${workerId}`);
        setWorker(w.data);
      } catch (err) {
        console.error("Erreur worker:", err);
        setWorker(null);
        setWorkerError("Impossible de récupérer le salarié (vérifie l'ID).");
      }

      // 2️⃣ Récupérer la prévisualisation du bulletin
      const r = await api.get(`/payroll/preview`, {
        params: { worker_id: workerId, period },
      });
      setPreview(r.data);
    } catch (error) {
      console.error("Erreur lors du chargement:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("fr-MG", {
      style: "currency",
      currency: "MGA",
    }).format(amount);
  };

  const formatPeriod = (period: string) => {
    const [year, month] = period.split("-");
    const monthNames = [
      "Janvier",
      "Février",
      "Mars",
      "Avril",
      "Mai",
      "Juin",
      "Juillet",
      "Août",
      "Septembre",
      "Octobre",
      "Novembre",
      "Décembre",
    ];
    return `${monthNames[parseInt(month) - 1]} ${year}`;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl p-6 mb-6 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
              <DocumentTextIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white">
                Gestion des Bulletins
              </h1>
              <p className="text-purple-100 mt-1">
                Prévisualisation et génération des bulletins de paie
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        {/* Formulaire de recherche */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            <ChartBarIcon className="h-6 w-6 text-blue-600" />
            Prévisualisation du Bulletin
          </h2>

          <div className="flex flex-col md:flex-row gap-4 items-start md:items-end">
            {/* Worker ID */}
            <div className="flex-1 min-w-0">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ID du Travailleur
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <UserIcon className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="number"
                  value={workerId}
                  onChange={(e) => setWorkerId(+e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="Entrez l'ID du travailleur"
                />
              </div>
            </div>

            {/* Période */}
            <div className="flex-1 min-w-0">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Période
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <CalendarIcon className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="month"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                />
              </div>
              {period && (
                <p className="text-sm text-gray-500 mt-2">
                  {formatPeriod(period)}
                </p>
              )}
            </div>

            {/* Bouton Charger */}
            <div className="w-full md:w-auto">
              <div className="h-6 mb-2 invisible">Label</div>
              <button
                onClick={load}
                disabled={isLoading}
                className="w-full md:w-auto min-w-[140px] inline-flex items-center justify-center gap-2 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-xl font-medium transition-all durée-200 hover:shadow-lg whitespace-nowrap"
              >
                {isLoading ? (
                  <>
                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                    Chargement...
                  </>
                ) : (
                  <>
                    <EyeIcon className="h-5 w-5" />
                    Prévisualiser
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Erreur worker */}
          {workerError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {workerError}
            </div>
          )}

          {/* Bouton Voir Bulletin */}
          {preview && (
            <div className="flex justify-end mt-6 pt-6 border-t border-gray-200">
              <Link
                to={`/payslip/${workerId}/${period}`}
                className="inline-flex items-center gap-2 bg-green-600 text-white hover:bg-green-700 px-6 py-3 rounded-xl font-medium transition-all durée-200 hover:shadow-lg"
              >
                <DocumentTextIcon className="h-5 w-5" />
                Voir le Bulletin Complet
              </Link>
            </div>
          )}
        </div>

        {/* Prévisualisation */}
        {preview && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            {/* Header de la prévisualisation */}
            <div className="border-b border-gray-200 p-6 bg-gradient-to-r from-gray-50 to-blue-50">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900 mb-2">
                    Prévisualisation du Bulletin
                  </h2>
                  <div className="flex flex-col gap-1 text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <UserIcon className="h-4 w-4" />
                      {worker ? (
                        <span>
                          {worker.prenom} {worker.nom} — Matricule :{" "}
                          <span className="font-medium">
                            {worker.matricule}
                          </span>
                        </span>
                      ) : (
                        <span>Travailleur ID: {workerId}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <CalendarIcon className="h-4 w-4" />
                      <span>Période: {formatPeriod(period)}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-2 md:mt-0">
                  <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                    <DocumentTextIcon className="h-4 w-4" />
                    Données de prévisualisation
                  </span>
                </div>
              </div>

              {/* 🔹 Petite fiche salarié sous le header */}
              {worker && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-800">
                  <div>
                    <p className="font-semibold text-gray-900">Coordonnées</p>
                    <p>{worker.adresse}</p>
                    <p>
                      Enfants :{" "}
                      <span className="font-medium">
                        {worker.nombre_enfant}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">
                      Données de travail
                    </p>
                    <p>
                      Horaire hebdo :{" "}
                      <span className="font-medium">
                        {worker.horaire_hebdo} h / semaine
                      </span>
                    </p>
                    <p>
                      VHM :{" "}
                      <span className="font-medium">
                        {worker.vhm.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">
                      Salaire de référence
                    </p>
                    <p>
                      Salaire base :{" "}
                      <span className="font-medium">
                        {worker.salaire_base.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                    <p>
                      Salaire horaire :{" "}
                      <span className="font-medium">
                        {worker.salaire_horaire.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Contenu de la prévisualisation */}
            <div className="p-6">
              {/* Résumé rapide */}
              {preview.salaire_net && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                    <CurrencyDollarIcon className="h-8 w-8 text-green-600 mx-auto mb-2" />
                    <div className="text-2xl font-bold text-green-700">
                      {formatCurrency(preview.salaire_net)}
                    </div>
                    <div className="text-sm text-green-600 font-medium">
                      Salaire Net
                    </div>
                  </div>

                  {preview.salaire_brut && (
                    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
                      <BuildingOfficeIcon className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                      <div className="text-xl font-bold text-blue-700">
                        {formatCurrency(preview.salaire_brut)}
                      </div>
                      <div className="text-sm text-blue-600 font-medium">
                        Salaire Brut
                      </div>
                    </div>
                  )}

                  {preview.total_heures_supp && (
                    <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 text-center">
                      <ClockIcon className="h-8 w-8 text-orange-600 mx-auto mb-2" />
                      <div className="text-xl font-bold text-orange-700">
                        {preview.total_heures_supp}h
                      </div>
                      <div className="text-sm text-orange-600 font-medium">
                        Heures Supp.
                      </div>
                    </div>
                  )}

                  {preview.total_primes && (
                    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 text-center">
                      <ChartBarIcon className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                      <div className="text-xl font-bold text-purple-700">
                        {formatCurrency(preview.total_primes)}
                      </div>
                      <div className="text-sm text-purple-600 font-medium">
                        Total Primes
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Données détaillées */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                  <h3 className="font-semibold text-gray-900">
                    Données détaillées du bulletin
                  </h3>
                </div>
                <pre className="p-4 bg-gray-900 text-green-400 text-sm overflow-x-auto max-h-96">
{JSON.stringify(
  preview,
  (key, value) => {
    if (
      typeof value === "number" &&
      (key.toLowerCase().includes("salaire") ||
        key.toLowerCase().includes("montant"))
    ) {
      return formatCurrency(value);
    }
    return value;
  },
  2
)}
                </pre>
              </div>

              {/* Informations */}
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <div className="flex items-start gap-3">
                  <DocumentTextIcon className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-medium text-blue-900 mb-1">
                      Informations sur la prévisualisation
                    </h4>
                    <p className="text-blue-700 text-sm">
                      Cette prévisualisation montre les données calculées pour
                      le bulletin de paie. Cliquez sur &quot;Voir le Bulletin
                      Complet&quot; pour accéder à la version formatée et
                      imprimable.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* État vide */}
        {!preview && !isLoading && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-12 text-center">
            <DocumentTextIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Aucune prévisualisation
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              Sélectionnez un travailleur et une période, puis cliquez sur
              &quot;Prévisualiser&quot; pour afficher les données du bulletin.
            </p>
            <div className="w-24 h-1 bg-gradient-to-r from-blue-500 to-purple-500 mx-auto rounded-full"></div>
          </div>
        )}
      </div>
    </div>
  );
}
