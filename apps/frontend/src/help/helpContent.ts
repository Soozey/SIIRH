export type HelpRole = "employe" | "manager" | "rh" | "direction" | "inspecteur" | "comptable" | "general";
export type HelpModuleCode =
  | "dashboard"
  | "workforce"
  | "payroll"
  | "time_absence"
  | "recruitment"
  | "contracts"
  | "compliance"
  | "reporting"
  | "employee_portal"
  | "master_data";

export type HelpTopic = {
  id: string;
  title: string;
  summary: string;
  workflows: string[];
  businessRules: string[];
  frequentErrors: string[];
  roles: HelpRole[];
};

export type RoleGuide = {
  role: HelpRole;
  title: string;
  canSee: string[];
  canDo: string[];
  cannotDo: string[];
};

export type ContextHelpItem = {
  key: string;
  module: HelpModuleCode;
  page: string;
  field?: string;
  title: string;
  roleText: Partial<Record<HelpRole, string>>;
  example?: string;
  rule?: string;
};

export const helpModules: Array<{
  code: HelpModuleCode;
  title: string;
  description: string;
  topics: HelpTopic[];
}> = [
  {
    code: "workforce",
    title: "RH / Dossiers salariés",
    description: "Base unique employeurs, travailleurs, structure et documents RH.",
    topics: [
      {
        id: "workforce-master-data",
        title: "Saisie unique des données RH",
        summary: "Les données salarié doivent être modifiées à la source canonique pour être visibles partout.",
        workflows: [
          "Créer ou mettre à jour le salarié dans Travailleurs.",
          "Vérifier l'affectation employeur et organisation.",
          "Contrôler la vue Salarié 360 si une donnée n'apparaît pas dans un autre module.",
        ],
        businessRules: [
          "Un salarié ne doit pas être recréé dans plusieurs modules.",
          "Les modules affichent de préférence la vue maître lorsque disponible.",
        ],
        frequentErrors: [
          "Modifier un champ historique de worker au lieu du dossier maître.",
          "Oublier l'employeur ou l'affectation organisationnelle.",
        ],
        roles: ["rh", "direction", "manager"],
      },
    ],
  },
  {
    code: "payroll",
    title: "Paie",
    description: "Préparation des runs, variables, journaux et bulletins.",
    topics: [
      {
        id: "payroll-variables",
        title: "Variables de paie et impact",
        summary: "Les absences, primes et HS/HM influencent la paie sans changer le moteur de calcul manuellement.",
        workflows: [
          "Préparer la période.",
          "Importer ou saisir les variables.",
          "Prévisualiser le bulletin avant impression ou export.",
        ],
        businessRules: [
          "Une absence validée ou une variable importée alimente la paie sur la même période.",
          "Le journal de paie sert de contrôle avant clôture.",
        ],
        frequentErrors: [
          "Importer des variables sur une mauvaise période.",
          "Confondre prime structurelle et variable mensuelle.",
        ],
        roles: ["rh", "comptable", "direction", "general"],
      },
    ],
  },
  {
    code: "time_absence",
    title: "Congés / Absences",
    description: "Demandes d'absence, circuits de validation, soldes et rapprochement pointage.",
    topics: [
      {
        id: "leave-annual",
        title: "Congé annuel et validation",
        summary: "Le congé payé s'acquiert à 2,5 jours par mois de service effectif et suit un circuit de validation.",
        workflows: [
          "Le salarié soumet la demande.",
          "Le N+1 et/ou RH valident selon la règle.",
          "La demande validée alimente soldes, pointage et paie.",
        ],
        businessRules: [
          "La première fraction de 15 jours doit être surveillée après ouverture du droit.",
          "Une requalification change l'impact sur solde, paie et reporting.",
        ],
        frequentErrors: [
          "Demander un congé sans vérifier le solde prévisionnel.",
          "Oublier le justificatif obligatoire pour maladie ou cas paramétrés.",
        ],
        roles: ["employe", "manager", "rh", "general"],
      },
    ],
  },
  {
    code: "recruitment",
    title: "Recrutement",
    description: "Fiches de poste, annonces, candidats, entretiens et conversion vers le salarié.",
    topics: [
      {
        id: "recruitment-flow",
        title: "Chaîne recrutement complète",
        summary: "La chaîne standard est fiche de poste -> annonce -> candidatures -> décision -> contrat.",
        workflows: [
          "Préparer la fiche de poste ou partir d'un modèle.",
          "Générer l'annonce et publier.",
          "Traiter les candidatures et convertir le candidat retenu.",
        ],
        businessRules: [
          "Les suggestions sont modifiables et doivent être validées par RH.",
          "L'inspection intervient en contrôle a posteriori, sans bloquer la publication.",
        ],
        frequentErrors: [
          "Publier une annonce sans vérifier le type de contrat suggéré.",
          "Dupliquer une fiche RH au lieu de la relier à l'existant.",
        ],
        roles: ["rh", "manager", "direction", "general"],
      },
    ],
  },
  {
    code: "contracts",
    title: "Contrats",
    description: "Contrats de travail, attestations et certificats, avec guidage Madagascar.",
    topics: [
      {
        id: "contracts-types",
        title: "Types de contrat Madagascar",
        summary: "Le système suggère CDI, CDD et variantes usuelles sans bloquer la saisie libre.",
        workflows: [
          "Choisir le salarié.",
          "Vérifier le type suggéré et les champs obligatoires.",
          "Générer le document puis l'imprimer ou l'ajuster.",
        ],
        businessRules: [
          "Le CDD doit rester limité dans le temps.",
          "Le contrat peut être actif avant contrôle inspection si le workflow l'autorise.",
        ],
        frequentErrors: [
          "Oublier la date d'effet ou le salaire.",
          "Confondre contrat d'essai et CDD.",
        ],
        roles: ["rh", "direction", "inspecteur", "general"],
      },
    ],
  },
  {
    code: "compliance",
    title: "Inspection du travail",
    description: "Contrôle, messages formels, plaintes, observations et suivi conformité.",
    topics: [
      {
        id: "inspection-scope",
        title: "Portefeuille inspecteur",
        summary: "L'inspecteur agit sur les entreprises et dossiers affectés à sa circonscription ou à son portefeuille.",
        workflows: [
          "Consulter le tableau de bord.",
          "Ouvrir l'entreprise ou le dossier.",
          "Tracer une observation, un avis ou une demande de correction.",
        ],
        businessRules: [
          "Chaque action sensible doit être historisée.",
          "Le contrôle peut être a posteriori pour contrats et offres.",
        ],
        frequentErrors: [
          "Envoyer un message sans objet ou sans destinataire.",
          "Traiter un dossier non affecté au mauvais inspecteur.",
        ],
        roles: ["inspecteur", "rh", "direction"],
      },
    ],
  },
  {
    code: "reporting",
    title: "Reporting",
    description: "Exports et contrôles transverses RH, paie, conformité et migration.",
    topics: [
      {
        id: "reporting-checks",
        title: "Contrôle et migration",
        summary: "Le reporting et les packages d'export servent à contrôler la cohérence et à préparer les migrations.",
        workflows: [
          "Prévisualiser avant export.",
          "Choisir le périmètre ou l'employeur.",
          "Télécharger le modèle ou le package adapté.",
        ],
        businessRules: [
          "Les packages de données doivent être prévisualisés avant import.",
          "Les modèles Excel métier facilitent les reprises sans toucher aux calculs.",
        ],
        frequentErrors: [
          "Exporter un périmètre trop large sans filtre employeur.",
          "Importer sans lire les avertissements du preview.",
        ],
        roles: ["rh", "direction", "comptable", "inspecteur", "general"],
      },
    ],
  },
];

