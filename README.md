# Compensation Optimizer · Jet HR

Prototipo per un team HR/Finance di **cost saving**. Dato il costo attuale di un dipendente e un
budget aggiuntivo, confronta quanto valore generano:

- un aumento di RAL;
- fringe benefit e buoni pasto entro i plafond residui;
- welfare familiare entro le spese eleggibili dichiarate;
- un mix che assegna ai benefit eleggibili la quota utilizzabile e investe il residuo in RAL.

Il risultato separa sempre **netto cash**, **valore vincolato dei benefit** e **costo aziendale**.
Non e' un portale self-service per il dipendente e non presenta un euro di welfare come un euro di
liquidita' libera.

La pagina offre due letture dello stesso calcolo:

- **Cost saving azienda**: raccomandazione, costo evitato, composizione grafica del costo diretto,
  confronto degli scenari, allocazione del budget e grafico stacked situazione attuale/dopo budget;
- **RAL -> netto dipendente**: netto annuo e mensile, waterfall delle trattenute, TFR, dettaglio
  fiscale, incremento del netto mensile cash e confronto grafico attuale/dopo strategia tra netto,
  contributi, imposte e benefit.
  Questa vista supporta l'analisi HR senza cambiare il focus decisionale del prodotto.

## Avvio locale

Richiede Python 3.13.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Aprire <http://localhost:5000>. Per eseguire i test:

```bash
python -m pytest tests -q
```

## Ambiente

La configurazione non contiene segreti. `.env` e' ignorato da Git; `.env.example` documenta i
default usati dall'interfaccia.

| Variabile | Default | Significato |
|---|---:|---|
| `FLASK_DEBUG` | `1` in `.env.example` | Debug del server locale |
| `DEFAULT_EMPLOYER_CONTRIBUTION_RATE` | `0.30` | Stima contributi a carico del datore |
| `DEFAULT_INAIL_RATE` | `0.004` | Stima premio INAIL |

Le ultime due aliquote sono modificabili nella sezione **Ambiente aziendale**. Non esiste
un'aliquota datoriale universale: settore, CCNL, dimensione, qualifica e inquadramento previdenziale
possono cambiarla. Il prototipo rende quindi l'assunzione visibile invece di nasconderla.

La configurazione Render e' versionata in `render.yaml` e usa gli stessi default.

## Modello decisionale

Il costo diretto corrente e' calcolato come:

```text
RAL + contributi datore + premio INAIL + TFR + benefit attuali
```

La baseline dei benefit somma fringe benefit annui, buoni pasto correnti per le giornate indicate
e welfare aziendale annuo. Il budget aggiuntivo resta separato, così i grafici confrontano il
pacchetto retributivo realmente in essere con quello proposto.

Per lo scenario aumento, il motore risolve la RAL incrementale acquistabile con il budget e
ricalcola l'intera posizione fiscale: usa quindi il **netto marginale**, non un'aliquota media.

Per benefit e mix applica nell'ordine:

1. plafond fringe residuo: 1.000 euro, oppure 2.000 con figli fiscalmente a carico;
2. incremento del buono pasto elettronico fino a 10 euro per i giorni indicati;
3. welfare familiare entro le spese rimborsabili dichiarate;
4. nello scenario mix, eventuale budget residuo convertito in aumento RAL.

```text
efficienza = valore ricevuto / costo aziendale allocato
```

L'algoritmo massimizza il valore nominale ricevuto. La UI chiarisce che i benefit sono vincolati:
la raccomandazione e' valida solo se il dipendente utilizza davvero quelle prestazioni.

## Regole fiscali 2026 implementate

- IRPEF 23% / 33% / 43%;
- detrazione da lavoro dipendente;
- somma esente e detrazione aggiuntiva del cuneo strutturale;
- trattamento integrativo con controllo di capienza per gli input modellati;
- waterfall esplicito da IRPEF lorda a netta, con detrazioni e bonus fiscali automatici;
- contributi dipendente al 9,19%, come profilo semplificato;
- addizionale regionale 2026;
- addizionale comunale da delibere MEF, incluse esenzioni e scaglioni strutturati;
- TFR pari a RAL / 13,5;
- fringe benefit 2025-2027 e buoni pasto elettronici 2026.

Le fonti primarie sono elencate in [`sources.md`](sources.md).

## Addizionali comunali

`data/comuni_addizionale_2026.json` e' generato dagli elenchi ufficiali MEF 2026 e 2025. Ad agosto
2026 il file dell'anno corrente riporta ancora `0*` per alcuni comuni. Il normalizzatore applica:

1. regola ufficiale 2026, se strutturata;
2. ultima regola ufficiale 2025, quando il 2026 e' ancora `0*`;
3. stima aggregata 2024 soltanto se nessuna regola strutturata e' disponibile.

Ogni comune conserva `fonte_anno` e `stato`; la UI li espone nella baseline fiscale. Milano, per
esempio, usa l'aliquota ufficiale dello 0,8% e l'esenzione completa fino a 23.000 euro.

Per rigenerare il file dopo aver scaricato i due CSV dal portale MEF:

```bash
python scripts/build_addizionali_comunali.py addcom2026.csv addcom2025.csv
```

## Architettura

```text
app.py                         API Flask e validazione
calc/pipeline.py               RAL -> netto 2026
calc/costo_azienda.py          costo diretto e RAL acquistabile
calc/ottimizzatore.py          eleggibilita', scenari e raccomandazione
calc/cuneo.py                  misure strutturali sul cuneo
calc/addizionali.py            regole regionali e comunali
scripts/build_addizionali_comunali.py
templates/index.html           UI decisionale HR/Finance
static/                        design Jet HR esistente, senza build step
tests/                         formule, soglie, budget e API
```

Il frontend non contiene formule fiscali: invia gli input a `POST /api/ottimizza` e visualizza il
risultato. `POST /api/calcola` resta disponibile come endpoint di baseline.

## Limiti dichiarati

- profilo standard: dipendente privato, impiegato, tempo indeterminato, anno intero;
- contributi datoriali e INAIL configurabili ma non derivati automaticamente dal CSC aziendale;
- nessun incentivo contributivo o agevolazione all'assunzione;
- nessun reddito diverso da quello di lavoro dipendente;
- familiari usati per l'eleggibilita' dei benefit, non ancora per tutte le detrazioni personali;
- welfare considerato valido solo in presenza dei requisiti dell'art. 51 TUIR;
- premio di risultato escluso dall'MVP: richiede accordo depositato e verifica degli obiettivi;
- costi del provider welfare e altri costi amministrativi esclusi;
- simulazione annuale, non cedolino mensile.

Prima di usare una raccomandazione reale, Finance deve inserire le aliquote aziendali effettive e
Payroll/consulente del lavoro deve validare eleggibilita' e trattamento delle singole voci.
