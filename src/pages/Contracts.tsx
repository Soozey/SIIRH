import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  IdentificationIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";
import EmploymentAttestation from "../components/EmploymentAttestation";
import EmploymentContract from "../components/EmploymentContract";
import WorkCertificate from "../components/WorkCertificate";


interface Employer {
  id: number;
  raison_sociale: string;
  nif?: string | null;
  adresse?: string | null;
  ville?: string | null;
  pays?: string | null;
  stat?: string | null;
  representant?: string | null;
  rep_nom_prenom?: string | null;
  rep_fonction?: string | null;
  logo_path?: string | null;
}

interface WorkerSummary {
  id: number;
  employer_id: number;
  matricule?: string | null;
  nom: string;
  prenom: string;
  poste?: string | null;
}

interface WorkerDetails extends WorkerSummary {
  date_embauche?: string | null;
  date_debauche?: string | null;
  nature_contrat?: string | null;
  categorie_prof?: string | null;
  salaire_base?: number | null;
  date_naissance?: string | null;
  lieu_naissance?: string | null;
  cin?: string | null;
  cin_delivre_le?: string | null;
  cin_lieu?: string | null;
  adresse?: string | null;
  duree_essai_jours?: number | null;
  horaire_hebdo?: number | null;
  position_history?: Array<{
    poste: string;
    categorie_prof?: string | null;
    start_date: string;
    end_date?: string | null;
  }>;
}

type DocumentMode = "contract" | "attestation" | "certificate";

const shellCardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300/50";


export default function Contracts() {
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(null);
  const [documentMode, setDocumentMode] = useState<DocumentMode>("contract");

  const { data: employers = [] } = useQuery({
    queryKey: ["contracts", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  useEffect(() => {
    if (!selectedEmployerId && employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["contracts", "workers", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<WorkerSummary[]>("/workers", {
        params: { employer_id: selectedEmployerId },
      })
    ).data,
  });

  useEffect(() => {
    if (!workers.length) {
      setSelectedWorkerId(null);
      return;
    }
    if (!selectedWorkerId || !workers.some((worker) => worker.id === selectedWorkerId)) {
      setSelectedWorkerId(workers[0].id);
    }
  }, [workers, selectedWorkerId]);

  const { data: worker } = useQuery({
    queryKey: ["contracts", "worker", selectedWorkerId],
    enabled: selectedWorkerId !== null,
    queryFn: async () => (await api.get<WorkerDetails>(`/workers/${selectedWorkerId}`)).data,
  });

  const employer = employers.find((item) => item.id === selectedEmployerId) ?? null;
  const documentLabel =
    documentMode === "contract" ? "Contrat" : documentMode === "attestation" ? "Attestation" : "Certificat";

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(29,78,216,0.88),rgba(88,28,135,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Module contrats
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Contrats, attestations et certificats RH
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Reutilisation des generateurs documentaires deja presents pour sortir
              rapidement les pieces RH attendues.
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
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Document</div>
              <div className="mt-3 text-lg font-semibold text-white">{documentLabel}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.55fr]">
        <div className={shellCardClassName}>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3">
              <ClipboardDocumentListIcon className="h-6 w-6 text-cyan-300" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Selection du dossier</h2>
              <p className="text-sm text-slate-400">Employeur, salarie et type de document.</p>
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
                {employers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.raison_sociale}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                Salarie
              </label>
              <select
                value={selectedWorkerId ?? ""}
                onChange={(event) => setSelectedWorkerId(Number(event.target.value))}
                className={inputClassName}
              >
                {workers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nom} {item.prenom} {item.matricule ? `(${item.matricule})` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { id: "contract" as const, label: "Contrat" },
                { id: "attestation" as const, label: "Attestation" },
                { id: "certificate" as const, label: "Certificat" },
              ].map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setDocumentMode(mode.id)}
                  className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                    documentMode === mode.id
                      ? "bg-cyan-400 text-slate-950"
                      : "border border-white/10 bg-white/5 text-slate-200 hover:border-cyan-300/40"
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>

          {worker ? (
            <div className="mt-8 rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
              <div className="flex items-center gap-3">
                <IdentificationIcon className="h-5 w-5 text-cyan-300" />
                <div className="text-sm font-semibold text-white">
                  {worker.nom} {worker.prenom}
                </div>
              </div>
              <div className="mt-4 space-y-2 text-sm text-slate-400">
                <div>Poste: {worker.poste || "Non renseigne"}</div>
                <div>Contrat: {worker.nature_contrat || "Non renseigne"}</div>
                <div>Matricule: {worker.matricule || "Non renseigne"}</div>
              </div>
            </div>
          ) : null}
        </div>

        <div className={`${shellCardClassName} overflow-hidden p-0`}>
          <div className="border-b border-white/10 px-6 py-5">
            <div className="flex items-center gap-3">
              <DocumentTextIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Document RH</h2>
                <p className="text-sm text-slate-400">
                  Previsualisation directe avant impression.
                </p>
              </div>
            </div>
          </div>

          <div className="max-h-[78vh] overflow-auto bg-slate-900/60">
            {employer && worker ? (
              documentMode === "contract" ? (
                <EmploymentContract worker={worker} employer={employer} />
              ) : documentMode === "attestation" ? (
                <EmploymentAttestation worker={worker} employer={employer} />
              ) : (
                <WorkCertificate worker={worker} employer={employer} />
              )
            ) : (
              <div className="flex min-h-[480px] items-center justify-center px-6 text-center text-sm text-slate-400">
                Selectionnez un employeur et un salarie pour afficher le document.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
