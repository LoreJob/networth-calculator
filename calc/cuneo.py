"""Misure strutturali sul cuneo fiscale introdotte dalla legge 207/2024."""

from __future__ import annotations


def somma_esente(reddito_lavoro: float) -> float:
    """Somma non imponibile spettante fino a 20.000 euro di reddito da lavoro."""
    if reddito_lavoro <= 0 or reddito_lavoro > 20_000:
        return 0.0
    if reddito_lavoro <= 8_500:
        aliquota = 0.071
    elif reddito_lavoro <= 15_000:
        aliquota = 0.053
    else:
        aliquota = 0.048
    return reddito_lavoro * aliquota


def detrazione_aggiuntiva(reddito_complessivo: float) -> float:
    """Detrazione di 1.000 euro tra 20-32 mila, con decalage fino a 40 mila."""
    if 20_000 < reddito_complessivo <= 32_000:
        return 1_000.0
    if 32_000 < reddito_complessivo < 40_000:
        return 1_000.0 * (40_000 - reddito_complessivo) / 8_000
    return 0.0
