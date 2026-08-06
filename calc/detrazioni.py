"""Detrazione per redditi da lavoro dipendente, art. 13 comma 1 e 1-bis TUIR."""

from __future__ import annotations

# Bonus dell'art. 13 comma 1-bis: importo fisso aggiuntivo per una fascia intermedia di reddito.
BONUS_COMMA_1_BIS = 65.0
BONUS_REDDITO_MINIMO = 25_000.0
BONUS_REDDITO_MASSIMO = 35_000.0


def detrazione_lavoro_dipendente(imponibile_fiscale: float) -> float:
    """Detrazione spettante sul reddito da lavoro dipendente, in euro annui.

    Struttura dell'art. 13 co.1 TUIR:
      R <= 15.000            -> 1.955 fissi
      15.000 < R <= 28.000   -> 1.910 + 1.190 x (28.000 - R) / 13.000
      28.000 < R <= 50.000   -> 1.910 x (50.000 - R) / 22.000
      R > 50.000             -> nessuna detrazione

    Nota sulla discontinuita' a 15.000: la formula del secondo ramo vale 3.100 euro in 15.000,
    contro i 1.955 del primo ramo. Non e' un errore di implementazione, e' come e' scritta la
    norma; il salto e' compensato nella pratica dal trattamento integrativo, che si azzera
    progressivamente proprio in quella fascia.

    ASSUNZIONE: nessun carico familiare, quindi nessuna detrazione per coniuge o figli a carico;
    reddito da lavoro dipendente come unica fonte di reddito, quindi la detrazione non va
    rapportata ad altri redditi.
    """
    reddito = imponibile_fiscale

    if reddito <= 0:
        return 0.0
    if reddito <= 15_000:
        detrazione = 1_955.0
    elif reddito <= 28_000:
        detrazione = 1_910.0 + 1_190.0 * (28_000 - reddito) / 13_000
    elif reddito <= 50_000:
        detrazione = 1_910.0 * (50_000 - reddito) / 22_000
    else:
        detrazione = 0.0

    if BONUS_REDDITO_MINIMO < reddito <= BONUS_REDDITO_MASSIMO:
        detrazione += BONUS_COMMA_1_BIS

    return detrazione
