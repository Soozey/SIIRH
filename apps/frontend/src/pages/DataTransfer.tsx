import { useEffect, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  CircleStackIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  Cog6ToothIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  PlayIcon,
  ShieldCheckIcon,
  XCircleIcon,
} from "@heroicons/react/24/outline";

import {
  downloadAbsencesTemplate,
  downloadCustomContractsTemplate,
  downloadHsHmTemplate,
  downloadPrimesTemplate,
  downloadRecruitmentImportTemplate,
  downloadSstIncidentsTemplate,
  downloadTalentsTemplate,
  downloadWorkersTemplate,
  downloadSystemDataExport,
  downloadSystemDataUpdatePackage,
  executeSystemDataImport,
  getSystemUpdateJob,
  previewSystemDataExport,
  previewSystemDataImport,
  startSystemUpdate,
  getApiErrorMessage,
  type SystemDataExportPreview,
  type SystemDataImportExecuteResponse,
  type SystemDataImportReport,
  type SystemUpdateJobStatus,
} from "../api";
import HelpTooltip from "../components/help/HelpTooltip";
import IamAccessManagerPanel from "../components/IamAccessManagerPanel";
import { getContextHelp } from "../help/helpContent";


function isUpdatePackage(file: File | null): boolean {
  if (!file) return false;
  const name = file.name.toLowerCase();
  return name.endsWith(".zip") || name.endsWith(".tar.gz") || name.endsWith(".tgz");
}

function statusClasses(status: string): string {
  if (status === "success") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (status === "failed") return "border-rose-500/40 bg-rose-500/10 text-rose-200";
  return "border-cyan-400/40 bg-cyan-500/10 text-cyan-200";
}

function formatJobStatus(status: string): string {
  if (status === "success") return "Succes";
  if (status === "failed") return "Echec";
  if (status === "running") return "En cours";
  if (status === "queued") return "En attente";
  return status;
}


