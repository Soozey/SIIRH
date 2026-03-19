/**
 * Configuration de l'API
 * 
 * IMPORTANT: Utiliser 127.0.0.1 au lieu de localhost pour de meilleures performances
 * sur Windows (évite le délai de résolution DNS de 2 secondes)
 */

export const API_CONFIG = {
  // Utiliser 127.0.0.1 pour de meilleures performances sur Windows
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 10000, // 10 secondes
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Retourne l'URL de base de l'API
 */
export const getApiBaseURL = (): string => {
  return API_CONFIG.baseURL;
};

/**
 * Construit une URL complète pour un endpoint
 */
export const buildApiUrl = (endpoint: string): string => {
  const base = API_CONFIG.baseURL.replace(/\/$/, ''); // Enlever le slash final
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${path}`;
};

/**
 * Configuration pour axios
 */
export const axiosConfig = {
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: API_CONFIG.headers,
};

// Export par défaut
export default API_CONFIG;
