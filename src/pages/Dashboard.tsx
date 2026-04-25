import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BanknotesIcon,
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
import {
  CorporatePanel,
  CorporatePageHeader,
  CorporateSectionHeader,
  CorporateStatCard,
  CorporateStatusBadge,
} from "../components/corporate/CorporateUI";
import { useAuth } from "../contexts/useAuth";
import { sessionHasRole } from "../rbac";
import { formatCount } from "../utils/format";

interface Employer {
  id: number;
  raison_sociale?: string;
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

  const { data: legalStatus } = useQuery({
    queryKey: ["dashboard", "legal-modules-status"],
    queryFn: async () => (await api.get<LegalModulesStatus>("/compliance/legal-modules-status")).data,
  });

  const { data: debugPanel } = useQuery({
    queryKey: ["dashboard", "debug-execution-panel"],
    enabled: canSeeDebugPanel,
    queryFn: async () => (await api.get<DebugExecutionPanel>("/system-update/debug-execution-panel")).data,
  });

  const totalWorkers = workersSummary?.total ?? 0;
  const modules: ModuleCard[] = [
    {
      title: "Employés",
      path: "/workers",
      description: "Dossiers salariés, documents, contrat actif et données de paie.",
      status: "Actif",
      icon: UserGroupIcon,
      metric: `${formatCount(totalWorkers)} dossier${totalWorkers > 1 ? "s" : ""}`,
    },
    {
      title: "Paie Madagascar",
      path: "/payroll",
      description: "Bulletins, variables, état de paie, exports et contrôle Ariary.",
      status: "Actif",
      icon: BanknotesIcon,
      metric: "IRSA, CNaPS, OSTIE, FMFP selon données existantes",
    },
    {
      title: "Recrutement",
      path: "/recruitment",
      description: "Fiches de poste, candidats et pipeline de sélection.",
      status: "Actif",
      icon: BriefcaseIcon,
      metric: `${formatCount(jobs.length)} poste${jobs.length > 1 ? "s" : ""}`,
    },
    {
      title: "Contrats",
      path: "/contracts",
      description: "Contrats, attestations et certificats prêts à imprimer.",
      status: "Actif",
      icon: ClipboardDocumentListIcon,
      metric: `${formatCount(contracts.length)} contrat${contracts.length > 1 ? "s" : ""}`,
    },
    {
      title: "Inspection du travail",
      path: "/inspection",
      description: "Dossiers, plaintes, échanges, conformité et pièces à examiner.",
      status: "Actif",
      icon: ShieldCheckIcon,
      metric: `${formatCount(legalStatus?.procedures_created ?? 0)} procédure${(legalStatus?.procedures_created ?? 0) > 1 ? "s" : ""}`,
    },
    {
      title: "Reporting",
      path: "/reporting",
      description: "Exports, contrôles croisés RH / paie et tableaux de suivi.",
      status: "Actif",
      icon: ChartBarIcon,
    },
  ];

