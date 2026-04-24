import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BuildingOffice2Icon,
  BriefcaseIcon,
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

import { api } from "../../api";
import { useAuth } from "../../contexts/AuthContext";
import { sessionHasRole } from "../../rbac";
import { useToast } from "../ui/ToastProvider";


type TabKey = "dashboard" | "companies" | "offers" | "cases" | "collective" | "conciliation" | "pv" | "assistant" | "messages" | "help" | "settings";
type InboxBucketKey = "new" | "mine" | "waiting_employee" | "waiting_employer" | "closed";

interface EmployerSummary {
  id: number;
  raison_sociale: string;
  nif?: string | null;
  stat?: string | null;
  rccm?: string | null;
  adresse?: string | null;
  secteur?: string | null;
  contact_rh?: string | null;
  company_size: number;
  open_cases: number;
  pending_job_offers: number;
  pending_reviews: number;
  unread_messages: number;
  latest_activity_at?: string | null;
}

interface WorkerSummary {
  id: number;
  employer_id: number;
  matricule?: string | null;
  nom: string;
  prenom: string;
  poste?: string | null;
  departement?: string | null;
  service?: string | null;
}

interface CaseItem {
  id: number;
  case_number: string;
  employer_id: number;
  worker_id?: number | null;
  case_type: string;
  sub_type?: string | null;
  subject: string;
  description: string;
  category?: string | null;
  district?: string | null;
  urgency: string;
  confidentiality: string;
  current_stage: string;
  status: string;
  outcome_summary?: string | null;
  resolution_type?: string | null;
  assigned_inspector_user_id?: number | null;
  last_response_at?: string | null;
  closed_at?: string | null;
  is_sensitive: boolean;
  created_at: string;
  updated_at: string;
}

interface JobOfferSummary {
  id: number;
  employer_id: number;
  employer_name?: string | null;
  title: string;
  department?: string | null;
  location?: string | null;
  contract_type: string;
  status: string;
  description?: string | null;
  workflow_status: string;
  announcement_status?: string | null;
  validation_comment?: string | null;
  publication_mode?: string | null;
  publication_url?: string | null;
  submitted_to_inspection_at?: string | null;
  last_reviewed_at?: string | null;
  attachments: Array<{ name?: string; path?: string }>;
}

interface FormalMessage {
  id: number;
  reference_number: string;
  subject: string;
  body: string;
  status: string;
  sent_at?: string | null;
  recipients: Array<{
    id: number;
    employer_id?: number | null;
    user_id?: number | null;
    recipient_type: string;
    status: string;
  }>;
}

interface InspectionDocument {
  id: number;
  title: string;
  document_type: string;
  status: string;
  current_version_number: number;
  versions: Array<{ id: number; original_name: string; download_url?: string | null }>;
}

interface LabourClaim {
  id: number;
  claim_type: string;
  claimant_party: string;
  factual_basis: string;
  amount_requested?: number | null;
  status: string;
  conciliation_outcome?: string | null;
  inspector_observations?: string | null;
}

interface LabourEvent {
  id: number;
  event_type: string;
  title: string;
  description?: string | null;
  status: string;
  scheduled_at?: string | null;
  completed_at?: string | null;
  participants: Array<Record<string, unknown>>;
}

interface LabourPv {
  id: number;
  pv_number: string;
  pv_type: string;
  title: string;
  content: string;
  status: string;
  version_number: number;
  measures_to_execute?: string | null;
  execution_deadline?: string | null;
  delivered_to_parties_at?: string | null;
}

interface LabourWorkspace {
  case: CaseItem;
  claims: LabourClaim[];
  events: LabourEvent[];
  pv_records: LabourPv[];
  messages: Array<{ id: number; body: string; created_at: string; sender_role: string }>;
  documents: InspectionDocument[];
  document_access_logs: Array<{ id: number; action: string; created_at: string; user_id?: number | null }>;
  related: Record<string, unknown>;
  help_topics: Array<{ code: string; title: string; summary: string; steps: string[] }>;
  legal_summary?: Record<string, unknown>;
}

interface HelpPayload {
  role_context: string;
  topics: Array<{ code: string; title: string; summary: string; steps: string[] }>;
  principles: string[];
}

interface EmployerDetail {
  employer: Record<string, unknown>;
  compliance_status: Record<string, number>;
  contacts: Array<{ label: string; value: string }>;
  documents: InspectionDocument[];
  cases: CaseItem[];
  job_offers: JobOfferSummary[];
  formal_messages: FormalMessage[];
  observations: Array<{ id: number; message: string; status_marker: string; created_at: string }>;
  actions: Array<{ id: number; action: string; entity_type: string; created_at: string }>;
}

interface DashboardPayload {
  metrics: Record<string, number>;
  recent_companies: EmployerSummary[];
  recent_cases: CaseItem[];
  recent_messages: FormalMessage[];
  pending_job_offers: JobOfferSummary[];
  pending_documents: Array<{ document_id: number; title: string; case_number: string; updated_at: string }>;
  alerts: Array<{ case_id: number; case_number: string; subject: string; urgency: string; status: string }>;
}

interface ParameterItem {
  id: number;
  category: string;
  label: string;
  description?: string | null;
}

interface InspectorUser {
  id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
}

const shellCard = "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClass = "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClass = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";

const tabs: Array<{ key: TabKey; label: string; icon: typeof ShieldCheckIcon }> = [
  { key: "dashboard", label: "Tableau de bord", icon: ShieldCheckIcon },
  { key: "companies", label: "Entreprises", icon: BuildingOffice2Icon },
  { key: "offers", label: "Offres", icon: BriefcaseIcon },
  { key: "cases", label: "Dossiers", icon: ClipboardDocumentListIcon },
  { key: "collective", label: "Doleances", icon: ClipboardDocumentListIcon },
  { key: "conciliation", label: "Conciliation", icon: ClipboardDocumentListIcon },
  { key: "pv", label: "PV", icon: ClipboardDocumentListIcon },
  { key: "assistant", label: "Assistant", icon: ChatBubbleLeftRightIcon },
  { key: "messages", label: "Messagerie", icon: ChatBubbleLeftRightIcon },
  { key: "help", label: "Aide", icon: ExclamationTriangleIcon },
  { key: "settings", label: "Parametres", icon: ExclamationTriangleIcon },
];

const categoryOptions = [
  { value: "complaint_category", label: "Categories plaintes" },
  { value: "submission_type", label: "Types dossiers" },
  { value: "decision_type", label: "Types decisions" },
  { value: "message_template", label: "Modeles messages" },
  { value: "circonscription", label: "Circonscriptions" },
];

const metricLabels: Record<string, string> = {
  companies_followed: "Entreprises suivies",
  pending_job_offers: "Offres d'emploi en attente",
  pending_reviews: "Revues en attente",
  complaints_new: "Nouvelles plaintes",
  complaints_in_progress: "Plaintes en cours",
  complaints_closed: "Plaintes cloturees",
  cases_to_qualify: "Dossiers a qualifier",
  convocations_to_emit: "Convocations a emettre",
  conciliations_scheduled: "Conciliations programmees",
  waiting_employer: "En attente employeur",
  waiting_employee: "En attente employe",
  urgent_sensitive_cases: "Dossiers urgents / sensibles",
  stale_cases_7d: "Dossiers sans action 7 j",
  pv_to_produce: "PV a produire",
  pv_issued: "PV emis",
  non_execution_cases: "Dossiers de non-execution",
  sanction_reviews: "Contestations de sanctions",
  delegate_protection_cases: "Dossiers delegues / proteges",
  collective_grievances: "Doleances collectives",
  unread_messages: "Messages non lus",
  pending_corrections: "Corrections en attente",
  critical_alerts: "Alertes critiques",
};

const fieldLabels: Record<string, string> = {
  id: "Identifiant",
  raison_sociale: "Raison sociale",
  nif: "NIF",
  stat: "STAT",
  rccm: "RCCM",
  adresse: "Adresse",
  ville: "Ville",
  activite: "Activite",
  contact_rh: "Contact RH",
  email: "Email",
  telephone: "Telephone",
  representant: "Representant",
  effectif_declare: "Effectif declare",
  open_cases: "Dossiers ouverts",
  pending_reviews: "Revues en attente",
  pending_job_offers: "Offres en attente",
};

const statusLabels: Record<string, string> = {
  draft: "Brouillon",
  issued: "Emis",
  sent: "Envoye",
  planned: "Planifie",
  scheduled: "Programme",
  received: "Recu",
  submitted: "Soumis",
  in_review: "En instruction",
  investigating: "Investigation",
  conciliation: "Conciliation",
  correction_requested: "Correction demandee",
  closed: "Cloture",
  archived: "Archive",
  rejected: "Rejete",
  pending_validation: "Validation en attente",
  needs_correction: "Correction requise",
  validated: "Valide",
  validated_with_observations: "Valide avec observations",
  published: "Publie",
  published_non_validated: "Publie non valide",
  published_non_conforme: "Publie non conforme",
  active: "Actif",
  filing: "Depot",
  instruction: "Instruction",
  SOUMIS: "Soumis",
  A_QUALIFIER: "A qualifier",
  EN_ATTENTE_PIECES: "En attente de pieces",
  EN_ATTENTE_EMPLOYEUR: "En attente employeur",
  EN_ATTENTE_EMPLOYE: "En attente employe",
  EN_CONCILIATION: "En conciliation",
  CONCILIATION_PARTIELLE: "Conciliation partielle",
  NON_CONCILIE: "Non concilie",
  CARENCE: "Carence",
  PV_A_EMETTRE: "PV a emettre",
  PV_EMIS: "PV emis",
  EN_SUIVI_EXECUTION: "Suivi d'execution",
  NON_EXECUTE: "Non execute",
  ORIENTE_JURIDICTION: "Oriente vers la juridiction",
  CLOTURE: "Cloture",
  ARCHIVE: "Archive",
};

const caseTypeLabels: Record<string, string> = {
  individual_complaint: "Plainte individuelle",
  individual_claim: "Reclamation individuelle",
  individual_dispute: "Differend individuel",
  collective_grievance: "Doleance collective",
  doleance_collective: "Doleance collective",
  sanction_review: "Contestation de sanction",
  intervention_request: "Demande d'intervention",
  compliance_control: "Controle de conformite",
  delegate_protection: "Delegue du personnel / salarie protege",
  infraction_report: "Infraction / constat",
  other_inspection: "Autre dossier inspection",
  general_claim: "Reclamation generale",
  inspection_claim: "Saisine inspection",
};

