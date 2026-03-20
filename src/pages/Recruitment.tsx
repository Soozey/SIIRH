import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckBadgeIcon,
  DocumentTextIcon,
  SparklesIcon,
  UserPlusIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";

import { api } from "../api";
import { useToast } from "../components/ui/ToastProvider";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface JobPosting {
  id: number;
  employer_id: number;
  title: string;
  department: string | null;
  location: string | null;
  contract_type: string;
  status: string;
  salary_range: string | null;
  description: string | null;
  skills_required: string | null;
}

interface Candidate {
  id: number;
  employer_id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  status: string;
  summary: string | null;
}

interface Application {
  id: number;
  job_posting_id: number;
  candidate_id: number;
  stage: string;
  score: number | null;
  notes: string | null;
}

interface JobProfile {
  id: number;
  workflow_status: string;
  announcement_status: string;
  assistant_source: Record<string, unknown>;
  announcement_share_pack: Announcement | Record<string, never>;
  manager_title: string | null;
  mission_summary: string | null;
  main_activities: string[];
  technical_skills: string[];
  behavioral_skills: string[];
  education_level: string | null;
  experience_required: string | null;
  languages: string[];
  tools: string[];
  certifications: string[];
  salary_min: number | null;
  salary_max: number | null;
  working_hours: string | null;
  benefits: string[];
  desired_start_date: string | null;
  application_deadline: string | null;
  publication_channels: string[];
  classification: string | null;
  interview_criteria: string[];
  validation_comment: string | null;
  announcement_title: string | null;
  announcement_body: string | null;
}

interface Suggestion {
  probable_title: string;
  probable_department: string;
  mission_summary: string;
  main_activities: string[];
  technical_skills: string[];
  behavioral_skills: string[];
  education_level: string;
  experience_required: string;
  languages: string[];
  tools: string[];
  certifications: string[];
  interview_criteria: string[];
  suggestion_sources: string[];
}

interface Announcement {
  title: string;
  slug: string;
  public_url: string;
  web_body: string;
  email_subject: string;
  email_body: string;
  facebook_text: string;
  linkedin_text: string;
  whatsapp_text: string;
  copy_text: string;
}

interface RecruitmentActivity {
  id: number;
  event_type: string;
  message: string;
  created_at: string;
}

interface RecruitmentInterview {
  id: number;
  round_label: string;
  scheduled_at: string | null;
  status: string;
  recommendation: string | null;
  score_total: number | null;
  notes: string | null;
}

const shellCard =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClass =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClass = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";

const splitValues = (value: string) =>
  value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

const joinValues = (values: string[] | null | undefined) => (values || []).join("\n");

const emptyDraft = {
  title: "",
  department: "",
  location: "",
  contract_type: "CDI",
  status: "draft",
  salary_range: "",
  description: "",
  skills_required: "",
  manager_title: "",
  mission_summary: "",
  main_activities: "",
  technical_skills: "",
  behavioral_skills: "",
  education_level: "",
  experience_required: "",
  languages: "",
  tools: "",
  certifications: "",
  salary_min: "",
  salary_max: "",
  working_hours: "",
  benefits: "",
  desired_start_date: "",
  application_deadline: "",
  publication_channels: "E-mail\nLinkedIn\nPDF",
  classification: "",
  interview_criteria: "",
  validation_comment: "",
};