  return (
    <div className="siirh-page">
      <CorporatePageHeader
        eyebrow="SIIRH Madagascar"
        title="Tableau de bord RH"
        subtitle="Vue opérationnelle connectée aux données backend : effectifs, paie, contrats, recrutement, conformité et reporting."
        actions={
          <>
            <Link to="/reporting" className="siirh-btn-secondary">Rapports</Link>
            <Link to="/workers" className="siirh-btn-primary">Nouvel employé</Link>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CorporateStatCard label="Effectif total" value={formatCount(totalWorkers)} hint="Dossiers travailleurs" icon={UserGroupIcon} tone="navy" />
        <CorporateStatCard label="Employeurs" value={formatCount(employers.length)} hint="Sociétés et établissements" icon={BuildingOfficeIcon} tone="emerald" />
        <CorporateStatCard label="Contrats" value={formatCount(contracts.length)} hint="Documents contractuels" icon={ClipboardDocumentListIcon} tone="blue" />
        <CorporateStatCard label="Conformité" value={formatCount(legalStatus?.modules_implemented ?? 0)} hint="Modules légaux activés" icon={ShieldCheckIcon} tone="amber" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.35fr_0.85fr]">
        <CorporatePanel>
          <CorporateSectionHeader
            title="Modules de production"
            subtitle="Accès directs aux parcours RH les plus utilisés."
            actions={<CorporateStatusBadge tone="success">Données réelles</CorporateStatusBadge>}
          />
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {modules.map((module) => {
              const Icon = module.icon;
              return (
                <Link key={module.path} to={module.path} className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-[#50C878] hover:shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#002147]/10 text-[#002147]">
                      <Icon className="h-5 w-5" />
                    </div>
                    <CorporateStatusBadge tone="success">{module.status}</CorporateStatusBadge>
                  </div>
                  <h3 className="mt-4 text-base font-extrabold text-[#07152f]">{module.title}</h3>
                  <p className="mt-2 min-h-12 text-sm font-medium leading-6 text-slate-600">{module.description}</p>
                  {module.metric ? <div className="mt-3 text-sm font-bold text-[#002147]">{module.metric}</div> : null}
                </Link>
              );
            })}
          </div>
        </CorporatePanel>

        <CorporatePanel>
          <CorporateSectionHeader
            title="Priorités du jour"
            subtitle="Actions utiles sans inventer de données métier."
          />
          <div className="mt-5 space-y-3">
            <Link to="/payroll" className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-[#07152f] hover:bg-white">
              <span>Contrôler la paie en Ariary</span>
              <CorporateStatusBadge tone="info">Paie</CorporateStatusBadge>
            </Link>
            <Link to="/workers" className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-[#07152f] hover:bg-white">
              <span>Vérifier les dossiers salariés</span>
              <CorporateStatusBadge tone="neutral">{formatCount(totalWorkers)}</CorporateStatusBadge>
            </Link>
            <Link to="/inspection" className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-[#07152f] hover:bg-white">
              <span>Suivre les dossiers inspection</span>
              <CorporateStatusBadge tone="warning">{formatCount(legalStatus?.procedures_created ?? 0)}</CorporateStatusBadge>
            </Link>
            <Link to="/reporting" className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-[#07152f] hover:bg-white">
              <span>Exporter les rapports</span>
              <CorporateStatusBadge tone="info">Excel / PDF</CorporateStatusBadge>
            </Link>
          </div>
        </CorporatePanel>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <CorporatePanel>
          <CorporateSectionHeader
            title="Conformité et inspection du travail"
            subtitle="Synthèse des workflows légaux exposés par le backend."
            actions={<Link to="/inspection" className="siirh-btn-secondary">Ouvrir l’inspection</Link>}
          />
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <CorporateStatCard label="Modules" value={formatCount(legalStatus?.modules_implemented ?? 0)} icon={Squares2X2Icon} tone="navy" />
            <CorporateStatCard label="Procédures" value={formatCount(legalStatus?.procedures_created ?? 0)} icon={ClipboardDocumentListIcon} tone="blue" />
            <CorporateStatCard label="PV générés" value={formatCount(legalStatus?.pv_generated ?? 0)} icon={ShieldCheckIcon} tone="emerald" />
            <CorporateStatCard label="Tests" value={formatCount(legalStatus?.test_cases ?? 0)} icon={ExclamationTriangleIcon} tone="amber" />
          </div>
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {(legalStatus?.employers ?? []).map((item) => (
              <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="font-extrabold text-[#07152f]">{item.raison_sociale}</div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm font-semibold text-slate-600">
                  <span>Salariés : {formatCount(item.workers)}</span>
                  <span>Dossiers : {formatCount(item.inspection_cases)}</span>
                  <span>PV : {formatCount(item.pv_generated)}</span>
                  <span>Ruptures : {formatCount(item.termination_workflows)}</span>
                </div>
              </div>
            ))}
          </div>
        </CorporatePanel>

        <CorporatePanel>
          <CorporateSectionHeader title="Couverture des rôles" subtitle="Profils disponibles pour les parcours de contrôle et de lecture." />
          <div className="mt-5 flex flex-wrap gap-2">
            {(legalStatus?.role_coverage ?? []).length ? (
              legalStatus?.role_coverage.map((item) => <CorporateStatusBadge key={item} tone="info">{item}</CorporateStatusBadge>)
            ) : (
              <CorporateStatusBadge tone="neutral">Aucune donnée de couverture exposée</CorporateStatusBadge>
            )}
          </div>
          <div className="mt-5 rounded-lg bg-[#002147] p-5 text-white">
            <h3 className="font-extrabold">Paie et RH Madagascar</h3>
            <p className="mt-2 text-sm font-medium leading-6 text-slate-200">
              L’interface conserve les calculs existants et expose les contrôles IRSA, CNaPS, OSTIE et FMFP uniquement quand les données backend sont disponibles.
            </p>
          </div>
        </CorporatePanel>
      </section>

      {canSeeDebugPanel ? (
        <CorporatePanel>
          <CorporateSectionHeader title="Panneau technique" subtitle="Contrôle post-build et post-seed réservé aux administrateurs." />
          <div className="mt-5 grid gap-4 xl:grid-cols-4">
            {[
              { title: "Migrations exécutées", items: debugPanel?.last_migrations_executed ?? [] },
              { title: "Seed exécuté", items: debugPanel?.last_seed_executed ?? [] },
              { title: "Erreurs", items: debugPanel?.last_errors ?? [] },
              { title: "Modules créés", items: debugPanel?.modules_created ?? [] },
            ].map((section) => (
              <div key={section.title} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-extrabold uppercase tracking-wide text-slate-600">{section.title}</div>
                <div className="mt-3 space-y-2">
                  {section.items.length ? section.items.map((item) => (
                    <div key={`${section.title}:${item.label}:${item.value}`} className="rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-700">
                      <div className="font-bold text-[#07152f]">{item.label}</div>
                      <div className="break-words">{item.value}</div>
                    </div>
                  )) : <div className="text-sm font-medium text-slate-500">Aucune donnée récente.</div>}
                </div>
              </div>
            ))}
          </div>
        </CorporatePanel>
      ) : null}
    </div>
  );
}
