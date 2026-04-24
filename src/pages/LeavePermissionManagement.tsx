import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api";
import HelpTooltip from "../components/help/HelpTooltip";
import WorkCalendar from "../components/WorkCalendar";
import { useAuth } from "../contexts/AuthContext";
import { getContextHelp } from "../help/helpContent";
import { sessionHasRole } from "../rbac";

type Employer = {
  id: number;
  raison_sociale: string;
};

type Worker = {
  id: number;
  employer_id: number;
  matricule?: string | null;
  nom: string;
  prenom: string;
};

type LeaveType = {
  id: number;
  code: string;
  label: string;
  category: string;
  deduct_from_annual_balance: boolean;
  justification_required: boolean;
  validation_required: boolean;
  payroll_impact: string;
  attendance_impact: string;
};

type LeaveRequest = {
  id: number;
  request_ref: string;
  worker_id: number;
  leave_type_code: string;
  final_leave_type_code: string;
  status: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  subject: string;
  reason?: string | null;
  comment?: string | null;
  validations_remaining: string[];
  alerts: Array<{ code: string; severity: string; message: string }>;
  approvals: Array<{ id: number; approver_label?: string | null; status: string; comment?: string | null }>;
  history: Array<{ id: number; action: string; actor_name?: string | null; comment?: string | null; created_at: string }>;
};

type LeaveDashboard = {
  worker_id: number;
  employer_id: number;
  period: string;
  balances: Record<string, number>;
  requests: LeaveRequest[];
  alerts: Array<{ code: string; severity: string; message: string }>;
  notifications: Array<{ type: string; label: string; status: string }>;
  calendar: Array<{ id: number; start_date: string; end_date: string; status: string; leave_type_code: string; subject: string }>;
};

type ValidatorDashboard = {
  metrics: Record<string, number>;
  pending_requests: LeaveRequest[];
  urgent_requests: LeaveRequest[];
  conflicts: LeaveRequest[];
  alerts: Array<{ severity: string; message: string }>;
};

type ApprovalRuleStep = {
  id?: number;
  step_order: number;
  parallel_group: number;
  approver_kind: string;
  approver_role_code?: string | null;
  approver_user_id?: number | null;
  is_required?: boolean;
  label?: string | null;
};

type RuleEditorStep = {
  step_order: number;
  parallel_group: number;
  approver_kind: string;
  approver_role_code: string;
  approver_user_id: string;
  is_required: boolean;
  label: string;
};

type ApprovalRule = {
  id: number;
  leave_type_code: string;
  approval_mode: string;
  fallback_on_reject: string;
  steps: ApprovalRuleStep[];
};

type PlanningCycle = {
  id: number;
  title: string;
};

type PlanningProposal = {
  id: number;
  worker_id: number;
  worker_name: string;
  score: number;
  rationale: Array<{ factor: string; weight: number; message: string }>;
};

type AppUser = {
  id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
  employer_id?: number | null;
};

type ReconciliationRow = {
  id: number;
  leave_request_id: number;
  employer_id: number;
  worker_id: number;
  worker_name?: string | null;
  request_ref?: string | null;
  leave_type_code?: string | null;
  subject?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  period: string;
  status: string;
  discrepancy_level: string;
  attendance_payload: Record<string, unknown>;
  leave_payload: Record<string, unknown>;
  notes?: string | null;
};

type RuleEditorState = {
  id: number | null;
  leave_type_code: string;
  approval_mode: string;
  fallback_on_reject: string;
  active: boolean;
  steps: RuleEditorStep[];
};

const panelClass = "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClass = "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50";
const badge = (status: string) => {
  if (status.includes("approved") || status === "integrated") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-100";
  if (status.includes("reject")) return "border-rose-400/30 bg-rose-400/10 text-rose-100";
  if (status.includes("requal")) return "border-amber-400/30 bg-amber-400/10 text-amber-100";
  return "border-cyan-400/20 bg-cyan-400/10 text-cyan-100";
};

