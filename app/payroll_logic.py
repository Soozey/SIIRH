# backend/app/payroll_logic.py
from typing import Dict, List, Tuple, Any

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
    sal = _money(base_cot * (taux_sal/100.0))
    pat = _money(base_cot * (taux_pat/100.0))
    return base_cot, sal, pat

def compute_fmfp(brut_base: float, taux_pat: float):
    return _money(brut_base * (taux_pat/100.0))

def compute_smie(brut_base: float, taux_sal: float, taux_pat: float, forfait_sal: float, forfait_pat: float):
    sal = _money(brut_base * (taux_sal/100.0)) + _money(forfait_sal)
    pat = _money(brut_base * (taux_pat/100.0)) + _money(forfait_pat)
    return sal, pat

def compute_preview(employer, worker, payvar, period: str):
    """
    Calcule les lignes + totaux d'un bulletin de PREVIEW.
    Version simplifiée :
      - Salaire journalier = base / 21.67
      - HS 130% = heures * taux_horaire * 1.3 (idem 150% = *1.5)
      - Dimanche 40% = heures * taux_horaire * 0.4
      - Nuit hab. 30% = heures * taux_horaire * 0.3
      - Nuit occ. 50% = heures * taux_horaire * 0.5
      - Férié 200% = heures * taux_horaire * 2.0
      - Avances & déductions : montants négatifs côté salarié
      - CNaPS / SMIE / FMFP : paramétrables côté employeur (simples ici)
      - IRSA: mis à 0 (à brancher ensuite)
    """
    lines: List[Dict[str, Any]] = []

    # Données de base
    salaire_base = _money(worker.salaire_base)
    taux_h = worker.salaire_horaire or (worker.vhm and (worker.salaire_base / worker.vhm)) or 0.0
    taux_h = _money(taux_h)

    # 1) Salaire de base
    lines.append(_row("Salaire de base", 1, salaire_base, "", salaire_base, "", 0))

    # 2) Variables (si aucune saisie, on calcule quand même le brut)
    pv = payvar
    if pv:
        # Absences en jours
        per_day = _money(salaire_base / ABS_DIVISOR)

        def add_abs(label, jours):
            jours = float(jours or 0)
            if jours:
                m = -_money(jours * per_day)
                lines.append(_row(label, jours, per_day, "", m, "", 0))

        add_abs("Absence maladie", pv.abs_maladie_j)
        add_abs("Absence non rémunérée (jours)", pv.abs_non_remu_j)
        add_abs("Mis à pied", pv.mise_a_pied_j)

        # Absence en heures (optionnel)
        if (pv.abs_non_remu_h or 0) > 0:
            m = -_money(float(pv.abs_non_remu_h) * taux_h)
            lines.append(_row("Absence non rémunérée (heures)", pv.abs_non_remu_h, taux_h, "", m, "", 0))

        # Heures sup (montant complet)
        def add_hs(label, heures, coef):
            heures = float(heures or 0)
            if heures:
                m = _money(heures * taux_h * coef)
                lines.append(_row(label, heures, taux_h, f"{int(coef*100)}%", m, "", 0))

        add_hs("HS Non Imposable à 130%", pv.hsni_130_h, 1.3)
        add_hs("HS Imposable à 130%", pv.hsi_130_h, 1.3)
        add_hs("HS Non Imposable à 150%", pv.hsni_150_h, 1.5)
        add_hs("HS Imposable à 150%", pv.hsi_150_h, 1.5)

        # Majorations
        def add_maj(label, heures, coef):
            heures = float(heures or 0)
            if heures:
                m = _money(heures * taux_h * coef)
                lines.append(_row(label, heures, taux_h, f"{int(coef*100)}%", m, "", 0))

        add_maj("Travail de dimanche 40%", pv.dimanche_h, 0.4)
        add_maj("Travail de nuit habituelle 30%", pv.nuit_hab_h, 0.3)
        add_maj("Travail de nuit occasionnelle 50%", pv.nuit_occ_h, 0.5)
        add_maj("Travail le jour férié 200%", pv.ferie_jour_h, 2.0)

        # Primes 1..10 (si présentes dans ton modèle)
        for i in range(1, 11):
            val = getattr(pv, f"prime{i}", 0.0) if hasattr(pv, f"prime{i}") else 0.0
            if val and float(val) != 0:
                lines.append(_row(f"Prime/indemnité {i}", 1, "", "", _money(val), "", 0))

        # Avantages en nature
        if getattr(pv, "avantage_vehicule", 0):  lines.append(_row("Avantage en nature véhicule", 1, "", "", _money(pv.avantage_vehicule), "", 0))
        if getattr(pv, "avantage_logement", 0):  lines.append(_row("Avantage en nature logement", 1, "", "", _money(pv.avantage_logement), "", 0))
        if getattr(pv, "avantage_telephone", 0): lines.append(_row("Avantage en nature téléphone", 1, "", "", _money(pv.avantage_telephone), "", 0))
        if getattr(pv, "avantage_autres", 0):    lines.append(_row("Autres avantages en natures", 1, "", "", _money(pv.avantage_autres), "", 0))

        # Allocation familiale (crédit salaire)
        if getattr(pv, "alloc_familiale", 0):
            lines.append(_row("Allocation familiale", 1, "", "", _money(pv.alloc_familiale), "", 0))

        # Avances & déductions
        if getattr(pv, "avance_quinzaine", 0):
            lines.append(_row("Avance sur salaire (quinzaine)", "", "", "", -_money(pv.avance_quinzaine), "", 0))
        if getattr(pv, "avance_speciale_rembfixe", 0):
            lines.append(_row("Avance spéciale (mensuelle)", "", "", "", -_money(pv.avance_speciale_rembfixe), "", 0))
        for k in ("autre_ded1", "autre_ded2", "autre_ded3", "autre_ded4"):
            v = getattr(pv, k, 0.0)
            if v and float(v) != 0:
                lines.append(_row(k.replace("_", " ").title(), "", "", "", -_money(v), "", 0))

    # ---- BRUT provisoire (avant cotisations) ----
    brut = 0.0
    credits = 0.0
    debits = 0.0
    for l in lines:
        amt = l["montant_sal"]
        if amt > 0 and not any(key in l["label"].lower() for key in ["cotisation", "irsa"]):
            brut += amt
        if amt > 0: credits += amt
        else: debits += abs(amt)
    brut = _money(brut)

    # ---- CNaPS / SMIE / FMFP (paramètres employeur) ----
    cotis_sal_total = 0.0
    cotis_pat_total = 0.0

    # CNaPS
    base_cnaps, cnaps_sal, cnaps_pat = compute_cnaps(
        brut,
        getattr(employer, "taux_sal_cnaps", 1.0) or 0.0,
        getattr(employer, "taux_pat_cnaps", 13.0) or 0.0,
        getattr(employer, "plafond_cnaps_base", 0.0) or 0.0
    )
    if cnaps_sal or cnaps_pat:
        lines.append(_row("Cotisation CNaPS", "", f"{base_cnaps}", f"S:{getattr(employer,'taux_sal_cnaps',1.0)}% / P:{getattr(employer,'taux_pat_cnaps',13.0)}%",
                          -cnaps_sal, "", cnaps_pat))
        cotis_sal_total += cnaps_sal
        cotis_pat_total += cnaps_pat

    # SMIE
    smie_sal, smie_pat = compute_smie(
        brut,
        getattr(employer, "taux_sal_smie", 0.0) or 0.0,
        getattr(employer, "taux_pat_smie", 0.0) or 0.0,
        getattr(employer, "smie_forfait_sal", 0.0) or 0.0,
        getattr(employer, "smie_forfait_pat", 0.0) or 0.0
    )
    if smie_sal or smie_pat:
        rate_txt = []
        if (getattr(employer, "taux_sal_smie", 0.0) or 0) > 0: rate_txt.append(f"S:{employer.taux_sal_smie}%")
        if (getattr(employer, "taux_pat_smie", 0.0) or 0) > 0: rate_txt.append(f"P:{employer.taux_pat_smie}%")
        if (getattr(employer, "smie_forfait_sal", 0.0) or 0) > 0: rate_txt.append(f"S forfait {employer.smie_forfait_sal}")
        if (getattr(employer, "smie_forfait_pat", 0.0) or 0) > 0: rate_txt.append(f"P forfait {employer.smie_forfait_pat}")
        lines.append(_row("Cotisation SMIE", "", f"{brut}", " / ".join(rate_txt) or "", -smie_sal, "", smie_pat))
        cotis_sal_total += smie_sal
        cotis_pat_total += smie_pat

    # FMFP (employeur uniquement)
    fmfp_pat = compute_fmfp(brut, getattr(employer, "taux_pat_fmfp", 1.0) or 0.0)
    if fmfp_pat:
        lines.append(_row("Cotisation FMFP", "", f"{brut}", f"P:{getattr(employer,'taux_pat_fmfp',1.0)}%", 0.0, "", fmfp_pat))
        cotis_pat_total += fmfp_pat

    # ---- Totaux finaux ----
    credits = 0.0
    debits = 0.0
    for l in lines:
        amt = l["montant_sal"]
        if amt > 0: credits += amt
        else: debits += abs(amt)

    cotisations = _money(cotis_sal_total + cotis_pat_total)
    irsa = _money(0.0)  # à implémenter plus tard
    net = _money(credits - debits)

    totals = {
        "brut": _money(brut),
        "cotisations_salariales": _money(cotis_sal_total),
        "cotisations_patronales": _money(cotis_pat_total),
        "cotisations": _money(cotisations),
        "irsa": irsa,
        "debits": _money(debits),
        "credits": _money(credits),
        "net": net,
    }
    return lines, totals
