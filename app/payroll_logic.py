# backend/app/payroll_logic.py
from typing import Dict, List, Any, Optional
from datetime import date, datetime

ABS_DIVISOR = 21.67  # Salaire journalier = base / 21.67 (tu peux mettre 30 si tu préfères)


def _money(x: float) -> float:
    return round(float(x or 0.0), 2)


def _row(label, nombre="", base="", taux_sal="", montant_sal=0.0, taux_pat="", montant_pat=0.0):
    return {
        "label": label,
        "nombre": nombre,
        "base": base,
        "taux_sal": taux_sal,
        "montant_sal": _money(montant_sal),
        "taux_pat": taux_pat,
        "montant_pat": _money(montant_pat),
    }


def _apply_plafond(base: float, plafond: float) -> float:
    if not plafond or plafond <= 0:
        return _money(base)
    return _money(min(base, plafond))


def compute_cnaps(brut_base: float, taux_sal: float, taux_pat: float, plafond: float):
    base_cot = _apply_plafond(brut_base, plafond)
    sal = _money(base_cot * (taux_sal / 100.0))
    pat = _money(base_cot * (taux_pat / 100.0))
    return base_cot, sal, pat


def compute_fmfp(brut_base: float, taux_pat: float, plafond: float):
    base_cot = _apply_plafond(brut_base, plafond)
    return _money(base_cot * (taux_pat / 100.0))


def compute_smie(brut_base: float, taux_sal: float, taux_pat: float, forfait_sal: float, forfait_pat: float, plafond: float = 0.0):
    base_cot = _apply_plafond(brut_base, plafond)
    sal = _money(base_cot * (taux_sal / 100.0)) + _money(forfait_sal)
    pat = _money(base_cot * (taux_pat / 100.0)) + _money(forfait_pat)
    return base_cot, sal, pat


from .constants.payroll_constants import CALCULATION_CONSTANTS
from .services.payroll_regulation_service import resolve_regulatory_snapshot

def calculate_constants(
    worker,
    payvar,
    brut_numeraire_courant: float,
    salaire_base: float,
    salaire_horaire: float,
    salaire_journalier: float,
    period: Optional[str] = None,
) -> Dict[str, float]:
    """
    Génère le dictionnaire des constantes utilisables dans les formules.
    Utilise maintenant le référentiel centralisé de constantes.
    """
    constants = {}

    # --- ANCIENNETÉ ---
    # Conversion date embauche -> maintenant
    today = date.today()
    d_emb = worker.date_embauche
    ancien_an = 0.0
    ancien_ms = 0.0
    ancien_jr = 0.0
    
    if d_emb:
        # ANCIENAN : écart en années
        ancien_an = float(today.year - d_emb.year)
        
        # ANCIENMS : écart en mois (mois en cours INCLUS)
        # Ex: Emb 01/01/2023, Paie 01/2023 => 1 mois
        ancien_ms = ((today.year - d_emb.year) * 12 + (today.month - d_emb.month)) + 1
        
        # ANCIENJR : écart en jours
        delta = today - d_emb
        ancien_jr = float(delta.days)

    constants["ANCIENAN"] = ancien_an
    constants["ANCIENMS"] = float(ancien_ms)
    constants["ANCIENJR"] = ancien_jr

    # --- ENFANTS ---
    constants["NOMBRENF"] = float(getattr(worker, "nombre_enfant", 0) or 0.0)

    # --- SME (Salaire Minimum d'Embauche Employeur) ---
    # On accède à l'employeur via la relation ORM
    sme = 0.0
    if worker.employer:
        sme = worker.employer.sm_embauche or 0.0
    constants["SME"] = float(sme)

    # --- SALAIRES ---
    constants["SALDBASE"] = salaire_base
    constants["SALHORAI"] = salaire_horaire
    constants["SALJOURN"] = salaire_journalier
    
    # --- SOMMBRUT ---
    constants["SOMMBRUT"] = brut_numeraire_courant

    # --- DAYSWORK (Jours travaillés du mois) ---
    # Utilise la constante centralisée pour le diviseur
    
    days_work = 0.0
    target_period = period or getattr(payvar, "period", None)
    if target_period:
        try:
            year_str, month_str = target_period.split('-')
            year = int(year_str)
            month = int(month_str)
            
            import calendar
            _, last_day = calendar.monthrange(year, month)
            
            # Charger les overrides en mémoire pour éviter N requêtes
            # worker.employer.calendar_days est une liste d'objets CalendarDay
            # On crée un dict: date -> is_worked
            # date -> worked/off/closed (fallback legacy: is_worked)
            calendar_map = {}
            if worker.employer:
                 for cd in worker.employer.calendar_days:
                     if cd.date.year == year and cd.date.month == month:
                         if hasattr(cd, "status") and cd.status:
                             calendar_map[cd.date] = cd.status
                         else:
                             calendar_map[cd.date] = "worked" if cd.is_worked else "off"

            for day in range(1, last_day + 1):
                current_date = date(year, month, day)
                
                # Check Override
                status = calendar_map.get(current_date)
                
                if status is None:
                    # default: weekday=worked, saturday/sunday=off
                    # Défaut : Lundi(0)..Vendredi(4) = True
                    # Samedi(5)..Dimanche(6) = False
                    status = "worked" if (current_date.weekday() < 5) else "off"
                
                if status == "worked":
                    days_work += 1.0

        except Exception as e:
            # Fallback en cas d'erreur de parsing ou autre
            print(f"Error calculating DAYSWORK: {e}")
            # Utilise la constante centralisée pour les jours travaillés par défaut
            days_work = float(CALCULATION_CONSTANTS["working_days_per_month"])
            
    constants["DAYSWORK"] = days_work

    return constants


