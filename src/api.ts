// src/api.ts
import axios from "axios";

export const AUTH_STORAGE_KEY = "siirh.auth.session";

export type AuthSession = {
  token: string;
  user_id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
  effective_role_code?: string | null;
  role_label?: string | null;
  role_scope?: string | null;
  module_permissions?: Record<string, string[]>;
  assigned_role_codes?: string[];
  employer_id?: number | null;
  worker_id?: number | null;
};

export function getStoredSession(): AuthSession | null {
  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function storeSession(session: AuthSession | null) {
  if (!session) {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function getStoredToken(): string | null {
  return getStoredSession()?.token ?? null;
}

// Instance axios commune pour tout le frontend
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001",
});

const publicApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001",
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      storeSession(null);
      window.dispatchEvent(new CustomEvent("siirh:unauthorized"));
    }
    return Promise.reject(error);
  }
);

export async function loginRequest(username: string, password: string): Promise<AuthSession> {
  const response = await api.post<AuthSession>("/auth/login", { username, password });
  return response.data;
}

export async function fetchCurrentSession(): Promise<AuthSession> {
  const response = await api.get<AuthSession>("/auth/me");
  const stored = getStoredSession();
  return { ...response.data, token: stored?.token ?? response.data.token };
}

export async function logoutRequest() {
  await api.post("/auth/logout");
}

/**
 * Appelle le backend pour CALCULER ET ENREGISTRER les HS.
 * Utilise l'endpoint POST /hs/calculate-and-save
 */
export async function calculateHSBackendHS(payloadHS: object) {
  const response = await api.post("/hs/calculate-and-save", payloadHS);
  return response.data; // HSCalculationReadHS
}

/**
 * Récupère TOUS les enregistrements HS en base.
 * Utilise l'endpoint GET /hs/all
 */
export async function getAllHSCalculationsHS(workerId?: number, mois?: string) {
  const params: Record<string, string | number> = {};
  if (typeof workerId === "number" && workerId > 0) {
    params.worker_id = workerId;
  }
  if (mois) {
    params.mois = mois;
  }
  const response = await api.get("/hs/all", { params });
  return response.data; // HSCalculationReadHS[]
}

/**
 * Supprime un enregistrement HS par son id_HS.
 * Utilise l'endpoint DELETE /hs/{hs_id}
 */
export async function deleteHSCalculationHS(hsId: number) {
  await api.delete(`/hs/${hsId}`);
}

export async function exportHSCalculationToPayroll(
  hsId: number,
  payrollRunId: number,
  taux?: {
    taux_hs130?: number;
    taux_hs150?: number;
    taux_hmnh?: number;
    taux_hmno?: number;
    taux_hmd?: number;
    taux_hmjf?: number;
  }
) {
  const response = await api.post(`/hs/${hsId}/export-to-payroll`, taux ?? {}, {
    params: { payroll_run_id: payrollRunId },
  });
  return response.data;
}

export interface HSImportPreviewRow {
  worker_id_HS?: number | null;
  matricule: string;
  nom: string;
  date_HS: string;
  type_jour_HS: "N" | "JF" | "F";
  entree_HS: string;
  sortie_HS: string;
  type_nuit_HS?: "H" | "O" | null;
  duree_pause_minutes_HS: number;
}

export interface HSImportPreviewResponse {
  success: boolean;
  message: string;
  rows_imported: number;
  data: HSImportPreviewRow[];
  errors: string[];
}

