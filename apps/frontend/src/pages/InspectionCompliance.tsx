import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpTrayIcon, ClipboardDocumentCheckIcon, ShieldCheckIcon, UserPlusIcon } from "@heroicons/react/24/outline";

import { api } from "../api";
import InspectorPortalWorkspace from "../components/inspection/InspectorPortalWorkspace";
import { useToast } from "../components/ui/useToast";
import { useAuth } from "../contexts/useAuth";
import { sessionHasRole } from "../rbac";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface ContractQueueItem {
  contract_id: number;
  contract_title: string;
  worker_id: number;
  worker_name: string;
  matricule?: string | null;
  status: string;
  review_stage?: string | null;
  missing_fields: string[];
}

interface IntegrityIssue {
  severity: string;
  issue_type: string;
  entity_type: string;
  entity_id: string;
  message: string;
}

interface ComplianceVisit {
  id: number;
  inspector_name?: string | null;
  status: string;
  scheduled_at?: string | null;
}

interface DashboardPayload {
  review_counts: Record<string, number>;
  contract_queue: ContractQueueItem[];
  integrity_issues: IntegrityIssue[];
  pending_declarations: Array<Record<string, unknown>>;
  upcoming_visits: ComplianceVisit[];
}

interface ComplianceReview {
  id: number;
  review_stage: string;
  status: string;
  checklist: Array<{ label: string; status: string; value?: unknown }>;
  observations: Array<{ message?: string; status_marker?: string; created_at?: string }>;
}

interface EmployerRegisterEntry {
  id: number;
  status: string;
  registry_label: string;
  details: Record<string, unknown>;
}

interface InspectorCaseItem {
  id: number;
  case_number: string;
  subject: string;
  status: string;
  current_stage: string;
  assigned_inspector_user_id?: number | null;
}

interface InspectorUser {
  id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
}

interface InspectorAssignment {
  id: number;
  case_id: number;
  inspector_user_id: number;
  scope: string;
  status: string;
  notes?: string | null;
  assigned_at: string;
  inspector?: InspectorUser | null;
}

interface InspectionDocumentVersion {
  id: number;
  version_number: number;
  original_name: string;
  download_url?: string | null;
  created_at: string;
}

interface InspectionDocument {
  id: number;
  title: string;
  document_type: string;
  confidentiality: string;
  current_version_number: number;
  versions: InspectionDocumentVersion[];
}

interface WorkerItem {
  id: number;
  nom: string;
  prenom: string;
  matricule?: string | null;
  poste?: string | null;
  departement?: string | null;
}

interface LegalEmployerStatus {
  id: number;
  raison_sociale: string;
  workers: number;
  inspection_cases: number;
  pv_generated: number;
  termination_workflows: number;
}

interface LegalModulesStatus {
  modules_implemented: number;
  procedures_created: number;
  pv_generated: number;
  test_cases: number;
  employers: LegalEmployerStatus[];
  highlights: Array<{ label: string; value: number }>;
  role_coverage: string[];
}

const cardClassName =
  "siirh-panel";
const inputClassName =
  "siirh-input";


