import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CheckBadgeIcon,
  ClipboardDocumentCheckIcon,
  CalendarDaysIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface DeclarationItem {
  id: string;
  label: string;
  owner: string;
  dueDate: string;
  description: string;
  route: string;
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50";


function buildDueDate(period: string, dayOfMonth: number): string {
  const [year, month] = period.split("-").map(Number);
  return new Date(year, month - 1, dayOfMonth).toLocaleDateString("fr-FR");
}


export default function Declarations() {
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));

  const { data: employers = [] } = useQuery({
    queryKey: ["declarations", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  useEffect(() => {
    if (!selectedEmployerId && employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }, [employers, selectedEmployerId]);

  const declarationItems: DeclarationItem[] = [
    {
      id: "irsa",
      label: "Declaration IRSA",
      owner: "Comptabilite / Paie",
      dueDate: buildDueDate(period, 15),
      description: "Controle de la retenue a la source et coherence bulletins / variables.",
      route: "/payroll",
    },
    {
      id: "cnaps",
      label: "Declaration CNAPS",
      owner: "Paie / RH",
      dueDate: buildDueDate(period, 15),
      description: "Verifie l'assiette, les taux et les effectifs couverts.",
      route: "/payroll",
    },
    {
      id: "ostie",
      label: "Declaration OSTIE / SMIE",
      owner: "RH / Conformite",
      dueDate: buildDueDate(period, 15),
      description: "S'assure que les affiliations et plafonds employeur sont alignes.",
      route: "/reporting",
    },
    {
      id: "fmfp",
      label: "Versement FMFP",
      owner: "Finance / RH",
      dueDate: buildDueDate(period, 20),
      description: "A rapprocher du plan de formation et du budget talents.",
      route: "/talents",
    },
    {
      id: "documents",
      label: "Archivage bulletins et pieces",
      owner: "Administration RH",
      dueDate: buildDueDate(period, 25),
      description: "Classement des bulletins, contrats, avenants et justificatifs d'absence.",
      route: "/contracts",
    },
  ];

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(30,64,175,0.88),rgba(21,128,61,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Module declarations
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Calendrier de conformite RH et sociale
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Vue operationnelle des echeances sociales rattachees a la paie,
              aux documents RH et aux actions de suivi.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Employeurs</div>
              <div className="mt-3 text-3xl font-semibold text-white">{employers.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Echeances</div>
              <div className="mt-3 text-3xl font-semibold text-white">{declarationItems.length}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <CalendarDaysIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Periode de suivi</h2>
              <p className="text-sm text-slate-400">Pilotage mensuel des obligations.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                Employeur
              </label>
              <select
                value={selectedEmployerId ?? ""}
                onChange={(event) => setSelectedEmployerId(Number(event.target.value))}
                className={inputClassName}
              >
                {employers.map((employer) => (
                  <option key={employer.id} value={employer.id}>
                    {employer.raison_sociale}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                Mois
              </label>
              <input
                type="month"
                value={period}
                onChange={(event) => setPeriod(event.target.value)}
                className={inputClassName}
              />
            </div>
          </div>

          <div className="mt-8 rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
            <div className="flex items-center gap-3">
              <CheckBadgeIcon className="h-5 w-5 text-emerald-300" />
              <div className="text-sm font-semibold text-white">Checklist commerciale</div>
            </div>
            <div className="mt-4 space-y-2 text-sm text-slate-400">
              <div>1. Controle paie et variables</div>
              <div>2. Declaration organismes sociaux</div>
              <div>3. Archivage et preuve documentaire</div>
              <div>4. Relance des dossiers non regles</div>
            </div>
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ClipboardDocumentCheckIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Echeancier</h2>
              <p className="text-sm text-slate-400">
                Actions a suivre pour {period}.
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {declarationItems.map((item) => (
              <a
                key={item.id}
                href={item.route}
                className="block rounded-[1.5rem] border border-white/10 bg-white/5 p-5 transition hover:border-cyan-300/40 hover:bg-cyan-400/8"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-white">{item.label}</div>
                    <div className="mt-2 text-sm text-slate-400">{item.owner}</div>
                  </div>
                  <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-200">
                    {item.dueDate}
                  </span>
                </div>
                <div className="mt-4 text-sm leading-6 text-slate-400">{item.description}</div>
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
