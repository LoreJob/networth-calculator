"""Regressioni fiscali e invarianti del motore di cost saving."""

from __future__ import annotations

import pytest

from app import app
from calc import addizionali, cuneo, familiari, irpef, trattamento_integrativo
from calc.costo_azienda import costo_retribuzione, ral_per_budget
from calc.ottimizzatore import confronta
from calc.pipeline import calcola

MILANO = "F205"


@pytest.mark.parametrize("ral", [10_000, 20_000, 25_000, 35_000, 50_000, 70_000])
def test_pipeline_restituisce_valori_finiti_e_positivi(ral):
    risultato = calcola(ral, MILANO, 13)
    assert risultato["risultato"]["netto_annuo"] > 0
    assert risultato["risultato"]["netto_mensile"] > 0
    dettaglio = risultato["dettaglio"]
    assert (
        dettaglio["irpef_lorda"]
        - dettaglio["detrazione_lavoro_applicata"]
        - dettaglio["detrazione_coniuge_applicata"]
        - dettaglio["detrazione_figli_applicata"]
        - dettaglio["detrazione_cuneo_applicata"]
    ) == pytest.approx(dettaglio["irpef_netta"], abs=0.02)
    waterfall = risultato["waterfall"]
    assert waterfall[0]["importo"] + sum(v["importo"] for v in waterfall[1:-1]) == pytest.approx(
        waterfall[-1]["importo"], abs=0.03
    )


def test_waterfall_mostra_la_detrazione_cuneo_quando_spetta():
    risultato = calcola(35_000, MILANO, 13)
    voce = next(v for v in risultato["waterfall"] if v["etichetta"] == "Detrazione cuneo")
    assert voce["importo"] == 1_000


def test_irpef_2026_progressiva():
    assert irpef.irpef_lorda(28_000) == pytest.approx(6_440)
    assert irpef.irpef_lorda(35_000) == pytest.approx(6_440 + 7_000 * 0.33)
    assert irpef.irpef_lorda(60_000) == pytest.approx(6_440 + 22_000 * 0.33 + 10_000 * 0.43)


def test_cuneo_strutturale_alle_soglie():
    assert cuneo.somma_esente(8_000) == pytest.approx(568)
    assert cuneo.somma_esente(10_000) == pytest.approx(530)
    assert cuneo.somma_esente(18_000) == pytest.approx(864)
    assert cuneo.somma_esente(20_001) == 0
    assert cuneo.detrazione_aggiuntiva(25_000) == 1_000
    assert cuneo.detrazione_aggiuntiva(36_000) == 500
    assert cuneo.detrazione_aggiuntiva(40_000) == 0


def test_trattamento_integrativo_verifica_capienza():
    assert trattamento_integrativo.trattamento_integrativo(14_000, 3_220, 1_955) == 1_200
    assert trattamento_integrativo.trattamento_integrativo(8_000, 1_840, 1_955) == 0
    assert trattamento_integrativo.trattamento_integrativo(20_000, 4_600, 5_100) == 500
    assert trattamento_integrativo.trattamento_integrativo(20_000, 4_600, 3_000) == 0


def test_coniuge_a_carico_genera_detrazione_personale():
    risultato = familiari.calcola_familiari(
        31_000, {"presente": True, "reddito": 0, "mesi_carico": 12}, []
    )
    assert risultato["coniuge"]["a_carico"] is True
    assert risultato["detrazione_coniuge"] == 710
    oltre_soglia = familiari.calcola_familiari(
        31_000, {"presente": True, "reddito": 2_841, "mesi_carico": 12}, []
    )
    assert oltre_soglia["detrazione_coniuge"] == 0


def test_eta_figli_determina_i_mesi_di_detrazione_2026():
    profilo = familiari.calcola_familiari(35_000, None, [
        {"data_nascita": "2005-08-10", "reddito": 0, "mesi_carico": 12, "quota_detrazione": 1},
        {"data_nascita": "1996-08-10", "reddito": 0, "mesi_carico": 12, "quota_detrazione": 1},
        {"data_nascita": "1990-01-10", "reddito": 0, "mesi_carico": 12, "quota_detrazione": 1, "disabile": True},
        {"data_nascita": "2010-01-10", "reddito": 0, "mesi_carico": 12, "quota_detrazione": 1},
    ])
    assert [figlio["mesi_detrazione"] for figlio in profilo["figli"]] == [5, 7, 12, 0]
    assert profilo["numero_figli_a_carico"] == 4


