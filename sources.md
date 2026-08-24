# Fonti normative e dati

Fonti primarie usate dal modello, consultate per l'anno fiscale 2026.

| Regola | Fonte ufficiale |
|---|---|
| IRPEF 23% / 33% / 43% | [Legge 30 dicembre 2025 n. 199, art. 1 co. 3](https://www.normattiva.it/eli/stato/LEGGE/2025/12/30/199/CONSOLIDATED) |
| Somma esente e detrazione aggiuntiva sul cuneo | [Legge 30 dicembre 2024 n. 207, art. 1 co. 4-9](https://www.normattiva.it/eli/id/2024/12/31/24G00229/ORIGINAL) |
| Detrazione lavoro dipendente | [DPR 917/1986, art. 13](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917) |
| Detrazioni per coniuge e figli a carico | [DPR 917/1986, art. 12](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917~art12) |
| Nuovo regime lavoratori impatriati | [D.Lgs. 209/2023, art. 5](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2023-12-27;209~art5) |
| Eta' e mesi di detrazione dei figli | [Agenzia delle Entrate, circolare 4/E del 16 maggio 2025](https://def.finanze.it/DocTribFrontend/getContent.do?id=%7B7CC565F8-09C0-4BC6-B725-9E556F578021%7D) |
| Trattamento integrativo | [DL 5 febbraio 2020 n. 3, art. 1](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2020-02-05;3) |
| Reddito dipendente e welfare | [DPR 917/1986, art. 51](https://www.normattiva.it/uri-res/N2Ls?urn%3Anir%3Astato%3Alegge%3A1986%3B917~art51=) |
| Fringe benefit 2025-2027 | [Agenzia delle Entrate, Quadro RC](https://infoprecompilata.agenziaentrate.gov.it/portale/web/guest/quadro-rc) |
| Buono pasto elettronico fino a 10 euro dal 2026 | [Legge 199/2025, art. 1 co. 14](https://www.normattiva.it/eli/stato/LEGGE/2025/12/30/199/CONSOLIDATED) |
| TFR, quota annua / 13,5 | [Codice civile, art. 2120](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art2120) |
| Addizionali regionali | [Dipartimento delle Finanze, open data](https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?search_class%5B0%5D=cCOMUNE&opendata=yes) |
| Addizionali comunali 2026 | [Dipartimento delle Finanze, elenchi generali](https://www1.finanze.gov.it/finanze2/dipartimentopolitichefiscali/fiscalitalocale/nuova_addcomirpef/download/tabella.htm) |
| Regola comunale di Milano | [Comune di Milano, addizionale comunale IRPEF](https://www.comune.milano.it/aree-tematiche/tributi/addizionale-comunale-irpef) |

## Assunzioni che non derivano da una singola aliquota normativa

Il default del 30% per i contributi datoriali e lo 0,4% per INAIL sono parametri di scenario, non aliquote dichiarate valide per tutte le aziende. Sono visibili e modificabili nella UI e tramite variabili d'ambiente. Una simulazione reale deve usare i valori del profilo contributivo aziendale.

L'aliquota INPS del dipendente e' fissata al 9,19% per il profilo standard del prototipo. Massimale, contributo aggiuntivo dell'1% e casistiche previdenziali diverse restano fuori dall'MVP.

## Provenienza dei dati comunali

Il normalizzatore conserva per ogni comune:

- `fonte_anno`: anno dell'elenco MEF effettivamente utilizzato;
- `stato=ufficiale`: regola strutturata 2026;
- `stato=fallback_2025`: il 2026 riporta ancora `0*`;
- `stato=specificita_non_modellate`: delibera con condizioni personali non rappresentabili;
- `stato=stima_aggregata`: fallback residuale ai dati dichiarativi aggregati 2024.

Questa informazione fa parte della risposta API e viene mostrata nella UI: una stima non viene mai presentata come una delibera ufficiale.
