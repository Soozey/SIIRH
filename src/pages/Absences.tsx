import React, { useState } from "react";
import { api } from "../api";
import WorkerSearchSelect from "../components/WorkerSearchSelect";

type AbsenceInput = {
  worker_id: number;           // ID du salarié
  salaire_base: number;
  salaire_horaire: number;
  ABSM_J: number;
  ABSM_H: number;
  ABSNR_J: number;
  ABSNR_H: number;
  ABSMP: number;
  ABS1_J: number;
  ABS1_H: number;
  ABS2_J: number;
  ABS2_H: number;
};

type AbsenceRubriqueResult = {
  code: string;
  label: string;
  unite: "jour" | "heure";
  nombre: number;
  base: number;
  montant_salarial: number;
};

type AbsenceCalculationResult = {
  salaire_journalier: number;
  salaire_horaire: number;
  rubriques: AbsenceRubriqueResult[];
  total_retenues_absence: number;
};

// 🔹 Adapté exactement à ton JSON /workers/{id}
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

const initialForm: AbsenceInput = {
  worker_id: 0,
  salaire_base: 0,
  salaire_horaire: 0,
  ABSM_J: 0,
  ABSM_H: 0,
  ABSNR_J: 0,
  ABSNR_H: 0,
  ABSMP: 0,
  ABS1_J: 0,
  ABS1_H: 0,
  ABS2_J: 0,
  ABS2_H: 0,
};

