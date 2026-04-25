import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  BellIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  QuestionMarkCircleIcon,
} from "@heroicons/react/24/outline";

import Navigation from "./Navigation";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";


interface LayoutProps {
  children: ReactNode;
  className?: string;
}


export default function Layout({ children, className = "" }: LayoutProps) {
  const { theme } = useTheme();
  const { session } = useAuth();
  return (
    <div className={`layout-shell min-h-screen ${theme === "light" ? "bg-[#f7f8fb] text-slate-900" : "bg-slate-950 text-slate-100"}`}>
      <Navigation />
      <main className={`min-h-screen md:pl-72 ${className}`}>
        <header className="layout-header sticky top-0 z-30 flex h-20 items-center justify-between gap-4 border-b border-slate-200 bg-white/98 px-4 shadow-sm md:px-8">
          <div className="relative hidden w-full max-w-xl md:block">
            <MagnifyingGlassIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
            <input
              className="h-11 w-full rounded-md border border-slate-200 bg-slate-100/80 pl-11 pr-4 text-sm font-medium text-slate-800 outline-none transition focus:border-[#002147] focus:bg-white focus:ring-2 focus:ring-blue-100"
              placeholder="Rechercher un employé, un dossier ou un module..."
              type="search"
            />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <Link
              to="/help"
              className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-[#002147]"
              aria-label="Aide"
            >
              <QuestionMarkCircleIcon className="h-6 w-6" />
            </Link>
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-[#002147]"
              aria-label="Notifications"
            >
              <BellIcon className="h-5 w-5" />
            </button>
            <Link
              to="/workers"
              className="hidden items-center gap-2 rounded-md bg-[#50C878] px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-600 sm:inline-flex"
            >
              <PlusIcon className="h-4 w-4" />
              Nouvel employé
            </Link>
            <div className="hidden min-w-0 border-l border-slate-200 pl-3 lg:block">
              <div className="truncate text-sm font-bold text-[#07152f]">{session?.full_name || session?.username}</div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{session?.effective_role_code || session?.role_code}</div>
            </div>
          </div>
        </header>
        <div className={`layout-main min-h-[calc(100vh-5rem)] px-4 py-5 md:px-8 md:py-7 ${
          theme === "light"
            ? "bg-[#f7f8fb]"
            : "bg-[radial-gradient(circle_at_top_left,_rgba(14,116,144,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(3,105,161,0.10),_transparent_28%),linear-gradient(180deg,_rgba(2,6,23,1),_rgba(15,23,42,1))]"
        }`}>
          <div className="layout-main-content mx-auto max-w-[1680px]">{children}</div>
        </div>
      </main>
    </div>
  );
}