def _safe_eval(expr: str, constants: Dict[str, float]) -> float:
    """
    Évalue une expression mathématique simple avec les constantes fournies.
    Supporte +, -, *, /, (, ).
    """
    if not expr or not expr.strip():
        return 0.0
        
    code = expr.strip().upper()
    
    # Trier les clés par longueur décroissante pour éviter les collisions de remplacement
    sorted_keys = sorted(constants.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        if key in code:
            code = code.replace(key, str(constants[key]))
            
    # Nettoyage final pour eval
    allowed_chars = "0123456789.+-*/() "
    if not all(c in allowed_chars for c in code):
        try:
            return float(code)
        except:
            return 0.0

    try:
        return float(eval(code, {"__builtins__": None}, {}))
    except:
        return 0.0


def evaluate_formula(formula: str, constants: Dict[str, float]) -> float:
    return _safe_eval(formula, constants)


def compute_preview(employer, worker, payvar, period: str, custom_primes_override=None, **kwargs):
    """
    Calcule les lignes + totaux d'un bulletin de PREVIEW.
    """

    computed_constants = {}
    working_primes = []
    lines: List[Dict[str, Any]] = []

    # Données de base
    salaire_base = _money(worker.salaire_base)
    taux_h = worker.salaire_horaire or (worker.vhm and (worker.salaire_base / worker.vhm)) or 0.0
    taux_h = _money(taux_h)

    # 1) Salaire de base (EN PREMIER)
    lines.append(_row("Salaire de base", 1, salaire_base, "", salaire_base, "", 0))

    # 0) HS / HM (Nouvelle méthode via Import/Link)
    hs_hm_dict = kwargs.get("hs_hm_dict", None)
    if hs_hm_dict:
        # Mapping des clés vers libellés et taux
        # Structure de hs_hm_dict attendue : { 'hsni_130_heures': ..., 'hsni_130_montant': ..., ... }
        
        # Liste de config pour l'affichage
        # (clé_heures, clé_montant, libellé, Taux texte)
        hs_config = [
            ("hsni_130", "HS Non Imposable 130%", "130%"),
            ("hsi_130",  "HS Imposable 130%",     "130%"),
            ("hsni_150", "HS Non Imposable 150%", "150%"),
            ("hsi_150",  "HS Imposable 150%",     "150%"),
            ("hmnh",     "Heures Majorées Nuit Hab. 30%", "30%"),
            ("hmno",     "Heures Majorées Nuit Occ. 50%", "50%"),
            ("hmd",      "Heures Majorées Dimanche 40%",  "40%"),
            ("hmjf",     "Heures Majorées Jours Fériés 50%", "50%"), # Ou 100% selon logique, ici on affiche ce qui est stocké
        ]

        for code, label, taux_txt in hs_config:
            h_key = f"{code}_heures"
            m_key = f"{code}_montant"
            
            val_h = hs_hm_dict.get(h_key, 0.0)
            val_m = hs_hm_dict.get(m_key, 0.0)
            
            if val_h and float(val_h) > 0:
                lines.append({
                    "label": label,
                    "nombre": float(val_h),
                    "base": taux_h,      # On affiche le taux horaire de base
                    "taux_sal": taux_txt,
                    "montant_sal": _money(val_m),
                    "taux_pat": "",
                    "montant_pat": 0.0
                })

    # -------- ABSENCES --------
    per_day = _money(salaire_base / ABS_DIVISOR)

    def add_abs(label: str, valeur, use_hourly=False, informative_only: bool = False):
        valeur = float(valeur or 0)
        if valeur:
            if use_hourly:
                base_value = taux_h
                m = 0.0 if informative_only else -_money(valeur * taux_h)
                lines.append(_row(label, valeur, base_value, "", m, "", 0))
            else:
                base_value = per_day
                m = 0.0 if informative_only else -_money(valeur * per_day)
                lines.append(_row(label, valeur, base_value, "", m, "", 0))

    # Priorité: données importées > payvar
    absence_dict = kwargs.get("absence_dict", None)
    
    if absence_dict:
        # Utiliser données importées depuis Excel
        add_abs("Absence maladie (jours)", absence_dict.get("ABSM_J", 0), informative_only=True)
        add_abs("Absence maladie (heures)", absence_dict.get("ABSM_H", 0), use_hourly=True, informative_only=True)
        add_abs("Absence non rémunérée (jours)", absence_dict.get("ABSNR_J", 0))
        add_abs("Absence non rémunérée (heures)", absence_dict.get("ABSNR_H", 0), use_hourly=True)
        add_abs("Mise à pied", absence_dict.get("ABSMP", 0))
        add_abs("Autre absence 1 (jours)", absence_dict.get("ABS1_J", 0))
        add_abs("Autre absence 1 (heures)", absence_dict.get("ABS1_H", 0), use_hourly=True)
        add_abs("Autre absence 2 (jours)", absence_dict.get("ABS2_J", 0))
        add_abs("Autre absence 2 (heures)", absence_dict.get("ABS2_H", 0), use_hourly=True)

    # 2) Variables (si aucune saisie, on calcule quand même le brut)
    pv = payvar
    if pv:
        if not absence_dict:
            # Fallback: utiliser payvar (saisie manuelle) si pas d'import
            abs_non_remu_j = getattr(pv, "abs_non_remu_j", None)
            abs_maladie_j = getattr(pv, "abs_maladie_j", 0)
            mise_a_pied_j = getattr(pv, "mise_a_pied_j", 0)
            abs_non_remu_h = getattr(pv, "abs_non_remu_h", 0)

            if abs_non_remu_j is None:
                abs_non_remu_j = getattr(pv, "absences_non_remu", 0) or 0

            add_abs("Absence maladie", abs_maladie_j, informative_only=True)
            add_abs("Absence non rémunérée (jours)", abs_non_remu_j)
            add_abs("Mise à pied", mise_a_pied_j)
            add_abs("Absence non rémunérée (heures)", abs_non_remu_h, use_hourly=True)

        # -------- HEURES SUP --------
        def add_hs(label: str, heures, coef: float):
            heures = float(heures or 0)
            if heures:
                m = _money(heures * taux_h * coef)
                lines.append(_row(label, heures, taux_h, f"{int(coef * 100)}%", m, "", 0))

        hsni_130_h = getattr(pv, "hsni_130_h", getattr(pv, "hsni_130", 0))
        hsi_130_h = getattr(pv, "hsi_130_h", getattr(pv, "hsi_130", 0))
        hsni_150_h = getattr(pv, "hsni_150_h", getattr(pv, "hsni_150", 0))
        hsi_150_h = getattr(pv, "hsi_150_h", getattr(pv, "hsi_150", 0))

        add_hs("HS Non Imposable à 130%", hsni_130_h, 1.3)
        add_hs("HS Imposable à 130%", hsi_130_h, 1.3)
        add_hs("HS Non Imposable à 150%", hsni_150_h, 1.5)
        add_hs("HS Imposable à 150%", hsi_150_h, 1.5)

        # -------- MAJORATIONS --------
        def add_maj(label: str, heures, coef: float):
            heures = float(heures or 0)
            if heures:
                m = _money(heures * taux_h * coef)
                lines.append(_row(label, heures, taux_h, f"{int(coef * 100)}%", m, "", 0))

        dimanche_h = getattr(pv, "dimanche_h", 0)
        nuit_hab_h = getattr(pv, "nuit_hab_h", 0)
        nuit_occ_h = getattr(pv, "nuit_occ_h", 0)
        ferie_jour_h = getattr(pv, "ferie_jour_h", 0)

        add_maj("Travail de dimanche 40%", dimanche_h, 0.4)
        add_maj("Travail de nuit habituelle 30%", nuit_hab_h, 0.3)
        add_maj("Travail de nuit occasionnelle 50%", nuit_occ_h, 0.5)
        add_maj("Travail le jour férié 200%", ferie_jour_h, 2.0)

    # -------- PRIMES DYNAMIQUES (Formules + Overrides Importés) --------
    # Source 1 : Formules (définies via Gestion des Primes Globales)
    # Source 2 : Overrides (Imports Excel)
    # Priorité : Override (Import) > Formule (Globale)

    # Calcul préliminaire du brut pour les constantes
    brut_courant = salaire_base + 0.0
    for l in lines:
         if "cotisation" not in l["label"].lower() and "avance" not in l["label"].lower():
             brut_courant += l["montant_sal"]
    
    # Récupération des primes du salarié (via Global Primes)
    working_primes = custom_primes_override if custom_primes_override is not None else getattr(worker, "primes", [])
    
    # Constantes pour évaluation des formules
    computed_constants = calculate_constants(
        worker, 
        payvar, 
        brut_courant, 
        worker.salaire_base, 
        taux_h,
        (worker.salaire_base / 21.67),
        period=period,
    )

    primes_overrides_dict = kwargs.get("primes_overrides", {}) or {}
    existing_labels_norm = set()

    if working_primes:
        for prime in working_primes:
            if not prime.is_active:
                continue
            try:
                # Récupérer override temporaire (depuis import Excel)
                override = primes_overrides_dict.get(prime.label, {})
                ov_nombre = override.get("nombre")
                ov_base = override.get("base")

                # Evaluation Nombre : Override > Formule > Défaut
                if ov_nombre is not None:
                    nombre = float(ov_nombre)  # IMPORTE
                elif prime.formula_nombre:
                    nombre = evaluate_formula(prime.formula_nombre, computed_constants)  # FORMULE GLOBALE
                else:
                    nombre = 0.0  # DÉFAUT (Modifié de 1.0 à 0.0)
                
                # Evaluation Base : Override > Formule > Défaut
                if ov_base is not None:
                    base = float(ov_base)  # IMPORTE
                elif prime.formula_base:
                    base = evaluate_formula(prime.formula_base, computed_constants)  # FORMULE GLOBALE
                else:
                    base = 0.0  # DÉFAUT
                
                # Evaluation Taux (pas d'override possible, toujours formule)
                # DÉFAUT Taux : 0.0 (Modifié de 1.0 à 0.0 pour éviter calcul parasite)
                taux = evaluate_formula(prime.formula_taux, computed_constants) if prime.formula_taux else 0.0
                taux = taux / 100.0 # Convert to percentage (input 1 -> 0.01)
                
                # Opérateurs
                op1 = getattr(prime, "operation_1", "*")
                op2 = getattr(prime, "operation_2", "*")

                def apply_op(a, op, b):
                    if op == "+": return a + b
                    if op == "-": return a - b
                    if op == "*": return a * b
                    if op == "/": return a / b if b != 0 else 0
                    return a * b

                # Calcul final
                val_inter = apply_op(nombre, op1, base)
                montant = apply_op(val_inter, op2, taux)
                
                if montant > 0:
                    lines.append({
                        "label": prime.label,
                        "nombre": nombre if (prime.formula_nombre or ov_nombre is not None) else None,
                        "base": base if (prime.formula_base or ov_base is not None) else None,
                        "taux_sal": taux if prime.formula_taux else None,
                        "montant_sal": montant,
                        "taux_pat": None,
                        "montant_pat": 0
                    })
                    existing_labels_norm.add(prime.label.lower().strip())

            except Exception as e:
                # Ignorer les erreurs de formule (affichage = 0)
                pass 

    # Si des overrides existent pour des labels NON présents dans working_primes (ex: nouveaux labels)
    # On doit aussi les traiter
    for label, override in primes_overrides_dict.items():
        if label.lower().strip() in existing_labels_norm:
            continue # Déjà traité via working_primes
        
        try:
            ov_nombre = override.get("nombre")
            ov_base = override.get("base")
            if ov_nombre is None and ov_base is None: continue
            
            nombre = float(ov_nombre) if ov_nombre is not None else 1.0
            base = float(ov_base) if ov_base is not None else 0.0
            montant = nombre * base # Simple multiplication
            
            if montant > 0:
                 lines.append({
                    "label": label,
                    "nombre": nombre if ov_nombre is not None else None,
                    "base": base if ov_base is not None else None,
                    "taux_sal": 1.0,
                    "montant_sal": montant,
                    "taux_pat": None,
                    "montant_pat": 0
                })
                 existing_labels_norm.add(label.lower().strip())
        except: pass 

    # -------- PRIMES 1..10 (LEGACY / MANUEL) --------
    # Ces primes sont traitées APRÈS les primes importées
    # Si un label existe déjà via import, on SKIP le manuel (Priorité Import > Manuel)

    primes_overrides_dict = kwargs.get("primes_overrides", {}) or {}

    if pv or primes_overrides_dict:
        # Récupération des labels custom
        # (Prime 1..5 customs dans employer, 6..10 sont fix "Prime X")
        
        for i in range(1, 11):
            # Determine Label
            default_label = f"Prime {i}"
            custom_label = None
            if i <= 5:
                custom_label = getattr(employer, f"label_prime{i}", None)
            
            final_label = custom_label if custom_label else default_label
            
            # CHECK DUPLICATE: Skip if already handled by Global Primes
            if final_label.lower().strip() in existing_labels_norm:
                continue

            field = f"prime{i}"
            val = getattr(pv, field, 0.0) if pv else 0.0

            # Check Override (PayrollPrime)
            # Priorité: si on trouve un override pour ce label, on l'utilise (Nombre/Base)
            override = primes_overrides_dict.get(final_label, {})
            ov_nombre = override.get("nombre")
            ov_base = override.get("base")
            
            if ov_nombre is not None or ov_base is not None:
                # Calcul via Nombre * Base (Si l'un est manquant, on applique des défauts logiques)
                nombre = float(ov_nombre) if ov_nombre is not None else 1.0
                base = float(ov_base) if ov_base is not None else 0.0
                montant = nombre * base
                if montant > 0:
                     lines.append(_row(final_label, nombre, base, "", _money(montant), "", 0))
            
            elif val and float(val) != 0:
                # Fallback: Valeur simple dans PayVar (Montant unique)
                lines.append(_row(final_label, 1, "", "", _money(val), "", 0))


        # Allocation familiale
        # Allocation familiale
        if pv and getattr(pv, "alloc_familiale", 0):
            lines.append(_row("Allocation familiale", 1, "", "", _money(pv.alloc_familiale), "", 0))

        # Avances & déductions
        if pv and getattr(pv, "avance_quinzaine", 0):
            lines.append(_row("Avance sur salaire (quinzaine)","","","",-_money(pv.avance_quinzaine),"",0))
        if pv and getattr(pv, "avance_speciale_rembfixe", 0):
            lines.append(_row("Avance spéciale (mensuelle)","","","",-_money(pv.avance_speciale_rembfixe),"",0))
        for k in ("autre_ded1", "autre_ded2", "autre_ded3", "autre_ded4"):
            v = getattr(pv, k, 0.0) if pv else 0.0
            if v and float(v) != 0:
                lines.append(_row(k.replace("_", " ").title(), "", "", "", -_money(v), "", 0))

    # Avantages en nature (Hybrid: PayVar > Worker)
    # MOVED OUTSIDE the pv conditional block to ensure they're always evaluated
    av_vehicule = getattr(pv, "avantage_vehicule", 0) if pv else 0
    if av_vehicule == 0: av_vehicule = getattr(worker, "avantage_vehicule", 0) or 0

    av_logement = getattr(pv, "avantage_logement", 0) if pv else 0
    if av_logement == 0: av_logement = getattr(worker, "avantage_logement", 0) or 0

    av_telephone = getattr(pv, "avantage_telephone", 0) if pv else 0
    if av_telephone == 0: av_telephone = getattr(worker, "avantage_telephone", 0) or 0

    av_autres = getattr(pv, "avantage_autres", 0) if pv else 0
    if av_autres == 0: av_autres = getattr(worker, "avantage_autres", 0) or 0

    if av_vehicule > 0:
        lines.append(_row("Avantage en nature véhicule", 1, "", "", _money(av_vehicule), "", 0))
    if av_logement > 0:
        lines.append(_row("Avantage en nature logement", 1, "", "", _money(av_logement), "", 0))
    if av_telephone > 0:
        lines.append(_row("Avantage en nature téléphone", 1, "", "", _money(av_telephone), "", 0))
    if av_autres > 0:
        lines.append(_row("Autres avantages en natures", 1, "", "", _money(av_autres), "", 0))

    # [PATCH] Termination Indemnities (Moved to main scope)
    # --- INDEMNITÉS DE RUPTURE (SI APPLICABLE) ---
    term_data = kwargs.get("termination_data")
    
    if term_data:
        import math
        
        groupe = term_data.get("groupe_preavis", 1) or 1
        nature = term_data.get("nature_contrat", "CDI")
        d_deb = term_data.get("date_debauche")
        d_emb = worker.date_embauche
        
        ancien_jr = 0
        if d_deb and d_emb:
            try:
                ancien_jr = (d_deb - d_emb).days
            except:
                ancien_jr = computed_constants.get("ANCIENJR", 0.0)
        else:
            ancien_jr = computed_constants.get("ANCIENJR", 0.0)
            
        
        notice_days = 0.0
        if nature == "CDI":
            S = ancien_jr
            G = int(groupe)
            if S > 0:
                if G == 1:
                    if S < 8: notice_days = 1
                    elif S < 90: notice_days = 3
                    elif S < 365: notice_days = 8
                    elif S <= 1825: notice_days = 10 + 2 * math.floor((S - 365) / 365)
                    else: notice_days = 30
                elif G == 2:
                    if S < 8: notice_days = 2
                    elif S < 90: notice_days = 8
                    elif S < 365: notice_days = 15
                    elif S <= 1825: notice_days = 30 + 2 * math.floor((S - 365) / 365)
                    else: notice_days = 45
                elif G == 3:
                    if S < 8: notice_days = 3
                    elif S < 90: notice_days = 15
                    elif S < 365: notice_days = 30
                    elif S <= 1825: notice_days = 45 + 2 * math.floor((S - 365) / 365)
                    else: notice_days = 60
                elif G == 4:
                    if S < 8: notice_days = 4
                    elif S < 90: notice_days = 30
                    elif S < 365: notice_days = 45
                    elif S <= 1825: notice_days = 75 + 2 * math.floor((S - 365) / 365)
                    else: notice_days = 90
                elif G == 5:
                    if S < 8: notice_days = 5
                    elif S < 90: notice_days = 30
                    elif S < 365: notice_days = 90
                    elif S <= 1825: notice_days = 120 + 2 * math.floor((S - 365) / 365)
                    else: notice_days = 180

        deja_fait = float(term_data.get("jours_deja_faits", 0.0))
        if deja_fait < 0: deja_fait = 0
        reste_a_faire = notice_days - deja_fait
        if reste_a_faire < 0: reste_a_faire = 0.0
        
        avg_2 = term_data.get("avg_gross_2", 0.0) or 0.0
        montant_preavis = reste_a_faire * (avg_2 / 30.0)
        
        # [PATCH] Démission = Montant négatif (dû à l'employeur)
        type_sortie = term_data.get("type_sortie")
        if type_sortie == "D":
            montant_preavis = -montant_preavis
            
        if montant_preavis != 0:
            daily_rate_notice = avg_2 / 30.0
            lines.append(_row("Indemnité compensatrice de préavis", _money(reste_a_faire), _money(daily_rate_notice), "", _money(montant_preavis), "", 0))

        balance_cp = term_data.get("leave_balance", 0.0)
        avg_12 = term_data.get("avg_gross_12", 0.0) or 0.0
        daily_rate_cp = avg_12 / 24.0
        
        if balance_cp > 0:
            montant_cp = balance_cp * daily_rate_cp
            lines.append(_row("Indemnité compensatrice de congés", _money(balance_cp), _money(daily_rate_cp), "", _money(montant_cp), "", 0))
        elif balance_cp < 0:
            montant_cp = balance_cp * daily_rate_cp 
            lines.append(_row("Retenue pour congés pris par anticipation", _money(balance_cp), _money(daily_rate_cp), "", _money(montant_cp), "", 0))


    # ---- Somme des bruts en numéraire ----
    somme_bruts_numeraire = 0.0
    total_non_imposable = 0.0  # Pour déduction ultérieure sur RIM
    
    for l in lines:
        label_l = l["label"].lower()
        amt = l["montant_sal"]
        if "cotisation" in label_l or "irsa" in label_l: continue
        if "avantage" in label_l and "nature" in label_l: continue
        # if "non imposable" in label_l: continue  <-- REVERTED: On inclut tout dans le brut
        if "allocation familiale" in label_l or "avance" in label_l or "ded" in label_l: continue
        
        if amt != 0:
            somme_bruts_numeraire += amt
            
        # Si non imposable (ex: HSNI 130/150), on cumule pour déduire du RIM plus tard
        if "non imposable" in label_l:
            total_non_imposable += amt

    somme_bruts_numeraire = _money(somme_bruts_numeraire)

    # ---- Somme des avantages en nature taxables ----
    somme_avantages_taxables = 0.0
    
    # Recalcul des valeurs résolues pour cette section (car scope différent ou pour être sûr)
    # Idéalement on déplacerait la résolution plus haut, mais ici on répète la logique pour minimiser le diff risque
    _av_veh = getattr(pv, "avantage_vehicule", 0) if pv else 0
    if _av_veh == 0: _av_veh = getattr(worker, "avantage_vehicule", 0) or 0

    _av_log = getattr(pv, "avantage_logement", 0) if pv else 0
    if _av_log == 0: _av_log = getattr(worker, "avantage_logement", 0) or 0

    _av_tel = getattr(pv, "avantage_telephone", 0) if pv else 0
    if _av_tel == 0: _av_tel = getattr(worker, "avantage_telephone", 0) or 0

    _av_aut = getattr(pv, "avantage_autres", 0) if pv else 0
    if _av_aut == 0: _av_aut = getattr(worker, "avantage_autres", 0) or 0

    av_vehicule_taxable = _money(_av_veh * 0.15) # TODO: Vérifier règle 15%
    av_logement_theorique = _av_log * 0.5
    plafond_logement = _money(somme_bruts_numeraire * 0.25)
    av_logement_taxable = _money(min(av_logement_theorique, plafond_logement))
    av_tel_taxable = _money(_av_tel * 0.15)
    av_autres_taxable = _money(_av_aut * 1.0)
    
    somme_brute_avantages = av_vehicule_taxable + av_logement_taxable + av_tel_taxable + av_autres_taxable
    plafond_global = _money(somme_bruts_numeraire * 0.20)
    
    if plafond_global > 0:
        somme_avantages_taxables = _money(min(somme_brute_avantages, plafond_global))
    else:
        somme_avantages_taxables = 0.0

    # ---- Somme des Bruts ----
    brut_total = _money(somme_bruts_numeraire + somme_avantages_taxables)

    # ---- CNaPS / SMIE / FMFP ----
    cotis_sal_total = 0.0
    cotis_pat_total = 0.0
    regulatory_snapshot = resolve_regulatory_snapshot(employer, worker)
    
    # CNaPS
    # Calcul du plafond : soit défini explicitement, soit par régime
    plafond_cnaps_db = getattr(employer, "plafond_cnaps_base", 0.0) or 0.0

    if plafond_cnaps_db > 0:
        plafond_cnaps = plafond_cnaps_db
    else:
        # Plafonds par défaut selon le régime (2025)
        # Non agricole : 2 101 440 Ar
        # Agricole :     2 132 000 Ar
        regime_code = "non_agricole"
        if getattr(employer, "type_regime", None):
             regime_code = getattr(employer.type_regime, "code", "non_agricole")
        
        if regime_code == "agricole":
            plafond_cnaps = 2_132_000.0
        else:
            plafond_cnaps = 2_101_440.0

    # CNaPS - Use worker override if set, otherwise employer default
    taux_sal_cnaps = getattr(worker, "taux_sal_cnaps_override", None)
    if taux_sal_cnaps is None:
        taux_sal_cnaps = getattr(employer, "taux_sal_cnaps", 1.0) or 0.0
    
    taux_pat_cnaps = getattr(worker, "taux_pat_cnaps_override", None)
    if taux_pat_cnaps is None:
        taux_pat_cnaps = getattr(employer, "taux_pat_cnaps", 13.0) or 0.0

    cnaps_cfg = regulatory_snapshot.get("cnaps", {})
    plafond_cnaps = cnaps_cfg.get("plafond", plafond_cnaps)
    taux_sal_cnaps = cnaps_cfg.get("taux_sal", taux_sal_cnaps)
    taux_pat_cnaps = cnaps_cfg.get("taux_pat", taux_pat_cnaps)
    
    base_cnaps, cnaps_sal, cnaps_pat = compute_cnaps(
        brut_total,
        taux_sal_cnaps,
        taux_pat_cnaps,
        plafond_cnaps,
    )
    if cnaps_sal or cnaps_pat:
        # Affichage séparé des taux
        taux_sal_txt = f"{taux_sal_cnaps}%"
        taux_pat_txt = f"{taux_pat_cnaps}%"
        lines.append(_row("Cotisation CNaPS", "", f"{base_cnaps}", taux_sal_txt, -cnaps_sal, taux_pat_txt, cnaps_pat))
        cotis_sal_total += cnaps_sal
        cotis_pat_total += cnaps_pat

    # SMIE
    sm_embauche = getattr(employer, "sm_embauche", 0.0) or 0.0
    
    # Plafond SMIE : manuel > automatique (8*SME) > 0
    plafond_smie_db = getattr(employer, "plafond_smie", 0.0) or 0.0
    if plafond_smie_db > 0:
        plafond_smie = plafond_smie_db
    else:
        plafond_smie = sm_embauche * 8 if sm_embauche > 0 else 0.0
    
    # SMIE - Use worker override if set, otherwise employer default
    taux_sal_smie = getattr(worker, "taux_sal_smie_override", None)
    if taux_sal_smie is None:
        taux_sal_smie = getattr(employer, "taux_sal_smie", 0.0) or 0.0
    
    taux_pat_smie = getattr(worker, "taux_pat_smie_override", None)
    if taux_pat_smie is None:
        taux_pat_smie = getattr(employer, "taux_pat_smie", 0.0) or 0.0

    smie_cfg = regulatory_snapshot.get("smie", {})
    plafond_smie = smie_cfg.get("plafond", plafond_smie)
    taux_sal_smie = smie_cfg.get("taux_sal", taux_sal_smie)
    taux_pat_smie = smie_cfg.get("taux_pat", taux_pat_smie)
    smie_forfait_sal = smie_cfg.get("forfait_sal", getattr(employer, "smie_forfait_sal", 0.0) or 0.0)
    smie_forfait_pat = smie_cfg.get("forfait_pat", getattr(employer, "smie_forfait_pat", 0.0) or 0.0)
    
    base_smie, smie_sal, smie_pat = compute_smie(
        brut_total,
        taux_sal_smie,
        taux_pat_smie,
        smie_forfait_sal,
        smie_forfait_pat,
        plafond_smie
    )
    if smie_sal or smie_pat:
        taux_sal_txt = f"{taux_sal_smie}%" if not smie_forfait_sal else "Forfait"
        taux_pat_txt = f"{taux_pat_smie}%" if not smie_forfait_pat else "Forfait"
        lines.append(_row("Cotisation SMIE", "", f"{base_smie}", taux_sal_txt, -smie_sal, taux_pat_txt, smie_pat))
        cotis_sal_total += smie_sal
        cotis_pat_total += smie_pat

    # FMFP
    # FMFP suit le plafond CNaPS
    # Use worker override if set, otherwise employer default
    taux_pat_fmfp = getattr(worker, "taux_pat_fmfp_override", None)
    if taux_pat_fmfp is None:
        taux_pat_fmfp = getattr(employer, "taux_pat_fmfp", 1.0) or 0.0

    fmfp_cfg = regulatory_snapshot.get("fmfp", {})
    taux_pat_fmfp = fmfp_cfg.get("taux_pat", taux_pat_fmfp)
    fmfp_plafond = fmfp_cfg.get("plafond", plafond_cnaps)

    fmfp_pat = compute_fmfp(brut_total, taux_pat_fmfp, fmfp_plafond)
    if fmfp_pat:
        taux_pat_txt = f"{taux_pat_fmfp}%"
        lines.append(_row("Cotisation FMFP", "", f"{fmfp_plafond if brut_total > fmfp_plafond else brut_total}", "", 0.0, taux_pat_txt, fmfp_pat))
        cotis_pat_total += fmfp_pat

    # ---- Totaux finaux ----
    credits = 0.0
    debits = 0.0
    for l in lines:
        amt = l["montant_sal"]
        if amt > 0: credits += amt
        else: debits += abs(amt)

    cotisations = cotis_sal_total + cotis_pat_total
    rim = brut_total - cotis_sal_total - total_non_imposable

    # IRSA
    from app.core.irsa import calcul_irsa
    nb_enfants = getattr(worker, "nombre_enfant", 0) or 0
    irsa_val = calcul_irsa(rim, nb_enfants)
    # Pour l'IRSA, préserver la valeur entière calculée (pas d'arrondi à 2 décimales)
    irsa = round(irsa_val, 0)  # Arrondir à l'entier le plus proche
    debits += irsa  # Utiliser la valeur arrondie pour la cohérence
    
    if irsa > 0:
        lines.append(_row("IRSA", "", "", "", -irsa, "", 0))
    
    # Avance sur salaire (affichage)
    avance_dict = kwargs.get("avance_dict", None)
    if avance_dict and avance_dict.get("montant", 0) > 0:
        montant_avance = _money(avance_dict["montant"])
        lines.append(_row("Avance sur salaire", "", "", "", -montant_avance, "", 0))

    # Net
    match_avance = getattr(payvar, "avance_quinzaine", 0.0) or 0.0
    match_speciale = getattr(payvar, "avance_speciale_rembfixe", 0.0) or 0.0
    match_ded = 0.0
    if payvar:
        for k in ("autre_ded1", "autre_ded2", "autre_ded3", "autre_ded4"):
             match_ded += (getattr(payvar, k, 0.0) or 0.0)
    
    # Avances importées depuis Excel
    avance_dict = kwargs.get("avance_dict", None)
    avance_importee = 0.0
    if avance_dict and avance_dict.get("montant", 0) > 0:
        avance_importee = float(avance_dict["montant"])

    net_val = somme_bruts_numeraire - cotis_sal_total - irsa - match_avance - match_speciale - match_ded - avance_importee
    net = _money(net_val)

    totals = {
        "salaire_brut_numeraire": _money(somme_bruts_numeraire),
        "somme_avantages_taxables": _money(somme_avantages_taxables),
        "brut": _money(brut_total),
        "cotisations_salariales": _money(cotis_sal_total),
        "cotisations_patronales": _money(cotis_pat_total),
        "cotisations": _money(cotisations),
        "irsa": irsa,
        "debits": _money(debits),
        "credits": _money(credits),
        "net": net,
        "regulatory_snapshot": regulatory_snapshot,
        "computed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    
    return lines, totals, computed_constants