const eventTypeLabels: Record<string, string> = {
  convocation: "Convocation",
  conciliation: "Conciliation",
  carence: "Carence",
  execution_followup: "Suivi d'execution",
  non_execution: "Non-execution",
  collective_notice: "Notification de la lettre",
  negotiation_meeting: "Reunion de negociation",
  negotiation_minutes: "PV de negociation",
  mediation: "Mediation",
  arbitration: "Arbitrage",
};

const pvTypeLabels: Record<string, string> = {
  conciliation_totale: "PV de conciliation totale",
  conciliation_partielle: "PV de conciliation partielle",
  non_conciliation: "PV de non-conciliation",
  carence: "PV de carence",
  non_execution: "PV de non-execution",
  transaction_acceptance: "PV d'acceptation de transaction",
  transaction_refusal: "PV de refus de transaction",
  infraction: "PV d'infraction",
};

const claimTypeLabels: Record<string, string> = {
  salaires_impayes: "Salaires impayes",
  indemnite_conge: "Indemnite de conge",
  preavis: "Preavis",
  indemnite_licenciement: "Indemnite de licenciement",
  di_rupture_abusive: "Dommages et interets pour rupture abusive",
  di_harcelement: "Dommages et interets pour harcelement",
  autres: "Autres",
};

const roleLabels: Record<string, string> = {
  employee: "Employe",
  employe: "Employe",
  employer: "Employeur",
  employeur: "Employeur",
  representative: "Representant",
  inspecteur: "Inspecteur",
  rh: "RH",
  juridique: "Juridique",
  direction: "Direction",
};

const documentTypeLabels: Record<string, string> = {
  inspection_attachment: "Piece inspection",
  supporting_document: "Piece justificative",
  contract_review: "Contrat soumis",
  inspection_order: "Convocation / prescription",
  proof: "Preuve complementaire",
};

const auditActionLabels: Record<string, string> = {
  "employee_portal.inspector_case.create": "Creation du dossier inspection",
  "employee_portal.inspector_case.status": "Mise a jour du statut du dossier",
  "employee_portal.inspector_case.assignment": "Affectation inspecteur",
  "employee_portal.inspector_message.create": "Message dossier ajoute",
  "employee_portal.inspection_document.create": "Piece GED ajoutee",
  "employee_portal.inspection_document.version": "Nouvelle version de piece GED",
  "employee_portal.labour_case_claim.create": "Pretention ajoutee",
  "employee_portal.labour_case_event.create": "Evenement dossier ajoute",
  "employee_portal.labour_pv.create": "PV genere",
  "employee_portal.labour_assistant.fallback": "Assistant utilise en mode de secours",
  "compliance.formal_message.create": "Message formel cree",
  "compliance.formal_message.send": "Message formel envoye",
};

const inboxBucketMeta: Record<
  InboxBucketKey,
  { label: string; description: string; tone: string; dot: string }
> = {
  new: {
    label: "Nouveau",
    description: "Depot recent a qualifier ou a prendre en main.",
    tone: "border-cyan-400/25 bg-cyan-400/10 text-cyan-100",
    dot: "bg-cyan-300",
  },
  mine: {
    label: "Assigne a moi",
    description: "Dossiers actifs deja pris en charge par l'inspecteur.",
    tone: "border-emerald-400/25 bg-emerald-400/10 text-emerald-100",
    dot: "bg-emerald-300",
  },
  waiting_employee: {
    label: "En attente agent",
    description: "Un retour ou une piece est attendu du salarie / agent.",
    tone: "border-amber-400/25 bg-amber-400/10 text-amber-100",
    dot: "bg-amber-300",
  },
  waiting_employer: {
    label: "En attente employeur",
    description: "Le prochain mouvement est attendu de l'employeur.",
    tone: "border-fuchsia-400/25 bg-fuchsia-400/10 text-fuchsia-100",
    dot: "bg-fuchsia-300",
  },
  closed: {
    label: "Clos",
    description: "Dossiers termines ou archives.",
    tone: "border-slate-400/25 bg-slate-400/10 text-slate-100",
    dot: "bg-slate-300",
  },
};

function normalizeStatusToken(value: string | null | undefined) {
  return (value || "").trim().toLowerCase();
}

function isClosedCase(item: CaseItem) {
  const status = normalizeStatusToken(item.status);
  return Boolean(item.closed_at) || ["closed", "archived", "cloture", "archive"].includes(status);
}

function isWaitingEmployeeCase(item: CaseItem) {
  const status = normalizeStatusToken(item.status);
  const stage = normalizeStatusToken(item.current_stage);
  return ["en_attente_employe", "waiting_employee"].includes(status)
    || ["waiting_employee", "awaiting_employee", "employee_response"].includes(stage);
}

function isWaitingEmployerCase(item: CaseItem) {
  const status = normalizeStatusToken(item.status);
  const stage = normalizeStatusToken(item.current_stage);
  return ["en_attente_employeur", "waiting_employer"].includes(status)
    || ["waiting_employer", "awaiting_employer"].includes(stage);
}

function isNewCase(item: CaseItem) {
  const status = normalizeStatusToken(item.status);
  const stage = normalizeStatusToken(item.current_stage);
  return ["received", "submitted", "a_qualifier", "new"].includes(status)
    || ["filing", "qualification"].includes(stage);
}

function resolveInboxBucket(item: CaseItem, currentUserId?: number | null): InboxBucketKey {
  if (isClosedCase(item)) {
    return "closed";
  }
  if (isWaitingEmployeeCase(item)) {
    return "waiting_employee";
  }
  if (isWaitingEmployerCase(item)) {
    return "waiting_employer";
  }
  if (isNewCase(item)) {
    return "new";
  }
  if (currentUserId && item.assigned_inspector_user_id === currentUserId) {
    return "mine";
  }
  return "mine";
}

function getDaysWithoutResponse(item: CaseItem) {
  const reference = item.last_response_at || item.updated_at || item.created_at;
  const timestamp = Date.parse(reference);
  if (!Number.isFinite(timestamp)) {
    return 0;
  }
  const diffMs = Date.now() - timestamp;
  return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
}

function getResponseUrgency(daysWithoutResponse: number) {
  if (daysWithoutResponse >= 7) {
    return {
      label: `Sans reponse depuis ${daysWithoutResponse} j`,
      tone: "border-rose-400/30 bg-rose-400/10 text-rose-100",
    };
  }
  if (daysWithoutResponse >= 3) {
    return {
      label: `Sans reponse depuis ${daysWithoutResponse} j`,
      tone: "border-amber-400/30 bg-amber-400/10 text-amber-100",
    };
  }
  return {
    label: daysWithoutResponse > 0 ? `Suivi ${daysWithoutResponse} j` : "Mouvement aujourd'hui",
    tone: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
  };
}

function translatedLabel(value: string | null | undefined, dictionary: Record<string, string> = {}) {
  if (!value) return "-";
  return dictionary[value] || dictionary[value.toLowerCase()] || value.replaceAll("_", " ");
}

function translatedRelatedPayload(payload: Record<string, unknown> | undefined) {
  if (!payload || Object.keys(payload).length === 0) return {};
  return {
    employeur: payload.employer,
    salarie: payload.worker,
    contrat: payload.contract,
    sanctions: payload.sanctions,
  };
}

function buildRelatedSummary(payload: Record<string, unknown> | undefined) {
  const related = translatedRelatedPayload(payload);
  const entries = [
    ["Employeur", (related.employeur as Record<string, unknown> | undefined)?.raison_sociale],
    ["Salarie", [((related.salarie as Record<string, unknown> | undefined)?.prenom || ""), ((related.salarie as Record<string, unknown> | undefined)?.nom || "")].filter(Boolean).join(" ")],
    ["Matricule", (related.salarie as Record<string, unknown> | undefined)?.matricule],
    ["Contrat", (related.contrat as Record<string, unknown> | undefined)?.title],
  ].filter(([, value]) => typeof value === "string" && value.trim().length > 0) as Array<[string, string]>;

  return entries;
}

function badgeClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes("valid") || normalized.includes("conforme") || normalized.includes("published")) {
    return "border-emerald-400/25 bg-emerald-400/10 text-emerald-100";
  }
  if (normalized.includes("reject") || normalized.includes("refus") || normalized.includes("closed")) {
    return "border-rose-400/25 bg-rose-400/10 text-rose-100";
  }
  if (normalized.includes("correction") || normalized.includes("pending") || normalized.includes("review")) {
    return "border-amber-400/25 bg-amber-400/10 text-amber-100";
  }
  return "border-cyan-400/25 bg-cyan-400/10 text-cyan-100";
}

interface InspectorPortalWorkspaceProps {
  initialTab?: TabKey;
}

