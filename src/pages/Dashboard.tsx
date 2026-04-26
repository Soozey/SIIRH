import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BanknotesIcon,
  BriefcaseIcon,
  BuildingOfficeIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  IdentificationIcon,
  ShieldCheckIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";

import { api, type AuthSession } from "../api";
import {
  CorporateEmptyState,
  CorporatePanel,
  CorporatePageHeader,
  CorporateSectionHeader,
  CorporateStatCard,
  CorporateStatusBadge,
} from "../components/corporate/CorporateUI";
import { useAuth } from "../contexts/useAuth";
import { hasModulePermission, sessionHasRole } from "../rbac";
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
  role_coverage: string[];
}

interface DebugExecutionItem {
  label: string;
  value: string;
}

interface DebugExecutionPanel {
  last_migrations_executed: DebugExecutionItem[];
  last_seed_executed: DebugExecutionItem[];
  last_errors: DebugExecutionItem[];
  modules_created: DebugExecutionItem[];
}

interface PortalDashboard {
  worker?: Record<string, unknown>;
  requests: Array<{ id: number; title: string; status: string; case_number?: string | null }>;
  inspector_cases: Array<{ id: number; subject: string; status: string; case_number: string }>;
  contracts: Array<{ id: number; title: string }>;
  notifications: Array<{ type: string; label: string; status: string; case_number?: string }>;
}

interface WorkerFlow {
  worker?: Record<string, unknown>;
  contract?: Record<string, unknown>;
  integrity_issues: Array<{ severity: string; message: string }>;
}

interface MessagesDashboard {
  channels_count?: number;
  unread_count?: number;
  recent_messages?: Array<{ id: number; body?: string; created_at?: string }>;
}

interface InspectorCase {
  id: number;
  case_number: string;
  subject: string;
  status: string;
  current_stage: string;
}

type ModuleCard = {
  title: string;
  path: string;
  description: string;
  status: string;
  icon: ComponentType<{ className?: string }>;
  metric?: string;
};

const employeeRoles = ["employe", "employee", "salarie_agent", "agent"];
const inspectorRoles = ["inspecteur", "inspection_travail", "labor_inspector", "labor_inspector_supervisor"];
const employerRoles = ["employeur", "employer_admin", "admin_employeur", "entreprise_cliente_portage_salarial"];
const rhRoles = ["admin", "system_admin", "rh", "drh", "hr_manager", "responsable_rh_gestionnaire_rh"];

