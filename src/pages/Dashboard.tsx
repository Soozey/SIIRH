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


interface Employer {
  id: number;
}

interface WorkerPagination {
  total: number;
}

interface JobPosting {
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

const shellCardClassName =
  "rounded-[2rem] border border-white/10 bg-slate-950/50 p-6 shadow-2xl shadow-slate-950/30 backdrop-blur";


export default function Dashboard() {
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

  const { data: trainings = [] } = useQuery({
    queryKey: ["dashboard", "talent-trainings"],
    queryFn: async () => (await api.get<Training[]>("/talents/trainings")).data,
  });

  const { data: incidents = [] } = useQuery({
    queryKey: ["dashboard", "sst-incidents"],
    queryFn: async () => (await api.get<Incident[]>("/sst/incidents")).data,
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
      metric: `${workersSummary?.total ?? 0} dossiers salaries`,
    },
    {
      title: "Employeurs",
      path: "/employers",
      description: "Base employeurs, etablissements et parametres RH / paie.",
      status: "Actif",
      icon: BuildingOfficeIcon,
      metric: `${employers.length} employeurs`,
    },
    {
      title: "Talents",
      path: "/talents",
      description: "Competences, affectations et plan de formation.",
      status: "Actif",
      icon: AcademicCapIcon,
      metric: `${trainings.length} formations`,
    },
    {
      title: "SST / AT-MP",
      path: "/sst",
      description: "Incidents, accidents, mesures prises et suivi de traitement.",
      status: "Actif",
      icon: ShieldCheckIcon,
      metric: `${incidents.length} incidents`,
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
  ];

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/20 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(37,99,235,0.88),rgba(14,116,144,0.9))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              SIIRH / SIHMADA
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Plateforme RH, paie et conformite
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-cyan-50/90">
              Les modules prioritaires du cahier des charges sont exposes depuis
              l&apos;accueil: recrutement, contrats, structure, talents, SST,
              declarations, paie et reporting.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Employeurs</div>
              <div className="mt-3 text-3xl font-semibold text-white">{employers.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Salaries</div>
              <div className="mt-3 text-3xl font-semibold text-white">{workersSummary?.total ?? 0}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Postes</div>
              <div className="mt-3 text-3xl font-semibold text-white">{jobs.length}</div>
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
              <p className="text-sm text-slate-400">
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
                  className="group rounded-[1.75rem] border border-white/10 bg-white/5 p-5 transition hover:-translate-y-0.5 hover:border-cyan-300/40 hover:bg-cyan-400/8"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-3">
                      <Icon className="h-6 w-6 text-cyan-300" />
                    </div>
                    <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
                      {module.status}
                    </span>
                  </div>

                  <div className="mt-5">
                    <h3 className="text-lg font-semibold text-white">{module.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{module.description}</p>
                    {module.metric ? (
                      <div className="mt-4 text-sm font-medium text-cyan-200">{module.metric}</div>
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
                <h2 className="text-xl font-semibold text-white">Parcours RH exposes</h2>
                <p className="text-sm text-slate-400">Visibilite immediate cote demo.</p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-5 py-4">
                <div className="text-sm font-semibold text-white">Administration du personnel</div>
                <div className="mt-2 text-sm text-slate-400">
                  Employeurs, travailleurs, contrats et structure organisationnelle.
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-5 py-4">
                <div className="text-sm font-semibold text-white">Cycle RH et talents</div>
                <div className="mt-2 text-sm text-slate-400">
                  Recrutement, competences, formation, SST et suivi documentaire.
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-5 py-4">
                <div className="text-sm font-semibold text-white">Paie et conformite</div>
                <div className="mt-2 text-sm text-slate-400">
                  Paie preservee, declarations et reporting exposes sans toucher au moteur.
                </div>
              </div>
            </div>
          </section>

          <section className={shellCardClassName}>
            <h2 className="text-xl font-semibold text-white">Acces rapide</h2>
            <div className="mt-5 grid gap-3">
              <Link
                to="/workers"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white"
              >
                Ouvrir les dossiers salaries
              </Link>
              <Link
                to="/payroll"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white"
              >
                Ouvrir la paie
              </Link>
              <Link
                to="/reporting"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:text-white"
              >
                Ouvrir le reporting
              </Link>
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}
