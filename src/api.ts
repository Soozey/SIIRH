// src/api.ts
import axios from "axios";

// Instance axios commune pour tout le frontend
export const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

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
