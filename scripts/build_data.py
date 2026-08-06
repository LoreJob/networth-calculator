"""Normalizza i due dataset MEF grezzi in JSON puliti, pronti per il lookup a runtime.

Script one-shot e idempotente: si rilancia quando cambiano i CSV di partenza.

    python scripts/build_data.py

Input  (in data/, non modificati):
  - addreg2026.csv
        MEF, aliquote dell'addizionale regionale IRPEF 2026 deliberate da regioni e province autonome.
  - Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024*.csv
        MEF, dichiarazioni aggregate per comune, anno d'imposta 2024.

Output (in data/, rigenerati):
  - regioni_addizionale_2026.json
  - comuni_addizionale_2024.json
"""

from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

# --- percorsi ------------------------------------------------------------------------------------

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DATI = os.path.join(RADICE, "data")

CSV_REGIONI = os.path.join(DIR_DATI, "addreg2026.csv")
# Il file comunale scaricato dal MEF puo' avere un suffisso " (1)" aggiunto dal browser:
# lo cerchiamo per pattern invece di fissare il nome esatto.
PATTERN_CSV_COMUNI = os.path.join(DIR_DATI, "Redditi_e_principali_variabili_IRPEF*.csv")

JSON_REGIONI = os.path.join(DIR_DATI, "regioni_addizionale_2026.json")
JSON_COMUNI = os.path.join(DIR_DATI, "comuni_addizionale_2024.json")

# I CSV MEF usano ';' come separatore e sono salvati con BOM.
SEPARATORE = ";"
ENCODING = "utf-8-sig"


# --- lettura CSV ---------------------------------------------------------------------------------


def leggi_csv(percorso: str) -> tuple[list[str], list[list[str]]]:
    """Ritorna (header ripulito, righe dati).

    L'header dei file MEF contiene spazi in coda ai nomi colonna (es. 'FASCIA ') e, nel file
    comunale, una colonna finale vuota che le righe dati non hanno: entrambi vanno normalizzati
    prima di cercare gli indici per nome.
    """
    with open(percorso, encoding=ENCODING, newline="") as f:
        righe = list(csv.reader(f, delimiter=SEPARATORE))
    header = [colonna.strip() for colonna in righe[0]]
    return header, righe[1:]


# --- addizionale regionale -----------------------------------------------------------------------

# Le fasce nel CSV sono testo libero, in tre forme:
#   "fino a 15000.00 euro"                      -> scaglione da 0 a 15.000
#   "oltre 15000.00 e fino a 28000.00 euro"     -> scaglione da 15.000 a 28.000
#   "oltre 50000.00 euro"                       -> ultimo scaglione, senza tetto
# piu' il caso speciale "Aliquota Unica", che non e' uno scaglione ma un'aliquota piatta.
RE_FINO_A = re.compile(r"^fino a\s+([\d.]+)\s+euro$", re.IGNORECASE)
RE_OLTRE_E_FINO_A = re.compile(r"^oltre\s+[\d.]+\s+e fino a\s+([\d.]+)\s+euro$", re.IGNORECASE)
RE_OLTRE = re.compile(r"^oltre\s+([\d.]+)\s+euro$", re.IGNORECASE)

# Nomi regione come compaiono nel dataset comunale -> chiave usata in addreg2026.csv.
# Il grosso si ottiene con 'REGIONE ' + maiuscolo; queste sono le eccezioni.
ECCEZIONI_NOME_REGIONE = {
    "EMILIA ROMAGNA": "REGIONE EMILIA-ROMAGNA",
    "TRENTINO ALTO ADIGE(P.A.BOLZANO)": "PROVINCIA AUTONOMA DI BOLZANO",
    "TRENTINO ALTO ADIGE(P.A.TRENTO)": "PROVINCIA AUTONOMA DI TRENTO",
}


def chiave_regione(nome_dataset_comunale: str) -> str:
    """Converte il nome regione del dataset comunale nella chiave di addreg2026.csv."""
    normalizzato = nome_dataset_comunale.upper().strip()
    if normalizzato in ECCEZIONI_NOME_REGIONE:
        return ECCEZIONI_NOME_REGIONE[normalizzato]
    return "REGIONE " + normalizzato


def limite_superiore_fascia(fascia: str) -> float | None:
    """Estrae il tetto dello scaglione descritto in `fascia`. None = scaglione senza tetto."""
    fascia = fascia.strip()
    for regex in (RE_FINO_A, RE_OLTRE_E_FINO_A):
        trovato = regex.match(fascia)
        if trovato:
            return float(trovato.group(1))
    if RE_OLTRE.match(fascia):
        return None
    raise ValueError(f"Fascia non riconosciuta: {fascia!r}")