function getText(value: unknown, fallback = "-") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function PortalCard({ to, title, text, icon: Icon }: { to: string; title: string; text: string; icon: ComponentType<{ className?: string }> }) {
  return (
    <Link to={to} className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-[#50C878] hover:shadow-sm">
      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#002147]/10 text-[#002147]">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="mt-4 text-base font-extrabold text-[#07152f]">{title}</h3>
      <p className="mt-2 text-sm font-semibold leading-6 text-slate-700">{text}</p>
    </Link>
  );
}

function EmployeeDashboard({ session }: { session: AuthSession }) {
  const workerId = session.worker_id ?? null;
  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ["dashboard", "employee-portal", workerId],
    enabled: workerId !== null,
    queryFn: async () => (await api.get<PortalDashboard>("/employee-portal/dashboard", { params: { worker_id: workerId } })).data,
  });
  const { data: flow } = useQuery({
    queryKey: ["dashboard", "employee-flow", workerId],
    enabled: workerId !== null,
    queryFn: async () => (await api.get<WorkerFlow>(`/employee-portal/worker-flow/${workerId}`)).data,
  });
  const { data: messagesDashboard } = useQuery({
    queryKey: ["dashboard", "employee-messages", session.employer_id],
    enabled: hasModulePermission(session, "messages"),
    queryFn: async () => (await api.get<MessagesDashboard>("/messages/dashboard", { params: { employer_id: session.employer_id ?? undefined } })).data,
  });

  const worker = dashboard?.worker ?? flow?.worker ?? {};
  const contract = flow?.contract ?? {};
  const displayName = session.full_name || `${getText(worker.prenom, "")} ${getText(worker.nom, "")}`.trim() || session.username;

  return (
    <div className="siirh-page">
      <CorporatePageHeader
        eyebrow="Portail personnel"
        title={`Bonjour ${displayName}`}
        subtitle="Vos données personnelles, demandes, documents et échanges. Les données affichées sont limitées à votre compte et à votre dossier salarié."
        actions={<Link to="/employee-portal" className="siirh-btn-primary">Ouvrir mon espace</Link>}
      />

      {!workerId ? (
        <CorporateEmptyState
          title="Aucun dossier salarié lié"
          description="Votre compte existe, mais aucun worker_id n'est associé. Contactez RH pour rattacher le compte à votre dossier."
        />
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <CorporateStatCard label="Statut compte" value={session.account_status || "Actif"} hint={session.must_change_password ? "Mot de passe à changer" : "Compte opérationnel"} icon={IdentificationIcon} tone={session.must_change_password ? "amber" : "emerald"} />
            <CorporateStatCard label="Demandes" value={formatCount(dashboard?.requests.length ?? 0)} hint="Demandes personnelles" icon={ClipboardDocumentListIcon} tone="blue" />
            <CorporateStatCard label="Contrats" value={formatCount(dashboard?.contracts.length ?? 0)} hint={getText(contract.title, "Contrat actif si disponible")} icon={DocumentTextIcon} tone="navy" />
            <CorporateStatCard label="Messages" value={formatCount(messagesDashboard?.unread_count ?? 0)} hint="Messages non lus" icon={ChatBubbleLeftRightIcon} tone="emerald" />
          </section>

          <section className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
            <CorporatePanel>
              <CorporateSectionHeader title="Mon dossier" subtitle="Informations exposées par les API employé et dossier RH." />
              {dashboardLoading ? (
                <div className="mt-5 text-sm font-semibold text-slate-700">Chargement du dossier...</div>
              ) : (
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="text-xs font-bold uppercase tracking-wide text-slate-600">Poste</div>
                    <div className="mt-2 font-extrabold text-[#07152f]">{getText(worker.poste)}</div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="text-xs font-bold uppercase tracking-wide text-slate-600">Matricule</div>
                    <div className="mt-2 font-extrabold text-[#07152f]">{getText(worker.matricule)}</div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="text-xs font-bold uppercase tracking-wide text-slate-600">Département / service</div>
                    <div className="mt-2 font-extrabold text-[#07152f]">{getText(worker.departement)} / {getText(worker.service)}</div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="text-xs font-bold uppercase tracking-wide text-slate-600">Employeur</div>
                    <div className="mt-2 font-extrabold text-[#07152f]">{getText(worker.employer_name ?? worker.raison_sociale)}</div>
                  </div>
                </div>
              )}
            </CorporatePanel>

            <CorporatePanel>
              <CorporateSectionHeader title="Actions autorisées" subtitle="Accès personnel, sans modules RH globaux." />
              <div className="mt-5 grid gap-3">
                <PortalCard to="/employee-portal" title="Mon portail" text="Demandes, doléances, messages et suivi personnel." icon={IdentificationIcon} />
                <PortalCard to="/leaves" title="Mes congés" text="Solde, demandes et historique si le module est disponible." icon={ClipboardDocumentListIcon} />
                <PortalCard to="/messages" title="Messages" text="Échanges autorisés avec RH, employeur ou inspection." icon={ChatBubbleLeftRightIcon} />
              </div>
            </CorporatePanel>
          </section>
        </>
      )}
    </div>
  );
}

function InspectorDashboard({ session }: { session: AuthSession }) {
  const { data: cases = [] } = useQuery({
    queryKey: ["dashboard", "inspection-cases", session.employer_id],
    queryFn: async () => (await api.get<InspectorCase[]>("/employee-portal/inspection-cases", { params: { employer_id: session.employer_id ?? undefined } })).data,
  });
  const pending = cases.filter((item) => !["closed", "CLOTURE", "RETIREE"].includes(item.status)).length;

  return (
    <div className="siirh-page">
      <CorporatePageHeader
        eyebrow="Inspection du travail"
        title="Portail inspection"
        subtitle="Dossiers, plaintes, messages et pièces du périmètre autorisé par le backend."
        actions={<Link to="/inspection" className="siirh-btn-primary">Ouvrir les dossiers</Link>}
      />
      <section className="grid gap-4 md:grid-cols-3">
        <CorporateStatCard label="Dossiers" value={formatCount(cases.length)} hint="Dossiers accessibles" icon={ShieldCheckIcon} tone="navy" />
        <CorporateStatCard label="En attente" value={formatCount(pending)} hint="Traitement ou instruction" icon={ExclamationTriangleIcon} tone="amber" />
        <CorporateStatCard label="Messages" value="API" hint="Via module messages / plaintes" icon={ChatBubbleLeftRightIcon} tone="blue" />
      </section>
      <CorporatePanel>
        <CorporateSectionHeader title="Dossiers récents" subtitle="Liste issue de l'API inspection/employee-portal." />
        <div className="mt-5 space-y-3">
          {cases.length ? cases.slice(0, 6).map((item) => (
            <Link key={item.id} to="/inspection" className="block rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-white">
              <div className="font-extrabold text-[#07152f]">{item.case_number} - {item.subject}</div>
              <div className="mt-2 text-sm font-semibold text-slate-700">{item.status} / {item.current_stage}</div>
            </Link>
          )) : <CorporateEmptyState title="Aucun dossier accessible" description="Aucun dossier inspection n'est exposé pour ce profil actuellement." />}
        </div>
      </CorporatePanel>
    </div>
  );
}

