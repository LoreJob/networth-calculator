"""Orchestratore: compone i moduli di calcolo in un unico risultato.

Unico punto in cui i passaggi vengono messi in sequenza. Le funzioni chiamate restano pure e
testabili una per una; qui si definisce solo l'ordine e la forma del risultato.
"""

from __future__ import annotations

from calc import addizionali, detrazioni, inps, irpef, tfr, trattamento_integrativo

MENSILITA_AMMESSE = (12, 13, 14)
MENSILITA_DEFAULT = 13


def calcola(ral: float, codice_comune: str, mensilita: int = MENSILITA_DEFAULT) -> dict:
    """Proiezione del netto annuo e mensile a partire dalla RAL.

    Ordine dei passaggi:
      1.  imponibile previdenziale = RAL
      2.  contributi INPS a carico del dipendente
      3.  imponibile fiscale = RAL - contributi INPS
      4.  IRPEF lorda progressiva sull'imponibile fiscale
      5.  detrazione da lavoro dipendente (+ eventuale bonus comma 1-bis)
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
    if ral <= 0:
        raise ValueError("La RAL deve essere positiva")
    if mensilita not in MENSILITA_AMMESSE:
        raise ValueError(f"Mensilita' non ammessa: {mensilita}")

    comune = addizionali.trova_comune(codice_comune)
    if comune is None:
        raise KeyError(f"Comune non presente nei dati: {codice_comune!r}")

    # 1-3. dalla RAL all'imponibile fiscale
    imponibile_previdenziale = ral
    contributi = inps.contributi_inps(imponibile_previdenziale)
    imponibile_fiscale = ral - contributi

    # 4-6. IRPEF nazionale
    irpef_lorda = irpef.irpef_lorda(imponibile_fiscale)
    detrazione = detrazioni.detrazione_lavoro_dipendente(imponibile_fiscale)
    irpef_netta = max(0.0, irpef_lorda - detrazione)

    # 7-8. addizionali locali
    add_regionale = addizionali.addizionale_regionale(imponibile_fiscale, comune["regione_key"])
    add_comunale = addizionali.addizionale_comunale(imponibile_fiscale, comune["aliquota"])

    # 9. somma erogata in busta paga, non un'imposta
    integrativo = trattamento_integrativo.trattamento_integrativo(imponibile_fiscale)

    # 10-11. netto
    netto_annuo = imponibile_fiscale - irpef_netta - add_regionale - add_comunale + integrativo
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
            "comunale": comune["aliquota"],
            "regionale_modalita": modalita_regionale,
        },
        "dettaglio": {
            "imponibile_previdenziale": round(imponibile_previdenziale, 2),
            "contributi_inps": round(contributi, 2),
            "imponibile_fiscale": round(imponibile_fiscale, 2),
            "irpef_lorda": round(irpef_lorda, 2),
            "detrazione_lavoro_dipendente": round(detrazione, 2),
            "irpef_netta": round(irpef_netta, 2),
            "addizionale_regionale": round(add_regionale, 2),
            "addizionale_comunale": round(add_comunale, 2),
            "trattamento_integrativo": round(integrativo, 2),
        },
        "risultato": {
            "netto_annuo": round(netto_annuo, 2),
            "netto_mensile": round(netto_mensile, 2),
            "tfr_annuo": round(tfr_annuo, 2),
        },
        # Voci gia' pronte per il waterfall: il frontend le disegna senza ricalcolare nulla.
        "waterfall": [
            {"etichetta": "RAL", "importo": round(ral, 2), "tipo": "inizio"},
            {"etichetta": "Contributi INPS", "importo": round(-contributi, 2), "tipo": "sottrazione"},
            {"etichetta": "IRPEF netta", "importo": round(-irpef_netta, 2), "tipo": "sottrazione"},
            {"etichetta": "Addizionale regionale", "importo": round(-add_regionale, 2), "tipo": "sottrazione"},
            {"etichetta": "Addizionale comunale", "importo": round(-add_comunale, 2), "tipo": "sottrazione"},
            {"etichetta": "Trattamento integrativo", "importo": round(integrativo, 2), "tipo": "aggiunta"},
            {"etichetta": "Netto annuo", "importo": round(netto_annuo, 2), "tipo": "fine"},
        ],
    }
