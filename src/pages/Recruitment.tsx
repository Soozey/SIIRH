import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  CheckBadgeIcon,
  DocumentTextIcon,
  SparklesIcon,
  UserPlusIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";

import { api, downloadRecruitmentImportTemplate, importRecruitmentResource, type TabularImportReport } from "../api";
import HelpTooltip from "../components/help/HelpTooltip";
import { getContextHelp } from "../help/helpContent";
import { useToast } from "../components/ui/ToastProvider";
import { useAuth } from "../contexts/AuthContext";
import { sessionHasRole } from "../rbac";


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
  publish_channels: string[];
  publish_status: string;
  publish_logs: Array<{ id?: number; channel: string; status: string; message?: string | null; timestamp?: string | null }>;
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
  workforce_job_profile_id: number | null;
  contract_guidance: ContractGuidance | Record<string, never>;
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
  working_days: string[];
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

interface ContractGuidance {
  suggested_primary_type: string;
  available_types: string[];
  language_options: string[];
  required_fields: string[];
  alerts: Array<{ severity: string; code: string; message: string }>;
  recommendations: string[];
  suggested_defaults: Record<string, unknown>;
}

interface Suggestion {
  probable_title: string;
  probable_department: string;
  detected_job_family: string;
  generated_context: string;
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
  classification: string;
  contract_type_suggestions: Array<{ code: string; label: string; description: string; recommended: boolean }>;
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
  interview_type: string;
  scheduled_at: string | null;
  interviewer_name: string | null;
  status: string;
  recommendation: string | null;
  score_total: number | null;
  notes: string | null;
}

interface RecruitmentLibraryItem {
  id: number;
  category: string;
  label: string;
  description: string | null;
  payload?: Record<string, unknown>;
}

interface PublicationChannel {
  id: number;
  company_id: number;
  channel_type: "facebook" | "linkedin" | "site_interne" | "email" | "api_externe";
  is_active: boolean;
  default_publish: boolean;
  config: Record<string, unknown>;
  secret_fields_configured: string[];
}

interface PublicationLog {
  id: number;
  job_id: number;
  channel: string;
  status: string;
  message: string | null;
  details: Record<string, unknown>;
  triggered_by_user_id: number | null;
  timestamp: string;
}

interface PublishResult {
  job: JobPosting;
  profile: JobProfile;
  channel_results: PublicationLog[];
}

interface WorkerSummary {
  id: number;
}

interface WorkforceJobProfile {
  id: number;
  employer_id: number;
  title: string;
  department?: string | null;
  category_prof?: string | null;
  classification_index?: string | null;
  notes?: string | null;
  required_skills: Array<{ type?: string; label?: string }>;
}

interface MasterHealth {
  employer_id: number;
  sample_size: number;
  workers_with_issues: number;
  items: Array<{ worker: { id: number; matricule?: string | null; nom?: string | null; prenom?: string | null }; integrity_issues: Array<{ message: string }> }>;
}

interface ClassificationOption {
  code: string;
  display: string;
  label: string;
  family: string;
  group?: number;
  description: string;
}

const shellCard =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClass =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClass = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";
const defaultContractTypeSuggestions = [
  "CDI",
  "CDD",
  "Contrat d'essai",
  "Contrat d'apprentissage",
  "Contrat saisonnier",
  "Contrat occasionnel",
  "Travail interimaire",
  "Portage salarial",
  "Travailleur migrant / expatrie",
];

const splitValues = (value: string) =>
  value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

const joinValues = (values: string[] | null | undefined) => (values || []).join("\n");
const uniqueValues = (values: Array<string | null | undefined>) =>
  Array.from(new Set(values.map((item) => (item || "").trim()).filter(Boolean)));
const buildSelectValues = (options: string[], currentValue: string) =>
  uniqueValues([...options, currentValue]);
const publicationChannelLabels: Record<string, string> = {
  facebook: "Facebook",
  linkedin: "LinkedIn",
  site_interne: "Site interne",
  email: "E-mail",
  api_externe: "API externe",
};

const publicationStatusLabels: Record<string, string> = {
  draft: "Draft",
  published: "Publié",
  partial: "Partiel",
  failed: "Erreur",
  publication_failed: "Erreur",
};

const publicationStatusClasses: Record<string, string> = {
  draft: "border-white/10 bg-white/5 text-slate-200",
  published: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
  partial: "border-amber-400/30 bg-amber-400/10 text-amber-100",
  failed: "border-rose-400/30 bg-rose-400/10 text-rose-100",
  publication_failed: "border-rose-400/30 bg-rose-400/10 text-rose-100",
};

const normalizeClassificationValue = (value: string) => value.trim().toLowerCase();

const parseClassificationOption = (item: RecruitmentLibraryItem): ClassificationOption => {
  const payload = item.payload ?? {};
  const payloadCode = typeof payload.code === "string" ? payload.code.trim() : "";
  const fallbackCode = item.label.includes(" - ") ? item.label.split(" - ")[0].trim() : item.label.trim();
  const code = payloadCode || fallbackCode;
  const label = typeof payload.label === "string" ? payload.label.trim() : item.label.replace(`${code} -`, "").trim();
  const family = typeof payload.family === "string" ? payload.family : "";
  const group = typeof payload.group === "number" ? payload.group : undefined;
  const description = typeof payload.description === "string" ? payload.description : item.description || "";
  const display = code && label ? `${code} - ${label}` : item.label;
  return { code, display, label, family, group, description };
};

