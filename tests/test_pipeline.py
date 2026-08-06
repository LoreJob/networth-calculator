"""Test della pipeline di calcolo su casi noti.

I valori attesi non sono presi da un simulatore esterno: sono le proprieta' che il calcolo deve
rispettare (progressivita', coerenza annuo/mensile, effetto della regione) piu' alcuni importi
ricalcolati a mano dalle formule di legge.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calc import addizionali, detrazioni, irpef, trattamento_integrativo  # noqa: E402
from calc.inps import ALIQUOTA_INPS_DIPENDENTE  # noqa: E402
from calc.pipeline import calcola  # noqa: E402

MILANO = "F205"
ROMA = "H501"
RAL_DI_PROVA = [20_000, 25_000, 35_000, 50_000, 70_000]


# --- pipeline completa ---------------------------------------------------------------------------


@pytest.mark.parametrize("ral", RAL_DI_PROVA)
def test_netto_compreso_tra_zero_e_ral(ral):
    """Il netto percepito e' sempre positivo e sempre inferiore alla RAL."""
    risultato = calcola(ral, MILANO, 13)
    netto = risultato["risultato"]["netto_annuo"]
    assert 0 < netto < ral


@pytest.mark.parametrize("ral", RAL_DI_PROVA)
def test_netto_mensile_coerente_con_annuo(ral):
    """netto mensile x mensilita' deve ridare il netto annuo, a meno degli arrotondamenti.

    Il mensile e' arrotondato al centesimo, quindi l'errore ammesso cresce con le mensilita':
    al massimo mezzo centesimo per rata.
    """
    for mensilita in (12, 13, 14):
        risultato = calcola(ral, MILANO, mensilita)
        annuo = risultato["risultato"]["netto_annuo"]
        mensile = risultato["risultato"]["netto_mensile"]
        assert abs(mensile * mensilita - annuo) <= mensilita * 0.005 + 0.01


@pytest.mark.parametrize("ral", RAL_DI_PROVA)
def test_dettaglio_ricompone_il_netto(ral):
    """Le voci del breakdown devono sommare esattamente al netto annuo dichiarato."""
    risultato = calcola(ral, MILANO, 13)
    d = risultato["dettaglio"]
    ricomposto = (
        d["imponibile_fiscale"]
        - d["irpef_netta"]
        - d["addizionale_regionale"]
        - d["addizionale_comunale"]
        + d["trattamento_integrativo"]
    )
    assert abs(ricomposto - risultato["risultato"]["netto_annuo"]) < 0.02


@pytest.mark.parametrize("ral", RAL_DI_PROVA)
def test_waterfall_somma_al_netto(ral):
    """Il waterfall parte dalla RAL, e sommando le variazioni arriva al netto finale."""
    voci = calcola(ral, MILANO, 13)["waterfall"]
    inizio = voci[0]["importo"]
    variazioni = sum(v["importo"] for v in voci[1:-1])
    assert abs(inizio + variazioni - voci[-1]["importo"]) < 0.02


def test_netto_cresce_con_la_ral():
    """Nessuna inversione: a RAL piu' alta deve corrispondere netto piu' alto."""
    netti = [calcola(ral, MILANO, 13)["risultato"]["netto_annuo"] for ral in RAL_DI_PROVA]
    assert netti == sorted(netti)


def test_nessun_salto_discontinuo_attorno_agli_scaglioni():
    """Attorno alle soglie di scaglione l'imposta cambia pendenza, non fa salti.

    100 euro di RAL in piu' non possono cambiare il netto di piu' di 100 euro: se accadesse,
    vorrebbe dire che l'aliquota dello scaglione superiore e' stata applicata all'intero
    reddito invece che alla sola quota eccedente.
    """
    for soglia in (28_000, 50_000):
        # Le soglie sono sull'imponibile fiscale: risaliamo alla RAL corrispondente.
        ral_soglia = soglia / (1 - ALIQUOTA_INPS_DIPENDENTE)
        prima = calcola(ral_soglia - 50, MILANO, 13)["risultato"]["netto_annuo"]
        dopo = calcola(ral_soglia + 50, MILANO, 13)["risultato"]["netto_annuo"]
        assert 0 <= dopo - prima <= 100


# --- effetto del comune scelto -------------------------------------------------------------------


def test_regione_derivata_dal_comune():
    """La regione non e' un input: si deriva dal comune selezionato."""
    assert calcola(35_000, MILANO, 13)["input"]["comune"]["regione"] == "Lombardia"
    assert calcola(35_000, ROMA, 13)["input"]["comune"]["regione"] == "Lazio"


