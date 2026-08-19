"""Normalizza gli elenchi ufficiali MEF delle addizionali comunali.

Uso:
    python scripts/build_addizionali_comunali.py FILE_2026 FILE_2025

Il file dell'anno corrente contiene ``0*`` finche' un comune non pubblica la delibera. In quel
caso si usa l'ultima regola ufficiale disponibile nel file precedente. I metadati nel JSON
rendono visibile il fallback al motore e alla UI.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATI = ROOT / "data"
COMUNI_PRECEDENTI = DATI / "comuni_addizionale_2024.json"
OUTPUT = DATI / "comuni_addizionale_2026.json"


def numero(testo: str) -> float | None:
    testo = (testo or "").strip().replace("*", "")
    if not testo:
        return None
    try:
        return float(testo.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def leggi_csv(percorso: Path) -> dict[str, dict]:
    with percorso.open(encoding="utf-8-sig", newline="") as file:
        return {riga["CODICE_CATASTALE"]: riga for riga in csv.DictReader(file, delimiter=";")}


def limite_fascia(descrizione: str) -> float | None:
    if "oltre euro" in descrizione.lower():
        return None
    valori = re.findall(r"euro\s+([\d.]+(?:,\d+)?)", descrizione, flags=re.IGNORECASE)
    return numero(valori[-1]) if valori else None


def regola(riga: dict, anno: int) -> dict | None:
    flag = (riga.get("FLAG_NUOVA") or "").strip()
    prima = (riga.get("ALIQUOTA") or "").strip()
    if prima.endswith("*") or flag not in {"1", "2", "3", "4", "5", "6"}:
        return None

    coppie = []
    for indice in range(1, 13):
        suffisso = "" if indice == 1 else f"_{indice}"
        aliquota = numero(riga.get(f"ALIQUOTA{suffisso}", ""))
        fascia = (riga.get(f"FASCIA{suffisso}") or "").strip()
        if aliquota is not None and aliquota > 0:
            coppie.append((aliquota / 100, fascia))

    if not coppie:
        return {"modalita": "unica", "aliquota": 0.0, "esenzione": 0.0,
                "fonte_anno": anno, "stato": "ufficiale"}

    esenzione = numero(riga.get("IMPORTO_ESENTE", "")) or 0.0
    if flag in {"1", "2", "5"} or len(coppie) == 1:
        return {
            "modalita": "unica",
            "aliquota": coppie[-1][0],
            "esenzione": esenzione if flag in {"2", "4"} else 0.0,
            "fonte_anno": anno,
            "stato": "ufficiale" if flag in {"1", "2"} else "specificita_non_modellate",
        }

    scaglioni = []
    for aliquota, fascia in coppie:
        scaglioni.append({"fino_a": limite_fascia(fascia), "aliquota": aliquota})
    # Alcune delibere ripetono o omettono una soglia nel testo libero: in quel caso la regola
    # non e' abbastanza strutturata per un calcolo affidabile e verra' gestita dal fallback.
    limiti = [s["fino_a"] for s in scaglioni if s["fino_a"] is not None]
    if limiti != sorted(set(limiti)) or scaglioni[-1]["fino_a"] is not None:
        return None
    return {
        "modalita": "scaglioni",
        "scaglioni": scaglioni,
        "esenzione": esenzione if flag == "4" else 0.0,
        "fonte_anno": anno,
        "stato": "ufficiale" if flag in {"3", "4"} else "specificita_non_modellate",
    }


def main(file_2026: str, file_2025: str) -> None:
    righe_2026 = leggi_csv(Path(file_2026))
    righe_2025 = leggi_csv(Path(file_2025))
    precedenti = json.loads(COMUNI_PRECEDENTI.read_text(encoding="utf-8"))
    risultato = []

    for comune in precedenti:
        codice = comune["codice"]
        nuova = regola(righe_2026.get(codice, {}), 2026)
        if nuova is None:
            riga_precedente = righe_2025.get(codice, {})
            nuova = regola(riga_precedente, 2025)
            # Dopo il 20 dicembre il portale MEF usa 0* soltanto per i comuni che non hanno
            # istituito l'addizionale. Nel file definitivo 2025 e' quindi una regola ufficiale,
            # non un dato mancante.
            if nuova is None and (riga_precedente.get("ALIQUOTA") or "").strip() == "0*":
                nuova = {
                    "modalita": "unica", "aliquota": 0.0, "esenzione": 0.0,
                    "fonte_anno": 2025, "stato": "fallback_2025",
                }
            if nuova:
                nuova["stato"] = "fallback_2025"
        if nuova is None:
            nuova = {
                "modalita": "unica",
                "aliquota": comune["aliquota"],
                "esenzione": 0.0,
                "fonte_anno": 2024,
                "stato": "stima_aggregata",
            }
        risultato.append({
            "codice": codice,
            "nome": comune["nome"],
            "provincia": comune["provincia"],
            "regione": comune["regione"],
            "regione_key": comune["regione_key"],
            **nuova,
        })

    OUTPUT.write_text(json.dumps(risultato, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    conteggi = {}
    for comune in risultato:
        conteggi[comune["stato"]] = conteggi.get(comune["stato"], 0) + 1
    print(f"Scritti {len(risultato)} comuni in {OUTPUT}: {conteggi}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: build_addizionali_comunali.py FILE_2026 FILE_2025")
    main(sys.argv[1], sys.argv[2])
