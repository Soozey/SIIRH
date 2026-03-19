import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Bars3Icon,
  BuildingOfficeIcon,
  CalendarIcon,
  ChartBarIcon,
  ClockIcon,
  DocumentTextIcon,
  PowerIcon,
  UserGroupIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

import { useAuth } from "../contexts/AuthContext";


interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { path: "/", label: "Employeurs", icon: BuildingOfficeIcon },
  { path: "/workers", label: "Travailleurs", icon: UserGroupIcon },
  { path: "/payroll", label: "Paie", icon: DocumentTextIcon },
  { path: "/hs", label: "Heures", icon: ClockIcon },
  { path: "/absences", label: "Absences", icon: CalendarIcon },
  { path: "/leaves", label: "Congés", icon: CalendarIcon },
  { path: "/reporting", label: "Reporting", icon: ChartBarIcon },
];


export default function Navigation() {
  const location = useLocation();
  const { session, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

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
        className="fixed left-4 top-4 z-[70] rounded-2xl border border-slate-800 bg-slate-950/90 p-3 text-slate-100 shadow-xl md:hidden"
      >
        <Bars3Icon className="h-6 w-6" />
      </button>

      <div
        className={`fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm transition-opacity md:hidden ${mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setMobileOpen(false)}
      />

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/10 bg-slate-950/90 p-5 shadow-2xl shadow-slate-950/50 backdrop-blur-xl transition-transform md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-cyan-200">
              SIIRH
            </div>
            <div className="mt-4 text-2xl font-semibold text-white">Pilotage RH</div>
            <div className="mt-2 text-sm text-slate-400">Paie, dossiers, conformité et reporting.</div>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="rounded-2xl border border-white/10 p-2 text-slate-400 md:hidden"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={`group flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition ${
                  active
                    ? "bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon className={`h-5 w-5 ${active ? "text-slate-950" : "text-slate-500 group-hover:text-cyan-300"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-[1.75rem] border border-white/10 bg-white/5 p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Session</div>
          <div className="mt-3 text-sm font-semibold text-white">{session?.full_name || session?.username}</div>
          <div className="mt-1 text-xs uppercase tracking-[0.2em] text-cyan-300">{session?.role_code}</div>
          {session?.username ? (
            <div className="mt-4 text-xs leading-5 text-slate-400">
              Utilisateur: <span className="font-medium text-slate-200">{session.username}</span>
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => logout()}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-rose-400/30 hover:bg-rose-500/10 hover:text-rose-100"
          >
            <PowerIcon className="h-4 w-4" />
            Fermer la session
          </button>
        </div>
      </aside>
    </>
  );
}