function EmployerDashboard({ session }: { session: AuthSession }) {
  const { data: workersSummary } = useQuery({
    queryKey: ["dashboard", "employer-workers", session.employer_id],
    enabled: session.employer_id !== null && session.employer_id !== undefined,
    queryFn: async () => (await api.get<WorkerPagination>("/workers/paginated", { params: { page: 1, page_size: 1, employer_id: session.employer_id } })).data,
  });

  return (
    <div className="siirh-page">
      <CorporatePageHeader
        eyebrow="Portail employeur"
        title="Tableau de bord employeur"
        subtitle="Données limitées à votre employeur et aux permissions retournées par le backend."
        actions={<Link to="/messages" className="siirh-btn-secondary">Messages</Link>}
      />
      <section className="grid gap-4 md:grid-cols-3">
        <CorporateStatCard label="Travailleurs" value={formatCount(workersSummary?.total ?? 0)} hint="Périmètre employeur" icon={UserGroupIcon} tone="navy" />
        <CorporateStatCard label="Contrats" value="API" hint="Contrats accessibles via /contracts" icon={ClipboardDocumentListIcon} tone="blue" />
        <CorporateStatCard label="Inspection" value="API" hint="Échanges et dossiers autorisés" icon={ShieldCheckIcon} tone="amber" />
      </section>
      <CorporatePanel>
        <CorporateSectionHeader title="Actions employeur" subtitle="Accès limités au périmètre autorisé." />
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <PortalCard to="/workers" title="Travailleurs" text="Consulter les travailleurs de votre périmètre." icon={UserGroupIcon} />
          <PortalCard to="/contracts" title="Contrats" text="Documents RH accessibles pour l'employeur." icon={ClipboardDocumentListIcon} />
          <PortalCard to="/messages" title="Messages" text="Échanges autorisés avec RH ou inspection." icon={ChatBubbleLeftRightIcon} />
        </div>
      </CorporatePanel>
    </div>
  );
}