def test_detrazioni_familiari_aumentano_il_netto_senza_superare_irpef():
    coniuge = {"presente": True, "reddito": 0, "mesi_carico": 12}
    figli = [{
        "data_nascita": "2003-01-10", "reddito": 0, "mesi_carico": 12,
        "quota_detrazione": 1,
    }]
    senza = calcola(35_000, MILANO, 13)
    con = calcola(35_000, MILANO, 13, coniuge, figli)
    assert con["risultato"]["netto_annuo"] > senza["risultato"]["netto_annuo"]
    dettaglio = con["dettaglio"]
    detrazioni_applicate = sum(dettaglio[chiave] for chiave in (
        "detrazione_lavoro_applicata", "detrazione_coniuge_applicata",
        "detrazione_figli_applicata", "detrazione_cuneo_applicata",
    ))
    assert detrazioni_applicate <= dettaglio["irpef_lorda"]


def test_milano_usa_delibera_ufficiale_con_esenzione():
    comune = addizionali.trova_comune(MILANO)
    assert comune["aliquota"] == pytest.approx(0.008)
    assert comune["esenzione"] == 23_000
    assert comune["stato"] == "fallback_2025"
    assert addizionali.addizionale_comunale(23_000, comune) == 0
    assert addizionali.addizionale_comunale(23_001, comune) == pytest.approx(184.008)


def test_costo_azienda_si_ricompone():
    costo = costo_retribuzione(35_000, 0.30, 0.004)
    assert costo["totale"] == pytest.approx(
        costo["ral"] + costo["contributi_datore"] + costo["inail"] + costo["tfr"]
    )
    assert ral_per_budget(costo["totale"], 0.30, 0.004) == pytest.approx(35_000)


def ottimizzazione(**override):
    input_base = dict(
        ral=35_000,
        codice_comune=MILANO,
        mensilita=13,
        budget=5_000,
        coniuge=None,
        figli=[{
            "data_nascita": "2010-01-01", "reddito": 0, "mesi_carico": 12,
            "quota_detrazione": 0.5,
        }],
        regime_fiscale=None,
        fringe_usati=0,
        buono_pasto_attuale=0,
        welfare_attuale=0,
        giorni_lavorativi=220,
        spese_welfare=1_500,
        aliquota_datore=0.30,
        aliquota_inail=0.004,
    )
    input_base.update(override)
    return confronta(**input_base)


def test_scenari_rispettano_il_budget():
    risultato = ottimizzazione()
    for scenario in risultato["scenari"]:
        assert scenario["costo_allocato"] + scenario["non_allocato"] == pytest.approx(5_000)
        assert scenario["costo_allocato"] <= 5_000
    assert risultato["raccomandazione"]["costo_aumento_equivalente"] >= 5_000
    assert risultato["raccomandazione"]["costo_evitato"] >= 0
    confronto = risultato["confronto_costi"]
    assert confronto["dopo_budget"]["totale"] - confronto["attuale"]["totale"] == pytest.approx(
        5_000, abs=0.02
    )
    for situazione in (confronto["attuale"], confronto["dopo_budget"]):
        somma = sum(situazione[c] for c in ("ral", "contributi_datore", "inail", "tfr", "benefit"))
        assert somma == pytest.approx(situazione["totale"], abs=0.02)
    assert confronto["incremento_percentuale"] == pytest.approx(
        confronto["incremento"] / confronto["attuale"]["totale"], abs=1e-5
    )
    dipendente = risultato["confronto_dipendente"]
    for situazione in (dipendente["attuale"], dipendente["dopo_budget"]):
        flusso = sum(situazione[c] for c in (
            "netto_cash", "contributi_dipendente", "irpef_netta", "addizionali", "benefit"
        ))
        assert flusso == pytest.approx(situazione["totale_flusso"], abs=0.02)
        assert situazione["netto_cash"] + situazione["benefit"] == pytest.approx(
            situazione["valore_totale"], abs=0.02
        )
    assert dipendente["dopo_budget"]["valore_totale"] - dipendente["attuale"]["valore_totale"] == pytest.approx(
        dipendente["incremento_valore"], abs=0.02
    )
    assert dipendente["incremento_netto_mensile"] == pytest.approx(
        dipendente["incremento_netto_cash"] / 13, abs=0.01
    )


