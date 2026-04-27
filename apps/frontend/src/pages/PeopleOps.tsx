import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AcademicCapIcon,
  ArrowPathIcon,
  BriefcaseIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface Worker {
  id: number;
  nom: string;
  prenom: string;
  matricule?: string | null;
}

interface DashboardData {
  workforce: Record<string, number | null>;
  performance: Record<string, number | null>;
  training: Record<string, number | null>;
  discipline: Record<string, number | null>;
  safety: Record<string, number | null>;
  alerts: Array<{ severity: string; message: string }>;
  legal_status?: LegalModulesStatus;
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

interface JobProfile {
  id: number;
  title: string;
  department?: string | null;
  criticality: string;
}

interface PerformanceCycle {
  id: number;
  name: string;
}

interface PerformanceReview {
  id: number;
  status: string;
  overall_score?: number | null;
  worker_id: number;
}

interface Training {
  id: number;
  title: string;
}

interface TrainingNeed {
  id: number;
  title: string;
  status: string;
}

interface TrainingPlan {
  id: number;
  name: string;
  plan_year: number;
}

interface DisciplineCase {
  id: number;
  subject: string;
  status: string;
}

interface TerminationWorkflow {
  id: number;
  motif: string;
  status: string;
}

interface DuerEntry {
  id: number;
  hazard: string;
  risk_family: string;
}

interface PreventionAction {
  id: number;
  action_title: string;
  status: string;
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";


export default function PeopleOps() {
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [jobProfileForm, setJobProfileForm] = useState({ title: "", department: "", criticality: "medium" });
  const [cycleForm, setCycleForm] = useState({
    name: "",
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date().toISOString().slice(0, 10),
  });
  const [reviewForm, setReviewForm] = useState({ cycle_id: "", overall_score: "3.5", status: "manager_review" });
  const [needForm, setNeedForm] = useState({ title: "", target_skill: "", due_date: "", recommended_training_id: "" });
  const [planForm, setPlanForm] = useState({ name: "", plan_year: String(new Date().getFullYear()), budget_amount: "0" });
  const [disciplineForm, setDisciplineForm] = useState({ subject: "", case_type: "warning" });
  const [terminationForm, setTerminationForm] = useState({
    motif: "",
    termination_type: "resignation",
    effective_date: new Date().toISOString().slice(0, 10),
    sensitive_case: false,
  });
  const [duerForm, setDuerForm] = useState({ site_name: "", risk_family: "", hazard: "", probability: "2", severity: "2" });
  const [preventionForm, setPreventionForm] = useState({ action_title: "", due_date: new Date().toISOString().slice(0, 10), inspection_follow_up: false });

  const { data: employers = [] } = useQuery({
    queryKey: ["people-ops", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const effectiveEmployerId = useMemo(() => {
    if (selectedEmployerId !== null && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["people-ops", "workers", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<Worker[]>("/workers", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const effectiveWorkerId = useMemo(() => {
    if (selectedWorkerId !== null && workers.some((item) => item.id === selectedWorkerId)) {
      return selectedWorkerId;
    }
    return workers[0]?.id ?? null;
  }, [workers, selectedWorkerId]);

  const { data: dashboard } = useQuery({
    queryKey: ["people-ops", "dashboard", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<DashboardData>("/people-ops/dashboard", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: jobProfiles = [] } = useQuery({
    queryKey: ["people-ops", "job-profiles", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<JobProfile[]>("/people-ops/job-profiles", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: cycles = [] } = useQuery({
    queryKey: ["people-ops", "performance-cycles", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<PerformanceCycle[]>("/people-ops/performance-cycles", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: reviews = [] } = useQuery({
    queryKey: ["people-ops", "performance-reviews", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<PerformanceReview[]>("/people-ops/performance-reviews", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: trainings = [] } = useQuery({
    queryKey: ["people-ops", "trainings", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<Training[]>("/talents/trainings", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: trainingNeeds = [] } = useQuery({
    queryKey: ["people-ops", "training-needs", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<TrainingNeed[]>("/people-ops/training-needs", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: trainingPlans = [] } = useQuery({
    queryKey: ["people-ops", "training-plans", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<TrainingPlan[]>("/people-ops/training-plans", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: disciplinaryCases = [] } = useQuery({
    queryKey: ["people-ops", "disciplinary", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<DisciplineCase[]>("/people-ops/disciplinary-cases", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: terminations = [] } = useQuery({
    queryKey: ["people-ops", "terminations", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<TerminationWorkflow[]>("/people-ops/termination-workflows", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: duerEntries = [] } = useQuery({
    queryKey: ["people-ops", "duer", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<DuerEntry[]>("/people-ops/duer", { params: { employer_id: effectiveEmployerId } })).data,
  });

  const { data: preventionActions = [] } = useQuery({
    queryKey: ["people-ops", "prevention", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (await api.get<PreventionAction[]>("/people-ops/prevention-actions", { params: { employer_id: effectiveEmployerId } })).data,
  });
  const dashboardWorkforce = dashboard?.workforce ?? {};
  const dashboardPerformance = dashboard?.performance ?? {};
  const dashboardTraining = dashboard?.training ?? {};
  const dashboardDiscipline = dashboard?.discipline ?? {};
  const dashboardSafety = dashboard?.safety ?? {};
  const dashboardAlerts = dashboard?.alerts ?? [];
  const legalStatus = dashboard?.legal_status;

  const invalidatePeopleOps = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["people-ops", "dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "job-profiles"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "performance-cycles"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "performance-reviews"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "training-needs"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "training-plans"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "disciplinary"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "terminations"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "duer"] }),
      queryClient.invalidateQueries({ queryKey: ["people-ops", "prevention"] }),
    ]);
  };

  const jobProfileMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null) {
        throw new Error("Aucun employeur disponible.");
      }
      return (
        await api.post("/people-ops/job-profiles", {
          employer_id: effectiveEmployerId,
          title: jobProfileForm.title,
          department: jobProfileForm.department || null,
          criticality: jobProfileForm.criticality,
          required_skills: [],
          mobility_paths: [],
          succession_candidates: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setJobProfileForm({ title: "", department: "", criticality: "medium" });
      setFeedback("Profil emploi GPEC enregistre.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation du profil impossible."),
  });

  const cycleMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null) {
        throw new Error("Aucun employeur disponible.");
      }
      return (
        await api.post("/people-ops/performance-cycles", {
          employer_id: effectiveEmployerId,
          name: cycleForm.name,
          cycle_type: "annual",
          start_date: cycleForm.start_date,
          end_date: cycleForm.end_date,
          status: "draft",
          objectives: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setCycleForm({ name: "", start_date: new Date().toISOString().slice(0, 10), end_date: new Date().toISOString().slice(0, 10) });
      setFeedback("Campagne d'evaluation creee.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation de la campagne impossible."),
  });

  const reviewMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null || effectiveWorkerId === null) {
        throw new Error("Employeur ou salarie indisponible.");
      }
      return (
        await api.post("/people-ops/performance-reviews", {
          cycle_id: Number(reviewForm.cycle_id),
          employer_id: effectiveEmployerId,
          worker_id: effectiveWorkerId,
          status: reviewForm.status,
          overall_score: Number(reviewForm.overall_score),
          objectives: [],
          competencies: [],
          development_actions: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setReviewForm({ cycle_id: "", overall_score: "3.5", status: "manager_review" });
      setFeedback("Evaluation individuelle enregistree.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation de l'evaluation impossible."),
  });

  const needMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null || effectiveWorkerId === null) {
        throw new Error("Employeur ou salarie indisponible.");
      }
      return (
        await api.post("/people-ops/training-needs", {
          employer_id: effectiveEmployerId,
          worker_id: effectiveWorkerId,
          source: "evaluation",
          priority: "medium",
          title: needForm.title,
          description: null,
          target_skill: needForm.target_skill || null,
          due_date: needForm.due_date || null,
          recommended_training_id: needForm.recommended_training_id ? Number(needForm.recommended_training_id) : null,
        })
      ).data;
    },
    onSuccess: async () => {
      setNeedForm({ title: "", target_skill: "", due_date: "", recommended_training_id: "" });
      setFeedback("Besoin de formation identifie.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation du besoin impossible."),
  });

  const planMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null) {
        throw new Error("Aucun employeur disponible.");
      }
      return (
        await api.post("/people-ops/training-plans", {
          employer_id: effectiveEmployerId,
          name: planForm.name,
          plan_year: Number(planForm.plan_year),
          budget_amount: Number(planForm.budget_amount),
          status: "draft",
          objectives: [],
          fmfp_tracking: {},
        })
      ).data;
    },
    onSuccess: async () => {
      setPlanForm({ name: "", plan_year: String(new Date().getFullYear()), budget_amount: "0" });
      setFeedback("Plan de formation cree.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation du plan impossible."),
  });

  const disciplineMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null || effectiveWorkerId === null) {
        throw new Error("Employeur ou salarie indisponible.");
      }
      return (
        await api.post("/people-ops/disciplinary-cases", {
          employer_id: effectiveEmployerId,
          worker_id: effectiveWorkerId,
          case_type: disciplineForm.case_type,
          severity: "medium",
          status: "draft",
          subject: disciplineForm.subject,
          description: disciplineForm.subject,
          documents: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setDisciplineForm({ subject: "", case_type: "warning" });
      setFeedback("Dossier disciplinaire cree.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation du dossier disciplinaire impossible."),
  });

  const terminationMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null || effectiveWorkerId === null) {
        throw new Error("Employeur ou salarie indisponible.");
      }
      return (
        await api.post("/people-ops/termination-workflows", {
          employer_id: effectiveEmployerId,
          worker_id: effectiveWorkerId,
          termination_type: terminationForm.termination_type,
          motif: terminationForm.motif,
          status: "draft",
          effective_date: terminationForm.effective_date,
          sensitive_case: terminationForm.sensitive_case,
          inspection_required: terminationForm.sensitive_case,
          checklist: [],
          documents: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setTerminationForm({
        motif: "",
        termination_type: "resignation",
        effective_date: new Date().toISOString().slice(0, 10),
        sensitive_case: false,
      });
      setFeedback("Workflow de rupture cree.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation du workflow de rupture impossible."),
  });

  const duerMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null) {
        throw new Error("Aucun employeur disponible.");
      }
      return (
        await api.post("/people-ops/duer", {
          employer_id: effectiveEmployerId,
          site_name: duerForm.site_name,
          risk_family: duerForm.risk_family,
          hazard: duerForm.hazard,
          probability: Number(duerForm.probability),
          severity: Number(duerForm.severity),
        })
      ).data;
    },
    onSuccess: async () => {
      setDuerForm({ site_name: "", risk_family: "", hazard: "", probability: "2", severity: "2" });
      setFeedback("Risque DUER enregistre.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation DUER impossible."),
  });

  const preventionMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null) {
        throw new Error("Aucun employeur disponible.");
      }
      return (
        await api.post("/people-ops/prevention-actions", {
          employer_id: effectiveEmployerId,
          action_title: preventionForm.action_title,
          due_date: preventionForm.due_date,
          inspection_follow_up: preventionForm.inspection_follow_up,
        })
      ).data;
    },
    onSuccess: async () => {
      setPreventionForm({ action_title: "", due_date: new Date().toISOString().slice(0, 10), inspection_follow_up: false });
      setFeedback("Action PAP enregistree.");
      await invalidatePeopleOps();
    },
    onError: (error) => setFeedback(error instanceof Error ? error.message : "Creation de l'action PAP impossible."),
  });

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(35,65,90,0.9),rgba(21,128,61,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Pilotage RH avance
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Evaluations, GPEC, formation, discipline et DUER/PAP</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Cockpit RH pour Madagascar: parcours talent, besoins de formation, workflows sensibles et prevention SST.
            </p>
            <p className="mt-2 text-xs text-cyan-100/70">
              Les referentiels competences et catalogues de formation restent centralises dans le module Talents & Formation.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:min-w-[320px]">
            <select className={inputClassName} value={effectiveEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))}>
              {employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.raison_sociale}</option>)}
            </select>
            <select className={inputClassName} value={effectiveWorkerId ?? ""} onChange={(event) => setSelectedWorkerId(Number(event.target.value))}>
              {workers.map((worker) => <option key={worker.id} value={worker.id}>{worker.nom} {worker.prenom} {worker.matricule ? `(${worker.matricule})` : ""}</option>)}
            </select>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-5">
        <div className={cardClassName}><div className="text-xs uppercase tracking-[0.22em] text-slate-500">Effectif actif</div><div className="mt-3 text-3xl font-semibold text-white">{dashboardWorkforce.workers_active ?? 0}</div></div>
        <div className={cardClassName}><div className="text-xs uppercase tracking-[0.22em] text-slate-500">Evaluations ouvertes</div><div className="mt-3 text-3xl font-semibold text-white">{dashboardPerformance.reviews_open ?? 0}</div></div>
        <div className={cardClassName}><div className="text-xs uppercase tracking-[0.22em] text-slate-500">Besoins formation</div><div className="mt-3 text-3xl font-semibold text-white">{dashboardTraining.needs_open ?? 0}</div></div>
        <div className={cardClassName}><div className="text-xs uppercase tracking-[0.22em] text-slate-500">Disciplinaire / rupture</div><div className="mt-3 text-3xl font-semibold text-white">{(dashboardDiscipline.disciplinary_open ?? 0) + (dashboardDiscipline.terminations_open ?? 0)}</div></div>
        <div className={cardClassName}><div className="text-xs uppercase tracking-[0.22em] text-slate-500">SST / PAP</div><div className="mt-3 text-3xl font-semibold text-white">{(dashboardSafety.duer_open ?? 0) + (dashboardSafety.prevention_actions_open ?? 0)}</div></div>
      </section>

      {feedback ? <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">{feedback}</div> : null}
      {dashboardAlerts.length ? (
        <section className={cardClassName}>
          <div className="flex items-center gap-3">
            <ExclamationTriangleIcon className="h-6 w-6 text-amber-300" />
            <h2 className="text-xl font-semibold text-white">Alertes prioritaires</h2>
          </div>
          <div className="mt-4 grid gap-3 xl:grid-cols-2">
            {dashboardAlerts.map((alert, index) => (
              <div key={`${alert.message}-${index}`} className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-4 text-sm text-amber-50">{alert.message}</div>
            ))}
          </div>
        </section>
      ) : null}

      {legalStatus ? (
        <section className={cardClassName}>
          <div className="flex items-center gap-3">
            <ShieldExclamationIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">SIIRH LEGAL MODULES STATUS</h2>
              <p className="text-sm text-slate-400">Etat visible des workflows malgaches relies au moteur RH courant.</p>
            </div>
          </div>
          <div className="mt-6 grid gap-4 xl:grid-cols-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Modules implementes</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus.modules_implemented}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Procedures creees</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus.procedures_created}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">PV generes</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus.pv_generated}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Tests reperes</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus.test_cases}</div>
            </div>
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <div>
              <div className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-200">Entreprises et cas visibles</div>
              <div className="mt-3 grid gap-3">
                {legalStatus.employers.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 text-sm text-slate-200">
                    <div className="font-semibold text-white">{item.raison_sociale}</div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <div>Salaries: <span className="font-semibold text-white">{item.workers}</span></div>
                      <div>Dossiers inspection: <span className="font-semibold text-white">{item.inspection_cases}</span></div>
                      <div>PV visibles: <span className="font-semibold text-white">{item.pv_generated}</span></div>
                      <div>Ruptures suivies: <span className="font-semibold text-white">{item.termination_workflows}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                <div className="text-sm font-semibold text-white">Highlights juridiques</div>
                <div className="mt-3 space-y-3 text-sm text-slate-300">
                  {legalStatus.highlights.map((item) => (
                    <div key={item.label} className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3">
                      <span>{item.label}</span>
                      <span className="font-semibold text-white">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                <div className="text-sm font-semibold text-white">Couverture des roles</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {legalStatus.role_coverage.map((item) => (
                    <span key={item} className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-100">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-2">
        <div className={cardClassName}>
          <div className="flex items-center gap-3"><BriefcaseIcon className="h-6 w-6 text-cyan-300" /><h2 className="text-xl font-semibold text-white">GPEC & profils emplois</h2></div>
          <div className="mt-6 grid gap-4">
            <input className={inputClassName} value={jobProfileForm.title} onChange={(event) => setJobProfileForm((current) => ({ ...current, title: event.target.value }))} placeholder="Intitule du poste" />
            <input className={inputClassName} value={jobProfileForm.department} onChange={(event) => setJobProfileForm((current) => ({ ...current, department: event.target.value }))} placeholder="Departement / service" />
            <select className={inputClassName} value={jobProfileForm.criticality} onChange={(event) => setJobProfileForm((current) => ({ ...current, criticality: event.target.value }))}>
              <option value="low">Faible</option><option value="medium">Moyenne</option><option value="high">Elevee</option><option value="critical">Critique</option>
            </select>
            <button type="button" onClick={() => jobProfileMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">{jobProfileMutation.isPending ? "Enregistrement..." : "Creer un profil emploi"}</button>
          </div>
          <div className="mt-6 space-y-3">
            {jobProfiles.slice(0, 5).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">{item.title} • {item.department || "Sans departement"} • {item.criticality}</div>)}
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3"><ChartBarIcon className="h-6 w-6 text-cyan-300" /><h2 className="text-xl font-semibold text-white">Evaluations & campagnes</h2></div>
          <div className="mt-6 grid gap-4">
            <input className={inputClassName} value={cycleForm.name} onChange={(event) => setCycleForm((current) => ({ ...current, name: event.target.value }))} placeholder="Campagne annuelle 2026" />
            <div className="grid gap-4 sm:grid-cols-2">
              <input type="date" className={inputClassName} value={cycleForm.start_date} onChange={(event) => setCycleForm((current) => ({ ...current, start_date: event.target.value }))} />
              <input type="date" className={inputClassName} value={cycleForm.end_date} onChange={(event) => setCycleForm((current) => ({ ...current, end_date: event.target.value }))} />
            </div>
            <button type="button" onClick={() => cycleMutation.mutate()} className="rounded-2xl border border-cyan-300/30 bg-white/5 px-4 py-3 text-sm font-semibold text-cyan-100">{cycleMutation.isPending ? "Creation..." : "Creer une campagne"}</button>
            <select className={inputClassName} value={reviewForm.cycle_id} onChange={(event) => setReviewForm((current) => ({ ...current, cycle_id: event.target.value }))}>
              <option value="">Selectionnez une campagne</option>
              {cycles.map((cycle) => <option key={cycle.id} value={cycle.id}>{cycle.name}</option>)}
            </select>
            <input className={inputClassName} value={reviewForm.overall_score} onChange={(event) => setReviewForm((current) => ({ ...current, overall_score: event.target.value }))} placeholder="Score global /5" />
            <button type="button" onClick={() => reviewMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">{reviewMutation.isPending ? "Enregistrement..." : "Creer une evaluation"}</button>
          </div>
          <div className="mt-6 space-y-3">
            {reviews.slice(0, 5).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">Salarie #{item.worker_id} • {item.status} • score {item.overall_score ?? "n/a"}</div>)}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className={cardClassName}>
          <div className="flex items-center gap-3"><AcademicCapIcon className="h-6 w-6 text-cyan-300" /><h2 className="text-xl font-semibold text-white">Besoins et plan de formation</h2></div>
          <div className="mt-6 grid gap-4">
            <input className={inputClassName} value={needForm.title} onChange={(event) => setNeedForm((current) => ({ ...current, title: event.target.value }))} placeholder="Besoin de formation" />
            <input className={inputClassName} value={needForm.target_skill} onChange={(event) => setNeedForm((current) => ({ ...current, target_skill: event.target.value }))} placeholder="Competence cible" />
            <div className="grid gap-4 sm:grid-cols-2">
              <input type="date" className={inputClassName} value={needForm.due_date} onChange={(event) => setNeedForm((current) => ({ ...current, due_date: event.target.value }))} />
              <select className={inputClassName} value={needForm.recommended_training_id} onChange={(event) => setNeedForm((current) => ({ ...current, recommended_training_id: event.target.value }))}>
                <option value="">Formation recommandee</option>
                {trainings.map((training) => <option key={training.id} value={training.id}>{training.title}</option>)}
              </select>
            </div>
            <button type="button" onClick={() => needMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">{needMutation.isPending ? "Enregistrement..." : "Creer un besoin"}</button>
            <input className={inputClassName} value={planForm.name} onChange={(event) => setPlanForm((current) => ({ ...current, name: event.target.value }))} placeholder="Plan de formation 2026" />
            <div className="grid gap-4 sm:grid-cols-2">
              <input className={inputClassName} value={planForm.plan_year} onChange={(event) => setPlanForm((current) => ({ ...current, plan_year: event.target.value }))} placeholder="Annee" />
              <input className={inputClassName} value={planForm.budget_amount} onChange={(event) => setPlanForm((current) => ({ ...current, budget_amount: event.target.value }))} placeholder="Budget Ariary" />
            </div>
            <button type="button" onClick={() => planMutation.mutate()} className="rounded-2xl border border-cyan-300/30 bg-white/5 px-4 py-3 text-sm font-semibold text-cyan-100">{planMutation.isPending ? "Creation..." : "Creer le plan"}</button>
          </div>
          <div className="mt-6 grid gap-3">
            {trainingNeeds.slice(0, 4).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">{item.title} • {item.status}</div>)}
            {trainingPlans.slice(0, 4).map((item) => <div key={item.id} className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-50">{item.name} • {item.plan_year}</div>)}
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3"><ShieldExclamationIcon className="h-6 w-6 text-cyan-300" /><h2 className="text-xl font-semibold text-white">Disciplinaire, rupture et prevention</h2></div>
          <div className="mt-6 grid gap-4">
            <input className={inputClassName} value={disciplineForm.subject} onChange={(event) => setDisciplineForm((current) => ({ ...current, subject: event.target.value }))} placeholder="Objet du dossier disciplinaire" />
            <select className={inputClassName} value={disciplineForm.case_type} onChange={(event) => setDisciplineForm((current) => ({ ...current, case_type: event.target.value }))}>
              <option value="warning">Avertissement</option><option value="hearing">Entretien disciplinaire</option><option value="suspension">Mesure conservatoire</option>
            </select>
            <button type="button" onClick={() => disciplineMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">{disciplineMutation.isPending ? "Creation..." : "Creer un dossier disciplinaire"}</button>
            <input className={inputClassName} value={terminationForm.motif} onChange={(event) => setTerminationForm((current) => ({ ...current, motif: event.target.value }))} placeholder="Motif de rupture / licenciement" />
            <div className="grid gap-4 sm:grid-cols-2">
              <select className={inputClassName} value={terminationForm.termination_type} onChange={(event) => setTerminationForm((current) => ({ ...current, termination_type: event.target.value }))}>
                <option value="resignation">Demission</option><option value="dismissal">Licenciement</option><option value="economic_dismissal">Licenciement economique</option>
              </select>
              <input type="date" className={inputClassName} value={terminationForm.effective_date} onChange={(event) => setTerminationForm((current) => ({ ...current, effective_date: event.target.value }))} />
            </div>
            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300"><input type="checkbox" checked={terminationForm.sensitive_case} onChange={(event) => setTerminationForm((current) => ({ ...current, sensitive_case: event.target.checked }))} /> Cas sensible / inspection requise</label>
            <button type="button" onClick={() => terminationMutation.mutate()} className="rounded-2xl border border-cyan-300/30 bg-white/5 px-4 py-3 text-sm font-semibold text-cyan-100">{terminationMutation.isPending ? "Creation..." : "Creer un workflow de rupture"}</button>

            <div className="grid gap-4 sm:grid-cols-2">
              <input className={inputClassName} value={duerForm.site_name} onChange={(event) => setDuerForm((current) => ({ ...current, site_name: event.target.value }))} placeholder="Site / etablissement" />
              <input className={inputClassName} value={duerForm.risk_family} onChange={(event) => setDuerForm((current) => ({ ...current, risk_family: event.target.value }))} placeholder="Famille de risque" />
            </div>
            <input className={inputClassName} value={duerForm.hazard} onChange={(event) => setDuerForm((current) => ({ ...current, hazard: event.target.value }))} placeholder="Danger identifie" />
            <button type="button" onClick={() => duerMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950">{duerMutation.isPending ? "Enregistrement..." : "Ajouter au DUER"}</button>
            <input className={inputClassName} value={preventionForm.action_title} onChange={(event) => setPreventionForm((current) => ({ ...current, action_title: event.target.value }))} placeholder="Action de prevention / PAP" />
            <div className="grid gap-4 sm:grid-cols-2">
              <input type="date" className={inputClassName} value={preventionForm.due_date} onChange={(event) => setPreventionForm((current) => ({ ...current, due_date: event.target.value }))} />
              <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300"><input type="checkbox" checked={preventionForm.inspection_follow_up} onChange={(event) => setPreventionForm((current) => ({ ...current, inspection_follow_up: event.target.checked }))} /> Suivi inspection</label>
            </div>
            <button type="button" onClick={() => preventionMutation.mutate()} className="rounded-2xl border border-cyan-300/30 bg-white/5 px-4 py-3 text-sm font-semibold text-cyan-100">{preventionMutation.isPending ? "Creation..." : "Creer une action PAP"}</button>
          </div>
          <div className="mt-6 grid gap-3">
            {disciplinaryCases.slice(0, 3).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">{item.subject} • {item.status}</div>)}
            {terminations.slice(0, 3).map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">{item.motif} • {item.status}</div>)}
            {duerEntries.slice(0, 2).map((item) => <div key={item.id} className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-50">{item.risk_family} • {item.hazard}</div>)}
            {preventionActions.slice(0, 2).map((item) => <div key={item.id} className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-50">{item.action_title} • {item.status}</div>)}
          </div>
        </div>
      </section>

      <section className={cardClassName}>
        <div className="flex items-center gap-3"><ArrowPathIcon className="h-6 w-6 text-cyan-300" /><h2 className="text-xl font-semibold text-white">Vue rapide RH Madagascar</h2></div>
        <div className="mt-4 grid gap-3 xl:grid-cols-4 text-sm text-slate-300">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">Postes critiques: {jobProfiles.filter((item) => item.criticality === "critical").length}</div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">Formations catalogue: {trainings.length}</div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">Evaluations saisies: {reviews.length}</div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">Actions prevention: {preventionActions.length}</div>
        </div>
      </section>
    </div>
  );
}