export default function DataTransfer() {
  const templateHubHelp = getContextHelp("data-transfer", "template_hub");
  const [file, setFile] = useState<File | null>(null);
  const [updateExisting, setUpdateExisting] = useState(true);
  const [skipExactDuplicates, setSkipExactDuplicates] = useState(true);
  const [continueOnError, setContinueOnError] = useState(true);
  const [strictMode, setStrictMode] = useState(false);
  const [selectedModulesRaw, setSelectedModulesRaw] = useState("");
  const [exportEmployerId, setExportEmployerId] = useState("");
  const [includeInactiveExport, setIncludeInactiveExport] = useState(true);
  const [includeDocumentContentExport, setIncludeDocumentContentExport] = useState(false);

  const [previewLoading, setPreviewLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [exportPreviewLoading, setExportPreviewLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportUpdateLoading, setExportUpdateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [report, setReport] = useState<SystemDataImportReport | null>(null);
  const [result, setResult] = useState<SystemDataImportExecuteResponse | null>(null);
  const [exportPreview, setExportPreview] = useState<SystemDataExportPreview | null>(null);

  const [updateFile, setUpdateFile] = useState<File | null>(null);
  const [updateDragActive, setUpdateDragActive] = useState(false);
  const [updateStarting, setUpdateStarting] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [updateJob, setUpdateJob] = useState<SystemUpdateJobStatus | null>(null);

  const selectedModules = useMemo(
    () => selectedModulesRaw.split(/[,;\n|]+/).map((item) => item.trim()).filter(Boolean),
    [selectedModulesRaw]
  );

  const options = useMemo(
    () => ({
      updateExisting,
      skipExactDuplicates,
      continueOnError,
      strictMode,
      selectedModules,
    }),
    [updateExisting, skipExactDuplicates, continueOnError, strictMode, selectedModules]
  );

  const exportOptions = useMemo(
    () => ({
      selectedModules,
      employerId: exportEmployerId ? Number(exportEmployerId) : undefined,
      includeInactive: includeInactiveExport,
      includeDocumentContent: includeDocumentContentExport,
    }),
    [selectedModules, exportEmployerId, includeInactiveExport, includeDocumentContentExport]
  );

  const updateRunning = useMemo(
    () => !!updateJob && (updateJob.status === "queued" || updateJob.status === "running"),
    [updateJob]
  );

  useEffect(() => {
    if (!updateJob?.job_id || !updateRunning) return;
    const timer = window.setInterval(async () => {
      try {
        const fresh = await getSystemUpdateJob(updateJob.job_id);
        setUpdateJob(fresh);
      } catch (err: unknown) {
        setUpdateError(getApiErrorMessage(err, "Lecture statut update impossible."));
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [updateJob?.job_id, updateRunning]);

  const handlePreview = async () => {
    if (!file) return;
    setPreviewLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await previewSystemDataImport(file, options);
      setReport(response);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Preview impossible."));
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setImportLoading(true);
    setError(null);
    try {
      const response = await executeSystemDataImport(file, options);
      setResult(response);
      setReport(response.report);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Import impossible."));
    } finally {
      setImportLoading(false);
    }
  };

  const handlePreviewExport = async () => {
    setExportPreviewLoading(true);
    setExportError(null);
    try {
      const preview = await previewSystemDataExport(exportOptions);
      setExportPreview(preview);
    } catch (err: unknown) {
      setExportError(getApiErrorMessage(err, "Preview export impossible."));
    } finally {
      setExportPreviewLoading(false);
    }
  };

  const handleExport = async () => {
    setExportLoading(true);
    setExportError(null);
    try {
      const { blob, filename } = await downloadSystemDataExport(exportOptions);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setExportError(getApiErrorMessage(err, "Export impossible."));
    } finally {
      setExportLoading(false);
    }
  };

  const handleExportUpdatePackage = async () => {
    setExportUpdateLoading(true);
    setExportError(null);
    try {
      const { blob, filename } = await downloadSystemDataUpdatePackage(exportOptions);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setExportError(getApiErrorMessage(err, "Export package update impossible."));
    } finally {
      setExportUpdateLoading(false);
    }
  };

  const handleStartSystemUpdate = async () => {
    if (!updateFile) return;
    if (!isUpdatePackage(updateFile)) {
      setUpdateError("Package invalide. Formats acceptes: .zip, .tar.gz, .tgz");
      return;
    }
    setUpdateStarting(true);
    setUpdateError(null);
    try {
      const job = await startSystemUpdate(updateFile);
      setUpdateJob(job);
    } catch (err: unknown) {
      setUpdateError(getApiErrorMessage(err, "Lancement update impossible."));
    } finally {
      setUpdateStarting(false);
    }
  };

  const canRunDataImportExport = !updateRunning && !updateStarting && !exportUpdateLoading;
  const canStartUpdate = !previewLoading && !importLoading && !exportPreviewLoading && !exportLoading && !exportUpdateLoading;

  const templateDownloads = [
    {
      key: "workers",
      label: "Salaries",
      description: "Modele Excel de reprise des salaries et dossiers RH de base.",
      action: () => downloadWorkersTemplate({ format: "xlsx" as const }),
    },
    {
      key: "recruitment-jobs",
      label: "Recrutement / Postes",
      description: "Modele offres, postes et annonces importables.",
      action: () => downloadRecruitmentImportTemplate("jobs", { format: "xlsx" as const }),
    },
    {
      key: "recruitment-candidates",
      label: "Recrutement / Candidats",
      description: "Modele candidats pour reprise ou migration recrutement.",
      action: () => downloadRecruitmentImportTemplate("candidates", { format: "xlsx" as const }),
    },
    {
      key: "contracts",
      label: "Contrats",
      description: "Modele contrats RH et contrats generes custom.",
      action: () => downloadCustomContractsTemplate({ format: "xlsx" as const }),
    },
    {
      key: "absences",
      label: "Absences",
      description: "Modele absences importables sans toucher au moteur de calcul.",
      action: () => downloadAbsencesTemplate({ format: "xlsx" as const }),
    },
    {
      key: "talents-skills",
      label: "Talents / Competences",
      description: "Modele referentiel competences.",
      action: () => downloadTalentsTemplate("skills", { format: "xlsx" as const }),
    },
    {
      key: "talents-trainings",
      label: "Talents / Formations",
      description: "Modele catalogue formations et plans.",
      action: () => downloadTalentsTemplate("trainings", { format: "xlsx" as const }),
    },
    {
      key: "sst",
      label: "SST / Incidents",
      description: "Modele accidents, incidents et quasi-accidents.",
      action: () => downloadSstIncidentsTemplate({ format: "xlsx" as const }),
    },
    {
      key: "paie-primes",
      label: "Paie / Primes",
      description: "Modele variables primes du mois.",
      action: () => {
        if (!exportEmployerId) {
          throw new Error("Renseignez d'abord un Employeur ID pour telecharger le modele primes.");
        }
        return downloadPrimesTemplate(Number(exportEmployerId), { prefilled: false, format: "xlsx" as const });
      },
    },
    {
      key: "paie-hshm",
      label: "Paie / HS-HM-Absences",
      description: "Modele paie de masse pour HS/HM/absences/avances.",
      action: () => downloadHsHmTemplate(),
    },
  ];

  const handleDownloadTemplateHub = async (download: (typeof templateDownloads)[number]) => {
    try {
      await download.action();
    } catch (err: unknown) {
      setExportError(getApiErrorMessage(err, `Telechargement du modele ${download.label} impossible.`));
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col gap-6">
      <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 md:p-8">
        <h1 className="text-2xl font-semibold text-white">Import / Export / Update Manager</h1>
        <p className="mt-2 text-sm text-slate-400">
          Import migration, export backup ZIP reimportable et mise a jour systeme par package signe SHA-256.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-3">
            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-cyan-200">
              <ArrowDownTrayIcon className="h-4 w-4" />
              Export Donnees
            </p>
            <p className="mt-1 text-xs text-cyan-100/90">Sauvegarde/migration des donnees metier (ZIP).</p>
          </div>
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-emerald-200">
              <ArrowUpTrayIcon className="h-4 w-4" />
              Import Donnees
            </p>
            <p className="mt-1 text-xs text-emerald-100/90">Fusion safe des donnees depuis package JSON/ZIP.</p>
          </div>
          <div className="rounded-xl border border-violet-500/30 bg-violet-500/10 p-3">
            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-violet-200">
              <DocumentDuplicateIcon className="h-4 w-4" />
              Export Update Donnees
            </p>
            <p className="mt-1 text-xs text-violet-100/90">ZIP source vers cible compatible Import Package.</p>
          </div>
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200">
              <Cog6ToothIcon className="h-4 w-4" />
              Import Update Logiciel
            </p>
            <p className="mt-1 text-xs text-amber-100/90">Mise a jour code + migration DB + rollback auto.</p>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-violet-500/30 bg-violet-500/5 p-4 md:p-5">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-violet-100">
                <ShieldCheckIcon className="h-4 w-4" />
                Import Update Logiciel
              </h2>
              <p className="mt-1 text-xs text-violet-200/80">
                TYPE: LOGICIEL | Workflow: upload, verification manifeste/SHA, backup last_stable, migration Alembic, restart.
              </p>
            </div>
            <div className="rounded-lg border border-violet-400/20 bg-slate-950/50 px-3 py-2 text-[11px] text-violet-100">
              Package update logiciel: <span className="font-semibold">manifest.json + payload/...</span>
            </div>
          </div>

          <div
            className={`mt-4 rounded-2xl border-2 border-dashed p-5 transition ${
              updateDragActive ? "border-violet-300 bg-violet-500/10" : "border-violet-500/30 bg-slate-900/50"
            }`}
            onDragEnter={(event) => {
              event.preventDefault();
              setUpdateDragActive(true);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              setUpdateDragActive(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setUpdateDragActive(false);
            }}
            onDrop={(event) => {
              event.preventDefault();
              setUpdateDragActive(false);
              const dropped = event.dataTransfer.files?.[0] ?? null;
              setUpdateFile(dropped);
              setUpdateError(null);
            }}
          >
            <div className="flex flex-col items-start gap-3 md:flex-row md:items-center md:justify-between">
              <div className="inline-flex items-center gap-2 text-sm text-slate-200">
                <ArrowUpTrayIcon className="h-5 w-5 text-violet-200" />
                Glisser/deposer le package update ici (.zip/.tar.gz)
              </div>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-violet-400/30 bg-violet-500/10 px-4 py-2 text-sm font-medium text-violet-100 hover:bg-violet-500/20">
                Choisir un fichier
                <input
                  type="file"
                  accept=".zip,.tar.gz,.tgz"
                  className="hidden"
                  onChange={(event) => {
                    setUpdateFile(event.target.files?.[0] ?? null);
                    setUpdateError(null);
                  }}
                />
              </label>
            </div>
            {updateFile ? (
              <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs text-violet-100">
                <CloudArrowUpIcon className="h-4 w-4" />
                {updateFile.name}
              </div>
            ) : null}
          </div>

          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <button
              type="button"
              onClick={handleStartSystemUpdate}
              disabled={!updateFile || updateStarting || updateRunning || !canStartUpdate}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {updateStarting || updateRunning ? (
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
              ) : (
                <PlayIcon className="h-4 w-4" />
              )}
              Importer et appliquer update logiciel
            </button>
          </div>

          {updateError ? (
            <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {updateError}
            </div>
          ) : null}

          {updateJob ? (
            <div className="mt-4 rounded-xl border border-violet-400/30 bg-slate-950/60 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="text-sm text-slate-200">
                  <p>
                    Job: <span className="font-semibold text-white">{updateJob.job_id}</span>
                  </p>
                  <p>
                    Version: <span className="text-violet-200">{updateJob.package_version || "n/a"}</span> | Mode:{" "}
                    <span className="text-violet-200">{updateJob.environment_mode}</span>
                  </p>
                </div>
                <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${statusClasses(updateJob.status)}`}>
                  {updateJob.status === "success" ? (
                    <CheckCircleIcon className="h-4 w-4" />
                  ) : updateJob.status === "failed" ? (
                    <XCircleIcon className="h-4 w-4" />
                  ) : (
                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  )}
                  {formatJobStatus(updateJob.status)} - {updateJob.stage}
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-2 flex items-center justify-between text-xs text-slate-300">
                  <span>Progression</span>
                  <span>{updateJob.progress}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-violet-400 transition-all duration-300"
                    style={{ width: `${updateJob.progress}%` }}
                  />
                </div>
              </div>

              {updateJob.error ? (
                <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                  {updateJob.error}
                  {updateJob.rollback_performed ? " (rollback effectue)" : ""}
                </div>
              ) : null}

              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/80 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">Journal de bord</p>
                <div className="mt-2 max-h-56 overflow-y-auto whitespace-pre-wrap font-mono text-xs leading-5 text-slate-200">
                  {updateJob.logs.length === 0 ? (
                    <p className="text-slate-500">Aucun log pour le moment.</p>
                  ) : (
                    updateJob.logs.map((line, idx) => <p key={`upd-log-${idx}`}>{line}</p>)
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="mt-6 rounded-2xl border border-cyan-500/30 bg-cyan-500/5 p-4 md:p-5">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-100">
                <DocumentDuplicateIcon className="h-4 w-4" />
                Modeles Excel d'import
                <HelpTooltip item={templateHubHelp} role="rh" compact />
              </h2>
              <p className="mt-1 text-xs text-cyan-200/80">
                Point d'entree central pour les reprises et migrations. Les imports metier restent dans leurs modules respectifs.
              </p>
            </div>
            <div className="rounded-lg border border-cyan-400/20 bg-slate-950/50 px-3 py-2 text-[11px] text-cyan-100">
              Conseil migration: telecharger le modele, completer hors ligne, previsualiser, puis importer.
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {templateDownloads.map((item) => (
              <div key={item.key} className="rounded-xl border border-cyan-400/20 bg-slate-900/50 p-4">
                <div className="text-sm font-semibold text-white">{item.label}</div>
                <div className="mt-1 text-xs leading-5 text-slate-400">{item.description}</div>
                <button
                  type="button"
                  onClick={() => void handleDownloadTemplateHub(item)}
                  className="mt-3 inline-flex items-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-500/20"
                >
                  <ArrowDownTrayIcon className="h-4 w-4" />
                  Telecharger modele
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:p-5">
          <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-slate-100">
            <CircleStackIcon className="h-4 w-4" />
            Export Donnees (Backup / Migration)
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            TYPE: DONNEES | Genere un package ZIP structure (manifest + modules) pour sauvegarde, migration et transfert.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            "Exporter backup donnees" = archive standard. "Exporter update donnees" = package source vers cible directement compatible Import Package.
          </p>

          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm text-slate-300">
              Modules (optionnel, separes par virgule)
              <input
                type="text"
                value={selectedModulesRaw}
                onChange={(event) => setSelectedModulesRaw(event.target.value)}
                placeholder="workers,payroll,absences,organisation,documents"
                className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-slate-300">
              Employeur ID (optionnel)
              <input
                type="number"
                min={1}
                value={exportEmployerId}
                onChange={(event) => setExportEmployerId(event.target.value)}
                placeholder="Export global si vide"
                className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
              />
            </label>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-2 text-sm text-slate-300 md:grid-cols-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeInactiveExport}
                onChange={(e) => setIncludeInactiveExport(e.target.checked)}
              />
              Inclure inactifs
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeDocumentContentExport}
                onChange={(e) => setIncludeDocumentContentExport(e.target.checked)}
              />
              Inclure contenu templates documents
            </label>
          </div>

          <div className="mt-5 flex flex-col gap-3 md:flex-row">
            <button
              type="button"
              onClick={handlePreviewExport}
              disabled={!canRunDataImportExport || exportPreviewLoading || exportLoading || exportUpdateLoading}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-sky-400/30 bg-sky-500/10 px-5 py-3 text-sm font-semibold text-sky-200 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exportPreviewLoading ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <EyeIcon className="h-4 w-4" />}
              Previsualiser export donnees
            </button>
            <button
              type="button"
              onClick={handleExport}
              disabled={!canRunDataImportExport || exportLoading || exportPreviewLoading || exportUpdateLoading}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exportLoading ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <CloudArrowUpIcon className="h-4 w-4" />}
              Exporter backup donnees
            </button>
            <button
              type="button"
              onClick={handleExportUpdatePackage}
              disabled={!canRunDataImportExport || exportUpdateLoading || exportLoading || exportPreviewLoading}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exportUpdateLoading ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <CloudArrowUpIcon className="h-4 w-4" />}
              Exporter update donnees (source vers cible)
            </button>
          </div>

          {exportError ? (
            <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {exportError}
            </div>
          ) : null}

          {exportPreview ? (
            <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950/60 p-4 text-sm text-slate-300">
              <p>
                Records estimes: <span className="font-semibold text-white">{exportPreview.total_records}</span>
              </p>
              <p>
                Modules exportes:{" "}
                <span className="text-slate-100">{exportPreview.manifest.modules_exported.join(", ") || "aucun"}</span>
              </p>
              {exportPreview.warnings.length > 0 ? (
                <div className="mt-2 text-xs text-amber-200">
                  {exportPreview.warnings.map((warning, idx) => (
                    <p key={`exp-w-${idx}`}>- {warning}</p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="mt-6 border-t border-slate-800 pt-6">
          <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-slate-100">
            <ArrowUpTrayIcon className="h-4 w-4" />
            Import Donnees depuis Package
          </h2>
          <p className="mt-1 text-xs text-slate-400">TYPE: DONNEES | Import d'un package exporte (JSON/ZIP) avec fusion safe.</p>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm text-slate-300">
            Package
            <input
              type="file"
              accept=".zip,.json,.dump,.txt"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm text-slate-300">
            Modules (optionnel, separes par virgule)
            <input
              type="text"
              value={selectedModulesRaw}
              onChange={(event) => setSelectedModulesRaw(event.target.value)}
              placeholder="workers,payroll,absences"
              className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
            />
          </label>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-2 text-sm text-slate-300 md:grid-cols-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={updateExisting} onChange={(e) => setUpdateExisting(e.target.checked)} />
            Update existing
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={skipExactDuplicates}
              onChange={(e) => setSkipExactDuplicates(e.target.checked)}
            />
            Skip exact duplicates
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={continueOnError} onChange={(e) => setContinueOnError(e.target.checked)} />
            Continue on error
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={strictMode} onChange={(e) => setStrictMode(e.target.checked)} />
            Strict mode
          </label>
        </div>

        <div className="mt-6 flex flex-col gap-3 md:flex-row">
          <button
            type="button"
            onClick={handlePreview}
            disabled={!file || previewLoading || importLoading || !canRunDataImportExport}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-500/10 px-5 py-3 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {previewLoading ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <EyeIcon className="h-4 w-4" />}
            Previsualiser import donnees
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={!file || previewLoading || importLoading || !canRunDataImportExport}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {importLoading ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <PlayIcon className="h-4 w-4" />}
            Importer donnees
          </button>
        </div>

        {file ? (
          <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-4 py-2 text-xs text-slate-300">
            <CloudArrowUpIcon className="h-4 w-4" />
            {file.name}
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        ) : null}
      </section>

      {report ? (
        <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 md:p-8">
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-6">
            <StatCard label="Traitées" value={report.total_processed_rows} />
            <StatCard label="Créées" value={report.total_created} />
            <StatCard label="Mises à jour" value={report.total_updated} />
            <StatCard label="Ignorées" value={report.total_skipped} />
            <StatCard label="En échec" value={report.total_failed} />
            <StatCard label="Conflits" value={report.total_conflicts} />
          </div>

          <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
            <p>
              Source: <span className="text-slate-100">{report.manifest.source_system || "n/a"}</span>
            </p>
            <p>
              Version du package: <span className="text-slate-100">{report.manifest.package_version || "n/a"}</span>
            </p>
            <p>
              Modules détectés:{" "}
              <span className="text-slate-100">{report.manifest.modules_detected.join(", ") || "aucun"}</span>
            </p>
          </div>

          {report.warnings.length > 0 || report.errors.length > 0 ? (
            <div className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
              <div className="mb-2 inline-flex items-center gap-2 font-semibold">
                <ExclamationTriangleIcon className="h-4 w-4" />
                Alertes / erreurs
              </div>
              {report.warnings.map((item, idx) => (
                <p key={`w-${idx}`}>- {item}</p>
              ))}
              {report.errors.map((item, idx) => (
                <p key={`e-${idx}`}>- {item}</p>
              ))}
            </div>
          ) : null}

          <div className="mt-6 overflow-x-auto rounded-2xl border border-slate-800">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-900/80 text-slate-300">
                <tr>
                  <th className="px-4 py-3">Module</th>
                  <th className="px-4 py-3">Détectés</th>
                  <th className="px-4 py-3">Créés</th>
                  <th className="px-4 py-3">Mis à jour</th>
                  <th className="px-4 py-3">Ignorés</th>
                  <th className="px-4 py-3">En échec</th>
                  <th className="px-4 py-3">Conflits</th>
                </tr>
              </thead>
              <tbody>
                {report.modules.map((module) => (
                  <tr key={module.module} className="border-t border-slate-800 text-slate-200">
                    <td className="px-4 py-3">{module.module}</td>
                    <td className="px-4 py-3">{module.detected_records}</td>
                    <td className="px-4 py-3">{module.created}</td>
                    <td className="px-4 py-3">{module.updated}</td>
                    <td className="px-4 py-3">{module.skipped}</td>
                    <td className="px-4 py-3">{module.failed}</td>
                    <td className="px-4 py-3">{module.conflicts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {result ? (
        <section className="rounded-3xl border border-emerald-500/30 bg-emerald-500/10 p-6 text-sm text-emerald-100">
          Import exécuté: importés={result.imported}, mis à jour={result.updated}, ignorés={result.skipped}, en échec=
          {result.failed}, conflits={result.conflicts}
        </section>
      ) : null}

      <IamAccessManagerPanel />

      <div className="flex-1" />
    </div>
  );
}


function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
