"""Trattamento integrativo (ex bonus Renzi), D.L. 3/2020 e successive modifiche."""

from __future__ import annotations

IMPORTO_PIENO = 1_200.0
SOGLIA_IMPORTO_PIENO = 15_000.0
SOGLIA_AZZERAMENTO = 28_000.0


def trattamento_integrativo(imponibile_fiscale: float) -> float:
    """Trattamento integrativo annuo spettante.

      R <= 15.000            -> 1.200 euro pieni
      15.000 < R <= 28.000   -> phase-out lineare da 1.200 a 0
      R > 28.000             -> nulla

    Si SOMMA al netto: non e' un'imposta ma una somma erogata in busta paga.

    SEMPLIFICAZIONE: il phase-out reale e' subordinato alla capienza delle detrazioni
    (l'importo spetta nei limiti della differenza tra detrazioni spettanti e imposta lorda).
    Qui usiamo l'interpolazione lineare sul reddito, che e' l'approssimazione comunemente
    adottata dai simulatori.
    """
    reddito = imponibile_fiscale

    if reddito <= 0:
        return 0.0
    if reddito <= SOGLIA_IMPORTO_PIENO:
        return IMPORTO_PIENO
    if reddito <= SOGLIA_AZZERAMENTO:
        quota_residua = (SOGLIA_AZZERAMENTO - reddito) / (SOGLIA_AZZERAMENTO - SOGLIA_IMPORTO_PIENO)
        return IMPORTO_PIENO * quota_residua
    return 0.0