def costruisci_regioni() -> dict:
    """Legge addreg2026.csv e produce la mappa regione -> regole dell'addizionale regionale."""
    header, righe = leggi_csv(CSV_REGIONI)
    i_regione = header.index("REGIONE")
    i_numero = header.index("NUMERO")
    i_aliquota = header.index("ALIQUOTA")
    i_fascia = header.index("FASCIA")

    # Alcune regioni (Molise, Puglia) compaiono con due delibere diverse nello stesso file.
    # Teniamo solo quella con NUMERO piu' alto, che e' anche la piu' recente per data di
    # pubblicazione: e' la delibera che sostituisce la precedente.
    numero_vigente: dict[str, int] = {}
    for riga in righe:
        regione = riga[i_regione].strip()
        numero = int(riga[i_numero])
        if numero > numero_vigente.get(regione, -1):
            numero_vigente[regione] = numero

    regioni: dict[str, dict] = {}
    for riga in righe:
        regione = riga[i_regione].strip()
        if int(riga[i_numero]) != numero_vigente[regione]:
            continue  # delibera superata

        # Le aliquote nel CSV sono in punti percentuali (1.23 = 1,23%).
        aliquota = float(riga[i_aliquota]) / 100
        fascia = riga[i_fascia].strip()

        if fascia.lower() == "aliquota unica":
            # Aliquota piatta applicata all'intero imponibile, non per scaglioni.
            regioni[regione] = {"modalita": "unica", "aliquota": aliquota}
            continue

        voce = regioni.setdefault(regione, {"modalita": "scaglioni", "scaglioni": []})
        voce["scaglioni"].append({"fino_a": limite_superiore_fascia(fascia), "aliquota": aliquota})

    # Ordina gli scaglioni per soglia crescente, con quello senza tetto in fondo.
    # Il numero di scaglioni varia per regione (Abruzzo, Liguria e Bolzano ne hanno 3, non 4):
    # non assumiamo mai una struttura fissa.
    for voce in regioni.values():
        if voce["modalita"] == "scaglioni":
            voce["scaglioni"].sort(key=lambda s: (s["fino_a"] is None, s["fino_a"]))

    return regioni


# --- addizionale comunale ------------------------------------------------------------------------

COL_COMUNE = "Denominazione Comune"
COL_PROVINCIA = "Sigla Provincia"
COL_REGIONE = "Regione"
COL_CODICE = "Codice catastale"
COL_ADDIZIONALE = "Addizionale comunale dovuta - Ammontare in euro"
COL_IMPONIBILE = "Reddito imponibile addizionale - Ammontare in euro"

# Riga di servizio del dataset MEF, senza comune associato.
REGIONE_NON_VALIDA = "Mancante/errata"


def costruisci_comuni() -> tuple[list[dict], dict[str, int]]:
    """Legge il dataset comunale e deriva un'aliquota media per ciascun comune.

    Il dataset MEF non contiene l'aliquota deliberata dal comune: contiene gli importi aggregati
    dichiarati. Ricaviamo quindi un'aliquota media effettiva come

        aliquota = "Addizionale comunale dovuta" / "Reddito imponibile addizionale"

    e' una stima, non l'aliquota di delibera: appiattisce soglie di esenzione e scaglioni
    comunali in un unico numero (Milano, per esempio, esenta i redditi bassi).
    """
    percorsi = sorted(glob.glob(PATTERN_CSV_COMUNI))
    if not percorsi:
        raise FileNotFoundError(f"Nessun file corrispondente a {PATTERN_CSV_COMUNI}")
    header, righe = leggi_csv(percorsi[0])

    i_codice = header.index(COL_CODICE)
    i_nome = header.index(COL_COMUNE)
    i_provincia = header.index(COL_PROVINCIA)
    i_regione = header.index(COL_REGIONE)
    i_addizionale = header.index(COL_ADDIZIONALE)
    i_imponibile = header.index(COL_IMPONIBILE)

    comuni: list[dict] = []
    esclusi = {"regione_non_valida": 0, "addizionale_mancante": 0, "imponibile_non_valido": 0}

    for riga in righe:
        regione_dataset = riga[i_regione].strip()
        if regione_dataset == REGIONE_NON_VALIDA:
            esclusi["regione_non_valida"] += 1
            continue

        # Numeratore assente: il comune non ha dichiarato addizionale comunale dovuta
        # (nel dataset 2024 succede in comuni molto piccoli). Senza numeratore l'aliquota
        # non e' derivabile, quindi il comune resta fuori e non e' selezionabile in UI.
        grezzo_addizionale = riga[i_addizionale].strip()
        if not grezzo_addizionale:
            esclusi["addizionale_mancante"] += 1
            continue

        # Denominatore assente o nullo: divisione per zero, stessa sorte.
        grezzo_imponibile = riga[i_imponibile].strip()
        if not grezzo_imponibile or float(grezzo_imponibile) <= 0:
            esclusi["imponibile_non_valido"] += 1
            continue

        comuni.append(
            {
                "codice": riga[i_codice].strip(),
                "nome": riga[i_nome].strip(),
                "provincia": riga[i_provincia].strip(),
                "regione": regione_dataset,
                "regione_key": chiave_regione(regione_dataset),
                "aliquota": float(grezzo_addizionale) / float(grezzo_imponibile),
            }
        )

    comuni.sort(key=lambda c: (c["nome"], c["provincia"]))
    return comuni, esclusi


# --- main ----------------------------------------------------------------------------------------


def main() -> int:
    regioni = costruisci_regioni()
    comuni, esclusi = costruisci_comuni()

    # Ogni comune deve poter risalire alla propria regione: se il mapping dei nomi non copre
    # tutto il dataset, il calcolo dell'addizionale regionale fallirebbe a runtime.
    orfani = sorted({c["regione_key"] for c in comuni} - set(regioni))
    if orfani:
        print(f"ERRORE: regioni presenti nei comuni ma assenti in addreg2026.csv: {orfani}")
        return 1

    with open(JSON_REGIONI, "w", encoding="utf-8") as f:
        json.dump(regioni, f, ensure_ascii=False, indent=2)
    with open(JSON_COMUNI, "w", encoding="utf-8") as f:
        json.dump(comuni, f, ensure_ascii=False, indent=2)

    unica = sum(1 for v in regioni.values() if v["modalita"] == "unica")
    print(f"Regioni scritte: {len(regioni)} ({unica} ad aliquota unica, {len(regioni) - unica} a scaglioni)")
    print(f"Comuni scritti:  {len(comuni)}")
    print(f"Comuni esclusi:  {sum(esclusi.values())}")
    for motivo, quanti in esclusi.items():
        print(f"  - {motivo}: {quanti}")
    print(f"\n{JSON_REGIONI}\n{JSON_COMUNI}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