export default function InspectionCompliance() {
  const { session } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [observation, setObservation] = useState("");
  const [visitDate, setVisitDate] = useState("");
  const [inspectorName, setInspectorName] = useState("");
  const [selectedInspectorUserId, setSelectedInspectorUserId] = useState<number | null>(null);
  const [assignmentScope, setAssignmentScope] = useState("lead");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentType, setDocumentType] = useState("supporting_document");
  const [documentFiles, setDocumentFiles] = useState<FileList | null>(null);

  const { data: employers = [] } = useQuery({
    queryKey: ["inspection", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const effectiveEmployerId = useMemo(() => {
    if (selectedEmployerId !== null && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, selectedEmployerId]);

  const { data: dashboard } = useQuery({
    queryKey: ["inspection", "dashboard", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<DashboardPayload>("/compliance/dashboard", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const { data: legalStatus } = useQuery({
    queryKey: ["inspection", "legal-status", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<LegalModulesStatus>("/compliance/legal-modules-status", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const { data: workers = [] } = useQuery({
    queryKey: ["inspection", "workers", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<WorkerItem[]>("/workers", {
        params: { employer_id: effectiveEmployerId, page: 1, page_size: 12 },
      })
    ).data,
  });

  const effectiveContractId = useMemo(() => {
    const contractQueue = dashboard?.contract_queue ?? [];
    if (selectedContractId !== null && contractQueue.some((item) => item.contract_id === selectedContractId)) {
      return selectedContractId;
    }
    return contractQueue[0]?.contract_id ?? null;
  }, [dashboard, selectedContractId]);

  const { data: registerEntries = [] } = useQuery({
    queryKey: ["inspection", "register", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<EmployerRegisterEntry[]>("/compliance/register", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const { data: reviews = [] } = useQuery({
    queryKey: ["inspection", "reviews", effectiveContractId],
    enabled: effectiveContractId !== null,
    queryFn: async () => (await api.get<ComplianceReview[]>(`/compliance/contracts/${effectiveContractId}/reviews`)).data,
  });

  const { data: cases = [] } = useQuery({
    queryKey: ["inspection", "cases", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<InspectorCaseItem[]>("/employee-portal/inspection-cases", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const effectiveCaseId = useMemo(() => {
    if (selectedCaseId !== null && cases.some((item) => item.id === selectedCaseId)) {
      return selectedCaseId;
    }
    return cases[0]?.id ?? null;
  }, [cases, selectedCaseId]);

  const { data: inspectors = [] } = useQuery({
    queryKey: ["inspection", "inspectors", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<InspectorUser[]>("/employee-portal/inspectors", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const effectiveInspectorUserId = useMemo(() => {
    if (selectedInspectorUserId !== null && inspectors.some((item) => item.id === selectedInspectorUserId)) {
      return selectedInspectorUserId;
    }
    return inspectors[0]?.id ?? null;
  }, [inspectors, selectedInspectorUserId]);

  const { data: assignments = [] } = useQuery({
    queryKey: ["inspection", "assignments", effectiveCaseId],
    enabled: effectiveCaseId !== null,
    queryFn: async () => (await api.get<InspectorAssignment[]>(`/employee-portal/inspection-cases/${effectiveCaseId}/assignments`)).data,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ["inspection", "documents", effectiveCaseId],
    enabled: effectiveCaseId !== null,
    queryFn: async () => (await api.get<InspectionDocument[]>(`/employee-portal/inspection-cases/${effectiveCaseId}/documents`)).data,
  });

  const latestReview = useMemo(() => reviews[0] ?? null, [reviews]);
  const dashboardReviewCounts = dashboard?.review_counts ?? {};
  const dashboardContractQueue = dashboard?.contract_queue ?? [];
  const dashboardIntegrityIssues = dashboard?.integrity_issues ?? [];
  const dashboardUpcomingVisits = dashboard?.upcoming_visits ?? [];
  const latestChecklist = latestReview?.checklist ?? [];
  const latestObservations = latestReview?.observations ?? [];

  const syncRegisterMutation = useMutation({
    mutationFn: async () => (
      await api.post<EmployerRegisterEntry[]>("/compliance/register/sync", null, {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
    onSuccess: async () => {
      toast.success("Registre synchronisé", "Le registre employeur a été reconstruit à partir des dossiers salariés.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "register", effectiveEmployerId] });
    },
    onError: (error: unknown) => {
      toast.error("Synchronisation impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    },
  });

  const createVersionMutation = useMutation({
    mutationFn: async (contractId: number) => (
      await api.post(`/compliance/contracts/${contractId}/versions`, {
        contract_id: contractId,
        status: "generated",
        source_module: "inspection",
      })
    ).data,
    onSuccess: async () => {
      toast.success("Version contractuelle créée", "Le snapshot de conformité a été généré.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "dashboard", effectiveEmployerId] });
    },
    onError: (error: unknown) => {
      const detail =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail !== "undefined"
          ? JSON.stringify((error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail)
          : error instanceof Error
            ? error.message
            : "Erreur inattendue.";
      toast.error("Version refusée", detail);
    },
  });

  const createReviewMutation = useMutation({
    mutationFn: async (contractId: number) => (
      await api.post(`/compliance/contracts/${contractId}/reviews`, {
        employer_id: effectiveEmployerId,
        contract_id: contractId,
        review_type: "contract_control",
        review_stage: "pre_signature",
        status: "submitted_control",
        requested_documents: ["Contrat signé", "Pièce d'identité", "Référence CNaPS / OSTIE"],
      })
    ).data,
    onSuccess: async () => {
      toast.success("Revue ouverte", "Le dossier de conformité est maintenant traçable.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "reviews", effectiveContractId] });
      await queryClient.invalidateQueries({ queryKey: ["inspection", "dashboard", effectiveEmployerId] });
    },
    onError: (error: unknown) => {
      toast.error("Revue impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    },
  });

  const observationMutation = useMutation({
    mutationFn: async () => (
      await api.post(`/compliance/reviews/${latestReview?.id}/observations`, {
        message: observation,
        status_marker: "observations_emises",
        observation_type: "inspection",
      })
    ).data,
    onSuccess: async () => {
      setObservation("");
      toast.success("Observation enregistrée", "L'historique du dossier a été mis à jour.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "reviews", effectiveContractId] });
    },
  });

  const visitMutation = useMutation({
    mutationFn: async () => (
      await api.post("/compliance/visits", {
        employer_id: effectiveEmployerId,
        review_id: latestReview?.id,
        visit_type: "inspection",
        status: "scheduled",
        inspector_name: inspectorName,
        scheduled_at: visitDate ? new Date(visitDate).toISOString() : null,
      })
    ).data,
    onSuccess: async () => {
      toast.success("Visite planifiée", "Le journal d'inspection a été enrichi.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "dashboard", effectiveEmployerId] });
    },
  });

  const assignmentMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveCaseId || !effectiveInspectorUserId) {
        throw new Error("Selectionnez un dossier et un inspecteur.");
      }
      return (
        await api.post(`/employee-portal/inspection-cases/${effectiveCaseId}/assignments`, {
          inspector_user_id: effectiveInspectorUserId,
          scope: assignmentScope,
        })
      ).data;
    },
    onSuccess: async () => {
      toast.success("Inspecteur affecte", "Le dossier est maintenant assigne nominativement.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "cases", effectiveEmployerId] });
      await queryClient.invalidateQueries({ queryKey: ["inspection", "assignments", effectiveCaseId] });
    },
    onError: (error) => {
      toast.error("Affectation impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    },
  });

  const uploadDocumentMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveCaseId || !documentFiles || documentFiles.length === 0) {
        throw new Error("Selectionnez un dossier et un fichier.");
      }
      const formData = new FormData();
      formData.append("title", documentTitle || "Piece inspection");
      formData.append("document_type", documentType);
      formData.append("description", "Document verse au coffre inspection");
      formData.append("visibility", "case_parties");
      formData.append("confidentiality", "restricted");
      formData.append("notes", "Depot via l'ecran inspection");
      formData.append("file", documentFiles[0]);
      return (await api.post(`/employee-portal/inspection-cases/${effectiveCaseId}/documents/upload`, formData)).data;
    },
    onSuccess: async () => {
      setDocumentTitle("");
      setDocumentType("supporting_document");
      setDocumentFiles(null);
      toast.success("Document depose", "Le coffre documentaire inspection a ete mis a jour.");
      await queryClient.invalidateQueries({ queryKey: ["inspection", "documents", effectiveCaseId] });
    },
    onError: (error) => {
      toast.error("Depot impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    },
  });

  if (sessionHasRole(session, ["judge_readonly", "court_clerk_readonly"])) {
    return <InspectorPortalWorkspace initialTab="cases" />;
  }

  if (sessionHasRole(session, ["inspecteur", "inspection_travail", "labor_inspector", "labor_inspector_supervisor"])) {
    return <InspectorPortalWorkspace />;
  }

  return (
    <div className="siirh-page">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(2,6,23,0.96),rgba(15,23,42,0.9),rgba(8,145,178,0.7))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Inspection du travail / conformité sociale
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Contrôles contractuels, registre employeur et observations
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Circuit de contrôle additif sur contrats et déclarations, sans toucher aux données métier sources de paie, congés et absences.
            </p>
          </div>

          <div className="w-full max-w-sm">
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100/70">Employeur</label>
            <select value={effectiveEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClassName}>
              {employers.map((item) => <option key={item.id} value={item.id}>{item.raison_sociale}</option>)}
            </select>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
        <div className="grid gap-6">
          {legalStatus ? (
            <div className={cardClassName}>
              <div className="flex items-center gap-3">
                <ShieldCheckIcon className="h-6 w-6 text-cyan-300" />
                <div>
                  <h2 className="text-xl font-semibold text-white">SIIRH LEGAL MODULES STATUS</h2>
                  <p className="text-sm text-slate-400">Modules visibles, dossiers réels et population accessible à l'inspection.</p>
                </div>
              </div>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">Modules</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{legalStatus.modules_implemented}</div>
                </div>
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">Procédures</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{legalStatus.procedures_created}</div>
                </div>
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">PV</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{legalStatus.pv_generated}</div>
                </div>
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">Tests</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{legalStatus.test_cases}</div>
                </div>
              </div>
              <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">Employeur contrôlé</div>
                  <div className="mt-4 space-y-3 text-sm text-slate-300">
                    {legalStatus.employers.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                        <div className="font-semibold text-white">{item.raison_sociale}</div>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <div>Salariés: <span className="font-semibold text-white">{item.workers}</span></div>
                          <div>Dossiers: <span className="font-semibold text-white">{item.inspection_cases}</span></div>
                          <div>PV: <span className="font-semibold text-white">{item.pv_generated}</span></div>
                          <div>Ruptures: <span className="font-semibold text-white">{item.termination_workflows}</span></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">Highlights juridiques</div>
                  <div className="mt-4 space-y-3 text-sm text-slate-300">
                    {legalStatus.highlights.map((item) => (
                      <div key={item.label} className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3">
                        <span>{item.label}</span>
                        <span className="font-semibold text-white">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          <div className={cardClassName}>
            <div className="flex items-center gap-3">
              <ShieldCheckIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Tableau de bord conformité</h2>
                <p className="text-sm text-slate-400">Statuts de revue, déclarations et visites programmées.</p>
              </div>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {Object.entries(dashboardReviewCounts).map(([status, count]) => (
                <div key={status} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">{status}</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{count}</div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => syncRegisterMutation.mutate()}
              className="mt-6 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white"
            >
              Synchroniser le registre employeur
            </button>
          </div>

          <div className={cardClassName}>
            <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">Contrats à contrôler</div>
            <div className="mt-4 space-y-3">
              {dashboardContractQueue.length ? dashboardContractQueue.map((item) => (
                <div
                  key={item.contract_id}
                  className={`rounded-[1.5rem] border p-4 ${effectiveContractId === item.contract_id ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"}`}
                >
                  <button type="button" className="w-full text-left" onClick={() => setSelectedContractId(item.contract_id)}>
                    <div className="text-sm font-semibold text-white">{item.contract_title}</div>
                    <div className="mt-1 text-sm text-slate-400">{item.worker_name} {item.matricule ? `(${item.matricule})` : ""}</div>
                    <div className="mt-2 text-xs uppercase tracking-[0.18em] text-cyan-300">{item.status}</div>
                    {(item.missing_fields ?? []).length ? (
                      <div className="mt-2 text-xs text-amber-300">Champs manquants: {(item.missing_fields ?? []).join(", ")}</div>
                    ) : null}
                  </button>
                  <div className="mt-3 flex gap-2">
                    <button type="button" onClick={() => createVersionMutation.mutate(item.contract_id)} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                      Créer version
                    </button>
                    <button type="button" onClick={() => createReviewMutation.mutate(item.contract_id)} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                      Initier revue
                    </button>
                  </div>
                </div>
              )) : <div className="text-sm text-slate-500">Aucun contrat détecté dans la file de contrôle.</div>}
            </div>
          </div>

          <div className={cardClassName}>
            <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">Anomalies inter-modules</div>
            <div className="mt-4 space-y-3">
              {dashboardIntegrityIssues.length ? dashboardIntegrityIssues.slice(0, 8).map((item) => (
                <div key={`${item.issue_type}-${item.entity_id}`} className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-50">
                  <div className="font-semibold">{item.message}</div>
                  <div className="mt-1 text-xs uppercase tracking-[0.18em] text-amber-200/80">{item.severity}</div>
                </div>
              )) : <div className="text-sm text-slate-500">Aucune anomalie structurelle remontée.</div>}
            </div>
          </div>

          <div className={cardClassName}>
            <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">Liste salariés visible pour l'inspection</div>
            <div className="mt-4 space-y-3">
              {workers.length ? workers.map((item) => (
                <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                  <div className="font-semibold text-white">{item.nom} {item.prenom}</div>
                  <div className="mt-1 text-slate-400">{item.poste || "Poste non renseigné"} {item.matricule ? `- ${item.matricule}` : ""}</div>
                  <div className="text-slate-400">{item.departement || "Département non renseigné"}</div>
                </div>
              )) : <div className="text-sm text-slate-500">Aucun salarié visible pour cet employeur.</div>}
            </div>
          </div>
        </div>

        <div className="grid gap-6">
          <div className={cardClassName}>
            <div className="flex items-center gap-3">
              <ClipboardDocumentCheckIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Dossier de revue</h2>
                <p className="text-sm text-slate-400">Checklist, observations et actions d’inspection.</p>
              </div>
            </div>

            {latestReview ? (
              <div className="mt-6 space-y-5">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">Statut: {latestReview.status}</div>
                  <div className="mt-1 text-sm text-slate-400">Étape: {latestReview.review_stage}</div>
                </div>

                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">Checklist de conformité</div>
                  <div className="mt-4 space-y-3">
                    {latestChecklist.map((item, index) => (
                      <div key={`${item.label}-${index}`} className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm">
                        <div className="text-slate-300">{item.label}</div>
                        <div className={item.status === "ok" ? "text-emerald-300" : "text-amber-300"}>{item.status}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                    <div className="text-sm font-semibold text-white">Ajouter une observation</div>
                    <textarea value={observation} onChange={(event) => setObservation(event.target.value)} rows={4} className="mt-3 w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-white" />
                    <button type="button" onClick={() => observationMutation.mutate()} className="mt-3 rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                      Enregistrer l'observation
                    </button>
                  </div>
                  <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                    <div className="text-sm font-semibold text-white">Programmer une visite</div>
                    <input value={inspectorName} onChange={(event) => setInspectorName(event.target.value)} placeholder="Nom de l'inspecteur" className={`${inputClassName} mt-3`} />
                    <input type="datetime-local" value={visitDate} onChange={(event) => setVisitDate(event.target.value)} className={`${inputClassName} mt-3`} />
                    <button type="button" onClick={() => visitMutation.mutate()} className="mt-3 rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                      Planifier
                    </button>
                  </div>
                </div>

                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                  <div className="text-sm font-semibold text-white">Historique des observations</div>
                  <div className="mt-4 space-y-3">
                    {latestObservations.length ? latestObservations.map((item, index) => (
                      <div key={`${item.created_at ?? index}`} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-300">
                        <div className="font-semibold text-white">{item.status_marker ?? "observation"}</div>
                        <div className="mt-1">{item.message ?? "-"}</div>
                      </div>
                    )) : <div className="text-sm text-slate-500">Aucune observation pour ce dossier.</div>}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-6 text-sm text-slate-400">
                Sélectionnez un contrat et initiez une revue pour ouvrir le dossier de conformité.
              </div>
            )}
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <div className={cardClassName}>
              <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">Registre employeur</div>
              <div className="mt-4 space-y-3">
                {registerEntries.length ? registerEntries.slice(0, 8).map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    <div className="font-semibold text-white">{item.registry_label}</div>
                    <div className="mt-1 text-slate-400">Statut: {item.status}</div>
                    <div className="text-slate-400">Matricule: {String(item.details.matricule ?? "-")}</div>
                  </div>
                )) : <div className="text-sm text-slate-500">Registre non synchronisé.</div>}
              </div>
            </div>

            <div className={cardClassName}>
              <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">Visites / contrôles</div>
              <div className="mt-4 space-y-3">
                {dashboardUpcomingVisits.length ? dashboardUpcomingVisits.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    <div className="font-semibold text-white">{item.inspector_name ?? "Inspection planifiée"}</div>
                    <div className="mt-1 text-slate-400">Statut: {item.status}</div>
                    <div className="text-slate-400">Date: {item.scheduled_at ?? "-"}</div>
                  </div>
                )) : <div className="text-sm text-slate-500">Aucune visite programmée.</div>}
              </div>
            </div>
          </div>
          <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <div className={cardClassName}>
              <div className="flex items-center gap-3">
                <UserPlusIcon className="h-6 w-6 text-cyan-300" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Affectation fine inspecteur</h2>
                  <p className="text-sm text-slate-400">Le profil inspecteur ne voit que les dossiers qui lui sont assignes.</p>
                </div>
              </div>

              <div className="mt-6 grid gap-4">
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Dossier</label>
                  <select value={effectiveCaseId ?? ""} onChange={(event) => setSelectedCaseId(Number(event.target.value))} className={inputClassName}>
                    {cases.map((item) => (
                      <option key={item.id} value={item.id}>{item.case_number} - {item.subject}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Inspecteur</label>
                  <select value={effectiveInspectorUserId ?? ""} onChange={(event) => setSelectedInspectorUserId(Number(event.target.value))} className={inputClassName}>
                    {inspectors.map((item) => (
                      <option key={item.id} value={item.id}>{item.full_name || item.username}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Scope</label>
                  <select value={assignmentScope} onChange={(event) => setAssignmentScope(event.target.value)} className={inputClassName}>
                    <option value="lead">Inspecteur principal</option>
                    <option value="backup">Inspecteur renfort</option>
                    <option value="review">Controle ponctuel</option>
                  </select>
                </div>
                <button type="button" onClick={() => assignmentMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300">
                  Affecter l'inspecteur
                </button>
              </div>

              <div className="mt-6 space-y-3">
                {assignments.length ? assignments.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    <div className="font-semibold text-white">{item.inspector?.full_name || item.inspector?.username || `Inspecteur #${item.inspector_user_id}`}</div>
                    <div className="mt-1 text-slate-400">Scope: {item.scope}</div>
                    <div className="text-slate-400">Statut: {item.status}</div>
                  </div>
                )) : <div className="text-sm text-slate-500">Aucune affectation nominative sur ce dossier.</div>}
              </div>
            </div>

            <div className={cardClassName}>
              <div className="flex items-center gap-3">
                <ArrowUpTrayIcon className="h-6 w-6 text-cyan-300" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Coffre documentaire inspection</h2>
                  <p className="text-sm text-slate-400">Depot versionne, telechargement et consultation du dossier.</p>
                </div>
              </div>

              <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <div className="space-y-4">
                  <input className={inputClassName} placeholder="Titre du document" value={documentTitle} onChange={(event) => setDocumentTitle(event.target.value)} />
                  <select className={inputClassName} value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
                    <option value="supporting_document">Piece justificative</option>
                    <option value="contract_review">Contrat soumis</option>
                    <option value="inspection_order">Convocation / prescription</option>
                    <option value="proof">Preuve complementaire</option>
                  </select>
                  <input type="file" className="block w-full text-sm text-slate-300" onChange={(event) => setDocumentFiles(event.target.files)} />
                  <button type="button" onClick={() => uploadDocumentMutation.mutate()} className="rounded-2xl bg-white/10 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/15">
                    Deposer dans le coffre
                  </button>
                </div>

                <div className="space-y-3">
                  {documents.length ? documents.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                      <div className="font-semibold text-white">{item.title}</div>
                      <div className="mt-1 text-slate-400">Type: {item.document_type}</div>
                      <div className="text-slate-400">Version courante: v{item.current_version_number}</div>
                      {item.versions[0]?.download_url ? (
                        <a href={item.versions[0].download_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200">
                          Ouvrir le document
                        </a>
                      ) : null}
                    </div>
                  )) : <div className="text-sm text-slate-500">Aucun document verse dans le coffre pour ce dossier.</div>}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