function AdminRhDashboard({ session }: { session: AuthSession }) {
  const canSeeDebugPanel = sessionHasRole(session, ["admin", "system_admin", "super_administrateur_systeme"]);
  const canWriteWorkforce = hasModulePermission(session, "workforce", "write");
  const canReadReporting = hasModulePermission(session, "reporting");

  const { data: employers = [] } = useQuery({
    queryKey: ["dashboard", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });
  const { data: workersSummary } = useQuery({
    queryKey: ["dashboard", "workers"],
    queryFn: async () => (await api.get<WorkerPagination>("/workers/paginated", { params: { page: 1, page_size: 1 } })).data,
  });
  const { data: jobs = [] } = useQuery({
    queryKey: ["dashboard", "recruitment-jobs"],
    enabled: hasModulePermission(session, "recruitment"),
    queryFn: async () => (await api.get<JobPosting[]>("/recruitment/jobs")).data,
  });
  const { data: contracts = [] } = useQuery({
    queryKey: ["dashboard", "contracts"],
    enabled: hasModulePermission(session, "contracts"),
    queryFn: async () => (await api.get<ContractSummary[]>("/custom-contracts")).data,
  });
  const { data: legalStatus } = useQuery({
    queryKey: ["dashboard", "legal-modules-status"],
    enabled: hasModulePermission(session, "compliance"),
    queryFn: async () => (await api.get<LegalModulesStatus>("/compliance/legal-modules-status")).data,
  });
  const { data: debugPanel } = useQuery({
    queryKey: ["dashboard", "debug-execution-panel"],
    enabled: canSeeDebugPanel,
    queryFn: async () => (await api.get<DebugExecutionPanel>("/system-update/debug-execution-panel")).data,
  });

  const totalWorkers = workersSummary?.total ?? 0;
  const modules: ModuleCard[] = [
    { title: "Employés", path: "/workers", description: "Dossiers salariés, documents et données RH.", status: "Actif", icon: UserGroupIcon, metric: `${formatCount(totalWorkers)} dossier${totalWorkers > 1 ? "s" : ""}` },
    { title: "Paie Madagascar", path: "/payroll", description: "Bulletins, variables, état de paie et exports.", status: "Actif", icon: BanknotesIcon, metric: "IRSA, CNaPS, OSTIE, FMFP" },
    { title: "Recrutement", path: "/recruitment", description: "Fiches de poste, candidats et pipeline.", status: "Actif", icon: BriefcaseIcon, metric: `${formatCount(jobs.length)} poste${jobs.length > 1 ? "s" : ""}` },
    { title: "Contrats", path: "/contracts", description: "Contrats, attestations et certificats.", status: "Actif", icon: ClipboardDocumentListIcon, metric: `${formatCount(contracts.length)} contrat${contracts.length > 1 ? "s" : ""}` },
    { title: "Inspection", path: "/inspection", description: "Dossiers, plaintes et conformité.", status: "Actif", icon: ShieldCheckIcon, metric: `${formatCount(legalStatus?.procedures_created ?? 0)} procédure${(legalStatus?.procedures_created ?? 0) > 1 ? "s" : ""}` },
    { title: "Reporting", path: "/reporting", description: "Exports et tableaux de suivi.", status: "Actif", icon: ChartBarIcon },
  ].filter((item) => {
    if (item.path === "/workers") return hasModulePermission(session, "workforce");
    if (item.path === "/payroll") return hasModulePermission(session, "payroll");
    if (item.path === "/recruitment") return hasModulePermission(session, "recruitment");
    if (item.path === "/contracts") return hasModulePermission(session, "contracts");
    if (item.path === "/inspection") return hasModulePermission(session, "compliance");
    if (item.path === "/reporting") return canReadReporting;
    return true;
  });

  return (
    <div className="siirh-page">
      <CorporatePageHeader
        eyebrow="SIIRH Madagascar"
        title="Tableau de bord RH"
        subtitle="Vue opérationnelle limitée aux permissions réelles du compte connecté."
        actions={
          <>
            {canReadReporting ? <Link to="/reporting" className="siirh-btn-secondary">Rapports</Link> : null}
            {canWriteWorkforce ? <Link to="/workers" className="siirh-btn-primary">Nouvel employé</Link> : null}
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {hasModulePermission(session, "workforce") ? <CorporateStatCard label="Effectif total" value={formatCount(totalWorkers)} hint="Dossiers travailleurs" icon={UserGroupIcon} tone="navy" /> : null}
        {hasModulePermission(session, "workforce") ? <CorporateStatCard label="Employeurs" value={formatCount(employers.length)} hint="Sociétés et établissements" icon={BuildingOfficeIcon} tone="emerald" /> : null}
        {hasModulePermission(session, "contracts") ? <CorporateStatCard label="Contrats" value={formatCount(contracts.length)} hint="Documents contractuels" icon={ClipboardDocumentListIcon} tone="blue" /> : null}
        {hasModulePermission(session, "compliance") ? <CorporateStatCard label="Conformité" value={formatCount(legalStatus?.modules_implemented ?? 0)} hint="Modules légaux activés" icon={ShieldCheckIcon} tone="amber" /> : null}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.35fr_0.85fr]">
        <CorporatePanel>
          <CorporateSectionHeader title="Modules autorisés" subtitle="Accès directs selon les permissions du backend." actions={<CorporateStatusBadge tone="success">Données réelles</CorporateStatusBadge>} />
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
          <CorporateSectionHeader title="Priorités du jour" subtitle="Actions connectées aux modules autorisés." />
          <div className="mt-5 space-y-3">
            {hasModulePermission(session, "payroll") ? <PortalCard to="/payroll" title="Contrôler la paie" text="Paie en Ariary et exports." icon={BanknotesIcon} /> : null}
            {hasModulePermission(session, "workforce") ? <PortalCard to="/workers" title="Dossiers salariés" text={`${formatCount(totalWorkers)} dossier(s) accessibles.`} icon={UserGroupIcon} /> : null}
            {hasModulePermission(session, "compliance") ? <PortalCard to="/inspection" title="Inspection" text={`${formatCount(legalStatus?.procedures_created ?? 0)} procédure(s).`} icon={ShieldCheckIcon} /> : null}
            {canReadReporting ? <PortalCard to="/reporting" title="Reporting" text="Exports et indicateurs autorisés." icon={ChartBarIcon} /> : null}
          </div>
        </CorporatePanel>
      </section>

      {canSeeDebugPanel ? (
        <CorporatePanel>
          <CorporateSectionHeader title="Panneau technique" subtitle="Réservé aux administrateurs." />
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

export default function Dashboard() {
  const { session } = useAuth();

  if (sessionHasRole(session, employeeRoles)) {
    return <EmployeeDashboard session={session as AuthSession} />;
  }
  if (sessionHasRole(session, inspectorRoles)) {
    return <InspectorDashboard session={session as AuthSession} />;
  }
  if (sessionHasRole(session, employerRoles) && !sessionHasRole(session, rhRoles)) {
    return <EmployerDashboard session={session as AuthSession} />;
  }
  return <AdminRhDashboard session={session as AuthSession} />;
}
