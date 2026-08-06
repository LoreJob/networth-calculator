"""Trattamento di fine rapporto maturato nell'anno."""

from __future__ import annotations

# La quota annua di TFR e' la retribuzione utile divisa per 13,5 (art. 2120 c.c.).
DIVISORE_TFR = 13.5


def tfr_maturato(ral: float) -> float:
    """Quota di TFR maturata nell'anno.

    NON entra nel netto annuo o mensile: e' un accantonamento, non cassa percepita dal
    lavoratore nell'anno. Viene mostrato separatamente come dato informativo.

    SEMPLIFICAZIONE: si usa la RAL come retribuzione utile e si ignora sia il contributo dello
    0,50% al Fondo di garanzia sia la rivalutazione annua del fondo accantonato.
    """
    if ral <= 0:
        return 0.0
    return ral / DIVISORE_TFR
