import { useEffect, useMemo, useState } from "react";
import { BookOpenIcon, QuestionMarkCircleIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";

import { useAuth } from "../contexts/AuthContext";
import { helpModules, roleGuides, type HelpRole } from "../help/helpContent";

const shellCard =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";

function resolveHelpRole(role?: string | null): HelpRole {
  const normalized = (role || "").trim().toLowerCase();
  if (normalized.includes("inspect")) return "inspecteur";
  if (normalized.includes("manager") || normalized.includes("departement")) return "manager";
  if (normalized.includes("rh") || normalized.includes("employeur")) return "rh";
  if (normalized.includes("direction") || normalized.includes("dg") || normalized.includes("pdg")) return "direction";
  if (normalized.includes("employ")) return "employe";
  return "general";
}

export default function HelpCenter() {
  const { session } = useAuth();
  const [activeModuleCode, setActiveModuleCode] = useState(helpModules[0]?.code ?? "workforce");
  const activeRole = useMemo(() => resolveHelpRole(session?.effective_role_code || session?.role_code), [session]);

  const scopedModules = useMemo(
    () =>
      helpModules
        .map((module) => ({
          ...module,
          topics: module.topics.filter((topic) => topic.roles.includes(activeRole) || topic.roles.includes("general")),
        }))
        .filter((module) => module.topics.length > 0),
    [activeRole],
  );

  const activeModule = useMemo(
    () => scopedModules.find((item) => item.code === activeModuleCode) ?? scopedModules[0] ?? helpModules[0],
    [activeModuleCode, scopedModules],
  );

  const currentRoleGuide = useMemo(() => roleGuides.find((item) => item.role === activeRole) ?? roleGuides[0], [activeRole]);

  useEffect(() => {
    if (!scopedModules.some((item) => item.code === activeModuleCode)) {
      setActiveModuleCode(scopedModules[0]?.code ?? helpModules[0]?.code ?? "workforce");
    }
  }, [activeModuleCode, scopedModules]);

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(8,47,73,0.9),rgba(37,99,235,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Aide utilisateur
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Mode d'emploi SIIRH</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Centre d'aide contextualise pour le role connecte, avec procedures utiles a l'ecran et rappels metier sans bruit inutile.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Modules utiles</div>
              <div className="mt-3 text-3xl font-semibold text-white">{scopedModules.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Role courant</div>
              <div className="mt-3 text-lg font-semibold text-white">{currentRoleGuide.title}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className={shellCard}>
          <div className="flex items-center gap-3">
            <BookOpenIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Modules</h2>
              <p className="text-sm text-slate-400">Documentation pratique limitee a votre perimetre.</p>
            </div>
          </div>
          <div className="mt-6 space-y-3">
            {scopedModules.map((module) => (
              <button
                key={module.code}
                type="button"
                onClick={() => setActiveModuleCode(module.code)}
                className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                  activeModuleCode === module.code
                    ? "border-cyan-300/40 bg-cyan-400/10 text-white"
                    : "border-white/10 bg-white/5 text-slate-200 hover:border-cyan-300/30"
                }`}
              >
                <div className="font-semibold">{module.title}</div>
                <div className="mt-1 text-xs text-slate-400">{module.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className={shellCard}>
          <div className="flex items-center gap-3">
            <QuestionMarkCircleIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">{activeModule?.title ?? "Aide"}</h2>
              <p className="text-sm text-slate-400">{activeModule?.description ?? "Documentation contextuelle."}</p>
            </div>
          </div>

          <div className="mt-6 space-y-6">
            {(activeModule?.topics ?? []).map((topic) => (
              <article key={topic.id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="text-lg font-semibold text-white">{topic.title}</div>
                <div className="mt-2 text-sm text-slate-300">{topic.summary}</div>
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Workflow</div>
                    <ul className="mt-2 space-y-2 text-sm text-slate-300">
                      {topic.workflows.map((item) => <li key={item}>- {item}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Regles metier</div>
                    <ul className="mt-2 space-y-2 text-sm text-slate-300">
                      {topic.businessRules.map((item) => <li key={item}>- {item}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Erreurs frequentes</div>
                    <ul className="mt-2 space-y-2 text-sm text-slate-300">
                      {topic.frequentErrors.map((item) => <li key={item}>- {item}</li>)}
                    </ul>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className={shellCard}>
        <div className="flex items-center gap-3">
          <ShieldCheckIcon className="h-6 w-6 text-cyan-300" />
          <div>
            <h2 className="text-xl font-semibold text-white">Aide par role</h2>
            <p className="text-sm text-slate-400">Ce que votre profil voit, fait et ne fait pas.</p>
          </div>
        </div>
        <div className="mt-6">
          <article className="rounded-2xl border border-cyan-300/40 bg-cyan-400/10 p-5">
            <div className="text-lg font-semibold text-white">{currentRoleGuide.title}</div>
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Peut voir</div>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">{currentRoleGuide.canSee.map((item) => <li key={item}>- {item}</li>)}</ul>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Peut faire</div>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">{currentRoleGuide.canDo.map((item) => <li key={item}>- {item}</li>)}</ul>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Ne peut pas faire</div>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">{currentRoleGuide.cannotDo.map((item) => <li key={item}>- {item}</li>)}</ul>
              </div>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