export const roleGuides: RoleGuide[] = [
  {
    role: "employe",
    title: "Employé",
    canSee: ["Ses demandes, son portail, ses messages, ses documents autorisés."],
    canDo: ["Soumettre congés/absences.", "Consulter son dossier et ses informations utiles.", "Répondre aux échanges formels autorisés."],
    cannotDo: ["Voir la paie des autres.", "Modifier les paramètres RH globaux.", "Valider les demandes d'autres salariés."],
  },
  {
    role: "manager",
    title: "Manager / N+1",
    canSee: ["Les demandes et indicateurs de son équipe selon son scope."],
    canDo: ["Valider ou commenter les demandes.", "Suivre l'activité et certains tableaux d'équipe."],
    cannotDo: ["Administrer l'installation.", "Modifier les rôles IAM globaux."],
  },
  {
    role: "rh",
    title: "RH",
    canSee: ["Les modules RH, paie, recrutement, talents et conformité selon le scope."],
    canDo: ["Créer et corriger les dossiers.", "Paramétrer circuits et modèles.", "Piloter les imports/export métier."],
    cannotDo: ["Contourner les journaux d'audit.", "Affecter des rôles hors de son périmètre."],
  },
  {
    role: "direction",
    title: "Direction",
    canSee: ["Les vues de supervision, reporting et contrôle global autorisées."],
    canDo: ["Consulter, arbitrer, suivre les indicateurs et certaines validations."],
    cannotDo: ["Modifier tous les paramètres techniques si non autorisé.", "Agir hors du périmètre de l'entreprise."],
  },
  {
    role: "inspecteur",
    title: "Inspecteur du travail",
    canSee: ["Les entreprises, cas et messages affectés."],
    canDo: ["Contrôler, observer, demander correction, valider ou refuser selon workflow."],
    cannotDo: ["Accéder aux entreprises hors portefeuille.", "Administrer la paie interne des entreprises."],
  },
];

