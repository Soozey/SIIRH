import { QuestionMarkCircleIcon } from "@heroicons/react/24/outline";
import { useMemo, useState } from "react";

import { type HelpRole, type ContextHelpItem } from "../../help/helpContent";

type Props = {
  item: ContextHelpItem | null;
  role?: string | null;
  compact?: boolean;
};

function resolveHelpRole(role?: string | null): HelpRole {
  const normalized = (role || "").trim().toLowerCase();
  if (normalized.includes("inspect")) return "inspecteur";
  if (normalized.includes("manager") || normalized.includes("departement")) return "manager";
  if (normalized.includes("rh") || normalized.includes("employeur")) return "rh";
  if (normalized.includes("direction") || normalized.includes("dg") || normalized.includes("pdg")) return "direction";
  if (normalized.includes("employ")) return "employe";
  return "general";
}

export default function HelpTooltip({ item, role, compact = false }: Props) {
  const [open, setOpen] = useState(false);
  const resolvedRole = useMemo(() => resolveHelpRole(role), [role]);

  if (!item) return null;

  const text = item.roleText[resolvedRole] || item.roleText.general || Object.values(item.roleText)[0] || "";

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className={`inline-flex items-center justify-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-cyan-200 transition hover:bg-cyan-400/20 ${
          compact ? "h-5 w-5" : "h-6 w-6"
        }`}
        aria-label={`Aide: ${item.title}`}
      >
        <QuestionMarkCircleIcon className={compact ? "h-3.5 w-3.5" : "h-4 w-4"} />
      </button>
      {open ? (
        <div
          className="absolute left-1/2 top-full z-[80] mt-2 w-72 -translate-x-1/2 rounded-2xl border border-white/10 bg-slate-950/95 p-4 text-left shadow-2xl shadow-slate-950/40 backdrop-blur"
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          <div className="text-sm font-semibold text-white">{item.title}</div>
          <div className="mt-2 text-xs leading-5 text-slate-300">{text}</div>
          {item.rule ? <div className="mt-3 text-xs text-cyan-200">Règle: {item.rule}</div> : null}
          {item.example ? <div className="mt-2 text-xs text-slate-400">Exemple: {item.example}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
