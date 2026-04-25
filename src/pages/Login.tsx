import { FormEvent, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  CheckCircleIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

import {
  getPublicRegistrationConfig,
  listPublicDemoAccounts,
  listPublicRoleCatalog,
  registerPublicUser,
  type PublicDemoAccount,
  type PublicRegistrationConfig,
  type RoleCatalogPublicItem,
} from "../api";
import { useAuth } from "../contexts/useAuth";
import { useToast } from "../components/ui/useToast";

const DEFAULT_DEMO_ACCOUNTS: PublicDemoAccount[] = [];

const DEMO_LOGIN_PASSWORD = "Siirh2026";

type CatalogStatus = "loading" | "live" | "fallback";

type RoleInsight = {
  title: string;
  aliases: string[];
  accesses: string[];
  accent: string;
};

const ROLE_INSIGHTS: RoleInsight[] = [
  {
    title: "Administrateur système",
    aliases: ["admin"],
    accesses: ["IAM", "Paramètres", "Journalisation"],
    accent: "border-slate-400/35 bg-slate-400/10 text-slate-100",
  },
  {
    title: "Administrateur employeur",
    aliases: ["employer_admin", "employeur"],
    accesses: ["Dossiers", "Messagerie", "Travailleurs"],
    accent: "border-cyan-400/35 bg-cyan-400/10 text-cyan-100",
  },
  {
    title: "Responsable RH",
    aliases: ["hr_manager", "drh", "rh"],
    accesses: ["Travailleurs", "Contrats", "Dossiers"],
    accent: "border-emerald-400/35 bg-emerald-400/10 text-emerald-100",
  },
  {
    title: "Chargé RH",
    aliases: ["hr_officer", "assistante_rh", "rh"],
    accesses: ["Travailleurs", "Organisation", "Messagerie"],
    accent: "border-blue-400/35 bg-blue-400/10 text-blue-100",
  },
  {
    title: "Employé",
    aliases: ["employee", "employe", "salarie_agent"],
    accesses: ["Doléances", "Messages", "Suivi"],
    accent: "border-fuchsia-400/35 bg-fuchsia-400/10 text-fuchsia-100",
  },
  {
    title: "Inspecteur du travail",
    aliases: ["labor_inspector", "inspecteur", "inspection_travail"],
    accesses: ["Inspection", "Conciliation", "PV"],
    accent: "border-rose-400/35 bg-rose-400/10 text-rose-100",
  },
  {
    title: "Inspecteur principal",
    aliases: ["labor_inspector_supervisor"],
    accesses: ["Inspection", "PV", "Pilotage"],
    accent: "border-rose-400/35 bg-rose-400/10 text-rose-100",
  },
  {
    title: "Délégué du personnel",
    aliases: ["staff_delegate"],
    accesses: ["Doléances", "Consultations", "Messages"],
    accent: "border-amber-400/35 bg-amber-400/10 text-amber-100",
  },
  {
    title: "Comité d’entreprise",
    aliases: ["works_council_member"],
    accesses: ["Consultations", "PV", "Registre"],
    accent: "border-violet-400/35 bg-violet-400/10 text-violet-100",
  },
  {
    title: "Juge",
    aliases: ["judge_readonly"],
    accesses: ["Lecture", "Dossiers", "PV"],
    accent: "border-slate-400/35 bg-slate-400/10 text-slate-100",
  },
  {
    title: "Greffier",
    aliases: ["court_clerk_readonly"],
    accesses: ["Pièces", "Classement", "PV"],
    accent: "border-slate-400/35 bg-slate-400/10 text-slate-100",
  },
  {
    title: "Auditeur",
    aliases: ["auditor_readonly", "audit"],
    accesses: ["Audit", "Reporting", "Conformité"],
    accent: "border-slate-400/35 bg-slate-400/10 text-slate-100",
  },
];

const FALLBACK_PUBLIC_ROLES: RoleCatalogPublicItem[] = [
  { code: "admin", label: "Administrateur système", scope: "global", base_role_code: "admin", is_active: true },
  { code: "employer_admin", label: "Administrateur employeur", scope: "company", base_role_code: "employeur", is_active: true },
  { code: "hr_manager", label: "Responsable RH", scope: "company", base_role_code: "rh", is_active: true },
  { code: "hr_officer", label: "Chargé RH", scope: "company", base_role_code: "rh", is_active: true },
  { code: "employee", label: "Employé", scope: "self", base_role_code: "employe", is_active: true },
  { code: "labor_inspector", label: "Inspecteur du travail", scope: "external", base_role_code: "inspecteur", is_active: true },
  { code: "labor_inspector_supervisor", label: "Inspecteur principal", scope: "external", base_role_code: "inspecteur", is_active: true },
  { code: "staff_delegate", label: "Délégué du personnel", scope: "company", base_role_code: "juridique", is_active: true },
  { code: "works_council_member", label: "Comité d’entreprise", scope: "company", base_role_code: "juridique", is_active: true },
  { code: "judge_readonly", label: "Juge", scope: "judicial", base_role_code: "judge_readonly", is_active: true },
  { code: "court_clerk_readonly", label: "Greffier", scope: "judicial", base_role_code: "court_clerk_readonly", is_active: true },
  { code: "auditor_readonly", label: "Auditeur", scope: "readonly", base_role_code: "auditor_readonly", is_active: true },
  { code: "inspecteur", label: "Inspecteur (alias actif)", scope: "external", base_role_code: "inspecteur", is_active: true },
];

function extractErrorDetail(error: unknown): string | null {
  if (typeof error !== "object" || error === null) return null;
  const response = (error as { response?: unknown }).response;
  if (typeof response !== "object" || response === null) return null;
  const data = (response as { data?: unknown }).data;
  if (typeof data !== "object" || data === null) return null;
  const detail = (data as { detail?: unknown }).detail;
  return typeof detail === "string" && detail.trim().length > 0 ? detail : null;
}

function normalizeToken(value?: string | null) {
  return (value || "").trim().toLowerCase();
}

function isTechnicalRole(item: RoleCatalogPublicItem) {
  const code = normalizeToken(item.code);
  const base = normalizeToken(item.base_role_code);
  const label = normalizeToken(item.label);
  return code.includes("admin") || code.includes("iam") || base === "admin" || label.includes("administrateur") || label.includes("iam");
}

function matchInsight(item: RoleCatalogPublicItem) {
  const code = normalizeToken(item.code);
  const base = normalizeToken(item.base_role_code);
  const label = normalizeToken(item.label);
  return ROLE_INSIGHTS.find((insight) => insight.aliases.some((alias) => [code, base, label].some((token) => token.includes(alias))));
}

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const toast = useToast();

  const [username, setUsername] = useState("admin@siirh.com");
  const [password, setPassword] = useState(DEMO_LOGIN_PASSWORD);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [demoAccounts, setDemoAccounts] = useState<PublicDemoAccount[]>(DEFAULT_DEMO_ACCOUNTS);
  const [demoAccountsStatus, setDemoAccountsStatus] = useState<CatalogStatus>("loading");
  const [registrationConfig, setRegistrationConfig] = useState<PublicRegistrationConfig | null>(null);
  const [registrationStatus, setRegistrationStatus] = useState<CatalogStatus>("loading");
  const [registrationLoading, setRegistrationLoading] = useState(false);
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerPasswordConfirm, setRegisterPasswordConfirm] = useState("");
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [registerFullName, setRegisterFullName] = useState("");
  const [registerWorkerMatricule, setRegisterWorkerMatricule] = useState("");
  const [registerRoleCode, setRegisterRoleCode] = useState("salarie_agent");
  const [selectedRoleCode, setSelectedRoleCode] = useState<string | null>(null);
  const [publicRoles, setPublicRoles] = useState<RoleCatalogPublicItem[]>([]);
  const [publicRolesStatus, setPublicRolesStatus] = useState<CatalogStatus>("loading");
  const [publicRolesError, setPublicRolesError] = useState<string | null>(null);

  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/";

  useEffect(() => {
    let cancelled = false;

    const loadRoleCatalog = async () => {
      setPublicRolesStatus("loading");
      setPublicRolesError(null);
      try {
        const rows = await listPublicRoleCatalog();
        if (cancelled) return;
        const sortedRows = [...rows].sort((a, b) => a.label.localeCompare(b.label, "fr", { sensitivity: "base" }));
        if (sortedRows.length === 0) {
          setPublicRoles(FALLBACK_PUBLIC_ROLES);
          setPublicRolesStatus("fallback");
          setPublicRolesError("Catalogue local utilise en attendant des roles publies.");
          return;
        }
        setPublicRoles(sortedRows);
        setPublicRolesStatus("live");
      } catch (error: unknown) {
        if (cancelled) return;
        setPublicRoles(FALLBACK_PUBLIC_ROLES);
        setPublicRolesStatus("fallback");
        setPublicRolesError(extractErrorDetail(error) ?? "Catalogue local utilise provisoirement.");
      }
    };

    const loadDemoAccounts = async () => {
      setDemoAccountsStatus("loading");
      try {
        const rows = await listPublicDemoAccounts();
        if (cancelled) return;
        setDemoAccounts(rows.length ? rows : DEFAULT_DEMO_ACCOUNTS);
        setDemoAccountsStatus(rows.length ? "live" : "fallback");
      } catch {
        if (cancelled) return;
        setDemoAccounts(DEFAULT_DEMO_ACCOUNTS);
        setDemoAccountsStatus("fallback");
      }
    };

    const loadRegistration = async () => {
      setRegistrationStatus("loading");
      try {
        const config = await getPublicRegistrationConfig();
        if (cancelled) return;
        setRegistrationConfig(config);
        setRegistrationStatus("live");
        if (config.allowed_roles.length > 0) setRegisterRoleCode(config.allowed_roles[0].code);
      } catch {
        if (cancelled) return;
        setRegistrationConfig({
          enabled: true,
          password_policy: "Min 8 caracteres, avec majuscule, minuscule et chiffre.",
          allowed_roles: [{ code: "salarie_agent", label: "Salarie / Agent", scope: "self" }],
        });
        setRegistrationStatus("fallback");
      }
    };

    void loadRoleCatalog();
    void loadDemoAccounts();
    void loadRegistration();

    return () => {
      cancelled = true;
    };
  }, []);

  const roleCatalog = useMemo(() => (publicRoles.length ? publicRoles : FALLBACK_PUBLIC_ROLES), [publicRoles]);
  const businessRoleCatalog = useMemo(() => roleCatalog.filter((item) => !isTechnicalRole(item)), [roleCatalog]);
  const technicalRoleCatalog = useMemo(() => roleCatalog.filter((item) => isTechnicalRole(item)), [roleCatalog]);

  const featuredRoles = useMemo(
    () =>
      ROLE_INSIGHTS.map((insight) => {
        const catalogRole =
          roleCatalog.find((item) => insight.aliases.some((alias) => normalizeToken(item.code) === alias || normalizeToken(item.base_role_code) === alias)) ||
          roleCatalog.find((item) => matchInsight(item)?.title === insight.title);
        return {
          insight,
          role: catalogRole ?? {
            code: insight.aliases[0],
            label: insight.title,
            scope: "catalogue",
            base_role_code: insight.aliases[0],
            is_active: true,
          },
        };
      }).filter((item, index, array) => array.findIndex((candidate) => candidate.role.code === item.role.code) === index),
    [roleCatalog]
  );

  const selectedRole = useMemo(() => {
    if (!selectedRoleCode) return featuredRoles[0] ?? null;
    return (
      featuredRoles.find((item) => item.role.code === selectedRoleCode) ??
      featuredRoles.find((item) => normalizeToken(item.role.base_role_code) === normalizeToken(selectedRoleCode)) ??
      featuredRoles[0] ??
      null
    );
  }, [featuredRoles, selectedRoleCode]);

  const demoAccountsByRole = useMemo(() => {
    const rows = new Map<string, PublicDemoAccount>();
    for (const item of demoAccounts) rows.set(item.role_code.trim().toLowerCase(), item);
    return rows;
  }, [demoAccounts]);

  const resolveRoleLogin = (roleCode: string) => {
    const normalized = roleCode.trim().toLowerCase();
    const aliases = [normalized];
    if (normalized === "direction" || normalized === "dg_direction_generale") aliases.push("dg");
    if (normalized === "manager" || normalized === "validateur_n1") aliases.push("manager");
    if (normalized === "admin" || normalized === "super_administrateur_systeme") aliases.push("admin");
    if (normalized === "inspecteur" || normalized === "inspection_travail") aliases.push("labor_inspector", "inspecteur");
    if (normalized === "drh" || normalized === "rh") aliases.push("hr_manager", "hr_officer");
    if (normalized === "employeur") aliases.push("employer_admin");
    if (normalized === "employe" || normalized === "salarie_agent") aliases.push("employee");
    for (const key of aliases) {
      const found = demoAccountsByRole.get(key);
      if (found) return found;
    }
    return null;
  };

  const handleRoleClick = (role: RoleCatalogPublicItem) => {
    setSelectedRoleCode(role.code);
    const loginForRole = resolveRoleLogin(role.code);
    if (loginForRole) {
      setUsername(loginForRole.username);
      setPassword(DEMO_LOGIN_PASSWORD);
      toast.info("Rôle présélectionné", `Compte de test sélectionné pour ${loginForRole.label}.`);
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      toast.success("Connexion établie", "Session sécurisée ouverte.");
      navigate(redirectTo, { replace: true });
    } catch (error: unknown) {
      toast.error("Connexion refusee", extractErrorDetail(error) ?? "Identifiants invalides.");
    } finally {
      setLoading(false);
    }
  };

  const handlePublicRegister = async (event: FormEvent) => {
    event.preventDefault();
    if (registerPassword !== registerPasswordConfirm) {
      toast.error("Création refusée", "La confirmation du mot de passe ne correspond pas.");
      return;
    }
    setRegistrationLoading(true);
    try {
      const created = await registerPublicUser({
        username: registerEmail.trim().toLowerCase(),
        password: registerPassword,
        full_name: registerFullName.trim() || undefined,
        role_code: registerRoleCode,
        worker_matricule: registerWorkerMatricule.trim(),
      });
      toast.success("Compte créé", `Compte actif pour ${created.username}.`);
      setUsername(created.username);
      setPassword(registerPassword);
      setRegisterEmail("");
      setRegisterPassword("");
      setRegisterPasswordConfirm("");
      setRegisterFullName("");
      setRegisterWorkerMatricule("");
    } catch (error: unknown) {
      toast.error("Création impossible", extractErrorDetail(error) ?? "Erreur inattendue.");
    } finally {
      setRegistrationLoading(false);
    }
  };

  const statusBadge = useMemo(() => {
    if (publicRolesStatus === "live") {
      return {
        icon: CheckCircleIcon,
        label: "Catalogue synchronisé",
        className: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
      };
    }
    if (publicRolesStatus === "fallback") {
      return {
        icon: InformationCircleIcon,
        label: "Catalogue local",
        className: "border-amber-400/30 bg-amber-400/10 text-amber-100",
      };
    }
    return {
      icon: InformationCircleIcon,
      label: "Chargement",
      className: "border-slate-400/30 bg-slate-400/10 text-slate-100",
    };
  }, [publicRolesStatus]);

  const StatusIcon = statusBadge.icon;

  return (
    <div className="relative min-h-screen overflow-y-auto bg-[#050d19] text-slate-100 md:h-screen md:overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,197,94,0.12),_transparent_24%),radial-gradient(circle_at_bottom_right,_rgba(6,182,212,0.14),_transparent_20%),linear-gradient(135deg,_rgba(15,23,42,0.985),_rgba(8,47,73,0.94))]" />
      <div className="relative mx-auto min-h-screen max-w-[1480px] px-3 py-3 sm:px-4 md:h-screen md:min-h-0 md:px-4 md:py-3 lg:px-5">
        <div className="grid gap-3 md:h-full md:grid-cols-[minmax(0,1.58fr)_minmax(350px,1.02fr)] md:overflow-hidden">
          <section className="flex min-h-0 flex-col overflow-hidden rounded-[1.3rem] border border-white/10 bg-slate-950/78 p-2.5 shadow-2xl shadow-slate-950/40 backdrop-blur-xl lg:p-3">
            <div className="rounded-[1.1rem] border border-cyan-400/20 bg-cyan-400/10 px-3 py-2">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.26em] text-cyan-200">SIIRH accès sécurisé</div>
                  <h1 className="mt-1 text-[1.08rem] font-semibold text-white">Connexion et gestion de compte</h1>
                  <p className="mt-0.5 text-[12px] leading-4 text-slate-300">Accès à la plateforme et aux comptes autorisés.</p>
                </div>
                <div className="grid shrink-0 grid-cols-3 gap-1.5 text-center text-[11px]">
                  <div className="rounded-lg border border-white/10 bg-slate-950/45 px-2 py-1.5"><div className="text-slate-400">Rôles</div><div className="mt-0.5 font-semibold text-white">{businessRoleCatalog.length}</div></div>
                  <div className="rounded-lg border border-white/10 bg-slate-950/45 px-2 py-1.5"><div className="text-slate-400">Tests</div><div className="mt-0.5 font-semibold text-white">{demoAccounts.length}</div></div>
                  <div className="rounded-lg border border-white/10 bg-slate-950/45 px-2 py-1.5"><div className="text-slate-400">Inscription</div><div className="mt-0.5 font-semibold text-white">{registrationConfig?.enabled ? "Active" : "Contrôlée"}</div></div>
                </div>
              </div>
            </div>

            <div className="mt-2.5 grid min-h-0 flex-1 gap-2.5 md:grid-rows-[minmax(0,0.9fr)_minmax(0,1.05fr)_minmax(0,0.82fr)]">
              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 p-2.5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Connexion</div>
                <form onSubmit={handleSubmit} className="mt-2 grid gap-2">
                  <label className="block">
                    <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Email</span>
                    <input type="email" value={username} onChange={(event) => setUsername(event.target.value)} className="h-8.5 w-full rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="admin@siirh.com" autoComplete="username" required />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Mot de passe</span>
                    <div className="flex gap-2">
                      <input type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} className="h-8.5 w-full rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="Mot de passe" autoComplete="current-password" required />
                      <button
                        type="button"
                        onClick={() => setShowPassword((current) => !current)}
                        className="rounded-lg border border-slate-700 px-3 text-[12px] text-slate-200"
                      >
                        {showPassword ? "Masquer" : "Afficher"}
                      </button>
                    </div>
                  </label>
                  <button type="submit" disabled={loading} className="flex h-8.5 w-full items-center justify-center rounded-lg bg-cyan-400 px-4 text-[15px] font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300">{loading ? "Connexion..." : "Se connecter"}</button>
                </form>
              </div>

              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 p-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Création de compte</div>
                    <p className="mt-0.5 text-[12px] leading-4 text-slate-400">Matricule existant requis. {registrationConfig?.password_policy ?? ""}</p>
                  </div>
                  <div className={`rounded-full border px-2 py-1 text-[11px] font-medium ${registrationStatus === "live" ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100" : "border-slate-400/30 bg-slate-400/10 text-slate-100"}`}>{registrationStatus === "live" ? "Actif" : "Local"}</div>
                </div>
                <form onSubmit={handlePublicRegister} className="mt-2 grid gap-1.5 md:grid-cols-2">
                  <input type="email" value={registerEmail} onChange={(event) => setRegisterEmail(event.target.value)} className="h-8.5 rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="email de connexion" required />
                  <input type="text" value={registerWorkerMatricule} onChange={(event) => setRegisterWorkerMatricule(event.target.value)} className="h-8.5 rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="matricule existant" required />
                  <input type="text" value={registerFullName} onChange={(event) => setRegisterFullName(event.target.value)} className="h-8.5 rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="nom complet" />
                  <select value={registerRoleCode} onChange={(event) => setRegisterRoleCode(event.target.value)} className="h-8.5 rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20">{(registrationConfig?.allowed_roles ?? []).map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select>
                  <input type={showRegisterPassword ? "text" : "password"} value={registerPassword} onChange={(event) => setRegisterPassword(event.target.value)} className="h-8.5 rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="mot de passe" required />
                  <input type={showRegisterPassword ? "text" : "password"} value={registerPasswordConfirm} onChange={(event) => setRegisterPasswordConfirm(event.target.value)} className="h-8.5 rounded-lg border border-slate-800 bg-slate-900/85 px-3 text-[15px] text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20" placeholder="confirmation" required />
                  <button
                    type="button"
                    onClick={() => setShowRegisterPassword((current) => !current)}
                    className="rounded-lg border border-slate-700 px-3 text-[12px] text-slate-200 md:col-span-2"
                  >
                    {showRegisterPassword ? "Masquer les mots de passe" : "Afficher les mots de passe"}
                  </button>
                  <button type="submit" disabled={registrationLoading || !registrationConfig?.enabled} className="md:col-span-2 flex h-8.5 items-center justify-center rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-4 text-[15px] font-semibold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60">{registrationLoading ? "Création..." : "Créer un compte"}</button>
                </form>
              </div>

              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Comptes de test</div>
                    <p className="mt-0.5 text-[12px] text-slate-400">Sélection rapide du compte avec le mot de passe local de test prérempli.</p>
                  </div>
                  <div className={`rounded-full border px-2 py-1 text-[11px] font-medium ${demoAccountsStatus === "live" ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100" : "border-slate-400/30 bg-slate-400/10 text-slate-100"}`}>{demoAccountsStatus === "live" ? "Synchronisé" : "API indisponible"}</div>
                </div>
                <div className="mt-2 grid gap-1.5 md:grid-cols-2 xl:grid-cols-3">
                  {demoAccounts.map((item) => (
                    <button
                      key={`${item.role_code}:${item.username}`}
                      type="button"
                      onClick={() => {
                        setUsername(item.username);
                        setPassword(DEMO_LOGIN_PASSWORD);
                      }}
                      className="rounded-lg border border-slate-800 bg-slate-900/75 px-2.5 py-1.5 text-left transition hover:border-cyan-400/40 hover:bg-slate-900"
                    >
                      <div className="truncate text-[12px] font-semibold text-white">{item.label}</div>
                      <div className="mt-0.5 truncate text-[11px] text-cyan-200">{item.username}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="flex min-h-0 flex-col overflow-hidden rounded-[1.3rem] border border-white/10 bg-slate-950/82 p-2.5 shadow-2xl shadow-slate-950/40 backdrop-blur-xl lg:p-3">
            <div className="grid min-h-0 flex-1 gap-2.5 md:grid-rows-[minmax(0,0.18fr)_minmax(0,0.56fr)_minmax(0,0.22fr)]">
              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Accès selon votre profil</div>
                    <p className="mt-0.5 text-[12px] leading-4 text-slate-400">Vue synthétique des rôles disponibles.</p>
                  </div>
                  <div className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] font-medium ${statusBadge.className}`}>
                    <StatusIcon className="h-3.5 w-3.5" />
                    {statusBadge.label}
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-1.5 text-[11px]">
                  <div className="rounded-lg border border-white/10 bg-slate-950/45 px-2 py-1.5"><div className="text-slate-400">Rôles métier</div><div className="mt-0.5 font-semibold text-white">{businessRoleCatalog.length}</div></div>
                  <div className="rounded-lg border border-white/10 bg-slate-950/45 px-2 py-1.5"><div className="text-slate-400">Techniques</div><div className="mt-0.5 font-semibold text-white">{technicalRoleCatalog.length}</div></div>
                  <div className="rounded-lg border border-white/10 bg-slate-950/45 px-2 py-1.5"><div className="text-slate-400">Statut</div><div className="mt-0.5 font-semibold text-white">{publicRolesStatus === "live" ? "Serveur" : publicRolesStatus === "fallback" ? "Local" : "Chargement"}</div></div>
                </div>
                {publicRolesError ? <div className="mt-1.5 text-[11px] text-slate-500">Source locale active temporairement.</div> : null}
              </div>

              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 px-2.5 py-2.5">
                <div className="flex items-center justify-between gap-2 px-1">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Rôles principaux</div>
                  <div className="text-[11px] text-slate-500">Accès métier</div>
                </div>
                <div className="mt-2 grid min-h-0 gap-1.5 overflow-y-auto pr-1">
                  {featuredRoles.map(({ insight, role }) => {
                    const isSelected = selectedRole?.role.code === role.code;
                    return (
                      <button
                        key={`${insight.title}:${role.code}`}
                        type="button"
                        onClick={() => handleRoleClick(role)}
                        className={`rounded-lg border px-2.5 py-2 text-left transition ${isSelected ? insight.accent : "border-slate-800 bg-slate-900/72 text-slate-200 hover:border-cyan-400/40 hover:bg-slate-900"}`}
                      >
                        <div className="grid gap-1 md:grid-cols-[minmax(110px,0.7fr)_minmax(0,1.35fr)_auto] md:items-center">
                          <div className="truncate text-[12px] font-semibold text-white">{insight.title}</div>
                          <div className="min-w-0">
                            <div className="mt-1 flex flex-wrap gap-1">
                              {insight.accesses.map((access) => (
                                <span key={`${role.code}:${access}`} className="rounded-full border border-white/10 bg-slate-950/55 px-1.5 py-0.5 text-[10px] font-medium text-slate-200">{access}</span>
                              ))}
                            </div>
                          </div>
                          <div className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${role.is_active ? "bg-emerald-400/15 text-emerald-100" : "bg-slate-700/50 text-slate-200"}`}>{role.is_active ? "actif" : "disponible"}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 px-3 py-2.5">
                {selectedRole ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="inline-flex items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[12px] font-semibold text-white">
                      <ShieldCheckIcon className="h-3.5 w-3.5 text-cyan-200" />
                      {selectedRole.insight.title}
                    </div>
                    {selectedRole.insight.accesses.map((access) => (
                      <span key={`selected:${access}`} className="rounded-full border border-white/10 bg-slate-950/55 px-2 py-1 text-[11px] font-medium text-slate-200">
                        {access}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
