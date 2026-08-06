"""IRPEF nazionale lorda, anno d'imposta 2026."""

from __future__ import annotations

from calc.scaglioni import Scaglione, applica_scaglioni

# Scaglioni IRPEF 2026: tre aliquote, invariate rispetto alla riforma a tre scaglioni.
#   23% fino a 28.000 euro
#   33% da 28.000 a 50.000 euro
#   43% oltre 50.000 euro
SCAGLIONI_IRPEF_2026: list[Scaglione] = [
    (28_000.0, 0.23),
    (50_000.0, 0.33),
    (None, 0.43),
]


def irpef_lorda(imponibile_fiscale: float) -> float:
    """IRPEF lorda progressiva sull'imponibile fiscale (RAL al netto dei contributi INPS)."""
    return applica_scaglioni(imponibile_fiscale, SCAGLIONI_IRPEF_2026)
