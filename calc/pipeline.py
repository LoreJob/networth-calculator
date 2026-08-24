"""Orchestratore: compone i moduli di calcolo in un unico risultato.

Unico punto in cui i passaggi vengono messi in sequenza. Le funzioni chiamate restano pure e
testabili una per una; qui si definisce solo l'ordine e la forma del risultato.
"""

from __future__ import annotations

from calc import (
    addizionali, cuneo, detrazioni, familiari, inps, irpef, regimi_agevolati, tfr,
    trattamento_integrativo,
)

MENSILITA_AMMESSE = (12, 13, 14)
MENSILITA_DEFAULT = 13

# RAL minima simulabile.
#
# Limite di prodotto, non fiscale: evita proiezioni annuali prive di significato per rapporti
# marginali. Il trattamento integrativo usa ora la verifica di capienza prevista dalla norma.
RAL_MINIMA = 1_000.0


def calcola(
    ral: float,
    codice_comune: str,
    mensilita: int = MENSILITA_DEFAULT,
    coniuge: dict | None = None,
    figli: list[dict] | None = None,
    regime_fiscale: dict | None = None,
) -> dict:
    """Proiezione del netto annuo e mensile a partire dalla RAL.

    Ordine dei passaggi:
      1.  imponibile previdenziale = RAL
      2.  contributi INPS a carico del dipendente
      3.  imponibile fiscale = RAL - contributi INPS
      4.  IRPEF lorda progressiva sull'imponibile fiscale
      5.  detrazioni da lavoro, coniuge e figli a carico
      6.  IRPEF netta = max(0, lorda - detrazioni)
      7.  addizionale regionale, con regione derivata dal comune scelto
      8.  addizionale comunale
      9.  trattamento integrativo (si somma, non si sottrae)
      10. netto annuo
      11. netto mensile = netto annuo / mensilita'
      12. TFR maturato, informativo e fuori dal netto

    Gli importi non vengono arrotondati durante il calcolo: l'arrotondamento avviene solo in
    uscita, per non propagare errori tra un passaggio e l'altro.
    """
    if ral < RAL_MINIMA:
        # Separatore delle migliaia all'italiana: il formato di default e' quello inglese.
        soglia = f"{RAL_MINIMA:,.0f}".replace(",", ".")
        raise ValueError(
            f"La RAL minima simulabile e' {soglia} euro"
        )
    if mensilita not in MENSILITA_AMMESSE:
        raise ValueError(f"Mensilita' non ammessa: {mensilita}")

    comune = addizionali.trova_comune(codice_comune)
    if comune is None:
        raise KeyError(f"Comune non presente nei dati: {codice_comune!r}")

    # 1-3. dalla RAL all'imponibile fiscale
    imponibile_previdenziale = ral
    contributi = inps.contributi_inps(imponibile_previdenziale)
    reddito_post_contributi = ral - contributi
    regime = regimi_agevolati.applica(ral, contributi, regime_fiscale)
    imponibile_fiscale = regime["imponibile_fiscale"]

    # 4-6. IRPEF nazionale e misure strutturali sul cuneo
    irpef_lorda = irpef.irpef_lorda(imponibile_fiscale)
    detrazione = detrazioni.detrazione_lavoro_dipendente(imponibile_fiscale)
    # Per carichi familiari e misure sul cuneo la quota esclusa dai regimi speciali deve essere
    # riaggiunta al reddito di riferimento; l'IRPEF resta invece calcolata sulla base agevolata.
    reddito_riferimento_agevolazioni = reddito_post_contributi
    situazione_familiare = familiari.calcola_familiari(
        reddito_riferimento_agevolazioni, coniuge, figli
    )
    detrazione_coniuge = situazione_familiare["detrazione_coniuge"]
    detrazione_figli = situazione_familiare["detrazione_figli"]
    detrazione_cuneo = cuneo.detrazione_aggiuntiva(reddito_riferimento_agevolazioni)
    # Le quote effettivamente usate vengono conservate separatamente per spiegare il passaggio
    # dall'IRPEF lorda alla netta senza mostrare detrazioni incapienti come denaro ricevuto.
    detrazione_applicata = min(irpef_lorda, detrazione)
    residuo_irpef = irpef_lorda - detrazione_applicata
    detrazione_coniuge_applicata = min(residuo_irpef, detrazione_coniuge)
    residuo_irpef -= detrazione_coniuge_applicata
    detrazione_figli_applicata = min(residuo_irpef, detrazione_figli)
    residuo_irpef -= detrazione_figli_applicata
    detrazione_cuneo_applicata = min(residuo_irpef, detrazione_cuneo)
    irpef_netta = residuo_irpef - detrazione_cuneo_applicata

    # 7-8. addizionali locali
    add_regionale = addizionali.addizionale_regionale(imponibile_fiscale, comune["regione_key"])
    add_comunale = addizionali.addizionale_comunale(imponibile_fiscale, comune)

    # 9. somma erogata in busta paga, non un'imposta
    integrativo = trattamento_integrativo.trattamento_integrativo(
        imponibile_fiscale,
        irpef_lorda,
        detrazione,
        detrazione_coniuge + detrazione_figli,
        reddito_riferimento_agevolazioni,
    )
    somma_cuneo = cuneo.somma_esente(reddito_riferimento_agevolazioni)

    # 10-11. netto
    netto_annuo = (
        reddito_post_contributi - irpef_netta - add_regionale - add_comunale + integrativo + somma_cuneo
    )
    netto_mensile = netto_annuo / mensilita

    # 12. accantonamento, fuori dal netto
    tfr_annuo = tfr.tfr_maturato(ral)

    regione = addizionali.trova_regione(comune["regione_key"])
    modalita_regionale = regione["modalita"] if regione else None

    return {
        "input": {
            "ral": round(ral, 2),
            "mensilita": mensilita,
            "comune": {
                "codice": comune["codice"],
                "nome": comune["nome"],
                "provincia": comune["provincia"],
                "regione": comune["regione"],
            },
        },
        "aliquote": {
            "inps": inps.ALIQUOTA_INPS_DIPENDENTE,
            "comunale": comune.get("aliquota"),
            "regionale_modalita": modalita_regionale,
        },
        "dettaglio": {
            "imponibile_previdenziale": round(imponibile_previdenziale, 2),
            "contributi_inps": round(contributi, 2),
            "reddito_post_contributi": round(reddito_post_contributi, 2),
            "quota_reddito_esente": round(regime["quota_esente"], 2),
            "imponibile_fiscale": round(imponibile_fiscale, 2),
            "irpef_lorda": round(irpef_lorda, 2),
            "detrazione_lavoro_dipendente": round(detrazione, 2),
            "detrazione_lavoro_applicata": round(detrazione_applicata, 2),
            "detrazione_coniuge": round(detrazione_coniuge, 2),
            "detrazione_coniuge_applicata": round(detrazione_coniuge_applicata, 2),
            "detrazione_figli": round(detrazione_figli, 2),
            "detrazione_figli_applicata": round(detrazione_figli_applicata, 2),
            "detrazione_cuneo": round(detrazione_cuneo, 2),
            "detrazione_cuneo_applicata": round(detrazione_cuneo_applicata, 2),
            "irpef_netta": round(irpef_netta, 2),
            "addizionale_regionale": round(add_regionale, 2),
            "addizionale_comunale": round(add_comunale, 2),
            "trattamento_integrativo": round(integrativo, 2),
            "somma_cuneo": round(somma_cuneo, 2),
        },
        "risultato": {
            "netto_annuo": round(netto_annuo, 2),
            "netto_mensile": round(netto_mensile, 2),
            "tfr_annuo": round(tfr_annuo, 2),
        },
        "fonti_dati": {
            "anno_fiscale": 2026,
            "comunale_anno": comune["fonte_anno"],
            "comunale_stato": comune["stato"],
            "comunale_esenzione": comune.get("esenzione", 0),
            "comunale_modalita": comune["modalita"],
        },
        "familiari": situazione_familiare,
        "regime_fiscale": {
            **regime,
            "quota_esente": round(regime["quota_esente"], 2),
            "imponibile_fiscale": round(regime["imponibile_fiscale"], 2),
        },
        # Voci gia' pronte per il waterfall: il frontend le disegna senza ricalcolare nulla.
        "waterfall": [
            {"etichetta": "RAL", "importo": round(ral, 2), "tipo": "inizio"},
            {"etichetta": "Contributi INPS", "importo": round(-contributi, 2), "tipo": "sottrazione"},
            {"etichetta": "IRPEF lorda", "importo": round(-irpef_lorda, 2), "tipo": "sottrazione"},
            {"etichetta": "Detrazione lavoro", "importo": round(detrazione_applicata, 2), "tipo": "aggiunta"},
            {"etichetta": "Detrazione coniuge", "importo": round(detrazione_coniuge_applicata, 2), "tipo": "aggiunta"},
            {"etichetta": "Detrazione figli", "importo": round(detrazione_figli_applicata, 2), "tipo": "aggiunta"},
            {"etichetta": "Detrazione cuneo", "importo": round(detrazione_cuneo_applicata, 2), "tipo": "aggiunta"},
            {"etichetta": "Addizionale regionale", "importo": round(-add_regionale, 2), "tipo": "sottrazione"},
            {"etichetta": "Addizionale comunale", "importo": round(-add_comunale, 2), "tipo": "sottrazione"},
            {"etichetta": "Trattamento integrativo", "importo": round(integrativo, 2), "tipo": "aggiunta"},
            {"etichetta": "Somma esente cuneo", "importo": round(somma_cuneo, 2), "tipo": "aggiunta"},
            {"etichetta": "Netto annuo", "importo": round(netto_annuo, 2), "tipo": "fine"},
        ],
    }