export default function LeavePermissionManagement() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const isEmployee = sessionHasRole(session, ["employe"]) && !!session?.worker_id;
  const canValidate = sessionHasRole(session, ["admin", "rh", "manager", "direction", "employeur"]);
  const canAdmin = sessionHasRole(session, ["admin", "rh", "employeur", "direction"]);

  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(session?.employer_id ?? null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(session?.worker_id ?? null);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [requestForm, setRequestForm] = useState({
    leave_type_code: "CONGE_ANNUEL",
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date().toISOString().slice(0, 10),
    subject: "",
    reason: "",
    comment: "",
    attachment_note: "",
  });
  const [requestFile, setRequestFile] = useState<File | null>(null);
  const [typeForm, setTypeForm] = useState({
    code: "",
    label: "",
    category: "permission",
    deduct_from_annual_balance: false,
    justification_required: false,
    payroll_impact: "none",
    attendance_impact: "absence",
  });
  const [ruleEditor, setRuleEditor] = useState<RuleEditorState>({
    id: null as number | null,
    leave_type_code: "CONGE_ANNUEL",
    approval_mode: "sequential",
    fallback_on_reject: "reject",
    active: true,
    steps: [
      { step_order: 1, parallel_group: 1, approver_kind: "manager", approver_role_code: "manager", approver_user_id: "", is_required: true, label: "N+1" },
      { step_order: 2, parallel_group: 1, approver_kind: "rh", approver_role_code: "rh", approver_user_id: "", is_required: true, label: "RH" },
    ],
  });
  const [planningForm, setPlanningForm] = useState({
    title: `Plan ${new Date().getFullYear()}`,
    planning_year: new Date().getFullYear(),
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date(new Date().setDate(new Date().getDate() + 14)).toISOString().slice(0, 10),
    max_absent_per_unit: 1,
  });
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [calendarScope, setCalendarScope] = useState<"global" | "team" | "personal">("global");
  const leaveBalanceHelp = getContextHelp("leaves", "leave_balance");
  const leaveWorkflowHelp = getContextHelp("leaves", "approval_mode");

  const { data: employers = [] } = useQuery({
    queryKey: ["leave", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
    enabled: !isEmployee,
  });

  const effectiveEmployerId = useMemo(() => {
    if (isEmployee) return session?.employer_id ?? null;
    if (selectedEmployerId && employers.some((item) => item.id === selectedEmployerId)) return selectedEmployerId;
    return employers[0]?.id ?? session?.employer_id ?? null;
  }, [employers, isEmployee, selectedEmployerId, session]);

  const { data: workers = [] } = useQuery({
    queryKey: ["leave", "workers", effectiveEmployerId],
    enabled: !isEmployee && effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<Worker[]>("/workers", { params: { employer_id: effectiveEmployerId } })
    ).data,
  });

  const effectiveWorkerId = useMemo(() => {
    if (isEmployee) return session?.worker_id ?? null;
    if (selectedWorkerId && workers.some((item) => item.id === selectedWorkerId)) return selectedWorkerId;
    return workers[0]?.id ?? null;
  }, [isEmployee, selectedWorkerId, session, workers]);

  const { data: leaveTypes = [] } = useQuery({
    queryKey: ["leave", "types", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<LeaveType[]>("/leaves/types", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: approvalRules = [] } = useQuery({
    queryKey: ["leave", "approval-rules", effectiveEmployerId],
    enabled: canAdmin && effectiveEmployerId !== null,
    queryFn: async () => (await api.get<ApprovalRule[]>("/leaves/approval-rules", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: users = [] } = useQuery({
    queryKey: ["leave", "users", effectiveEmployerId],
    enabled: canAdmin && effectiveEmployerId !== null,
    queryFn: async () => (await api.get<AppUser[]>("/auth/users", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: dashboard } = useQuery({
    queryKey: ["leave", "dashboard", effectiveWorkerId],
    enabled: effectiveWorkerId !== null,
    queryFn: async () => (await api.get<LeaveDashboard>(`/leaves/dashboard/worker/${effectiveWorkerId}`)).data,
  });

  const { data: validatorDashboard } = useQuery({
    queryKey: ["leave", "validator-dashboard", effectiveEmployerId, session?.user_id],
    enabled: canValidate,
    queryFn: async () => (
      await api.get<ValidatorDashboard>("/leaves/dashboard/validator", { params: { employer_id: effectiveEmployerId ?? undefined } })
    ).data,
  });

  const { data: reconciliationRows = [] } = useQuery({
    queryKey: ["leave", "reconciliation", effectiveEmployerId],
    enabled: canValidate,
    queryFn: async () => (await api.get<ReconciliationRow[]>("/leaves/reconciliation", { params: { employer_id: effectiveEmployerId ?? undefined } })).data,
  });

  const createRequestMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveWorkerId) throw new Error("Salarie requis");
      const created = (
        await api.post<LeaveRequest>("/leaves/requests", {
          worker_id: effectiveWorkerId,
          leave_type_code: requestForm.leave_type_code,
          start_date: requestForm.start_date,
          end_date: requestForm.end_date,
          subject: requestForm.subject,
          reason: requestForm.reason || null,
          comment: requestForm.comment || null,
          attachments: requestForm.attachment_note ? [{ name: requestForm.attachment_note, source: "manual_note" }] : [],
          submit_now: true,
        })
      ).data;
      if (requestFile) {
        const formData = new FormData();
        formData.append("attachment", requestFile);
        formData.append("label", requestForm.attachment_note || requestFile.name);
        await api.post(`/leaves/requests/${created.id}/attachments/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      return created;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave"] });
      setRequestForm((current) => ({ ...current, subject: "", reason: "", comment: "", attachment_note: "" }));
      setRequestFile(null);
      alert("Demande soumise.");
    },
    onError: (error: any) => alert(error?.response?.data?.detail || "Erreur lors de la demande."),
  });

  const createTypeMutation = useMutation({
    mutationFn: async () => (
      await api.post("/leaves/types", {
        employer_id: effectiveEmployerId,
        ...typeForm,
        validation_required: true,
        visibility_scope: "all",
        allow_requalification: true,
        supports_hour_range: false,
        active: true,
      })
    ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave", "types"] });
      setTypeForm({ code: "", label: "", category: "permission", deduct_from_annual_balance: false, justification_required: false, payroll_impact: "none", attendance_impact: "absence" });
    },
  });

  const createStandardRuleMutation = useMutation({
    mutationFn: async (leaveTypeCode: string) => (
      await api.post("/leaves/approval-rules", {
        employer_id: effectiveEmployerId,
        leave_type_code: leaveTypeCode,
        approval_mode: "sequential",
        fallback_on_reject: "reject",
        active: true,
        steps: [
          { step_order: 1, parallel_group: 1, approver_kind: "manager", approver_role_code: "manager", is_required: true, label: "N+1" },
          { step_order: 2, parallel_group: 1, approver_kind: "rh", approver_role_code: "rh", is_required: true, label: "RH" },
        ],
      })
    ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave", "approval-rules"] });
      alert("Circuit standard cree.");
    },
  });

  const saveRuleMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        employer_id: effectiveEmployerId,
        leave_type_code: ruleEditor.leave_type_code,
        approval_mode: ruleEditor.approval_mode,
        fallback_on_reject: ruleEditor.fallback_on_reject,
        active: ruleEditor.active,
        steps: ruleEditor.steps.map((step) => ({
          step_order: Number(step.step_order),
          parallel_group: Number(step.parallel_group),
          approver_kind: step.approver_kind,
          approver_role_code: step.approver_role_code || null,
          approver_user_id: step.approver_user_id ? Number(step.approver_user_id) : null,
          is_required: step.is_required,
          label: step.label || null,
        })),
      };
      if (ruleEditor.id) {
        return (await api.put(`/leaves/approval-rules/${ruleEditor.id}`, payload)).data;
      }
      return (await api.post(`/leaves/approval-rules`, payload)).data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave", "approval-rules"] });
      alert("Circuit enregistre.");
      setRuleEditor({
        id: null,
        leave_type_code: "CONGE_ANNUEL",
        approval_mode: "sequential",
        fallback_on_reject: "reject",
        active: true,
        steps: [
          { step_order: 1, parallel_group: 1, approver_kind: "manager", approver_role_code: "manager", approver_user_id: "", is_required: true, label: "N+1" },
          { step_order: 2, parallel_group: 1, approver_kind: "rh", approver_role_code: "rh", approver_user_id: "", is_required: true, label: "RH" },
        ],
      });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (ruleId: number) => (await api.delete(`/leaves/approval-rules/${ruleId}`)).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave", "approval-rules"] });
    },
  });

  const decisionMutation = useMutation({
    mutationFn: async ({ requestId, action, comment }: { requestId: number; action: string; comment?: string }) => (
      await api.post(`/leaves/requests/${requestId}/decision`, { action, comment: comment || null })
    ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave"] });
    },
    onError: (error: any) => alert(error?.response?.data?.detail || "Decision impossible."),
  });

  const requalifyMutation = useMutation({
    mutationFn: async ({ requestId, newType, comment }: { requestId: number; newType: string; comment: string }) => (
      await api.post(`/leaves/requests/${requestId}/requalify`, { new_leave_type_code: newType, comment })
    ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave"] });
    },
    onError: (error: any) => alert(error?.response?.data?.detail || "Requalification impossible."),
  });

  const deleteRequestMutation = useMutation({
    mutationFn: async (requestId: number) => (await api.delete(`/leaves/requests/${requestId}`)).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leave"] });
    },
    onError: (error: any) => alert(error?.response?.data?.detail || "Suppression impossible."),
  });

  const createCycleMutation = useMutation({
    mutationFn: async () => (
      await api.post<PlanningCycle>("/leaves/planning/cycles", {
        employer_id: effectiveEmployerId,
        title: planningForm.title,
        planning_year: planningForm.planning_year,
        start_date: planningForm.start_date,
        end_date: planningForm.end_date,
        status: "draft",
        max_absent_per_unit: planningForm.max_absent_per_unit,
        blackout_periods: [],
        family_priority_enabled: true,
        notes: null,
      })
    ).data,
    onSuccess: (data) => {
      setSelectedCycleId(data.id);
    },
  });

  const { data: proposals = [] } = useQuery({
    queryKey: ["leave", "planning", selectedCycleId],
    enabled: selectedCycleId !== null,
    queryFn: async () => (await api.get<PlanningProposal[]>(`/leaves/planning/cycles/${selectedCycleId}/proposals`, { params: { regenerate: true } })).data,
  });

  const selectedType = leaveTypes.find((item) => item.code === requestForm.leave_type_code);
  const dashboardBalances = dashboard?.balances ?? {};
  const validatorMetrics = validatorDashboard?.metrics ?? {};
  const effectiveCalendarWorkerId = calendarScope === "personal" ? effectiveWorkerId : null;

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(29,78,216,0.88),rgba(17,94,89,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">Absences & conges</div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Demandes, validation, soldes et planification</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">Vue salarie, valideur et RH sur un meme ecran, avec impact paie et historique trace.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4"><div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Solde annuel</div><div className="mt-3 text-3xl font-semibold text-white">{dashboardBalances.annual_balance ?? 0}</div></div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4"><div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">En attente</div><div className="mt-3 text-3xl font-semibold text-white">{dashboardBalances.pending_annual ?? 0}</div></div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4"><div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">A valider</div><div className="mt-3 text-3xl font-semibold text-white">{validatorMetrics.pending ?? 0}</div></div>
          </div>
        </div>
      </section>

      <section className={panelClass}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Calendrier centralisé</h2>
            <p className="text-sm text-slate-400">
              Vue unique du calendrier société, des congés, des propositions de planning, des absences paie et des validations RH.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setCalendarScope("global")} className={`rounded-xl px-4 py-2 text-sm font-semibold ${calendarScope === "global" ? "bg-cyan-400 text-slate-950" : "border border-white/10 text-white"}`}>
              Vue globale
            </button>
            <button type="button" onClick={() => setCalendarScope("team")} className={`rounded-xl px-4 py-2 text-sm font-semibold ${calendarScope === "team" ? "bg-cyan-400 text-slate-950" : "border border-white/10 text-white"}`}>
              Vue équipe
            </button>
            <button type="button" onClick={() => setCalendarScope("personal")} className={`rounded-xl px-4 py-2 text-sm font-semibold ${calendarScope === "personal" ? "bg-cyan-400 text-slate-950" : "border border-white/10 text-white"}`}>
              Vue personnelle
            </button>
            <button type="button" onClick={() => setIsCalendarOpen(true)} disabled={!effectiveEmployerId} className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-40">
              Ouvrir le calendrier
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Périmètre actif</div>
            <div className="mt-2 text-sm text-slate-200">
              {calendarScope === "global" ? "Tous les salariés visibles selon vos droits." : calendarScope === "team" ? "Équipe visible selon le périmètre managérial." : "Salarié courant uniquement."}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Notifications</div>
            <div className="mt-2 space-y-2 text-sm text-slate-200">
              {(dashboard?.notifications ?? []).slice(0, 3).map((item, index) => (
                <div key={`${item.label}-${index}`} className="rounded-xl border border-white/10 bg-slate-950/40 px-3 py-2">
                  <div className="font-medium text-white">{item.label}</div>
                  <div className="text-xs text-slate-400">{item.status}</div>
                </div>
              ))}
              {!(dashboard?.notifications ?? []).length ? <div className="text-slate-400">Aucun rappel sur le périmètre courant.</div> : null}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Alertes</div>
            <div className="mt-2 space-y-2 text-sm text-slate-200">
              {(dashboard?.alerts ?? []).slice(0, 3).map((item) => (
                <div key={item.code} className="rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-amber-100">
                  {item.message}
                </div>
              ))}
              {!(dashboard?.alerts ?? []).length ? <div className="text-slate-400">Aucune alerte de solde ou de fractionnement.</div> : null}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.35fr]">
        <div className={panelClass}>
          {!isEmployee ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Employeur</label>
                <select value={effectiveEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClass}>
                  {employers.map((item) => <option key={item.id} value={item.id}>{item.raison_sociale}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Salarie</label>
                <select value={effectiveWorkerId ?? ""} onChange={(event) => setSelectedWorkerId(Number(event.target.value))} className={inputClass}>
                  {workers.map((item) => <option key={item.id} value={item.id}>{item.nom} {item.prenom} {item.matricule ? `(${item.matricule})` : ""}</option>)}
                </select>
              </div>
            </div>
          ) : null}

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Situation reelle</div>
              <div className="mt-3 space-y-2 text-sm text-slate-200">
                <div>Acquis: <span className="font-semibold text-white">{dashboardBalances.acquired ?? 0}</span></div>
                <div>Consomme: <span className="font-semibold text-white">{dashboardBalances.consumed ?? 0}</span></div>
                <div>Solde: <span className="font-semibold text-white">{dashboardBalances.annual_balance ?? 0}</span></div>
                <div>Previsionnel: <span className="font-semibold text-white">{dashboardBalances.projected_annual_balance ?? 0}</span></div>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Droits permissions</div>
              <div className="mt-3 space-y-2 text-sm text-slate-200">
                <div>Quota: <span className="font-semibold text-white">{dashboardBalances.permission_allowance ?? 0}</span></div>
                <div>Pris: <span className="font-semibold text-white">{dashboardBalances.permission_consumed ?? 0}</span></div>
                <div>Restant: <span className="font-semibold text-white">{dashboardBalances.permission_balance ?? 0}</span></div>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-sm text-cyan-50">
            <div className="font-semibold text-white">Nouvelle demande</div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <select value={requestForm.leave_type_code} onChange={(event) => setRequestForm((current) => ({ ...current, leave_type_code: event.target.value }))} className={inputClass}>
                {leaveTypes.map((item) => <option key={item.id} value={item.code}>{item.label}</option>)}
              </select>
              <input value={requestForm.subject} onChange={(event) => setRequestForm((current) => ({ ...current, subject: event.target.value }))} className={inputClass} placeholder="Objet obligatoire" />
              <input type="date" value={requestForm.start_date} onChange={(event) => setRequestForm((current) => ({ ...current, start_date: event.target.value }))} className={inputClass} />
              <input type="date" value={requestForm.end_date} onChange={(event) => setRequestForm((current) => ({ ...current, end_date: event.target.value }))} className={inputClass} />
              <input value={requestForm.reason} onChange={(event) => setRequestForm((current) => ({ ...current, reason: event.target.value }))} className={inputClass} placeholder="Motif / raison" />
              <input value={requestForm.attachment_note} onChange={(event) => setRequestForm((current) => ({ ...current, attachment_note: event.target.value }))} className={inputClass} placeholder="Reference piece jointe" />
              <input type="file" onChange={(event) => setRequestFile(event.target.files?.[0] ?? null)} className={inputClass} />
              <textarea value={requestForm.comment} onChange={(event) => setRequestForm((current) => ({ ...current, comment: event.target.value }))} className={`${inputClass} md:col-span-2 min-h-[92px]`} placeholder="Commentaire interne" />
            </div>
            {selectedType ? (
              <div className="mt-4 grid gap-2 text-xs text-cyan-100/90 md:grid-cols-2">
                <div className="flex items-center gap-2">Deduction solde: <span className="font-semibold text-white">{selectedType.deduct_from_annual_balance ? "Oui" : "Non"}</span><HelpTooltip item={leaveBalanceHelp} role={session?.effective_role_code || session?.role_code} compact /></div>
                <div>Impact paie: <span className="font-semibold text-white">{selectedType.payroll_impact}</span></div>
                <div>Impact pointage: <span className="font-semibold text-white">{selectedType.attendance_impact}</span></div>
                <div>Justificatif: <span className="font-semibold text-white">{selectedType.justification_required ? "Requis" : "Optionnel"}</span></div>
              </div>
            ) : null}
            <button type="button" onClick={() => createRequestMutation.mutate()} disabled={!effectiveWorkerId || !requestForm.subject} className="mt-4 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-40">Soumettre la demande</button>
          </div>
        </div>

        <div className={panelClass}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Historique et workflow</h2>
              <p className="text-sm text-slate-400">Validation en cours, requalification et integration.</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {(dashboard?.requests ?? []).map((request) => (
              <div key={request.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="text-sm text-slate-400">{request.request_ref}</div>
                    <div className="mt-1 text-lg font-semibold text-white">{request.subject}</div>
                    <div className="mt-1 text-sm text-slate-300">{request.start_date} {"->"} {request.end_date} | {request.duration_days} j | {request.final_leave_type_code}</div>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badge(request.status)}`}>{request.status}</span>
                </div>
                {request.validations_remaining.length ? <div className="mt-3 text-sm text-cyan-100">A valider par: {request.validations_remaining.join(", ")}</div> : null}
                {request.alerts.length ? <div className="mt-3 space-y-1">{request.alerts.map((alert) => <div key={`${request.id}-${alert.code}`} className="text-sm text-amber-200">{alert.message}</div>)}</div> : null}
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  {request.approvals.map((approval) => <span key={approval.id} className={`rounded-full border px-3 py-1 ${badge(approval.status)}`}>{approval.approver_label || "Validateur"}: {approval.status}</span>)}
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {request.status !== "approved" && request.status !== "integrated" && request.status !== "cancelled" ? (
                    <button type="button" onClick={() => decisionMutation.mutate({ requestId: request.id, action: "cancel", comment: "Annulation demandee depuis le front" })} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                      Annuler
                    </button>
                  ) : null}
                  {request.status !== "approved" && request.status !== "integrated" ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (window.confirm(`Supprimer la demande ${request.request_ref} ?`)) {
                          deleteRequestMutation.mutate(request.id);
                        }
                      }}
                      className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-100"
                    >
                      Supprimer
                    </button>
                  ) : null}
                </div>
                {canValidate ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => decisionMutation.mutate({ requestId: request.id, action: "approve" })} className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-xs font-semibold text-emerald-100">Approuver</button>
                    <button type="button" onClick={() => { const comment = window.prompt("Motif du rejet / retour correction"); if (comment !== null) decisionMutation.mutate({ requestId: request.id, action: "request_correction", comment }); }} className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-100">Demander correction</button>
                    <button type="button" onClick={() => { const newType = window.prompt("Nouveau type (ex: PERMISSION_LEGALE)", request.final_leave_type_code); const comment = window.prompt("Commentaire obligatoire pour la requalification"); if (newType && comment) requalifyMutation.mutate({ requestId: request.id, newType, comment }); }} className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs font-semibold text-amber-100">Requalifier</button>
                  </div>
                ) : null}
                <div className="mt-4 border-t border-white/10 pt-4">
                  <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Timeline</div>
                  <div className="mt-3 space-y-2">
                    {request.history.map((event) => (
                      <div key={event.id} className="rounded-xl border border-white/5 bg-slate-900/70 px-3 py-2 text-sm text-slate-300">
                        <span className="font-semibold text-white">{event.action}</span> | {event.actor_name || "Systeme"} | {new Date(event.created_at).toLocaleString()}
                        {event.comment ? <div className="mt-1 text-slate-400">{event.comment}</div> : null}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            {!(dashboard?.requests ?? []).length ? <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-slate-400">Aucune demande sur le scope courant.</div> : null}
          </div>
        </div>
      </section>

      {canValidate ? (
        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className={panelClass}>
            <h2 className="text-xl font-semibold text-white">Tableau de validation</h2>
            <p className="text-sm text-slate-400">Demandes en attente, urgentes et conflits detectes.</p>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">En attente: <span className="font-semibold text-white">{validatorMetrics.pending ?? 0}</span></div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">Urgentes: <span className="font-semibold text-white">{validatorMetrics.urgent ?? 0}</span></div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">Conflits: <span className="font-semibold text-white">{validatorMetrics.conflicts ?? 0}</span></div>
            </div>
            <div className="mt-6 space-y-3">
              {(validatorDashboard?.pending_requests ?? []).map((request) => (
                <div key={`validator-${request.id}`} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-white">{request.subject}</div>
                      <div className="text-sm text-slate-400">{request.start_date} {"->"} {request.end_date} | {request.final_leave_type_code}</div>
                    </div>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badge(request.status)}`}>{request.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={panelClass}>
            <h2 className="text-xl font-semibold text-white">Parametrage RH</h2>
            <p className="text-sm text-slate-400">Catalogue des types et circuit standard N+1 puis RH.</p>
            {canAdmin ? (
              <>
                <div className="mt-6 grid gap-3">
                  <input value={typeForm.code} onChange={(event) => setTypeForm((current) => ({ ...current, code: event.target.value.toUpperCase() }))} className={inputClass} placeholder="Code type" />
                  <input value={typeForm.label} onChange={(event) => setTypeForm((current) => ({ ...current, label: event.target.value }))} className={inputClass} placeholder="Libelle" />
                  <select value={typeForm.category} onChange={(event) => setTypeForm((current) => ({ ...current, category: event.target.value }))} className={inputClass}>
                    <option value="permission">Permission</option>
                    <option value="leave">Conge</option>
                    <option value="absence">Absence</option>
                    <option value="sick_leave">Maladie</option>
                  </select>
                  <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300"><input type="checkbox" checked={typeForm.deduct_from_annual_balance} onChange={(event) => setTypeForm((current) => ({ ...current, deduct_from_annual_balance: event.target.checked }))} /> Deductible du solde annuel</label>
                  <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300"><input type="checkbox" checked={typeForm.justification_required} onChange={(event) => setTypeForm((current) => ({ ...current, justification_required: event.target.checked }))} /> Justificatif requis</label>
                  <button type="button" onClick={() => createTypeMutation.mutate()} className="rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950">Ajouter le type</button>
                </div>
                <div className="mt-6 space-y-3">
                  {leaveTypes.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="font-semibold text-white">{item.label}</div>
                          <div className="text-sm text-slate-400">{item.code} | {item.payroll_impact} | {item.attendance_impact}</div>
                        </div>
                        <button type="button" onClick={() => createStandardRuleMutation.mutate(item.code)} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Circuit standard</button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-6">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-[0.22em] text-slate-500"><span>Circuits existants</span><HelpTooltip item={leaveWorkflowHelp} role={session?.effective_role_code || session?.role_code} compact /></div>
                  <div className="mt-3 space-y-3">
                    {approvalRules.map((rule) => (
                      <div key={rule.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="font-semibold text-white">{rule.leave_type_code}</div>
                            <div className="mt-2">{rule.steps.map((step) => step.label || `${step.approver_kind}`).join(" -> ")}</div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                setRuleEditor({
                                  id: rule.id,
                                  leave_type_code: rule.leave_type_code,
                                  approval_mode: rule.approval_mode,
                                  fallback_on_reject: rule.fallback_on_reject,
                                  active: true,
                                  steps: rule.steps.map((step) => ({
                                    step_order: step.step_order,
                                    parallel_group: step.parallel_group,
                                    approver_kind: step.approver_kind,
                                    approver_role_code: step.approver_role_code || "",
                                    approver_user_id: step.approver_user_id ? String(step.approver_user_id) : "",
                                    is_required: true,
                                    label: step.label || "",
                                  })),
                                })
                              }
                              className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white"
                            >
                              Editer
                            </button>
                            <button type="button" onClick={() => deleteRuleMutation.mutate(rule.id)} className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-100">Supprimer</button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-6 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4">
                  <div className="font-semibold text-white">Editeur complet de circuit</div>
                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <select value={ruleEditor.leave_type_code} onChange={(event) => setRuleEditor((current) => ({ ...current, leave_type_code: event.target.value }))} className={inputClass}>
                      {leaveTypes.map((item) => <option key={item.id} value={item.code}>{item.label}</option>)}
                    </select>
                    <select value={ruleEditor.approval_mode} onChange={(event) => setRuleEditor((current) => ({ ...current, approval_mode: event.target.value }))} className={inputClass}>
                      <option value="sequential">Sequentiel</option>
                      <option value="parallel">Parallele</option>
                    </select>
                    <select value={ruleEditor.fallback_on_reject} onChange={(event) => setRuleEditor((current) => ({ ...current, fallback_on_reject: event.target.value }))} className={inputClass}>
                      <option value="reject">Rejet final</option>
                      <option value="return_to_employee">Retour salarie</option>
                      <option value="rh_arbitration">Arbitrage RH</option>
                    </select>
                  </div>
                  <div className="mt-4 space-y-3">
                    {ruleEditor.steps.map((step, index) => (
                      <div key={`editor-step-${index}`} className="grid gap-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4 md:grid-cols-6">
                        <input value={step.step_order} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, step_order: Number(event.target.value) } : item) }))} className={inputClass} placeholder="Ordre" />
                        <input value={step.parallel_group} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, parallel_group: Number(event.target.value) } : item) }))} className={inputClass} placeholder="Groupe" />
                        <select value={step.approver_kind} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, approver_kind: event.target.value } : item) }))} className={inputClass}>
                          <option value="manager">N+1</option>
                          <option value="n_plus_2">N+2</option>
                          <option value="rh">RH</option>
                          <option value="direction">Direction</option>
                          <option value="site_manager">Responsable site/service</option>
                          <option value="specific">Validateur specifique</option>
                        </select>
                        <select value={step.approver_role_code} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, approver_role_code: event.target.value } : item) }))} className={inputClass}>
                          <option value="">Role libre</option>
                          <option value="manager">manager</option>
                          <option value="rh">rh</option>
                          <option value="direction">direction</option>
                          <option value="departement">departement</option>
                        </select>
                        <select value={step.approver_user_id} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, approver_user_id: event.target.value } : item) }))} className={inputClass}>
                          <option value="">Utilisateur specifique</option>
                          {users.map((user) => <option key={user.id} value={user.id}>{user.full_name || user.username} ({user.role_code})</option>)}
                        </select>
                        <input value={step.label} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item) }))} className={inputClass} placeholder="Libelle" />
                        <label className="md:col-span-5 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300"><input type="checkbox" checked={step.is_required} onChange={(event) => setRuleEditor((current) => ({ ...current, steps: current.steps.map((item, itemIndex) => itemIndex === index ? { ...item, is_required: event.target.checked } : item) }))} /> Validateur requis</label>
                        <button type="button" onClick={() => setRuleEditor((current) => ({ ...current, steps: current.steps.filter((_, itemIndex) => itemIndex !== index) }))} className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-100">Retirer</button>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => setRuleEditor((current) => ({ ...current, steps: [...current.steps, { step_order: current.steps.length + 1, parallel_group: 1, approver_kind: "manager", approver_role_code: "manager", approver_user_id: "", is_required: true, label: "" }] }))} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Ajouter une etape</button>
                    <button type="button" onClick={() => saveRuleMutation.mutate()} className="rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950">Enregistrer le circuit</button>
                  </div>
                </div>
              </>
            ) : <div className="mt-6 text-sm text-slate-400">Acces reserve RH / administration.</div>}
          </div>
        </section>
      ) : null}

      {canAdmin ? (
        <section className={panelClass}>
          <h2 className="text-xl font-semibold text-white">Planification intelligente du conge annuel</h2>
          <p className="text-sm text-slate-400">Scoring legal + anciennete + reliquats + continuite de service.</p>
          <div className="mt-6 grid gap-3 md:grid-cols-4">
            <input value={planningForm.title} onChange={(event) => setPlanningForm((current) => ({ ...current, title: event.target.value }))} className={inputClass} placeholder="Titre du cycle" />
            <input type="number" value={planningForm.planning_year} onChange={(event) => setPlanningForm((current) => ({ ...current, planning_year: Number(event.target.value) }))} className={inputClass} />
            <input type="date" value={planningForm.start_date} onChange={(event) => setPlanningForm((current) => ({ ...current, start_date: event.target.value }))} className={inputClass} />
            <input type="date" value={planningForm.end_date} onChange={(event) => setPlanningForm((current) => ({ ...current, end_date: event.target.value }))} className={inputClass} />
          </div>
          <button type="button" onClick={() => createCycleMutation.mutate()} disabled={!effectiveEmployerId} className="mt-4 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-40">Generer des propositions</button>
          <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {proposals.map((proposal) => (
              <div key={proposal.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="font-semibold text-white">{proposal.worker_name}</div>
                <div className="mt-1 text-sm text-slate-400">Score {proposal.score.toFixed(1)}</div>
                <div className="mt-3 space-y-2 text-sm text-slate-300">
                  {proposal.rationale.map((item, index) => <div key={`${proposal.id}-${index}`}>{item.message} ({item.weight})</div>)}
                </div>
              </div>
            ))}
            {!proposals.length ? <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-slate-400">Aucune proposition. Creez un cycle pour lancer le scoring.</div> : null}
          </div>
        </section>
      ) : null}

      {canValidate ? (
        <section className={panelClass}>
          <h2 className="text-xl font-semibold text-white">Rapprochement absence / pointage</h2>
          <p className="text-sm text-slate-400">Vue RH dediee aux demandes integrees et aux ecarts detectes.</p>
          <div className="mt-6 grid gap-3">
            {reconciliationRows.map((row) => (
              <div key={row.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="font-semibold text-white">{row.request_ref || `Demande #${row.leave_request_id}`} | {row.worker_name || `Salarie #${row.worker_id}`}</div>
                    <div className="mt-1 text-sm text-slate-400">
                      {row.start_date && row.end_date ? `${row.start_date} -> ${row.end_date}` : `Periode ${row.period}`}
                      {row.leave_type_code ? ` | ${row.leave_type_code}` : ""}
                    </div>
                    {row.subject ? <div className="mt-1 text-sm text-slate-300">{row.subject}</div> : null}
                  </div>
                  <div className="flex gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badge(row.status)}`}>{row.status}</span>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${badge(row.discrepancy_level)}`}>{row.discrepancy_level}</span>
                  </div>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2 text-sm text-slate-300">
                  <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Pointage / absences paie</div>
                    <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-slate-300">{JSON.stringify(row.attendance_payload, null, 2)}</pre>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Demande RH</div>
                    <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-slate-300">{JSON.stringify(row.leave_payload, null, 2)}</pre>
                  </div>
                </div>
                <div className="mt-3 text-sm text-amber-200">{row.notes}</div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button type="button" onClick={() => decisionMutation.mutate({ requestId: row.leave_request_id, action: "cancel", comment: "Annulation suite a conflit pointage/conge" })} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                    Annuler la demande
                  </button>
                  <button type="button" onClick={() => { const newType = window.prompt("Nouveau type (ex: PERMISSION_LEGALE)", row.leave_type_code || "PERMISSION_LEGALE"); const comment = window.prompt("Commentaire obligatoire pour la requalification", "Requalification suite a conflit pointage/conge"); if (newType && comment) requalifyMutation.mutate({ requestId: row.leave_request_id, newType, comment }); }} className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs font-semibold text-amber-100">
                    Requalifier
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm(`Supprimer la demande ${row.request_ref || row.leave_request_id} ?`)) {
                        deleteRequestMutation.mutate(row.leave_request_id);
                      }
                    }}
                    className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-100"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
            {!reconciliationRows.length ? <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-slate-400">Aucune reconciliation disponible sur le scope courant.</div> : null}
          </div>
        </section>
      ) : null}

      {effectiveEmployerId ? (
        <WorkCalendar
          isOpen={isCalendarOpen}
          onClose={() => setIsCalendarOpen(false)}
          employerId={effectiveEmployerId}
          initialPeriod={dashboard?.period ?? new Date().toISOString().slice(0, 7)}
          title={`Calendrier ${calendarScope === "global" ? "global" : calendarScope === "team" ? "équipe" : "personnel"}`}
          workerId={effectiveCalendarWorkerId}
          editable={canAdmin}
          showAgenda
        />
      ) : null}
    </div>
  );
}
