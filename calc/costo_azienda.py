"""Costo diretto del lavoro per l'azienda, con parametri espliciti e modificabili."""

from __future__ import annotations

ALIQUOTA_CONTRIBUTI_DATORE_DEFAULT = 0.30
ALIQUOTA_INAIL_DEFAULT = 0.004
DIVISORE_TFR = 13.5


def costo_retribuzione(
    ral: float,
    aliquota_datore: float = ALIQUOTA_CONTRIBUTI_DATORE_DEFAULT,
    aliquota_inail: float = ALIQUOTA_INAIL_DEFAULT,
) -> dict:
    """Costo annuo diretto; non include costi indiretti, amministrativi o incentivi."""
    contributi = ral * aliquota_datore
    inail = ral * aliquota_inail
    tfr = ral / DIVISORE_TFR
    totale = ral + contributi + inail + tfr
    return {
        "ral": ral,
        "contributi_datore": contributi,
        "inail": inail,
        "tfr": tfr,
        "totale": totale,
    }


def ral_per_budget(budget: float, aliquota_datore: float, aliquota_inail: float) -> float:
    """Incremento RAL acquistabile con un budget aziendale comprensivo degli oneri diretti."""
    moltiplicatore = 1 + aliquota_datore + aliquota_inail + 1 / DIVISORE_TFR
    return max(0.0, budget) / moltiplicatore
