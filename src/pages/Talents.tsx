import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AcademicCapIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
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

interface Skill {
  id: number;
  employer_id: number;
  code: string;
  name: string;
  description: string | null;
  scale_max: number;
  is_active: boolean;
}

interface EmployeeSkill {
  id: number;
  worker_id: number;
  skill_id: number;
  level: number;
  source: string;
}

interface Training {
  id: number;
  employer_id: number;
  title: string;
  provider: string | null;
  duration_hours: number;
  mode: string | null;
  price: number;
  objectives: string | null;
  status: string;
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClassName = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";


export default function Talents() {
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [skillForm, setSkillForm] = useState({
    code: "",
    name: "",
    description: "",
    scale_max: "5",
  });
  const [assignmentForm, setAssignmentForm] = useState({
    skill_id: "",
    level: "3",
    source: "manager",
  });
  const [trainingForm, setTrainingForm] = useState({
    title: "",
    provider: "",
    duration_hours: "7",
    mode: "presentiel",
    price: "0",
    objectives: "",
    status: "draft",
  });

  const { data: employers = [] } = useQuery({
    queryKey: ["talents", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  useEffect(() => {
    if (!selectedEmployerId && employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }, [employers, selectedEmployerId]);

  const { data: workers = [] } = useQuery({
    queryKey: ["talents", "workers", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<Worker[]>("/workers", {
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

  const { data: skills = [] } = useQuery({
    queryKey: ["talents", "skills", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<Skill[]>("/talents/skills", {
        params: { employer_id: selectedEmployerId },
      })
    ).data,
  });

  const { data: employeeSkills = [] } = useQuery({
    queryKey: ["talents", "employee-skills", selectedWorkerId],
    enabled: selectedWorkerId !== null,
    queryFn: async () => (
      await api.get<EmployeeSkill[]>("/talents/employee-skills", {
        params: { worker_id: selectedWorkerId },
      })
    ).data,
  });

  const { data: trainings = [] } = useQuery({
    queryKey: ["talents", "trainings", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (
      await api.get<Training[]>("/talents/trainings", {
        params: { employer_id: selectedEmployerId },
      })
    ).data,
  });

  const invalidateTalents = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["talents", "skills"] }),
      queryClient.invalidateQueries({ queryKey: ["talents", "employee-skills"] }),
      queryClient.invalidateQueries({ queryKey: ["talents", "trainings"] }),
    ]);
  };

  const createSkillMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEmployerId) {
        throw new Error("Selectionnez un employeur.");
      }
      return (
        await api.post<Skill>("/talents/skills", {
          employer_id: selectedEmployerId,
          code: skillForm.code,
          name: skillForm.name,
          description: skillForm.description || null,
          scale_max: Number(skillForm.scale_max || "5"),
          is_active: true,
        })
      ).data;
    },
    onSuccess: async () => {
      setSkillForm({ code: "", name: "", description: "", scale_max: "5" });
      setFeedback("Competence enregistree.");
      await invalidateTalents();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : "Creation de la competence impossible.");
    },
  });

  const createEmployeeSkillMutation = useMutation({
    mutationFn: async () => {
      if (!selectedWorkerId || !assignmentForm.skill_id) {
        throw new Error("Selectionnez un salarie et une competence.");
      }
      return (
        await api.post<EmployeeSkill>("/talents/employee-skills", {
          worker_id: selectedWorkerId,
          skill_id: Number(assignmentForm.skill_id),
          level: Number(assignmentForm.level || "1"),
          source: assignmentForm.source,
        })
      ).data;
    },
    onSuccess: async () => {
      setAssignmentForm({ skill_id: "", level: "3", source: "manager" });
      setFeedback("Competence affectee au salarie.");
      await invalidateTalents();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : "Affectation impossible.");
    },
  });

