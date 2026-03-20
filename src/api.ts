// src/api.ts
import axios from "axios";

export const AUTH_STORAGE_KEY = "siirh.auth.session";

export type AuthSession = {
  token: string;
  user_id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
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
export async function calculateHSBackendHS(payloadHS: any) {
  const response = await api.post("/hs/calculate-and-save", payloadHS);
  return response.data; // HSCalculationReadHS
}

/**
 * Récupère TOUS les enregistrements HS en base.
 * Utilise l'endpoint GET /hs/all
 */
export async function getAllHSCalculationsHS() {
  const response = await api.get("/hs/all");
  return response.data; // HSCalculationReadHS[]
}

/**
 * Supprime un enregistrement HS par son id_HS.
 * Utilise l'endpoint DELETE /hs/{hs_id}
 */
export async function deleteHSCalculationHS(hsId: number) {
  await api.delete(`/hs/${hsId}`);
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

/**
 * Import HS/HM data from Excel file for a specific payroll run.
 * Endpoint: POST /payroll-hs-hm/{payroll_run_id}/import-excel
 */
export async function importHsHmExcel(payrollRunId: number, file: File): Promise<ExcelImportSummary> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<ExcelImportSummary>(
    `/payroll-hs-hm/${payrollRunId}/import-excel`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data; // { id, employer_id, period, ... }
}

export async function downloadHsHmTemplate(payrollRunId?: number) {
  const url = payrollRunId
    ? `/payroll-hs-hm/template?payroll_run_id=${payrollRunId}`
    : "/payroll-hs-hm/template";

  const response = await api.get(url, {
    responseType: "blob",
  });

  // Create a link element, hide it, direct it towards the blob, and then 'click' it intentionally.
  // Create a link element, hide it, direct it towards the blob, and then 'click' it intentionally.
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.setAttribute("download", "Modele_Import_Paie.xlsx");
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

// --- PRIMES ---
export async function downloadPrimesTemplate(employerId: number) {
  const response = await api.get("/primes/template", {
    params: { employer_id: employerId },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", "Modele_Import_Primes.xlsx");
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}

export interface PrimesImportSummary {
  message: string;
  updated_items: number;
  errors: string[];
}

export async function importPrimesExcel(
  period: string,
  file: File,
  employerId: number
): Promise<PrimesImportSummary> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("period", period);
  formData.append("employer_id", employerId.toString());

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
export async function getAllHsHmForPayroll(payrollRunId: number) {
  const response = await api.get(`/payroll-hs-hm/${payrollRunId}/all`);
  return response.data; // PayrollHsHmOut[]
}

/**
 * Met à jour les heures HS/HM pour un travailleur donné.
 * Endpoint: PUT /payroll-hs-hm/{payroll_run_id}/{worker_id}
 */
export async function updateWorkerHsHm(payrollRunId: number, workerId: number, payload: any) {
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
export async function getWorkers(employerId?: number) {
  const params: any = {};
  if (employerId) params.employer_id = employerId;
  const response = await api.get("/workers", { params });
  return response.data; // Worker[]
}

export async function getEmployer(id: number) {
  const response = await api.get(`/employers/${id}`);
  return response.data;
}

export async function updateEmployer(id: number, data: any) {
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
}

export interface AssociationRequest {
  worker_id: number;
  prime_id: number;
  is_active: boolean;
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

export const updatePrimeValues = async (payrollRunId: number, workerId: number, values: any) => {
  const response = await api.put(`/primes/values/${payrollRunId}/${workerId}`, values);
  return response.data;
};

export const resetBulkPrimeValues = async (payrollRunId: number, workerIds: number[]) => {
  const response = await api.post(`/primes/values/${payrollRunId}/reset-bulk`, workerIds);
  return response.data;
};

// --- CALENDAR ---
export const getCalendar = async (employerId: number, year: number, month: number) => {
  const res = await api.get(`/calendar/${employerId}/${year}/${month}`);
  return res.data;
};

export const toggleCalendarDay = async (employerId: number, date: string, isWorked: boolean) => {
  const res = await api.post(`/calendar/toggle`, { employer_id: employerId, date, is_worked: isWorked });
  return res.data;
};

export async function downloadWorkersTemplate() {
  const response = await api.get("/workers/import/template", {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", "model_import_salaries.xlsx");
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
}
