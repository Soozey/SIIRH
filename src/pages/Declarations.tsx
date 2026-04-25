import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDownTrayIcon, CheckBadgeIcon, ClipboardDocumentCheckIcon, DocumentChartBarIcon } from "@heroicons/react/24/outline";

import { api } from "../api";
import { useAuth } from "../contexts/useAuth";
import { hasModulePermission } from "../rbac";
import { useToast } from "../components/ui/useToast";
import { formatCount, formatNumber } from "../utils/format";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface ExportTemplate {
  id: number;
  code: string;
  type_document: string;
  version: string;
  format: string;
  options: Record<string, unknown>;
}

interface IntegrityIssue {
  severity: string;
  issue_type: string;
  entity_type: string;
  entity_id: string;
  message: string;
}

interface PreviewPayload {
  template_code: string;
  document_type: string;
  format: string;
  meta: Record<string, unknown>;
  columns: string[];
  rows: Array<Record<string, unknown>>;
  issues: IntegrityIssue[];
}

interface ExportJob {
  id: number;
  document_type: string;
  start_period: string;
  end_period: string;
  status: string;
  created_at: string;
}

interface Declaration {
  id: number;
  channel: string;
  period_label: string;
  status: string;
  reference_number?: string | null;
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50";


function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
}

function formatPreviewValue(value: unknown): string {
  if (typeof value === "number") {
    return formatNumber(value, Number.isInteger(value) ? 0 : 2);
  }
  if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) {
    const numericValue = Number(value);
    return formatNumber(numericValue, Number.isInteger(numericValue) ? 0 : 2);
  }
  return String(value ?? "-");
}


