from typing import Any, Dict


CNAPS_DEFAULT_PLAFOND_BY_REGIME: Dict[str, float] = {
    "agricole": 2_132_000.0,
    "non_agricole": 2_101_440.0,
}


DECLARATIVE_ORGANISM_MAPPING: Dict[str, Dict[str, Any]] = {
    "cnaps": {
        "label": "CNaPS",
        "declaration_code": "CNAPS",
        "is_configurable": True,
    },
    "ostie": {
        "label": "OSTIE",
        "declaration_code": "OSTIE",
        "is_configurable": True,
        # No rate is enforced here until explicitly configured.
    },
    "fmfp": {
        "label": "FMFP",
        "declaration_code": "FMFP",
        "is_configurable": True,
    },
    "irsa": {
        "label": "IRSA",
        "declaration_code": "IRSA",
        "is_configurable": True,
    },
}


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _resolve_regime_code(employer: Any) -> str:
    type_regime = getattr(employer, "type_regime", None)
    code = getattr(type_regime, "code", None)
    if isinstance(code, str) and code.strip():
        return code.strip().lower()
    return "non_agricole"


def resolve_regulatory_snapshot(employer: Any, worker: Any) -> Dict[str, Any]:
    regime_code = _resolve_regime_code(employer)

    configured_cnaps_plafond = _as_float(getattr(employer, "plafond_cnaps_base", 0.0), 0.0)
    cnaps_plafond = (
        configured_cnaps_plafond
        if configured_cnaps_plafond > 0
        else CNAPS_DEFAULT_PLAFOND_BY_REGIME.get(regime_code, CNAPS_DEFAULT_PLAFOND_BY_REGIME["non_agricole"])
    )

    taux_sal_cnaps = _as_float(
        getattr(worker, "taux_sal_cnaps_override", None),
        _as_float(getattr(employer, "taux_sal_cnaps", 1.0), 1.0),
    )
    taux_pat_cnaps = _as_float(
        getattr(worker, "taux_pat_cnaps_override", None),
        _as_float(getattr(employer, "taux_pat_cnaps", 13.0), 13.0),
    )

    sm_embauche = _as_float(getattr(employer, "sm_embauche", 0.0), 0.0)
    configured_smie_plafond = _as_float(getattr(employer, "plafond_smie", 0.0), 0.0)
    smie_plafond = configured_smie_plafond if configured_smie_plafond > 0 else (sm_embauche * 8 if sm_embauche > 0 else 0.0)

    taux_sal_smie = _as_float(
        getattr(worker, "taux_sal_smie_override", None),
        _as_float(getattr(employer, "taux_sal_smie", 0.0), 0.0),
    )
    taux_pat_smie = _as_float(
        getattr(worker, "taux_pat_smie_override", None),
        _as_float(getattr(employer, "taux_pat_smie", 0.0), 0.0),
    )

    smie_forfait_sal = _as_float(getattr(employer, "smie_forfait_sal", 0.0), 0.0)
    smie_forfait_pat = _as_float(getattr(employer, "smie_forfait_pat", 0.0), 0.0)

    taux_pat_fmfp = _as_float(
        getattr(worker, "taux_pat_fmfp_override", None),
        _as_float(getattr(employer, "taux_pat_fmfp", 1.0), 1.0),
    )

    # Placeholder for OSTIE rates. Keep it configurable and inactive by default.
    taux_sal_ostie = _as_float(getattr(worker, "taux_sal_ostie_override", None), 0.0)
    taux_pat_ostie = _as_float(getattr(worker, "taux_pat_ostie_override", None), 0.0)

    return {
        "regime_code": regime_code,
        "work_time_reference": {
            "weekly_hours_default": 40.0,
            "monthly_hours_reference": 173.33,
        },
        "cnaps": {
            "taux_sal": taux_sal_cnaps,
            "taux_pat": taux_pat_cnaps,
            "plafond": cnaps_plafond,
        },
        "smie": {
            "taux_sal": taux_sal_smie,
            "taux_pat": taux_pat_smie,
            "forfait_sal": smie_forfait_sal,
            "forfait_pat": smie_forfait_pat,
            "plafond": smie_plafond,
        },
        "fmfp": {
            "taux_pat": taux_pat_fmfp,
            "plafond": cnaps_plafond,
        },
        "ostie": {
            "taux_sal": taux_sal_ostie,
            "taux_pat": taux_pat_ostie,
        },
        "declarative_mapping": DECLARATIVE_ORGANISM_MAPPING,
        "unconfirmed_rules": {
            "avantage_vehicule_taxable_rate": 0.15,
            "avantage_telephone_taxable_rate": 0.15,
            "avantage_logement_taxable_cap_rate": 0.25,
            "avantages_global_cap_rate": 0.20,
        },
    }
