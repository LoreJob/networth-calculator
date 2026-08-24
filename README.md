# Compensation Optimizer · Jet HR

Prototipo per un team HR/Finance di **cost saving**. Dato il costo attuale di un dipendente e un
budget aggiuntivo, confronta quanto valore generano:

- un aumento di RAL;
- fringe benefit e buoni pasto entro i plafond residui;
- welfare familiare entro le spese eleggibili dichiarate;
- nuovo regime fiscale agevolato per lavoratori impatriati dal 2024;
- un mix che assegna ai benefit eleggibili la quota utilizzabile e investe il residuo in RAL.

Il profilo familiare modella coniuge e figli a carico: le detrazioni personali vengono ricalcolate
sia sulla RAL attuale sia su quella successiva all'aumento, mentre i figli fiscalmente a carico
determinano automaticamente il plafond fringe applicabile.

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
- detrazione per coniuge a carico, rapportata ai mesi;
- detrazione per figli a carico, con eta', mesi e quota 0% / 50% / 100%;
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
calc/familiari.py              coniuge, figli, eta' e detrazioni personali
calc/regimi_agevolati.py       nuovo regime lavoratori impatriati
calc/addizionali.py            regole regionali e comunali
scripts/build_addizionali_comunali.py
templates/index.html           UI decisionale HR/Finance
static/                        design Jet HR esistente, senza build step
tests/                         formule, soglie, budget e API
```

Il frontend non contiene formule fiscali: invia gli input a `POST /api/ottimizza` e visualizza il
risultato. `POST /api/calcola` resta disponibile come endpoint di baseline.

## Assunzioni e limiti dichiarati

Il risultato e' una **stima decisionale annuale**, non un cedolino, un parere fiscale o una raccomandazione pronta per essere applicata. Le semplificazioni seguenti sono intenzionali e fanno parte del perimetro del prototipo.

### Profilo del dipendente

- dipendente del settore privato, impiegato, a tempo indeterminato e occupato per l'intero anno;
- RAL ammessa tra 1.000 e 10.000.000 euro per limiti di prodotto; gli estremi non implicano che il modello sia attendibile per rapporti marginali o redditi molto elevati;
- RAL come unica retribuzione imponibile e unico reddito: sono esclusi altri datori di lavoro, redditi personali, premi, straordinari, variabile, arretrati e periodi non lavorati;
- un solo comune di residenza fiscale per l'anno; non sono gestiti trasferimenti di residenza;
- 12, 13 o 14 mensilita' cambiano solo la divisione del netto annuo: non viene simulato il singolo cedolino, il calendario dei pagamenti o l'arrotondamento mensile;
- coniuge non legalmente ed effettivamente separato e figli sono gli unici familiari modellati. Ascendenti conviventi e altri familiari restano esclusi;
- reddito complessivo del dipendente assunto uguale al solo reddito prodotto dalla RAL. Reddito, mesi a carico e quota spettante dei familiari sono dichiarati dall'utente e non verificati da CU;
- eta' dei figli calcolata dalla data di nascita nel solo anno 2026: la detrazione decorre dal mese del 21° compleanno e termina il mese prima del 30°, salvo disabilita' accertata;
- nessun codice fiscale o documento familiare viene acquisito o validato;
- regime impatriati dal 2024 modellato nella versione base: 50% del reddito di lavoro imponibile, limite annuo agevolabile di 600.000 euro e durata di 5 periodi d'imposta;
- il regime si applica solo se l'utente attesta che Payroll o il consulente ha verificato i requisiti. Il tool non verifica residenza estera, qualificazione, continuita' dell'attivita' o documenti;
- rientro dei cervelli per docenti/ricercatori e' escluso perché non coerente con il profilo standard del prototipo;
- maggiorazione impatriati con figlio minore, regimi transitori e vecchia agevolazione territoriale del Mezzogiorno sono esclusi;
- il regime riduce solo l'imponibile fiscale: RAL, contributi previdenziali, TFR e costo aziendale restano invariati. La quota esente e' riaggiunta alle soglie delle misure che richiedono il reddito per intero;

### Imposte e contributi del dipendente

- anno fiscale 2026 e regole note/versionate nel repository; il modello non si aggiorna
  automaticamente quando cambia la normativa;
- imponibile previdenziale assunto uguale alla RAL e contributi dipendente applicati con aliquota
  unica del 9,19%; non sono gestiti l'1% aggiuntivo, massimali, fondi speciali, esoneri o aliquote
  dipendenti da settore e qualifica;
- in regime ordinario l'imponibile fiscale e' RAL meno contributi dipendente; nei regimi agevolati la percentuale si applica al reddito di lavoro gia' al netto dei contributi obbligatori;
- IRPEF, detrazioni da lavoro e famiglia e cuneo sono calcolati sul solo reddito modellato. Sono
  escluse detrazioni per spese, altre deduzioni personali e altri redditi;
- trattamento integrativo verificato rispetto alle detrazioni da lavoro e famiglia disponibili nel
  modello, non rispetto all'insieme completo degli oneri rilevanti previsto nei casi reali;
- addizionale regionale calcolata con le aliquote ordinarie: eventuali riduzioni legate a figli,
  disabilita' o altre condizioni regionali non sono applicate;
- addizionale comunale presa dalla fonte MEF 2026; dove la regola non e' disponibile viene usato il
  fallback ufficiale 2025 e, in ultima istanza, la stima 2024 indicata nei dati. Non sono simulati
  acconto, saldo e relative tempistiche in busta paga;
- gli importi sono calcolati su base annuale e arrotondati solo in uscita.

### Costo aziendale e TFR

- contributi datore e premio INAIL sono aliquote configurabili, non valori ricavati da CSC,
  ATECO, CCNL, qualifica, dimensione aziendale, posizione assicurativa o storico infortuni;
- sono esclusi fondi contrattuali, enti bilaterali, assicurazioni, payroll, formazione, assenze,
  costi amministrativi e altri costi indiretti del lavoro;
- nessun incentivo contributivo, sgravio, agevolazione all'assunzione o credito d'imposta;
- TFR stimato come RAL / 13,5, assumendo tutta la RAL utile. Non sono considerati contributo al
  Fondo di garanzia, rivalutazione del fondo, anticipi o destinazione alla previdenza complementare;
- fiscalita' d'impresa, deducibilita', IVA e trattamento contabile dei benefit sono esclusi.

### Fringe benefit

- il campo fringe attuale e' trattato come totale annuo gia' utilizzato. Il sistema non recupera o
  verifica valori da CU, precedenti datori, auto, prestiti, utenze, affitto, mutuo o altri benefit;
- il plafond e' 1.000 euro, elevato a 2.000 con figli fiscalmente a carico, e il motore assegna solo
  la capienza residua;
- non viene simulato il superamento del plafond: nella realta' il superamento rende imponibile
  l'intero ammontare, con effetti su IRPEF e contributi di dipendente e datore;
- tutte le tipologie sono valorizzate al nominale. Sono escluse le regole specifiche per auto in
  uso promiscuo, prestiti, fabbricati, stock option e altri compensi in natura;
- un euro di fringe e' assunto pari a un euro di costo aziendale e a un euro di valore ricevuto:
  non sono inclusi commissioni del provider, sconti, IVA indetraibile, costi operativi o valore
  percepito dal dipendente;
- il sistema non verifica documentazione, titolarita' della spesa o divieto di doppia agevolazione
  per rimborsi di utenze, affitto e interessi sul mutuo.

### Buoni pasto e welfare

- sono modellati solo buoni pasto elettronici, fino a 10 euro per ogni giornata dichiarata;
- il valore attuale annuo dei buoni e' stimato come valore giornaliero per numero di giorni: non
  sono verificati presenze, assenze, trasferte o dati effettivi del provider;
- welfare attuale e ulteriori spese familiari sono importi dichiarati dall'utente. Il motore assume
  che le nuove spese siano reali, documentate, non gia' rimborsate e ammesse dall'art. 51 TUIR;
- non viene verificato che il piano sia rivolto alla generalita' o a categorie omogenee di
  dipendenti, ne' sono applicati tutti i limiti specifici delle singole prestazioni;
- welfare e buoni pasto sono valorizzati al nominale, senza commissioni, IVA, costi amministrativi
  o probabilita' di utilizzo.

### Ottimizzatore e interpretazione dei risultati

- il budget e' annuale e riferito a un singolo dipendente; non sono gestiti popolazione aziendale,
  equita' interna, salary band, costo pluriennale o rinnovi contrattuali;
- l'allocazione segue un ordine fisso: fringe, buoni pasto, welfare e infine RAL. Non esplora tutte
  le combinazioni possibili e non considera preferenze del dipendente o policy aziendali;
- la strategia consigliata massimizza il valore **nominale** ricevuto. Liquidita', vincoli d'uso,
  gradimento, tasso di utilizzo, rischio fiscale e complessita' operativa non hanno un punteggio;
- il "costo evitato" e' il costo teorico necessario per generare lo stesso valore nominale con
  sola RAL: non rappresenta un risparmio contabilizzato o garantito;
- sono esclusi premio di risultato, previdenza complementare, assistenza sanitaria, auto
  aziendale, flexible benefits complessi, partecipazioni e altre leve di compensation;
- la baseline somma RAL, costi diretti e benefit dichiarati; accuratezza e completezza degli input
  restano responsabilita' dell'utilizzatore.
- non viene ricostruito l'anno precedente: requisiti, eta', redditi e detrazioni sono proiettati
  esclusivamente per il 2026.

### Dati necessari prima di un utilizzo reale

Finance dovrebbe inserire aliquote e costi aziendali effettivi. Payroll o il consulente del lavoro
dovrebbe inoltre validare almeno:

- posizione previdenziale, assicurativa e contrattuale del dipendente;
- redditi, giorni lavorati, detrazioni e situazione familiare rilevanti;
- fringe complessivi dell'anno, inclusi precedenti datori, e loro valore fiscale;
- capienza, documentazione e requisiti del piano welfare;
- costo del provider, IVA, commissioni e trattamento contributivo/fiscale di ogni voce.