export default function Declarations() {
  const { session } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const canWriteDeclarations = hasModulePermission(session, "declarations", "write");
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedTemplateCode, setSelectedTemplateCode] = useState<string>("");
  const [startPeriod, setStartPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [endPeriod, setEndPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [referenceDrafts, setReferenceDrafts] = useState<Record<number, string>>({});
  const [preview, setPreview] = useState<PreviewPayload | null>(null);

  const { data: employers = [] } = useQuery({
    queryKey: ["declarations", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const { data: templates = [] } = useQuery({
    queryKey: ["declarations", "templates"],
    queryFn: async () => (await api.get<ExportTemplate[]>("/statutory-exports/templates")).data,
  });

  const effectiveEmployerId = useMemo(() => {
    if (selectedEmployerId && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, selectedEmployerId]);

  const effectiveTemplateCode = useMemo(() => {
    if (selectedTemplateCode && templates.some((item) => item.code === selectedTemplateCode)) {
      return selectedTemplateCode;
    }
    return templates[0]?.code ?? "";
  }, [selectedTemplateCode, templates]);

  const { data: jobs = [] } = useQuery({
    queryKey: ["declarations", "jobs", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<ExportJob[]>("/statutory-exports/jobs", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const { data: declarations = [] } = useQuery({
    queryKey: ["declarations", "statutory", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<Declaration[]>("/statutory-exports/declarations", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.code === effectiveTemplateCode) ?? null,
    [effectiveTemplateCode, templates],
  );

  const previewMutation = useMutation({
    mutationFn: async () => (
      await api.post<PreviewPayload>("/statutory-exports/preview", {
        employer_id: effectiveEmployerId,
        template_code: effectiveTemplateCode,
        start_period: startPeriod,
        end_period: endPeriod,
      })
    ).data,
    onSuccess: (data) => {
      setPreview(data);
      toast.success("Prévisualisation prête", "Les données sources et anomalies ont été consolidées.");
    },
    onError: (error: unknown) => {
      const detail = error instanceof Error ? error.message : "Impossible de générer la prévisualisation.";
      toast.error("Prévisualisation impossible", detail);
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => (
      await api.post<ExportJob>("/statutory-exports/generate", {
        employer_id: effectiveEmployerId,
        template_code: effectiveTemplateCode,
        start_period: startPeriod,
        end_period: endPeriod,
      })
    ).data,
    onSuccess: async (job) => {
      toast.success("Export généré", `${job.document_type} est disponible dans l'historique.`);
      await queryClient.invalidateQueries({ queryKey: ["declarations", "jobs", effectiveEmployerId] });
      await queryClient.invalidateQueries({ queryKey: ["declarations", "statutory", effectiveEmployerId] });
    },
    onError: (error: unknown) => {
      const detail = error instanceof Error ? error.message : "La génération a échoué.";
      toast.error("Export impossible", detail);
    },
  });

  const submitMutation = useMutation({
    mutationFn: async (declarationId: number) => {
      const formData = new FormData();
      formData.append("reference_number", referenceDrafts[declarationId] || `REF-${declarationId}`);
      formData.append("status", "submitted");
      return (await api.post(`/statutory-exports/declarations/${declarationId}/submit`, formData)).data;
    },
    onSuccess: async () => {
      toast.success("Déclaration tracée", "La référence et le statut ont été archivés.");
      await queryClient.invalidateQueries({ queryKey: ["declarations", "statutory", effectiveEmployerId] });
    },
    onError: (error: unknown) => {
      const detail = error instanceof Error ? error.message : "Soumission impossible.";
      toast.error("Traçabilité non enregistrée", detail);
    },
  });

  const handleDownloadJob = async (jobId: number) => {
    try {
      const response = await api.get(`/statutory-exports/jobs/${jobId}/download`, { responseType: "blob" });
      downloadBlob(response.data, `export_${jobId}`);
    } catch (error) {
      toast.error("Téléchargement impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(30,64,175,0.88),rgba(21,128,61,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Centre de rapports RH et sociaux
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Déclarations, états sociaux et preuves d’inspection
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Génération versionnée des sorties réglementaires à partir des données SIRH existantes, sans recalculer la paie.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Templates</div>
              <div className="mt-3 text-3xl font-semibold text-white">{formatCount(templates.length)}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Exports</div>
              <div className="mt-3 text-3xl font-semibold text-white">{formatCount(jobs.length)}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Déclarations</div>
              <div className="mt-3 text-3xl font-semibold text-white">{formatCount(declarations.length)}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <DocumentChartBarIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Configuration</h2>
              <p className="text-sm text-slate-400">Choix du périmètre, du modèle et de la période.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Employeur</label>
              <select value={effectiveEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClassName}>
                {employers.map((item) => <option key={item.id} value={item.id}>{item.raison_sociale}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Type de document</label>
              <select value={effectiveTemplateCode} onChange={(event) => setSelectedTemplateCode(event.target.value)} className={inputClassName}>
                {templates.map((item) => <option key={item.id} value={item.code}>{item.type_document}</option>)}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Début</label>
                <input type="month" value={startPeriod} onChange={(event) => setStartPeriod(event.target.value)} className={inputClassName} />
              </div>
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Fin</label>
                <input type="month" value={endPeriod} onChange={(event) => setEndPeriod(event.target.value)} className={inputClassName} />
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
            <div className="text-sm font-semibold text-white">{selectedTemplate?.type_document ?? "Template"}</div>
            <div className="mt-2 text-sm text-slate-400">Format: {selectedTemplate?.format ?? "-"}</div>
            <div className="text-sm text-slate-400">Version: {selectedTemplate?.version ?? "-"}</div>
          </div>

          <div className="mt-6 grid gap-3">
            <button
              type="button"
              onClick={() => previewMutation.mutate()}
              disabled={!effectiveEmployerId || !effectiveTemplateCode || previewMutation.isPending}
              className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50"
            >
              {previewMutation.isPending ? "Préparation..." : "Prévisualiser les données"}
            </button>
            <button
              type="button"
              onClick={() => generateMutation.mutate()}
              disabled={!effectiveEmployerId || !effectiveTemplateCode || !canWriteDeclarations || generateMutation.isPending}
              className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              {generateMutation.isPending ? "Génération..." : "Générer l'export"}
            </button>
          </div>
        </div>

        <div className="grid gap-6">
          <div className={cardClassName}>
            <div className="flex items-center gap-3">
              <ClipboardDocumentCheckIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Prévisualisation</h2>
                <p className="text-sm text-slate-400">Aperçu des données consolidées avant génération.</p>
              </div>
            </div>

            {preview ? (
              <div className="mt-6 space-y-5">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">{preview.document_type}</div>
                  <div className="mt-2 text-sm text-slate-400">
                    {Object.entries(preview.meta).map(([key, value]) => `${key}: ${formatPreviewValue(value)}`).join(" | ")}
                  </div>
                </div>

                <div className="overflow-auto rounded-[1.5rem] border border-white/10 bg-slate-950/50">
                  <table className="min-w-full text-sm">
                    <thead className="bg-white/5 text-slate-300">
                      <tr>
                        {preview.columns.slice(0, 8).map((column) => (
                          <th key={column} className="px-4 py-3 text-left font-semibold">{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.slice(0, 8).map((row, index) => (
                        <tr key={index} className="border-t border-white/5 text-slate-200">
                          {preview.columns.slice(0, 8).map((column) => (
                            <td key={column} className="px-4 py-3">{formatPreviewValue(row[column])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">Contrôles et anomalies</div>
                  <div className="mt-4 space-y-3">
                    {preview.issues.length ? preview.issues.slice(0, 8).map((issue) => (
                      <div key={`${issue.issue_type}-${issue.entity_id}`} className="rounded-2xl border border-amber-200 bg-amber-50/95 p-4 text-sm text-amber-950">
                        <div className="font-semibold">{issue.message}</div>
                        <div className="mt-1 text-xs uppercase tracking-[0.2em] text-amber-700">{issue.severity}</div>
                      </div>
                    )) : <div className="text-sm text-slate-500">Aucune anomalie détectée sur ce périmètre.</div>}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-6 text-sm text-slate-400">
                Lancez une prévisualisation pour voir les colonnes, les lignes et les données manquantes avant génération.
              </div>
            )}
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <div className={cardClassName}>
              <div className="flex items-center gap-3">
                <ArrowDownTrayIcon className="h-6 w-6 text-cyan-300" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Historique des exports</h2>
                  <p className="text-sm text-slate-400">Fichiers générés et téléchargeables.</p>
                </div>
              </div>
              <div className="mt-6 space-y-3">
                {jobs.length ? jobs.map((job) => (
                  <div key={job.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <div className="text-sm font-semibold text-white">{job.document_type}</div>
                    <div className="mt-1 text-sm text-slate-400">{job.start_period} → {job.end_period}</div>
                    <div className="text-xs uppercase tracking-[0.18em] text-cyan-300">{job.status}</div>
                    <button
                      type="button"
                      onClick={() => handleDownloadJob(job.id)}
                      className="mt-3 rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white"
                    >
                      Télécharger
                    </button>
                  </div>
                )) : <div className="text-sm text-slate-500">Aucun export généré pour cet employeur.</div>}
              </div>
            </div>

            <div className={cardClassName}>
              <div className="flex items-center gap-3">
                <CheckBadgeIcon className="h-6 w-6 text-cyan-300" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Journal des déclarations</h2>
                  <p className="text-sm text-slate-400">Références de dépôt et statuts archivés.</p>
                </div>
              </div>
              <div className="mt-6 space-y-3">
                {declarations.length ? declarations.map((item) => (
                  <div key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <div className="text-sm font-semibold text-white">{item.channel}</div>
                    <div className="mt-1 text-sm text-slate-400">{item.period_label}</div>
                    <div className="text-xs uppercase tracking-[0.18em] text-cyan-300">{item.status}</div>
                    <input
                      value={referenceDrafts[item.id] ?? item.reference_number ?? ""}
                      onChange={(event) => setReferenceDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                      placeholder="Référence de dépôt"
                      className="mt-3 w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-sm text-white"
                    />
                    <button
                      type="button"
                      onClick={() => submitMutation.mutate(item.id)}
                      disabled={!canWriteDeclarations || submitMutation.isPending}
                      className="mt-3 rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white"
                    >
                      Marquer comme soumis
                    </button>
                  </div>
                )) : <div className="text-sm text-slate-500">Aucune déclaration historisée.</div>}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
