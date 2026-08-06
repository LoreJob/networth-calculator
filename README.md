# Calcolatore RAL &rarr; Netto

**Demo live: <https://networth-calculator-x8rk.onrender.com/>**
(gira sul piano gratuito di Render: se e' in sleep, la prima richiesta impiega 30&ndash;60 secondi)

Prototipo web che, data una RAL e un comune di residenza fiscale, proietta la retribuzione netta
annuale e mensile mostrando ogni voce trattenuta lungo il percorso: contributi INPS, IRPEF netta,
addizionale regionale, addizionale comunale e trattamento integrativo.

L'obiettivo del progetto e' una logica di calcolo **corretta, leggibile e verificabile**: niente
librerie fiscali di terze parti, niente black box. Ogni aliquota usata viene da un dataset del MEF
o da una norma citata in [`sources.md`](sources.md).

## Come si lancia

```bash
pip install -r requirements.txt
python app.py
```

Poi apri <http://localhost:5000>.

Per rigenerare i dati normalizzati a partire dai CSV grezzi del MEF (vedi
[Dati](#dati-e-come-vengono-normalizzati)):

```bash
python scripts/build_data.py
```

## Come e' fatto

```
app.py                  Flask: routing e validazione degli input. Nessuna logica fiscale.
calc/                   Logica di calcolo, funzioni pure e testabili una per una.
  scaglioni.py            applicazione progressiva di un'imposta a scaglioni
  inps.py                 contributi previdenziali a carico del dipendente
  irpef.py                IRPEF nazionale lorda 2026
  detrazioni.py           detrazione lavoro dipendente, art. 13 TUIR
  addizionali.py          addizionali regionale e comunale, lookup sui dati MEF
  trattamento_integrativo.py
  tfr.py
  pipeline.py             orchestratore: mette in sequenza i passaggi
data/                   i due CSV grezzi del MEF e i JSON normalizzati letti a runtime
scripts/build_data.py   normalizza i CSV MEF nei due JSON usati a runtime
static/, templates/     frontend HTML/CSS/JS vanilla, nessuna build step
tests/                  test della pipeline sui casi noti
```

Il frontend **non calcola nulla**: chiama `POST /api/calcola` e si limita a formattare e
disegnare la risposta. Le due API sono:

| Endpoint | Cosa fa |
|---|---|
| `GET /api/comuni` | elenco dei 7.817 comuni selezionabili, caricato una volta e filtrato lato client |
| `POST /api/calcola` | riceve `{ral, comune, mensilita}`, restituisce il breakdown completo |

### Scelte tecniche

- **Waterfall disegnato con `<div>` proporzionali**, non con una libreria da CDN. Il grafico ha
  sette barre con un posizionamento banale: una dipendenza esterna avrebbe aggiunto peso, un punto
  di rottura in piu' in produzione e nessun vantaggio. Cosi' l'app resta a dipendenza zero lato
  browser e funziona anche se la CDN e' irraggiungibile.
- **Autocomplete scritto a mano** invece di un `<select>`: con quasi 8.000 comuni la select nativa
  e' inusabile. La lista arriva una volta sola all'avvio e il filtro e' in memoria, con priorita'
  ai match dall'inizio del nome e massimo 10 suggerimenti.
- **La regione non e' un input.** Si deriva dal comune scelto tramite il campo `Regione` del
  dataset MEF, quindi non puo' esserci incoerenza tra comune e regione.
- **Chiave dei comuni = codice catastale**, non il nome: cinque denominazioni sono condivise da due
  comuni diversi (CASTRO, LIVO, PEGLIO, SAMONE, SAN TEODORO).

## Come si calcola

| # | Passaggio | Formula |
|---|---|---|
| 1 | Imponibile previdenziale | = RAL |
| 2 | Contributi INPS | imponibile previdenziale &times; 9,19% |
| 3 | Imponibile fiscale | RAL &minus; contributi INPS |
| 4 | IRPEF lorda | 23% fino a 28.000, 33% da 28.000 a 50.000, 43% oltre |
| 5 | Detrazione lavoro dipendente | art. 13 co. 1 TUIR, + 65 &euro; se 25.000 &lt; R &le; 35.000 |
| 6 | IRPEF netta | max(0, lorda &minus; detrazione) |
| 7 | Addizionale regionale | lookup per regione derivata dal comune |
| 8 | Addizionale comunale | imponibile fiscale &times; aliquota del comune |
| 9 | Trattamento integrativo | 1.200 &euro; fino a 15.000, phase-out lineare fino a 28.000 |
| 10 | Netto annuo | imponibile fiscale &minus; IRPEF netta &minus; addizionali + trattamento integrativo |
| 11 | Netto mensile | netto annuo / mensilita' (12, 13 o 14) |
| 12 | TFR maturato | RAL / 13,5 &mdash; **fuori dal netto**, mostrato a parte |

Le imposte a scaglioni sono applicate in modo **progressivo**: l'aliquota di uno scaglione colpisce
solo la quota di reddito che ricade in quello scaglione, mai l'intero reddito.

### Le due modalita' dell'addizionale regionale

Il dataset MEF distingue due modi in cui le regioni deliberano l'addizionale, e l'app li implementa
entrambi perche' danno risultati diversi:

- **aliquote per scaglioni** (15 tra regioni e province autonome): progressive come l'IRPEF. Il
  numero di scaglioni cambia da regione a regione &mdash; Abruzzo, Liguria e Bolzano ne hanno tre,
  non quattro, quindi il parser non assume mai una struttura fissa.
- **aliquota unica** (6: Valle d'Aosta, Veneto, Calabria, Sicilia, Sardegna, Basilicata): una sola
  aliquota applicata all'**intero** imponibile, non per scaglioni.

## Dati e come vengono normalizzati

`scripts/build_data.py` legge i due CSV grezzi del MEF e produce i JSON letti a runtime.

**`addreg2026.csv` &rarr; `regioni_addizionale_2026.json`** (21 voci)

Il campo `FASCIA` e' testo libero (`"oltre 15000.00 e fino a 28000.00 euro"`) e viene parsato in
soglie numeriche. Molise e Puglia compaiono con **due delibere diverse** nello stesso file: si tiene
solo quella con `NUMERO` piu' alto, che e' anche la piu' recente per data di pubblicazione.

**`Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.csv` &rarr; `comuni_addizionale_2024.json`** (7.817 comuni)

Il dataset **non contiene l'aliquota deliberata**: contiene importi aggregati dichiarati. L'aliquota
comunale e' quindi derivata:

```
aliquota_comunale = "Addizionale comunale dovuta" / "Reddito imponibile addizionale"
```

**80 comuni sono esclusi** dal JSON e non sono selezionabili nella UI:

| Motivo | Quanti |
|---|---|
| `Addizionale comunale dovuta` assente: senza numeratore l'aliquota non e' derivabile (sono comuni molto piccoli) | 79 |
| Riga di servizio del dataset, senza comune e con regione `Mancante/errata` | 1 |

## Assunzioni

- Lavoratore dipendente a tempo indeterminato, **nessun carico familiare**. Diverse regioni
  (Marche, Umbria, Puglia, Sardegna, Veneto, Trento, Bolzano) prevedono aliquote agevolate o
  detrazioni condizionate a figli o familiari disabili a carico: sono ignorate e si usa sempre
  l'aliquota base per fascia di reddito.
- Anno intero lavorato, nessuna variazione contrattuale in corso d'anno.
- Reddito da lavoro dipendente come unica fonte di reddito.
- Contributi INPS al 9,19% su tutta la RAL, senza massimale contributivo (circa 120.000 &euro;) e
  senza l'aliquota aggiuntiva sulla quota eccedente la prima fascia pensionabile: per RAL molto alte
  i contributi risultano sovrastimati.
- Nessun fringe benefit, straordinario, premio di risultato o welfare aziendale.
- Addizionali regionale e comunale calcolate sullo stesso anno, mentre in busta paga sono trattenute
  a saldo e in acconto nell'anno successivo.
- TFR escluso dal netto: e' un accantonamento, non cassa percepita nell'anno.

## Limiti noti

- **Cuneo fiscale strutturale 2026 non implementato.** La quota esente e la detrazione aggiuntiva di
  1.000 &euro; per la fascia 20.000&ndash;32.000 &euro; sono un meccanismo distinto dalla detrazione
  dell'art. 13, con una propria base di calcolo e un proprio decalage: implementarlo a meta' avrebbe
  prodotto numeri peggiori che non implementarlo affatto. Conseguenza pratica: in quella fascia di
  reddito **l'app sottostima il netto reale**.
- **Doppia semplificazione sull'addizionale comunale.** Il dato e' fermo all'anno d'imposta 2024
  (il piu' recente pubblicato) ed e' un'aliquota media derivata per via indiretta, non letta da
  delibera. Molti comuni &mdash; Milano compreso &mdash; hanno soglie di esenzione o scaglioni che
  un'unica aliquota piatta non puo' riprodurre: sul dato 2024 Milano risulta allo 0,718% contro lo
  0,8% deliberato, proprio perche' la media incorpora i redditi esentati.
- **Trattamento integrativo approssimato**: si usa il phase-out lineare sul reddito, senza la
  verifica di capienza rispetto alle detrazioni prevista dalla norma.

## Validazione

I test in `tests/test_pipeline.py` (32 casi, `python -m pytest tests -q`) verificano sui cinque
importi richiesti &mdash; 20.000, 25.000, 35.000, 50.000 e 70.000 &euro;, comune Milano, 13
mensilita' &mdash; che:

- il netto sia sempre positivo e sempre inferiore alla RAL;
- il netto cresca al crescere della RAL, senza inversioni;
- attorno alle soglie di scaglione (28.000 e 50.000 di imponibile fiscale) 100 &euro; di RAL in piu'
  non cambino il netto di piu' di 100 &euro;: se accadesse, vorrebbe dire che l'aliquota superiore
  e' stata applicata all'intero reddito invece che alla sola quota eccedente;
- netto mensile &times; mensilita' ridia il netto annuo, a meno degli arrotondamenti al centesimo;
- le voci del breakdown e le barre del waterfall ricompongano esattamente il netto;
- cambiando comune (Milano &rarr; Roma) cambino regione derivata e **entrambe** le addizionali,
  lasciando invariati imponibile fiscale e IRPEF.

Piu' i singoli moduli confrontati con il calcolo manuale delle formule di legge.

### Risultati &mdash; Milano, 13 mensilita'

| RAL | INPS | IRPEF netta | Add. reg. | Add. com. | Tratt. integr. | **Netto annuo** | **Netto mensile** | TFR |
|---|---|---|---|---|---|---|---|---|
| 20.000 | 1.838 | 1.367 | 234 | 130 | +908 | **17.339** | **1.334** | 1.481 |
| 25.000 | 2.298 | 2.827 | 306 | 163 | +489 | **19.896** | **1.530** | 1.852 |
| 35.000 | 3.216 | 6.042 | 455 | 228 | &mdash; | **25.058** | **1.928** | 2.593 |
| 50.000 | 4.595 | 11.785 | 689 | 326 | &mdash; | **32.605** | **2.508** | 3.704 |
| 70.000 | 6.433 | 19.534 | 1.003 | 456 | &mdash; | **42.574** | **3.275** | 5.185 |

Stessa RAL, comune diverso (35.000 &euro;, 13 mensilita'):

| Comune | Regione | Add. regionale | Add. comunale | Netto annuo |
|---|---|---|---|---|
| Milano | Lombardia | 455 | 228 | 25.058 |
| Roma | Lazio | 818 | 277 | 24.646 |

### Validazione manuale contro simulatori di terze parti

**Da completare.** Il confronto va fatto a mano su due o tre degli importi qui sopra, usando un
simulatore pubblico e annotando lo scostamento. Gli scostamenti attesi, in ordine di impatto:

1. **Fascia 20.000&ndash;32.000 &euro;**: i simulatori aggiornati applicano il cuneo fiscale
   strutturale 2026, qui non implementato. L'app dara' un netto **piu' basso**, ed e' lo
   scostamento piu' grande.
2. **Addizionale comunale**: qui e' una media derivata dai dati 2024, i simulatori usano l'aliquota
   deliberata. Differenza di poche decine di euro l'anno, in entrambe le direzioni.
3. **Detrazioni per carichi familiari**: i simulatori le espongono come input, qui sono azzerate per
   assunzione. A parita' di impostazione (nessun familiare a carico) la voce non incide.
4. **Arrotondamenti e ratei**: i cedolini reali arrotondano all'euro per mensilita' e distribuiscono
   detrazioni e trattamento integrativo mese per mese.

## Deploy

L'app e' online su <https://networth-calculator-x8rk.onrender.com/>.

Il servizio gira su **Render**, piano gratuito, con `gunicorn app:app`
(vedi [`render.yaml`](render.yaml)). Il workflow in
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) chiama il Deploy Hook di Render a
ogni push su `main`, usando il secret `RENDER_DEPLOY_HOOK`.

> **Nota sul tier gratuito:** dopo 15 minuti di inattivita' il servizio va in sleep e la prima
> richiesta successiva impiega 30&ndash;60 secondi per risvegliarlo. E' il comportamento noto del
> piano free di Render, non un problema dell'applicazione.

---

Simulazione semplificata a fini dimostrativi, non sostituisce un cedolino reale.
