"""Addizionali regionale e comunale all'IRPEF, con lookup sui dati precalcolati in data/.

I due JSON sono prodotti da scripts/build_data.py a partire dai CSV MEF grezzi.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from calc.scaglioni import applica_scaglioni

DIR_DATI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
JSON_REGIONI = os.path.join(DIR_DATI, "regioni_addizionale_2026.json")
JSON_COMUNI = os.path.join(DIR_DATI, "comuni_addizionale_2024.json")


# --- caricamento dati ----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _regioni() -> dict:
    """Mappa chiave regione -> regole dell'addizionale. Letta una sola volta per processo."""
    with open(JSON_REGIONI, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _comuni_per_codice() -> dict:
    """Mappa codice catastale -> comune.

    La chiave e' il codice catastale e non il nome, perche' nel dataset MEF cinque denominazioni
    sono condivise da due comuni diversi (CASTRO, LIVO, PEGLIO, SAMONE, SAN TEODORO).
    """
    with open(JSON_COMUNI, encoding="utf-8") as f:
        return {comune["codice"]: comune for comune in json.load(f)}


def elenco_comuni() -> list[dict]:
    """Tutti i comuni selezionabili, ordinati per nome. Usato per popolare l'autocomplete."""
    return sorted(_comuni_per_codice().values(), key=lambda c: (c["nome"], c["provincia"]))


def trova_comune(codice: str) -> dict | None:
    """Comune per codice catastale, None se non presente nel dataset."""
    return _comuni_per_codice().get(codice)


def trova_regione(chiave_regione: str) -> dict | None:
    """Regole dell'addizionale regionale per chiave regione, None se assente."""
    return _regioni().get(chiave_regione)


# --- calcolo -------------------------------------------------------------------------------------


def addizionale_regionale(imponibile_fiscale: float, chiave_regione: str) -> float:
    """Addizionale regionale IRPEF 2026 dovuta sull'imponibile fiscale.

    Le regioni deliberano l'addizionale in due modi diversi e il dataset MEF li distingue:

      - "unica": una sola aliquota applicata all'INTERO imponibile (es. Veneto, Sicilia,
        Sardegna, Basilicata, Calabria, Valle d'Aosta). Non e' progressiva: superata
        l'eventuale soglia di esenzione, l'aliquota colpisce tutto il reddito.
      - "scaglioni": aliquote crescenti applicate per scaglioni come l'IRPEF nazionale, dove
        ogni aliquota tocca solo la quota di reddito compresa nel proprio scaglione. Il numero
        di scaglioni varia da regione a regione (Abruzzo, Liguria e Bolzano ne hanno tre).

    ASSUNZIONE: si usa sempre l'aliquota base per fascia di reddito. Diverse regioni prevedono
    aliquote agevolate, detrazioni o deduzioni condizionate a figli o familiari a carico e a
    situazioni di disabilita' (Marche, Umbria, Puglia, Sardegna, Veneto, Trento, Bolzano):
    l'ipotesi del prototipo e' "nessun carico familiare", quindi quelle clausole sono ignorate.
    """
    if imponibile_fiscale <= 0:
        return 0.0

    regione = _regioni().get(chiave_regione)
    if regione is None:
        raise KeyError(f"Regione non presente nei dati: {chiave_regione!r}")

    if regione["modalita"] == "unica":
        return imponibile_fiscale * regione["aliquota"]

    scaglioni = [(s["fino_a"], s["aliquota"]) for s in regione["scaglioni"]]
    return applica_scaglioni(imponibile_fiscale, scaglioni)


def addizionale_comunale(imponibile_fiscale: float, aliquota: float) -> float:
    """Addizionale comunale IRPEF dovuta sull'imponibile fiscale.

    L'aliquota e' quella media derivata dal dataset MEF 2024 (vedi scripts/build_data.py) e si
    applica in modo piatto: e' una stima, non riproduce le soglie di esenzione ne' gli scaglioni
    deliberati dai singoli comuni.
    """
    if imponibile_fiscale <= 0:
        return 0.0
    return imponibile_fiscale * aliquota