export default function Recruitment() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [selectedApplicationId, setSelectedApplicationId] = useState<number | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [suggestionSources, setSuggestionSources] = useState<string[]>([]);
  const [announcementPreview, setAnnouncementPreview] = useState<Announcement | null>(null);
  const [candidateForm, setCandidateForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    education_level: "",
    experience_years: "0",
    source: "",
    summary: "",
  });
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [interviewForm, setInterviewForm] = useState({
    round_label: "Tour 1",
    scheduled_at: "",
    interviewer_name: "",
    notes: "",
    recommendation: "advance",
    score_total: "",
  });
  const [decisionForm, setDecisionForm] = useState({
    shortlist_rank: "",
    decision_status: "offer_sent",
    decision_comment: "",
  });

  const { data: employers = [] } = useQuery({
    queryKey: ["recruitment", "employers"],
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  useEffect(() => {
    if (!selectedEmployerId && employers.length > 0) {
      setSelectedEmployerId(employers[0].id);
    }
  }, [employers, selectedEmployerId]);

  const { data: jobs = [], isLoading: isLoadingJobs } = useQuery({
    queryKey: ["recruitment", "jobs", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (await api.get<JobPosting[]>("/recruitment/jobs", { params: { employer_id: selectedEmployerId } })).data,
  });

  const { data: candidates = [] } = useQuery({
    queryKey: ["recruitment", "candidates", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (await api.get<Candidate[]>("/recruitment/candidates", { params: { employer_id: selectedEmployerId } })).data,
  });

  const { data: applications = [] } = useQuery({
    queryKey: ["recruitment", "applications", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (await api.get<Application[]>("/recruitment/applications", { params: { employer_id: selectedEmployerId } })).data,
  });

  const { data: profile } = useQuery({
    queryKey: ["recruitment", "profile", selectedJobId],
    enabled: selectedJobId !== null,
    queryFn: async () => (await api.get<JobProfile>(`/recruitment/jobs/${selectedJobId}/profile`)).data,
  });

  const { data: activities = [] } = useQuery({
    queryKey: ["recruitment", "activities", selectedApplicationId],
    enabled: selectedApplicationId !== null,
    queryFn: async () => (await api.get<RecruitmentActivity[]>(`/recruitment/applications/${selectedApplicationId}/activities`)).data,
  });

  const { data: interviews = [] } = useQuery({
    queryKey: ["recruitment", "interviews", selectedApplicationId],
    enabled: selectedApplicationId !== null,
    queryFn: async () => (await api.get<RecruitmentInterview[]>(`/recruitment/applications/${selectedApplicationId}/interviews`)).data,
  });

  useEffect(() => {
    if (!selectedJobId && jobs.length > 0) {
      setSelectedJobId(jobs[0].id);
    }
  }, [jobs, selectedJobId]);

  useEffect(() => {
    if (!selectedApplicationId && applications.length > 0) {
      setSelectedApplicationId(applications[0].id);
    }
  }, [applications, selectedApplicationId]);

  useEffect(() => {
    const job = jobs.find((item) => item.id === selectedJobId);
    if (!job) {
      setDraft(emptyDraft);
      setAnnouncementPreview(null);
      return;
    }
    setDraft({
      title: job.title || "",
      department: job.department || "",
      location: job.location || "",
      contract_type: job.contract_type || "CDI",
      status: job.status || "draft",
      salary_range: job.salary_range || "",
      description: job.description || "",
      skills_required: job.skills_required || "",
      manager_title: profile?.manager_title || "",
      mission_summary: profile?.mission_summary || "",
      main_activities: joinValues(profile?.main_activities),
      technical_skills: joinValues(profile?.technical_skills),
      behavioral_skills: joinValues(profile?.behavioral_skills),
      education_level: profile?.education_level || "",
      experience_required: profile?.experience_required || "",
      languages: joinValues(profile?.languages),
      tools: joinValues(profile?.tools),
      certifications: joinValues(profile?.certifications),
      salary_min: profile?.salary_min?.toString() || "",
      salary_max: profile?.salary_max?.toString() || "",
      working_hours: profile?.working_hours || "",
      benefits: joinValues(profile?.benefits),
      desired_start_date: profile?.desired_start_date || "",
      application_deadline: profile?.application_deadline || "",
      publication_channels: joinValues(profile?.publication_channels),
      classification: profile?.classification || "",
      interview_criteria: joinValues(profile?.interview_criteria),
      validation_comment: profile?.validation_comment || "",
    });
    const sharePack = profile?.announcement_share_pack as Announcement | undefined;
    setAnnouncementPreview(sharePack?.title ? sharePack : null);
  }, [jobs, profile, selectedJobId]);

  const selectedJobApplications = useMemo(
    () => applications.filter((item) => !selectedJobId || item.job_posting_id === selectedJobId),
    [applications, selectedJobId],
  );

  const invalidateRecruitment = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["recruitment", "jobs"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "candidates"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "applications"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "profile"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "activities"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "interviews"] }),
    ]);
  };

  const suggestMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post<Suggestion>("/recruitment/job-assistant/suggest", {
          employer_id: selectedEmployerId,
          title: draft.title,
          department: draft.department,
          description: `${draft.description}\n${draft.skills_required}`,
        })
      ).data,
    onSuccess: (data) => {
      setDraft((current) => ({
        ...current,
        title: current.title || data.probable_title,
        department: current.department || data.probable_department,
        mission_summary: current.mission_summary || data.mission_summary,
        main_activities: current.main_activities || joinValues(data.main_activities),
        technical_skills: current.technical_skills || joinValues(data.technical_skills),
        behavioral_skills: current.behavioral_skills || joinValues(data.behavioral_skills),
        education_level: current.education_level || data.education_level,
        experience_required: current.experience_required || data.experience_required,
        languages: current.languages || joinValues(data.languages),
        tools: current.tools || joinValues(data.tools),
        certifications: current.certifications || joinValues(data.certifications),
        interview_criteria: current.interview_criteria || joinValues(data.interview_criteria),
      }));
      setSuggestionSources(data.suggestion_sources);
      toast.success("Suggestions appliquées", "Toutes les propositions restent librement modifiables.");
    },
    onError: () => toast.error("Assistant indisponible", "Impossible de générer les suggestions pour cette fiche."),
  });

  const saveJobMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEmployerId) throw new Error("Employeur requis");
      const jobPayload = {
        employer_id: selectedEmployerId,
        title: draft.title,
        department: draft.department || null,
        location: draft.location || null,
        contract_type: draft.contract_type,
        status: draft.status,
        salary_range: draft.salary_range || null,
        description: draft.description || null,
        skills_required: draft.skills_required || null,
      };
      const job = selectedJobId
        ? (await api.put<JobPosting>(`/recruitment/jobs/${selectedJobId}`, jobPayload)).data
        : (await api.post<JobPosting>("/recruitment/jobs", jobPayload)).data;
      const profilePayload = {
        manager_title: draft.manager_title || null,
        mission_summary: draft.mission_summary || null,
        main_activities: splitValues(draft.main_activities),
        technical_skills: splitValues(draft.technical_skills),
        behavioral_skills: splitValues(draft.behavioral_skills),
        education_level: draft.education_level || null,
        experience_required: draft.experience_required || null,
        languages: splitValues(draft.languages),
        tools: splitValues(draft.tools),
        certifications: splitValues(draft.certifications),
        salary_min: draft.salary_min ? Number(draft.salary_min) : null,
        salary_max: draft.salary_max ? Number(draft.salary_max) : null,
        working_hours: draft.working_hours || null,
        benefits: splitValues(draft.benefits),
        desired_start_date: draft.desired_start_date || null,
        application_deadline: draft.application_deadline || null,
        publication_channels: splitValues(draft.publication_channels),
        classification: draft.classification || null,
        workflow_status: draft.status === "published" ? "validated" : "draft",
        validation_comment: draft.validation_comment || null,
        assistant_source: { suggestion_sources: suggestionSources },
        interview_criteria: splitValues(draft.interview_criteria),
        announcement_title: announcementPreview?.title || null,
        announcement_body: announcementPreview?.web_body || null,
        announcement_status: profile?.announcement_status || "draft",
        announcement_share_pack: announcementPreview || {},
      };
      await api.put(`/recruitment/jobs/${job.id}/profile`, profilePayload);
      return job;
    },
    onSuccess: async (job) => {
      setSelectedJobId(job.id);
      await invalidateRecruitment();
      toast.success("Fiche enregistrée", "La fiche de poste et son profil ont été sauvegardés.");
    },
    onError: (error) => toast.error("Enregistrement impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const submitValidationMutation = useMutation({
    mutationFn: async () => api.post(`/recruitment/jobs/${selectedJobId}/submit-for-validation`),
    onSuccess: async () => {
      await invalidateRecruitment();
      toast.success("Validation demandée", "La fiche a été transmise au circuit de validation RH.");
    },
  });

  const generateAnnouncementMutation = useMutation({
    mutationFn: async () => (await api.post<Announcement>(`/recruitment/jobs/${selectedJobId}/generate-announcement`)).data,
    onSuccess: (data) => {
      setAnnouncementPreview(data);
      toast.success("Annonce générée", "Les variantes e-mail, LinkedIn, Facebook et PDF sont prêtes.");
    },
  });

  const publishMutation = useMutation({
    mutationFn: async () => api.post(`/recruitment/jobs/${selectedJobId}/publish`),
    onSuccess: async () => {
      await invalidateRecruitment();
      toast.success("Annonce publiée", "Le poste est maintenant prêt à être diffusé.");
    },
  });

  const uploadCandidateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEmployerId || !cvFile) throw new Error("Employeur et CV requis");
      const formData = new FormData();
      formData.append("employer_id", selectedEmployerId.toString());
      formData.append("first_name", candidateForm.first_name);
      formData.append("last_name", candidateForm.last_name);
      formData.append("email", candidateForm.email);
      formData.append("phone", candidateForm.phone);
      formData.append("education_level", candidateForm.education_level);
      formData.append("experience_years", candidateForm.experience_years);
      formData.append("source", candidateForm.source);
      formData.append("summary", candidateForm.summary);
      if (selectedJobId) formData.append("job_posting_id", selectedJobId.toString());
      formData.append("cv_file", cvFile);
      attachments.forEach((file) => formData.append("attachments", file));
      await api.post("/recruitment/candidates/upload", formData, { headers: { "Content-Type": "multipart/form-data" } });
    },
    onSuccess: async () => {
      setCandidateForm({ first_name: "", last_name: "", email: "", phone: "", education_level: "", experience_years: "0", source: "", summary: "" });
      setCvFile(null);
      setAttachments([]);
      await invalidateRecruitment();
      toast.success("Candidature reçue", "Le CV original, les pièces et la candidature ont été enregistrés.");
    },
    onError: (error) => toast.error("Dépôt impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const createInterviewMutation = useMutation({
    mutationFn: async () =>
      api.post(`/recruitment/applications/${selectedApplicationId}/interviews`, {
        round_label: interviewForm.round_label,
        scheduled_at: interviewForm.scheduled_at || null,
        interviewer_name: interviewForm.interviewer_name || null,
        notes: interviewForm.notes || null,
        recommendation: interviewForm.recommendation,
        score_total: interviewForm.score_total ? Number(interviewForm.score_total) : null,
      }),
    onSuccess: async () => {
      setInterviewForm({ round_label: "Tour 1", scheduled_at: "", interviewer_name: "", notes: "", recommendation: "advance", score_total: "" });
      await invalidateRecruitment();
      toast.success("Entretien planifié", "Le tour d'entretien a été ajouté au dossier.");
    },
  });

  const decisionMutation = useMutation({
    mutationFn: async () =>
      api.post(`/recruitment/applications/${selectedApplicationId}/decision`, {
        shortlist_rank: decisionForm.shortlist_rank ? Number(decisionForm.shortlist_rank) : null,
        decision_status: decisionForm.decision_status,
        decision_comment: decisionForm.decision_comment || null,
      }),
    onSuccess: async () => {
      await invalidateRecruitment();
      toast.success("Décision enregistrée", "La shortlist ou la décision finale a été tracée.");
    },
  });

  const convertMutation = useMutation({
    mutationFn: async () => api.post(`/recruitment/applications/${selectedApplicationId}/convert-to-worker`),
    onSuccess: async () => {
      await invalidateRecruitment();
      toast.success("Conversion effectuée", "Le candidat est devenu salarié et un brouillon de contrat a été créé.");
    },
  });

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(14,116,144,0.88),rgba(8,145,178,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Recrutement complet
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Fiche de poste assistée, annonce, candidatures et décision</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Le système suggère, mais ne bloque jamais. Chaque proposition reste éditable avant validation, publication et conversion candidat vers salarié.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4"><div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Postes</div><div className="mt-3 text-3xl font-semibold text-white">{jobs.length}</div></div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4"><div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Candidats</div><div className="mt-3 text-3xl font-semibold text-white">{candidates.length}</div></div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4"><div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Candidatures</div><div className="mt-3 text-3xl font-semibold text-white">{applications.length}</div></div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.95fr]">
        <div className={shellCard}>
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-white">Fiche de poste</h2>
              <p className="mt-1 text-sm text-slate-400">Assistance intelligente modifiable, workflow de validation et génération d’annonce.</p>
            </div>
            <div className="flex items-center gap-3">
              <select value={selectedEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClass}>
                {employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.raison_sociale}</option>)}
              </select>
              <select value={selectedJobId ?? ""} onChange={(event) => setSelectedJobId(Number(event.target.value) || null)} className={inputClass}>
                <option value="">Nouveau poste</option>
                {jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
              </select>
            </div>
          </div>

          {isLoadingJobs ? <div className="mt-6 h-48 animate-pulse rounded-3xl bg-slate-900/70" /> : null}

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div><label className={labelClass}>Intitulé</label><input value={draft.title} onChange={(e) => setDraft((c) => ({ ...c, title: e.target.value }))} className={inputClass} placeholder="Responsable paie" /></div>
            <div><label className={labelClass}>Département / Service</label><input value={draft.department} onChange={(e) => setDraft((c) => ({ ...c, department: e.target.value }))} className={inputClass} placeholder="Ressources humaines" /></div>
            <div><label className={labelClass}>Localisation</label><input value={draft.location} onChange={(e) => setDraft((c) => ({ ...c, location: e.target.value }))} className={inputClass} placeholder="Antananarivo" /></div>
            <div><label className={labelClass}>Responsable hiérarchique</label><input value={draft.manager_title} onChange={(e) => setDraft((c) => ({ ...c, manager_title: e.target.value }))} className={inputClass} placeholder="DRH" /></div>
            <div><label className={labelClass}>Type de contrat</label><input value={draft.contract_type} onChange={(e) => setDraft((c) => ({ ...c, contract_type: e.target.value }))} className={inputClass} placeholder="CDI" /></div>
            <div><label className={labelClass}>Classification / Indice</label><input value={draft.classification} onChange={(e) => setDraft((c) => ({ ...c, classification: e.target.value }))} className={inputClass} placeholder="Cadre C2" /></div>
            <div className="md:col-span-2"><label className={labelClass}>Description libre du besoin</label><textarea value={draft.description} onChange={(e) => setDraft((c) => ({ ...c, description: e.target.value }))} className={`${inputClass} min-h-[88px]`} placeholder="Décrivez le besoin métier, l’environnement, les enjeux et le profil recherché." /></div>
            <div className="md:col-span-2"><label className={labelClass}>Mission principale</label><textarea value={draft.mission_summary} onChange={(e) => setDraft((c) => ({ ...c, mission_summary: e.target.value }))} className={`${inputClass} min-h-[80px]`} /></div>
            <div><label className={labelClass}>Activités principales</label><textarea value={draft.main_activities} onChange={(e) => setDraft((c) => ({ ...c, main_activities: e.target.value }))} className={`${inputClass} min-h-[120px]`} placeholder="Une activité par ligne" /></div>
            <div><label className={labelClass}>Compétences techniques</label><textarea value={draft.technical_skills} onChange={(e) => setDraft((c) => ({ ...c, technical_skills: e.target.value }))} className={`${inputClass} min-h-[120px]`} placeholder="Une compétence par ligne" /></div>
            <div><label className={labelClass}>Compétences comportementales</label><textarea value={draft.behavioral_skills} onChange={(e) => setDraft((c) => ({ ...c, behavioral_skills: e.target.value }))} className={`${inputClass} min-h-[120px]`} /></div>
            <div><label className={labelClass}>Outils / logiciels / certifications</label><textarea value={`${draft.tools}${draft.certifications ? `\n${draft.certifications}` : ""}`} onChange={(e) => setDraft((c) => ({ ...c, tools: e.target.value, certifications: "" }))} className={`${inputClass} min-h-[120px]`} /></div>
            <div><label className={labelClass}>Langues</label><textarea value={draft.languages} onChange={(e) => setDraft((c) => ({ ...c, languages: e.target.value }))} className={`${inputClass} min-h-[90px]`} /></div>
            <div><label className={labelClass}>Critères d’entretien pondérables</label><textarea value={draft.interview_criteria} onChange={(e) => setDraft((c) => ({ ...c, interview_criteria: e.target.value }))} className={`${inputClass} min-h-[90px]`} /></div>
            <div><label className={labelClass}>Niveau d’études</label><input value={draft.education_level} onChange={(e) => setDraft((c) => ({ ...c, education_level: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Expérience requise</label><input value={draft.experience_required} onChange={(e) => setDraft((c) => ({ ...c, experience_required: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Salaire minimum</label><input value={draft.salary_min} onChange={(e) => setDraft((c) => ({ ...c, salary_min: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Salaire maximum</label><input value={draft.salary_max} onChange={(e) => setDraft((c) => ({ ...c, salary_max: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Date souhaitée</label><input type="date" value={draft.desired_start_date} onChange={(e) => setDraft((c) => ({ ...c, desired_start_date: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Date limite candidature</label><input type="date" value={draft.application_deadline} onChange={(e) => setDraft((c) => ({ ...c, application_deadline: e.target.value }))} className={inputClass} /></div>
            <div className="md:col-span-2"><label className={labelClass}>Canaux de publication / avantages / horaires</label><textarea value={[draft.publication_channels, draft.benefits, draft.working_hours].filter(Boolean).join("\n")} onChange={(e) => setDraft((c) => ({ ...c, publication_channels: e.target.value, benefits: "", working_hours: "" }))} className={`${inputClass} min-h-[88px]`} placeholder="Ex: LinkedIn, E-mail, PDF, 40h/semaine, assurance santé" /></div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={() => suggestMutation.mutate()} className="inline-flex items-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950"><SparklesIcon className="h-5 w-5" />Suggérer la fiche</button>
            <button type="button" onClick={() => saveJobMutation.mutate()} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white">Enregistrer</button>
            <button type="button" onClick={() => submitValidationMutation.mutate()} disabled={!selectedJobId} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Soumettre</button>
            <button type="button" onClick={() => generateAnnouncementMutation.mutate()} disabled={!selectedJobId} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Générer l’annonce</button>
            <button type="button" onClick={() => publishMutation.mutate()} disabled={!selectedJobId} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-5 py-3 text-sm font-semibold text-emerald-100 disabled:opacity-40"><CheckBadgeIcon className="h-5 w-5" />Publier</button>
          </div>
          {suggestionSources.length > 0 ? <div className="mt-4 text-sm text-cyan-200">Sources de suggestion: {suggestionSources.join(", ")}</div> : null}
        </div>

        <div className="space-y-6">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Annonce multicanale</h2>
            <p className="mt-1 text-sm text-slate-400">Une seule source de vérité pour web, e-mail, LinkedIn, Facebook et PDF.</p>
            {announcementPreview ? (
              <div className="mt-5 space-y-4 text-sm text-slate-200">
                <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-5">
                  <div className="text-lg font-semibold text-white">{announcementPreview.title}</div>
                  <div className="mt-2 whitespace-pre-wrap text-slate-300">{announcementPreview.web_body}</div>
                </div>
                <div className="grid gap-3">
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4"><div className="font-semibold text-cyan-200">E-mail</div><div className="mt-2 whitespace-pre-wrap">{announcementPreview.email_body}</div></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4"><div className="font-semibold text-cyan-200">LinkedIn</div><div className="mt-2 whitespace-pre-wrap">{announcementPreview.linkedin_text}</div></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4"><div className="font-semibold text-cyan-200">Facebook</div><div className="mt-2 whitespace-pre-wrap">{announcementPreview.facebook_text}</div></div>
                </div>
              </div>
            ) : <div className="mt-5 rounded-3xl border border-dashed border-white/10 p-6 text-sm text-slate-400">Générez une annonce pour prévisualiser le texte public et les variantes de partage.</div>}
          </div>

          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Dépôt de candidature structuré</h2>
            <div className="mt-5 grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <input value={candidateForm.first_name} onChange={(e) => setCandidateForm((c) => ({ ...c, first_name: e.target.value }))} className={inputClass} placeholder="Prénom" />
                <input value={candidateForm.last_name} onChange={(e) => setCandidateForm((c) => ({ ...c, last_name: e.target.value }))} className={inputClass} placeholder="Nom" />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <input value={candidateForm.email} onChange={(e) => setCandidateForm((c) => ({ ...c, email: e.target.value }))} className={inputClass} placeholder="Email" />
                <input value={candidateForm.phone} onChange={(e) => setCandidateForm((c) => ({ ...c, phone: e.target.value }))} className={inputClass} placeholder="Téléphone" />
              </div>
              <textarea value={candidateForm.summary} onChange={(e) => setCandidateForm((c) => ({ ...c, summary: e.target.value }))} className={`${inputClass} min-h-[90px]`} placeholder="Résumé candidat ou note recruteur" />
              <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(e) => setCvFile(e.target.files?.[0] || null)} className={inputClass} />
              <input type="file" multiple onChange={(e) => setAttachments(Array.from(e.target.files || []))} className={inputClass} />
              <button type="button" onClick={() => uploadCandidateMutation.mutate()} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950"><UserPlusIcon className="h-5 w-5" />Déposer CV + pièces</button>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className={shellCard}>
          <div className="flex items-center gap-3">
            <UsersIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Pipeline candidat</h2>
              <p className="text-sm text-slate-400">Shortlist triable, entretiens multi-tours, score et décision.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            {selectedJobApplications.map((application) => {
              const candidate = candidates.find((item) => item.id === application.candidate_id);
              const isActive = application.id === selectedApplicationId;
              return (
                <button
                  key={application.id}
                  type="button"
                  onClick={() => setSelectedApplicationId(application.id)}
                  className={`rounded-3xl border px-4 py-4 text-left transition ${isActive ? "border-cyan-400/40 bg-cyan-400/10" : "border-white/10 bg-slate-900/70 hover:border-white/20"}`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-semibold text-white">{candidate ? `${candidate.first_name} ${candidate.last_name}` : `Candidat #${application.candidate_id}`}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.22em] text-slate-400">{application.stage}</div>
                    </div>
                    <div className="text-sm text-cyan-200">{application.score ?? "n/a"}</div>
                  </div>
                </button>
              );
            })}
            {selectedJobApplications.length === 0 ? <div className="rounded-3xl border border-dashed border-white/10 p-6 text-sm text-slate-400">Aucune candidature liée à ce poste pour le moment.</div> : null}
          </div>
        </div>

        <div className="space-y-6">
          <div className={shellCard}>
            <div className="flex items-center gap-3">
              <DocumentTextIcon className="h-6 w-6 text-cyan-300" />
              <div>
                <h2 className="text-xl font-semibold text-white">Journal et entretiens</h2>
                <p className="text-sm text-slate-400">Historique tracé, entretiens planifiés et recommandations.</p>
              </div>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <input value={interviewForm.round_label} onChange={(e) => setInterviewForm((c) => ({ ...c, round_label: e.target.value }))} className={inputClass} placeholder="Tour 1" />
              <input type="datetime-local" value={interviewForm.scheduled_at} onChange={(e) => setInterviewForm((c) => ({ ...c, scheduled_at: e.target.value }))} className={inputClass} />
              <input value={interviewForm.interviewer_name} onChange={(e) => setInterviewForm((c) => ({ ...c, interviewer_name: e.target.value }))} className={inputClass} placeholder="Intervieweur" />
              <input value={interviewForm.score_total} onChange={(e) => setInterviewForm((c) => ({ ...c, score_total: e.target.value }))} className={inputClass} placeholder="Score total" />
              <textarea value={interviewForm.notes} onChange={(e) => setInterviewForm((c) => ({ ...c, notes: e.target.value }))} className={`${inputClass} min-h-[90px] md:col-span-2`} placeholder="Notes, objections, points forts, signaux faibles" />
              <button type="button" disabled={!selectedApplicationId} onClick={() => createInterviewMutation.mutate()} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Planifier un entretien</button>
            </div>
            <div className="mt-6 space-y-3">
              {interviews.map((interview) => (
                <div key={interview.id} className="rounded-2xl border border-white/10 bg-slate-900/70 p-4 text-sm text-slate-300">
                  <div className="flex items-center justify-between gap-3"><div className="font-semibold text-white">{interview.round_label}</div><div>{interview.status}</div></div>
                  <div className="mt-2">{interview.scheduled_at || "Date à confirmer"}</div>
                  <div className="mt-2 text-cyan-200">{interview.recommendation || "Aucune recommandation"}</div>
                </div>
              ))}
              {activities.slice(0, 5).map((activity) => (
                <div key={activity.id} className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 text-sm text-slate-300">
                  <div className="font-semibold text-white">{activity.message}</div>
                  <div className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">{new Date(activity.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>

          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Décision finale et onboarding</h2>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <input value={decisionForm.shortlist_rank} onChange={(e) => setDecisionForm((c) => ({ ...c, shortlist_rank: e.target.value }))} className={inputClass} placeholder="Rang shortlist" />
              <select value={decisionForm.decision_status} onChange={(e) => setDecisionForm((c) => ({ ...c, decision_status: e.target.value }))} className={inputClass}>
                <option value="offer_sent">Promesse envoyée</option>
                <option value="offer_accepted">Promesse acceptée</option>
                <option value="rejected">Rejet</option>
              </select>
              <textarea value={decisionForm.decision_comment} onChange={(e) => setDecisionForm((c) => ({ ...c, decision_comment: e.target.value }))} className={`${inputClass} min-h-[90px] md:col-span-2`} placeholder="Motivation de décision, réserves, prochaine étape" />
              <button type="button" disabled={!selectedApplicationId} onClick={() => decisionMutation.mutate()} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Enregistrer la décision</button>
              <button type="button" disabled={!selectedApplicationId} onClick={() => convertMutation.mutate()} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40"><CheckBadgeIcon className="h-5 w-5" />Convertir en salarié</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