export default function InspectorPortalWorkspace({
  initialTab = "dashboard",
}: InspectorPortalWorkspaceProps) {
  const { session } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const isInspectorOperator = sessionHasRole(session, [
    "inspecteur",
    "inspection_travail",
    "labor_inspector",
    "labor_inspector_supervisor",
  ]);
  const isJudgeReadonly = sessionHasRole(session, ["judge_readonly"]);
  const isCourtClerkReadonly = sessionHasRole(session, ["court_clerk_readonly"]);
  const isJudicialReadonly = isJudgeReadonly || isCourtClerkReadonly;
  const canManagePortalSettings = sessionHasRole(session, ["admin", "rh", "juridique", "direction", "labor_inspector_supervisor"]);
  const [activeTab, setActiveTab] = useState<TabKey>(initialTab);
  const [inboxView, setInboxView] = useState<InboxBucketKey>("new");
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [selectedOfferId, setSelectedOfferId] = useState<number | null>(null);
  const [offerComment, setOfferComment] = useState("");
  const [publicationMode, setPublicationMode] = useState("external");
  const [publicationUrl, setPublicationUrl] = useState("");
  const [caseDocument, setCaseDocument] = useState<File | null>(null);
  const [selectedParameterCategory, setSelectedParameterCategory] = useState("complaint_category");
  const [messageForm, setMessageForm] = useState({ subject: "", body: "" });
  const [messageRecipients, setMessageRecipients] = useState<number[]>([]);
  const [parameterForm, setParameterForm] = useState({ label: "", description: "" });
  const [assignmentForm, setAssignmentForm] = useState({ employer_id: "", inspector_user_id: "", circonscription: "" });
  const [statusForm, setStatusForm] = useState({
    status: "A_QUALIFIER",
    current_stage: "instruction",
    note: "",
    outcome_summary: "",
    resolution_type: "",
  });
  const [caseFilters, setCaseFilters] = useState({
    status: "",
    case_type: "",
    urgency: "",
    confidentiality: "",
    district: "",
    has_documents: "",
  });
  const [claimForm, setClaimForm] = useState({
    claim_type: "salaires_impayes",
    claimant_party: "employee",
    factual_basis: "",
    amount_requested: "",
    status: "submitted",
    conciliation_outcome: "",
    inspector_observations: "",
  });
  const [eventForm, setEventForm] = useState({
    event_type: "conciliation",
    title: "",
    description: "",
    status: "planned",
    scheduled_at: "",
  });
  const [pvForm, setPvForm] = useState({
    pv_type: "conciliation_totale",
    title: "",
    status: "draft",
    measures_to_execute: "",
    execution_deadline: "",
  });
  const [assistantForm, setAssistantForm] = useState({
    role_context: "inspecteur",
    intent: "qualifier",
    prompt: "",
  });
  const [assistantAnswer, setAssistantAnswer] = useState<Record<string, unknown> | null>(null);
  const availableTabs = useMemo<Array<{ key: TabKey; label: string; icon: typeof ShieldCheckIcon }>>(() => {
    if (isJudicialReadonly) {
      return tabs.filter((tab) => ["cases", "pv", "messages", "help"].includes(tab.key));
    }
    return tabs.filter((tab) => tab.key !== "settings" || canManagePortalSettings);
  }, [canManagePortalSettings, isJudicialReadonly]);

  const { data: employers = [] } = useQuery({
    queryKey: ["inspection-portal", "employers"],
    enabled: isInspectorOperator,
    queryFn: async () => (await api.get<EmployerSummary[]>("/compliance/inspector-employers")).data,
  });

  useEffect(() => {
    if (!isInspectorOperator) {
      return;
    }
    if (!selectedEmployerId && employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
      setAssignmentForm((current) => ({ ...current, employer_id: String(employers[0].id) }));
    }
  }, [employers, isInspectorOperator, selectedEmployerId]);

  useEffect(() => {
    const nextTab = availableTabs.some((item) => item.key === initialTab) ? initialTab : availableTabs[0]?.key ?? "cases";
    setActiveTab(nextTab);
  }, [availableTabs, initialTab]);

  useEffect(() => {
    if (availableTabs.some((item) => item.key === activeTab)) {
      return;
    }
    setActiveTab(availableTabs[0]?.key ?? "cases");
  }, [activeTab, availableTabs]);

  const { data: dashboard } = useQuery({
    queryKey: ["inspection-portal", "dashboard", selectedEmployerId],
    enabled: isInspectorOperator,
    queryFn: async () => (await api.get<DashboardPayload>("/compliance/inspector-dashboard", { params: { employer_id: selectedEmployerId ?? undefined } })).data,
  });

  const { data: employerDetail } = useQuery({
    queryKey: ["inspection-portal", "employer-detail", selectedEmployerId],
    enabled: isInspectorOperator && selectedEmployerId !== null,
    queryFn: async () => (await api.get<EmployerDetail>(`/compliance/inspector-employers/${selectedEmployerId}`)).data,
  });
  const { data: employerWorkers = [] } = useQuery({
    queryKey: ["inspection-portal", "workers", selectedEmployerId],
    enabled: isInspectorOperator && selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<WorkerSummary[]>("/workers", {
        params: { employer_id: selectedEmployerId, page: 1, page_size: 12 },
      })
    ).data,
  });
  const dashboardMetrics = dashboard?.metrics ?? {};
  const dashboardRecentCompanies = dashboard?.recent_companies ?? [];
  const dashboardPendingOffers = dashboard?.pending_job_offers ?? [];
  const dashboardAlerts = dashboard?.alerts ?? [];
  const employerEntity = employerDetail?.employer ?? {};
  const employerDocuments = employerDetail?.documents ?? [];
  const employerObservations = employerDetail?.observations ?? [];
  const employerActions = employerDetail?.actions ?? [];

  const { data: offers = [] } = useQuery({
    queryKey: ["inspection-portal", "offers", selectedEmployerId],
    enabled: isInspectorOperator,
    queryFn: async () => (await api.get<JobOfferSummary[]>("/compliance/job-offers", { params: { employer_id: selectedEmployerId ?? undefined } })).data,
  });

  const { data: cases = [] } = useQuery({
    queryKey: ["inspection-portal", "cases", selectedEmployerId, caseFilters],
    queryFn: async () => (
      await api.get<CaseItem[]>("/employee-portal/inspection-cases", {
        params: {
          employer_id: selectedEmployerId ?? undefined,
          status: caseFilters.status || undefined,
          case_type: caseFilters.case_type || undefined,
          urgency: caseFilters.urgency || undefined,
          confidentiality: caseFilters.confidentiality || undefined,
          district: caseFilters.district || undefined,
          has_documents: caseFilters.has_documents ? caseFilters.has_documents === "true" : undefined,
        },
      })
    ).data,
  });

  useEffect(() => {
    if (selectedCaseId && cases.some((item) => item.id === selectedCaseId)) {
      return;
    }
    setSelectedCaseId(cases[0]?.id ?? null);
  }, [cases, selectedCaseId]);

  const { data: caseMessages = [] } = useQuery({
    queryKey: ["inspection-portal", "case-messages", selectedCaseId],
    enabled: selectedCaseId !== null,
    queryFn: async () => (await api.get<Array<{ id: number; body: string; created_at: string; sender_role: string }>>(`/employee-portal/inspection-cases/${selectedCaseId}/messages`)).data,
  });

  const { data: caseDocuments = [] } = useQuery({
    queryKey: ["inspection-portal", "case-documents", selectedCaseId],
    enabled: selectedCaseId !== null,
    queryFn: async () => (await api.get<InspectionDocument[]>(`/employee-portal/inspection-cases/${selectedCaseId}/documents`)).data,
  });

  const { data: workspace } = useQuery({
    queryKey: ["inspection-portal", "workspace", selectedCaseId],
    enabled: selectedCaseId !== null,
    queryFn: async () => (await api.get<LabourWorkspace>(`/employee-portal/inspection-cases/${selectedCaseId}/workspace`)).data,
  });

  const { data: helpPayload } = useQuery({
    queryKey: ["inspection-portal", "help"],
    queryFn: async () => (
      await api.get<HelpPayload>("/employee-portal/inspection-help", {
        params: { role_context: isJudgeReadonly ? "juge" : isCourtClerkReadonly ? "greffe" : "inspecteur" },
      })
    ).data,
  });

  const { data: formalMessages = [] } = useQuery({
    queryKey: ["inspection-portal", "formal-messages", selectedEmployerId],
    enabled: isInspectorOperator,
    queryFn: async () => (await api.get<FormalMessage[]>("/compliance/formal-messages", { params: { employer_id: selectedEmployerId ?? undefined } })).data,
  });

  const { data: parameterItems = [] } = useQuery({
    queryKey: ["inspection-portal", "parameters", selectedParameterCategory],
    enabled: isInspectorOperator,
    queryFn: async () => (await api.get<ParameterItem[]>("/compliance/parameters", { params: { category: selectedParameterCategory } })).data,
  });

  const { data: inspectors = [] } = useQuery({
    queryKey: ["inspection-portal", "inspectors", selectedEmployerId],
    enabled: isInspectorOperator && selectedEmployerId !== null,
    queryFn: async () => (await api.get<InspectorUser[]>("/employee-portal/inspectors", { params: { employer_id: selectedEmployerId ?? undefined } })).data,
  });

  useEffect(() => {
    if (selectedOfferId && offers.some((item) => item.id === selectedOfferId)) {
      return;
    }
    setSelectedOfferId(offers[0]?.id ?? null);
  }, [offers, selectedOfferId]);

  const selectedOffer = useMemo(
    () => offers.find((item) => item.id === selectedOfferId) ?? offers[0] ?? null,
    [offers, selectedOfferId],
  );
  const selectedCase = useMemo(() => cases.find((item) => item.id === selectedCaseId) ?? null, [cases, selectedCaseId]);
  const employerNameById = useMemo(
    () => Object.fromEntries(employers.map((item) => [item.id, item.raison_sociale])),
    [employers],
  );
  const assistantPreview = useMemo(() => {
    if (!selectedCase || !workspace) {
      return {
        statut: "Aucun dossier selectionne",
        instruction: "Selectionnez un dossier pour charger le contexte d'assistance.",
      };
    }
    return {
      dossier: selectedCase.case_number,
      objet: selectedCase.subject,
      statut: translatedLabel(selectedCase.status, statusLabels),
      etape: translatedLabel(selectedCase.current_stage, statusLabels),
      entreprise: employerNameById[selectedCase.employer_id] || `Entreprise #${selectedCase.employer_id}`,
      pretentions: workspace.claims.length,
      evenements: workspace.events.length,
      pv: workspace.pv_records.length,
      messages: workspace.messages.length,
      pieces: workspace.documents.length,
      resume_juridique: workspace.legal_summary || {},
      suggestion: "Utilisez l'assistant pour preparer une convocation, qualifier le dossier ou generer un projet de PV.",
    };
  }, [employerNameById, selectedCase, workspace]);
  const inboxBuckets = useMemo(() => {
    const bucketEntries: Array<{ key: InboxBucketKey; items: CaseItem[] }> = [
      { key: "new", items: [] },
      { key: "mine", items: [] },
      { key: "waiting_employee", items: [] },
      { key: "waiting_employer", items: [] },
      { key: "closed", items: [] },
    ];
    const bucketMap = new Map(bucketEntries.map((entry) => [entry.key, entry]));
    const sortedCases = [...cases].sort((left, right) => {
      const leftTs = Date.parse(left.last_response_at || left.updated_at || left.created_at);
      const rightTs = Date.parse(right.last_response_at || right.updated_at || right.created_at);
      return rightTs - leftTs;
    });
    sortedCases.forEach((item) => {
      const bucket = resolveInboxBucket(item, session?.user_id);
      bucketMap.get(bucket)?.items.push(item);
    });
    return bucketEntries.map((entry) => ({
      ...entry,
      ...inboxBucketMeta[entry.key],
      count: entry.items.length,
    }));
  }, [cases, session?.user_id]);
  const activeInboxBucket = useMemo(
    () => inboxBuckets.find((item) => item.key === inboxView) ?? inboxBuckets[0],
    [inboxBuckets, inboxView],
  );
  const inboxCases = activeInboxBucket?.items ?? [];
  const selectedCaseBucket = selectedCase ? resolveInboxBucket(selectedCase, session?.user_id) : null;

  useEffect(() => {
    if (!inboxBuckets.length) {
      return;
    }
    if ((activeInboxBucket?.count ?? 0) > 0) {
      return;
    }
    const fallbackBucket = inboxBuckets.find((item) => item.count > 0);
    if (fallbackBucket && fallbackBucket.key !== inboxView) {
      setInboxView(fallbackBucket.key);
    }
  }, [activeInboxBucket, inboxBuckets, inboxView]);

  useEffect(() => {
    if (activeTab !== "messages") {
      return;
    }
    if (selectedCaseId && inboxCases.some((item) => item.id === selectedCaseId)) {
      return;
    }
    setSelectedCaseId(inboxCases[0]?.id ?? null);
  }, [activeTab, inboxCases, selectedCaseId]);

  useEffect(() => {
    if (!selectedCase) {
      return;
    }
    setStatusForm((current) => ({
      ...current,
      status: selectedCase.status || current.status,
      current_stage: selectedCase.current_stage || current.current_stage,
      outcome_summary: selectedCase.outcome_summary || "",
      resolution_type: selectedCase.resolution_type || "",
      note: "",
    }));
  }, [selectedCase]);

  const refreshPortal = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "employers"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "employer-detail"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "offers"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "cases"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "formal-messages"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "case-documents"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "case-messages"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "workspace"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "parameters"] }),
      queryClient.invalidateQueries({ queryKey: ["inspection-portal", "inspectors"] }),
    ]);
  };

  const openMetricView = (metricKey: string) => {
    switch (metricKey) {
      case "pending_job_offers":
      case "pending_corrections":
        setActiveTab("offers");
        break;
      case "complaints_new":
      case "cases_to_qualify":
        setCaseFilters((current) => ({ ...current, status: "A_QUALIFIER" }));
        setActiveTab("cases");
        break;
      case "complaints_closed":
      case "pv_issued":
        setInboxView("closed");
        setActiveTab("messages");
        break;
      case "waiting_employer":
        setInboxView("waiting_employer");
        setActiveTab("messages");
        break;
      case "waiting_employee":
        setInboxView("waiting_employee");
        setActiveTab("messages");
        break;
      default:
        setActiveTab("cases");
        break;
    }
  };

  const updateCaseStatusMutation = useMutation({
    mutationFn: async (payload?: Partial<typeof statusForm>) => {
      if (!selectedCaseId) throw new Error("Selectionnez un dossier.");
      const nextPayload = { ...statusForm, ...(payload ?? {}) };
      return (await api.patch(`/employee-portal/inspection-cases/${selectedCaseId}/status`, nextPayload)).data;
    },
    onSuccess: async (_, payload) => {
      if (payload) {
        setStatusForm((current) => ({ ...current, ...payload }));
      }
      toast.success("Statut mis a jour", "Le dossier a ete actualise.");
      await refreshPortal();
    },
    onError: (error) => toast.error("Mise a jour impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const uploadCaseDocumentMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCaseId || !caseDocument) throw new Error("Selectionnez un dossier et un fichier.");
      const formData = new FormData();
      formData.append("title", caseDocument.name);
      formData.append("document_type", "inspection_attachment");
      formData.append("description", "Depot depuis le portail inspection");
      formData.append("visibility", "case_parties");
      formData.append("confidentiality", "restricted");
      formData.append("notes", "Ajout inspection");
      formData.append("file", caseDocument);
      return (await api.post(`/employee-portal/inspection-cases/${selectedCaseId}/documents/upload`, formData)).data;
    },
    onSuccess: async () => {
      setCaseDocument(null);
      toast.success("Document ajoute", "La piece a ete rattachee au dossier.");
      await refreshPortal();
    },
    onError: (error) => toast.error("Depot impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const offerDecisionMutation = useMutation({
    mutationFn: async (action: string) => {
      if (!selectedOffer) throw new Error("Aucune offre selectionnee.");
      if (["request_correction", "refuse"].includes(action) && !offerComment.trim()) {
        throw new Error("Un motif est obligatoire.");
      }
      return (await api.post(`/compliance/job-offers/${selectedOffer.id}/decision`, { action, comment: offerComment || null, publication_mode: publicationMode || null, publication_url: publicationUrl || null })).data;
    },
    onSuccess: async () => {
      toast.success("Decision enregistree", "Le workflow de l'offre a ete mis a jour.");
      setOfferComment("");
      await refreshPortal();
    },
    onError: (error) => toast.error("Decision impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const createMessageMutation = useMutation({
    mutationFn: async (sendNow: boolean) => {
      if (!messageForm.subject.trim()) throw new Error("L'objet est obligatoire.");
      if (!messageRecipients.length) throw new Error("Selectionnez au moins un destinataire.");
      return (
        await api.post<FormalMessage>("/compliance/formal-messages", {
          subject: messageForm.subject,
          body: messageForm.body,
          message_scope: messageRecipients.length > 1 ? "broadcast" : "individual",
          related_entity_type: selectedCaseId ? "inspector_case" : null,
          related_entity_id: selectedCaseId ? String(selectedCaseId) : null,
          recipients: messageRecipients.map((employerId) => ({ employer_id: employerId, recipient_type: "employer" })),
          send_now: sendNow,
        })
      ).data;
    },
    onSuccess: async () => {
      toast.success("Message enregistre", "Le journal d'envoi a ete mis a jour.");
      setMessageForm({ subject: "", body: "" });
      setMessageRecipients([]);
      await refreshPortal();
    },
    onError: (error) => toast.error("Envoi impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const sendDraftMutation = useMutation({
    mutationFn: async (messageId: number) => (await api.post(`/compliance/formal-messages/${messageId}/send`)).data,
    onSuccess: async () => {
      toast.success("Message envoye", "Le message formel a ete emis.");
      await refreshPortal();
    },
  });

  const createParameterMutation = useMutation({
    mutationFn: async () => (await api.post("/compliance/parameters", { category: selectedParameterCategory, label: parameterForm.label, description: parameterForm.description || null, payload: {}, is_active: true })).data,
    onSuccess: async () => {
      toast.success("Parametre ajoute", "Le referentiel a ete enrichi.");
      setParameterForm({ label: "", description: "" });
      await refreshPortal();
    },
    onError: (error) => toast.error("Ajout impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const createAssignmentMutation = useMutation({
    mutationFn: async () => (
      await api.post("/compliance/inspector-assignments", {
        employer_id: Number(assignmentForm.employer_id),
        inspector_user_id: Number(assignmentForm.inspector_user_id),
        assignment_scope: "portfolio",
        circonscription: assignmentForm.circonscription || null,
      })
    ).data,
    onSuccess: async () => {
      toast.success("Affectation creee", "Le portefeuille inspecteur a ete mis a jour.");
      setAssignmentForm((current) => ({ ...current, inspector_user_id: "", circonscription: "" }));
      await refreshPortal();
    },
    onError: (error) => toast.error("Affectation impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const createClaimMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCaseId) throw new Error("Selectionnez un dossier.");
      return (
        await api.post(`/employee-portal/inspection-cases/${selectedCaseId}/claims`, {
          claim_type: claimForm.claim_type,
          claimant_party: claimForm.claimant_party,
          factual_basis: claimForm.factual_basis,
          amount_requested: claimForm.amount_requested ? Number(claimForm.amount_requested) : null,
          status: claimForm.status,
          conciliation_outcome: claimForm.conciliation_outcome || null,
          inspector_observations: claimForm.inspector_observations || null,
          metadata: {},
        })
      ).data;
    },
    onSuccess: async () => {
      toast.success("Pretention ajoutee", "La demande est rattachee au dossier sans decision automatique.");
      setClaimForm({ claim_type: "salaires_impayes", claimant_party: "employee", factual_basis: "", amount_requested: "", status: "submitted", conciliation_outcome: "", inspector_observations: "" });
      await refreshPortal();
    },
    onError: (error) => toast.error("Pretention impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const createEventMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCaseId) throw new Error("Selectionnez un dossier.");
      return (
        await api.post(`/employee-portal/inspection-cases/${selectedCaseId}/events`, {
          event_type: eventForm.event_type,
          title: eventForm.title || eventForm.event_type,
          description: eventForm.description || null,
          status: eventForm.status,
          scheduled_at: eventForm.scheduled_at ? new Date(eventForm.scheduled_at).toISOString() : null,
          participants: [],
          metadata: {},
        })
      ).data;
    },
    onSuccess: async () => {
      toast.success("Evenement ajoute", "La chronologie du dossier a ete mise a jour.");
      setEventForm({ event_type: "conciliation", title: "", description: "", status: "planned", scheduled_at: "" });
      await refreshPortal();
    },
    onError: (error) => toast.error("Evenement impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const createPvMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCaseId) throw new Error("Selectionnez un dossier.");
      return (
        await api.post(`/employee-portal/inspection-cases/${selectedCaseId}/pv`, {
          pv_type: pvForm.pv_type,
          title: pvForm.title || null,
          status: pvForm.status,
          measures_to_execute: pvForm.measures_to_execute || null,
          execution_deadline: pvForm.execution_deadline ? new Date(pvForm.execution_deadline).toISOString() : null,
          metadata: {},
        })
      ).data;
    },
    onSuccess: async () => {
      toast.success("PV genere", "Un brouillon versionne est disponible dans le dossier.");
      setPvForm({ pv_type: "conciliation_totale", title: "", status: "draft", measures_to_execute: "", execution_deadline: "" });
      await refreshPortal();
    },
    onError: (error) => toast.error("PV impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const assistantMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCaseId) throw new Error("Selectionnez un dossier.");
      return (
        await api.post<{ response: Record<string, unknown> }>(`/employee-portal/inspection-cases/${selectedCaseId}/assistant`, {
          role_context: assistantForm.role_context,
          intent: assistantForm.intent,
          prompt: assistantForm.prompt,
          include_case_summary: true,
        })
      ).data;
    },
    onSuccess: (data) => {
      setAssistantAnswer(data.response);
      toast.success("Assistant disponible", "Reponse de secours generee cote serveur.");
    },
    onError: (error) => toast.error("Assistant indisponible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.96),rgba(20,83,45,0.25),rgba(8,145,178,0.55))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Inspection du travail Madagascar
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Portail inspecteur, controles, saisines et messages formels</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Vue unifiee pour les entreprises suivies, les dossiers transmis, les plaintes, les offres soumises a validation et les echanges administratifs traces.
            </p>
          </div>

          {isInspectorOperator ? (
            <div className="w-full max-w-sm">
              <label className={labelClass}>Entreprise / périmètre</label>
              <select value={selectedEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClass}>
                {employers.map((item) => (
                  <option key={item.id} value={item.id}>{item.raison_sociale}</option>
                ))}
              </select>
            </div>
          ) : (
            <div className="inline-flex items-center rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm font-semibold text-cyan-100">
              {isJudgeReadonly ? "Accès juge" : "Accès greffe"}
            </div>
          )}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          {availableTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-semibold transition ${activeTab === tab.key ? "border-cyan-300/40 bg-cyan-400/10 text-cyan-100" : "border-white/10 bg-slate-950/40 text-slate-300 hover:text-white"}`}
              >
                <Icon className="h-5 w-5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {activeTab === "dashboard" ? (
        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="grid gap-6">
            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Indicateurs clefs</h2>
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                {Object.entries(dashboardMetrics).map(([key, value]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => openMetricView(key)}
                    className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-left transition hover:bg-white/10"
                  >
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{translatedLabel(key, metricLabels)}</div>
                    <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Entreprises recentes</h2>
              <div className="mt-6 space-y-3">
                {dashboardRecentCompanies.map((item) => (
                  <button key={item.id} type="button" onClick={() => { setSelectedEmployerId(item.id); setActiveTab("companies"); }} className="flex w-full items-center justify-between rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-left">
                    <div>
                      <div className="font-semibold text-white">{item.raison_sociale}</div>
                      <div className="mt-1 text-sm text-slate-400">{item.secteur || "Secteur non renseigne"}</div>
                    </div>
                    <div className="text-sm text-cyan-200">{item.open_cases} dossier(s)</div>
                  </button>
                ))}
              </div>
            </div>

            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Salaries visibles dans le portefeuille</h2>
              <div className="mt-6 grid gap-3 md:grid-cols-2">
                {employerWorkers.length ? employerWorkers.slice(0, 8).map((item) => (
                  <div key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    <div className="font-semibold text-white">{item.nom} {item.prenom}</div>
                    <div className="mt-1 text-slate-400">{item.poste || "Poste non renseigne"} {item.matricule ? `- ${item.matricule}` : ""}</div>
                    <div className="text-cyan-200">{item.departement || "Departement non renseigne"}</div>
                  </div>
                )) : <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-400">Aucun salarie visible pour l'entreprise selectionnee.</div>}
              </div>
            </div>
          </div>

          <div className="grid gap-6">
            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Offres en attente</h2>
              <div className="mt-6 space-y-3">
                {dashboardPendingOffers.map((offer) => (
                  <button
                    key={offer.id}
                    type="button"
                    onClick={() => {
                      setSelectedEmployerId(offer.employer_id);
                      setSelectedOfferId(offer.id);
                      setActiveTab("offers");
                    }}
                    className="w-full rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-left transition hover:bg-white/10"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-white">{offer.title}</div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(offer.workflow_status)}`}>{translatedLabel(offer.workflow_status, statusLabels)}</span>
                    </div>
                    <div className="mt-1 text-sm text-slate-400">{offer.employer_name}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Alertes critiques</h2>
              <div className="mt-6 space-y-3">
                {dashboardAlerts.length ? dashboardAlerts.map((alert) => (
                  <button
                    key={alert.case_id}
                    type="button"
                    onClick={() => {
                      setSelectedCaseId(alert.case_id);
                      setActiveTab("messages");
                    }}
                    className="w-full rounded-[1.5rem] border border-amber-400/20 bg-amber-400/10 p-4 text-left transition hover:bg-amber-400/15"
                  >
                    <div className="font-semibold text-white">{alert.case_number}</div>
                    <div className="mt-1 text-sm text-slate-200">{alert.subject}</div>
                  </button>
                )) : <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-400">Aucune alerte critique dans le perimetre courant.</div>}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "companies" ? (
        <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Portefeuille entreprises</h2>
            <div className="mt-6 space-y-3">
              {employers.map((item) => (
                <button key={item.id} type="button" onClick={() => setSelectedEmployerId(item.id)} className={`w-full rounded-[1.5rem] border p-4 text-left ${selectedEmployerId === item.id ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"}`}>
                  <div className="font-semibold text-white">{item.raison_sociale}</div>
                  <div className="mt-2 text-sm text-slate-400">{item.nif || "NIF non renseigne"} | {item.stat || "STAT non renseigne"}</div>
                  <div className="mt-2 text-xs text-cyan-200">{item.open_cases} dossiers | {item.pending_job_offers} offres en attente</div>
                </button>
              ))}
            </div>
          </div>

          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Fiche entreprise inspection</h2>
            {employerDetail ? (
              <div className="mt-6 space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  {Object.entries(employerEntity).map(([key, value]) => (
                    <div key={key} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{translatedLabel(key, fieldLabels)}</div>
                      <div className="mt-2 text-sm text-white">{String(value ?? "-")}</div>
                    </div>
                  ))}
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="font-semibold text-white">Documents</div>
                    <div className="mt-3 space-y-2 text-sm text-slate-300">{employerDocuments.slice(0, 4).map((document) => <div key={document.id}>{document.title}</div>)}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="font-semibold text-white">Observations</div>
                    <div className="mt-3 space-y-2 text-sm text-slate-300">{employerObservations.slice(0, 4).map((item) => <div key={item.id}>{item.message}</div>)}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="font-semibold text-white">Journal</div>
                    <div className="mt-3 space-y-2 text-sm text-slate-300">{employerActions.slice(0, 4).map((item) => <div key={item.id}>{translatedLabel(item.action, auditActionLabels)}</div>)}</div>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-white">Salaries de l'entreprise</div>
                    <button type="button" onClick={() => setActiveTab("cases")} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200">
                      Ouvrir les dossiers
                    </button>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {employerWorkers.length ? employerWorkers.map((worker) => (
                      <div key={worker.id} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-300">
                        <div className="font-semibold text-white">{worker.nom} {worker.prenom}</div>
                        <div className="mt-1 text-slate-400">{worker.poste || "Poste non renseigne"}</div>
                        <div className="text-slate-400">{worker.service || worker.departement || "Service non renseigne"}</div>
                        {worker.matricule ? <div className="mt-2 text-cyan-200">{worker.matricule}</div> : null}
                      </div>
                    )) : <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-400">Aucun salarie visible sur le perimetre de cette entreprise.</div>}
                  </div>
                </div>
              </div>
            ) : <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-400">Aucune entreprise selectionnee.</div>}
          </div>
        </section>
      ) : null}

      {activeTab === "offers" ? (
        <section className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Offres soumises</h2>
            <div className="mt-6 space-y-3">
              {offers.map((offer) => (
                <button
                  key={offer.id}
                  type="button"
                  onClick={() => setSelectedOfferId(offer.id)}
                  className={`w-full rounded-[1.5rem] border p-4 text-left transition ${
                    selectedOffer?.id === offer.id
                      ? "border-cyan-300/40 bg-cyan-400/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-white">{offer.title}</div>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(offer.workflow_status)}`}>{translatedLabel(offer.workflow_status, statusLabels)}</span>
                  </div>
                  <div className="mt-1 text-sm text-slate-400">{offer.employer_name}</div>
                  {offer.validation_comment ? <div className="mt-3 text-sm text-amber-100">{offer.validation_comment}</div> : null}
                </button>
              ))}
            </div>
          </div>
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Decision inspection</h2>
            {selectedOffer ? (
              <div className="mt-6 space-y-4">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="font-semibold text-white">{selectedOffer.title}</div>
                  <div className="mt-1 text-sm text-slate-400">{selectedOffer.employer_name}</div>
                  <div className="mt-3 grid gap-2 text-sm text-slate-300">
                    {selectedOffer.description ? (
                      <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">{selectedOffer.description}</div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-white/10 bg-slate-950/30 p-3 text-slate-400">
                        Aucune description detaillee disponible sur cette offre.
                      </div>
                    )}
                    <div>Departement: <span className="font-semibold text-white">{selectedOffer.department || "-"}</span></div>
                    <div>Localisation: <span className="font-semibold text-white">{selectedOffer.location || "-"}</span></div>
                    <div>Type de contrat: <span className="font-semibold text-white">{selectedOffer.contract_type || "-"}</span></div>
                    <div>Soumise inspection: <span className="font-semibold text-white">{selectedOffer.submitted_to_inspection_at ? new Date(selectedOffer.submitted_to_inspection_at).toLocaleString("fr-FR") : "-"}</span></div>
                    <div>Derniere revue: <span className="font-semibold text-white">{selectedOffer.last_reviewed_at ? new Date(selectedOffer.last_reviewed_at).toLocaleString("fr-FR") : "-"}</span></div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(selectedOffer.status)}`}>{translatedLabel(selectedOffer.status, statusLabels)}</span>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(selectedOffer.workflow_status)}`}>{translatedLabel(selectedOffer.workflow_status, statusLabels)}</span>
                    {selectedOffer.announcement_status ? (
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(selectedOffer.announcement_status)}`}>{translatedLabel(selectedOffer.announcement_status, statusLabels)}</span>
                    ) : null}
                  </div>
                  {(selectedOffer.attachments ?? []).length ? (
                    <div className="mt-3 text-xs text-cyan-200">
                      Pieces jointes: {(selectedOffer.attachments ?? []).map((item) => item.name || item.path || "-").join(", ")}
                    </div>
                  ) : null}
                </div>
                <textarea className={`${inputClass} min-h-[140px]`} value={offerComment} onChange={(event) => setOfferComment(event.target.value)} placeholder="Motif / observations de l'inspection" />
                <div className="grid gap-4 md:grid-cols-2">
                  <input className={inputClass} value={publicationMode} onChange={(event) => setPublicationMode(event.target.value)} placeholder="Mode de publication" />
                  <input className={inputClass} value={publicationUrl} onChange={(event) => setPublicationUrl(event.target.value)} placeholder="Lien de publication" />
                </div>
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={() => { if (window.confirm("Valider definitivement cette offre ?")) offerDecisionMutation.mutate("approve"); }} className="rounded-2xl bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950">Valider</button>
                  <button type="button" onClick={() => { if (window.confirm("Demander une correction ?")) offerDecisionMutation.mutate("request_correction"); }} className="rounded-2xl bg-amber-400 px-4 py-3 text-sm font-semibold text-slate-950">Demander correction</button>
                  <button type="button" onClick={() => { if (window.confirm("Refuser definitivement cette offre ?")) offerDecisionMutation.mutate("refuse"); }} className="rounded-2xl bg-rose-400 px-4 py-3 text-sm font-semibold text-slate-950">Refuser</button>
                  <button type="button" onClick={() => offerDecisionMutation.mutate("record_publication")} className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white">Enregistrer publication</button>
                </div>
              </div>
            ) : <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-400">Aucune offre disponible pour le moment.</div>}
          </div>
        </section>
      ) : null}

      {activeTab === "cases" ? (
        <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          <div className="grid gap-6">
            {isInspectorOperator ? (
              <div className={shellCard}>
                <h2 className="text-xl font-semibold text-white">Reception des dossiers</h2>
                <div className="mt-6 grid gap-4">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                    Les dossiers sont crees par les flux employe/employeur et remontent ici automatiquement. Cette vue inspecteur est reservee a la qualification, l'affectation, la conciliation, la production de PV et la cloture.
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setCaseFilters((current) => ({ ...current, status: "A_QUALIFIER" }));
                    }}
                    className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white"
                  >
                    Afficher les dossiers a qualifier
                  </button>
                </div>
              </div>
            ) : null}

            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Liste des dossiers</h2>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <select className={inputClass} value={caseFilters.status} onChange={(event) => setCaseFilters((current) => ({ ...current, status: event.target.value }))}>
                  <option value="">Tous statuts</option><option value="SOUMIS">Soumis</option><option value="A_QUALIFIER">A qualifier</option><option value="EN_ATTENTE_EMPLOYEUR">Attente employeur</option><option value="EN_CONCILIATION">Conciliation</option><option value="PV_A_EMETTRE">PV a emettre</option><option value="PV_EMIS">PV emis</option><option value="NON_EXECUTE">Non execute</option><option value="CLOTURE">Cloture</option>
                </select>
                <select className={inputClass} value={caseFilters.case_type} onChange={(event) => setCaseFilters((current) => ({ ...current, case_type: event.target.value }))}>
                  <option value="">Tous types</option><option value="individual_complaint">Plainte</option><option value="collective_grievance">Doleance collective</option><option value="sanction_review">Sanction</option><option value="delegate_protection">Delegue protege</option><option value="infraction_report">Infraction</option>
                </select>
                <select className={inputClass} value={caseFilters.urgency} onChange={(event) => setCaseFilters((current) => ({ ...current, urgency: event.target.value }))}>
                  <option value="">Toutes urgences</option><option value="normal">Normal</option><option value="high">Urgent</option>
                </select>
                <select className={inputClass} value={caseFilters.has_documents} onChange={(event) => setCaseFilters((current) => ({ ...current, has_documents: event.target.value }))}>
                  <option value="">Pieces jointes: indifferent</option><option value="true">Avec pieces</option><option value="false">Sans piece</option>
                </select>
                <input className={inputClass} value={caseFilters.district} onChange={(event) => setCaseFilters((current) => ({ ...current, district: event.target.value }))} placeholder="Filtrer par district / ressort" />
                <select className={inputClass} value={caseFilters.confidentiality} onChange={(event) => setCaseFilters((current) => ({ ...current, confidentiality: event.target.value }))}>
                  <option value="">Toutes confidentialites</option><option value="restricted">Restreint</option><option value="confidential">Confidentiel</option><option value="sensitive">Sensible</option>
                </select>
              </div>
              <div className="mt-6 space-y-3">
                {cases.map((item) => (
                  <button key={item.id} type="button" onClick={() => setSelectedCaseId(item.id)} className={`w-full rounded-[1.5rem] border p-4 text-left ${selectedCaseId === item.id ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"}`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-white">{item.case_number}</div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(item.status)}`}>{translatedLabel(item.status, statusLabels)}</span>
                    </div>
                    <div className="mt-1 text-sm text-slate-400">{item.subject}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Traitement du dossier</h2>
            {selectedCase ? (
              <div className="mt-6 space-y-6">
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="font-semibold text-white">{selectedCase.case_number}</div>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(selectedCase.status)}`}>{translatedLabel(selectedCase.status, statusLabels)}</span>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(selectedCase.current_stage)}`}>{translatedLabel(selectedCase.current_stage, statusLabels)}</span>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">{selectedCase.description}</div>
                </div>
                {isInspectorOperator ? (
                  <>
                    <div className="grid gap-4 md:grid-cols-2">
                      <select className={inputClass} value={statusForm.status} onChange={(event) => setStatusForm((current) => ({ ...current, status: event.target.value }))}><option value="A_QUALIFIER">A qualifier</option><option value="EN_ATTENTE_PIECES">Attente pieces</option><option value="EN_ATTENTE_EMPLOYEUR">Attente employeur</option><option value="EN_ATTENTE_EMPLOYE">Attente employe</option><option value="EN_CONCILIATION">Conciliation</option><option value="CONCILIATION_PARTIELLE">Conciliation partielle</option><option value="NON_CONCILIE">Non concilie</option><option value="CARENCE">Carence</option><option value="PV_A_EMETTRE">PV a emettre</option><option value="PV_EMIS">PV emis</option><option value="EN_SUIVI_EXECUTION">Suivi execution</option><option value="NON_EXECUTE">Non execute</option><option value="ORIENTE_JURIDICTION">Oriente juridiction</option><option value="CLOTURE">Cloture</option></select>
                      <input className={inputClass} value={statusForm.current_stage} onChange={(event) => setStatusForm((current) => ({ ...current, current_stage: event.target.value }))} placeholder="Etape courante" />
                    </div>
                    <textarea className={`${inputClass} min-h-[100px]`} value={statusForm.note} onChange={(event) => setStatusForm((current) => ({ ...current, note: event.target.value }))} placeholder="Note de traitement" />
                    <div className="grid gap-4 md:grid-cols-2">
                      <input className={inputClass} value={statusForm.outcome_summary} onChange={(event) => setStatusForm((current) => ({ ...current, outcome_summary: event.target.value }))} placeholder="Resume / issue" />
                      <input className={inputClass} value={statusForm.resolution_type} onChange={(event) => setStatusForm((current) => ({ ...current, resolution_type: event.target.value }))} placeholder="Type de resolution" />
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <button type="button" onClick={() => updateCaseStatusMutation.mutate({})} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Mettre a jour</button>
                      <input type="file" className="block text-sm text-slate-300" onChange={(event) => setCaseDocument(event.target.files?.[0] ?? null)} />
                      <button type="button" onClick={() => uploadCaseDocumentMutation.mutate()} className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white">Ajouter une piece</button>
                    </div>
                  </>
                ) : isCourtClerkReadonly ? (
                  <div className="flex flex-wrap gap-3">
                    <input type="file" className="block text-sm text-slate-300" onChange={(event) => setCaseDocument(event.target.files?.[0] ?? null)} />
                    <button type="button" onClick={() => uploadCaseDocumentMutation.mutate()} className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white">Associer une piece</button>
                  </div>
                ) : null}
                <div className="grid gap-6 md:grid-cols-2">
                  <div><h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Messages</h3><div className="mt-4 space-y-3">{caseMessages.map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{translatedLabel(item.sender_role, roleLabels)}</div><div className="mt-2">{item.body}</div></div>)}</div></div>
                  <div><h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Documents</h3><div className="mt-4 space-y-3">{(caseDocuments ?? []).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{item.title}</div><div className="mt-2 text-slate-400">{translatedLabel(item.document_type, documentTypeLabels)} | version {item.current_version_number}</div></div>)}</div></div>
                </div>
                <div className="grid gap-6 xl:grid-cols-3">
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Pretentions</h3>
                    <div className="mt-4 space-y-3">{(workspace?.claims ?? []).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{translatedLabel(item.claim_type, claimTypeLabels)}</div><div className="mt-1">{item.factual_basis}</div><div className="mt-2 text-cyan-200">{item.amount_requested ? `${item.amount_requested} MGA demandes` : "Montant non renseigne"}</div></div>)}</div>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Chronologie</h3>
                    <div className="mt-4 space-y-3">{(workspace?.events ?? []).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{item.title}</div><div className="mt-1 text-slate-400">{translatedLabel(item.event_type, eventTypeLabels)} | {translatedLabel(item.status, statusLabels)}</div><div className="mt-1 text-cyan-200">{item.scheduled_at ?? "Date non planifiee"}</div></div>)}</div>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">PV</h3>
                    <div className="mt-4 space-y-3">{(workspace?.pv_records ?? []).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{item.pv_number}</div><div className="mt-1 text-slate-400">{translatedLabel(item.pv_type, pvTypeLabels)} v{item.version_number}</div><div className="mt-1 text-cyan-200">{translatedLabel(item.status, statusLabels)}</div></div>)}</div>
                  </div>
                </div>
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Synthese du dossier</h3>
                    <div className="mt-4 space-y-3">
                      {buildRelatedSummary(workspace?.related).length ? buildRelatedSummary(workspace?.related).map(([label, value]) => (
                        <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</div>
                          <div className="mt-2 font-semibold text-white">{value}</div>
                        </div>
                      )) : (
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
                          Aucune information complementaire a afficher.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-400">Selectionnez un dossier pour le traiter.</div>}
          </div>
        </section>
      ) : null}

      {activeTab === "collective" ? (
        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Doleances collectives</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">Circuit distinct: lettre de doleances, signataires, negociation, PV, mediation puis arbitrage si necessaire.</p>
            <div className="mt-6 grid gap-4">
              <button type="button" onClick={() => { setCaseFilters((current) => ({ ...current, case_type: "collective_grievance" })); setActiveTab("cases"); }} className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white">Ouvrir les dossiers collectifs</button>
              {(cases.filter((item) => item.case_type === "collective_grievance" || item.case_type === "doleance_collective")).map((item) => <button key={item.id} type="button" onClick={() => setSelectedCaseId(item.id)} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-left text-sm text-slate-300"><div className="font-semibold text-white">{item.case_number}</div><div className="mt-1">{item.subject}</div><div className="mt-2 text-cyan-200">{translatedLabel(item.status, statusLabels)}</div></button>)}
            </div>
          </div>
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Jalons collectifs</h2>
            <div className="mt-6 grid gap-4">
              <select className={inputClass} value={eventForm.event_type} onChange={(event) => setEventForm((current) => ({ ...current, event_type: event.target.value }))}><option value="collective_notice">Notification de la lettre</option><option value="negotiation_meeting">Premiere reunion de negociation</option><option value="negotiation_minutes">PV de negociation</option><option value="mediation">Mediation</option><option value="arbitration">Arbitrage</option></select>
              <input className={inputClass} value={eventForm.title} onChange={(event) => setEventForm((current) => ({ ...current, title: event.target.value }))} placeholder="Titre du jalon" />
              <input type="datetime-local" className={inputClass} value={eventForm.scheduled_at} onChange={(event) => setEventForm((current) => ({ ...current, scheduled_at: event.target.value }))} />
              <textarea className={`${inputClass} min-h-[120px]`} value={eventForm.description} onChange={(event) => setEventForm((current) => ({ ...current, description: event.target.value }))} placeholder="Signataires, representants, suite prevue" />
              <button type="button" onClick={() => createEventMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Ajouter le jalon</button>
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "conciliation" ? (
        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Pretentions et dommages demandes</h2>
            <p className="mt-2 text-sm text-slate-400">Aucune attribution automatique: le bloc structure les demandes pour conciliation ou orientation.</p>
            <div className="mt-6 grid gap-4">
              <select className={inputClass} value={claimForm.claim_type} onChange={(event) => setClaimForm((current) => ({ ...current, claim_type: event.target.value }))}><option value="salaires_impayes">Salaires impayes</option><option value="indemnite_conge">Indemnite de conge</option><option value="preavis">Preavis</option><option value="indemnite_licenciement">Indemnite de licenciement</option><option value="di_rupture_abusive">Dommages et interets rupture abusive</option><option value="di_harcelement">Dommages et interets harcelement</option><option value="autres">Autres</option></select>
              <select className={inputClass} value={claimForm.claimant_party} onChange={(event) => setClaimForm((current) => ({ ...current, claimant_party: event.target.value }))}><option value="employee">Employe</option><option value="employer">Employeur</option><option value="representative">Representant</option></select>
              <textarea className={`${inputClass} min-h-[120px]`} value={claimForm.factual_basis} onChange={(event) => setClaimForm((current) => ({ ...current, factual_basis: event.target.value }))} placeholder="Base factuelle / prejudice invoque" />
              <input className={inputClass} value={claimForm.amount_requested} onChange={(event) => setClaimForm((current) => ({ ...current, amount_requested: event.target.value }))} placeholder="Montant demande en MGA, facultatif" />
              <textarea className={`${inputClass} min-h-[100px]`} value={claimForm.inspector_observations} onChange={(event) => setClaimForm((current) => ({ ...current, inspector_observations: event.target.value }))} placeholder="Observations inspecteur" />
              <button type="button" onClick={() => createClaimMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Ajouter la pretention</button>
            </div>
          </div>
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Convocation / conciliation</h2>
            <div className="mt-6 grid gap-4">
              <select className={inputClass} value={eventForm.event_type} onChange={(event) => setEventForm((current) => ({ ...current, event_type: event.target.value }))}><option value="convocation">Convocation</option><option value="conciliation">Tentative de conciliation</option><option value="carence">Carence</option><option value="execution_followup">Suivi execution</option><option value="non_execution">Non-execution</option></select>
              <input className={inputClass} value={eventForm.title} onChange={(event) => setEventForm((current) => ({ ...current, title: event.target.value }))} placeholder="Objet de l'evenement" />
              <input type="datetime-local" className={inputClass} value={eventForm.scheduled_at} onChange={(event) => setEventForm((current) => ({ ...current, scheduled_at: event.target.value }))} />
              <textarea className={`${inputClass} min-h-[120px]`} value={eventForm.description} onChange={(event) => setEventForm((current) => ({ ...current, description: event.target.value }))} placeholder="Presences, points discutes, accords/desaccords" />
              <button type="button" onClick={() => createEventMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Tracer l'evenement</button>
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "pv" ? (
        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          {isInspectorOperator ? (
            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Generateur de PV</h2>
              <div className="mt-6 grid gap-4">
                <select className={inputClass} value={pvForm.pv_type} onChange={(event) => setPvForm((current) => ({ ...current, pv_type: event.target.value }))}><option value="conciliation_totale">PV conciliation totale</option><option value="conciliation_partielle">PV conciliation partielle</option><option value="non_conciliation">PV non-conciliation</option><option value="carence">PV de carence</option><option value="non_execution">PV de non-execution</option><option value="transaction_acceptance">PV acceptation transaction</option><option value="transaction_refusal">PV refus transaction</option><option value="infraction">PV d'infraction</option></select>
                <input className={inputClass} value={pvForm.title} onChange={(event) => setPvForm((current) => ({ ...current, title: event.target.value }))} placeholder="Titre du PV" />
                <select className={inputClass} value={pvForm.status} onChange={(event) => setPvForm((current) => ({ ...current, status: event.target.value }))}><option value="draft">Brouillon</option><option value="issued">Emis</option><option value="sent">Delivre aux parties</option></select>
                <textarea className={`${inputClass} min-h-[120px]`} value={pvForm.measures_to_execute} onChange={(event) => setPvForm((current) => ({ ...current, measures_to_execute: event.target.value }))} placeholder="Mesures a executer" />
                <input type="datetime-local" className={inputClass} value={pvForm.execution_deadline} onChange={(event) => setPvForm((current) => ({ ...current, execution_deadline: event.target.value }))} />
                <button type="button" onClick={() => createPvMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Generer le PV</button>
              </div>
            </div>
          ) : (
            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">PV accessibles</h2>
              <p className="mt-4 text-sm leading-6 text-slate-300">
                Lecture restreinte aux PV visibles pour le rôle judiciaire courant.
              </p>
            </div>
          )}
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">PV du dossier</h2>
            <div className="mt-6 space-y-3">{(workspace?.pv_records ?? []).map((item) => <div key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{item.pv_number} - {item.title}</div><div className="mt-1 text-cyan-200">{translatedLabel(item.pv_type, pvTypeLabels)} | v{item.version_number} | {translatedLabel(item.status, statusLabels)}</div><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950/70 p-4 text-xs text-slate-300">{item.content}</pre></div>)}</div>
          </div>
        </section>
      ) : null}

      {activeTab === "assistant" ? (
        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Assistant inspection</h2>
            <p className="mt-2 text-sm text-slate-400">Service serveur avec mode de secours par modeles. Il assiste, structure et ne juge pas.</p>
            <div className="mt-6 grid gap-4">
              <select className={inputClass} value={assistantForm.role_context} onChange={(event) => setAssistantForm((current) => ({ ...current, role_context: event.target.value }))}><option value="inspecteur">Inspecteur</option></select>
              <select className={inputClass} value={assistantForm.intent} onChange={(event) => setAssistantForm((current) => ({ ...current, intent: event.target.value }))}><option value="qualifier">Qualifier ce dossier</option><option value="convocation">Preparer une convocation</option><option value="pv_conciliation_partielle">Preparer un PV</option><option value="sanction_checklist">Verifier une sanction</option><option value="pieces_manquantes">Lister les pieces manquantes</option><option value="doleance_collective">Doleance collective</option></select>
              <textarea className={`${inputClass} min-h-[160px]`} value={assistantForm.prompt} onChange={(event) => setAssistantForm((current) => ({ ...current, prompt: event.target.value }))} placeholder="Demande a l'assistant" />
              <button type="button" onClick={() => assistantMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Interroger l'assistant</button>
            </div>
          </div>
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Reponse structuree</h2>
            <div className="mt-6 space-y-3">
              {Object.entries((assistantAnswer ?? assistantPreview) as Record<string, unknown>).map(([key, value]) => (
                <div key={key} className="rounded-2xl border border-white/10 bg-slate-950/70 p-4 text-sm text-slate-300">
                  <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{translatedLabel(key)}</div>
                  <div className="mt-2 whitespace-pre-wrap text-white">
                    {typeof value === "string" || typeof value === "number" ? String(value) : Array.isArray(value) ? value.join(", ") : "Information disponible"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "messages" ? (
        <div className="space-y-6">
          <section className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
            <div className={shellCard}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-white">Boite inspecteur</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    Lecture rapide des plaintes a traiter. Chaque dossier tombe dans une seule file de pilotage.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => refreshPortal()}
                  className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white"
                >
                  Actualiser
                </button>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {inboxBuckets.map((bucket) => (
                  <button
                    key={bucket.key}
                    type="button"
                    onClick={() => setInboxView(bucket.key)}
                    className={`rounded-[1.5rem] border p-4 text-left transition ${
                      inboxView === bucket.key
                        ? `${bucket.tone} shadow-lg shadow-slate-950/20`
                        : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className={`h-2.5 w-2.5 rounded-full ${bucket.dot}`} />
                      <span className="text-2xl font-semibold text-white">{bucket.count}</span>
                    </div>
                    <div className="mt-4 text-sm font-semibold text-white">{bucket.label}</div>
                    <div className="mt-1 text-xs leading-5 text-slate-300">{bucket.description}</div>
                  </button>
                ))}
              </div>

              <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-white">{activeInboxBucket?.label || "File"}</div>
                    <div className="mt-1 text-xs text-slate-400">{activeInboxBucket?.description}</div>
                  </div>
                  <div className="rounded-full border border-white/10 px-3 py-1 text-xs font-semibold text-slate-200">
                    {inboxCases.length} dossier(s)
                  </div>
                </div>

                <div className="mt-4 space-y-3">
                  {inboxCases.length ? inboxCases.map((item) => {
                    const bucket = inboxBucketMeta[resolveInboxBucket(item, session?.user_id)];
                    const daysWithoutResponse = getDaysWithoutResponse(item);
                    const responseUrgency = getResponseUrgency(daysWithoutResponse);
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setSelectedCaseId(item.id)}
                        className={`w-full rounded-[1.5rem] border p-4 text-left transition ${
                          selectedCaseId === item.id
                            ? "border-cyan-300/40 bg-cyan-400/10"
                            : "border-white/10 bg-slate-950/40 hover:bg-white/10"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-white">{item.subject}</div>
                            <div className="mt-1 text-xs uppercase tracking-[0.2em] text-cyan-200">{item.case_number}</div>
                          </div>
                          <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${bucket.tone}`}>
                            {bucket.label}
                          </span>
                        </div>
                        <div className="mt-3 text-sm text-slate-300">{employerNameById[item.employer_id] || `Entreprise #${item.employer_id}`}</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${responseUrgency.tone}`}>
                            {responseUrgency.label}
                          </span>
                          {item.is_sensitive ? (
                            <span className="rounded-full border border-rose-400/30 bg-rose-400/10 px-3 py-1 text-[11px] font-semibold text-rose-100">
                              Sensible
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-400">
                          <span>{translatedLabel(item.case_type, caseTypeLabels)}</span>
                          <span>•</span>
                          <span>{translatedLabel(item.status, statusLabels)}</span>
                          <span>•</span>
                          <span>Maj {new Date(item.last_response_at || item.updated_at).toLocaleString("fr-FR")}</span>
                        </div>
                      </button>
                    );
                  }) : (
                    <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/30 px-4 py-6 text-sm text-slate-400">
                      Aucun dossier dans cette file.
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className={shellCard}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-white">Lecture du dossier</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    Vue simple pour comprendre tout de suite qui attend quoi.
                  </p>
                </div>
                {selectedCase ? (
                  <button
                    type="button"
                    onClick={() => setActiveTab("cases")}
                    className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white"
                  >
                    Ouvrir le dossier complet
                  </button>
                ) : null}
              </div>

              {selectedCase ? (
                <div className="mt-6 space-y-5">
                  {(() => {
                    const daysWithoutResponse = getDaysWithoutResponse(selectedCase);
                    const responseUrgency = getResponseUrgency(daysWithoutResponse);
                    return (
                  <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="text-xs uppercase tracking-[0.2em] text-cyan-200">{selectedCase.case_number}</div>
                        <div className="mt-2 text-2xl font-semibold text-white">{selectedCase.subject}</div>
                        <div className="mt-2 text-sm text-slate-300">
                          {employerNameById[selectedCase.employer_id] || `Entreprise #${selectedCase.employer_id}`}
                        </div>
                      </div>
                      {selectedCaseBucket ? (
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${inboxBucketMeta[selectedCaseBucket].tone}`}>
                          {inboxBucketMeta[selectedCaseBucket].label}
                        </span>
                      ) : null}
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${responseUrgency.tone}`}>
                        {responseUrgency.label}
                      </span>
                      {selectedCase.is_sensitive ? (
                        <span className="rounded-full border border-rose-400/30 bg-rose-400/10 px-3 py-1 text-xs font-semibold text-rose-100">
                          Dossier sensible
                        </span>
                      ) : null}
                    </div>

                    <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Statut metier</div>
                        <div className="mt-2 text-sm font-semibold text-white">{translatedLabel(selectedCase.status, statusLabels)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Etape</div>
                        <div className="mt-2 text-sm font-semibold text-white">{translatedLabel(selectedCase.current_stage, statusLabels)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Type</div>
                        <div className="mt-2 text-sm font-semibold text-white">{translatedLabel(selectedCase.case_type, caseTypeLabels)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                        <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Dernier mouvement</div>
                        <div className="mt-2 text-sm font-semibold text-white">
                          {new Date(selectedCase.last_response_at || selectedCase.updated_at).toLocaleString("fr-FR")}
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/40 p-4 text-sm leading-6 text-slate-300">
                      {selectedCase.description || "Aucune description fournie."}
                    </div>
                  </div>
                    );
                  })()}

                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Priorite de lecture</div>
                      <div className="mt-3 text-sm font-semibold text-white">
                        {selectedCaseBucket ? inboxBucketMeta[selectedCaseBucket].label : "A classer"}
                      </div>
                      <div className="mt-2 text-sm leading-6 text-slate-400">
                        {selectedCaseBucket ? inboxBucketMeta[selectedCaseBucket].description : "Verifier le dernier echange et statuer."}
                      </div>
                    </div>
                    <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Affectation</div>
                      <div className="mt-3 text-sm font-semibold text-white">
                        {selectedCase.assigned_inspector_user_id === session?.user_id ? "Assigne a moi" : "Dispatch auto / autre inspecteur"}
                      </div>
                      <div className="mt-2 text-sm text-slate-400">
                        Inspecteur id: {selectedCase.assigned_inspector_user_id || "non defini"}
                      </div>
                    </div>
                    <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Sensibilite</div>
                      <div className="mt-3 text-sm font-semibold text-white">{selectedCase.is_sensitive ? "Sensible" : "Standard"}</div>
                      <div className="mt-2 text-sm text-slate-400">
                        Confidentialite: {translatedLabel(selectedCase.confidentiality, statusLabels)}
                      </div>
                    </div>
                  </div>

                  {isInspectorOperator ? (
                  <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Actions rapides</h3>
                        <div className="mt-1 text-sm text-slate-400">
                          Mise a jour instantanee de la file sans passer par le formulaire complet.
                        </div>
                      </div>
                      {updateCaseStatusMutation.isPending ? (
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Mise a jour...</div>
                      ) : null}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <button
                        type="button"
                        disabled={updateCaseStatusMutation.isPending}
                        onClick={() =>
                          updateCaseStatusMutation.mutate({
                            status: "in_review",
                            current_stage: "instruction",
                            note: "Pris en charge depuis la boite inspecteur.",
                          })
                        }
                        className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/20 disabled:opacity-50"
                      >
                        Prendre en charge
                      </button>
                      <button
                        type="button"
                        disabled={updateCaseStatusMutation.isPending}
                        onClick={() =>
                          updateCaseStatusMutation.mutate({
                            status: "EN_ATTENTE_EMPLOYE",
                            current_stage: "waiting_employee",
                            note: "Retour ou piece demande au salarie / agent.",
                          })
                        }
                        className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:bg-amber-400/20 disabled:opacity-50"
                      >
                        Passer en attente agent
                      </button>
                      <button
                        type="button"
                        disabled={updateCaseStatusMutation.isPending}
                        onClick={() =>
                          updateCaseStatusMutation.mutate({
                            status: "EN_ATTENTE_EMPLOYEUR",
                            current_stage: "waiting_employer",
                            note: "Retour ou piece demande a l'employeur.",
                          })
                        }
                        className="rounded-2xl border border-fuchsia-400/30 bg-fuchsia-400/10 px-4 py-3 text-sm font-semibold text-fuchsia-100 transition hover:bg-fuchsia-400/20 disabled:opacity-50"
                      >
                        Passer en attente employeur
                      </button>
                      <button
                        type="button"
                        disabled={updateCaseStatusMutation.isPending}
                        onClick={() =>
                          updateCaseStatusMutation.mutate({
                            status: "CLOTURE",
                            current_stage: "closed",
                            note: "Dossier cloture depuis la boite inspecteur.",
                          })
                        }
                        className="rounded-2xl border border-slate-400/30 bg-slate-400/10 px-4 py-3 text-sm font-semibold text-slate-100 transition hover:bg-slate-400/20 disabled:opacity-50"
                      >
                        Clore
                      </button>
                    </div>
                  </div>
                  ) : null}

                  <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Chronologie des echanges</h3>
                      <div className="text-xs text-slate-500">{caseMessages.length} message(s)</div>
                    </div>
                    <div className="mt-4 space-y-3">
                      {caseMessages.length ? caseMessages.map((item) => (
                        <article key={item.id} className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-sm font-semibold text-white">{translatedLabel(item.sender_role, roleLabels)}</div>
                            <div className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString("fr-FR")}</div>
                          </div>
                          <div className="mt-3 text-sm leading-6 text-slate-300">{item.body}</div>
                        </article>
                      )) : (
                        <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/30 px-4 py-6 text-sm text-slate-400">
                          Aucun message sur ce dossier pour le moment.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/5 px-4 py-10 text-sm text-slate-400">
                  Selectionnez une file puis un dossier pour ouvrir la lecture.
                </div>
              )}
            </div>
          </section>

          {isInspectorOperator ? (
          <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Nouveau message formel</h2>
              <p className="mt-2 text-sm text-slate-400">
                Bloc secondaire pour les communications formelles sortantes de l'inspection.
              </p>
              <div className="mt-6 grid gap-4">
                <input className={inputClass} value={messageForm.subject} onChange={(event) => setMessageForm((current) => ({ ...current, subject: event.target.value }))} placeholder="Objet" />
                <textarea className={`${inputClass} min-h-[140px]`} value={messageForm.body} onChange={(event) => setMessageForm((current) => ({ ...current, body: event.target.value }))} placeholder="Corps du message" />
                <div>
                  <label className={labelClass}>Destinataires entreprises</label>
                  <select multiple className={`${inputClass} min-h-[200px]`} value={messageRecipients.map(String)} onChange={(event) => setMessageRecipients(Array.from(event.target.selectedOptions).map((option) => Number(option.value)))}>
                    {employers.map((item) => <option key={item.id} value={item.id}>{item.raison_sociale}</option>)}
                  </select>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={() => createMessageMutation.mutate(false)} className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white">Enregistrer brouillon</button>
                  <button type="button" onClick={() => { if (window.confirm("Envoyer ce message formel ?")) createMessageMutation.mutate(true); }} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Envoyer</button>
                </div>
              </div>
            </div>

            <div className={shellCard}>
              <h2 className="text-xl font-semibold text-white">Journal d'envoi</h2>
              <div className="mt-6 space-y-3">
                {formalMessages.length ? formalMessages.map((item) => (
                  <div key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-white">{item.subject}</div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass(item.status)}`}>{translatedLabel(item.status, statusLabels)}</span>
                    </div>
                    <div className="mt-2 text-sm text-slate-300">{item.body}</div>
                    <div className="mt-3 text-xs text-slate-400">Ref {item.reference_number} | {(item.recipients ?? []).length} destinataire(s)</div>
                    {item.status === "draft" ? <button type="button" onClick={() => { if (window.confirm("Envoyer ce brouillon maintenant ?")) sendDraftMutation.mutate(item.id); }} className="mt-3 rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Envoyer le brouillon</button> : null}
                  </div>
                )) : (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 px-4 py-6 text-sm text-slate-400">
                    Aucun message formel pour ce perimetre.
                  </div>
                )}
              </div>
            </div>
          </section>
          ) : null}
        </div>
      ) : null}

      {activeTab === "help" ? (
        <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Principes metier</h2>
            <div className="mt-6 space-y-3">{(helpPayload?.principles ?? []).map((item) => <div key={item} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">{item}</div>)}</div>
          </div>
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">FAQ et workflows inspection</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-2">{(helpPayload?.topics ?? workspace?.help_topics ?? []).map((topic) => <div key={topic.code} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5"><div className="font-semibold text-white">{topic.title}</div><div className="mt-2 text-sm leading-6 text-slate-300">{topic.summary}</div><div className="mt-4 space-y-2">{topic.steps.map((step) => <div key={step} className="rounded-xl bg-slate-950/60 px-3 py-2 text-xs text-cyan-100">{step}</div>)}</div></div>)}</div>
          </div>
        </section>
      ) : null}

      {activeTab === "settings" && canManagePortalSettings ? (
        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Referentiels inspection</h2>
            <div className="mt-6 grid gap-4">
              <select className={inputClass} value={selectedParameterCategory} onChange={(event) => setSelectedParameterCategory(event.target.value)}>{categoryOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
              <input className={inputClass} value={parameterForm.label} onChange={(event) => setParameterForm((current) => ({ ...current, label: event.target.value }))} placeholder="Libelle" />
              <textarea className={`${inputClass} min-h-[110px]`} value={parameterForm.description} onChange={(event) => setParameterForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
              <button type="button" onClick={() => createParameterMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Ajouter</button>
              <div className="space-y-2">{parameterItems.map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300"><div className="font-semibold text-white">{item.label}</div>{item.description ? <div className="mt-1 text-slate-400">{item.description}</div> : null}</div>)}</div>
            </div>
          </div>

          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Affectation inspecteur</h2>
            <div className="mt-6 grid gap-4">
              <select className={inputClass} value={assignmentForm.employer_id} onChange={(event) => setAssignmentForm((current) => ({ ...current, employer_id: event.target.value }))}><option value="">Entreprise</option>{employers.map((item) => <option key={item.id} value={item.id}>{item.raison_sociale}</option>)}</select>
              <select className={inputClass} value={assignmentForm.inspector_user_id} onChange={(event) => setAssignmentForm((current) => ({ ...current, inspector_user_id: event.target.value }))}><option value="">Inspecteur</option>{inspectors.map((item) => <option key={item.id} value={item.id}>{item.full_name || item.username}</option>)}</select>
              <input className={inputClass} value={assignmentForm.circonscription} onChange={(event) => setAssignmentForm((current) => ({ ...current, circonscription: event.target.value }))} placeholder="Circonscription" />
              <button type="button" onClick={() => createAssignmentMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">Affecter</button>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
