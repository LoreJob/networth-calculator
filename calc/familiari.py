"""Detrazioni 2026 per coniuge e figli fiscalmente a carico."""

from __future__ import annotations

from datetime import date

ANNO_FISCALE = 2026
SOGLIA_REDDITO_FAMILIARE = 2_840.51
SOGLIA_REDDITO_FIGLIO_FINO_24 = 4_000.0
DETRAZIONE_FIGLIO = 950.0
SOGLIA_BASE_FIGLI = 95_000.0
INCREMENTO_SOGLIA_PER_FIGLIO = 15_000.0


def _data_iso(valore: str) -> date:
    try:
        risultato = date.fromisoformat(str(valore))
    except (TypeError, ValueError):
        raise ValueError("Data di nascita del figlio non valida") from None
    if risultato > date(ANNO_FISCALE, 12, 31):
        raise ValueError("La data di nascita del figlio non puo' essere futura")
    return risultato


def _mesi(valore: object, nome: str) -> int:
    try:
        numero = int(valore)
    except (TypeError, ValueError):
        raise ValueError(f"{nome} non validi") from None
    if not 0 <= numero <= 12:
        raise ValueError(f"{nome} devono essere tra 0 e 12")
    return numero


def _reddito(valore: object, nome: str) -> float:
    try:
        numero = float(valore)
    except (TypeError, ValueError):
        raise ValueError(f"{nome} non valido") from None
    if numero < 0:
        raise ValueError(f"{nome} non puo' essere negativo")
    return numero


def _eta_al_31_dicembre(data_nascita: date) -> int:
    return ANNO_FISCALE - data_nascita.year


def _mesi_esistenza(data_nascita: date) -> int:
    if data_nascita.year < ANNO_FISCALE:
        return 12
    return 13 - data_nascita.month


def _mesi_detrazione_per_eta(data_nascita: date, disabile: bool) -> int:
    """Mesi dal 21° compleanno al mese prima del 30°, senza limite alto se disabile."""
    mesi = 0
    for mese in range(1, 13):
        indice = ANNO_FISCALE * 12 + mese
        mese_21 = (data_nascita.year + 21) * 12 + data_nascita.month
        mese_30 = (data_nascita.year + 30) * 12 + data_nascita.month
        if indice >= mese_21 and (disabile or indice < mese_30):
            mesi += 1
    return mesi


def _detrazione_coniuge_base(reddito: float) -> float:
    if reddito <= 15_000:
        return max(0.0, 800.0 - 110.0 * reddito / 15_000.0)
    if reddito <= 40_000:
        maggiorazioni = (
            (29_000, 29_200, 10),
            (29_200, 34_700, 20),
            (34_700, 35_000, 30),
            (35_000, 35_100, 20),
            (35_100, 35_200, 10),
        )
        extra = next((valore for minimo, massimo, valore in maggiorazioni if minimo < reddito <= massimo), 0)
        return 690.0 + extra
    if reddito <= 80_000:
        return 690.0 * (80_000.0 - reddito) / 40_000.0
    return 0.0


def calcola_familiari(
    reddito_contribuente: float,
    coniuge: dict | None = None,
    figli: list[dict] | None = None,
) -> dict:
    """Valida il profilo e restituisce detrazioni e stato fiscale dei familiari."""
    coniuge = coniuge or {}
    figli = figli or []
    if not isinstance(coniuge, dict) or not isinstance(figli, list):
        raise ValueError("Situazione familiare non valida")

    coniuge_presente = bool(coniuge.get("presente", False))
    reddito_coniuge = _reddito(coniuge.get("reddito", 0), "Reddito del coniuge")
    mesi_coniuge = _mesi(coniuge.get("mesi_carico", 12), "I mesi del coniuge")
    coniuge_a_carico = (
        coniuge_presente
        and mesi_coniuge > 0
        and reddito_coniuge <= SOGLIA_REDDITO_FAMILIARE
    )
    detrazione_coniuge = (
        _detrazione_coniuge_base(reddito_contribuente) * mesi_coniuge / 12
        if coniuge_a_carico else 0.0
    )

    figli_normalizzati = []
    for indice, figlio in enumerate(figli, start=1):
        if not isinstance(figlio, dict):
            raise ValueError(f"Dati del figlio {indice} non validi")
        nascita = _data_iso(figlio.get("data_nascita", ""))
        reddito_figlio = _reddito(figlio.get("reddito", 0), f"Reddito del figlio {indice}")
        mesi_carico = min(
            _mesi(figlio.get("mesi_carico", 12), f"I mesi del figlio {indice}"),
            _mesi_esistenza(nascita),
        )
        try:
            quota = float(figlio.get("quota_detrazione", 0.5))
        except (TypeError, ValueError):
            raise ValueError(f"Quota di detrazione del figlio {indice} non valida") from None
        if quota not in (0.0, 0.5, 1.0):
            raise ValueError("La quota di detrazione deve essere 0%, 50% o 100%")

        eta = _eta_al_31_dicembre(nascita)
        soglia = (
            SOGLIA_REDDITO_FIGLIO_FINO_24
            if eta <= 24 else SOGLIA_REDDITO_FAMILIARE
        )
        a_carico = mesi_carico > 0 and reddito_figlio <= soglia
        disabile = bool(figlio.get("disabile", False))
        mesi_eta = _mesi_detrazione_per_eta(nascita, disabile)
        mesi_detrazione = min(mesi_carico, mesi_eta) if a_carico else 0
        figli_normalizzati.append({
            "data_nascita": nascita.isoformat(),
            "eta_fine_anno": eta,
            "reddito": reddito_figlio,
            "soglia_reddito": soglia,
            "mesi_carico": mesi_carico,
            "mesi_detrazione": mesi_detrazione,
            "quota_detrazione": quota,
            "disabile": disabile,
            "a_carico": a_carico,
        })

    numero_figli_carico = sum(1 for figlio in figli_normalizzati if figlio["a_carico"])
    soglia_detrazione = SOGLIA_BASE_FIGLI + INCREMENTO_SOGLIA_PER_FIGLIO * max(
        0, numero_figli_carico - 1
    )
    coefficiente = max(0.0, (soglia_detrazione - reddito_contribuente) / soglia_detrazione)
    detrazione_figli = 0.0
    for figlio in figli_normalizzati:
        detrazione = (
            DETRAZIONE_FIGLIO
            * coefficiente
            * figlio["mesi_detrazione"] / 12
            * figlio["quota_detrazione"]
        )
        figlio["detrazione"] = detrazione
        detrazione_figli += detrazione

    return {
        "coniuge": {
            "presente": coniuge_presente,
            "reddito": reddito_coniuge,
            "mesi_carico": mesi_coniuge,
            "a_carico": coniuge_a_carico,
            "detrazione": detrazione_coniuge,
        },
        "figli": figli_normalizzati,
        "figli_a_carico": numero_figli_carico > 0,
        "numero_figli_a_carico": numero_figli_carico,
        "detrazione_coniuge": detrazione_coniuge,
        "detrazione_figli": detrazione_figli,
        "detrazione_totale": detrazione_coniuge + detrazione_figli,
    }
