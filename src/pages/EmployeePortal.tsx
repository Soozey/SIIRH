import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import {
  BanknotesIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  IdentificationIcon,
  InboxStackIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";
import { useAuth } from "../contexts/useAuth";
import { sessionHasRole } from "../rbac";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface Worker {
  id: number;
  employer_id: number;
  nom: string;
  prenom: string;
  matricule?: string | null;
  poste?: string | null;
}

interface PortalDashboard {
  worker: Record<string, unknown>;
  requests: Array<{ id: number; title: string; status: string; case_number?: string | null }>;
  inspector_cases: Array<{ id: number; subject: string; status: string; case_number: string }>;
  contracts: Array<{ id: number; title: string }>;
  performance_reviews: Array<{ id: number; status: string; overall_score?: number | null }>;
  training_plan_items: Array<{ id: number; status: string }>;
  notifications: Array<{ type: string; label: string; status: string; case_number?: string }>;
}

interface PayrollArchive {
  id: number;
  employer_id: number;
  worker_id: number;
  period: string;
  month: number;
  year: number;
  worker_matricule?: string | null;
  worker_full_name?: string | null;
  brut: number;
  cotisations_salariales: number;
  cotisations_patronales: number;
  irsa: number;
  net: number;
  archived_at: string;
}

interface HrDossierDocument {
  id: string;
  title: string;
  document_type: string;
  section_code: string;
  status: string;
  document_date?: string | null;
  expiration_date?: string | null;
  download_url?: string | null;
}

interface HrDossier {
  access_scope: string;
  worker: Record<string, unknown>;
  documents: HrDossierDocument[];
  sections: Record<string, { title: string }>;
}

interface WorkerFlow {
  worker: Record<string, unknown>;
  candidate: Record<string, unknown>;
  job_posting: Record<string, unknown>;
  job_profile: Record<string, unknown>;
  workforce_job_profile: Record<string, unknown>;
  contract: Record<string, unknown>;
  integrity_issues: Array<{ severity: string; message: string }>;
}

interface InspectorCase {
  id: number;
  case_number: string;
  subject: string;
  status: string;
  current_stage: string;
  case_type: string;
}

interface InspectorMessage {
  id: number;
  body: string;
  sender_role: string;
  created_at: string;
  attachments: Array<{ name?: string; path?: string }>;
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClassName = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";

const moneyFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

const requestTypeLabels: Record<string, string> = {
  document_request: "Demande de document",
  hr_claim: "Question ou reclamation RH",
  data_correction: "Correction de donnees",
  inspection_filing: "Saisine inspection",
};

const caseTypeLabels: Record<string, string> = {
  individual_complaint: "Plainte individuelle",
  collective_grievance: "Doleance collective",
  general_claim: "Reclamation generale",
  salary_dispute: "Litige salaire",
  disciplinary_dispute: "Procedure disciplinaire",
  harassment_alert: "Alerte harcelement / dignite",
  delegate_protection: "Protection representant / delegue",
  inspection_claim: "Saisine inspection",
};

const sourcePartyLabels: Record<string, string> = {
  employee: "Employe / agent",
  employeur: "Employeur",
  representative: "Representant du personnel",
  group_of_employees: "Groupe d'employes",
};

const caseStatusLabels: Record<string, string> = {
  submitted: "Envoye",
  received: "Recu",
  in_review: "En cours d'analyse",
  investigating: "Investigation",
  EN_ATTENTE_EMPLOYE: "En attente agent",
  EN_ATTENTE_EMPLOYEUR: "En attente employeur",
  conciliation: "Conciliation",
  CLOTURE: "Cloture",
  closed: "Cloture",
  RETIREE: "Retirée",
};

function translatedLabel(value: string | null | undefined, dictionary: Record<string, string>) {
  if (!value) {
    return "-";
  }
  return dictionary[value] || dictionary[value.toLowerCase()] || value.replaceAll("_", " ");
}


export default function EmployeePortal() {
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const isEmployeeScoped = sessionHasRole(session, ["employe"]);
  const isEmployerScoped = sessionHasRole(session, ["employeur"]);
  const isInspectorScoped = sessionHasRole(session, ["inspecteur"]);

  const senderRole = session?.effective_role_code || session?.role_code || "employee";
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(session?.employer_id ?? null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(session?.worker_id ?? null);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [requestForm, setRequestForm] = useState({
    request_type: "document_request",
    destination: "rh",
    title: "",
    description: "",
    priority: "normal",
    confidentiality: "standard",
  });
  const [caseForm, setCaseForm] = useState({
    case_type: "individual_complaint",
    source_party: isEmployerScoped ? "employeur" : "employee",
    subject: "",
    description: "",
    confidentiality: "restricted",
    amicable_attempt_status: "documented",
  });
  const [messageBody, setMessageBody] = useState("");
  const [messageFiles, setMessageFiles] = useState<FileList | null>(null);

  const { data: employers = [] } = useQuery({
    queryKey: ["employee-portal", "employers"],
    enabled: !isEmployeeScoped && !isInspectorScoped,
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const effectiveEmployerId = useMemo(() => {
    if (selectedEmployerId !== null && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["employee-portal", "workers", effectiveEmployerId],
    enabled: effectiveEmployerId !== null && !isEmployeeScoped && !isInspectorScoped,
    queryFn: async () => (await api.get<Worker[]>("/workers", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const effectiveWorkerId = useMemo(() => {
    if (session?.worker_id) {
      return session.worker_id;
    }
    if (selectedWorkerId !== null && workers.some((item) => item.id === selectedWorkerId)) {
      return selectedWorkerId;
    }
    return workers[0]?.id ?? null;
  }, [workers, selectedWorkerId, session?.worker_id]);

  const { data: dashboard } = useQuery({
    queryKey: ["employee-portal", "dashboard", effectiveWorkerId],
    enabled: effectiveWorkerId !== null && !isInspectorScoped,
    queryFn: async () => (await api.get<PortalDashboard>("/employee-portal/dashboard", { params: { worker_id: effectiveWorkerId } })).data,
  });

  const { data: flow } = useQuery({
    queryKey: ["employee-portal", "flow", effectiveWorkerId],
    enabled: effectiveWorkerId !== null && !isInspectorScoped,
    queryFn: async () => (await api.get<WorkerFlow>(`/employee-portal/worker-flow/${effectiveWorkerId}`)).data,
  });

  const { data: hrDossier, isLoading: hrDossierLoading, isError: hrDossierError } = useQuery({
    queryKey: ["employee-portal", "my-hr-dossier"],
    enabled: isEmployeeScoped && !isInspectorScoped,
    queryFn: async () => (await api.get<HrDossier>("/employee-portal/me/hr-dossier")).data,
  });

  const { data: payslips = [], isLoading: payslipsLoading, isError: payslipsError } = useQuery({
    queryKey: ["employee-portal", "my-payslips"],
    enabled: isEmployeeScoped && !isInspectorScoped,
    queryFn: async () => (await api.get<PayrollArchive[]>("/employee-portal/me/payslips")).data,
  });

  const { data: cases = [] } = useQuery({
    queryKey: ["employee-portal", "cases", effectiveWorkerId, effectiveEmployerId],
    enabled: !isInspectorScoped && (effectiveWorkerId !== null || effectiveEmployerId !== null),
    queryFn: async () => (
      await api.get<InspectorCase[]>("/employee-portal/inspection-cases", {
        params: {
          worker_id: effectiveWorkerId ?? undefined,
          employer_id: effectiveWorkerId ? undefined : effectiveEmployerId ?? undefined,
        },
      })
    ).data,
  });

  const effectiveCaseId = useMemo(() => {
    if (selectedCaseId !== null && cases.some((item) => item.id === selectedCaseId)) {
      return selectedCaseId;
    }
    return cases[0]?.id ?? null;
  }, [cases, selectedCaseId]);

  const { data: messages = [] } = useQuery({
    queryKey: ["employee-portal", "messages", effectiveCaseId],
    enabled: effectiveCaseId !== null && !isInspectorScoped,
    queryFn: async () => (await api.get<InspectorMessage[]>(`/employee-portal/inspection-cases/${effectiveCaseId}/messages`)).data,
  });

  const invalidatePortal = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["employee-portal", "dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["employee-portal", "cases"] }),
      queryClient.invalidateQueries({ queryKey: ["employee-portal", "messages"] }),
      queryClient.invalidateQueries({ queryKey: ["employee-portal", "flow"] }),
    ]);
  };

  const downloadProtectedFile = async (url: string, filename: string) => {
    const response = await api.get<Blob>(url, { responseType: "blob" });
    const objectUrl = URL.createObjectURL(response.data);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(objectUrl);
  };

  const createRequestMutation = useMutation({
    mutationFn: async () => {
      if (effectiveWorkerId === null) {
        throw new Error("Aucun salarie disponible.");
      }
      return (
        await api.post("/employee-portal/requests", {
          employer_id: effectiveEmployerId,
          worker_id: effectiveWorkerId,
          ...requestForm,
          attachments: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setRequestForm({
        request_type: "document_request",
        destination: "rh",
        title: "",
        description: "",
        priority: "normal",
        confidentiality: "standard",
      });
      setFeedback("Demande employee self-service enregistree.");
      await invalidatePortal();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation de la demande impossible."),
  });

  const createCaseMutation = useMutation({
    mutationFn: async () => {
      if (effectiveWorkerId === null) {
        throw new Error("Aucun salarie disponible.");
      }
      return (
        await api.post<InspectorCase>("/employee-portal/inspection-cases", {
          employer_id: effectiveEmployerId,
          worker_id: effectiveWorkerId,
          ...caseForm,
          attachments: [],
          tags: ["employee_portal"],
          current_stage: "filing",
        })
      ).data;
    },
    onSuccess: async (createdCase) => {
      setCaseForm({
        case_type: "individual_complaint",
        source_party: isEmployerScoped ? "employeur" : "employee",
        subject: "",
        description: "",
        confidentiality: "restricted",
        amicable_attempt_status: "documented",
      });
      setSelectedCaseId(createdCase.id);
      setFeedback(`Dossier inspection ${createdCase.case_number} cree.`);
      await invalidatePortal();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation du dossier impossible."),
  });

  const sendMessageMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveCaseId) {
        throw new Error("Selectionnez d'abord un dossier.");
      }
      if (messageFiles && messageFiles.length > 0) {
        const formData = new FormData();
        formData.append("body", messageBody);
        formData.append("sender_role", senderRole);
        formData.append(
          "direction",
          isInspectorScoped
            ? "inspector_to_employee"
            : isEmployerScoped
              ? "employer_to_inspector"
              : "employee_to_inspector"
        );
        formData.append("message_type", "message");
        formData.append("visibility", "case_parties");
        Array.from(messageFiles).forEach((file) => formData.append("attachments", file));
        return (await api.post(`/employee-portal/inspection-cases/${effectiveCaseId}/messages/upload`, formData)).data;
      }
      return (
        await api.post(`/employee-portal/inspection-cases/${effectiveCaseId}/messages`, {
          sender_role: senderRole,
          direction:
            isInspectorScoped
              ? "inspector_to_employee"
              : isEmployerScoped
                ? "employer_to_inspector"
                : "employee_to_inspector",
          message_type: "message",
          visibility: "case_parties",
          body: messageBody,
          attachments: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setMessageBody("");
      setMessageFiles(null);
      setFeedback("Message formel transmis.");
      await invalidatePortal();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Envoi impossible."),
  });

  const withdrawCaseMutation = useMutation({
    mutationFn: async (caseId: number) => (
      await api.post<InspectorCase>(`/employee-portal/inspection-cases/${caseId}/withdraw`)
    ).data,
    onSuccess: async (updatedCase) => {
      setSelectedCaseId(updatedCase.id);
      setFeedback(`La doléance ${updatedCase.case_number} a été retirée.`);
      await invalidatePortal();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Retrait impossible."),
  });

  const selectedWorkerLabel = useMemo(() => {
    const worker = workers.find((item) => item.id === effectiveWorkerId);
    return worker ? `${worker.nom} ${worker.prenom}` : session?.full_name ?? session?.username ?? "Salarie";
  }, [workers, effectiveWorkerId, session?.full_name, session?.username]);
  const flowWorker = (flow?.worker ?? {}) as Record<string, unknown>;
  const flowCandidate = (flow?.candidate ?? {}) as Record<string, unknown>;
  const flowJobPosting = (flow?.job_posting ?? {}) as Record<string, unknown>;
  const flowJobProfile = (flow?.job_profile ?? {}) as Record<string, unknown>;
  const flowWorkforceProfile = (flow?.workforce_job_profile ?? {}) as Record<string, unknown>;
  const flowContract = (flow?.contract ?? {}) as Record<string, unknown>;
  const dashboardRequests = dashboard?.requests ?? [];
  const dashboardContracts = dashboard?.contracts ?? [];
  const dashboardNotifications = dashboard?.notifications ?? [];
  const flowIntegrityIssues = flow?.integrity_issues ?? [];
  const caseMessages = messages ?? [];

  if (isInspectorScoped) {
    return <Navigate to="/messages" replace />;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(30,41,59,0.9),rgba(8,145,178,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Portail salarie / agent
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Questions, plaintes et echanges avec l'inspection</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Canal formel entre salarié, employeur et inspecteur du travail, avec traçabilité, historique et statut.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Demandes</div>
              <div className="mt-3 text-3xl font-semibold text-white">{dashboardRequests.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Dossiers inspection</div>
              <div className="mt-3 text-3xl font-semibold text-white">{cases.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Contrats</div>
              <div className="mt-3 text-3xl font-semibold text-white">{dashboardContracts.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Actions a suivre</div>
              <div className="mt-3 text-3xl font-semibold text-white">{dashboardNotifications.length}</div>
            </div>
          </div>
        </div>
      </section>

      {isEmployeeScoped ? (
        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <div className={cardClassName}>
            <div className="flex items-center gap-3">
              <DocumentTextIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Mon dossier permanent RH</h2>
                <p className="text-sm text-slate-400">Documents et informations issus de votre dossier salarié réel.</p>
              </div>
            </div>
            {hrDossierLoading ? (
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">Chargement du dossier permanent...</div>
            ) : hrDossierError ? (
              <div className="mt-6 rounded-2xl border border-red-300/30 bg-red-500/10 p-4 text-sm text-red-100">Dossier permanent indisponible ou non autorisé.</div>
            ) : (
              <div className="mt-6 space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Matricule</div>
                    <div className="mt-2 font-semibold text-white">{String(hrDossier?.worker?.matricule ?? flowWorker.matricule ?? "-")}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Poste</div>
                    <div className="mt-2 font-semibold text-white">{String(hrDossier?.worker?.poste ?? flowWorker.poste ?? "-")}</div>
                  </div>
                </div>
                {(hrDossier?.documents ?? []).length ? (
                  <div className="space-y-3">
                    {(hrDossier?.documents ?? []).slice(0, 8).map((document) => (
                      <div key={document.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <div>
                            <div className="font-semibold text-white">{document.title}</div>
                            <div className="mt-1 text-xs text-slate-400">
                              {document.document_type} - {hrDossier?.sections?.[document.section_code]?.title ?? document.section_code} - {document.status}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                              Date: {document.document_date || "-"} | Expiration: {document.expiration_date || "-"}
                            </div>
                          </div>
                          {document.download_url ? (
                            <button type="button" className="rounded-xl border border-cyan-300/30 px-3 py-2 text-xs font-semibold text-cyan-100" onClick={() => downloadProtectedFile(document.download_url || "", `${document.title}.bin`)}>
                              Télécharger
                            </button>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-5 text-sm text-slate-400">Aucun document personnel disponible dans le dossier permanent.</div>
                )}
              </div>
            )}
          </div>

          <div className={cardClassName}>
            <div className="flex items-center gap-3">
              <BanknotesIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Mes bulletins de paie</h2>
                <p className="text-sm text-slate-400">Archives de paie clôturées rattachées uniquement à votre compte.</p>
              </div>
            </div>
            {payslipsLoading ? (
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">Chargement des bulletins...</div>
            ) : payslipsError ? (
              <div className="mt-6 rounded-2xl border border-red-300/30 bg-red-500/10 p-4 text-sm text-red-100">Bulletins indisponibles ou non autorisés.</div>
            ) : payslips.length ? (
              <div className="mt-6 space-y-3">
                {payslips.slice(0, 8).map((payslip) => (
                  <div key={payslip.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="font-semibold text-white">Bulletin {payslip.period}</div>
                        <div className="mt-1 text-xs text-slate-400">Net à payer: {moneyFormat.format(payslip.net)} Ar | Brut: {moneyFormat.format(payslip.brut)} Ar</div>
                        <div className="mt-1 text-xs text-slate-500">Archivé le {new Date(payslip.archived_at).toLocaleDateString("fr-FR")}</div>
                      </div>
                      <button type="button" className="rounded-xl border border-cyan-300/30 px-3 py-2 text-xs font-semibold text-cyan-100" onClick={() => downloadProtectedFile(`/employee-portal/me/payslips/${payslip.id}/download`, `bulletin_${payslip.period}.pdf`)}>
                        Voir / télécharger
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/5 p-5 text-sm text-slate-400">Aucun bulletin disponible.</div>
            )}
          </div>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.05fr_1.05fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <IdentificationIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Nouvelle demande</h2>
              <p className="text-sm text-slate-400">Canal simple pour poser une question RH, demander un document ou saisir l'inspection selon le besoin.</p>
            </div>
          </div>

          {!isEmployeeScoped ? (
            <div className="mt-6 grid gap-4">
              <div>
                <label className={labelClassName}>Employeur</label>
                <select className={inputClassName} value={effectiveEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(event.target.value ? Number(event.target.value) : null)}>
                  {employers.map((employer) => (
                    <option key={employer.id} value={employer.id}>{employer.raison_sociale}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClassName}>Salarie</label>
                <select className={inputClassName} value={effectiveWorkerId ?? ""} onChange={(event) => setSelectedWorkerId(event.target.value ? Number(event.target.value) : null)}>
                  {workers.map((worker) => (
                    <option key={worker.id} value={worker.id}>{worker.nom} {worker.prenom} {worker.matricule ? `(${worker.matricule})` : ""}</option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="mt-6 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm text-cyan-100">
              Dossier connecte: {selectedWorkerLabel}
            </div>
          )}

          <div className="mt-6 grid gap-4">
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm text-cyan-100">
              Que puis-je faire ici ? Cette zone sert aux demandes courantes. Si vous avez besoin d'un suivi formel par l'inspection du travail, utilisez plutôt le bloc "Ouvrir une plainte inspection".
            </div>
            <div>
              <label className={labelClassName}>Type de demande</label>
              <select className={inputClassName} value={requestForm.request_type} onChange={(event) => setRequestForm((current) => ({ ...current, request_type: event.target.value }))}>
                <option value="document_request">Demande de document</option>
                <option value="hr_claim">Question ou reclamation RH</option>
                <option value="data_correction">Correction de donnees</option>
                <option value="inspection_filing">Saisine inspection</option>
              </select>
            </div>
            <div>
              <label className={labelClassName}>Destination</label>
              <select className={inputClassName} value={requestForm.destination} onChange={(event) => setRequestForm((current) => ({ ...current, destination: event.target.value }))}>
                <option value="rh">RH</option>
                <option value="manager">Manager</option>
                <option value="inspection">Inspecteur du travail</option>
              </select>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-slate-300">
              Acheminement: <span className="font-semibold text-white">{translatedLabel(requestForm.request_type, requestTypeLabels)}</span> vers <span className="font-semibold text-white">{requestForm.destination === "inspection" ? "inspection du travail" : requestForm.destination}</span>.
              {requestForm.destination === "inspection" ? " Un dossier inspection sera cree si le traitement formel est necessaire." : ""}
            </div>
            <input className={inputClassName} value={requestForm.title} onChange={(event) => setRequestForm((current) => ({ ...current, title: event.target.value }))} placeholder="Objet de la demande" />
            <textarea className={`${inputClassName} min-h-[120px]`} value={requestForm.description} onChange={(event) => setRequestForm((current) => ({ ...current, description: event.target.value }))} placeholder="Expliquez la demande ou la reclamation." />
            <button type="button" onClick={() => createRequestMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300">
              {createRequestMutation.isPending ? "Enregistrement..." : "Envoyer la demande"}
            </button>
          </div>

          {feedback ? <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">{feedback}</div> : null}
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <InboxStackIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Chaine RH du dossier</h2>
              <p className="text-sm text-slate-400">Recrutement {"->"} contrat {"->"} salarie {"->"} integrite.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Salarie</div>
              <div className="mt-2 text-white">{selectedWorkerLabel}</div>
              <div className="mt-2 text-slate-400">Poste: {(flowWorker.poste as string | undefined) || "Non renseigne"}</div>
              <div className="text-slate-400">Matricule: {(flowWorker.matricule as string | undefined) || "Non renseigne"}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Recrutement</div>
              <div className="mt-2 text-white">{(flowJobPosting.title as string | undefined) || "Pas de poste relie"}</div>
              <div className="mt-2 text-slate-400">{(flowCandidate.email as string | undefined) || "Candidat source non retrouve"}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Fiche de poste</div>
              <div className="mt-2 text-white">{(flowWorkforceProfile.title as string | undefined) || (flowJobPosting.title as string | undefined) || "Aucune fiche reliee"}</div>
              <div className="mt-2 text-slate-400">{(flowWorkforceProfile.department as string | undefined) || (flowJobPosting.department as string | undefined) || "Departement non renseigne"}</div>
              <div className="mt-2 text-slate-400">{(flowJobProfile.classification as string | undefined) || (flowWorkforceProfile.classification_index as string | undefined) || "Classification non renseignee"}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Contrat</div>
              <div className="mt-2 text-white">{(flowContract.title as string | undefined) || "Aucun contrat"}</div>
              <div className="mt-2 text-slate-400">{dashboardContracts.length} contrat(s) visible(s)</div>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50/95 p-4 text-amber-950">
              <div className="text-xs uppercase tracking-[0.22em] text-amber-700">Controle d'integrite</div>
              {flowIntegrityIssues.length ? (
                <ul className="mt-3 space-y-2">
                  {flowIntegrityIssues.map((issue, index) => <li key={`${issue.message}-${index}`}>{issue.message}</li>)}
                </ul>
              ) : (
                <div className="mt-3">Aucune rupture de chaine detectee.</div>
              )}
            </div>
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ShieldCheckIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Ouvrir une plainte inspection</h2>
              <p className="text-sm text-slate-400">Créez un dossier formel quand la demande doit etre suivie par un inspecteur.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm text-cyan-100">
              Cette plainte arrive dans la boite inspecteur, est historisee, puis peut passer en analyse, attente d'informations, conciliation, convocation, PV ou cloture.
            </div>
            <div>
              <label className={labelClassName}>Type de dossier</label>
              <select className={inputClassName} value={caseForm.case_type} onChange={(event) => setCaseForm((current) => ({ ...current, case_type: event.target.value }))}>
                <option value="individual_complaint">Plainte individuelle</option>
                <option value="collective_grievance">Doleance collective</option>
                <option value="salary_dispute">Litige salaire</option>
                <option value="disciplinary_dispute">Procedure disciplinaire</option>
                <option value="harassment_alert">Alerte harcelement / dignite</option>
                <option value="delegate_protection">Protection representant / delegue</option>
                <option value="general_claim">Reclamation generale</option>
              </select>
            </div>
            <div>
              <label className={labelClassName}>Emetteur de la saisine</label>
              <select className={inputClassName} value={caseForm.source_party} onChange={(event) => setCaseForm((current) => ({ ...current, source_party: event.target.value }))}>
                <option value="employee">Employe / agent</option>
                <option value="group_of_employees">Groupe d'employes</option>
                <option value="representative">Representant du personnel</option>
                <option value="employeur">Employeur</option>
              </select>
            </div>
            <div>
              <label className={labelClassName}>Tentative amiable</label>
              <select className={inputClassName} value={caseForm.amicable_attempt_status} onChange={(event) => setCaseForm((current) => ({ ...current, amicable_attempt_status: event.target.value }))}>
                <option value="documented">Tentative amiable deja faite</option>
                <option value="not_started">Pas encore tentee</option>
                <option value="in_progress">En cours</option>
                <option value="failed">Tentative amiable echouee</option>
              </select>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-slate-300">
              Qualification actuelle: <span className="font-semibold text-white">{translatedLabel(caseForm.case_type, caseTypeLabels)}</span>.
              Emetteur: <span className="font-semibold text-white">{translatedLabel(caseForm.source_party, sourcePartyLabels)}</span>.
              {caseForm.case_type === "collective_grievance" ? " Joignez idealement la lettre de doleances, les signataires et les premieres demarches deja faites." : ""}
            </div>
            <input className={inputClassName} value={caseForm.subject} onChange={(event) => setCaseForm((current) => ({ ...current, subject: event.target.value }))} placeholder="Objet du dossier" />
            <textarea className={`${inputClassName} min-h-[120px]`} value={caseForm.description} onChange={(event) => setCaseForm((current) => ({ ...current, description: event.target.value }))} placeholder="Expose des faits, tentative amiable et pieces disponibles." />
            <button type="button" onClick={() => createCaseMutation.mutate()} className="rounded-2xl border border-cyan-300/30 bg-white/5 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/10">
              {createCaseMutation.isPending ? "Creation..." : "Ouvrir une plainte inspection"}
            </button>
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">
              Acheminement automatique: la plainte est rattachee a la societe puis assignee a l'inspecteur disponible pour ce perimetre.
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ChatBubbleLeftRightIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Plaintes et echanges</h2>
              <p className="text-sm text-slate-400">Fil formel entre salarie, employeur et inspecteur.</p>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {cases.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 px-4 py-6 text-sm text-slate-400">Aucun dossier formel pour ce perimetre.</div>
            ) : (
              cases.map((item) => (
                <div
                  key={item.id}
                  className={`rounded-2xl border px-4 py-4 transition ${
                    effectiveCaseId === item.id ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedCaseId(item.id)}
                    className="w-full text-left"
                  >
                    <div className="text-sm font-semibold text-white">{item.case_number}</div>
                    <div className="mt-1 text-sm text-slate-300">{item.subject}</div>
                    <div className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                      {translatedLabel(item.status, caseStatusLabels)} • {translatedLabel(item.case_type, caseTypeLabels)}
                    </div>
                  </button>
                  {isEmployeeScoped && ["received", "submitted", "SOUMIS", "A_QUALIFIER", "EN_ATTENTE_PIECES"].includes(item.status) ? (
                    <button
                      type="button"
                      onClick={() => withdrawCaseMutation.mutate(item.id)}
                      className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs font-semibold text-amber-100"
                    >
                      {withdrawCaseMutation.isPending ? "Retrait..." : "Retirer la doléance"}
                    </button>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-white">Fil de discussion officiel</h2>
              <p className="text-sm text-slate-400">Chaque message est historise, date et visible par les parties du dossier.</p>
            </div>
            {effectiveCaseId ? (
              <div className="text-xs uppercase tracking-[0.22em] text-cyan-200">
                {cases.find((item) => item.id === effectiveCaseId)?.case_number}
              </div>
            ) : null}
          </div>

          <div className="mt-6 space-y-3 rounded-[1.5rem] border border-white/10 bg-black/10 p-4">
            {caseMessages.length === 0 ? (
              <div className="text-sm text-slate-400">Aucun message sur ce dossier.</div>
            ) : (
              caseMessages.map((message) => (
                <article key={message.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-4 text-xs uppercase tracking-[0.18em] text-slate-500">
                    <span>{message.sender_role}</span>
                    <span>{new Date(message.created_at).toLocaleString("fr-FR")}</span>
                  </div>
                  <div className="mt-3 text-sm leading-6 text-slate-200">{message.body}</div>
                  {(message.attachments ?? []).length > 0 ? (
                    <div className="mt-3 text-xs text-cyan-200">
                      {(message.attachments ?? []).map((attachment, index) => <div key={`${attachment.path ?? attachment.name}-${index}`}>{attachment.name || attachment.path}</div>)}
                    </div>
                  ) : null}
                </article>
              ))
            )}
          </div>

          <div className="mt-6 grid gap-4">
            <textarea className={`${inputClassName} min-h-[120px]`} value={messageBody} onChange={(event) => setMessageBody(event.target.value)} placeholder="Ecrire la question, la plainte, la reponse ou la demande de piece." />
            <input type="file" multiple onChange={(event) => setMessageFiles(event.target.files)} className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-2xl file:border-0 file:bg-cyan-400 file:px-4 file:py-3 file:text-sm file:font-semibold file:text-slate-950" />
            <button type="button" onClick={() => sendMessageMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300">
              {sendMessageMutation.isPending ? "Envoi..." : "Envoyer le message"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
