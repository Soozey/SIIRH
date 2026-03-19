"""
Constantes pour la génération de documents (contrats, certificats, attestations)
"""
from typing import Dict, List, Any

# Champs disponibles pour les documents
DOCUMENT_FIELDS = {
    # Informations employeur
    "employer": {
        "raison_sociale": {
            "label": "Raison sociale",
            "type": "text",
            "category": "Employeur",
            "description": "Nom de l'entreprise"
        },
        "adresse": {
            "label": "Adresse",
            "type": "text", 
            "category": "Employeur",
            "description": "Adresse complète de l'entreprise"
        },
        "ville": {
            "label": "Ville",
            "type": "text",
            "category": "Employeur", 
            "description": "Ville du siège social"
        },
        "nif": {
            "label": "NIF",
            "type": "text",
            "category": "Employeur",
            "description": "Numéro d'Identification Fiscale"
        },
        "stat": {
            "label": "STAT",
            "type": "text",
            "category": "Employeur",
            "description": "Numéro statistique"
        },
        "cnaps_num": {
            "label": "N° CNaPS",
            "type": "text",
            "category": "Employeur",
            "description": "Numéro CNaPS employeur"
        },
        "representant": {
            "label": "Représentant légal",
            "type": "text",
            "category": "Employeur",
            "description": "Nom du représentant légal"
        },
        "rep_fonction": {
            "label": "Fonction représentant",
            "type": "text",
            "category": "Employeur",
            "description": "Fonction du représentant légal"
        }
    },
    
    # Informations travailleur
    "worker": {
        "matricule": {
            "label": "Matricule",
            "type": "text",
            "category": "Travailleur",
            "description": "Numéro matricule du salarié"
        },
        "nom": {
            "label": "Nom",
            "type": "text",
            "category": "Travailleur",
            "description": "Nom de famille"
        },
        "prenom": {
            "label": "Prénom",
            "type": "text",
            "category": "Travailleur",
            "description": "Prénom(s)"
        },
        "nom_complet": {
            "label": "Nom complet",
            "type": "computed",
            "category": "Travailleur",
            "description": "Nom et prénom",
            "formula": "{prenom} {nom}"
        },
        "sexe": {
            "label": "Sexe",
            "type": "text",
            "category": "Travailleur",
            "description": "Masculin/Féminin"
        },
        "date_naissance": {
            "label": "Date de naissance",
            "type": "date",
            "category": "Travailleur",
            "description": "Date de naissance",
            "format": "dd/MM/yyyy"
        },
        "lieu_naissance": {
            "label": "Lieu de naissance",
            "type": "text",
            "category": "Travailleur",
            "description": "Lieu de naissance"
        },
        "adresse": {
            "label": "Adresse",
            "type": "text",
            "category": "Travailleur",
            "description": "Adresse personnelle"
        },
        "cin": {
            "label": "CIN",
            "type": "text",
            "category": "Travailleur",
            "description": "Carte d'Identité Nationale"
        },
        "cnaps": {
            "label": "N° CNaPS",
            "type": "text",
            "category": "Travailleur",
            "description": "Numéro CNaPS du salarié"
        },
        "date_embauche": {
            "label": "Date d'embauche",
            "type": "date",
            "category": "Travailleur",
            "description": "Date d'entrée dans l'entreprise",
            "format": "dd/MM/yyyy"
        },
        "poste": {
            "label": "Poste",
            "type": "text",
            "category": "Travailleur",
            "description": "Intitulé du poste"
        },
        "categorie_prof": {
            "label": "Catégorie professionnelle",
            "type": "text",
            "category": "Travailleur",
            "description": "Catégorie professionnelle"
        },
        "salaire_base": {
            "label": "Salaire de base",
            "type": "currency",
            "category": "Travailleur",
            "description": "Salaire de base mensuel",
            "format": "0,0 Ar"
        },
        "nature_contrat": {
            "label": "Nature du contrat",
            "type": "text",
            "category": "Travailleur",
            "description": "CDI/CDD"
        },
        # Champs organisationnels
        "etablissement": {
            "label": "Établissement",
            "type": "text",
            "category": "Structure Organisationnelle",
            "description": "Établissement d'affectation"
        },
        "departement": {
            "label": "Département",
            "type": "text",
            "category": "Structure Organisationnelle",
            "description": "Département d'affectation"
        },
        "service": {
            "label": "Service",
            "type": "text",
            "category": "Structure Organisationnelle",
            "description": "Service d'affectation"
        },
        "unite": {
            "label": "Unité",
            "type": "text",
            "category": "Structure Organisationnelle",
            "description": "Unité d'affectation"
        }
    },
    
    # Informations de paie
    "payroll": {
        "periode": {
            "label": "Période",
            "type": "text",
            "category": "Paie",
            "description": "Période de paie (MM/YYYY)"
        },
        "salaire_brut": {
            "label": "Salaire brut",
            "type": "currency",
            "category": "Paie",
            "description": "Salaire brut total",
            "format": "0,0 Ar"
        },
        "net_a_payer": {
            "label": "Net à payer",
            "type": "currency",
            "category": "Paie",
            "description": "Montant net à payer",
            "format": "0,0 Ar"
        },
        "cotisations_salariales": {
            "label": "Cotisations salariales",
            "type": "currency",
            "category": "Paie",
            "description": "Total cotisations salariales",
            "format": "0,0 Ar"
        }
    },
    
    # Dates système
    "system": {
        "date_aujourd_hui": {
            "label": "Date d'aujourd'hui",
            "type": "date",
            "category": "Système",
            "description": "Date actuelle",
            "format": "dd/MM/yyyy"
        },
        "annee_courante": {
            "label": "Année courante",
            "type": "text",
            "category": "Système",
            "description": "Année en cours"
        }
    }
}