def test_benefit_attuali_entrano_in_entrambe_le_baseline():
    risultato = ottimizzazione(
        fringe_usati=500, buono_pasto_attuale=8, welfare_attuale=600,
        giorni_lavorativi=200,
    )
    benefit_attuali = 500 + 8 * 200 + 600
    costi = risultato["confronto_costi"]
    dipendente = risultato["confronto_dipendente"]
    assert risultato["input"]["benefit_attuali"] == benefit_attuali
    assert costi["attuale"]["benefit"] == benefit_attuali
    assert dipendente["attuale"]["benefit"] == benefit_attuali
    assert costi["dopo_budget"]["benefit"] >= benefit_attuali
    assert dipendente["dopo_budget"]["benefit"] >= benefit_attuali
    assert costi["dopo_budget"]["totale"] - costi["attuale"]["totale"] == pytest.approx(
        5_000, abs=0.02
    )


def test_figli_a_carico_alzano_solo_il_plafond_fringe():
    con_figli = ottimizzazione()["scenari"][1]
    senza_figli = ottimizzazione(figli=[])["scenari"][1]
    fringe_con = next(v for v in con_figli["benefit"] if v["tipo"] == "fringe")
    fringe_senza = next(v for v in senza_figli["benefit"] if v["tipo"] == "fringe")
    assert fringe_con["importo"] == 2_000
    assert fringe_senza["importo"] == 1_000


def test_mix_destina_il_residuo_alla_ral():
    risultato = ottimizzazione(
        figli=[], buono_pasto_attuale=10, spese_welfare=0, budget=5_000
    )
    mix = next(s for s in risultato["scenari"] if s["codice"] == "mix")
    assert mix["valore_benefit"] == 1_000
    assert mix["incremento_ral"] > 0
    assert mix["costo_allocato"] == 5_000
    assert risultato["confronto_dipendente"]["incremento_netto_mensile"] > 0


def test_api_ottimizzazione():
    with app.test_client() as client:
        pagina = client.get("/")
        risposta = client.post("/api/ottimizza", json={
            "ral": 35_000, "comune": MILANO, "mensilita": 13, "budget": 5_000,
            "coniuge": {"presente": True, "reddito": 0, "mesi_carico": 12},
            "figli": [{"data_nascita": "2010-01-01", "reddito": 0,
                       "mesi_carico": 12, "quota_detrazione": 0.5}],
            "fringe_usati": 0, "buono_pasto_attuale": 0,
            "welfare_attuale": 0, "giorni_lavorativi": 220, "spese_welfare": 1_500,
            "aliquota_datore": 0.30, "aliquota_inail": 0.004,
        })
    html = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    assert 'id="vista-azienda"' in html
    assert 'id="vista-dipendente"' in html
    assert 'id="costo-stack"' in html
    assert 'id="grafico-confronto-costi"' in html
    assert 'id="grafico-confronto-dipendente"' in html
    assert 'id="aggiungi-figlio"' in html
    assert risposta.status_code == 200
    assert len(risposta.get_json()["scenari"]) == 3


def test_impatriati_riduce_il_reddito_imponibile_e_aumenta_il_netto():
    ordinario = calcola(50_000, MILANO, 13)
    agevolato = calcola(50_000, MILANO, 13, regime_fiscale={
        "tipo": "impatriati_2024", "anno_inizio": 2024, "requisiti_attestati": True,
    })
    assert agevolato["regime_fiscale"]["quota_imponibile"] == 0.50
    reddito_lavoro = 50_000 - agevolato["dettaglio"]["contributi_inps"]
    assert agevolato["dettaglio"]["quota_reddito_esente"] == pytest.approx(
        reddito_lavoro * 0.50
    )
    assert agevolato["dettaglio"]["imponibile_fiscale"] == pytest.approx(reddito_lavoro * 0.50)
    assert agevolato["risultato"]["netto_annuo"] > ordinario["risultato"]["netto_annuo"]


def test_impatriati_applica_limite_e_non_modifica_costo_previdenziale():
    risultato = calcola(700_000, MILANO, 13, regime_fiscale={
        "tipo": "impatriati_2024", "anno_inizio": 2025, "requisiti_attestati": True,
    })
    assert risultato["dettaglio"]["quota_reddito_esente"] == pytest.approx(300_000)
    assert risultato["dettaglio"]["imponibile_previdenziale"] == 700_000


def test_regime_agevolato_richiede_requisiti_e_periodo_attivo():
    with pytest.raises(ValueError, match="requisiti"):
        calcola(50_000, MILANO, 13, regime_fiscale={
            "tipo": "impatriati_2024", "anno_inizio": 2024,
        })
    with pytest.raises(ValueError, match="non e' attivo"):
        calcola(50_000, MILANO, 13, regime_fiscale={
            "tipo": "impatriati_2024", "anno_inizio": 2030, "requisiti_attestati": True,
        })
