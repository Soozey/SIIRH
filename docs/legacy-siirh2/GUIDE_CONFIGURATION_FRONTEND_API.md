# 🔧 Guide de Configuration Frontend pour l'API Hiérarchique

## 🎯 Problème de Performance Résolu

### Symptôme
Les requêtes API prenaient 2 secondes au lieu de 50ms.

### Cause
Résolution DNS lente de "localhost" sur Windows.

### Solution
Utiliser `127.0.0.1` au lieu de `localhost`.

---

## ✅ Configuration Recommandée

### Option 1: Fichier de Configuration Centralisé

**Créer: `siirh-frontend/src/config/api.ts`**

```typescript
// Configuration de l'API
export const API_CONFIG = {
  // Utiliser 127.0.0.1 pour de meilleures performances sur Windows
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 10000, // 10 secondes
  headers: {
    'Content-Type': 'application/json',
  },
};

// Export pour axios
export const getApiBaseURL = () => API_CONFIG.baseURL;
```

**Utilisation dans les composants:**

```typescript
import { API_CONFIG } from '@/config/api';
import axios from 'axios';

const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: API_CONFIG.headers,
});

// Exemple d'utilisation
const fetchTree = async (employerId: number) => {
  const response = await api.get(
    `/employers/${employerId}/hierarchical-organization/tree`
  );
  return response.data;
};
```

### Option 2: Variable d'Environnement

**Créer/Modifier: `siirh-frontend/.env`**

```env
# API Configuration
VITE_API_URL=http://127.0.0.1:8000

# Pour la production
# VITE_API_URL=https://api.votre-domaine.com
```

**Utilisation:**

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
```

---

## 🚀 Optimisations Recommandées

### 1. Cache Local pour les Options en Cascade

```typescript
import { useQuery } from '@tanstack/react-query';

const useCascadingOptions = (employerId: number, parentId?: number) => {
  return useQuery({
    queryKey: ['cascading-options', employerId, parentId],
    queryFn: () => fetchCascadingOptions(employerId, parentId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });
};
```

### 2. Debounce pour la Recherche

```typescript
import { useMemo } from 'react';
import debounce from 'lodash/debounce';

const useSearchNodes = () => {
  const debouncedSearch = useMemo(
    () =>
      debounce(async (query: string) => {
        if (query.length < 2) return [];
        const response = await api.get('/search', { params: { query } });
        return response.data;
      }, 300), // 300ms de délai
    []
  );

  return debouncedSearch;
};
```

### 3. Préchargement des Données

```typescript
// Précharger l'arbre au montage du composant
useEffect(() => {
  if (employerId) {
    queryClient.prefetchQuery({
      queryKey: ['organizational-tree', employerId],
      queryFn: () => fetchOrganizationalTree(employerId),
    });
  }
}, [employerId]);
```

---

## 📊 Performances Attendues

Avec la configuration optimisée:

| Opération | Temps Attendu | Statut |
|-----------|---------------|--------|
| Chargement arbre | < 50ms | ✅ Excellent |
| Options cascade | < 50ms | ✅ Excellent |
| Recherche | < 100ms | ✅ Bon |
| Création nœud | < 100ms | ✅ Bon |
| Mise à jour | < 100ms | ✅ Bon |

---

## 🔍 Vérification de la Configuration

### Test Rapide

```typescript
// Test de connexion API
const testApiConnection = async () => {
  const start = performance.now();
  try {
    const response = await fetch(`${API_BASE_URL}/employers`);
    const elapsed = performance.now() - start;
    
    console.log(`✅ API accessible en ${elapsed.toFixed(2)}ms`);
    
    if (elapsed > 200) {
      console.warn('⚠️ Temps de réponse élevé. Vérifiez la configuration.');
    }
    
    return response.ok;
  } catch (error) {
    console.error('❌ Erreur de connexion API:', error);
    return false;
  }
};
```

---

## 🛠️ Dépannage

### Problème: Requêtes toujours lentes

**Vérifications:**

1. **Vérifier l'URL utilisée**
   ```typescript
   console.log('API URL:', API_BASE_URL);
   // Doit afficher: http://127.0.0.1:8000
   ```

2. **Tester directement**
   ```bash
   curl http://127.0.0.1:8000/employers
   ```

3. **Vérifier le fichier hosts**
   - Windows: `C:\Windows\System32\drivers\etc\hosts`
   - Doit contenir: `127.0.0.1 localhost`

### Problème: CORS

Si vous rencontrez des erreurs CORS:

```python
# siirh-backend/app/main.py
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
```

---

## 📝 Checklist de Migration

- [ ] Créer le fichier de configuration API
- [ ] Mettre à jour les variables d'environnement
- [ ] Remplacer `localhost` par `127.0.0.1` dans le code
- [ ] Tester les performances
- [ ] Implémenter le cache pour les options en cascade
- [ ] Ajouter le debounce sur la recherche
- [ ] Vérifier que tous les composants utilisent la nouvelle configuration
- [ ] Tester en développement
- [ ] Documenter pour l'équipe

---

## 🎉 Résultat Attendu

Après la configuration:
- ✅ Temps de réponse < 100ms
- ✅ Interface réactive
- ✅ Expérience utilisateur fluide
- ✅ Pas de délais perceptibles
