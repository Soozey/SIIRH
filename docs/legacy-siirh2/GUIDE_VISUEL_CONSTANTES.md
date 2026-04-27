# 🎯 Guide Visuel - Où Cliquer pour Accéder aux Constantes

## 📍 **Étape 1 : Accès Principal**

### **Dans la Barre de Navigation (en haut de l'écran)**
```
┌─────────────────────────────────────────────────────────────────┐
│ SIRH Paie                                                       │
├─────────────────────────────────────────────────────────────────┤
│ [Employeurs] [Travailleurs] [Bulletin] [HS] [Absences] [Congés] │
│ [Reporting] [Documents] ← CLIQUEZ ICI                           │
└─────────────────────────────────────────────────────────────────┘
```

**👆 Cliquez sur "Documents" (avec l'icône engrenage ⚙️)**

---

## 📍 **Étape 2 : Page Documents - 3 Options**

### **Interface de la Page Documents**
```
┌─────────────────────────────────────────────────────────────────┐
│ Gestion des Documents                    [🧪 Test API] [⚙️ Constantes] [➕ Nouveau Document] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 📋 Templates Prédéfinis                                         │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│ │📄 Certificat│ │📄 Attestation│ │📄 Contrat   │                │
│ │de travail   │ │d'emploi     │ │de travail   │                │
│ │             │ │             │ │             │                │
│ │[✏️ Utiliser] │ │[✏️ Utiliser] │ │[✏️ Utiliser] │                │
│ └─────────────┘ └─────────────┘ └─────────────┘                │
│                                                                 │
│ 📝 Documents Personnalisés                                      │
│ [Aucun document personnalisé - Créer votre premier document]   │
└─────────────────────────────────────────────────────────────────┘
```

### **3 Façons d'Accéder aux Constantes :**

#### **Option A : Bouton "🧪 Test API"** (Nouveau !)
- **Action** : Ouvre une page de test des constantes
- **Utilité** : Voir toutes les données chargées depuis l'API
- **Parfait pour** : Vérifier que tout fonctionne

#### **Option B : Bouton "⚙️ Constantes"**
- **Action** : Ouvre le gestionnaire de constantes
- **Utilité** : Explorer toutes les constantes par catégorie
- **Parfait pour** : Comprendre les données disponibles

#### **Option C : Bouton "➕ Nouveau Document"**
- **Action** : Ouvre l'éditeur avec palette de champs
- **Utilité** : Créer un document en utilisant les constantes
- **Parfait pour** : Utilisation pratique

---

## 📍 **Étape 3A : Test API (Nouveau !)**

### **Page de Test des Constantes**
```
┌─────────────────────────────────────────────────────────────────┐
│ 🧪 Test des Constantes SIIRH                                   │
│ Vérifiez que toutes les constantes sont bien chargées          │
├─────────────────────────────────────────────────────────────────┤
│ [Constantes de Paie] [Constantes Métier] [Champs de Documents] │
│ [Catégories de Champs] [Règles de Validation]                  │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Données chargées avec succès                                │
│ 📊 Éléments: 5                                                 │
│ 💾 Taille: 2847 caractères                                     │
│ 🔗 Type: Object                                                │
│                                                                 │
│ {                                                               │
│   "cotisations": {                                              │
│     "cnaps": { "salarial": 1.0, "patronal_general": 13.0 }    │
│     "smie": { "salarial": 0.0, "patronal": 0.0 }             │
│   },                                                            │
│   "majorations": { ... }                                       │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

**👆 Cliquez sur les onglets pour voir différents types de constantes**

---

## 📍 **Étape 3B : Gestionnaire de Constantes**

### **Interface du Gestionnaire**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚙️ Référentiel de Constantes                          [✖️ Fermer] │
│ Gestion centralisée des données de référence du système SIIRH  │
├─────────────────────────────────────────────────────────────────┤
│ [💰 Paie] [🏢 Métier] [📄 Documents] [✅ Validation]            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 🧮 Taux de cotisations                                [▼]       │
│ 🧮 Majorations heures supplémentaires                [▼]       │
│ 🧮 Constantes de calcul                              [▼]       │
│ 🧮 Formules prédéfinies                              [▼]       │
│ 🧮 Variables disponibles                             [▼]       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**👆 Cliquez sur les onglets et les sections [▼] pour explorer**

---

## 📍 **Étape 3C : Éditeur de Documents**

### **Interface de l'Éditeur**
```
┌─────────────────────────────────────────────────────────────────┐
│ ✏️ Éditeur de document                    [👁️ Aperçu] [💾 Enregistrer] │
├─────────────────┬───────────────────────────────────────────────┤
│ Champs disponibles │ Zone d'édition                            │
│                 │                                               │
│ 🏢 Employeur     │ Tapez votre texte ici...                    │
│ ▼ Raison sociale│                                               │
│ ▼ Adresse       │ Cliquez sur les champs à gauche pour        │
│ ▼ NIF           │ les insérer automatiquement                  │
│ ▼ Représentant  │                                               │
│                 │ Exemple:                                      │
│ 👤 Travailleur  │ Je certifie que {{nom_complet}} travaille   │
│ ▼ Nom complet   │ dans notre entreprise {{raison_sociale}}    │
│ ▼ Matricule     │ depuis le {{date_embauche}}.                │
│ ▼ Poste         │                                               │
│ ▼ Salaire base  │                                               │
│                 │                                               │
│ 💰 Paie        │                                               │
│ ▼ Période       │                                               │
│ ▼ Salaire brut  │                                               │
│                 │                                               │
│ 🗓️ Système      │                                               │
│ ▼ Date aujourd'hui                                              │
│ ▼ Année courante│                                               │
└─────────────────┴───────────────────────────────────────────────┘
```

**👆 Cliquez sur les champs (▼) pour les insérer dans votre document**

---

## 🚀 **Accès Rapide - URLs Directes**

### **Si vous connaissez les URLs :**
```bash
# Page principale des documents
http://localhost:3000/documents

# Test des constantes (nouveau)
http://localhost:3000/constants-demo

# API directe (pour développeurs)
http://localhost:8000/constants/payroll
http://localhost:8000/docs
```

---

## 🎯 **Résumé - Où Cliquer**

| Objectif | Où Cliquer | Résultat |
|----------|-------------|----------|
| **Voir les constantes** | Menu "Documents" → "🧪 Test API" | Page de test avec toutes les données |
| **Explorer les constantes** | Menu "Documents" → "⚙️ Constantes" | Gestionnaire complet par catégories |
| **Utiliser les constantes** | Menu "Documents" → "➕ Nouveau Document" | Éditeur avec palette de champs |
| **Template rapide** | Menu "Documents" → Cliquer sur un template | Éditeur pré-rempli |

---

## 💡 **Conseils d'Utilisation**

### **Pour Débuter :**
1. **Cliquez sur "🧪 Test API"** pour vérifier que tout fonctionne
2. **Explorez "⚙️ Constantes"** pour voir toutes les données disponibles
3. **Testez "➕ Nouveau Document"** pour créer votre premier document

### **Pour Créer un Document :**
1. Choisissez un template OU créez un nouveau document
2. Dans l'éditeur, cliquez sur les champs dans la palette de gauche
3. Les champs s'insèrent automatiquement : `{{nom_du_champ}}`
4. Cliquez "Aperçu" pour voir le rendu final
5. Cliquez "Enregistrer" pour sauvegarder

### **En Cas de Problème :**
- Vérifiez que le serveur backend est démarré : `python start_server.py`
- Vérifiez que le serveur frontend est démarré : `npm run dev`
- Testez l'API directement : http://localhost:8000/docs

**Les constantes sont maintenant accessibles en 1 clic depuis le menu "Documents" !**