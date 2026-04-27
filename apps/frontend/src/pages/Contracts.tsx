import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  IdentificationIcon,
} from "@heroicons/react/24/outline";

import {
  api,
  downloadCustomContractsTemplate,
  importCustomContractsFile,
  type TabularImportReport,
} from "../api";
import HelpTooltip from "../components/help/HelpTooltip";
import { useAuth } from "../contexts/useAuth";
import { getContextHelp } from "../help/helpContent";
import { hasModulePermission, sessionHasRole } from "../rbac";
import EmploymentAttestation from "../components/EmploymentAttestation";
import EmploymentContract from "../components/EmploymentContract";
import WorkCertificate from "../components/WorkCertificate";
import { useWorkerContracts } from "../hooks/useCustomContracts";
import { useWorkerData } from "../hooks/useConstants";


interface Employer {
  id: number;
  raison_sociale: string;
  nif?: string | null;
  adresse?: string | null;
  ville?: string | null;
  pays?: string | null;
  stat?: string | null;
  representant?: string | null;
  rep_nom_prenom?: string | null;
  rep_fonction?: string | null;
  logo_path?: string | null;
}

interface WorkerSummary {
  id: number;
  employer_id: number;
  matricule?: string | null;
  nom: string;
  prenom: string;
  poste?: string | null;
}

interface WorkerDetails extends WorkerSummary {
  date_embauche?: string | null;
  date_debauche?: string | null;
  nature_contrat?: string | null;
  categorie_prof?: string | null;
  salaire_base?: number | null;
  date_naissance?: string | null;
  lieu_naissance?: string | null;
  cin?: string | null;
  cin_delivre_le?: string | null;
  cin_lieu?: string | null;
  adresse?: string | null;
  duree_essai_jours?: number | null;
  horaire_hebdo?: number | null;
  position_history?: Array<{
    poste: string;
    categorie_prof?: string | null;
    start_date: string;
    end_date?: string | null;
  }>;
}

interface ContractGuidance {
  suggested_primary_type: string;
  available_types: string[];
  language_options: string[];
  required_fields: string[];
  alerts: Array<{ severity: string; code: string; message: string }>;
  recommendations: string[];
  suggested_defaults: Record<string, unknown>;
}

type DocumentMode = "contract" | "attestation" | "certificate";

const shellCardClassName =
  "theme-safe-surface rounded-lg border border-slate-300 bg-white p-5 shadow-sm";
const inputClassName =
  "siirh-input";


