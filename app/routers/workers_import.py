from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from datetime import datetime
from ..config.config import get_db
from .. import models, schemas
from ..security import WRITE_RH_ROLES, can_manage_worker, require_roles
from ..services.audit_service import record_audit

router = APIRouter(prefix="/workers/import", tags=["workers-import"])

@router.get("/template")
def get_workers_import_template(
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    GÃ©nÃ¨re un modÃ¨le Excel pour l'import des salariÃ©s.
    """
    # Create DataFrame with headers - Raison Sociale en premiÃ¨re colonne
    headers = [
        "Raison Sociale", "Matricule", "Nom", "Prenom", "Sexe (M/F)", "Situation Familiale", 
        "Date de Naissance (JJ/MM/AAAA)", "Lieu de Naissance", "Date Embauche (JJ/MM/AAAA)", 
        "Nature du Contrat", "Duree Essai (jours)", "Date Fin Essai (JJ/MM/AAAA)", "Salaire Base", 
        "Horaire Hebdo", "Type Regime (Agricole/Non Agricole)", "Groupe de Preavis (1-5)", 
        "Etablissement", "Departement", "Service", "Unite",  # Nouveaux champs organisationnels
        "Adresse", "Telephone", "Email", "CIN", "CIN Delivre le (JJ/MM/AAAA)", 
        "CIN Lieu de delivrance", "Numero CNaPS", "Nombre Enfants", "Poste Actuel", 
        "Categorie Professionnelle", "Mode de Paiement", "Nom de la Banque", "BIC / SWIFT", 
        "Code Banque", "Code Guichet", "Numero de Compte", "Cle RIB", "Solde Conge Initial"
    ]
    
    df = pd.DataFrame(columns=headers)
    
    # Add an example row
    example = {
        "Raison Sociale": "Karibo Services",
        "Matricule": "M001",
        "Nom": "RAKOTO",
        "Prenom": "Jean",
        "Sexe (M/F)": "M",
        "Situation Familiale": "MariÃ©(e)",
        "Date de Naissance (JJ/MM/AAAA)": "15/05/1985",
        "Lieu de Naissance": "Antananarivo",
        "Date Embauche (JJ/MM/AAAA)": "01/01/2024",
        "Nature du Contrat": "CDI",
        "Duree Essai (jours)": 90,
        "Date Fin Essai (JJ/MM/AAAA)": "31/03/2024",
        "Salaire Base": 250000,
        "Horaire Hebdo": 40,
        "Type Regime (Agricole/Non Agricole)": "Non Agricole",
        "Groupe de Preavis (1-5)": 2,
        "Etablissement": "SiÃ¨ge Social",  # Exemple de structure organisationnelle
        "Departement": "Ressources Humaines",
        "Service": "Administration",
        "Unite": "Paie",
        "Adresse": "Lot IVC Tana",
        "Telephone": "0340000000",
        "Email": "jean.rakoto@example.com",
        "CIN": "101234567890",
        "CIN Delivre le (JJ/MM/AAAA)": "01/01/2020",
        "CIN Lieu de delivrance": "Antananarivo",
        "Numero CNaPS": "9876543210X",
        "Nombre Enfants": 2,
        "Poste Actuel": "Ouvrier",
        "Categorie Professionnelle": "M1",
        "Mode de Paiement": "Virement",
        "Nom de la Banque": "BNI",
        "BIC / SWIFT": "BNIMMG",
        "Code Banque": "'00005",  # Apostrophe pour forcer le texte
        "Code Guichet": "'00081",  # Apostrophe pour forcer le texte
        "Numero de Compte": "'12345678901",  # Apostrophe pour forcer le texte
        "Cle RIB": "63",
        "Solde Conge Initial": 0
    }
    df = pd.concat([df, pd.DataFrame([example])], ignore_index=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='SalariÃ©s')
        
        # Adjust column widths and format bank codes as text
        worksheet = writer.sheets['SalariÃ©s']
        workbook = writer.book
        
        # Format pour forcer le texte sur les colonnes bancaires
        text_format = workbook.add_format({'num_format': '@'})
        
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
            
            # Forcer le format texte pour les codes bancaires
            if col in ["Code Banque", "Code Guichet", "Numero de Compte"]:
                worksheet.set_column(i, i, column_len, text_format)

        # Ajouter des listes dÃ©roulantes pour faciliter la saisie
        # Trouver les indices des colonnes
        col_indices = {col: i for i, col in enumerate(df.columns)}
        
        # DÃ©finir les options pour chaque liste dÃ©roulante
        dropdown_options = {
            "Sexe (M/F)": ["M", "F"],
            "Situation Familiale": ["CÃ©libataire", "MariÃ©(e)", "DivorcÃ©(e)", "Veuf(ve)"],
            "Nature du Contrat": ["CDI", "CDD"],
            "Type Regime (Agricole/Non Agricole)": ["Agricole", "Non Agricole"],
            "Mode de Paiement": ["Virement", "EspÃ¨ces", "ChÃ¨que"],
            "Groupe de Preavis (1-5)": [1, 2, 3, 4, 5]
        }
        
        # Appliquer les validations de donnÃ©es (listes dÃ©roulantes)
        for col_name, options in dropdown_options.items():
            if col_name in col_indices:
                col_idx = col_indices[col_name]
                # Convertir les options en chaÃ®ne pour xlsxwriter
                if col_name == "Groupe de Preavis (1-5)":
                    options_str = [str(x) for x in options]
                else:
                    options_str = options
                
                # Appliquer la validation sur les lignes 2 Ã  1000 (ligne 1 = en-tÃªtes)
                worksheet.data_validation(1, col_idx, 1000, col_idx, {
                    'validate': 'list',
                    'source': options_str,
                    'dropdown': True,
                    'error_title': 'Valeur invalide',
                    'error_message': f'Veuillez choisir une valeur dans la liste: {", ".join(options_str)}'
                })
        
        # Ajouter des commentaires explicatifs sur les colonnes avec listes dÃ©roulantes
        comment_format = workbook.add_format({'font_color': 'blue', 'italic': True})
        
        comments = {
            "Sexe (M/F)": "Cliquez sur la flÃ¨che pour choisir: M (Masculin) ou F (FÃ©minin)",
            "Situation Familiale": "Cliquez sur la flÃ¨che pour choisir parmi les options disponibles",
            "Nature du Contrat": "Cliquez sur la flÃ¨che pour choisir: CDI ou CDD",
            "Type Regime (Agricole/Non Agricole)": "Cliquez sur la flÃ¨che pour choisir le type de rÃ©gime",
            "Mode de Paiement": "Cliquez sur la flÃ¨che pour choisir le mode de paiement",
            "Groupe de Preavis (1-5)": "Cliquez sur la flÃ¨che pour choisir le groupe (1=minimum, 5=maximum)"
        }
        
        for col_name, comment_text in comments.items():
            if col_name in col_indices:
                col_idx = col_indices[col_name]
                # Ajouter un commentaire Ã  la cellule d'en-tÃªte
                worksheet.write_comment(0, col_idx, comment_text, {'width': 300, 'height': 60})

    output.seek(0)
    
    filename = "model_import_salaries.xlsx"
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

@router.post("")
def import_workers(
    file: UploadFile = File(...), 
    update_existing: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.AppUser = Depends(require_roles(*WRITE_RH_ROLES)),
):
    """
    Importe une liste de salariÃ©s depuis un fichier Excel.
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(400, "Le fichier doit Ãªtre au format Excel (.xlsx)")
        
    try:
        content = file.file.read()
        df = pd.read_excel(io.BytesIO(content))
        
        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First few rows:\n{df.head()}")
        
        # Basic validation of required columns
        required_cols = ["Matricule", "Nom"]
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(400, f"Colonne manquante: {col}")
                
        imported_count = 0
        skipped_count = 0
        updated_count = 0
        errors = []
        
        # Pre-fetch regimes to map "Type RÃ©gime" text to ID
        regimes = db.query(models.TypeRegime).all()
        print(f"Available regimes: {[(r.id, r.code, r.label) for r in regimes]}")
        
        # Default fallback
        default_regime = next((r for r in regimes if r.code == "non_agricole"), regimes[0]) if regimes else None
        if not default_regime:
            raise HTTPException(400, "Aucun rÃ©gime configurÃ© dans le systÃ¨me.")
        
        # Get all employers to map Name -> ID
        all_employers = db.query(models.Employer).all()
        print(f"Available employers: {[(e.id, e.raison_sociale) for e in all_employers]}")
        
        if not all_employers:
             raise HTTPException(400, "Aucun employeur configurÃ© dans le systÃ¨me.")
             
        # Normalize employer names for easier matching
        employer_map = {e.raison_sociale.lower().strip(): e for e in all_employers}
        default_employer = all_employers[0] # Fallback if not specified
        
        for index, row in df.iterrows():
            try:
                print(f"\n=== Processing row {index+1} ===")
                print(f"Row data: {dict(row)}")
                
                # Skip example row if it looks exactly like the example
                matricule_raw = row.get("Matricule")
                nom_raw = row.get("Nom")
                
                if (str(matricule_raw).strip() == "M001" and 
                    str(nom_raw).strip().upper() == "RAKOTO"):
                    print(f"Skipping example row at index {index}")
                    continue

                matricule = str(matricule_raw).strip()
                if not matricule or matricule.lower() == "nan" or pd.isna(matricule_raw):
                    print(f"Skipping empty matricule at row {index+1}")
                    continue
                
                print(f"Processing matricule: '{matricule}'")
                    
                # Check existence
                existing = db.query(models.Worker).filter(models.Worker.matricule == matricule).first()
                if existing:
                    if not can_manage_worker(db, user, worker=existing):
                        errors.append(f"Ligne {index+2}: droits insuffisants pour modifier {matricule}.")
                        continue
                    if not update_existing:
                        skipped_count += 1
                        errors.append(f"Ligne {index+2}: Matricule {matricule} existe dÃ©jÃ . (IgnorÃ©)")
                        print(f"Skipping existing worker: {matricule}")
                        continue
                    else:
                        print(f"Will update existing worker: {matricule}")
                
                # Parse dates
                date_embauche = None
                raw_date_embauche = row.get("Date Embauche (JJ/MM/AAAA)")
                if pd.notna(raw_date_embauche):
                    if isinstance(raw_date_embauche, datetime):
                        date_embauche = raw_date_embauche.date()
                    else:
                        try:
                            date_embauche = datetime.strptime(str(raw_date_embauche), "%d/%m/%Y").date()
                        except:
                            try:
                                # Try other formats
                                date_embauche = pd.to_datetime(raw_date_embauche).date()
                            except:
                                errors.append(f"Ligne {index+2}: Format date embauche invalide pour {matricule}")
                                continue

                date_naissance = None
                raw_date_naissance = row.get("Date de Naissance (JJ/MM/AAAA)")
                if pd.notna(raw_date_naissance):
                    if isinstance(raw_date_naissance, datetime):
                        date_naissance = raw_date_naissance.date()
                    else:
                        try:
                            date_naissance = datetime.strptime(str(raw_date_naissance), "%d/%m/%Y").date()
                        except:
                            try:
                                date_naissance = pd.to_datetime(raw_date_naissance).date()
                            except:
                                print(f"Warning: Invalid birth date format for {matricule}")

                # Parse date fin essai
                date_fin_essai = None
                raw_date_fin_essai = row.get("Date Fin Essai (JJ/MM/AAAA)")
                if pd.notna(raw_date_fin_essai):
                    if isinstance(raw_date_fin_essai, datetime):
                        date_fin_essai = raw_date_fin_essai.date()
                    else:
                        try:
                            date_fin_essai = datetime.strptime(str(raw_date_fin_essai), "%d/%m/%Y").date()
                        except:
                            try:
                                date_fin_essai = pd.to_datetime(raw_date_fin_essai).date()
                            except:
                                print(f"Warning: Invalid date fin essai format for {matricule}")

                # Parse date CIN delivrÃ© le
                cin_delivre_le = None
                raw_cin_delivre_le = row.get("CIN Delivre le (JJ/MM/AAAA)")
                if pd.notna(raw_cin_delivre_le):
                    if isinstance(raw_cin_delivre_le, datetime):
                        cin_delivre_le = raw_cin_delivre_le.date()
                    else:
                        try:
                            cin_delivre_le = datetime.strptime(str(raw_cin_delivre_le), "%d/%m/%Y").date()
                        except:
                            try:
                                cin_delivre_le = pd.to_datetime(raw_cin_delivre_le).date()
                            except:
                                print(f"Warning: Invalid CIN delivery date format for {matricule}")
                
                # Basic info
                nom = str(row.get("Nom", "")).strip().upper()
                prenom = str(row.get("Prenom", "")).strip()
                
                if not nom:
                    errors.append(f"Ligne {index+2}: Nom manquant pour matricule {matricule}")
                    continue
                
                # Regime Logic
                regime_text = str(row.get("Type Regime (Agricole/Non Agricole)", "")).lower()
                regime_id = default_regime.id
                vhm = default_regime.vhm
                
                if "agricole" in regime_text and "non" not in regime_text:
                     agri = next((r for r in regimes if r.code == "agricole"), None)
                     if agri:
                         regime_id = agri.id
                         vhm = agri.vhm
                
                # Employer Logic
                employer_name = str(row.get("Raison Sociale", "")).strip()
                target_employer = default_employer
                
                if employer_name and employer_name.lower() != "nan" and pd.notna(row.get("Raison Sociale")):
                    found = employer_map.get(employer_name.lower())
                    if found:
                        target_employer = found
                        print(f"Found employer: {target_employer.raison_sociale}")
                    else:
                        print(f"Employer '{employer_name}' not found, using default: {default_employer.raison_sociale}")
                        errors.append(f"Ligne {index+2}: Employeur '{employer_name}' inconnu, utilisation de l'employeur par dÃ©faut.")
                
                if not can_manage_worker(db, user, employer_id=target_employer.id):
                    errors.append(
                        f"Ligne {index+2}: droits insuffisants pour l'employeur {target_employer.raison_sociale}."
                    )
                    continue

                # Numeric fields with safe conversion
                def safe_float(val, default=0.0):
                    if pd.isna(val) or val == "":
                        return default
                    try:
                        return float(val)
                    except:
                        return default
                
                def safe_int(val, default=0):
                    if pd.isna(val) or val == "":
                        return default
                    try:
                        return int(float(val))
                    except:
                        return default
                
                salaire_base = safe_float(row.get("Salaire Base", 0))
                horaire_hebdo = safe_float(row.get("Horaire Hebdo", 40))
                nombre_enfant = safe_int(row.get("Nombre Enfants", 0))
                solde_conge_initial = safe_float(row.get("Solde Conge Initial", 0))
                duree_essai_jours = safe_int(row.get("Duree Essai (jours)", 0))
                groupe_preavis = safe_int(row.get("Groupe de Preavis (1-5)", 1))
                
                # Validation du groupe de prÃ©avis (doit Ãªtre entre 1 et 5)
                if groupe_preavis < 1 or groupe_preavis > 5:
                    groupe_preavis = 1  # Valeur par dÃ©faut
                
                # String fields with safe conversion
                def safe_str(val, default=""):
                    if pd.isna(val):
                        return default
                    return str(val).strip()
                
                sexe = safe_str(row.get("Sexe (M/F)", "")).upper()
                situation_familiale = safe_str(row.get("Situation Familiale", ""))
                lieu_naissance = safe_str(row.get("Lieu de Naissance", ""))
                adresse = safe_str(row.get("Adresse", ""))
                telephone = safe_str(row.get("Telephone", ""))
                email = safe_str(row.get("Email", "")).lower()
                cin = safe_str(row.get("CIN", ""))
                cin_lieu = safe_str(row.get("CIN Lieu de delivrance", ""))
                cnaps_num = safe_str(row.get("Numero CNaPS", ""))
                categorie_prof = safe_str(row.get("Categorie Professionnelle", ""))
                poste = safe_str(row.get("Poste Actuel", ""))
                nature_contrat = safe_str(row.get("Nature du Contrat", "CDI"))
                mode_paiement = safe_str(row.get("Mode de Paiement", "Virement"))
                
                # Champs organisationnels
                etablissement = safe_str(row.get("Etablissement", ""))
                departement = safe_str(row.get("Departement", ""))
                service = safe_str(row.get("Service", ""))
                unite = safe_str(row.get("Unite", ""))
                
                # Bank details
                banque = safe_str(row.get("Nom de la Banque", ""))
                bic = safe_str(row.get("BIC / SWIFT", ""))
                code_banque = safe_str(row.get("Code Banque", ""))
                code_guichet = safe_str(row.get("Code Guichet", ""))
                compte_num = safe_str(row.get("Numero de Compte", ""))
                cle_rib = safe_str(row.get("Cle RIB", ""))
                
                print(f"About to create/update worker: {matricule}")
                
                # Create or Update Worker
                if existing:
                    print(f"Updating existing worker: {matricule}")
                    # Update fields
                    existing.nom = nom
                    existing.prenom = prenom
                    if date_embauche:
                        existing.date_embauche = date_embauche
                    existing.salaire_base = salaire_base
                    existing.horaire_hebdo = horaire_hebdo
                    existing.type_regime_id = regime_id
                    existing.vhm = vhm
                    existing.adresse = adresse
                    existing.nombre_enfant = nombre_enfant
                    existing.employer_id = target_employer.id
                    existing.categorie_prof = categorie_prof
                    existing.poste = poste
                    existing.solde_conge_initial = solde_conge_initial
                    existing.nature_contrat = nature_contrat
                    existing.duree_essai_jours = duree_essai_jours
                    existing.mode_paiement = mode_paiement
                    existing.groupe_preavis = groupe_preavis
                    
                    # Dates
                    if date_fin_essai:
                        existing.date_fin_essai = date_fin_essai
                    if cin_delivre_le:
                        existing.cin_delivre_le = cin_delivre_le
                    
                    # Identity
                    if sexe:
                        existing.sexe = sexe
                    if situation_familiale:
                        existing.situation_familiale = situation_familiale
                    if date_naissance:
                        existing.date_naissance = date_naissance
                    if lieu_naissance:
                        existing.lieu_naissance = lieu_naissance
                    if cin:
                        existing.cin = cin
                    if cin_lieu:
                        existing.cin_lieu = cin_lieu
                    if cnaps_num:
                        existing.cnaps_num = cnaps_num
                    
                    # Contact
                    if telephone:
                        existing.telephone = telephone
                    if email:
                        existing.email = email
                    
                    # Bank
                    if banque:
                        existing.banque = banque
                    if bic:
                        existing.bic = bic
                    if code_banque:
                        existing.code_banque = code_banque
                    if code_guichet:
                        existing.code_guichet = code_guichet
                    if compte_num:
                        existing.compte_num = compte_num
                    if cle_rib:
                        existing.cle_rib = cle_rib
                    
                    # Champs organisationnels
                    if etablissement:
                        existing.etablissement = etablissement
                    if departement:
                        existing.departement = departement
                    if service:
                        existing.service = service
                    if unite:
                        existing.unite = unite
                    
                    worker = existing
                    updated_count += 1
                else:
                    print(f"Creating new worker: {matricule}")
                    worker = models.Worker(
                        employer_id=target_employer.id,
                        matricule=matricule,
                        nom=nom,
                        prenom=prenom,
                        date_embauche=date_embauche,
                        salaire_base=salaire_base,
                        horaire_hebdo=horaire_hebdo,
                        type_regime_id=regime_id,
                        vhm=vhm,
                        adresse=adresse,
                        nombre_enfant=nombre_enfant,
                        salaire_horaire=0,  # Will be calculated
                        nature_contrat=nature_contrat,
                        duree_essai_jours=duree_essai_jours,
                        date_fin_essai=date_fin_essai,
                        mode_paiement=mode_paiement,
                        groupe_preavis=groupe_preavis,
                        categorie_prof=categorie_prof,
                        poste=poste,
                        solde_conge_initial=solde_conge_initial,
                        # Identity
                        sexe=sexe,
                        situation_familiale=situation_familiale,
                        date_naissance=date_naissance,
                        lieu_naissance=lieu_naissance,
                        cin=cin,
                        cin_delivre_le=cin_delivre_le,
                        cin_lieu=cin_lieu,
                        cnaps_num=cnaps_num,
                        # Contact
                        telephone=telephone,
                        email=email,
                        # Bank
                        banque=banque,
                        bic=bic,
                        code_banque=code_banque,
                        code_guichet=code_guichet,
                        compte_num=compte_num,
                        cle_rib=cle_rib,
                        # Champs organisationnels
                        etablissement=etablissement,
                        departement=departement,
                        service=service,
                        unite=unite
                    )
                    db.add(worker)
                    imported_count += 1
                    print(f"Added new worker to session: {matricule}")

                # Calculate hourly rate
                if worker.vhm and worker.vhm > 0:
                    worker.salaire_horaire = worker.salaire_base / worker.vhm
                    
                db.flush()  # To get ID
                print(f"Worker ID after flush: {worker.id}")
                
                # Add Initial Position History (only for new workers or if position changed)
                if poste and not existing:  # Only for new workers
                    try:
                        history = models.WorkerPositionHistory(
                            worker_id=worker.id,
                            poste=poste,
                            categorie_prof=categorie_prof,
                            start_date=date_embauche or datetime.now().date()
                        )
                        db.add(history)
                        print(f"Added position history for worker: {matricule}")
                    except Exception as e:
                        print(f"Warning: Could not add position history for {matricule}: {e}")
                
            except Exception as e:
                print(f"Error processing row {index+1}: {str(e)}")
                errors.append(f"Ligne {index+2}: Erreur inattendue - {str(e)}")
                
        print(f"Final counts - Imported: {imported_count}, Updated: {updated_count}, Skipped: {skipped_count}")
        
        if imported_count > 0 or updated_count > 0:
            record_audit(
                db,
                actor=user,
                action="workers.import",
                entity_type="worker_import",
                entity_id=f"{imported_count}:{updated_count}:{skipped_count}",
                route="/workers/import",
                after={
                    "imported": imported_count,
                    "updated": updated_count,
                    "skipped": skipped_count,
                    "errors_count": len(errors),
                },
            )
            db.commit()
            print("Changes committed to database")
        else:
            print("No changes to commit")
            
        return {
            "imported": imported_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": errors
        }

    except Exception as e:
        print(f"General error: {str(e)}")
        raise HTTPException(500, f"Erreur lors du traitement du fichier: {str(e)}")

