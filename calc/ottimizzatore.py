"""Confronto di strategie retributive a parita' di budget aziendale."""

from __future__ import annotations

from calc.costo_azienda import costo_retribuzione, ral_per_budget
from calc.pipeline import calcola

FRINGE_STANDARD = 1_000.0
FRINGE_CON_FIGLI = 2_000.0
BUONO_PASTO_ELETTRONICO_GIORNALIERO = 10.0


def _r2(valore: float) -> float:
    return round(valore, 2)


def _allocazione_benefit(
    budget: float,
    figli_a_carico: bool,
    fringe_usati: float,
    buono_pasto_attuale: float,
    giorni_lavorativi: int,
    spese_welfare: float,
) -> tuple[list[dict], float]:
    residuo = budget
    voci = []

    plafond = FRINGE_CON_FIGLI if figli_a_carico else FRINGE_STANDARD
    disponibile_fringe = max(0.0, plafond - fringe_usati)
    fringe = min(residuo, disponibile_fringe)
    if fringe:
        voci.append({"tipo": "fringe", "etichetta": "Fringe benefit", "importo": fringe})
        residuo -= fringe

    disponibile_pasti = max(
        0.0, (BUONO_PASTO_ELETTRONICO_GIORNALIERO - buono_pasto_attuale) * giorni_lavorativi
    )
    pasti = min(residuo, disponibile_pasti)
    if pasti:
        voci.append({"tipo": "buoni_pasto", "etichetta": "Buoni pasto elettronici", "importo": pasti})
        residuo -= pasti

    welfare = min(residuo, max(0.0, spese_welfare))
    if welfare:
        voci.append({"tipo": "welfare", "etichetta": "Welfare familiare", "importo": welfare})
        residuo -= welfare

    return voci, residuo


def _scenario(
    codice: str,
    nome: str,
    budget: float,
    incremento_ral: float,
    incremento_netto: float,
    benefit: list[dict],
    non_allocato: float = 0.0,
) -> dict:
    valore_benefit = sum(v["importo"] for v in benefit)
    valore = incremento_netto + valore_benefit
    speso = budget - non_allocato
    return {
        "codice": codice,
        "nome": nome,
        "budget": _r2(budget),
        "costo_allocato": _r2(speso),
        "non_allocato": _r2(non_allocato),
        "incremento_ral": _r2(incremento_ral),
        "netto_cash": _r2(incremento_netto),
        "valore_benefit": _r2(valore_benefit),
        "valore_totale": _r2(valore),
        "efficienza": round(valore / speso, 4) if speso else 0.0,
        "benefit": [{**v, "importo": _r2(v["importo"])} for v in benefit],
    }


def _costo_aumento_per_netto(
    target_netto: float,
    ral: float,
    codice_comune: str,
    mensilita: int,
    aliquota_datore: float,
    aliquota_inail: float,
    netto_attuale: float,
) -> float:
    """Costo aziendale necessario per generare lo stesso valore tramite sola RAL."""
    basso, alto = 0.0, max(1_000.0, target_netto * 3)

    def incremento(costo: float) -> float:
        delta = ral_per_budget(costo, aliquota_datore, aliquota_inail)
        nuovo = calcola(ral + delta, codice_comune, mensilita)["risultato"]["netto_annuo"]
        return nuovo - netto_attuale

    while incremento(alto) < target_netto and alto < 10_000_000:
        alto *= 2
    for _ in range(45):
        medio = (basso + alto) / 2
        if incremento(medio) < target_netto:
            basso = medio
        else:
            alto = medio
    return alto


def _composizione_dipendente(fiscale: dict, benefit: float = 0.0) -> dict:
    """Voci che distribuiscono le risorse lorde tra trattenute e valore ricevuto."""
    dettaglio = fiscale["dettaglio"]
    netto = fiscale["risultato"]["netto_annuo"]
    addizionali = dettaglio["addizionale_regionale"] + dettaglio["addizionale_comunale"]
    totale_flusso = (
        netto + dettaglio["contributi_inps"] + dettaglio["irpef_netta"] + addizionali + benefit
    )
    return {
        "ral": fiscale["input"]["ral"],
        "netto_cash": netto,
        "contributi_dipendente": dettaglio["contributi_inps"],
        "irpef_netta": dettaglio["irpef_netta"],
        "addizionali": addizionali,
        "benefit": benefit,
        "valore_totale": netto + benefit,
        "totale_flusso": totale_flusso,
    }


