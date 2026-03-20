import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExclamationTriangleIcon,
  LifebuoyIcon,
  ShieldExclamationIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface Worker {
  id: number;
  employer_id: number;
  nom: string;
  prenom: string;
  matricule?: string | null;
  poste?: string | null;
}

interface Incident {
  id: number;
  employer_id: number;
  worker_id: number | null;
  incident_type: string;
  severity: string;
  status: string;
  occurred_at: string;
  location: string | null;
  description: string;
  action_taken: string | null;
  witnesses: string | null;
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClassName = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";


export default function Sst() {
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [form, setForm] = useState({
    incident_type: "",
    severity: "medium",
    status: "open",
    occurred_at: new Date().toISOString().slice(0, 16),
    location: "",
    description: "",
    action_taken: "",
    witnesses: "",
  });

  const { data: employers = [] } = useQuery({
    queryKey: ["sst", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  useEffect(() => {
    if (!selectedEmployerId && employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["sst", "workers", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<Worker[]>("/workers", {
        params: { employer_id: selectedEmployerId },
      })
    ).data,
  });

  const { data: incidents = [] } = useQuery({
    queryKey: ["sst", "incidents", selectedEmployerId, selectedWorkerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<Incident[]>("/sst/incidents", {
        params: {
          employer_id: selectedEmployerId,
          worker_id: selectedWorkerId ?? undefined,
        },
      })
    ).data,
  });

  const createIncidentMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEmployerId) {
        throw new Error("Selectionnez un employeur.");
      }
      return (
        await api.post<Incident>("/sst/incidents", {
          employer_id: selectedEmployerId,
          worker_id: selectedWorkerId,
          incident_type: form.incident_type,
          severity: form.severity,
          status: form.status,
          occurred_at: new Date(form.occurred_at).toISOString(),
          location: form.location || null,
          description: form.description,
          action_taken: form.action_taken || null,
          witnesses: form.witnesses || null,
        })
      ).data;
    },
    onSuccess: async () => {
      setForm({
        incident_type: "",
        severity: "medium",
        status: "open",
        occurred_at: new Date().toISOString().slice(0, 16),
        location: "",
        description: "",
        action_taken: "",
        witnesses: "",
      });
      setFeedback("Incident SST enregistre.");
      await queryClient.invalidateQueries({ queryKey: ["sst", "incidents"] });
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : "Declaration impossible.");
    },
  });

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(127,29,29,0.88),rgba(180,83,9,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Module SST / AT-MP
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Sante, securite et incidents de travail
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Declaration d&apos;incidents, suivi des actions et historique des cas
              sensibles par employeur et salarie.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Employeurs</div>
              <div className="mt-3 text-3xl font-semibold text-white">{employers.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Salaries</div>
              <div className="mt-3 text-3xl font-semibold text-white">{workers.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Incidents</div>
              <div className="mt-3 text-3xl font-semibold text-white">{incidents.length}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr_1fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <LifebuoyIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Perimetre</h2>
              <p className="text-sm text-slate-400">Employeur et salarie concernes.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div>
              <label className={labelClassName}>Employeur</label>
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
              <label className={labelClassName}>Salarie</label>
              <select
                value={selectedWorkerId ?? ""}
                onChange={(event) => setSelectedWorkerId(event.target.value ? Number(event.target.value) : null)}
                className={inputClassName}
              >
                <option value="">Tous les salaries</option>
                {workers.map((worker) => (
                  <option key={worker.id} value={worker.id}>
                    {worker.nom} {worker.prenom} {worker.matricule ? `(${worker.matricule})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {feedback ? (
            <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
              {feedback}
            </div>
          ) : null}
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ShieldExclamationIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Declarer un incident</h2>
              <p className="text-sm text-slate-400">AT, MP, incident, alerte ou quasi-accident.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelClassName}>Type</label>
                <input
                  value={form.incident_type}
                  onChange={(event) => setForm((current) => ({ ...current, incident_type: event.target.value }))}
                  className={inputClassName}
                  placeholder="Accident de travail"
                />
              </div>
              <div>
                <label className={labelClassName}>Date / heure</label>
                <input
                  type="datetime-local"
                  value={form.occurred_at}
                  onChange={(event) => setForm((current) => ({ ...current, occurred_at: event.target.value }))}
                  className={inputClassName}
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className={labelClassName}>Gravite</label>
                <select
                  value={form.severity}
                  onChange={(event) => setForm((current) => ({ ...current, severity: event.target.value }))}
                  className={inputClassName}
                >
                  <option value="low">Faible</option>
                  <option value="medium">Moyenne</option>
                  <option value="high">Elevee</option>
                  <option value="critical">Critique</option>
                </select>
              </div>
              <div>
                <label className={labelClassName}>Statut</label>
                <select
                  value={form.status}
                  onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                  className={inputClassName}
                >
                  <option value="open">Ouvert</option>
                  <option value="investigating">En analyse</option>
                  <option value="mitigated">Mesures prises</option>
                  <option value="closed">Cloture</option>
                </select>
              </div>
              <div>
                <label className={labelClassName}>Lieu</label>
                <input
                  value={form.location}
                  onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))}
                  className={inputClassName}
                  placeholder="Atelier / Bureau / Chantier"
                />
              </div>
            </div>
            <div>
              <label className={labelClassName}>Description</label>
              <textarea
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                className={`${inputClassName} min-h-28 resize-y`}
                placeholder="Circonstances, faits observes, impact"
              />
            </div>
            <div>
              <label className={labelClassName}>Mesures prises</label>
              <textarea
                value={form.action_taken}
                onChange={(event) => setForm((current) => ({ ...current, action_taken: event.target.value }))}
                className={`${inputClassName} min-h-20 resize-y`}
                placeholder="Premiers soins, isolement, declaration, enquete"
              />
            </div>
            <div>
              <label className={labelClassName}>Temoins</label>
              <input
                value={form.witnesses}
                onChange={(event) => setForm((current) => ({ ...current, witnesses: event.target.value }))}
                className={inputClassName}
                placeholder="Noms ou references des temoins"
              />
            </div>
            <button
              type="button"
              onClick={() => createIncidentMutation.mutate()}
              disabled={createIncidentMutation.isPending}
              className="rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createIncidentMutation.isPending ? "Enregistrement..." : "Declarer l'incident"}
            </button>
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ExclamationTriangleIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Journal SST</h2>
              <p className="text-sm text-slate-400">Suivi chronologique des cas.</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {incidents.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-slate-400">
                Aucun incident enregistre dans ce perimetre.
              </div>
            ) : (
              incidents.map((incident) => {
                const worker = workers.find((item) => item.id === incident.worker_id);
                return (
                  <article key={incident.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-white">{incident.incident_type}</div>
                        <div className="mt-1 text-sm text-slate-400">
                          {new Date(incident.occurred_at).toLocaleString("fr-FR")}
                        </div>
                      </div>
                      <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-amber-200">
                        {incident.severity}
                      </span>
                    </div>
                    <div className="mt-3 text-sm text-slate-400">
                      {worker ? `${worker.nom} ${worker.prenom}` : "Cas non rattache"} • {incident.status}
                    </div>
                    <div className="mt-3 text-sm leading-6 text-slate-400">{incident.description}</div>
                    {incident.action_taken ? (
                      <div className="mt-3 rounded-2xl border border-white/10 bg-slate-900/60 px-4 py-3 text-sm text-slate-300">
                        Mesures: {incident.action_taken}
                      </div>
                    ) : null}
                  </article>
                );
              })
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
