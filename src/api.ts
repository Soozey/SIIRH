// src/api/api.ts
import axios from "axios";

// Instance axios commune pour tout le frontend
export const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

/**
 * Appelle le backend pour calculer les HS.
 * payloadHS doit respecter le modèle HSCalculationRequestHS côté backend.
 */
export async function calculateHSBackendHS(payloadHS: any) {
  const response = await api.post("/hs/calculate", payloadHS);
  return response.data;
}
