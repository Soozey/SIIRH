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

import { useAuth } from "../contexts/useAuth";
import { useTheme } from "../contexts/useTheme";
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
  { path: "/recruitment/settings", label: "Paramètres recrutement", icon: BriefcaseIcon, module: "recruitment" },
  { path: "/contracts", label: "Contrats", icon: ClipboardDocumentListIcon, module: "contracts" },
  { path: "/employers", label: "Employeurs", icon: BuildingOfficeIcon, module: "workforce" },
  { path: "/workers", label: "Travailleurs", icon: UserGroupIcon, module: "workforce" },
  { path: "/organization", label: "Organisation", icon: Squares2X2Icon, module: "organization" },
  { path: "/payroll", label: "Paie", icon: ClipboardDocumentListIcon, module: "payroll" },
  { path: "/primes", label: "Primes", icon: ClipboardDocumentListIcon, module: "payroll" },
  { path: "/hs", label: "Temps (Heures)", icon: ClockIcon, module: "time_absence" },
  { path: "/absences", label: "Absences", icon: CalendarIcon, module: "time_absence" },
  { path: "/leaves", label: "Congés", icon: CalendarIcon, module: "time_absence" },
  { path: "/declarations", label: "Déclarations", icon: ExclamationTriangleIcon, module: "declarations" },
  { path: "/inspection", label: "Inspection", icon: ShieldCheckIcon, module: "compliance" },
  { path: "/messages", label: "Messages", icon: ChatBubbleLeftRightIcon, module: "messages" },
  { path: "/employee-portal", label: "Portail employé", icon: IdentificationIcon, module: "employee_portal" },
  { path: "/employee-360", label: "Dossier permanent RH", icon: IdentificationIcon, module: "workforce" },
  { path: "/people-ops", label: "People Ops RH", icon: BriefcaseIcon, module: "people_ops" },
  { path: "/talents", label: "Talents & Formation", icon: AcademicCapIcon, module: "talents" },
  { path: "/sst", label: "SST", icon: ShieldCheckIcon, module: "sst" },
  { path: "/reporting", label: "Reporting", icon: ChartBarIcon, module: "reporting" },
  { path: "/help", label: "Aide / Mode d’emploi", icon: BookOpenIcon },
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
        className="fixed left-4 top-4 z-[70] rounded-md border border-slate-700 bg-[#002147] p-3 text-white shadow-xl md:hidden"
      >
        <Bars3Icon className="h-6 w-6" />
      </button>

      <div
        className={`fixed inset-0 z-40 bg-slate-950/60 transition-opacity md:hidden ${mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setMobileOpen(false)}
      />

      <aside
        className={`layout-sidebar fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden border-r border-[#123b68] bg-[#002147] p-5 text-white shadow-xl transition-transform md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <div className="text-2xl font-extrabold tracking-tight text-white">RH Madagascar</div>
            <div className="mt-1 text-xs font-semibold uppercase tracking-[0.25em] text-slate-300">
              Portail administratif
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="rounded-md border border-white/10 p-2 text-slate-200 md:hidden"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="mb-4 flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-md border border-white/10 bg-white/8 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-white/14"
          >
            {theme === "dark" ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
            {theme === "dark" ? "Mode clair" : "Mode sombre"}
          </button>
          <Link
            to="/help"
            onClick={() => setMobileOpen(false)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/10 bg-white/8 text-white transition hover:bg-white/14"
            aria-label="Ouvrir l'aide"
          >
            <BookOpenIcon className="h-5 w-5" />
          </Link>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto pr-1">
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
                  className={`group flex items-center gap-3 rounded-md px-4 py-3 text-[15px] font-semibold transition ${
                    active
                      ? "bg-white/12 text-white"
                      : "text-slate-300 hover:bg-white/8 hover:text-white"
                  }`}
                >
                  <Icon className={`h-5 w-5 ${active ? "text-white" : "text-slate-300 group-hover:text-white"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
        </nav>

        <div className="mt-6 rounded-lg border border-white/10 bg-white/8 p-4">
          <div className="text-[12px] font-bold uppercase tracking-[0.24em] text-slate-300">Session</div>
          <div className="mt-3 text-[15px] font-semibold text-white">{session?.full_name || session?.username}</div>
          <div className="mt-1 text-[12px] font-bold uppercase tracking-[0.2em] text-[#50C878]">
            {session?.effective_role_code || session?.role_code}
          </div>
          {session?.username ? (
            <div className="mt-4 text-[13px] leading-5 text-slate-300">
              Utilisateur : <span className="font-semibold text-white">{session.username}</span>
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => logout()}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-md border border-white/10 bg-[#001936] px-4 py-3 text-sm font-bold text-white transition hover:border-rose-300/40 hover:bg-rose-500/15"
          >
            <PowerIcon className="h-4 w-4" />
            Fermer la session
          </button>
        </div>
      </aside>
    </>
  );
}