export const contextualHelp: ContextHelpItem[] = [
  {
    key: "recruitment.contract_type",
    module: "recruitment",
    page: "recruitment",
    field: "contract_type",
    title: "Type de contrat",
    roleText: {
      general: "Choisissez un type adapté au besoin réel. Le système suggère les formes courantes à Madagascar mais laisse la saisie libre.",
      rh: "Vérifiez si le besoin est permanent avant de retenir un CDD. Le guidage Madagascar signale les points d'attention.",
    },
    example: "Exemple: CDI pour un poste durable, CDD pour un besoin limité dans le temps.",
    rule: "Un CDD doit rester limité et justifié; le système alerte mais ne bloque pas.",
  },
  {
    key: "leave.annual_balance",
    module: "time_absence",
    page: "leaves",
    field: "leave_balance",
    title: "Solde de congé annuel",
    roleText: {
      employe: "Le solde affiché distingue acquis, consommé, en attente et prévisionnel.",
      rh: "Le solde dépend des droits acquis, des validations et des requalifications déjà tracées.",
    },
    example: "Exemple: une demande soumise peut réduire le solde prévisionnel sans être encore consommée.",
    rule: "Base légale suivie: 2,5 jours par mois de service effectif.",
  },
  {
    key: "leave.workflow",
    module: "time_absence",
    page: "leaves",
    field: "approval_mode",
    title: "Circuit de validation",
    roleText: {
      manager: "Selon le paramétrage, vous pouvez valider seul, avant RH, ou en parallèle.",
      rh: "Un circuit séquentiel déclenche l'étape suivante après validation; un circuit parallèle notifie plusieurs validateurs en même temps.",
    },
    example: "Exemple: Congé annuel = N+1 puis RH.",
    rule: "Les décisions importantes sont historisées et peuvent entraîner une requalification.",
  },
  {
    key: "contracts.guidance",
    module: "contracts",
    page: "contracts",
    field: "contract_guidance",
    title: "Assistant contrat Madagascar",
    roleText: {
      rh: "Le guidage rappelle les types disponibles, les langues proposées et les champs à vérifier avant édition.",
      inspecteur: "Le contrôle inspection peut rester a posteriori selon le workflow en place.",
    },
    example: "Exemple: date d'effet, fonction, catégorie professionnelle et salaire sont des points à vérifier.",
    rule: "Le guidage alerte sans bloquer la génération documentaire.",
  },
  {
    key: "payroll.period_run",
    module: "payroll",
    page: "payroll",
    field: "period",
    title: "Préparer la période de paie",
    roleText: {
      general: "Préparer la période permet de sécuriser les imports et de rattacher les variables au bon run de paie.",
    },
    example: "Exemple: créez d'abord le run d'avril avant d'importer primes ou HS/HM.",
    rule: "Les variables importées sont appliquées sur la période du run sélectionné.",
  },
  {
    key: "data_transfer.templates",
    module: "master_data",
    page: "data-transfer",
    field: "template_hub",
    title: "Modèles d'import",
    roleText: {
      rh: "Les modèles Excel servent aux reprises et migrations sans modifier directement les tables.",
      direction: "Le preview reste recommandé avant tout import de masse.",
    },
    example: "Exemple: téléchargez d'abord le modèle Salariés ou Contrats, complétez-le, puis importez.",
    rule: "Prévisualiser avant import limite les collisions et erreurs de structure.",
  },
];

export function getHelpModule(code: HelpModuleCode) {
  return helpModules.find((item) => item.code === code) ?? null;
}

export function getContextHelp(page: string, field?: string) {
  return contextualHelp.find((item) => item.page === page && item.field === field) ?? null;
}
