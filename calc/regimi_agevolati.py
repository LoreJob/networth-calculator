"""Regimi fiscali agevolati applicabili al reddito di lavoro dipendente.

Il modulo non decide se il lavoratore possiede i requisiti legali: richiede un'attestazione
esplicita dell'utente e verifica soltanto coerenza temporale e percentuale del regime scelto.
"""

from __future__ import annotations

ANNO_FISCALE = 2026
ORDINARIO = "ordinario"
IMPATRIATI_2024 = "impatriati_2024"


def applica(ral: float, contributi: float, configurazione: dict | None = None) -> dict:
    """Restituisce imponibile e quota esclusa, senza modificare contributi o costo azienda."""
    dati = configurazione or {}
    tipo = str(dati.get("tipo") or ORDINARIO)
    reddito_post_contributi = max(0.0, ral - contributi)

    if tipo == ORDINARIO:
        return {
            "tipo": ORDINARIO,
            "nome": "Regime ordinario",
            "anno_inizio": None,
            "anno_fine": None,
            "quota_imponibile": 1.0,
            "quota_esente": 0.0,
            "imponibile_fiscale": reddito_post_contributi,
            "requisiti_attestati": False,
        }

    if tipo != IMPATRIATI_2024:
        raise ValueError("Regime fiscale non supportato")
    if dati.get("requisiti_attestati") is not True:
        raise ValueError("Conferma che i requisiti del regime agevolato siano stati verificati")
    try:
        anno_inizio = int(dati.get("anno_inizio"))
    except (TypeError, ValueError):
        raise ValueError("Inserisci l'anno di inizio del regime agevolato") from None

    if anno_inizio < 2024:
        raise ValueError("Il nuovo regime impatriati e' applicabile ai trasferimenti dal 2024")
    nome = "Lavoratori impatriati dal 2024"
    quota_imponibile = 0.50
    durata = 5
    limite_agevolabile = 600_000.0

    anno_fine = anno_inizio + durata - 1
    if not anno_inizio <= ANNO_FISCALE <= anno_fine:
        raise ValueError(
            f"Il regime selezionato non e' attivo nel {ANNO_FISCALE} "
            f"(periodo dichiarato {anno_inizio}-{anno_fine})"
        )

    # I contributi obbligatori non formano il reddito di lavoro dipendente (art. 51 TUIR). La
    # percentuale agevolata si applica quindi al reddito gia' al netto di tali contributi. Per gli
    # impatriati l'agevolazione si ferma a 600.000 euro annui e l'eccedenza resta imponibile.
    reddito_agevolabile = min(reddito_post_contributi, limite_agevolabile)
    reddito_non_agevolabile = max(0.0, reddito_post_contributi - limite_agevolabile)
    imponibile_fiscale = reddito_agevolabile * quota_imponibile + reddito_non_agevolabile
    quota_esente = reddito_post_contributi - imponibile_fiscale

    return {
        "tipo": tipo,
        "nome": nome,
        "anno_inizio": anno_inizio,
        "anno_fine": anno_fine,
        "quota_imponibile": quota_imponibile,
        "quota_esente": quota_esente,
        "imponibile_fiscale": imponibile_fiscale,
        "requisiti_attestati": True,
    }
