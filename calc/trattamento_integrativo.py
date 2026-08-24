"""Trattamento integrativo (ex bonus Renzi), D.L. 3/2020 e successive modifiche."""

from __future__ import annotations

IMPORTO_PIENO = 1_200.0
SOGLIA_IMPORTO_PIENO = 15_000.0
SOGLIA_AZZERAMENTO = 28_000.0


def trattamento_integrativo(
    imponibile_fiscale: float,
    irpef_lorda: float | None = None,
    detrazione_lavoro: float | None = None,
    altre_detrazioni_rilevanti: float = 0.0,
    reddito_riferimento: float | None = None,
) -> float:
    """Trattamento integrativo annuo spettante.

      R <= 15.000            -> 1.200 euro se l'imposta supera la detrazione da lavoro - 75 euro
      15.000 < R <= 28.000   -> differenza positiva tra detrazioni rilevanti e imposta, max 1.200
      R > 28.000             -> nulla

    Si SOMMA al netto: non e' un'imposta ma una somma erogata in busta paga.

    Il chiamante passa imposta e detrazioni effettive. I valori opzionali mantengono la funzione
    utilizzabile isolatamente, ma la pipeline usa sempre il controllo di capienza.
    """
    # La quota esente del regime impatriati rileva per intero nella verifica delle soglie del
    # trattamento integrativo.
    reddito = imponibile_fiscale if reddito_riferimento is None else reddito_riferimento

    if reddito <= 0:
        return 0.0
    if irpef_lorda is None or detrazione_lavoro is None:
        return 0.0
    if reddito <= SOGLIA_IMPORTO_PIENO:
        return IMPORTO_PIENO if irpef_lorda > max(0.0, detrazione_lavoro - 75.0) else 0.0
    if reddito <= SOGLIA_AZZERAMENTO:
        detrazioni_rilevanti = detrazione_lavoro + altre_detrazioni_rilevanti
        return min(IMPORTO_PIENO, max(0.0, detrazioni_rilevanti - irpef_lorda))
    return 0.0
