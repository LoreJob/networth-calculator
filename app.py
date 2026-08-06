"""Applicazione Flask: routing e validazione degli input.

Qui non c'e' logica fiscale. Tutti i calcoli stanno in calc/, questo modulo si limita a
validare la richiesta, chiamare la pipeline e restituire JSON.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request, send_from_directory

from calc import addizionali
from calc.pipeline import MENSILITA_AMMESSE, MENSILITA_DEFAULT, RAL_MINIMA, calcola

app = Flask(__name__)

RADICE = os.path.dirname(os.path.abspath(__file__))

# Limite di sanita' sull'input: non e' una regola fiscale, serve solo a fermare valori assurdi
# prima di arrivare al calcolo.
RAL_MASSIMA = 10_000_000


@app.get("/")
def home():
    return render_template(
        "index.html",
        mensilita_ammesse=MENSILITA_AMMESSE,
        mensilita_default=MENSILITA_DEFAULT,
        ral_minima=int(RAL_MINIMA),
    )


# I loghi e le immagini di prodotto restano nelle cartelle originali del repo invece di essere
# spostati dentro static/: li serviamo da qui.
@app.get("/brand/<path:nome_file>")
def brand(nome_file: str):
    return send_from_directory(os.path.join(RADICE, "logo_pictogram"), nome_file)


@app.get("/api/comuni")
def api_comuni():
    """Elenco dei comuni selezionabili, per l'autocomplete lato client.

    Restituito una sola volta all'avvio della pagina: sono circa 7.800 voci, il filtro poi
    avviene in memoria nel browser.
    """
    comuni = [
        {
            "codice": c["codice"],
            "nome": c["nome"],
            "provincia": c["provincia"],
            "regione": c["regione"],
        }
        for c in addizionali.elenco_comuni()
    ]
    return jsonify({"comuni": comuni, "totale": len(comuni)})


@app.post("/api/calcola")
def api_calcola():
    """Calcola il netto a partire da {ral, comune, mensilita}."""
    dati = request.get_json(silent=True) or {}

    try:
        ral = float(dati.get("ral"))
    except (TypeError, ValueError):
        return jsonify({"errore": "RAL mancante o non numerica"}), 400
    if ral > RAL_MASSIMA:
        massima = f"{RAL_MASSIMA:,.0f}".replace(",", ".")
        return jsonify({"errore": f"La RAL non puo' superare {massima} euro"}), 400
    # Il limite inferiore lo impone la pipeline, che sa perche' esiste: qui non si duplica
    # la soglia, si lascia risalire il ValueError con il suo messaggio.

    try:
        mensilita = int(dati.get("mensilita", MENSILITA_DEFAULT))
    except (TypeError, ValueError):
        return jsonify({"errore": "Mensilita' non valida"}), 400
    if mensilita not in MENSILITA_AMMESSE:
        return jsonify({"errore": f"Mensilita' ammesse: {', '.join(map(str, MENSILITA_AMMESSE))}"}), 400

    codice_comune = (dati.get("comune") or "").strip()
    if not codice_comune:
        return jsonify({"errore": "Seleziona un comune di residenza fiscale"}), 400

    try:
        return jsonify(calcola(ral, codice_comune, mensilita))
    except KeyError:
        return jsonify({"errore": "Comune non presente nel dataset MEF 2024"}), 400
    except ValueError as errore:
        return jsonify({"errore": str(errore)}), 400


if __name__ == "__main__":
    # Solo per lo sviluppo locale. In produzione l'app gira con gunicorn (vedi render.yaml).
    app.run(debug=True, port=5000)
