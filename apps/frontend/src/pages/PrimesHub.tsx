import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

type Employer = {
  id: number;
  raison_sociale: string;
};

export default function PrimesHub() {
  const { data: employers = [], isLoading, isError } = useQuery({
    queryKey: ["primes-hub", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  const [selectedEmployerId, setSelectedEmployerId] = useState<number | "">("");

  const selectedEmployer = useMemo(
    () => employers.find((item) => item.id === selectedEmployerId) ?? null,
    [employers, selectedEmployerId]
  );

  if (isLoading) {
    return <div className="rounded-2xl border border-white/10 bg-slate-900/40 p-6 text-slate-300">Chargement des employeurs...</div>;
  }

  if (isError) {
    return <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-6 text-red-100">Impossible de charger les employeurs.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-6">
        <h1 className="text-2xl font-semibold text-white">Module Primes</h1>
        <p className="mt-2 text-sm text-slate-400">
          Sélectionnez un employeur pour ouvrir la gestion détaillée des primes.
        </p>
      </div>

      <div className="rounded-[1.75rem] border border-white/10 bg-slate-900/40 p-6">
        <label className="mb-2 block text-sm font-medium text-slate-200">Employeur</label>
        <select
          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-slate-100"
          value={selectedEmployerId}
          onChange={(event) => setSelectedEmployerId(Number(event.target.value) || "")}
        >
          <option value="">Choisir un employeur</option>
          {employers.map((employer) => (
            <option key={employer.id} value={employer.id}>
              {employer.raison_sociale}
            </option>
          ))}
        </select>

        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            to={selectedEmployer ? `/employers/${selectedEmployer.id}/primes` : "/employers"}
            className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
              selectedEmployer
                ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
                : "cursor-not-allowed bg-slate-700 text-slate-400"
            }`}
            onClick={(event) => {
              if (!selectedEmployer) {
                event.preventDefault();
              }
            }}
          >
            Ouvrir la gestion des primes
          </Link>
          <Link
            to="/payroll"
            className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-white/5"
          >
            Aller vers Paie
          </Link>
        </div>
      </div>
    </div>
  );
}
