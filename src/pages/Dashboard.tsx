import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AcademicCapIcon,
  BriefcaseIcon,
  BuildingOfficeIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  Squares2X2Icon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";
import { useAuth } from "../contexts/AuthContext";
import { sessionHasRole } from "../rbac";
import { formatCount } from "../utils/format";


interface Employer {
  id: number;
}

interface WorkerPagination {
  total: number;
}

interface JobPosting {
  id: number;
}

interface ContractSummary {
  id: number;
}

interface Training {
  id: number;
}

interface Incident {
  id: number;
}

interface ModuleCard {
  title: string;
  path: string;
  description: string;
  status: string;
  icon: ComponentType<{ className?: string }>;
  metric?: string;
}

interface LegalModulesStatus {
  modules_implemented: number;
  procedures_created: number;
  pv_generated: number;
  test_cases: number;
  employers: Array<{
    id: number;
    raison_sociale: string;
    workers: number;
    inspection_cases: number;
    pv_generated: number;
    termination_workflows: number;
  }>;
  highlights: Array<{ label: string; value: number }>;
  role_coverage: string[];
}

interface DebugExecutionItem {
  label: string;
  value: string;
  at?: string | null;
}

interface DebugExecutionPanel {
  last_migrations_executed: DebugExecutionItem[];
  last_seed_executed: DebugExecutionItem[];
  last_errors: DebugExecutionItem[];
  modules_created: DebugExecutionItem[];
}

const shellCardClassName =
  "siirh-panel";