# Templates de documents prédéfinis
DOCUMENT_TEMPLATES = {
    "certificat_travail": {
        "nom": "Certificat de travail",
        "description": "Certificat attestant de l'emploi d'un salarié",
        "champs_requis": [
            "employer.raison_sociale",
            "employer.representant", 
            "employer.rep_fonction",
            "worker.nom_complet",
            "worker.poste",
            "worker.date_embauche",
            "system.date_aujourd_hui"
        ],
        "template": """
CERTIFICAT DE TRAVAIL

Je soussigné(e) {employer.representant}, {employer.rep_fonction} de {employer.raison_sociale}, 
certifie que {worker.nom_complet} a été employé(e) dans notre entreprise en qualité de {worker.poste} 
du {worker.date_embauche} à ce jour.

Ce certificat lui est délivré pour servir et valoir ce que de droit.

Fait à {employer.ville}, le {system.date_aujourd_hui}

{employer.representant}
{employer.rep_fonction}
        """
    },
    
    "attestation_emploi": {
        "nom": "Attestation d'emploi",
        "description": "Attestation confirmant l'emploi actuel",
        "champs_requis": [
            "employer.raison_sociale",
            "employer.adresse",
            "employer.nif",
            "worker.nom_complet",
            "worker.matricule",
            "worker.poste",
            "worker.salaire_base",
            "worker.date_embauche"
        ],
        "template": """
ATTESTATION D'EMPLOI

L'entreprise {employer.raison_sociale}, située {employer.adresse}, 
NIF : {employer.nif}, atteste que :

{worker.nom_complet}, matricule {worker.matricule}, 
est employé(e) dans notre entreprise en qualité de {worker.poste} 
depuis le {worker.date_embauche}.

Son salaire mensuel de base est de {worker.salaire_base}.

Cette attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit.

Fait le {system.date_aujourd_hui}
        """
    },
    
    "contrat_travail": {
        "nom": "Contrat de travail",
        "description": "Contrat de travail standard",
        "champs_requis": [
            "employer.raison_sociale",
            "employer.adresse", 
            "employer.representant",
            "worker.nom_complet",
            "worker.adresse",
            "worker.poste",
            "worker.salaire_base",
            "worker.date_embauche",
            "worker.nature_contrat"
        ],
        "template": """
CONTRAT DE TRAVAIL

Entre les soussignés :

{employer.raison_sociale}, représentée par {employer.representant}, 
dont le siège social est situé {employer.adresse}, ci-après dénommée "l'Employeur"

ET

{worker.nom_complet}, demeurant {worker.adresse}, ci-après dénommé(e) "le Salarié"

Il a été convenu ce qui suit :

Article 1 - ENGAGEMENT
Le Salarié est engagé en qualité de {worker.poste} à compter du {worker.date_embauche} 
sous contrat {worker.nature_contrat}.

Article 2 - REMUNERATION  
Le salaire mensuel de base est fixé à {worker.salaire_base}.

Fait en double exemplaire le {system.date_aujourd_hui}

L'Employeur                    Le Salarié
        """
    }
}

# Mappings pour l'interface glisser-déposer
FIELD_MAPPINGS = {
    "categories": {
        "Employeur": "employer",
        "Travailleur": "worker", 
        "Paie": "payroll",
        "Système": "system"
    },
    "types": {
        "text": "Texte",
        "date": "Date",
        "currency": "Montant",
        "computed": "Calculé"
    }
}

# Configuration de l'éditeur de documents
DOCUMENT_EDITOR_CONFIG = {
    "toolbar": {
        "formatting": ["bold", "italic", "underline"],
        "alignment": ["left", "center", "right", "justify"],
        "lists": ["bullet", "number"],
        "insert": ["field", "table", "image"]
    },
    "field_placeholder": "{{field_name}}",
    "preview_mode": True,
    "auto_save": True
}