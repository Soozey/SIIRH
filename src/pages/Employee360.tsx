import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CheckBadgeIcon,
  ClockIcon,
  DocumentArrowUpIcon,
  ExclamationTriangleIcon,
  FolderOpenIcon,
  IdentificationIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";

interface Employer {
  id: number;
  raison_sociale: string;
}

interface WorkerSummary {
  id: number;
  employer_id: number;
  matricule?: string | null;
  nom: string;
  prenom: string;
}

interface HrDossierSection {
  key: string;
  title: string;
  source: string;
  data: Record<string, unknown>;
}

interface HrDossierDocumentVersion {
  id: string;
  version_number: number;
  original_name?: string | null;
  mime_type?: string | null;
  file_size?: number | null;
  created_at?: string | null;
}

interface HrDossierDocument {
  id: string;
  title: string;
  section_code: string;
  document_type: string;
  status: string;
  source_module: string;
  document_date?: string | null;
  expiration_date?: string | null;
  is_expired: boolean;
  comment?: string | null;
  can_preview: boolean;
  download_url?: string | null;
  preview_url?: string | null;
  current_version_number: number;
  metadata: Record<string, unknown>;
  versions: HrDossierDocumentVersion[];
}

interface HrDossierAlert {
  code: string;
  severity: string;
  message: string;
  details: Record<string, unknown>;
}

interface HrDossierTimelineEvent {
  id: string;
  section_code: string;
  event_type: string;
  title: string;
  description?: string | null;
  status?: string | null;
  event_date?: string | null;
  source_module?: string | null;
  payload: Record<string, unknown>;
}

interface HrDossierView {
  worker: Record<string, unknown>;
  access_scope: string;
  summary: Record<string, unknown>;
  completeness: {
    score: number;
    completed_items: number;
    total_items: number;
    missing_items: string[];
  };
  alerts: HrDossierAlert[];
  sections: Record<string, HrDossierSection>;
  documents: HrDossierDocument[];
  timeline: HrDossierTimelineEvent[];
}

interface HrDossierReportRow {
  worker_id: number;
  employer_id: number;
  matricule?: string | null;
  full_name: string;
  completeness_score: number;
  missing_contract_document: boolean;
  missing_medical_visit: boolean;
  missing_cnaps_number: boolean;
  expired_document_count: number;
  missing_items: string[];
}

interface HrDossierReport {
  employer_id: number;
  total_workers: number;
  incomplete_workers: number;
  missing_contract_document_workers: number;
  missing_medical_visit_workers: number;
  missing_cnaps_number_workers: number;
  workers_with_expired_documents: number;
  rows: HrDossierReportRow[];
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50";
const sectionOrder = [
  "identity",
  "administration_contract",
  "recruitment",
  "health",
  "affiliations",
  "payroll",
  "time_absence",
  "career",
  "disciplinary",
  "exit",
  "documents",
];

const accessScopeLabels: Record<string, string> = {
  full: "Accès complet",
  payroll: "Accès paie ciblé",
  manager: "Accès responsable limité",
  self: "Accès personnel",
  none: "Aucun accès",
};

function prettifyFieldLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\bcnaps\b/gi, "CNaPS")
    .replace(/\bcin\b/gi, "CIN")
    .replace(/\birsa\b/gi, "IRSA")
    .replace(/\bostie\b/gi, "OSTIE")
    .replace(/\bsmie\b/gi, "SMIE")
    .replace(/\bdrh\b/gi, "DRH")
    .replace(/\bhs\b/gi, "HS")
    .replace(/\bhm\b/gi, "HM")
    .replace(/\bpdf\b/gi, "PDF")
    .replace(/\bcv\b/gi, "CV")
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

function parseEditorValue(raw: string): unknown {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (!Number.isNaN(Number(trimmed)) && trimmed === String(Number(trimmed))) return Number(trimmed);
  if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return raw;
    }
  }
  return raw;
}

function renderValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-slate-500">-</span>;
  }
  if (Array.isArray(value)) {
    if (!value.length) return <span className="text-slate-500">[]</span>;
    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <pre key={index} className="overflow-x-auto rounded-xl bg-white/5 p-3 text-xs text-slate-200">
            {typeof item === "object" ? JSON.stringify(item, null, 2) : String(item)}
          </pre>
        ))}
      </div>
    );
  }
  if (typeof value === "object") {
    return <pre className="overflow-x-auto rounded-xl bg-white/5 p-3 text-xs text-slate-200">{JSON.stringify(value, null, 2)}</pre>;
  }
  return <span className="text-white">{String(value)}</span>;
}

function openBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(url);
}

export default function Employee360() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialEmployerId = Number(searchParams.get("employer_id") || 0) || null;
  const initialWorkerId = Number(searchParams.get("worker_id") || 0) || null;

  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(initialEmployerId);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(initialWorkerId);
  const [workerSearch, setWorkerSearch] = useState("");
  const [activeTab, setActiveTab] = useState<string>("identity");
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadSection, setUploadSection] = useState("documents");
  const [uploadType, setUploadType] = useState("other");
  const [uploadDate, setUploadDate] = useState("");
  const [uploadExpirationDate, setUploadExpirationDate] = useState("");
  const [uploadComment, setUploadComment] = useState("");
  const [uploadVisibleEmployee, setUploadVisibleEmployee] = useState(false);
  const [uploadVisibleManager, setUploadVisibleManager] = useState(false);
  const [uploadVisiblePayroll, setUploadVisiblePayroll] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null);
  const [newVersionFiles, setNewVersionFiles] = useState<Record<string, File | null>>({});

  const { data: employers = [] } = useQuery({
    queryKey: ["hr-dossier", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const effectiveEmployerId = useMemo(() => {
    if (selectedEmployerId !== null && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["hr-dossier", "workers", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<WorkerSummary[]>("/workers", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const effectiveWorkerId = useMemo(() => {
    if (selectedWorkerId !== null && workers.some((item) => item.id === selectedWorkerId)) {
      return selectedWorkerId;
    }
    return workers[0]?.id ?? null;
  }, [workers, selectedWorkerId]);

  const filteredWorkers = useMemo(() => {
    const query = workerSearch.trim().toLowerCase();
    if (!query) return workers;
    return workers.filter((item) =>
      [item.matricule, item.nom, item.prenom]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }, [workerSearch, workers]);

  const dossierQuery = useQuery({
    queryKey: ["hr-dossier", "worker", effectiveWorkerId],
    enabled: effectiveWorkerId !== null,
    queryFn: async () => (await api.get<HrDossierView>(`/master-data/workers/${effectiveWorkerId}/hr-dossier`)).data,
  });

  const reportQuery = useQuery({
    queryKey: ["hr-dossier", "report", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<HrDossierReport>(`/master-data/employers/${effectiveEmployerId}/hr-dossiers/report`)).data,
  });

  const orderedTabs = useMemo(() => {
    const available = Object.keys(dossierQuery.data?.sections ?? {});
    return sectionOrder.filter((item) => available.includes(item));
  }, [dossierQuery.data]);

  useEffect(() => {
    if (!effectiveEmployerId && !effectiveWorkerId) {
      return;
    }
    const next = new URLSearchParams();
    if (effectiveEmployerId) next.set("employer_id", String(effectiveEmployerId));
    if (effectiveWorkerId) next.set("worker_id", String(effectiveWorkerId));
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [effectiveEmployerId, effectiveWorkerId, searchParams, setSearchParams]);

  useEffect(() => {
    if (!orderedTabs.includes(activeTab)) {
      setActiveTab(orderedTabs[0] ?? "identity");
    }
  }, [activeTab, orderedTabs]);

  const activeSection = dossierQuery.data?.sections?.[activeTab];
  const canEdit = dossierQuery.data?.access_scope === "full" && activeTab !== "documents";

  useEffect(() => {
    if (!activeSection) {
      setEditValues({});
      return;
    }
    const next: Record<string, string> = {};
    Object.entries(activeSection.data ?? {}).forEach(([key, value]) => {
      next[key] = stringifyValue(value);
    });
    setEditValues(next);
  }, [activeSection]);

  const invalidateCurrent = async () => {
    await queryClient.invalidateQueries({ queryKey: ["hr-dossier", "worker", effectiveWorkerId] });
    await queryClient.invalidateQueries({ queryKey: ["hr-dossier", "report", effectiveEmployerId] });
  };

  const saveSectionMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveWorkerId || !activeSection) return;
      const payload: Record<string, unknown> = {};
      Object.entries(editValues).forEach(([key, value]) => {
        payload[key] = parseEditorValue(value);
      });
      await api.patch(`/master-data/workers/${effectiveWorkerId}/hr-dossier`, {
        section_key: activeSection.key,
        data: payload,
      });
    },
    onSuccess: invalidateCurrent,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveWorkerId || !uploadFiles || uploadFiles.length === 0) return;
      const formData = new FormData();
      Array.from(uploadFiles).forEach((file) => formData.append("files", file));
      formData.append("title", uploadTitle);
      formData.append("section_code", uploadSection);
      formData.append("document_type", uploadType);
      formData.append("document_date", uploadDate);
      formData.append("expiration_date", uploadExpirationDate);
      formData.append("comment", uploadComment);
      formData.append("visibility_scope", "hr_dossier");
      formData.append("visible_to_employee", String(uploadVisibleEmployee));
      formData.append("visible_to_manager", String(uploadVisibleManager));
      formData.append("visible_to_payroll", String(uploadVisiblePayroll));
      await api.post(`/master-data/workers/${effectiveWorkerId}/hr-dossier/documents/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: async () => {
      setUploadFiles(null);
      setUploadTitle("");
      setUploadDate("");
      setUploadExpirationDate("");
      setUploadComment("");
      await invalidateCurrent();
    },
  });

  const newVersionMutation = useMutation({
    mutationFn: async ({ documentId, file }: { documentId: string; file: File }) => {
      if (!effectiveWorkerId) return;
      const formData = new FormData();
      formData.append("file", file);
      await api.post(`/master-data/workers/${effectiveWorkerId}/hr-dossier/documents/${documentId}/new-version`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: invalidateCurrent,
  });

  const handleDownloadDocument = async (document: HrDossierDocument) => {
    if (document.source_module === "hr_dossier" && effectiveWorkerId) {
      const response = await api.get(
        `/master-data/workers/${effectiveWorkerId}/hr-dossier/documents/${document.id}/download`,
        { responseType: "blob" }
      );
      const versionName = document.versions[0]?.original_name || `${document.title}.bin`;
      openBlobDownload(response.data, versionName);
      return;
    }
    if (document.download_url) {
      window.open(`${api.defaults.baseURL}${document.download_url}`, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(8,47,73,0.9),rgba(59,130,246,0.7))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Dossier permanent RH
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Dossier centralisé RH</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Vue unifiée d’un salarié, alimentée par les modules existants sans dupliquer inutilement les données de contrat, organisation, paie, absences, carrière et sortie.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                void dossierQuery.refetch();
                void reportQuery.refetch();
              }}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm font-semibold text-white"
            >
              <ArrowPathIcon className={`h-5 w-5 ${dossierQuery.isFetching ? "animate-spin" : ""}`} />
              Actualiser
            </button>
            {effectiveEmployerId ? (
              <button
                type="button"
                onClick={async () => {
                  await api.post(`/master-data/employers/${effectiveEmployerId}/sync`);
                  await invalidateCurrent();
                }}
                className="inline-flex items-center gap-2 rounded-2xl border border-cyan-300/20 bg-cyan-400/10 px-4 py-3 text-sm font-semibold text-cyan-100"
              >
                <ShieldCheckIcon className="h-5 w-5" />
                Resynchroniser les données maîtres
              </button>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <IdentificationIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Périmètre salarié</h2>
              <p className="text-sm text-slate-400">Employeur, salarié, droits et reporting dossier.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Employeur</label>
              <select
                value={effectiveEmployerId ?? ""}
                onChange={(event) => setSelectedEmployerId(event.target.value ? Number(event.target.value) : null)}
                className={inputClassName}
              >
                {employers.map((item) => (
                  <option key={item.id} value={item.id}>{item.raison_sociale}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Recherche salarié</label>
              <input
                value={workerSearch}
                onChange={(event) => setWorkerSearch(event.target.value)}
                placeholder="Matricule, nom ou prénom"
                className={inputClassName}
              />
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Salarié</label>
              <select
                value={effectiveWorkerId ?? ""}
                onChange={(event) => setSelectedWorkerId(event.target.value ? Number(event.target.value) : null)}
                className={inputClassName}
              >
                {filteredWorkers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nom} {item.prenom} {item.matricule ? `(${item.matricule})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Complétude</div>
              <div className="mt-3 text-3xl font-semibold text-white">{dossierQuery.data?.completeness.score ?? 0}%</div>
              <div className="mt-2 text-sm text-slate-400">
                {dossierQuery.data?.completeness.completed_items ?? 0} / {dossierQuery.data?.completeness.total_items ?? 0} points clés
              </div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Accès</div>
              <div className="mt-3 text-xl font-semibold text-cyan-100">
                {accessScopeLabels[dossierQuery.data?.access_scope ?? ""] ?? "-"}
              </div>
              <div className="mt-2 text-sm text-slate-400">Documents visibles: {dossierQuery.data?.documents.length ?? 0}</div>
            </div>
          </div>

          <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
            <div className="text-sm font-semibold text-white">Reporting employeur</div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="rounded-xl bg-slate-900/60 p-4 text-sm text-slate-300">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Dossiers incomplets</div>
                <div className="mt-2 text-2xl font-semibold text-white">{reportQuery.data?.incomplete_workers ?? 0}</div>
              </div>
              <div className="rounded-xl bg-slate-900/60 p-4 text-sm text-slate-300">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Sans contrat</div>
                <div className="mt-2 text-2xl font-semibold text-white">{reportQuery.data?.missing_contract_document_workers ?? 0}</div>
              </div>
              <div className="rounded-xl bg-slate-900/60 p-4 text-sm text-slate-300">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Sans visite médicale</div>
                <div className="mt-2 text-2xl font-semibold text-white">{reportQuery.data?.missing_medical_visit_workers ?? 0}</div>
              </div>
              <div className="rounded-xl bg-slate-900/60 p-4 text-sm text-slate-300">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Documents expirés</div>
                <div className="mt-2 text-2xl font-semibold text-white">{reportQuery.data?.workers_with_expired_documents ?? 0}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-[1.5rem] border border-emerald-400/20 bg-emerald-500/10 p-5">
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-100/70">Salarié</div>
              <div className="mt-2 text-lg font-semibold text-white">
                {String(dossierQuery.data?.worker?.nom ?? "")} {String(dossierQuery.data?.worker?.prenom ?? "")}
              </div>
              <div className="mt-1 text-sm text-emerald-50/80">{String(dossierQuery.data?.worker?.matricule ?? "-")}</div>
            </div>
            <div className="rounded-[1.5rem] border border-cyan-400/20 bg-cyan-500/10 p-5">
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-100/70">Alertes</div>
              <div className="mt-2 text-3xl font-semibold text-white">{dossierQuery.data?.alerts.length ?? 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-violet-400/20 bg-violet-500/10 p-5">
              <div className="text-xs uppercase tracking-[0.2em] text-violet-100/70">Pièces</div>
              <div className="mt-2 text-3xl font-semibold text-white">{dossierQuery.data?.documents.length ?? 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-amber-400/20 bg-amber-500/10 p-5">
              <div className="text-xs uppercase tracking-[0.2em] text-amber-100/70">Révision</div>
              <div className="mt-2 text-3xl font-semibold text-white">{String(dossierQuery.data?.summary?.revision_number ?? 0)}</div>
            </div>
          </div>

          {dossierQuery.data?.alerts?.length ? (
            <div className={cardClassName}>
              <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <ExclamationTriangleIcon className="h-5 w-5 text-amber-300" />
                Alertes dossier
              </div>
              <div className="space-y-3">
                {dossierQuery.data.alerts.map((item) => (
                  <div key={item.code} className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-50">
                    <div className="font-semibold">{item.message}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.2em] text-amber-100/80">{item.severity}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className={cardClassName}>
            <div className="flex flex-wrap gap-2">
              {orderedTabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                    activeTab === tab
                      ? "bg-cyan-400 text-slate-950"
                      : "border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
                  }`}
                >
                  {dossierQuery.data?.sections[tab]?.title ?? tab}
                </button>
              ))}
            </div>
          </div>

          {activeTab === "documents" ? (
            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className={cardClassName}>
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <DocumentArrowUpIcon className="h-5 w-5 text-cyan-300" />
                  Dépôt documentaire
                </div>
                <div className="grid gap-4">
                  <input value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} placeholder="Titre du document" className={inputClassName} />
                  <div className="grid gap-4 md:grid-cols-2">
                    <select value={uploadSection} onChange={(e) => setUploadSection(e.target.value)} className={inputClassName}>
                      {sectionOrder.map((item) => (
                        <option key={item} value={item}>{dossierQuery.data?.sections[item]?.title ?? prettifyFieldLabel(item)}</option>
                      ))}
                    </select>
                    <select value={uploadType} onChange={(e) => setUploadType(e.target.value)} className={inputClassName}>
                      <option value="cin_passport">CIN / passeport</option>
                      <option value="contract">Contrat</option>
                      <option value="avenant">Avenant</option>
                      <option value="cv">CV</option>
                      <option value="diploma">Diplôme</option>
                      <option value="certificate">Certificat</option>
                      <option value="medical_visit">Visite médicale</option>
                      <option value="cnaps_document">Document CNaPS</option>
                      <option value="payroll_document">Document paie</option>
                      <option value="sanction">Sanction</option>
                      <option value="evaluation">Évaluation</option>
                      <option value="exit_document">Document de sortie</option>
                      <option value="other">Autre</option>
                    </select>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <input type="date" value={uploadDate} onChange={(e) => setUploadDate(e.target.value)} className={inputClassName} />
                    <input type="date" value={uploadExpirationDate} onChange={(e) => setUploadExpirationDate(e.target.value)} className={inputClassName} />
                  </div>
                  <textarea value={uploadComment} onChange={(e) => setUploadComment(e.target.value)} rows={4} placeholder="Commentaire" className={inputClassName} />
                  <label className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    <div className="font-semibold text-white">Fichiers</div>
                    <input type="file" multiple className="mt-3 block w-full text-sm text-slate-300" onChange={(e) => setUploadFiles(e.target.files)} />
                  </label>
                  <div className="grid gap-2 text-sm text-slate-300">
                    <label className="flex items-center gap-2"><input type="checkbox" checked={uploadVisibleEmployee} onChange={(e) => setUploadVisibleEmployee(e.target.checked)} /> Visible salarié</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={uploadVisibleManager} onChange={(e) => setUploadVisibleManager(e.target.checked)} /> Visible responsable</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={uploadVisiblePayroll} onChange={(e) => setUploadVisiblePayroll(e.target.checked)} /> Visible paie</label>
                  </div>
                  <button
                    type="button"
                    onClick={() => uploadMutation.mutate()}
                    disabled={uploadMutation.isPending || !uploadFiles || uploadFiles.length === 0}
                    className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50"
                  >
                    <FolderOpenIcon className="h-5 w-5" />
                    {uploadMutation.isPending ? "Téléversement..." : "Téléverser les documents"}
                  </button>
                </div>
              </div>

              <div className={cardClassName}>
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <CheckBadgeIcon className="h-5 w-5 text-cyan-300" />
                  Pièces disponibles
                </div>
                <div className="space-y-4">
                  {dossierQuery.data?.documents.length ? dossierQuery.data.documents.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="font-semibold text-white">{item.title}</div>
                          <div className="mt-1 text-sm text-slate-400">
                            {prettifyFieldLabel(item.document_type)} | {dossierQuery.data?.sections[item.section_code]?.title ?? prettifyFieldLabel(item.section_code)} | version {item.current_version_number}
                          </div>
                          <div className="mt-1 text-xs text-slate-500">
                            Date du document: {item.document_date || "-"} | expiration: {item.expiration_date || "-"}
                          </div>
                          {item.comment ? <div className="mt-2 text-sm text-slate-300">{item.comment}</div> : null}
                          {item.is_expired ? <div className="mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-300">Expiré</div> : null}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {item.preview_url ? (
                            <a
                              href={`${api.defaults.baseURL}${item.preview_url}`}
                              target="_blank"
                              rel="noreferrer"
                              className="rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-200"
                            >
                              Prévisualiser
                            </a>
                          ) : null}
                          {item.download_url ? (
                            <button
                              type="button"
                              onClick={() => void handleDownloadDocument(item)}
                              className="inline-flex items-center gap-2 rounded-xl border border-cyan-300/20 bg-cyan-400/10 px-3 py-2 text-sm text-cyan-100"
                            >
                              <ArrowDownTrayIcon className="h-4 w-4" />
                              Télécharger
                            </button>
                          ) : null}
                        </div>
                      </div>
                      {dossierQuery.data?.access_scope === "full" && !Number.isNaN(Number(item.id)) ? (
                        <div className="mt-4 flex flex-col gap-3 border-t border-white/10 pt-4 md:flex-row md:items-center">
                          <input
                            type="file"
                            className="block w-full text-sm text-slate-300"
                            onChange={(event) => {
                              const selected = event.target.files?.[0] ?? null;
                              setNewVersionFiles((current) => ({ ...current, [item.id]: selected }));
                            }}
                          />
                          <button
                            type="button"
                            onClick={() => {
                              const file = newVersionFiles[item.id];
                              if (!file) return;
                              newVersionMutation.mutate({ documentId: item.id, file });
                            }}
                            disabled={newVersionMutation.isPending || !newVersionFiles[item.id]}
                            className="rounded-xl border border-white/10 px-3 py-2 text-sm text-white disabled:opacity-50"
                          >
                            Ajouter une version
                          </button>
                        </div>
                      ) : null}
                    </div>
                  )) : <div className="text-sm text-slate-500">Aucune pièce visible sur ce dossier.</div>}
                </div>
              </div>
            </div>
          ) : (
            <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
              <div className={cardClassName}>
                <div className="mb-4 flex items-center justify-between gap-4">
                  <div>
                    <div className="text-lg font-semibold text-white">{activeSection?.title ?? "Section"}</div>
                    <div className="text-sm text-slate-400">
                      Origine des données: {activeSection?.source === "manual" ? "Saisie RH" : activeSection?.source ?? "-"}
                    </div>
                  </div>
                  {canEdit ? (
                    <button
                      type="button"
                      onClick={() => saveSectionMutation.mutate()}
                      disabled={saveSectionMutation.isPending}
                      className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
                    >
                      {saveSectionMutation.isPending ? "Enregistrement..." : "Enregistrer"}
                    </button>
                  ) : null}
                </div>

                {canEdit ? (
                  <div className="grid gap-4">
                    {Object.entries(editValues).map(([key, value]) => {
                      const isLarge = value.includes("\n") || value.startsWith("{") || value.startsWith("[") || value.length > 120;
                      return (
                        <div key={key}>
                          <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{prettifyFieldLabel(key)}</label>
                          {isLarge ? (
                            <textarea
                              rows={6}
                              value={value}
                              onChange={(event) => setEditValues((current) => ({ ...current, [key]: event.target.value }))}
                              className={inputClassName}
                            />
                          ) : (
                            <input
                              value={value}
                              onChange={(event) => setEditValues((current) => ({ ...current, [key]: event.target.value }))}
                              className={inputClassName}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(activeSection?.data ?? {}).map(([key, value]) => (
                      <div key={key} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{prettifyFieldLabel(key)}</div>
                        <div className="mt-2 text-sm text-slate-200">{renderValue(value)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className={cardClassName}>
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <ClockIcon className="h-5 w-5 text-cyan-300" />
                  Chronologie RH
                </div>
                <div className="space-y-4">
                  {(dossierQuery.data?.timeline ?? []).length ? dossierQuery.data?.timeline.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="font-semibold text-white">{item.title}</div>
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{item.event_date || "-"}</div>
                      </div>
                      <div className="mt-1 text-sm text-slate-400">{item.event_type} | {item.section_code}</div>
                      {item.description ? <div className="mt-3 text-sm text-slate-200">{item.description}</div> : null}
                    </div>
                  )) : <div className="text-sm text-slate-500">Aucun événement RH visible.</div>}
                </div>
              </div>
            </div>
          )}

          <div className={cardClassName}>
            <div className="mb-4 text-lg font-semibold text-white">Suivi employeur</div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm text-slate-300">
                <thead className="text-xs uppercase tracking-[0.18em] text-slate-500">
                  <tr>
                    <th className="px-3 py-3">Salarié</th>
                    <th className="px-3 py-3">Complétude</th>
                    <th className="px-3 py-3">Contrat</th>
                    <th className="px-3 py-3">Visite</th>
                    <th className="px-3 py-3">CNaPS</th>
                    <th className="px-3 py-3">Expirés</th>
                  </tr>
                </thead>
                <tbody>
                  {(reportQuery.data?.rows ?? []).slice(0, 15).map((item) => (
                    <tr key={item.worker_id} className="border-t border-white/10">
                      <td className="px-3 py-3">
                        <button
                          type="button"
                          onClick={() => setSelectedWorkerId(item.worker_id)}
                          className="text-left text-white hover:text-cyan-200"
                        >
                          {item.full_name}
                          <div className="text-xs text-slate-500">{item.matricule || "-"}</div>
                        </button>
                      </td>
                      <td className="px-3 py-3">{item.completeness_score}%</td>
                      <td className="px-3 py-3">{item.missing_contract_document ? "Manquant" : "OK"}</td>
                      <td className="px-3 py-3">{item.missing_medical_visit ? "Manquant" : "OK"}</td>
                      <td className="px-3 py-3">{item.missing_cnaps_number ? "Manquant" : "OK"}</td>
                      <td className="px-3 py-3">{item.expired_document_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