export default function Contracts() {
  const { session } = useAuth();
  const isInspector = sessionHasRole(session, ["inspecteur", "inspection_travail", "labor_inspector", "labor_inspector_supervisor"]);
  const canManageContractImport = hasModulePermission(session, "contracts", "write") && !isInspector;
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(null);
  const [documentMode, setDocumentMode] = useState<DocumentMode>("contract");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importUpdateExisting, setImportUpdateExisting] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importReport, setImportReport] = useState<TabularImportReport | null>(null);

  const { data: employers = [] } = useQuery({
    queryKey: ["contracts", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const effectiveEmployerId = useMemo(() => {
    if (selectedEmployerId && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["contracts", "workers", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<WorkerSummary[]>("/workers", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const effectiveWorkerId = useMemo(() => {
    if (selectedWorkerId && workers.some((item) => item.id === selectedWorkerId)) {
      return selectedWorkerId;
    }
    return workers[0]?.id ?? null;
  }, [selectedWorkerId, workers]);

  const { data: worker } = useQuery({
    queryKey: ["contracts", "worker", effectiveWorkerId],
    enabled: effectiveWorkerId !== null,
    queryFn: async () => (await api.get<WorkerDetails>(`/workers/${effectiveWorkerId}`)).data,
  });
  const { data: workerData } = useWorkerData(effectiveWorkerId || 0);
  const { data: workerContracts = [] } = useWorkerContracts(effectiveWorkerId || 0, "employment_contract");
  const { data: contractGuidance } = useQuery({
    queryKey: ["contracts", "guidance", effectiveWorkerId],
    enabled: effectiveWorkerId !== null,
    queryFn: async () => (await api.get<ContractGuidance>(`/custom-contracts/worker/${effectiveWorkerId}/guidance`)).data,
  });

  const employer = employers.find((item) => item.id === effectiveEmployerId) ?? null;
  const documentLabel =
    documentMode === "contract" ? "Contrat" : documentMode === "attestation" ? "Attestation" : "Certificat";
  const displayWorker = worker
    ? {
        ...worker,
        nom: workerData?.nom || worker.nom,
        prenom: workerData?.prenom || worker.prenom,
        matricule: workerData?.matricule || worker.matricule,
        poste: workerData?.poste || worker.poste,
        nature_contrat: workerData?.nature_contrat || worker.nature_contrat,
      }
    : null;
  const latestContract = workerContracts[0] ?? null;
  const suggestedDefaults = Object.entries(contractGuidance?.suggested_defaults ?? {}).filter(([, value]) => value !== null && value !== "");
  const contractsGuidanceHelp = getContextHelp("contracts", "contract_guidance");

  const handleDownloadTemplate = async (prefilled: boolean) => {
    try {
      await downloadCustomContractsTemplate({
        employerId: effectiveEmployerId ?? undefined,
        prefilled,
        format: "xlsx",
      });
    } catch (error) {
      console.error(error);
      setImportError("Impossible de télécharger le modèle de contrats.");
    }
  };

  const handleImportContracts = async () => {
    if (!importFile) {
      setImportError("Sélectionnez un fichier de contrats à importer.");
      return;
    }
    setImporting(true);
    setImportError(null);
    setImportReport(null);
    try {
      const report = await importCustomContractsFile(importFile, {
        updateExisting: importUpdateExisting,
      });
      setImportReport(report);
    } catch (error: unknown) {
      console.error(error);
      const apiDetail =
        typeof error === "object" &&
        error !== null &&
        "response" in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      const message = typeof apiDetail === "string" ? apiDetail : "Erreur lors de l'import des contrats.";
      setImportError(message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="siirh-page contracts-readable-scope">
      <section className="theme-safe-surface rounded-2xl border border-slate-300 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-xs font-bold uppercase tracking-wide text-blue-800">
              Module contrats
            </div>
            <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-[#07152f]">
              Contrats, attestations et certificats RH
            </h1>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-700">
              Réutilisation des générateurs documentaires déjà présents pour sortir
              rapidement les pièces RH attendues.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4">
              <div className="text-xs font-bold uppercase tracking-wide text-slate-700">Employeurs</div>
              <div className="mt-3 text-3xl font-extrabold text-[#07152f]">{employers.length}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4">
              <div className="text-xs font-bold uppercase tracking-wide text-slate-700">Salariés</div>
              <div className="mt-3 text-3xl font-extrabold text-[#07152f]">{workers.length}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4">
              <div className="text-xs font-bold uppercase tracking-wide text-slate-700">Document</div>
              <div className="mt-3 text-lg font-extrabold text-[#07152f]">{documentLabel}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.55fr]">
        <div className={shellCardClassName}>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-3">
              <ClipboardDocumentListIcon className="h-6 w-6 text-blue-700" />
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-[#07152f]">Sélection du dossier</h2>
              <p className="text-sm font-semibold text-slate-700">Employeur, salarié et type de document.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            {latestContract ? (
              <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-slate-800">
                <div className="text-xs font-bold uppercase tracking-wide text-blue-800">Contrôle inspection</div>
                <div className="mt-2 font-bold text-[#07152f]">{latestContract.title}</div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-blue-200 bg-white px-3 py-1 font-semibold text-blue-800">{latestContract.validation_status}</span>
                  <span className="rounded-full border border-blue-200 bg-white px-3 py-1 font-semibold text-blue-800">{latestContract.inspection_status}</span>
                  <span className="rounded-full border border-blue-200 bg-white px-3 py-1 font-semibold text-blue-800">Version {latestContract.active_version_number ?? 1}</span>
                </div>
                {latestContract.inspection_comment ? <p className="mt-3 text-slate-700">{latestContract.inspection_comment}</p> : <p className="mt-3 text-slate-700">Contrat actif immédiat, contrôle inspection a posteriori conservé.</p>}
              </div>
            ) : null}
            {contractGuidance ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-slate-800">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-amber-800">
                  <span>Assistant contrat Madagascar</span>
                  <HelpTooltip item={contractsGuidanceHelp} role={session?.effective_role_code || session?.role_code} compact />
                </div>
                <div className="mt-2 font-bold text-[#07152f]">Type suggéré: {contractGuidance.suggested_primary_type}</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {contractGuidance.available_types.map((item) => (
                    <span key={item} className={`rounded-full border px-3 py-1 text-xs ${item === contractGuidance.suggested_primary_type ? "border-amber-300 bg-white text-amber-900" : "border-slate-300 bg-white text-slate-700"}`}>
                      {item}
                    </span>
                  ))}
                </div>
                <div className="mt-2 text-slate-700">Langues: {contractGuidance.language_options.join(" / ")}</div>
                <div className="mt-2 text-slate-700">Champs à vérifier: {contractGuidance.required_fields.join(", ")}</div>
                {suggestedDefaults.length ? (
                  <div className="mt-3 rounded-xl border border-amber-200 bg-white p-3">
                    <div className="text-xs font-bold uppercase tracking-wide text-amber-800">Valeurs pré-remplies conseillées</div>
                    <div className="mt-2 grid gap-2 text-xs text-slate-800">
                      {suggestedDefaults.map(([key, value]) => (
                        <div key={key}>
                          <span className="font-semibold">{key}</span>: {String(value)}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {contractGuidance.recommendations.map((item) => <div key={item} className="mt-2 text-slate-700">{item}</div>)}
                {contractGuidance.alerts.map((item) => <div key={item.code} className="mt-2 font-semibold text-amber-900">{item.message}</div>)}
              </div>
            ) : null}
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-700">
                Employeur
              </label>
              <select
                value={effectiveEmployerId ?? ""}
                onChange={(event) => setSelectedEmployerId(Number(event.target.value))}
                className={inputClassName}
              >
                {employers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.raison_sociale}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-700">
                Salarié
              </label>
              <select
                value={effectiveWorkerId ?? ""}
                onChange={(event) => setSelectedWorkerId(Number(event.target.value))}
                className={inputClassName}
              >
                {workers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nom} {item.prenom} {item.matricule ? `(${item.matricule})` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { id: "contract" as const, label: "Contrat" },
                { id: "attestation" as const, label: "Attestation" },
                { id: "certificate" as const, label: "Certificat" },
              ].map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setDocumentMode(mode.id)}
                  className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                    documentMode === mode.id
                      ? "bg-cyan-400 text-slate-950"
                      : "border border-slate-300 bg-white text-slate-800 hover:border-blue-400 hover:bg-blue-50"
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>

          {canManageContractImport ? (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-col gap-2">
                <div className="text-sm font-bold text-[#07152f]">Import / Export Contrats (template)</div>
                <p className="text-xs text-slate-700">
                  Téléchargez un modèle puis importez les contrats en création ou mise à jour de masse.
                </p>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleDownloadTemplate(false)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100"
                >
                  Télécharger modèle
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadTemplate(true)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100"
                >
                  Export existants
                </button>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto_auto] md:items-center">
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800"
                />
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-800">
                  <input
                    type="checkbox"
                    checked={importUpdateExisting}
                    onChange={(event) => setImportUpdateExisting(event.target.checked)}
                  />
                  Mettre à jour
                </label>
                <button
                  type="button"
                  onClick={handleImportContracts}
                  disabled={!importFile || importing}
                  className="rounded-lg bg-[#002147] px-4 py-2 text-xs font-bold text-white hover:bg-[#07315f] disabled:opacity-60"
                >
                  {importing ? "Import..." : "Importer"}
                </button>
              </div>

              {importError ? <p className="mt-2 text-xs text-rose-300">{importError}</p> : null}
              {importReport ? (
                <div className="mt-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-800">
                  Créés: {importReport.created} | Maj: {importReport.updated} | Ignorés: {importReport.skipped} | Échec: {importReport.failed}
                  {importReport.error_report_csv ? (
                    <div className="mt-2">
                      <button
                        type="button"
                        onClick={() => {
                          const blob = new Blob([importReport.error_report_csv ?? ""], { type: "text/csv;charset=utf-8;" });
                          const url = URL.createObjectURL(blob);
                          const anchor = document.createElement("a");
                          anchor.href = url;
                          anchor.download = "contracts_import_errors.csv";
                          document.body.appendChild(anchor);
                          anchor.click();
                          document.body.removeChild(anchor);
                          URL.revokeObjectURL(url);
                        }}
                        className="rounded border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                      >
                        Télécharger erreurs CSV
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {displayWorker ? (
            <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <div className="flex items-center gap-3">
                <IdentificationIcon className="h-5 w-5 text-blue-700" />
                <div className="text-sm font-semibold text-[#07152f]">
                  {displayWorker.nom} {displayWorker.prenom}
                </div>
              </div>
              <div className="mt-4 space-y-2 text-sm font-semibold text-slate-700">
                <div>Poste: {displayWorker.poste || "Non renseigné"}</div>
                <div>Contrat: {displayWorker.nature_contrat || "Non renseigné"}</div>
                <div>Catégorie: {displayWorker.categorie_prof || "Non renseigné"}</div>
                <div>Matricule: {displayWorker.matricule || "Non renseigné"}</div>
                {workerData?.departement ? <div>Département canonique: {workerData.departement}</div> : null}
              </div>
            </div>
          ) : null}
        </div>

        <div className={`${shellCardClassName} overflow-hidden p-0`}>
          <div className="border-b border-slate-200 px-6 py-5">
            <div className="flex items-center gap-3">
              <DocumentTextIcon className="h-6 w-6 text-blue-700" />
              <div>
                <h2 className="text-xl font-extrabold text-[#07152f]">Document RH</h2>
                <p className="text-sm font-semibold text-slate-700">
                  Prévisualisation directe avant impression.
                </p>
              </div>
            </div>
          </div>

          <div className="document-preview contract-preview max-h-[78vh] overflow-auto bg-white p-4">
            {employer && worker ? (
              documentMode === "contract" ? (
                <EmploymentContract worker={worker} employer={employer} />
              ) : documentMode === "attestation" ? (
                <EmploymentAttestation worker={worker} employer={employer} />
              ) : (
                <WorkCertificate worker={worker} employer={employer} />
              )
            ) : (
              <div className="flex min-h-[480px] items-center justify-center px-6 text-center text-sm font-semibold text-slate-700">
                Sélectionnez un employeur et un salarié pour afficher le document.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}



