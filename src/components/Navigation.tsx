import { useState } from "react";
import type { ComponentType } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  AcademicCapIcon,
  BookOpenIcon,
  ArrowDownTrayIcon,
  Bars3Icon,
  BriefcaseIcon,
  BuildingOfficeIcon,
  CalendarIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  HomeIcon,
  IdentificationIcon,
  PowerIcon,
  ShieldCheckIcon,
  Squares2X2Icon,
  UserGroupIcon,
  XMarkIcon,
  SunIcon,
  MoonIcon,
} from "@heroicons/react/24/outline";

import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { hasModulePermission, sessionHasRole } from "../rbac";
import type { AppModule } from "../rbac";

interface NavItem {
  path: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  module?: AppModule;
  action?: "read" | "write" | "admin";
}

const navItems: NavItem[] = [
  { path: "/", label: "Accueil", icon: HomeIcon },
  { path: "/recruitment", label: "Recrutement", icon: BriefcaseIcon, module: "recruitment" },
  { path: "/recruitment/settings", label: "Parametres recrutement", icon: BriefcaseIcon, module: "recruitment" },
  { path: "/contracts", label: "Contrats", icon: ClipboardDocumentListIcon, module: "contracts" },
  { path: "/employers", label: "Employeurs", icon: BuildingOfficeIcon, module: "workforce" },
  { path: "/workers", label: "Travailleurs", icon: UserGroupIcon, module: "workforce" },
  { path: "/organization", label: "Organisation", icon: Squares2X2Icon, module: "organization" },
  { path: "/payroll", label: "Paie", icon: ClipboardDocumentListIcon, module: "payroll" },
  { path: "/primes", label: "Primes", icon: ClipboardDocumentListIcon, module: "payroll" },
  { path: "/hs", label: "Temps (Heures)", icon: ClockIcon, module: "time_absence" },
  { path: "/absences", label: "Absences", icon: CalendarIcon, module: "time_absence" },
  { path: "/leaves", label: "Conges", icon: CalendarIcon, module: "time_absence" },
  { path: "/declarations", label: "Declarations", icon: ExclamationTriangleIcon, module: "declarations" },
  { path: "/inspection", label: "Inspection", icon: ShieldCheckIcon, module: "compliance" },
  { path: "/messages", label: "Messages", icon: ChatBubbleLeftRightIcon, module: "messages" },
  { path: "/employee-portal", label: "Portail employe", icon: IdentificationIcon, module: "employee_portal" },
  { path: "/employee-360", label: "Dossier permanent RH", icon: IdentificationIcon, module: "workforce" },
  { path: "/people-ops", label: "People Ops RH", icon: BriefcaseIcon, module: "people_ops" },
  { path: "/talents", label: "Talents & Formation", icon: AcademicCapIcon, module: "talents" },
  { path: "/sst", label: "SST", icon: ShieldCheckIcon, module: "sst" },
  { path: "/reporting", label: "Reporting", icon: ChartBarIcon, module: "reporting" },
  { path: "/help", label: "Aide / Mode d'emploi", icon: BookOpenIcon },
  { path: "/data-transfer", label: "Import / Export", icon: ArrowDownTrayIcon, module: "master_data", action: "admin" },
];

export default function Navigation() {
  const location = useLocation();
  const { session, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isInspector = session?.effective_role_code === "inspecteur" || session?.role_code === "inspecteur";
  const canManageRecruitmentSettings = sessionHasRole(session, ["admin", "rh", "recrutement"]);

  const resolvedNavItems = navItems.map((item) => {
    if (item.path === "/messages" && isInspector) {
      return { ...item, label: "Plaintes / Messages" };
    }
    if (item.path === "/employee-portal" && isInspector) {
      return { ...item, label: "Portail salarie" };
    }
    return item;
  });

  const isActive = (path: string) => {
    if (path === "/") {
      return location.pathname === "/";
    }
    return location.pathname.startsWith(path);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-[70] rounded-xl border border-slate-700 bg-slate-900/95 p-3 text-slate-100 shadow-xl md:hidden"
      >
        <Bars3Icon className="h-6 w-6" />
      </button>

      <div
        className={`fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm transition-opacity md:hidden ${mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setMobileOpen(false)}
      />

      <aside
        className={`layout-sidebar fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden border-r border-slate-700/60 bg-slate-900/95 p-5 shadow-2xl shadow-slate-950/50 backdrop-blur-xl transition-transform md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-200">
              SIIRH
            </div>
            <div className="mt-4 text-2xl font-semibold text-white">Pilotage RH</div>
            <div className="mt-2 text-sm text-slate-400">
              Recrutement, contrats, paie, talents, SST, reporting.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="rounded-xl border border-white/10 p-2 text-slate-400 md:hidden"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="mb-4 flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-700/70 bg-slate-800/80 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:bg-slate-800"
          >
            {theme === "dark" ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
            {theme === "dark" ? "Mode clair" : "Mode sombre"}
          </button>
          <Link
            to="/help"
            onClick={() => setMobileOpen(false)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-sky-400/20 bg-sky-400/10 text-sky-200 transition hover:bg-sky-400/20"
            aria-label="Ouvrir l'aide"
          >
            <BookOpenIcon className="h-5 w-5" />
          </Link>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto pr-1">
          {resolvedNavItems
            .filter((item) => {
              if (isInspector && item.path === "/employee-portal") return false;
              if (item.path === "/recruitment/settings" && !canManageRecruitmentSettings) return false;
              if (!item.module) return true;
              return hasModulePermission(session, item.module, item.action ?? "read");
            })
            .map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  className={`group flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-medium transition ${
                    active
                      ? "bg-sky-500 text-white shadow-lg shadow-sky-900/30"
                      : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                  }`}
                >
                  <Icon className={`h-5 w-5 ${active ? "text-white" : "text-slate-500 group-hover:text-sky-300"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
        </nav>

        <div className="mt-6 rounded-2xl border border-slate-700/70 bg-slate-800/70 p-4">
          <div className="text-[12px] font-semibold uppercase tracking-[0.24em] text-slate-500">Session</div>
          <div className="mt-3 text-[15px] font-semibold text-white">{session?.full_name || session?.username}</div>
          <div className="mt-1 text-[12px] uppercase tracking-[0.2em] text-sky-300">
            {session?.effective_role_code || session?.role_code}
          </div>
          {session?.username ? (
            <div className="mt-4 text-[13px] leading-5 text-slate-400">
              Utilisateur: <span className="font-medium text-slate-200">{session.username}</span>
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => logout()}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-600 bg-slate-900/70 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-rose-400/30 hover:bg-rose-500/10 hover:text-rose-100"
          >
            <PowerIcon className="h-4 w-4" />
            Fermer la session
          </button>
        </div>
      </aside>
    </>
  );
}