const Absences: React.FC = () => {
  const [form, setForm] = useState<AbsenceInput>(initialForm);
  const [result, setResult] = useState<AbsenceCalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [worker, setWorker] = useState<Worker | null>(null);
  const [workerLoading, setWorkerLoading] = useState(false);
  const [workerError, setWorkerError] = useState<string | null>(null);

  // 🔹 Quand on modifie un input numérique (y compris worker_id)
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value === "" ? 0 : Number(value),
    }));
  };

  // 🔹 Récupérer les infos d'un salarié à partir du worker_id
  const fetchWorker = async (id: number) => {
    if (!id || id <= 0) return;
    setWorkerLoading(true);
    setWorkerError(null);

    try {
      const response = await api.get<Worker>(`/workers/${id}`);
      const data = response.data;
      setWorker(data);

      // Pré-remplissage salaire_base et salaire_horaire si dispo
      setForm((prev) => ({
        ...prev,
        salaire_base: data.salaire_base ?? prev.salaire_base,
        salaire_horaire: data.salaire_horaire ?? prev.salaire_horaire,
      }));
    } catch (err) {
      console.error(err);
      setWorker(null);
      setWorkerError("Impossible de récupérer le salarié (vérifie l'ID).");
    } finally {
      setWorkerLoading(false);
    }
  };


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await api.post<AbsenceCalculationResult>("/absences/calcul", form);
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError("Erreur lors du calcul des absences.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setForm(initialForm);
    setResult(null);
    setError(null);
    setWorker(null);
    setWorkerError(null);
  };

  // Groupes de champs pour une meilleure organisation
  const fieldGroups = [
    {
      title: "Salarié",
      description: "Identification du salarié concerné par ces absences",
      fields: [
        {
          name: "worker_id",
          label: "ID du salarié (worker_id)",
          type: "number",
        },
      ],
    },
    {
      title: "Salaire de base",
      description: "Informations de rémunération de base",
      fields: [
        {
          name: "salaire_base",
          label: "Salaire de base mensuel (Ar)",
          type: "number",
        },
        {
          name: "salaire_horaire",
          label: "Salaire horaire (Ar)",
          type: "number",
        },
      ],
    },
    {
      title: "Absence maladie (informatif)",
      description: "Absences pour maladie (pas de retenue, info bulletin)",
      fields: [
        { name: "ABSM_J", label: "Jours d'absence maladie", type: "number" },
        { name: "ABSM_H", label: "Heures d'absence maladie", type: "number" },
      ],
    },
    {
      title: "Absence non rémunérée",
      description: "Absences non prises en charge (retenues en paie)",
      fields: [
        { name: "ABSNR_J", label: "Jours non rémunérés", type: "number" },
        { name: "ABSNR_H", label: "Heures non rémunérées", type: "number" },
      ],
    },
    {
      title: "Mise à pied & autres absences",
      description: "Autres types d'absences",
      fields: [
        { name: "ABSMP", label: "Jours de mise à pied", type: "number" },
        { name: "ABS1_J", label: "Autre absence 1 (jours)", type: "number" },
        { name: "ABS1_H", label: "Autre absence 1 (heures)", type: "number" },
        { name: "ABS2_J", label: "Autre absence 2 (jours)", type: "number" },
        { name: "ABS2_H", label: "Autre absence 2 (heures)", type: "number" },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">
            Calcul des Absences
          </h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Saisis l&apos;ID du salarié, récupère automatiquement ses infos, puis
            renseigne les absences pour calculer les retenues sur salaire.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Formulaire */}
          <div className="lg:col-span-2">
            <form
              onSubmit={handleSubmit}
              className="bg-white rounded-2xl shadow-lg p-6"
            >
              {fieldGroups.map((group, groupIndex) => (
                <div
                  key={group.title}
                  className={groupIndex > 0 ? "mt-8" : ""}
                >
                  <div className="mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">
                      {group.title}
                    </h2>
                    <p className="text-sm text-gray-500">
                      {group.description}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {group.fields.map((field) => (
                      <div key={field.name}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {field.label}
                        </label>
                        {field.name === "worker_id" ? (
                          <WorkerSearchSelect
                            selectedId={form.worker_id || ""}
                            onSelect={(id) => {
                              const nid = Number(id);
                              setForm(prev => ({ ...prev, worker_id: nid }));
                              fetchWorker(nid);
                            }}
                          />
                        ) : (
                          <input
                            type={field.type}
                            name={field.name}
                            value={form[field.name as keyof AbsenceInput]}
                            onChange={handleChange}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                            placeholder="0"
                          />
                        )}
                      </div>
                    ))}
                  </div>

                  {groupIndex < fieldGroups.length - 1 && (
                    <hr className="my-6 border-gray-200" />
                  )}
                </div>
              ))}

              {/* Boutons */}
              <div className="flex flex-col sm:flex-row gap-3 mt-8 pt-6 border-t border-gray-200">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  {loading ? (
                    <span className="flex items-center justify-center">
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Calcul en cours...
                    </span>
                  ) : (
                    "Calculer les retenues"
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleReset}
                  className="px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 focus:ring-4 focus:ring-gray-200 transition-all durée-200"
                >
                  Réinitialiser
                </button>
              </div>

              {/* Message d'erreur calcul */}
              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-700 flex items-center">
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {error}
                  </p>
                </div>
              )}
            </form>
          </div>

          {/* Colonne de droite : infos salarié + résultats */}
          <div className="lg:col-span-1 space-y-4">
            {/* Infos salarié */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Informations du salarié
              </h2>

              {workerLoading && (
                <p className="text-sm text-gray-500">
                  Chargement des informations du salarié...
                </p>
              )}

              {workerError && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded">
                  <p className="text-sm text-red-700">{workerError}</p>
                </div>
              )}

              {!worker && !workerLoading && !workerError && (
                <p className="text-sm text-gray-500">
                  Saisis un ID de salarié et quitte le champ pour charger ses
                  informations.
                </p>
              )}

              {worker && (
                <div className="text-sm text-gray-800 space-y-3">
                  {/* Identité */}
                  <div>
                    <p className="font-semibold text-gray-900">
                      {worker.prenom} {worker.nom}
                    </p>
                    <p className="text-gray-500">
                      Matricule :{" "}
                      <span className="font-medium">{worker.matricule}</span>
                    </p>
                  </div>

                  {/* Coordonnées */}
                  <div>
                    <p>
                      Adresse :{" "}
                      <span className="font-medium">{worker.adresse}</span>
                    </p>
                    <p>
                      Nombre d&apos;enfants :{" "}
                      <span className="font-medium">
                        {worker.nombre_enfant}
                      </span>
                    </p>
                  </div>

                  {/* Données de travail */}
                  <div className="border-t border-gray-200 pt-2">
                    <p className="text-gray-500 font-medium mb-1">
                      Données de travail
                    </p>
                    <p>
                      Horaire hebdomadaire :{" "}
                      <span className="font-semibold">
                        {worker.horaire_hebdo} h / semaine
                      </span>
                    </p>
                    <p>
                      VHM (valeur heure mensuelle) :{" "}
                      <span className="font-semibold">
                        {worker.vhm.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                  </div>

                  {/* Salaire */}
                  <div className="border-t border-gray-200 pt-2">
                    <p className="text-gray-500 font-medium mb-1">
                      Informations salariales
                    </p>
                    <p>
                      Salaire de base :{" "}
                      <span className="font-semibold">
                        {worker.salaire_base.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                    <p>
                      Salaire horaire :{" "}
                      <span className="font-semibold">
                        {worker.salaire_horaire.toLocaleString("fr-FR")} Ar
                      </span>
                    </p>
                  </div>

                  {/* Infos techniques */}
                  <div className="border-t border-gray-200 pt-2 text-xs text-gray-500">
                    <p>
                      ID worker : {worker.id} | Employer ID :{" "}
                      {worker.employer_id} | Régime : {worker.type_regime_id}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Résultats du calcul */}
            {result ? (
              <div className="bg-white rounded-2xl shadow-lg p-6 sticky top-8">
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Résultats du calcul
                </h2>

                {/* Salaire de base */}
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">
                    SALAIRE DE BASE
                  </h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Journalier</span>
                      <span className="font-semibold">
                        {result.salaire_journalier.toFixed(2)} Ar
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Horaire</span>
                      <span className="font-semibold">
                        {result.salaire_horaire.toFixed(2)} Ar
                      </span>
                    </div>
                  </div>
                </div>

                {/* Détail des rubriques */}
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-3">
                    DÉTAIL DES RETENUES
                  </h3>
                  <div className="space-y-3">
                    {result.rubriques.map((rubrique) => (
                      <div
                        key={rubrique.code}
                        className="border-l-4 border-blue-500 pl-3"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-gray-900">
                              {rubrique.label}
                            </p>
                            <p className="text-sm text-gray-500">
                              {rubrique.nombre} {rubrique.unite} ×{" "}
                              {rubrique.base.toFixed(2)} Ar
                            </p>
                          </div>
                          <span className="font-semibold text-red-600">
                            {rubrique.montant_salarial.toFixed(2)} Ar
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Total */}
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-bold text-gray-900">
                      Total des retenues
                    </span>
                    <span className="text-xl font-bold text-red-600">
                      {result.total_retenues_absence.toFixed(2)} Ar
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  En attente de calcul
                </h3>
                <p className="text-gray-500 text-sm">
                  Les résultats des calculs de retenues s&apos;afficheront ici
                  après validation du formulaire.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Absences;
