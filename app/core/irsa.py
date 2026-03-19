# app/core/irsa.py

from math import floor

MINIMUM_PERCEPTION = 3000  # Ariary
DEDUCTION_PAR_ENFANT = 2000  # Ariary par enfant


def arrondir_centaines_inferieures(montant: float) -> int:
    """
    RIA = Revenu imposable Arrondi à la centaine inférieure.
    Exemple : 456 789 -> 456 700
    """
    if montant <= 0:
        return 0
    return int((montant // 100) * 100)


def calcul_irsa_brut(ria: float) -> float:
    """
    Calcule l'IRSA "brut" par TRANCHE à partir du RIA.
    Les tranches sont celles décrites dans ton PROMPT-ASSEMBLE.
    (Tu ajusteras les bornes/taux ici si les taux officiels changent.)
    """

    if ria <= 350_000:
        # Tranche 0 : exonéré
        return 0.0

    elif 350_001 <= ria <= 400_000:
        # Tranche 1 : 5% sur la partie au-dessus de 350 000
        return (ria - 350_001) * 0.05

    elif 400_001 <= ria <= 500_000:
        # Tranche 2 : 2 500 + 10% de la partie au-dessus de 400 000
        return (ria - 400_001) * 0.10 + 2_500

    elif 500_001 <= ria <= 600_000:
        # Tranche 3 : 12 500 + 15% de la partie au-dessus de 500 000
        return (ria - 500_001) * 0.15 + 12_500

    else:  # ria >= 600_001
        # Tranche 4 : 27 500 + 20% de la partie au-dessus de 600 000
        return (ria - 600_001) * 0.20 + 27_500


def appliquer_deduction_enfants(irsa_brut: float, nb_enfants: int) -> float:
    """
    Applique la déduction de 2 000 Ar par enfant à charge.
    """
    if nb_enfants is None:
        nb_enfants = 0
    nb_enfants = max(0, nb_enfants)

    deduction = DEDUCTION_PAR_ENFANT * nb_enfants
    return max(irsa_brut - deduction, 0.0)


def appliquer_minimum_perception(irsa_apres_deduction: float) -> float:
    """
    Teste le minimum de perception.
    Si le montant est inférieur à 3 000, IRSA = 0.
    Sinon, IRSA = montant calculé.
    """
    if irsa_apres_deduction >= MINIMUM_PERCEPTION:
        return irsa_apres_deduction
    return 0.0


def calcul_irsa(rim: float, nb_enfants: int) -> float:
    """
    Pipeline complet :
    1) RIA = RIM arrondi à la centaine inférieure
    2) IRSA brut = tranches IRSA sur le RIA
    3) Déduction de 2 000 Ar par enfant à charge
    4) Application du minimum de perception (3 000 Ar)
    """
    if rim <= 0:
        return 0.0

    ria = arrondir_centaines_inferieures(rim)
    irsa_brut = calcul_irsa_brut(ria)
    irsa_apres_deduction = appliquer_deduction_enfants(irsa_brut, nb_enfants)
    irsa_finale = appliquer_minimum_perception(irsa_apres_deduction)

    # On peut arrondir à l'ariary
    return round(irsa_finale, 2)