export async function downloadHsImportTemplate(options?: { employerId?: number }) {
  const response = await api.get("/hs/import/template", {
    params: {
      employer_id: options?.employerId,
    },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  const contentDisposition = response.headers?.["content-disposition"] ?? "";
  const filenameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
  link.setAttribute("download", filenameMatch?.[1] ?? "template_planning_hs.xlsx");
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export async function previewHsImport(file: File): Promise<HSImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post<HSImportPreviewResponse>("/hs/import/preview", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

// -------------------------------------------------------------
//  HS/HM Import & Link
// -------------------------------------------------------------

export interface ExcelImportSummary {
  total_rows: number;
  successful: number;
  failed: number;
  errors: string[];
}

export interface PayrollOrganizationFilters {
  etablissement?: string;
  departement?: string;
  service?: string;
  unite?: string;
}

/**
 * Import HS/HM data from Excel file for a specific payroll run.
 * Endpoint: POST /payroll-hs-hm/{payroll_run_id}/import-excel
 */
export async function importHsHmExcel(
  payrollRunId: number,
  file: File,
  filters?: PayrollOrganizationFilters | null
): Promise<ExcelImportSummary> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<ExcelImportSummary>(
    `/payroll-hs-hm/${payrollRunId}/import-excel`,
    formData,
    {
      params: filters ?? {},
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data; // { id, employer_id, period, ... }
}

export async function downloadHsHmTemplate(options?: {
  payrollRunId?: number;
  employerId?: number;
  filters?: PayrollOrganizationFilters | null;
}) {
  const response = await api.get("/payroll-hs-hm/template", {
    params: {
      payroll_run_id: options?.payrollRunId,
      employer_id: options?.employerId,
      ...(options?.filters ?? {}),
    },
    responseType: "blob",
  });

  // Create a link element, hide it, direct it towards the blob, and then 'click' it intentionally.
  // Create a link element, hide it, direct it towards the blob, and then 'click' it intentionally.
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = blobUrl;
  const suffix = options?.employerId ? `_${options.employerId}` : "";
  link.setAttribute("download", `Modele_Import_Paie${suffix}.xlsx`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
}

// --- PRIMES ---
export async function downloadPrimesTemplate(
  employerId: number,
  options?: { prefilled?: boolean; format?: "xlsx" | "csv"; filters?: PayrollOrganizationFilters | null }
) {
  const response = await api.get(`/primes/export-primes-template/${employerId}`, {
    params: {
      prefilled: options?.prefilled ?? true,
      export_format: options?.format ?? "xlsx",
      ...(options?.filters ?? {}),
    },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  link.setAttribute("download", `Modele_Import_Primes_${employerId}.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export interface PrimesImportSummary {
  message: string;
  updated_items: number;
  errors: string[];
  imported?: number;
  updated?: number;
  skipped?: number;
  report?: TabularImportReport;
}

export async function importPrimesExcel(
  period: string,
  file: File,
  employerId: number,
  options?: { updateExisting?: boolean; dryRun?: boolean; filters?: PayrollOrganizationFilters | null }
): Promise<PrimesImportSummary> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("period", period);
  formData.append("employer_id", employerId.toString());
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("dry_run", String(options?.dryRun ?? false));
  if (options?.filters?.etablissement) formData.append("etablissement", options.filters.etablissement);
  if (options?.filters?.departement) formData.append("departement", options.filters.departement);
  if (options?.filters?.service) formData.append("service", options.filters.service);
  if (options?.filters?.unite) formData.append("unite", options.filters.unite);

  const response = await api.post<PrimesImportSummary>("/primes/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

/**
 * Récupère ou crée un PayrollRun pour un employeur et une période donnés.
 * Endpoint: POST /payroll/get-or-create-run
 */
export async function getOrCreatePayrollRun(employerId: number, period: string) {
  const response = await api.post(`/payroll/get-or-create-run`, null, {
    params: { employer_id: employerId, period },
  });
  return response.data; // { id, employer_id, period, ... }
}


/**
 * Récupère toutes les données HS/HM liées à un payroll_run.
 * Endpoint: GET /payroll-hs-hm/{payroll_run_id}/all
 */
export async function getAllHsHmForPayroll(payrollRunId: number, filters?: PayrollOrganizationFilters | null) {
  const response = await api.get(`/payroll-hs-hm/${payrollRunId}/all`, { params: filters ?? {} });
  return response.data; // PayrollHsHmOut[]
}

/**
 * Met à jour les heures HS/HM pour un travailleur donné.
 * Endpoint: PUT /payroll-hs-hm/{payroll_run_id}/{worker_id}
 */
export async function updateWorkerHsHm(
  payrollRunId: number,
  workerId: number,
  payload: object
) {
  const response = await api.put(`/payroll-hs-hm/${payrollRunId}/${workerId}`, payload);
  return response.data; // PayrollHsHmOut
}

/**
 * Supprime les données HS/HM pour un travailleur donné.
 * Endpoint: DELETE /payroll-hs-hm/{payroll_run_id}/{worker_id}
 */
export async function deleteWorkerHsHm(payrollRunId: number, workerId: number) {
  const response = await api.delete(`/payroll-hs-hm/${payrollRunId}/${workerId}`);
  return response.data;
}


/**
 * Réinitialise HS/HM et Absences en masse pour une liste de salariés.
 * Endpoint: POST /payroll-hs-hm/{payroll_run_id}/reset-bulk
 */
export async function resetBulkHsHm(payrollRunId: number, workerIds: number[]) {
  const response = await api.post(`/payroll-hs-hm/${payrollRunId}/reset-bulk`, workerIds);
  return response.data;
}

/**
 * Récupère les travailleurs (optionnellement filtrés par employer_id).
 * Endpoint: GET /workers?employer_id=...
 */
export async function getWorkers(employerId?: number, filters?: PayrollOrganizationFilters | null) {
  const params: Record<string, number | string> = {};
  if (employerId) params.employer_id = employerId;
  if (filters?.etablissement) params.etablissement = filters.etablissement;
  if (filters?.departement) params.departement = filters.departement;
  if (filters?.service) params.service = filters.service;
  if (filters?.unite) params.unite = filters.unite;
  const response = await api.get("/workers", { params });
  return response.data; // Worker[]
}

export async function getEmployer(id: number) {
  const response = await api.get(`/employers/${id}`);
  return response.data;
}

export async function updateEmployer(id: number, data: object) {
  const response = await api.put(`/employers/${id}`, data);
  return response.data;
}

export async function deleteEmployer(id: number) {
  const response = await api.delete(`/employers/${id}`);
  return response.data;
}

// --- PRIMES MANAGEMENT ---
export interface Prime {
  id: number;
  employer_id: number;
  label: string;
  description: string;
  formula_nombre: string;
  formula_base: string;
  formula_taux: string;
  operation_1: string;
  operation_2: string;
  is_active: boolean;
  is_cotisable: boolean;
  is_imposable: boolean;
  target_mode: "global" | "segment" | "individual";
  target_worker_ids: number[];
  excluded_worker_ids: number[];
  target_organizational_node_ids: number[];
  target_organizational_unit_ids: number[];
}

export interface AssociationRequest {
  worker_id: number;
  prime_id: number;
  is_active: boolean;
  link_type?: "include" | "exclude";
}

export const getPrimes = async (employerId: number) => {
  const response = await api.get(`/primes/?employer_id=${employerId}`);
  return response.data;
};

export const createPrime = async (prime: Partial<Prime>) => {
  const response = await api.post(`/primes/`, prime);
  return response.data;
};

export const updatePrime = async (id: number, prime: Partial<Prime>) => {
  const response = await api.put(`/primes/${id}`, prime);
  return response.data;
};

export const deletePrime = async (id: number) => {
  const response = await api.delete(`/primes/${id}`);
  return response.data;
};

export const updateWorkerPrimeAssociation = async (auth: AssociationRequest) => {
  const response = await api.post(`/primes/associations`, auth);
  return response.data;
};

export const getWorkerAssociations = async (workerId: number) => {
  const response = await api.get(`/primes/associations?worker_id=${workerId}`);
  // returns array of {prime_id: int, is_active: bool}
  return response.data;
};

// --- PRIME VALUES MANAGEMENT (Values per Period) ---
export interface PrimeValuesOut {
  worker_id: number;
  matricule: string;
  nom: string;
  prenom: string;
  prime_13: number;
  prime1: number;
  prime2: number;
  prime3: number;
  prime4: number;
  prime5: number;
}

export const getPrimeValues = async (payrollRunId: number) => {
  const response = await api.get(`/primes/values/${payrollRunId}`);
  return response.data; // PrimeValuesOut[]
};

export const updatePrimeValues = async (
  payrollRunId: number,
  workerId: number,
  values: object
) => {
  const response = await api.put(`/primes/values/${payrollRunId}/${workerId}`, values);
  return response.data;
};

export const resetBulkPrimeValues = async (payrollRunId: number, workerIds: number[]) => {
  const response = await api.post(`/primes/values/${payrollRunId}/reset-bulk`, workerIds);
  return response.data;
};

// --- CALENDAR ---
export type CalendarDayStatus = "worked" | "off" | "closed" | "holiday";

export interface CalendarDay {
  date: string;
  is_worked: boolean;
  status: CalendarDayStatus;
  is_override: boolean;
}

export interface CalendarAgendaItem {
  id: string;
  date: string;
  end_date?: string | null;
  category: "leave" | "planning" | "absence" | "event";
  title: string;
  subtitle?: string | null;
  status: string;
  worker_id?: number | null;
  worker_name?: string | null;
  leave_type_code?: string | null;
}

export const getCalendar = async (employerId: number, year: number, month: number) => {
  const res = await api.get<CalendarDay[]>(`/calendar/${employerId}/${year}/${month}`);
  return res.data;
};

export const toggleCalendarDay = async (employerId: number, date: string, status: CalendarDayStatus) => {
  const res = await api.post(`/calendar/toggle`, { employer_id: employerId, date, status });
  return res.data;
};

export const getCalendarAgenda = async (employerId: number, year: number, month: number, workerId?: number | null) => {
  const res = await api.get<CalendarAgendaItem[]>(`/calendar/${employerId}/${year}/${month}/agenda`, {
    params: workerId ? { worker_id: workerId } : undefined,
  });
  return res.data;
};

export async function downloadWorkersTemplate(options?: {
  prefilled?: boolean;
  employerId?: number;
  format?: "xlsx" | "csv";
}) {
  const params: Record<string, string | number | boolean> = {};
  if (options?.prefilled) params.prefilled = true;
  if (typeof options?.employerId === "number") params.employer_id = options.employerId;
  if (options?.format) params.export_format = options.format;
  const response = await api.get("/workers/import/template", {
    params,
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  const contentDisposition = response.headers?.["content-disposition"] ?? "";
  const filenameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  const fallbackName = options?.prefilled ? `salaries_existants.${extension}` : `modele_import_salaries.${extension}`;
  link.setAttribute("download", filenameMatch?.[1] ?? fallbackName);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export interface ImportIssue {
  row_number: number;
  code: string;
  message: string;
  column?: string | null;
  value?: string | null;
}

export interface TabularImportReport {
  mode: "create" | "update" | "mixed";
  total_rows: number;
  processed_rows: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
  unknown_columns: string[];
  missing_columns: string[];
  issues: ImportIssue[];
  error_report_csv?: string | null;
}

export interface WorkersImportResponse {
  imported: number;
  updated: number;
  skipped: number;
  errors: string[];
  report?: TabularImportReport;
}

export async function previewWorkersImport(file: File, updateExisting: boolean): Promise<TabularImportReport> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("update_existing", String(updateExisting));
  const response = await api.post<TabularImportReport>("/workers/import/preview", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function importWorkers(file: File, updateExisting: boolean): Promise<WorkersImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("update_existing", String(updateExisting));
  const response = await api.post<WorkersImportResponse>("/workers/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function downloadTalentsTemplate(
  resource: "skills" | "trainings" | "employee-skills",
  options?: { employerId?: number; prefilled?: boolean; format?: "xlsx" | "csv" }
) {
  const response = await api.get("/talents/import/template", {
    params: {
      resource,
      employer_id: options?.employerId,
      prefilled: options?.prefilled ?? false,
      export_format: options?.format ?? "xlsx",
    },
    responseType: "blob",
  });
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `talents_${resource}_template.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export async function importTalentsResource(
  resource: "skills" | "trainings" | "employee-skills",
  file: File,
  options?: { employerId?: number; updateExisting?: boolean; dryRun?: boolean }
): Promise<TabularImportReport> {
  const formData = new FormData();
  formData.append("resource", resource);
  formData.append("file", file);
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("dry_run", String(options?.dryRun ?? false));
  if (typeof options?.employerId === "number") {
    formData.append("employer_id", String(options.employerId));
  }
  const response = await api.post<TabularImportReport>("/talents/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function downloadSstIncidentsTemplate(options?: {
  employerId?: number;
  prefilled?: boolean;
  format?: "xlsx" | "csv";
}) {
  const response = await api.get("/sst/incidents/template", {
    params: {
      employer_id: options?.employerId,
      prefilled: options?.prefilled ?? false,
      export_format: options?.format ?? "xlsx",
    },
    responseType: "blob",
  });
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `sst_incidents_template.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export async function importSstIncidents(
  file: File,
  options?: { updateExisting?: boolean; dryRun?: boolean }
): Promise<TabularImportReport> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("dry_run", String(options?.dryRun ?? false));
  const response = await api.post<TabularImportReport>("/sst/incidents/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function downloadRecruitmentImportTemplate(
  resource: "candidates" | "jobs",
  options?: { employerId?: number; prefilled?: boolean; format?: "xlsx" | "csv" }
) {
  const response = await api.get("/recruitment/import/template", {
    params: {
      resource,
      employer_id: options?.employerId,
      prefilled: options?.prefilled ?? false,
      export_format: options?.format ?? "xlsx",
    },
    responseType: "blob",
  });
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `recruitment_${resource}_template.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export async function importRecruitmentResource(
  resource: "candidates" | "jobs",
  file: File,
  options?: { updateExisting?: boolean; dryRun?: boolean }
): Promise<TabularImportReport> {
  const formData = new FormData();
  formData.append("resource", resource);
  formData.append("file", file);
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("dry_run", String(options?.dryRun ?? false));
  const response = await api.post<TabularImportReport>("/recruitment/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function downloadAbsencesTemplate(options?: {
  employerId?: number;
  prefilled?: boolean;
  format?: "xlsx" | "csv";
}) {
  const response = await api.get("/absences/import/template", {
    params: {
      employer_id: options?.employerId,
      prefilled: options?.prefilled ?? false,
      export_format: options?.format ?? "xlsx",
    },
    responseType: "blob",
  });
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `absences_template.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export async function importAbsencesFile(
  file: File,
  options?: { updateExisting?: boolean; dryRun?: boolean }
): Promise<TabularImportReport> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("dry_run", String(options?.dryRun ?? false));
  const response = await api.post<TabularImportReport>("/absences/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function downloadCustomContractsTemplate(options?: {
  employerId?: number;
  prefilled?: boolean;
  format?: "xlsx" | "csv";
}) {
  const response = await api.get("/custom-contracts/import/template", {
    params: {
      employer_id: options?.employerId,
      prefilled: options?.prefilled ?? false,
      export_format: options?.format ?? "xlsx",
    },
    responseType: "blob",
  });
  const extension = options?.format === "csv" ? "csv" : "xlsx";
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `custom_contracts_template.${extension}`);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export async function importCustomContractsFile(
  file: File,
  options?: { updateExisting?: boolean; dryRun?: boolean }
): Promise<TabularImportReport> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("dry_run", String(options?.dryRun ?? false));
  const response = await api.post<TabularImportReport>("/custom-contracts/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export interface SystemImportManifestSummary {
  source_system?: string | null;
  package_version?: string | null;
  export_version?: string | null;
  modules_detected: string[];
  modules_requested: string[];
  expected_records: Record<string, number>;
  detected_records: Record<string, number>;
  compatibility_warnings: string[];
}

export interface SystemImportModuleReport {
  module: string;
  expected_records?: number | null;
  detected_records: number;
  processed_rows: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
  conflicts: number;
  unmapped_fields: string[];
  issues: ImportIssue[];
}

export interface SystemDataImportReport {
  dry_run: boolean;
  started_at: string;
  finished_at?: string | null;
  manifest: SystemImportManifestSummary;
  modules: SystemImportModuleReport[];
  total_processed_rows: number;
  total_created: number;
  total_updated: number;
  total_skipped: number;
  total_failed: number;
  total_conflicts: number;
  warnings: string[];
  errors: string[];
}

export interface SystemDataImportExecuteResponse {
  imported: number;
  updated: number;
  skipped: number;
  failed: number;
  conflicts: number;
  report: SystemDataImportReport;
}

export interface SystemDataImportOptions {
  updateExisting?: boolean;
  skipExactDuplicates?: boolean;
  continueOnError?: boolean;
  strictMode?: boolean;
  selectedModules?: string[];
}

function appendSystemImportOptions(formData: FormData, options?: SystemDataImportOptions) {
  formData.append("update_existing", String(options?.updateExisting ?? true));
  formData.append("skip_exact_duplicates", String(options?.skipExactDuplicates ?? true));
  formData.append("continue_on_error", String(options?.continueOnError ?? true));
  formData.append("strict_mode", String(options?.strictMode ?? false));
  if (options?.selectedModules && options.selectedModules.length > 0) {
    formData.append("selected_modules", options.selectedModules.join(","));
  }
}

export async function previewSystemDataImport(
  file: File,
  options?: SystemDataImportOptions
): Promise<SystemDataImportReport> {
  const formData = new FormData();
  formData.append("file", file);
  appendSystemImportOptions(formData, options);
  const response = await api.post<SystemDataImportReport>("/system-data-import/preview", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function executeSystemDataImport(
  file: File,
  options?: SystemDataImportOptions
): Promise<SystemDataImportExecuteResponse> {
  const formData = new FormData();
  formData.append("file", file);
  appendSystemImportOptions(formData, options);
  const response = await api.post<SystemDataImportExecuteResponse>("/system-data-import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export interface SystemExportManifestSummary {
  source_system?: string | null;
  package_version?: string | null;
  export_version?: string | null;
  modules_requested: string[];
  modules_exported: string[];
  detected_records: Record<string, number>;
  compatibility_warnings: string[];
}

export interface SystemDataExportOptions {
  selectedModules?: string[];
  employerId?: number;
  includeInactive?: boolean;
  includeDocumentContent?: boolean;
}

export interface SystemDataExportPreview {
  generated_at: string;
  options: {
    selected_modules: string[];
    employer_id?: number | null;
    include_inactive: boolean;
    include_document_content: boolean;
  };
  manifest: SystemExportManifestSummary;
  total_records: number;
  warnings: string[];
}

export interface SystemDataExportDownload {
  blob: Blob;
  filename: string;
}

function buildSystemExportPayload(options?: SystemDataExportOptions) {
  return {
    selected_modules: options?.selectedModules ?? [],
    employer_id: options?.employerId,
    include_inactive: options?.includeInactive ?? true,
    include_document_content: options?.includeDocumentContent ?? false,
  };
}

export async function previewSystemDataExport(
  options?: SystemDataExportOptions
): Promise<SystemDataExportPreview> {
  const response = await api.post<SystemDataExportPreview>(
    "/system-data-export/preview",
    buildSystemExportPayload(options)
  );
  return response.data;
}

export async function downloadSystemDataExport(
  options?: SystemDataExportOptions
): Promise<SystemDataExportDownload> {
  const response = await api.post("/system-data-export", buildSystemExportPayload(options), {
    responseType: "blob",
  });
  const disposition = String(response.headers?.["content-disposition"] || "");
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  const rawFilename = match?.[1] || `sirh_paie_export_${new Date().toISOString().slice(0, 10)}.zip`;
  const filename = decodeURIComponent(rawFilename.replace(/"/g, "").trim());
  return { blob: response.data as Blob, filename };
}

export async function downloadSystemDataUpdatePackage(
  options?: SystemDataExportOptions
): Promise<SystemDataExportDownload> {
  const response = await api.post("/system-data-export/update-package", buildSystemExportPayload(options), {
    responseType: "blob",
  });
  const disposition = String(response.headers?.["content-disposition"] || "");
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  const rawFilename = match?.[1] || `sirh_paie_update_package_${new Date().toISOString().slice(0, 10)}.zip`;
  const filename = decodeURIComponent(rawFilename.replace(/"/g, "").trim());
  return { blob: response.data as Blob, filename };
}

export interface SystemUpdateJobStatus {
  job_id: string;
  status: string;
  stage: string;
  progress: number;
  environment_mode: string;
  package_filename: string;
  package_sha256?: string | null;
  package_version?: string | null;
  started_at: string;
  finished_at?: string | null;
  backup_path?: string | null;
  rollback_performed: boolean;
  logs: string[];
  error?: string | null;
}

export async function startSystemUpdate(file: File): Promise<SystemUpdateJobStatus> {
  const formData = new FormData();
  formData.append("package_file", file);
  const response = await api.post<SystemUpdateJobStatus>("/system-update/start", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function getSystemUpdateJob(jobId: string): Promise<SystemUpdateJobStatus> {
  const response = await api.get<SystemUpdateJobStatus>(`/system-update/jobs/${jobId}`);
  return response.data;
}

export async function listSystemUpdateJobs(limit = 20): Promise<SystemUpdateJobStatus[]> {
  const response = await api.get<SystemUpdateJobStatus[]>("/system-update/jobs", {
    params: { limit },
  });
  return response.data;
}

export interface RoleCatalogItem {
  code: string;
  label: string;
  scope: string;
  base_role_code?: string | null;
  modules: Record<string, string[]>;
  is_active: boolean;
}

export interface RoleCatalogPublicItem {
  code: string;
  label: string;
  scope: string;
  base_role_code?: string | null;
  is_active: boolean;
}

export interface PublicRegistrationRole {
  code: string;
  label: string;
  scope: string;
}

export interface PublicRegistrationConfig {
  enabled: boolean;
  password_policy: string;
  allowed_roles: PublicRegistrationRole[];
}

export interface PublicRegisterPayload {
  username: string;
  password: string;
  full_name?: string;
  role_code: string;
  worker_matricule: string;
}

export interface PublicRegisterResult {
  user_id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
  employer_id?: number | null;
  worker_id: number;
  created_at: string;
}

export interface PublicDemoAccount {
  label: string;
  role_code: string;
  username: string;
}

export interface IamPermissionCatalogItem {
  code: string;
  module: string;
  action: string;
  label: string;
  sensitivity: string;
}

export interface IamRoleActivation {
  role_code: string;
  is_enabled: boolean;
}

export interface IamUserRoleAssignment {
  id?: number;
  user_id?: number;
  role_code: string;
  employer_id?: number | null;
  worker_id?: number | null;
  is_active: boolean;
  valid_from?: string | null;
  valid_until?: string | null;
  delegated_by_user_id?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface IamUserPermissionOverride {
  id?: number;
  user_id?: number;
  permission_code: string;
  is_allowed: boolean;
  reason?: string | null;
  expires_at?: string | null;
  updated_by_user_id?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface AppUserLight {
  id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
  employer_id?: number | null;
  worker_id?: number | null;
  is_active: boolean;
}

export interface AppUser extends AppUserLight {
  created_at: string;
  updated_at: string;
}

export interface AppUserCreatePayload {
  username: string;
  password: string;
  full_name?: string | null;
  role_code: string;
  employer_id?: number | null;
  worker_id?: number | null;
  is_active?: boolean;
}

export interface AppUserUpdatePayload {
  full_name?: string | null;
  password?: string | null;
  role_code?: string | null;
  employer_id?: number | null;
  worker_id?: number | null;
  is_active?: boolean;
}

export interface AuditLogEntry {
  id: number;
  actor_user_id?: number | null;
  actor_role?: string | null;
  actor_username?: string | null;
  actor_full_name?: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  route?: string | null;
  employer_id?: number | null;
  worker_id?: number | null;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  created_at: string;
}

export interface UserAccessPreview {
  role_code: string;
  effective_role_code: string;
  role_label: string;
  role_scope: string;
  module_permissions: Record<string, string[]>;
  assigned_role_codes: string[];
}

export interface RolePermissionsPayload {
  role_code: string;
  modules: Record<string, string[]>;
}

export async function listRoleCatalog(options?: { assignableOnly?: boolean }): Promise<RoleCatalogItem[]> {
  const response = await api.get<RoleCatalogItem[]>("/auth/roles", {
    params: { assignable_only: options?.assignableOnly ?? false },
  });
  return response.data;
}

export async function listPublicRoleCatalog(): Promise<RoleCatalogPublicItem[]> {
  const response = await publicApi.get<RoleCatalogPublicItem[]>("/auth/public-roles");
  return response.data;
}

export async function getPublicRegistrationConfig(): Promise<PublicRegistrationConfig> {
  const response = await publicApi.get<PublicRegistrationConfig>("/auth/public-registration-config");
  return response.data;
}

export async function registerPublicUser(payload: PublicRegisterPayload): Promise<PublicRegisterResult> {
  const response = await publicApi.post<PublicRegisterResult>("/auth/register", payload);
  return response.data;
}

export async function listPublicDemoAccounts(): Promise<PublicDemoAccount[]> {
  const response = await publicApi.get<PublicDemoAccount[]>("/auth/demo-accounts");
  return response.data;
}

export async function listAuthUsers(options?: { employerId?: number; roleCode?: string }): Promise<AppUserLight[]> {
  const response = await api.get<AppUserLight[]>("/auth/users", {
    params: {
      employer_id: options?.employerId,
      role_code: options?.roleCode,
    },
  });
  return response.data;
}

export async function createAuthUser(payload: AppUserCreatePayload): Promise<AppUser> {
  const response = await api.post<AppUser>("/auth/users", payload);
  return response.data;
}

export async function updateAuthUser(userId: number, payload: AppUserUpdatePayload): Promise<AppUser> {
  const response = await api.patch<AppUser>(`/auth/users/${userId}`, payload);
  return response.data;
}

export async function deleteAuthUser(userId: number, currentPassword: string): Promise<AppUser> {
  const response = await api.delete<AppUser>(`/auth/users/${userId}`, {
    data: { current_password: currentPassword },
  });
  return response.data;
}

export async function listAuditLogs(options?: { limit?: number; userId?: number; action?: string }): Promise<AuditLogEntry[]> {
  const response = await api.get<AuditLogEntry[]>("/auth/audit-logs", {
    params: {
      limit: options?.limit ?? 50,
      user_id: options?.userId,
      action: options?.action,
    },
  });
  return response.data;
}

export async function listIamPermissions(): Promise<IamPermissionCatalogItem[]> {
  const response = await api.get<IamPermissionCatalogItem[]>("/auth/iam/permissions");
  return response.data;
}

export async function listIamRoleActivations(): Promise<IamRoleActivation[]> {
  const response = await api.get<IamRoleActivation[]>("/auth/iam/role-activations");
  return response.data;
}

export async function setIamRoleActivation(roleCode: string, isEnabled: boolean): Promise<IamRoleActivation> {
  const response = await api.put<IamRoleActivation>(`/auth/iam/role-activations/${encodeURIComponent(roleCode)}`, {
    is_enabled: isEnabled,
  });
  return response.data;
}

export async function setRolePermissions(
  roleCode: string,
  modules: Record<string, string[]>
): Promise<RolePermissionsPayload> {
  const response = await api.put<RolePermissionsPayload>(`/auth/iam/roles/${encodeURIComponent(roleCode)}/permissions`, {
    modules,
  });
  return response.data;
}

export async function getUserRoleAssignments(userId: number): Promise<IamUserRoleAssignment[]> {
  const response = await api.get<IamUserRoleAssignment[]>(`/auth/iam/users/${userId}/roles`);
  return response.data;
}

export async function setUserRoleAssignments(userId: number, assignments: IamUserRoleAssignment[]): Promise<IamUserRoleAssignment[]> {
  const payload = {
    assignments: assignments.map((item) => ({
      role_code: item.role_code,
      employer_id: item.employer_id ?? null,
      worker_id: item.worker_id ?? null,
      is_active: item.is_active,
      valid_from: item.valid_from ?? null,
      valid_until: item.valid_until ?? null,
    })),
  };
  const response = await api.put<IamUserRoleAssignment[]>(`/auth/iam/users/${userId}/roles`, payload);
  return response.data;
}

export async function getUserAccessPreview(userId: number): Promise<UserAccessPreview> {
  const response = await api.get<UserAccessPreview>(`/auth/iam/users/${userId}/access-preview`);
  return response.data;
}

export async function getUserPermissionOverrides(userId: number): Promise<IamUserPermissionOverride[]> {
  const response = await api.get<IamUserPermissionOverride[]>(`/auth/iam/users/${userId}/permission-overrides`);
  return response.data;
}

export async function setUserPermissionOverrides(
  userId: number,
  overrides: IamUserPermissionOverride[]
): Promise<IamUserPermissionOverride[]> {
  const response = await api.put<IamUserPermissionOverride[]>(`/auth/iam/users/${userId}/permission-overrides`, {
    overrides: overrides.map((item) => ({
      permission_code: item.permission_code,
      is_allowed: item.is_allowed,
      reason: item.reason ?? null,
      expires_at: item.expires_at ?? null,
    })),
  });
  return response.data;
}