def test_addizionali_diverse_tra_milano_e_roma():
    """Cambiando comune cambiano entrambe le addizionali, e quindi il netto."""
    milano = calcola(35_000, MILANO, 13)
    roma = calcola(35_000, ROMA, 13)

    assert milano["dettaglio"]["addizionale_regionale"] != roma["dettaglio"]["addizionale_regionale"]
    assert milano["dettaglio"]["addizionale_comunale"] != roma["dettaglio"]["addizionale_comunale"]
    # Il Lazio ha aliquote regionali piu' alte della Lombardia: a Roma il netto e' inferiore.
    assert roma["risultato"]["netto_annuo"] < milano["risultato"]["netto_annuo"]


def test_imponibile_fiscale_identico_indipendentemente_dal_comune():
    """Il comune tocca solo le addizionali, non contributi ne' imponibile."""
    milano = calcola(35_000, MILANO, 13)["dettaglio"]
    roma = calcola(35_000, ROMA, 13)["dettaglio"]
    assert milano["imponibile_fiscale"] == roma["imponibile_fiscale"]
    assert milano["irpef_netta"] == roma["irpef_netta"]


# --- singoli moduli ------------------------------------------------------------------------------


def test_irpef_lorda_calcolata_a_mano():
    """Verifica della progressivita' contro il calcolo manuale sugli scaglioni."""
    assert irpef.irpef_lorda(28_000) == pytest.approx(28_000 * 0.23)
    assert irpef.irpef_lorda(35_000) == pytest.approx(28_000 * 0.23 + 7_000 * 0.33)
    assert irpef.irpef_lorda(60_000) == pytest.approx(28_000 * 0.23 + 22_000 * 0.33 + 10_000 * 0.43)


def test_detrazione_rami_art_13():
    assert detrazioni.detrazione_lavoro_dipendente(14_000) == pytest.approx(1_955)
    assert detrazioni.detrazione_lavoro_dipendente(20_000) == pytest.approx(
        1_910 + 1_190 * 8_000 / 13_000
    )
    # Nella fascia 25.000-35.000 si aggiunge il bonus di 65 euro del comma 1-bis.
    assert detrazioni.detrazione_lavoro_dipendente(30_000) == pytest.approx(
        1_910 * 20_000 / 22_000 + 65
    )
    assert detrazioni.detrazione_lavoro_dipendente(55_000) == 0


def test_trattamento_integrativo_phase_out():
    assert trattamento_integrativo.trattamento_integrativo(14_000) == 1_200
    assert trattamento_integrativo.trattamento_integrativo(21_500) == pytest.approx(600)
    assert trattamento_integrativo.trattamento_integrativo(28_000) == pytest.approx(0)
    assert trattamento_integrativo.trattamento_integrativo(40_000) == 0


def test_addizionale_regionale_unica_non_e_progressiva():
    """Le regioni ad aliquota unica applicano l'aliquota all'intero imponibile."""
    veneto = addizionali.trova_regione("REGIONE VENETO")
    assert veneto["modalita"] == "unica"
    assert addizionali.addizionale_regionale(40_000, "REGIONE VENETO") == pytest.approx(
        40_000 * veneto["aliquota"]
    )


def test_addizionale_regionale_a_scaglioni_e_progressiva():
    """Le regioni a scaglioni tassano ogni fascia con la propria aliquota."""
    lombardia = addizionali.trova_regione("REGIONE LOMBARDIA")
    assert lombardia["modalita"] == "scaglioni"
    atteso = 15_000 * 0.0123 + 5_000 * 0.0158
    assert addizionali.addizionale_regionale(20_000, "REGIONE LOMBARDIA") == pytest.approx(atteso)


# --- validazione degli input ---------------------------------------------------------------------


def test_input_non_validi():
    with pytest.raises(ValueError):
        calcola(0, MILANO, 13)
    with pytest.raises(ValueError):
        calcola(30_000, MILANO, 15)
    with pytest.raises(KeyError):
        calcola(30_000, "ZZZZ", 13)


def test_comuni_omonimi_restano_distinti():
    """I cinque nomi duplicati nel dataset devono essere distinguibili per codice catastale."""
    omonimi = [c for c in addizionali.elenco_comuni() if c["nome"] == "SAN TEODORO"]
    assert len(omonimi) == 2
    assert {c["provincia"] for c in omonimi} == {"ME", "SS"}
