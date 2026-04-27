# 🎯 Guide d'Accès aux Constantes - Où les Trouver ?

## 📍 **Accès Principal - Menu Navigation**

### 1. **Dans l'Interface Web**
```
Menu Principal → "Documents" (icône engrenage ⚙️)
```

**Chemin complet :**
1. Ouvrez votre application SIIRH dans le navigateur
2. Dans la barre de navigation en haut, cliquez sur **"Documents"**
3. Vous arrivez sur la page de gestion des documents et constantes

### 2. **URL Directe**
```
http://localhost:3000/documents
```

---

## 🖥️ **Interface de Gestion des Constantes**

### **Page Documents - 3 Sections Principales**

#### 📊 **1. Bouton "Constantes"** (en haut à droite)
```
Page Documents → Bouton "Constantes" → Vue d'ensemble complète
```

**Ce que vous y trouvez :**
- **Onglet "Paie"** : Taux cotisations, majorations HS, formules
- **Onglet "Métier"** : Contrats, paiements, catégories professionnelles  
- **Onglet "Documents"** : Tous les champs disponibles (29 champs)
- **Onglet "Validation"** : Listes déroulantes, règles de validation

#### 📝 **2. Templates Prédéfinis**
```
Page Documents → Section "Templates Prédéfinis" → Cliquer sur un template
```

**Templates disponibles :**
- **Certificat de travail**
- **Attestation d'emploi**
- **Contrat de travail**

#### ✏️ **3. Bouton "Nouveau Document"**
```
Page Documents → "Nouveau Document" → Éditeur avec palette de champs
```

---

## 🎨 **Utilisation de l'Éditeur de Documents**

### **Interface de l'Éditeur**

```
┌─────────────────────────────────────────────────────────────┐
│                    Éditeur de document                      │
├─────────────────┬───────────────────────────────────────────┤
│   PALETTE       │           ZONE D'ÉDITION                  │
│   DE CHAMPS     │                                           │
│                 │   Tapez votre texte ici...                │
│ 🏢 Employeur    │                                           │
│ • Raison sociale│   Cliquez sur les champs à gauche        │
│ • Adresse       │   pour les insérer automatiquement       │
│ • NIF           │                                           │
│                 │   {{raison_sociale}} sera remplacé       │
│ 👤 Travailleur  │   par la vraie valeur en aperçu          │
│ • Nom complet   │                                           │
│ • Matricule     │                                           │
│ • Poste         │                                           │
│                 │                                           │
│ 💰 Paie        │                                           │
│ • Période       │                                           │
│ • Salaire brut  │                                           │
│                 │                                           │
│ 🗓️ Système      │                                           │
│ • Date aujourd'hui                                          │
│ • Année courante│                                           │
└─────────────────┴───────────────────────────────────────────┘
```

### **Comment Insérer des Champs**

1. **Cliquez sur un champ** dans la palette de gauche
2. Le champ s'insère automatiquement : `{{nom_du_champ}}`
3. **Bouton "Aperçu"** pour voir le rendu final avec les vraies données
4. **Bouton "Enregistrer"** pour sauvegarder votre document

---

## 🔗 **Accès Direct aux APIs (Pour Développeurs)**

### **Endpoints Disponibles**
```bash
# Serveur local (si démarré)
http://localhost:8000/constants/

# Endpoints principaux
/constants/payroll              # Constantes de paie
/constants/business             # Constantes métier  
/constants/document-fields      # Champs de documents
/constants/field-categories     # Champs par catégorie
/constants/validation          # Règles de validation
/constants/system-data         # Date, année courante
```

### **Documentation API**
```
http://localhost:8000/docs
```

---

## 📋 **Exemples Concrets d'Utilisation**

### **Exemple 1 : Créer un Certificat de Travail**

1. **Accès** : Menu "Documents" → "Templates Prédéfinis" → "Certificat de travail"
2. **Édition** : Le template s'ouvre avec des champs pré-insérés
3. **Personnalisation** : Cliquez sur d'autres champs dans la palette pour les ajouter
4. **Aperçu** : Cliquez "Aperçu" pour voir le rendu final
5. **Sauvegarde** : Cliquez "Enregistrer"

### **Exemple 2 : Voir Toutes les Constantes**

1. **Accès** : Menu "Documents" → Bouton "Constantes"
2. **Navigation** : Cliquez sur les onglets (Paie, Métier, Documents, Validation)
3. **Exploration** : Cliquez sur les sections pour voir le détail
4. **Fermeture** : Bouton "Fermer" pour revenir à la liste

### **Exemple 3 : Document Personnalisé**

1. **Accès** : Menu "Documents" → "Nouveau Document"
2. **Rédaction** : Tapez votre texte dans la zone d'édition
3. **Insertion** : Cliquez sur les champs dans la palette de gauche
4. **Résultat** : Les champs apparaissent comme `{{nom_du_champ}}`
5. **Test** : Bouton "Aperçu" pour voir avec les vraies données

---

## 🚀 **Démarrage Rapide**

### **Si l'Interface n'est Pas Accessible**

1. **Vérifiez le serveur backend** :
   ```bash
   cd siirh-backend
   python start_server.py
   ```

2. **Vérifiez le serveur frontend** :
   ```bash
   cd siirh-frontend  
   npm run dev
   ```

3. **Ouvrez l'application** :
   ```
   http://localhost:3000
   ```

4. **Cliquez sur "Documents"** dans le menu principal

---

## 🎯 **Résumé - Où Trouver les Constantes**

| Besoin | Où Aller | Action |
|--------|-----------|---------|
| **Voir toutes les constantes** | Menu "Documents" → "Constantes" | Explorer les onglets |
| **Créer un document** | Menu "Documents" → "Nouveau Document" | Utiliser la palette de champs |
| **Utiliser un template** | Menu "Documents" → Templates prédéfinis | Cliquer sur un template |
| **API pour développeurs** | http://localhost:8000/docs | Consulter la documentation |
| **Test des constantes** | Terminal backend | `python test_direct_endpoint.py` |

---

## 💡 **Points Clés à Retenir**

1. **Menu "Documents"** = Point d'entrée principal
2. **Bouton "Constantes"** = Vue d'ensemble complète  
3. **Palette de champs** = Insertion par clic simple
4. **Aperçu temps réel** = Voir le résultat immédiatement
5. **29 champs disponibles** = Couvrent tous les besoins documentaires

**Le référentiel de constantes est accessible via le menu "Documents" et transforme la création de documents en quelques clics !**