def confronta(
    *,
    ral: float,
    codice_comune: str,
    mensilita: int,
    budget: float,
    figli_a_carico: bool,
    fringe_usati: float,
    buono_pasto_attuale: float,
    welfare_attuale: float,
    giorni_lavorativi: int,
    spese_welfare: float,
    aliquota_datore: float,
    aliquota_inail: float,
) -> dict:
    """Restituisce baseline aziendale, scenari puri e mix suggerito."""
    if budget <= 0:
        raise ValueError("Il budget aziendale deve essere maggiore di zero")
    if not 0 <= aliquota_datore <= 1 or not 0 <= aliquota_inail <= 0.2:
        raise ValueError("Le aliquote aziendali non sono plausibili")
    if not 0 <= giorni_lavorativi <= 366:
        raise ValueError("I giorni lavorativi devono essere tra 0 e 366")
    if min(fringe_usati, buono_pasto_attuale, welfare_attuale, spese_welfare) < 0:
        raise ValueError("Gli importi dei benefit non possono essere negativi")

    situazione = calcola(ral, codice_comune, mensilita)
    costo = costo_retribuzione(ral, aliquota_datore, aliquota_inail)
    benefit_attuali = fringe_usati + buono_pasto_attuale * giorni_lavorativi + welfare_attuale

    incremento_ral_puro = ral_per_budget(budget, aliquota_datore, aliquota_inail)
    nuovo_puro = calcola(ral + incremento_ral_puro, codice_comune, mensilita)
    netto_puro = nuovo_puro["risultato"]["netto_annuo"] - situazione["risultato"]["netto_annuo"]
    aumento = _scenario(
        "aumento", "Solo aumento RAL", budget, incremento_ral_puro, netto_puro, []
    )

    benefit, residuo = _allocazione_benefit(
        budget, figli_a_carico, fringe_usati, buono_pasto_attuale,
        giorni_lavorativi, spese_welfare,
    )
    solo_benefit = _scenario(
        "benefit", "Solo benefit eleggibili", budget, 0.0, 0.0, benefit, residuo
    )

    incremento_ral_mix = ral_per_budget(residuo, aliquota_datore, aliquota_inail)
    nuovo_mix = calcola(ral + incremento_ral_mix, codice_comune, mensilita)
    netto_mix = nuovo_mix["risultato"]["netto_annuo"] - situazione["risultato"]["netto_annuo"]
    mix = _scenario("mix", "Mix ottimizzato", budget, incremento_ral_mix, netto_mix, benefit)

    scenari = [aumento, solo_benefit, mix]
    migliore = max(scenari, key=lambda s: (s["valore_totale"], s["costo_allocato"]))
    if migliore["codice"] == "aumento":
        delta_ral_scelto = incremento_ral_puro
        benefit_scelti = 0.0
        situazione_dopo = nuovo_puro
    elif migliore["codice"] == "benefit":
        delta_ral_scelto = 0.0
        benefit_scelti = sum(voce["importo"] for voce in benefit)
        situazione_dopo = situazione
    else:
        delta_ral_scelto = incremento_ral_mix
        benefit_scelti = sum(voce["importo"] for voce in benefit)
        situazione_dopo = nuovo_mix

    costo_dopo_retribuzione = costo_retribuzione(
        ral + delta_ral_scelto, aliquota_datore, aliquota_inail
    )
    costo_attuale_totale = costo["totale"] + benefit_attuali
    costo_dopo_totale = costo_dopo_retribuzione["totale"] + benefit_attuali + benefit_scelti
    incremento_costo = costo_dopo_totale - costo_attuale_totale
    dipendente_attuale = _composizione_dipendente(situazione, benefit_attuali)
    dipendente_dopo = _composizione_dipendente(
        situazione_dopo, benefit_attuali + benefit_scelti
    )
    incremento_valore_dipendente = (
        dipendente_dopo["valore_totale"] - dipendente_attuale["valore_totale"]
    )
    incremento_netto_cash = dipendente_dopo["netto_cash"] - dipendente_attuale["netto_cash"]
    costo_equivalente = _costo_aumento_per_netto(
        migliore["valore_totale"], ral, codice_comune, mensilita, aliquota_datore,
        aliquota_inail, situazione["risultato"]["netto_annuo"],
    )
    if migliore["codice"] == "aumento":
        nota = "Non risultano plafond benefit utilizzabili: il budget viene convertito in aumento RAL."
    else:
        nota = (
            "Massimizza il valore usando solo plafond e spese dichiarate; "
            "i benefit non equivalgono a liquidita' libera."
        )

    return {
        "input": {
            "budget": _r2(budget),
            "figli_a_carico": figli_a_carico,
            "benefit_attuali": _r2(benefit_attuali),
            "aliquota_datore": aliquota_datore,
            "aliquota_inail": aliquota_inail,
        },
        "baseline": {
            "netto_annuo": situazione["risultato"]["netto_annuo"],
            "netto_mensile": situazione["risultato"]["netto_mensile"],
            "costo_azienda": {
                **{chiave: _r2(valore) for chiave, valore in costo.items()},
                "benefit": _r2(benefit_attuali),
                "totale": _r2(costo_attuale_totale),
            },
            "dettaglio_fiscale": situazione,
        },
        "scenari": scenari,
        "confronto_costi": {
            "attuale": {
                "ral": _r2(costo["ral"]),
                "contributi_datore": _r2(costo["contributi_datore"]),
                "inail": _r2(costo["inail"]),
                "tfr": _r2(costo["tfr"]),
                "benefit": _r2(benefit_attuali),
                "totale": _r2(costo_attuale_totale),
            },
            "dopo_budget": {
                "ral": _r2(costo_dopo_retribuzione["ral"]),
                "contributi_datore": _r2(costo_dopo_retribuzione["contributi_datore"]),
                "inail": _r2(costo_dopo_retribuzione["inail"]),
                "tfr": _r2(costo_dopo_retribuzione["tfr"]),
                "benefit": _r2(benefit_attuali + benefit_scelti),
                "totale": _r2(costo_dopo_totale),
            },
            "incremento": _r2(incremento_costo),
            "incremento_percentuale": round(
                incremento_costo / costo_attuale_totale, 6
            ) if costo_attuale_totale else 0.0,
        },
        "confronto_dipendente": {
            "attuale": {chiave: _r2(valore) for chiave, valore in dipendente_attuale.items()},
            "dopo_budget": {chiave: _r2(valore) for chiave, valore in dipendente_dopo.items()},
            "incremento_valore": _r2(incremento_valore_dipendente),
            "incremento_netto_cash": _r2(incremento_netto_cash),
            "incremento_netto_mensile": _r2(incremento_netto_cash / mensilita),
            "incremento_percentuale": round(
                incremento_valore_dipendente / dipendente_attuale["valore_totale"], 6
            ) if dipendente_attuale["valore_totale"] else 0.0,
        },
        "raccomandazione": {
            "codice": migliore["codice"],
            "titolo": migliore["nome"],
            "vantaggio_vs_aumento": _r2(migliore["valore_totale"] - aumento["valore_totale"]),
            "costo_aumento_equivalente": _r2(costo_equivalente),
            "costo_evitato": _r2(max(0.0, costo_equivalente - budget)),
            "nota": nota,
        },
        "regole": {
            "anno": 2026,
            "plafond_fringe": FRINGE_CON_FIGLI if figli_a_carico else FRINGE_STANDARD,
            "buono_pasto_giornaliero": BUONO_PASTO_ELETTRONICO_GIORNALIERO,
        },
    }
