"""Applicazione progressiva di un'imposta a scaglioni.

Usata sia dall'IRPEF nazionale sia dalle addizionali regionali che ragionano per scaglioni.
"""

from __future__ import annotations

Scaglione = tuple[float | None, float]  # (tetto dello scaglione, aliquota); tetto None = ultimo


def applica_scaglioni(imponibile: float, scaglioni: list[Scaglione]) -> float:
    """Imposta progressiva: ogni aliquota colpisce solo la quota di reddito nel proprio scaglione.

    Esempio con gli scaglioni IRPEF e imponibile 35.000:
        28.000 x 23% + 7.000 x 33%
    e NON 35.000 x 33%: l'aliquota dello scaglione superiore non si applica all'intero reddito.

    `scaglioni` deve essere ordinato per tetto crescente e terminare con un tetto None.
    """
    if imponibile <= 0:
        return 0.0

    imposta = 0.0
    soglia_precedente = 0.0
    for tetto, aliquota in scaglioni:
        if tetto is None:
            imposta += (imponibile - soglia_precedente) * aliquota
            break
        if imponibile <= tetto:
            imposta += (imponibile - soglia_precedente) * aliquota
            break
        imposta += (tetto - soglia_precedente) * aliquota
        soglia_precedente = tetto

    return imposta
