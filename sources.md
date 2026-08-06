# Fonti

## Normativa fiscale

| Voce | Fonte | Link |
|---|---|---|
| Scaglioni e aliquote IRPEF 2026 (23% / 33% / 43%) | Agenzia delle Entrate &ndash; IRPEF, aliquote e scaglioni | https://www.agenziaentrate.gov.it/portale/aliquote-e-calcolo-dell-irpef |
| Detrazione per redditi da lavoro dipendente, art. 13 co. 1 e 1-bis TUIR | Agenzia delle Entrate &ndash; detrazioni per tipologia di reddito | https://www.agenziaentrate.gov.it/portale/detrazioni-per-tipologia-di-reddito |
| Testo dell'art. 13 TUIR | D.P.R. 917/1986, art. 13 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917 |
| Trattamento integrativo (ex bonus Renzi), 1.200 euro con phase-out 15.000&ndash;28.000 | D.L. 3/2020 convertito in L. 21/2020, art. 1 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2020-02-05;3 |
| Aliquota contributiva IVS a carico del dipendente, 9,19% | INPS &ndash; aliquote contributive lavoratori dipendenti settore privato | https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-strumento.schede-strumenti.aliquote-contributive-lavoratori-dipendenti.html |
| Quota annua di TFR pari alla retribuzione divisa per 13,5 | Codice civile, art. 2120 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art2120 |
| Legge di bilancio 2026 (impianto IRPEF e misure sul cuneo) | L. 199/2025 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2025;199 |

## Dataset

| File | Fonte | Link |
|---|---|---|
| `data/addreg2026.csv` | MEF &ndash; Dipartimento delle Finanze, addizionale regionale all'IRPEF, anno 2026 | https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?search_class%5B0%5D=cCOMUNE&opendata=yes |
| `data/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.csv` | MEF &ndash; Dipartimento delle Finanze, redditi e principali variabili IRPEF su base comunale, anno d'imposta 2024 | https://www1.finanze.gov.it/finanze/pagina_dichiarazioni/public/dichiarazioni.php |

Entrambi i CSV sono versionati insieme ai JSON che ne derivano: senza i file di partenza
l'aliquota comunale derivata e le 80 esclusioni non sarebbero verificabili e
`scripts/build_data.py` non sarebbe rieseguibile. Per rigenerare i JSON:
`python scripts/build_data.py`.

## Come le fonti entrano nel codice

- `calc/irpef.py` &rarr; scaglioni IRPEF 2026
- `calc/detrazioni.py` &rarr; art. 13 co. 1 e 1-bis TUIR
- `calc/inps.py` &rarr; aliquota INPS 9,19%
- `calc/trattamento_integrativo.py` &rarr; D.L. 3/2020
- `calc/tfr.py` &rarr; art. 2120 c.c.
- `calc/addizionali.py` + `scripts/build_data.py` &rarr; i due dataset MEF

## Nota sull'addizionale comunale

Il dataset comunale MEF **non contiene l'aliquota deliberata dai comuni**: contiene gli importi
aggregati dichiarati. L'aliquota usata dall'app e' derivata come rapporto tra
`Addizionale comunale dovuta` e `Reddito imponibile addizionale`, quindi e' una stima media
dell'anno d'imposta 2024 e non una fonte normativa. Il limite e' descritto nel README.