const resolveClassificationCode = (
  value: string,
  options: ClassificationOption[],
): string => {
  const normalized = normalizeClassificationValue(value);
  if (!normalized) return "";
  const match = options.find(
    (option) =>
      normalizeClassificationValue(option.code) === normalized ||
      normalizeClassificationValue(option.display) === normalized ||
      normalizeClassificationValue(option.label) === normalized,
  );
  return match ? match.code : value.trim();
};

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
  working_days: "",
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
  const { session } = useAuth();
  const recruitmentContractHelp = getContextHelp("recruitment", "contract_type");
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [selectedApplicationId, setSelectedApplicationId] = useState<number | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [suggestionSources, setSuggestionSources] = useState<string[]>([]);
  const [assistantSuggestion, setAssistantSuggestion] = useState<Suggestion | null>(null);
  const [assistantVersion, setAssistantVersion] = useState<"short" | "long">("long");
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
  const [jobAttachment, setJobAttachment] = useState<File | null>(null);
  const [selectedWorkforceProfileId, setSelectedWorkforceProfileId] = useState<number | null>(null);
  const [interviewForm, setInterviewForm] = useState({
    round_label: "Entretien RH",
    interview_type: "Entretien RH",
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
  const [importResource, setImportResource] = useState<"candidates" | "jobs">("candidates");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importReport, setImportReport] = useState<TabularImportReport | null>(null);
  const [jobPublishChannels, setJobPublishChannels] = useState<string[]>([]);
  const canManagePublication = sessionHasRole(session, ["admin", "rh", "recrutement"]);

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

  const { data: workers = [] } = useQuery({
    queryKey: ["recruitment", "workers", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (await api.get<WorkerSummary[]>("/workers", { params: { employer_id: selectedEmployerId } })).data,
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

  const { data: libraryItems = [] } = useQuery({
    queryKey: ["recruitment", "library-items", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () =>
      (
        await api.get<RecruitmentLibraryItem[]>("/recruitment/library-items", {
          params: { employer_id: selectedEmployerId },
        })
      ).data,
  });

  const { data: masterHealth } = useQuery({
    queryKey: ["recruitment", "master-health", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (await api.get<MasterHealth>(`/master-data/employers/${selectedEmployerId}/health`, { params: { sample_limit: 20 } })).data,
  });

  const { data: workforceProfiles = [] } = useQuery({
    queryKey: ["recruitment", "workforce-profiles", selectedEmployerId],
    enabled: selectedEmployerId !== null,
    queryFn: async () => (await api.get<WorkforceJobProfile[]>("/people-ops/job-profiles", { params: { employer_id: selectedEmployerId } })).data,
  });

  const { data: contractGuidance } = useQuery({
    queryKey: ["recruitment", "contract-guidance", selectedJobId],
    enabled: selectedJobId !== null,
    queryFn: async () => (await api.get<ContractGuidance>(`/recruitment/jobs/${selectedJobId}/contract-guidance`)).data,
  });

  const { data: publicationChannels = [] } = useQuery({
    queryKey: ["recruitment", "publication-channels", selectedEmployerId],
    enabled: selectedEmployerId !== null && canManagePublication,
    queryFn: async () =>
      (await api.get<PublicationChannel[]>("/recruitment/publication-channels", { params: { employer_id: selectedEmployerId } })).data,
  });

  const { data: publicationLogs = [] } = useQuery({
    queryKey: ["recruitment", "publication-logs", selectedJobId],
    enabled: selectedJobId !== null,
    queryFn: async () => (await api.get<PublicationLog[]>(`/recruitment/jobs/${selectedJobId}/publication-logs`)).data,
  });

  const libraryValuesByCategory = useMemo(() => {
    const values: Record<string, string[]> = {};
    libraryItems.forEach((item) => {
      if (!values[item.category]) values[item.category] = [];
      values[item.category].push(item.label);
    });
    return values;
  }, [libraryItems]);

  const classificationOptions = useMemo(
    () =>
      libraryItems
        .filter((item) => item.category === "professional_classification")
        .map(parseClassificationOption),
    [libraryItems],
  );

  const selectedClassification = useMemo(() => {
    const normalized = normalizeClassificationValue(draft.classification);
    if (!normalized) return null;
    return (
      classificationOptions.find(
        (option) =>
          normalizeClassificationValue(option.code) === normalized ||
          normalizeClassificationValue(option.display) === normalized ||
          normalizeClassificationValue(option.label) === normalized,
      ) || null
    );
  }, [classificationOptions, draft.classification]);

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
      setSelectedWorkforceProfileId(null);
      setJobPublishChannels([]);
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
      working_days: joinValues(profile?.working_days),
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
    setSelectedWorkforceProfileId(profile?.workforce_job_profile_id ?? null);
    setJobPublishChannels(Array.isArray(job.publish_channels) ? job.publish_channels : []);
  }, [jobs, profile, selectedJobId]);

  const selectedJobApplications = useMemo(
    () => applications.filter((item) => !selectedJobId || item.job_posting_id === selectedJobId),
    [applications, selectedJobId],
  );

  const departmentSuggestions = libraryValuesByCategory.department ?? [];
  const locationSuggestions = libraryValuesByCategory.location ?? [];
  const contractTypeSuggestions = useMemo(
    () => Array.from(new Set([...(libraryValuesByCategory.contract_type ?? []), ...defaultContractTypeSuggestions])),
    [libraryValuesByCategory],
  );
  const educationLevelSuggestions = libraryValuesByCategory.education_level ?? [];
  const experienceLevelSuggestions = libraryValuesByCategory.experience_level ?? [];
  const candidateSourceSuggestions = libraryValuesByCategory.candidate_source ?? [];
  const jobTitleSuggestions = (libraryValuesByCategory.job_template ?? []).slice(0, 50);
  const benefitSuggestions = libraryValuesByCategory.benefit ?? [];
  const workingScheduleSuggestions = libraryValuesByCategory.working_schedule ?? [];
  const workingDaySuggestions = libraryValuesByCategory.working_days ?? [];
  const interviewStageSuggestions = libraryValuesByCategory.interview_stage ?? ["Entretien RH", "Entretien technique", "Entretien manager", "Entretien DG"];
  const linkedWorkforceProfile = workforceProfiles.find((item) => item.id === selectedWorkforceProfileId) || null;
  const activePublicationChannels = publicationChannels.filter((item) => item.is_active);
  const selectedJob = jobs.find((item) => item.id === selectedJobId) || null;
  const canSuggestTitleReference = !!draft.title.trim() && !jobTitleSuggestions.some((value) => value.toLowerCase() === draft.title.trim().toLowerCase());
  const canSuggestDepartmentReference = !!draft.department.trim() && !departmentSuggestions.some((value) => value.toLowerCase() === draft.department.trim().toLowerCase());
  const canSuggestLocationReference = !!draft.location.trim() && !locationSuggestions.some((value) => value.toLowerCase() === draft.location.trim().toLowerCase());
  const selectedApplication = selectedJobApplications.find((item) => item.id === selectedApplicationId) || null;
  const selectedCandidate = candidates.find((item) => item.id === selectedApplication?.candidate_id) || null;

  const invalidateRecruitment = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["recruitment", "jobs"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "candidates"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "applications"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "profile"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "contract-guidance"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "activities"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "interviews"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "publication-logs"] }),
      queryClient.invalidateQueries({ queryKey: ["recruitment", "publication-channels"] }),
    ]);
  };

  const suggestMutation = useMutation({
    mutationFn: async (params?: { mode?: "generate" | "improve" | "adapt"; focus_block?: string }) =>
      (
        await api.post<Suggestion>("/recruitment/job-assistant/suggest", {
          employer_id: selectedEmployerId,
          title: draft.title,
          department: draft.department,
          contract_type: draft.contract_type,
          description: `${draft.description}\n${draft.skills_required}`,
          sector: employers.find((item) => item.id === selectedEmployerId)?.raison_sociale || "",
          mode: params?.mode || "generate",
          version: assistantVersion,
          focus_block: params?.focus_block || null,
        })
      ).data,
    onSuccess: (data, params) => {
      const focusBlock = params?.focus_block;
      setAssistantSuggestion({
        ...data,
        main_activities: Array.isArray(data.main_activities) ? data.main_activities : [],
        technical_skills: Array.isArray(data.technical_skills) ? data.technical_skills : [],
        behavioral_skills: Array.isArray(data.behavioral_skills) ? data.behavioral_skills : [],
        languages: Array.isArray(data.languages) ? data.languages : [],
        tools: Array.isArray(data.tools) ? data.tools : [],
        certifications: Array.isArray(data.certifications) ? data.certifications : [],
        interview_criteria: Array.isArray(data.interview_criteria) ? data.interview_criteria : [],
        suggestion_sources: Array.isArray(data.suggestion_sources) ? data.suggestion_sources : [],
        contract_type_suggestions: Array.isArray(data.contract_type_suggestions) ? data.contract_type_suggestions : [],
      });
      setDraft((current) => ({
        ...current,
        title: !focusBlock && (!current.title || params?.mode === "adapt") ? data.probable_title : current.title,
        department: !focusBlock && (!current.department || params?.mode === "adapt") ? data.probable_department : current.department,
        contract_type: !focusBlock && Array.isArray(data.contract_type_suggestions) && data.contract_type_suggestions[0]?.label ? data.contract_type_suggestions[0].label : current.contract_type,
        description: !focusBlock || focusBlock === "description" ? data.generated_context : current.description,
        mission_summary: !focusBlock || focusBlock === "mission_summary" ? data.mission_summary : current.mission_summary,
        main_activities: !focusBlock || focusBlock === "main_activities" ? joinValues(data.main_activities) : current.main_activities,
        technical_skills: !focusBlock || focusBlock === "technical_skills" ? joinValues(data.technical_skills) : current.technical_skills,
        behavioral_skills: !focusBlock || focusBlock === "behavioral_skills" ? joinValues(data.behavioral_skills) : current.behavioral_skills,
        education_level: !focusBlock || focusBlock === "education_level" ? data.education_level : current.education_level,
        experience_required: !focusBlock || focusBlock === "experience_required" ? data.experience_required : current.experience_required,
        languages: !focusBlock || focusBlock === "languages" ? joinValues(data.languages) : current.languages,
        tools: !focusBlock || focusBlock === "tools" ? joinValues(data.tools) : current.tools,
        certifications: !focusBlock || focusBlock === "tools" ? joinValues(data.certifications) : current.certifications,
        interview_criteria: !focusBlock || focusBlock === "interview_criteria" ? joinValues(data.interview_criteria) : current.interview_criteria,
        classification: !focusBlock && !current.classification ? data.classification || "" : current.classification,
      }));
      setSuggestionSources(Array.isArray(data.suggestion_sources) ? data.suggestion_sources : []);
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
        publish_channels: jobPublishChannels,
        publish_status: selectedJob?.publish_status || "draft",
        publish_logs: selectedJob?.publish_logs || [],
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
        working_days: splitValues(draft.working_days),
        benefits: splitValues(draft.benefits),
        desired_start_date: draft.desired_start_date || null,
        application_deadline: draft.application_deadline || null,
        publication_channels: splitValues(draft.publication_channels),
        classification: draft.classification || null,
        workflow_status: draft.status === "published" ? (profile?.workflow_status || "published_non_validated") : (profile?.workflow_status || "draft"),
        validation_comment: draft.validation_comment || null,
        assistant_source: { suggestion_sources: suggestionSources },
        interview_criteria: splitValues(draft.interview_criteria),
        announcement_title: announcementPreview?.title || null,
        announcement_body: announcementPreview?.web_body || null,
        announcement_status: profile?.announcement_status || "draft",
        announcement_share_pack: announcementPreview || {},
        workforce_job_profile_id: selectedWorkforceProfileId,
        contract_guidance: contractGuidance || profile?.contract_guidance || {},
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
    mutationFn: async () =>
      (
        await api.post<PublishResult>(`/recruitment/jobs/${selectedJobId}/publish`, {
          channels: jobPublishChannels,
        })
      ).data,
    onSuccess: async (data) => {
      setJobPublishChannels(data.job.publish_channels || []);
      await invalidateRecruitment();
      const successCount = data.channel_results.filter((item) => item.status === "success").length;
      const failureCount = data.channel_results.filter((item) => item.status !== "success").length;
      toast.success("Publication terminée", `${successCount} canal(aux) OK${failureCount ? `, ${failureCount} en erreur` : ""}.`);
    },
    onError: (error) => toast.error("Publication impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const retryPublishMutation = useMutation({
    mutationFn: async (channel: string) =>
      (
        await api.post<PublishResult>(`/recruitment/jobs/${selectedJobId}/publish/retry`, {
          channel,
        })
      ).data,
    onSuccess: async (_, channel) => {
      await invalidateRecruitment();
      toast.success("Relance effectuée", `Nouvelle tentative sur ${publicationChannelLabels[channel] || channel}.`);
    },
    onError: (error) => toast.error("Relance impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const uploadJobAttachmentMutation = useMutation({
    mutationFn: async () => {
      if (!selectedJobId || !jobAttachment) throw new Error("Selectionnez une piece");
      const formData = new FormData();
      formData.append("attachment", jobAttachment);
      return (await api.post(`/recruitment/jobs/${selectedJobId}/attachments/upload`, formData, { headers: { "Content-Type": "multipart/form-data" } })).data;
    },
    onSuccess: async () => {
      setJobAttachment(null);
      await invalidateRecruitment();
      toast.success("Piece ajoutee", "Le dossier d'offre conserve maintenant une piece justificative.");
    },
    onError: () => toast.error("Upload impossible", "La piece de l'offre n'a pas pu etre envoyee."),
  });

  const syncMasterDataMutation = useMutation({
    mutationFn: async () => (await api.post(`/master-data/employers/${selectedEmployerId}/sync`)).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["recruitment", "master-health", selectedEmployerId] });
      toast.success("Donnees maitre synchronisees", "Les salaries existants sont reprojetes dans les vues canoniques des autres modules.");
    },
    onError: () => toast.error("Synchronisation impossible", "Le recalage des donnees maitres a echoue."),
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

  const handleDownloadImportTemplate = async (prefilled: boolean) => {
    if (!selectedEmployerId) return;
    try {
      await downloadRecruitmentImportTemplate(importResource, {
        employerId: selectedEmployerId,
        prefilled,
      });
    } catch (error) {
      toast.error("Téléchargement impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    }
  };

  const handleRecruitmentImport = async () => {
    if (!importFile) return;
    setImporting(true);
    setImportReport(null);
    try {
      const report = await importRecruitmentResource(importResource, importFile, { updateExisting: true });
      setImportReport(report);
      await invalidateRecruitment();
      toast.success(
        "Import recrutement terminé",
        `${report.created} création(s), ${report.updated} mise(s) à jour, ${report.failed} échec(s).`
      );
    } catch (error) {
      toast.error("Import impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    } finally {
      setImporting(false);
    }
  };

  const handleDownloadRecruitmentErrorReport = () => {
    const csv = importReport?.error_report_csv;
    if (!csv) return;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `recruitment_${importResource}_import_errors.csv`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
  };

  const createInterviewMutation = useMutation({
    mutationFn: async () =>
      api.post(`/recruitment/applications/${selectedApplicationId}/interviews`, {
        round_label: interviewForm.round_label,
        interview_type: interviewForm.interview_type,
        scheduled_at: interviewForm.scheduled_at || null,
        interviewer_name: interviewForm.interviewer_name || null,
        notes: interviewForm.notes || null,
        recommendation: interviewForm.recommendation,
        score_total: interviewForm.score_total ? Number(interviewForm.score_total) : null,
      }),
    onSuccess: async () => {
      setInterviewForm({ round_label: "Entretien RH", interview_type: "Entretien RH", scheduled_at: "", interviewer_name: "", notes: "", recommendation: "advance", score_total: "" });
      await invalidateRecruitment();
      toast.success("Entretien planifié", "L'étape d'entretien a été ajoutée au dossier.");
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

  const noEmployerConfigured = employers.length === 0;

  const applyWorkforceProfile = (workforceProfileId: number | null) => {
    setSelectedWorkforceProfileId(workforceProfileId);
    const selected = workforceProfiles.find((item) => item.id === workforceProfileId);
    if (!selected) return;
    const requiredSkills = selected.required_skills || [];
    setDraft((current) => ({
      ...current,
      title: current.title || selected.title || "",
      department: current.department || selected.department || "",
      classification: current.classification || selected.classification_index || "",
      technical_skills:
        current.technical_skills ||
        requiredSkills.filter((item) => item.type !== "behavioral").map((item) => item.label || "").filter(Boolean).join("\n"),
      behavioral_skills:
        current.behavioral_skills ||
        requiredSkills.filter((item) => item.type === "behavioral").map((item) => item.label || "").filter(Boolean).join("\n"),
      mission_summary: current.mission_summary || selected.notes || "",
    }));
  };

  const copyAnnouncementText = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success("Texte copie", `${label} est maintenant dans le presse-papiers.`);
    } catch {
      toast.error("Copie impossible", "Le texte n'a pas pu etre copie.");
    }
  };

  const toggleDraftListValue = (field: "benefits" | "working_days", value: string) => {
    setDraft((current) => {
      const values = splitValues(current[field]);
      const nextValues = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
      return { ...current, [field]: nextValues.join("\n") };
    });
  };

  const addReferenceMutation = useMutation({
    mutationFn: async ({ category, label, payload }: { category: string; label: string; payload?: Record<string, unknown> }) =>
      (
        await api.post("/recruitment/library-items", {
          employer_id: selectedEmployerId,
          category,
          label,
          description: `Ajout depuis la fiche de poste ${draft.title || label}`,
          payload: payload || { value: label },
          is_active: true,
        })
      ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["recruitment", "library-items", selectedEmployerId] });
      toast.success("Referentiel enrichi", "La valeur est maintenant disponible dans les listes du module.");
    },
    onError: () => toast.error("Ajout impossible", "La valeur n'a pas pu etre ajoutee au referentiel."),
  });

  const saveTemplateMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post("/recruitment/library-items", {
          employer_id: selectedEmployerId,
          category: "job_template",
          label: draft.title,
          description: draft.mission_summary || draft.description || "",
          payload: {
            department: draft.department,
            mission_summary: draft.mission_summary,
            main_activities: splitValues(draft.main_activities),
            technical_skills: splitValues(draft.technical_skills),
            behavioral_skills: splitValues(draft.behavioral_skills),
            education_level: draft.education_level,
            experience_required: draft.experience_required,
            languages: splitValues(draft.languages),
            tools: splitValues(draft.tools),
            certifications: splitValues(draft.certifications),
            working_hours: draft.working_hours,
            working_days: splitValues(draft.working_days),
            benefits: splitValues(draft.benefits),
            interview_criteria: splitValues(draft.interview_criteria),
            classification: draft.classification,
          },
          is_active: true,
        })
      ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["recruitment", "library-items", selectedEmployerId] });
      toast.success("Modele enregistre", "Le poste peut maintenant etre reutilise comme modele.");
    },
    onError: () => toast.error("Enregistrement impossible", "Le modele de fiche n'a pas pu etre sauvegarde."),
  });

  const syncWorkforceProfileMutation = useMutation({
    mutationFn: async () => (await api.post<JobProfile>(`/recruitment/jobs/${selectedJobId}/sync-workforce-profile`)).data,
    onSuccess: async (data) => {
      setSelectedWorkforceProfileId(data.workforce_job_profile_id ?? null);
      await queryClient.invalidateQueries({ queryKey: ["recruitment", "workforce-profiles", selectedEmployerId] });
      await invalidateRecruitment();
      toast.success("Fiche RH synchronisee", "La fiche de poste recrutement est maintenant reliee au referentiel RH.");
    },
    onError: () => toast.error("Synchronisation impossible", "La fiche RH n'a pas pu etre mise a jour."),
  });

  return (
    <div className="space-y-8">
      
      {noEmployerConfigured ? (
        <section className="rounded-[1.5rem] border border-amber-400/30 bg-amber-500/10 px-5 py-4 text-amber-100">
          <div className="text-sm font-semibold">Aucun employeur configuré</div>
          <p className="mt-2 text-sm text-amber-50/90">
            Le module Recrutement dépend d&apos;un employeur actif. Configurez d&apos;abord un employeur pour activer les formulaires et workflows.
          </p>
          <a
            href="/employers"
            className="mt-3 inline-flex rounded-xl border border-amber-300/40 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-100 hover:bg-amber-500/20"
          >
            Ouvrir Employeurs
          </a>
        </section>
      ) : null}

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
            <div className="flex flex-wrap items-center gap-3">
              {selectedJob ? (
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${publicationStatusClasses[selectedJob.publish_status] || publicationStatusClasses.draft}`}>
                  {publicationStatusLabels[selectedJob.publish_status] || selectedJob.publish_status}
                </span>
              ) : null}
              {canManagePublication ? (
                <Link to="/recruitment/settings" className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-100">
                  Paramètres recrutement
                </Link>
              ) : null}
              <select value={selectedEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClass}>
                {employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.raison_sociale}</option>)}
              </select>
              <select value={selectedJobId ?? ""} onChange={(event) => setSelectedJobId(Number(event.target.value) || null)} className={inputClass}>
                <option value="">Nouveau poste</option>
                {jobs.map((job) => <option key={job.id} value={job.id}>{job.title} | {publicationStatusLabels[job.publish_status] || job.publish_status}</option>)}
              </select>
            </div>
          </div>

          {isLoadingJobs ? <div className="mt-6 h-48 animate-pulse rounded-3xl bg-slate-900/70" /> : null}

          <div className="mt-6 grid gap-4 rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4 md:grid-cols-[1.1fr_auto] md:items-end">
            <div>
              <label className={labelClass}>Fiche de poste RH existante</label>
              <select value={selectedWorkforceProfileId ?? ""} onChange={(event) => applyWorkforceProfile(event.target.value ? Number(event.target.value) : null)} className={inputClass}>
                <option value="">Aucune fiche RH liee</option>
                {workforceProfiles.map((item) => <option key={item.id} value={item.id}>{item.title}{item.department ? ` | ${item.department}` : ""}</option>)}
              </select>
              <p className="mt-2 text-xs text-cyan-100/80">Selection depuis le referentiel RH ou saisie manuelle complete. Le lien reste optionnel et editable.</p>
            </div>
            <button type="button" disabled={!selectedJobId} onClick={() => syncWorkforceProfileMutation.mutate()} className="rounded-2xl border border-cyan-300/30 bg-slate-950/40 px-4 py-3 text-sm font-semibold text-cyan-100 disabled:opacity-40">
              Enregistrer comme fiche RH
            </button>
          </div>

          {!isLoadingJobs && jobs.length === 0 ? (
            <div className="mt-6 rounded-3xl border border-dashed border-white/10 bg-slate-900/50 p-6 text-sm text-slate-400">
              Aucune offre disponible pour le moment.
            </div>
          ) : null}

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Intitulé</label>
              <div className="grid gap-2">
                <select value={jobTitleSuggestions.includes(draft.title) ? draft.title : ""} onChange={(e) => setDraft((c) => ({ ...c, title: e.target.value || c.title }))} className={inputClass}>
                  <option value="">Choisir dans le référentiel</option>
                  {buildSelectValues(jobTitleSuggestions, draft.title).map((value) => <option key={`job-title-${value}`} value={value}>{value}</option>)}
                </select>
                <input value={draft.title} onChange={(e) => setDraft((c) => ({ ...c, title: e.target.value }))} className={inputClass} placeholder="Ou saisir un nouvel intitulé" />
              </div>
            </div>
            <div>
              <label className={labelClass}>Département / Service</label>
              <div className="grid gap-2">
                <select value={departmentSuggestions.includes(draft.department) ? draft.department : ""} onChange={(e) => setDraft((c) => ({ ...c, department: e.target.value || c.department }))} className={inputClass}>
                  <option value="">Choisir dans le référentiel</option>
                  {buildSelectValues(departmentSuggestions, draft.department).map((value) => <option key={`department-${value}`} value={value}>{value}</option>)}
                </select>
                <input value={draft.department} onChange={(e) => setDraft((c) => ({ ...c, department: e.target.value }))} className={inputClass} placeholder="Ou saisir un nouveau service" />
              </div>
            </div>
            <div><label className={labelClass}>Localisation</label><select value={draft.location} onChange={(e) => setDraft((c) => ({ ...c, location: e.target.value }))} className={inputClass}><option value="">Sélectionner</option>{buildSelectValues(locationSuggestions, draft.location).map((value) => <option key={`location-${value}`} value={value}>{value}</option>)}</select></div>
            <div><label className={labelClass}>Responsable hiérarchique</label><input value={draft.manager_title} onChange={(e) => setDraft((c) => ({ ...c, manager_title: e.target.value }))} className={inputClass} placeholder="DRH" /></div>
            <div>
              <div className="flex items-center gap-2">
                <label className={labelClass}>Type de contrat</label>
                <HelpTooltip item={recruitmentContractHelp} role="rh" compact />
              </div>
              <select value={draft.contract_type} onChange={(e) => setDraft((c) => ({ ...c, contract_type: e.target.value }))} className={inputClass}>
                {buildSelectValues(contractTypeSuggestions, draft.contract_type).map((value) => <option key={`contract-type-${value}`} value={value}>{value}</option>)}
              </select>
              <p className="mt-2 text-xs text-slate-400">
                Suggestions standards Madagascar: {contractTypeSuggestions.slice(0, 5).join(", ")}
                {contractTypeSuggestions.length > 5 ? "..." : ""}
              </p>
              {assistantSuggestion?.contract_type_suggestions?.length ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {assistantSuggestion.contract_type_suggestions.slice(0, 4).map((item) => (
                    <button key={`contract-suggestion-${item.code}`} type="button" onClick={() => setDraft((current) => ({ ...current, contract_type: item.label }))} className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${item.recommended ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50" : "border-white/10 text-white"}`}>
                      {item.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <div><label className={labelClass}>Classification / Indice</label><select value={resolveClassificationCode(draft.classification, classificationOptions)} onChange={(e) => setDraft((c) => ({ ...c, classification: e.target.value }))} className={inputClass}><option value="">Sélectionner</option>{classificationOptions.map((option) => <option key={`${option.code}-${option.display}`} value={option.code}>{option.display}</option>)}</select>{selectedClassification ? <p className="mt-2 text-xs text-cyan-200">{selectedClassification.family}{selectedClassification.group ? ` | Groupe ${selectedClassification.group}` : ""}{selectedClassification.description ? ` | ${selectedClassification.description}` : ""}</p> : <p className="mt-2 text-xs text-slate-500">Référentiel métier chargé depuis la base RH.</p>}</div>
            <div className="md:col-span-2"><label className={labelClass}>Description libre du besoin</label><textarea value={draft.description} onChange={(e) => setDraft((c) => ({ ...c, description: e.target.value }))} className={`${inputClass} min-h-[88px]`} placeholder="Décrivez le besoin métier, l’environnement, les enjeux et le profil recherché." /></div>
            <div className="md:col-span-2"><label className={labelClass}>Mission principale</label><textarea value={draft.mission_summary} onChange={(e) => setDraft((c) => ({ ...c, mission_summary: e.target.value }))} className={`${inputClass} min-h-[80px]`} /></div>
            <div><label className={labelClass}>Activités principales</label><textarea value={draft.main_activities} onChange={(e) => setDraft((c) => ({ ...c, main_activities: e.target.value }))} className={`${inputClass} min-h-[120px]`} placeholder="Une activité par ligne" /></div>
            <div><label className={labelClass}>Compétences techniques</label><textarea value={draft.technical_skills} onChange={(e) => setDraft((c) => ({ ...c, technical_skills: e.target.value }))} className={`${inputClass} min-h-[120px]`} placeholder="Une compétence par ligne" /></div>
            <div><label className={labelClass}>Compétences comportementales</label><textarea value={draft.behavioral_skills} onChange={(e) => setDraft((c) => ({ ...c, behavioral_skills: e.target.value }))} className={`${inputClass} min-h-[120px]`} /></div>
            <div><label className={labelClass}>Outils / logiciels / certifications</label><textarea value={`${draft.tools}${draft.certifications ? `\n${draft.certifications}` : ""}`} onChange={(e) => setDraft((c) => ({ ...c, tools: e.target.value, certifications: "" }))} className={`${inputClass} min-h-[120px]`} /></div>
            <div><label className={labelClass}>Langues</label><textarea value={draft.languages} onChange={(e) => setDraft((c) => ({ ...c, languages: e.target.value }))} className={`${inputClass} min-h-[90px]`} /></div>
            <div><label className={labelClass}>Critères d’entretien pondérables</label><textarea value={draft.interview_criteria} onChange={(e) => setDraft((c) => ({ ...c, interview_criteria: e.target.value }))} className={`${inputClass} min-h-[90px]`} /></div>
            <div><label className={labelClass}>Niveau d’études</label><select value={draft.education_level} onChange={(e) => setDraft((c) => ({ ...c, education_level: e.target.value }))} className={inputClass}><option value="">Sélectionner</option>{buildSelectValues(educationLevelSuggestions, draft.education_level).map((value) => <option key={`education-${value}`} value={value}>{value}</option>)}</select></div>
            <div><label className={labelClass}>Expérience requise</label><select value={draft.experience_required} onChange={(e) => setDraft((c) => ({ ...c, experience_required: e.target.value }))} className={inputClass}><option value="">Sélectionner</option>{buildSelectValues(experienceLevelSuggestions, draft.experience_required).map((value) => <option key={`experience-${value}`} value={value}>{value}</option>)}</select></div>
            <div><label className={labelClass}>Salaire minimum</label><input value={draft.salary_min} onChange={(e) => setDraft((c) => ({ ...c, salary_min: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Salaire maximum</label><input value={draft.salary_max} onChange={(e) => setDraft((c) => ({ ...c, salary_max: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Date souhaitée</label><input type="date" value={draft.desired_start_date} onChange={(e) => setDraft((c) => ({ ...c, desired_start_date: e.target.value }))} className={inputClass} /></div>
            <div><label className={labelClass}>Date limite candidature</label><input type="date" value={draft.application_deadline} onChange={(e) => setDraft((c) => ({ ...c, application_deadline: e.target.value }))} className={inputClass} /></div>
            <div className="md:col-span-2">
              <label className={labelClass}>Avantages</label>
              <div className="flex flex-wrap gap-2">
                {benefitSuggestions.map((value) => {
                  const selected = splitValues(draft.benefits).includes(value);
                  return (
                    <button key={`benefit-${value}`} type="button" onClick={() => toggleDraftListValue("benefits", value)} className={`rounded-full border px-3 py-2 text-xs font-semibold ${selected ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50" : "border-white/10 text-white"}`}>
                      {value}
                    </button>
                  );
                })}
              </div>
            </div>
            <div><label className={labelClass}>Horaires</label><select value={draft.working_hours} onChange={(e) => setDraft((c) => ({ ...c, working_hours: e.target.value }))} className={inputClass}><option value="">Sélectionner</option>{buildSelectValues(workingScheduleSuggestions, draft.working_hours).map((value) => <option key={`working-hours-${value}`} value={value}>{value}</option>)}</select></div>
            <div className="md:col-span-2"><label className={labelClass}>Jours de travail</label><div className="flex flex-wrap gap-2">{workingDaySuggestions.map((value) => { const selected = splitValues(draft.working_days).includes(value); return <button key={`working-day-${value}`} type="button" onClick={() => toggleDraftListValue("working_days", value)} className={`rounded-full border px-3 py-2 text-xs font-semibold ${selected ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50" : "border-white/10 text-white"}`}>{value}</button>; })}</div></div>
            <div className="md:col-span-2 rounded-2xl border border-white/10 bg-slate-900/60 p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-white">Publication 1 clic</div>
                  <div className="mt-1 text-xs text-slate-400">Canaux actifs pour cette offre. Les secrets restent côté backend.</div>
                </div>
                <div className="text-xs text-slate-400">{jobPublishChannels.length} sélectionné(s)</div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {activePublicationChannels.length ? activePublicationChannels.map((channel) => {
                  const selected = jobPublishChannels.includes(channel.channel_type);
                  return (
                    <button
                      key={channel.id}
                      type="button"
                      onClick={() => setJobPublishChannels((current) => selected ? current.filter((item) => item !== channel.channel_type) : [...current, channel.channel_type])}
                      className={`rounded-full border px-3 py-2 text-xs font-semibold ${selected ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50" : "border-white/10 text-white"}`}
                    >
                      {publicationChannelLabels[channel.channel_type] || channel.channel_type}
                      {channel.default_publish ? " • défaut" : ""}
                    </button>
                  );
                }) : (
                  <div className="text-sm text-slate-400">
                    Aucun canal actif. Ouvrez <Link to="/recruitment/settings" className="text-cyan-200 underline">Paramètres recrutement</Link> pour activer la diffusion.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={() => suggestMutation.mutate(undefined)} className="inline-flex items-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950"><SparklesIcon className="h-5 w-5" />Suggérer la fiche</button>
            <button type="button" onClick={() => saveJobMutation.mutate()} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white">Enregistrer</button>
            <button type="button" onClick={() => submitValidationMutation.mutate()} disabled={!selectedJobId} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Notifier inspection</button>
            <button type="button" onClick={() => generateAnnouncementMutation.mutate()} disabled={!selectedJobId} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Générer l’annonce</button>
            <button type="button" onClick={() => publishMutation.mutate()} disabled={!selectedJobId || !canManagePublication || publishMutation.isPending || jobPublishChannels.length === 0} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-5 py-3 text-sm font-semibold text-emerald-100 disabled:opacity-40"><CheckBadgeIcon className="h-5 w-5" />{publishMutation.isPending ? "Publication..." : "Publier"}</button>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <HelpTooltip item={recruitmentContractHelp} role="rh" />
            <button type="button" onClick={() => suggestMutation.mutate({ mode: "generate" })} className="rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-4 py-2 text-xs font-semibold text-cyan-100">Generer automatiquement</button>
            <button type="button" onClick={() => suggestMutation.mutate({ mode: "improve" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Ameliorer</button>
            <button type="button" onClick={() => suggestMutation.mutate({ mode: "adapt" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Adapter au poste</button>
            <button type="button" onClick={() => setAssistantVersion((current) => current === "long" ? "short" : "long")} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Version {assistantVersion === "long" ? "longue" : "courte"}</button>
            <button type="button" onClick={() => suggestMutation.mutate({ focus_block: "description" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Regenerer description</button>
            <button type="button" onClick={() => suggestMutation.mutate({ focus_block: "mission_summary" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Regenerer mission</button>
            <button type="button" onClick={() => suggestMutation.mutate({ focus_block: "main_activities" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Regenerer activites</button>
            <button type="button" onClick={() => suggestMutation.mutate({ focus_block: "technical_skills" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Regenerer competences</button>
            <button type="button" onClick={() => suggestMutation.mutate({ focus_block: "behavioral_skills" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Regenerer soft skills</button>
            <button type="button" onClick={() => suggestMutation.mutate({ focus_block: "interview_criteria" })} className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-white">Regenerer entretien</button>
          </div>
          {assistantSuggestion ? (
            <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-4 text-sm text-cyan-50">
              <div className="font-semibold text-white">Assistant contexte poste</div>
              <div className="mt-1 text-xs uppercase tracking-[0.18em] text-cyan-200">{assistantSuggestion.probable_title || draft.title || "Poste"}{assistantSuggestion.probable_department ? ` | ${assistantSuggestion.probable_department}` : ""}</div>
              <div className="mt-2 text-cyan-100">{assistantSuggestion.generated_context}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {assistantSuggestion.contract_type_suggestions.map((item) => (
                  <button key={item.code} type="button" onClick={() => setDraft((current) => ({ ...current, contract_type: item.label }))} className={`rounded-full border px-3 py-1 text-xs font-semibold ${item.recommended ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50" : "border-white/10 text-white"}`}>
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="mt-3 grid gap-2">
                {assistantSuggestion.contract_type_suggestions.slice(0, 4).map((item) => (
                  <div key={`${item.code}-desc`} className="text-xs text-cyan-100">{item.label}: {item.description}</div>
                ))}
              </div>
            </div>
          ) : null}
          {suggestionSources.length > 0 ? <div className="mt-4 text-sm text-cyan-200">Sources de suggestion: {suggestionSources.join(", ")}</div> : null}
          {linkedWorkforceProfile ? <div className="mt-3 text-sm text-cyan-100">Fiche RH liee: {linkedWorkforceProfile.title}{linkedWorkforceProfile.department ? ` | ${linkedWorkforceProfile.department}` : ""}</div> : null}
          <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
            <div className="font-semibold text-white">Referentiel et reutilisation</div>
            <div className="mt-1 text-xs text-slate-400">{jobTitleSuggestions.length} intitulés standardisés et réutilisables chargés depuis la base recrutement.</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" disabled={!canSuggestTitleReference} onClick={() => addReferenceMutation.mutate({ category: "job_template", label: draft.title, payload: { department: draft.department || "", mission_summary: draft.mission_summary || "" } })} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Ajouter l'intitule</button>
              <button type="button" disabled={!canSuggestDepartmentReference} onClick={() => addReferenceMutation.mutate({ category: "department", label: draft.department })} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Ajouter le departement</button>
              <button type="button" disabled={!canSuggestLocationReference} onClick={() => addReferenceMutation.mutate({ category: "location", label: draft.location })} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Ajouter la localisation</button>
              <button type="button" onClick={() => saveTemplateMutation.mutate()} disabled={!draft.title.trim()} className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-100 disabled:opacity-40">Sauvegarder comme modele</button>
            </div>
          </div>
          {contractGuidance ? (
            <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-50">
              <div className="font-semibold text-white">Guidage contrat Madagascar</div>
              <div className="mt-2">Type suggere: <span className="font-semibold">{contractGuidance.suggested_primary_type}</span></div>
              <div className="mt-2">Langues: {contractGuidance.language_options.join(" / ")}</div>
              <div className="mt-2">Champs a verifier: {contractGuidance.required_fields.join(", ")}</div>
              {contractGuidance.recommendations.map((item) => <div key={item} className="mt-2">{item}</div>)}
              {contractGuidance.alerts.map((alert) => <div key={alert.code} className="mt-2 text-amber-100">{alert.message}</div>)}
            </div>
          ) : null}
        </div>

        <div className="space-y-6">
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Socle transverse</h2>
            <p className="mt-1 text-sm text-slate-400">Visibilite sur les donnees employeur/salaries deja presentes dans la base et sur leur synchronisation canonique.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3 text-sm text-slate-300">
              <div>Employeur: <span className="font-semibold text-white">{employers.find((item) => item.id === selectedEmployerId)?.raison_sociale || "-"}</span></div>
              <div>Salaries existants: <span className="font-semibold text-white">{workers.length}</span></div>
              <div>Alertes master data: <span className="font-semibold text-white">{masterHealth?.workers_with_issues ?? 0}</span></div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => syncMasterDataMutation.mutate()} disabled={!selectedEmployerId} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Resynchroniser les donnees maitre</button>
              <button type="button" onClick={() => window.location.assign("/employee-360")} className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-100">Ouvrir Salarie 360</button>
            </div>
            {(masterHealth?.items ?? []).slice(0, 3).map((item, index) => (
              <div key={`master-health-${index}`} className="mt-3 rounded-xl border border-amber-400/20 bg-amber-400/10 p-3 text-xs text-amber-50">
                <div className="font-semibold">{item.worker?.nom} {item.worker?.prenom} {item.worker?.matricule ? `(${item.worker.matricule})` : ""}</div>
                <div className="mt-1">{item.integrity_issues[0]?.message || "Ecart de coherence detecte."}</div>
              </div>
            ))}
          </div>
          <div className={shellCard}>
            <h2 className="text-xl font-semibold text-white">Publication et annonce</h2>
            <p className="mt-1 text-sm text-slate-400">Prévisualisation diffusion, statut par canal et variantes prêtes à publier.</p>
            {selectedJob ? (
              <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-white">État de publication</div>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${publicationStatusClasses[selectedJob.publish_status] || publicationStatusClasses.draft}`}>
                    {publicationStatusLabels[selectedJob.publish_status] || selectedJob.publish_status}
                  </span>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {jobPublishChannels.map((channelType) => {
                    const lastLog = publicationLogs.find((item) => item.channel === channelType);
                    const status = lastLog?.status || "draft";
                    return (
                      <div key={channelType} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-300">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-semibold text-white">{publicationChannelLabels[channelType] || channelType}</div>
                          <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${publicationStatusClasses[status] || publicationStatusClasses.draft}`}>
                            {publicationStatusLabels[status] || status}
                          </span>
                        </div>
                        <div className="mt-2 text-xs text-slate-400">{lastLog?.message || "Pas encore publié sur ce canal."}</div>
                        <div className="mt-3 flex items-center justify-between gap-3">
                          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{lastLog?.timestamp ? new Date(lastLog.timestamp).toLocaleString() : "En attente"}</div>
                          <button
                            type="button"
                            disabled={!canManagePublication || retryPublishMutation.isPending}
                            onClick={() => retryPublishMutation.mutate(channelType)}
                            className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
                          >
                            {retryPublishMutation.isPending ? "Relance..." : "Retry"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                  {!jobPublishChannels.length ? <div className="text-sm text-slate-400">Aucun canal rattaché à cette offre.</div> : null}
                </div>
              </div>
            ) : null}
            {announcementPreview ? (
              <div className="mt-5 space-y-4 text-sm text-slate-200">
                <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-5">
                  <div className="text-lg font-semibold text-white">{announcementPreview.title}</div>
                  <div className="mt-2 text-xs text-cyan-200">{announcementPreview.public_url}</div>
                  <div className="mt-2 whitespace-pre-wrap text-slate-300">{announcementPreview.web_body}</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => copyAnnouncementText(announcementPreview.web_body, "Annonce web")} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Copier web</button>
                  <button type="button" onClick={() => copyAnnouncementText(announcementPreview.facebook_text, "Texte Facebook")} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Copier Facebook</button>
                  <button type="button" onClick={() => copyAnnouncementText(announcementPreview.linkedin_text, "Texte LinkedIn")} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Copier LinkedIn</button>
                  <button type="button" onClick={() => copyAnnouncementText(announcementPreview.copy_text, "Texte externe")} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">Copier externe</button>
                  <button type="button" disabled={!selectedJobId} onClick={() => window.open(`${api.defaults.baseURL}/recruitment/jobs/${selectedJobId}/announcement-pdf`, "_blank")} className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-100 disabled:opacity-40">Imprimer PDF</button>
                </div>
                <div className="grid gap-3">
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4"><div className="font-semibold text-cyan-200">E-mail</div><div className="mt-2 whitespace-pre-wrap">{announcementPreview.email_body}</div></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4"><div className="font-semibold text-cyan-200">LinkedIn</div><div className="mt-2 whitespace-pre-wrap">{announcementPreview.linkedin_text}</div></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4"><div className="font-semibold text-cyan-200">Facebook</div><div className="mt-2 whitespace-pre-wrap">{announcementPreview.facebook_text}</div></div>
                </div>
              </div>
            ) : <div className="mt-5 rounded-3xl border border-dashed border-white/10 p-6 text-sm text-slate-400">Générez une annonce pour prévisualiser le texte public et les variantes de partage.</div>}
            {publicationLogs.length ? (
              <div className="mt-5 space-y-3">
                {publicationLogs.slice(0, 8).map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-slate-900/70 p-4 text-sm text-slate-300">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-white">{publicationChannelLabels[item.channel] || item.channel}</div>
                      <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${publicationStatusClasses[item.status] || publicationStatusClasses.draft}`}>
                        {publicationStatusLabels[item.status] || item.status}
                      </span>
                    </div>
                    <div className="mt-2">{item.message || "Aucun détail."}</div>
                    <div className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">{new Date(item.timestamp).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            ) : null}
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
              <div className="grid gap-4 md:grid-cols-3">
                <select value={candidateForm.education_level} onChange={(e) => setCandidateForm((c) => ({ ...c, education_level: e.target.value }))} className={inputClass}>
                  <option value="">Niveau d'études</option>
                  {buildSelectValues(educationLevelSuggestions, candidateForm.education_level).map((value) => <option key={`candidate-education-${value}`} value={value}>{value}</option>)}
                </select>
                <input type="number" min={0} step={0.5} value={candidateForm.experience_years} onChange={(e) => setCandidateForm((c) => ({ ...c, experience_years: e.target.value }))} className={inputClass} placeholder="Expérience (années)" />
                <select value={candidateForm.source} onChange={(e) => setCandidateForm((c) => ({ ...c, source: e.target.value }))} className={inputClass}>
                  <option value="">Source candidature</option>
                  {buildSelectValues(candidateSourceSuggestions, candidateForm.source).map((value) => <option key={`candidate-source-${value}`} value={value}>{value}</option>)}
                </select>
              </div>
              <textarea value={candidateForm.summary} onChange={(e) => setCandidateForm((c) => ({ ...c, summary: e.target.value }))} className={`${inputClass} min-h-[90px]`} placeholder="Résumé candidat ou note recruteur" />
              <input type="file" onChange={(e) => setJobAttachment(e.target.files?.[0] || null)} className={inputClass} />
              <button type="button" disabled={!selectedJobId || !jobAttachment} onClick={() => uploadJobAttachmentMutation.mutate()} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Ajouter une piece a l'offre</button>
              <input type="file" accept=".pdf,.doc,.docx,.txt" onChange={(e) => setCvFile(e.target.files?.[0] || null)} className={inputClass} />
              <input type="file" multiple onChange={(e) => setAttachments(Array.from(e.target.files || []))} className={inputClass} />
              <button type="button" onClick={() => uploadCandidateMutation.mutate()} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950"><UserPlusIcon className="h-5 w-5" />Déposer CV + pièces</button>
              <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Import / Export en masse</div>
                <div className="mt-3 grid gap-3">
                  <select
                    value={importResource}
                    onChange={(event) => setImportResource(event.target.value as "candidates" | "jobs")}
                    className={inputClass}
                  >
                    <option value="candidates">Candidats</option>
                    <option value="jobs">Fiches de poste</option>
                  </select>
                  <input
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                    className={inputClass}
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleDownloadImportTemplate(false)}
                      className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <ArrowDownTrayIcon className="h-4 w-4" />
                      Modèle vide
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDownloadImportTemplate(true)}
                      className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <ArrowDownTrayIcon className="h-4 w-4" />
                      Export existant
                    </button>
                    <button
                      type="button"
                      onClick={handleRecruitmentImport}
                      disabled={!importFile || importing}
                      className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-60"
                    >
                      <ArrowUpTrayIcon className="h-4 w-4" />
                      {importing ? "Import..." : "Importer"}
                    </button>
                  </div>
                </div>
                {importReport ? (
                  <div className="mt-3 rounded-xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-xs text-cyan-100">
                    <div>{importReport.created} création(s), {importReport.updated} mise(s) à jour, {importReport.failed} échec(s).</div>
                    {importReport.error_report_csv ? (
                      <button
                        type="button"
                        onClick={handleDownloadRecruitmentErrorReport}
                        className="mt-2 underline"
                      >
                        Télécharger rapport d'erreurs
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
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
            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/60 p-4 text-sm text-slate-300">
              <div className="font-semibold text-white">Candidat actif</div>
              <div className="mt-2">{selectedCandidate ? `${selectedCandidate.first_name} ${selectedCandidate.last_name}` : "Sélectionnez un candidat dans le pipeline."}</div>
              <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{selectedApplication?.stage || "Aucune étape active"}</div>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <select value={interviewForm.round_label} onChange={(e) => setInterviewForm((c) => ({ ...c, round_label: e.target.value, interview_type: e.target.value }))} className={inputClass}>
                {buildSelectValues(interviewStageSuggestions, interviewForm.round_label).map((value) => <option key={`interview-stage-${value}`} value={value}>{value}</option>)}
              </select>
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
                  <div className="mt-2 text-xs uppercase tracking-[0.18em] text-cyan-200">{interview.interview_type || interview.round_label}</div>
                  <div className="mt-2">{interview.scheduled_at ? new Date(interview.scheduled_at).toLocaleString() : "Date à confirmer"}</div>
                  <div className="mt-2">Évaluateur: <span className="text-white">{interview.interviewer_name || "Non renseigné"}</span></div>
                  <div className="mt-2">Score: <span className="text-white">{interview.score_total ?? "n/a"}</span></div>
                  <div className="mt-2 text-cyan-200">{interview.recommendation || "Aucune recommandation"}</div>
                  <div className="mt-2 whitespace-pre-wrap text-slate-400">{interview.notes || "Aucun commentaire saisi."}</div>
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