export default function Dashboard() {
  const { session } = useAuth();
  const canSeeDebugPanel = sessionHasRole(session, ["admin", "system_admin", "super_administrateur_systeme"]);

  const { data: employers = [] } = useQuery({
    queryKey: ["dashboard", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const { data: workersSummary } = useQuery({
    queryKey: ["dashboard", "workers"],
    queryFn: async () => (
      await api.get<WorkerPagination>("/workers/paginated", {
        params: { page: 1, page_size: 1 },
      })
    ).data,
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ["dashboard", "recruitment-jobs"],
    queryFn: async () => (await api.get<JobPosting[]>("/recruitment/jobs")).data,
  });

  const { data: contracts = [] } = useQuery({
    queryKey: ["dashboard", "contracts"],
    queryFn: async () => (await api.get<ContractSummary[]>("/custom-contracts")).data,
  });

  const { data: trainings = [] } = useQuery({
    queryKey: ["dashboard", "talent-trainings"],
    queryFn: async () => (await api.get<Training[]>("/talents/trainings")).data,
  });

  const { data: incidents = [] } = useQuery({
    queryKey: ["dashboard", "sst-incidents"],
    queryFn: async () => (await api.get<Incident[]>("/sst/incidents")).data,
  });

  const { data: legalStatus } = useQuery({
    queryKey: ["dashboard", "legal-modules-status"],
    queryFn: async () => (await api.get<LegalModulesStatus>("/compliance/legal-modules-status")).data,
  });

  const { data: debugPanel } = useQuery({
    queryKey: ["dashboard", "debug-execution-panel"],
    enabled: canSeeDebugPanel,
    queryFn: async () => (await api.get<DebugExecutionPanel>("/system-update/debug-execution-panel")).data,
  });

  const modules: ModuleCard[] = [
    {
      title: "Recrutement",
      path: "/recruitment",
      description: "Fiches de poste, candidats, candidatures et pipeline de selection.",
      status: "Actif",
      icon: BriefcaseIcon,
      metric: `${jobs.length} postes ouverts`,
    },
    {
      title: "Contrats",
      path: "/contracts",
      description: "Contrats, attestations et certificats de travail prets a imprimer.",
      status: "Actif",
      icon: ClipboardDocumentListIcon,
      metric: `${formatCount(contracts.length)} contrat${contracts.length > 1 ? "s" : ""} enregistres`,
    },
    {
      title: "Employeurs",
      path: "/employers",
      description: "Base employeurs, etablissements et parametres RH / paie.",
      status: "Actif",
      icon: BuildingOfficeIcon,
      metric: `${formatCount(employers.length)} employeur${employers.length > 1 ? "s" : ""}`,
    },
    {
      title: "Talents",
      path: "/talents",
      description: "Competences, affectations et plan de formation.",
      status: "Actif",
      icon: AcademicCapIcon,
      metric: `${formatCount(trainings.length)} formation${trainings.length > 1 ? "s" : ""}`,
    },
    {
      title: "SST / AT-MP",
      path: "/sst",
      description: "Incidents, accidents, mesures prises et suivi de traitement.",
      status: "Actif",
      icon: ShieldCheckIcon,
      metric: `${formatCount(incidents.length)} incident${incidents.length > 1 ? "s" : ""}`,
    },
    {
      title: "Declarations",
      path: "/declarations",
      description: "Pilotage mensuel des obligations sociales et pieces a produire.",
      status: "Actif",
      icon: ExclamationTriangleIcon,
    },
    {
      title: "Organisation",
      path: "/organization",
      description: "Structure classique et hierarchique par employeur.",
      status: "Actif",
      icon: Squares2X2Icon,
    },
    {
      title: "Reporting",
      path: "/reporting",
      description: "Exports et controles croises RH / paie.",
      status: "Actif",
      icon: ChartBarIcon,
    },
    {
      title: "Salarie 360",
      path: "/employee-360",
      description: "Source canonique intermodules pour verifier que les donnees deja saisies alimentent bien RH, contrats, recrutement et conformite.",
      status: "Actif",
      icon: UserGroupIcon,
      metric: `${formatCount(workersSummary?.total ?? 0)} dossiers synchronisables`,
    },
  ];

  return (
    <div className="siirh-page">
      <section className="rounded-[2rem] border border-sky-300/25 bg-[linear-gradient(135deg,rgba(15,23,42,0.96),rgba(30,58,138,0.90),rgba(12,74,110,0.90))] p-8 shadow-xl shadow-slate-900/20">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-sky-100">
              SIIRH / SIHMADA
            </div>
            <h1 className="mt-6 text-[2.75rem] font-semibold tracking-tight text-white lg:text-[3rem]">
              Plateforme RH, paie et conformite
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-8 text-cyan-50/90">
              Les modules prioritaires du cahier des charges sont exposes depuis
              l&apos;accueil: recrutement, contrats, structure, talents, SST,
              declarations, paie et reporting.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-sm uppercase tracking-[0.24em] text-cyan-100/70">Employeurs</div>
              <div className="mt-3 text-[2.1rem] font-semibold text-white">{formatCount(employers.length)}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-sm uppercase tracking-[0.24em] text-cyan-100/70">Salaries</div>
              <div className="mt-3 text-[2.1rem] font-semibold text-white">{formatCount(workersSummary?.total ?? 0)}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-sm uppercase tracking-[0.24em] text-cyan-100/70">Postes</div>
              <div className="mt-3 text-[2.1rem] font-semibold text-white">{formatCount(jobs.length)}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.35fr_0.9fr]">
        <div className={shellCardClassName}>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3">
              <Squares2X2Icon className="h-6 w-6 text-cyan-300" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Modules disponibles</h2>
              <p className="text-base text-slate-400">
                Acces directs aux parcours RH prioritaires.
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            {modules.map((module) => {
              const Icon = module.icon;

              return (
                <Link
                  key={module.path}
                  to={module.path}
                    className="group rounded-[1.2rem] border border-slate-200 bg-white/80 p-5 transition hover:-translate-y-0.5 hover:border-sky-300"
                  >
                  <div className="flex items-start justify-between gap-4">
                    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-3">
                      <Icon className="h-6 w-6 text-cyan-300" />
                    </div>
                    <span className="status-success">
                      {module.status}
                    </span>
                  </div>

                  <div className="mt-5">
                    <h3 className="text-xl font-semibold text-slate-900">{module.title}</h3>
                    <p className="mt-2 text-[15px] leading-7 text-slate-600">{module.description}</p>
                    {module.metric ? (
                      <div className="mt-4 text-[15px] font-medium text-sky-700">{module.metric}</div>
                    ) : null}
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="space-y-6">
          <section className={shellCardClassName}>
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 p-3">
                <UserGroupIcon className="h-6 w-6 text-amber-200" />
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-white">Parcours RH exposes</h2>
                <p className="text-base text-slate-400">Visibilite immediate cote demo.</p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-5 py-4">
                <div className="text-base font-semibold text-white">Administration du personnel</div>
                <div className="mt-2 text-[15px] text-slate-400">
                  Employeurs, travailleurs, contrats et structure organisationnelle.
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-5 py-4">
                <div className="text-base font-semibold text-white">Cycle RH et talents</div>
                <div className="mt-2 text-[15px] text-slate-400">
                  Recrutement, competences, formation, SST et suivi documentaire.
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-5 py-4">
                <div className="text-base font-semibold text-white">Paie et conformite</div>
                <div className="mt-2 text-[15px] text-slate-400">
                  Paie preservee, declarations et reporting exposes sans toucher au moteur.
                </div>
              </div>
            </div>
          </section>

          <section className={shellCardClassName}>
            <h2 className="text-2xl font-semibold text-white">Acces rapide</h2>
            <div className="mt-5 grid gap-3">
              <Link
                to="/workers"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[15px] font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white"
              >
                Ouvrir les dossiers salaries
              </Link>
              <Link
                to="/payroll"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[15px] font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white"
              >
                Ouvrir la paie
              </Link>
              <Link
                to="/reporting"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[15px] font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white"
              >
                Ouvrir le reporting
              </Link>
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className={shellCardClassName}>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
              <ShieldCheckIcon className="h-6 w-6 text-emerald-300" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">SIIRH LEGAL MODULES STATUS</h2>
              <p className="text-base text-slate-400">Etat visible des workflows juridiques relies au backend reel.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-4">
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-200">Modules implemented</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus?.modules_implemented ?? 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-200">Procedures created</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus?.procedures_created ?? 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-200">PV generated</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus?.pv_generated ?? 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-emerald-200">Test cases</div>
              <div className="mt-3 text-3xl font-semibold text-white">{legalStatus?.test_cases ?? 0}</div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            {(legalStatus?.employers ?? []).map((item) => (
              <div key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
                <div className="text-lg font-semibold text-white">{item.raison_sociale}</div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-slate-300">Salaries: <span className="font-semibold text-white">{item.workers}</span></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-slate-300">Dossiers: <span className="font-semibold text-white">{item.inspection_cases}</span></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-slate-300">PV: <span className="font-semibold text-white">{item.pv_generated}</span></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-slate-300">Ruptures: <span className="font-semibold text-white">{item.termination_workflows}</span></div>
                </div>
              </div>
            ))}
          </div>

          {(legalStatus?.highlights?.length ?? 0) > 0 ? (
            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {legalStatus?.highlights.map((item) => (
                <div key={item.label} className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-50">
                  {item.label}: <span className="font-semibold">{item.value}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className={shellCardClassName}>
          <h2 className="text-xl font-semibold text-white">Legal Access Coverage</h2>
          <p className="mt-2 text-base text-slate-400">Profils actives pour controle, contentieux et lecture externe.</p>
          <div className="mt-6 flex flex-wrap gap-2">
            {(legalStatus?.role_coverage ?? []).map((item) => (
              <span key={item} className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200">{item}</span>
            ))}
          </div>
          <div className="mt-6 grid gap-3">
            <Link to="/inspection" className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[15px] font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white">
              Ouvrir l&apos;inspection
            </Link>
            <Link to="/people-ops" className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[15px] font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white">
              Ouvrir les workflows de rupture
            </Link>
            <Link to="/workers" className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[15px] font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white">
              Ouvrir la liste des salaries
            </Link>
          </div>
        </div>
      </section>

      {canSeeDebugPanel ? (
        <section className={shellCardClassName}>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 p-3">
              <ClipboardDocumentListIcon className="h-6 w-6 text-amber-200" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">DEBUG EXECUTION PANEL</h2>
              <p className="text-base text-slate-400">Panneau temporaire de verification post-build et post-seed.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-4">
            {[
              { title: "Last migrations executed", items: debugPanel?.last_migrations_executed ?? [] },
              { title: "Last seed executed", items: debugPanel?.last_seed_executed ?? [] },
              { title: "Last errors", items: debugPanel?.last_errors ?? [] },
              { title: "Modules created", items: debugPanel?.modules_created ?? [] },
            ].map((section) => (
              <div key={section.title} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <div className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-100">{section.title}</div>
                <div className="mt-4 space-y-3">
                  {section.items.length ? section.items.map((item) => (
                    <div key={`${section.title}:${item.label}:${item.value}`} className="rounded-2xl border border-white/10 bg-slate-900/70 px-3 py-3 text-sm text-slate-300">
                      <div className="font-semibold text-white">{item.label}</div>
                      <div className="mt-1 break-words">{item.value}</div>
                      {item.at ? <div className="mt-2 text-xs text-slate-500">{new Date(item.at).toLocaleString()}</div> : null}
                    </div>
                  )) : (
                    <div className="rounded-2xl border border-white/10 bg-slate-900/70 px-3 py-3 text-sm text-slate-500">Aucune donnee recente.</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