  const createTrainingMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEmployerId) {
        throw new Error("Selectionnez un employeur.");
      }
      return (
        await api.post<Training>("/talents/trainings", {
          employer_id: selectedEmployerId,
          title: trainingForm.title,
          provider: trainingForm.provider || null,
          duration_hours: Number(trainingForm.duration_hours || "0"),
          mode: trainingForm.mode || null,
          price: Number(trainingForm.price || "0"),
          objectives: trainingForm.objectives || null,
          status: trainingForm.status,
        })
      ).data;
    },
    onSuccess: async () => {
      setTrainingForm({
        title: "",
        provider: "",
        duration_hours: "7",
        mode: "presentiel",
        price: "0",
        objectives: "",
        status: "draft",
      });
      setFeedback("Formation enregistree.");
      await invalidateTalents();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : "Creation de la formation impossible.");
    },
  });

  const selectedWorker = workers.find((worker) => worker.id === selectedWorkerId) ?? null;

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(21,94,117,0.9),rgba(67,56,202,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Module talents
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              Competences, affectations et formation
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Referentiel de competences, niveaux salaries et plan de formation.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Competences</div>
              <div className="mt-3 text-3xl font-semibold text-white">{skills.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Affectations</div>
              <div className="mt-3 text-3xl font-semibold text-white">{employeeSkills.length}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Formations</div>
              <div className="mt-3 text-3xl font-semibold text-white">{trainings.length}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.85fr_1fr_1fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <SparklesIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Cadre RH</h2>
              <p className="text-sm text-slate-400">Employeur et salarie cibles.</p>
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
                onChange={(event) => setSelectedWorkerId(Number(event.target.value))}
                className={inputClassName}
              >
                {workers.map((worker) => (
                  <option key={worker.id} value={worker.id}>
                    {worker.nom} {worker.prenom} {worker.matricule ? `(${worker.matricule})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedWorker ? (
            <div className="mt-8 rounded-[1.5rem] border border-white/10 bg-white/5 p-5">
              <div className="text-sm font-semibold text-white">
                {selectedWorker.nom} {selectedWorker.prenom}
              </div>
              <div className="mt-2 text-sm text-slate-400">{selectedWorker.poste || "Poste non renseigne"}</div>
            </div>
          ) : null}

          {feedback ? (
            <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
              {feedback}
            </div>
          ) : null}
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ArrowTrendingUpIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Competences</h2>
              <p className="text-sm text-slate-400">Referentiel + affectation salarie.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelClassName}>Code</label>
                <input
                  value={skillForm.code}
                  onChange={(event) => setSkillForm((current) => ({ ...current, code: event.target.value }))}
                  className={inputClassName}
                  placeholder="PAIE-ADV"
                />
              </div>
              <div>
                <label className={labelClassName}>Libelle</label>
                <input
                  value={skillForm.name}
                  onChange={(event) => setSkillForm((current) => ({ ...current, name: event.target.value }))}
                  className={inputClassName}
                  placeholder="Administration paie"
                />
              </div>
            </div>
            <div>
              <label className={labelClassName}>Description</label>
              <textarea
                value={skillForm.description}
                onChange={(event) => setSkillForm((current) => ({ ...current, description: event.target.value }))}
                className={`${inputClassName} min-h-24 resize-y`}
                placeholder="Domaine, indicateurs, pieces de preuve"
              />
            </div>
            <div>
              <label className={labelClassName}>Echelle max</label>
              <input
                type="number"
                min="1"
                max="10"
                value={skillForm.scale_max}
                onChange={(event) => setSkillForm((current) => ({ ...current, scale_max: event.target.value }))}
                className={inputClassName}
              />
            </div>
            <button
              type="button"
              onClick={() => createSkillMutation.mutate()}
              disabled={createSkillMutation.isPending}
              className="rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createSkillMutation.isPending ? "Enregistrement..." : "Creer la competence"}
            </button>

            <div className="mt-3 border-t border-white/10 pt-6">
              <div className="text-sm font-semibold text-white">Affecter au salarie</div>
              <div className="mt-4 grid gap-4">
                <div>
                  <label className={labelClassName}>Competence</label>
                  <select
                    value={assignmentForm.skill_id}
                    onChange={(event) => setAssignmentForm((current) => ({ ...current, skill_id: event.target.value }))}
                    className={inputClassName}
                  >
                    <option value="">Selectionner</option>
                    {skills.map((skill) => (
                      <option key={skill.id} value={skill.id}>
                        {skill.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClassName}>Niveau</label>
                    <input
                      type="number"
                      min="1"
                      value={assignmentForm.level}
                      onChange={(event) => setAssignmentForm((current) => ({ ...current, level: event.target.value }))}
                      className={inputClassName}
                    />
                  </div>
                  <div>
                    <label className={labelClassName}>Source</label>
                    <select
                      value={assignmentForm.source}
                      onChange={(event) => setAssignmentForm((current) => ({ ...current, source: event.target.value }))}
                      className={inputClassName}
                    >
                      <option value="manager">Manager</option>
                      <option value="rh">RH</option>
                      <option value="evaluation">Evaluation</option>
                    </select>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => createEmployeeSkillMutation.mutate()}
                  disabled={createEmployeeSkillMutation.isPending}
                  className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {createEmployeeSkillMutation.isPending ? "Enregistrement..." : "Affecter la competence"}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <AcademicCapIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Formations</h2>
              <p className="text-sm text-slate-400">Catalogues et lots de formation.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <div>
              <label className={labelClassName}>Intitule</label>
              <input
                value={trainingForm.title}
                onChange={(event) => setTrainingForm((current) => ({ ...current, title: event.target.value }))}
                className={inputClassName}
                placeholder="Excel avance pour RH"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelClassName}>Organisme</label>
                <input
                  value={trainingForm.provider}
                  onChange={(event) => setTrainingForm((current) => ({ ...current, provider: event.target.value }))}
                  className={inputClassName}
                  placeholder="Cabinet interne"
                />
              </div>
              <div>
                <label className={labelClassName}>Mode</label>
                <input
                  value={trainingForm.mode}
                  onChange={(event) => setTrainingForm((current) => ({ ...current, mode: event.target.value }))}
                  className={inputClassName}
                  placeholder="presentiel"
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className={labelClassName}>Duree (h)</label>
                <input
                  type="number"
                  min="0"
                  value={trainingForm.duration_hours}
                  onChange={(event) =>
                    setTrainingForm((current) => ({ ...current, duration_hours: event.target.value }))
                  }
                  className={inputClassName}
                />
              </div>
              <div>
                <label className={labelClassName}>Prix</label>
                <input
                  type="number"
                  min="0"
                  value={trainingForm.price}
                  onChange={(event) => setTrainingForm((current) => ({ ...current, price: event.target.value }))}
                  className={inputClassName}
                />
              </div>
              <div>
                <label className={labelClassName}>Statut</label>
                <select
                  value={trainingForm.status}
                  onChange={(event) => setTrainingForm((current) => ({ ...current, status: event.target.value }))}
                  className={inputClassName}
                >
                  <option value="draft">Brouillon</option>
                  <option value="scheduled">Programmee</option>
                  <option value="active">Active</option>
                  <option value="closed">Cloturee</option>
                </select>
              </div>
            </div>
            <div>
              <label className={labelClassName}>Objectifs</label>
              <textarea
                value={trainingForm.objectives}
                onChange={(event) => setTrainingForm((current) => ({ ...current, objectives: event.target.value }))}
                className={`${inputClassName} min-h-24 resize-y`}
                placeholder="Public cible, objectifs, livrables"
              />
            </div>
            <button
              type="button"
              onClick={() => createTrainingMutation.mutate()}
              disabled={createTrainingMutation.isPending}
              className="rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createTrainingMutation.isPending ? "Enregistrement..." : "Creer la formation"}
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className={cardClassName}>
          <h2 className="text-xl font-semibold text-white">Referentiel competences</h2>
          <div className="mt-5 space-y-4">
            {skills.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-slate-400">
                Aucune competence enregistree.
              </div>
            ) : (
              skills.map((skill) => (
                <article key={skill.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="text-sm font-semibold text-white">{skill.name}</div>
                  <div className="mt-2 text-sm text-slate-400">{skill.code} • Niveau max {skill.scale_max}</div>
                  {skill.description ? <div className="mt-3 text-sm text-slate-400">{skill.description}</div> : null}
                </article>
              ))
            )}
          </div>
        </div>

        <div className={cardClassName}>
          <h2 className="text-xl font-semibold text-white">Competences du salarie</h2>
          <div className="mt-5 space-y-4">
            {employeeSkills.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-slate-400">
                Aucune competence affectee.
              </div>
            ) : (
              employeeSkills.map((employeeSkill) => {
                const skill = skills.find((item) => item.id === employeeSkill.skill_id);
                return (
                  <article key={employeeSkill.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="text-sm font-semibold text-white">{skill?.name || "Competence"}</div>
                    <div className="mt-2 text-sm text-slate-400">
                      Niveau {employeeSkill.level} • Source {employeeSkill.source}
                    </div>
                  </article>
                );
              })
            )}
          </div>
        </div>

        <div className={cardClassName}>
          <h2 className="text-xl font-semibold text-white">Catalogue formations</h2>
          <div className="mt-5 space-y-4">
            {trainings.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-slate-400">
                Aucune formation enregistree.
              </div>
            ) : (
              trainings.map((training) => (
                <article key={training.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="text-sm font-semibold text-white">{training.title}</div>
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-200">
                      {training.status}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-slate-400">
                    {training.provider || "Organisme non renseigne"} • {training.duration_hours} h
                  </div>
                  {training.objectives ? (
                    <div className="mt-3 text-sm text-slate-400">{training.objectives}</div>
                  ) : null}
                </article>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
