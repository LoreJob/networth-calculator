/* UI del Compensation Optimizer. Tutti i calcoli restano nell'API. */
(function () {
  "use strict";

  var euro = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  var euroPreciso = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", minimumFractionDigits: 2 });
  var pct = new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 1 });
  var $ = function (id) { return document.getElementById(id); };
  var tooltipGrafico = document.createElement("div");
  tooltipGrafico.className = "grafico-tooltip";
  tooltipGrafico.hidden = true;
  tooltipGrafico.setAttribute("role", "tooltip");
  document.body.appendChild(tooltipGrafico);
  var el = {
    modulo: $("modulo"), budget: $("budget"), ral: $("ral"), comune: $("comune"),
    suggerimenti: $("suggerimenti"), derivato: $("derivato"), mensilita: $("mensilita"),
    figli: $("figli"), fringeUsati: $("fringe-usati"), buonoPasto: $("buono-pasto"),
    welfareAttuale: $("welfare-attuale"), speseWelfare: $("spese-welfare"),
    aliquotaDatore: $("aliquota-datore"),
    aliquotaInail: $("aliquota-inail"), giorni: $("giorni"), calcola: $("calcola"),
    errore: $("errore"), risultati: $("risultati"), scenari: $("scenari"),
    allocazione: $("allocazione"), logo: $("logo"), tema: $("tema"),
    vistaAzienda: $("vista-azienda"), vistaDipendente: $("vista-dipendente"),
    costoStack: $("costo-stack"), legendaCosto: $("legenda-costo"),
    waterfallDipendente: $("waterfall-dipendente"), dettaglioDipendente: $("dettaglio-dipendente")
  };
  var comuni = [];
  var comuneScelto = null;
  var evidenziato = -1;
  var vistaAttiva = "azienda";

  function posizionaTooltip(x, y) {
    var margine = 12;
    var rettangolo = tooltipGrafico.getBoundingClientRect();
    var sinistra = Math.min(window.innerWidth - rettangolo.width - margine, x + 12);
    var alto = y - rettangolo.height - 12;
    if (alto < margine) alto = y + 12;
    tooltipGrafico.style.left = Math.max(margine, sinistra) + "px";
    tooltipGrafico.style.top = Math.min(window.innerHeight - rettangolo.height - margine, alto) + "px";
  }

  function abilitaTooltipGrafico(segmento, etichetta, importo, quota) {
    var descrizione = etichetta + ": " + euroPreciso.format(importo) + " (" + pct.format(quota) + ")";
    segmento.tabIndex = 0;
    segmento.setAttribute("aria-label", descrizione);

    function mostra(x, y) {
      tooltipGrafico.innerHTML = "";
      var titolo = document.createElement("strong");
      titolo.textContent = etichetta;
      var dettaglio = document.createElement("span");
      dettaglio.textContent = euroPreciso.format(importo) + " · " + pct.format(quota);
      tooltipGrafico.appendChild(titolo);
      tooltipGrafico.appendChild(dettaglio);
      tooltipGrafico.hidden = false;
      posizionaTooltip(x, y);
    }

    segmento.addEventListener("mouseenter", function (evento) { mostra(evento.clientX, evento.clientY); });
    segmento.addEventListener("mousemove", function (evento) { posizionaTooltip(evento.clientX, evento.clientY); });
    segmento.addEventListener("mouseleave", function () { tooltipGrafico.hidden = true; });
    segmento.addEventListener("focus", function () {
      var r = segmento.getBoundingClientRect();
      mostra(r.left + r.width / 2, r.top + r.height / 2);
    });
    segmento.addEventListener("blur", function () { tooltipGrafico.hidden = true; });
  }

  window.addEventListener("scroll", function () { tooltipGrafico.hidden = true; }, true);

  function applicaTema(tema) {
    document.documentElement.setAttribute("data-theme", tema);
    el.logo.src = tema === "dark" ? "/brand/JetHR%20Logo%20White.svg" : "/brand/JetHR%20Logo%20Dark.svg";
    el.tema.textContent = tema === "dark" ? "Tema chiaro" : "Tema scuro";
    localStorage.setItem("tema", tema);
  }
  applicaTema(localStorage.getItem("tema") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  el.tema.addEventListener("click", function () {
    applicaTema(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });

  function impostaVista(vista) {
    vistaAttiva = vista;
    var azienda = vista === "azienda";
    el.vistaAzienda.hidden = !azienda;
    el.vistaDipendente.hidden = azienda;
    $("tab-azienda").setAttribute("aria-selected", String(azienda));
    $("tab-dipendente").setAttribute("aria-selected", String(!azienda));
    $("tab-azienda").tabIndex = azienda ? 0 : -1;
    $("tab-dipendente").tabIndex = azienda ? -1 : 0;
    $("titolo-vista").textContent = azienda
      ? "Più valore, a parità di costo aziendale"
      : "Dalla RAL al netto del dipendente";
    $("sottotitolo-vista").textContent = azienda
      ? "Confronta aumento salariale e benefit eleggibili, misura il valore generato e trova il mix più efficiente."
      : "Visualizza come la retribuzione lorda viene distribuita tra contributi, imposte e netto percepito.";
    $("azione-calcola").textContent = azienda ? "Ottimizza il budget" : "Calcola il netto";
  }

  document.querySelectorAll(".vista-switch button").forEach(function (bottone) {
    bottone.addEventListener("click", function () { impostaVista(bottone.dataset.vista); });
    bottone.addEventListener("keydown", function (evento) {
      if (evento.key !== "ArrowLeft" && evento.key !== "ArrowRight") return;
      evento.preventDefault();
      var destinazione = bottone.dataset.vista === "azienda" ? "dipendente" : "azienda";
      impostaVista(destinazione);
      $(destinazione === "azienda" ? "tab-azienda" : "tab-dipendente").focus();
    });
  });
  impostaVista("azienda");

  function mostraErrore(messaggio) {
    el.errore.textContent = messaggio;
    el.errore.hidden = false;
  }

  fetch("/api/comuni").then(function (r) { return r.json(); }).then(function (dati) {
    comuni = dati.comuni;
    el.comune.placeholder = "Cerca tra " + dati.totale.toLocaleString("it-IT") + " comuni";
  }).catch(function () { mostraErrore("Non riesco a caricare i comuni."); });

  function filtra(testo) {
    var cercato = testo.trim().toLowerCase();
    if (cercato.length < 2) return [];
    var inizio = comuni.filter(function (c) { return c.nome.toLowerCase().indexOf(cercato) === 0; });
    var interno = comuni.filter(function (c) { return c.nome.toLowerCase().indexOf(cercato) > 0; });
    return inizio.concat(interno).slice(0, 10);
  }

  function scegli(comune) {
    comuneScelto = comune;
    el.comune.value = comune.nome + " (" + comune.provincia + ")";
    el.derivato.textContent = comune.regione + " · addizionali locali applicate";
    el.derivato.classList.add("attivo");
    el.suggerimenti.hidden = true;
    el.comune.setAttribute("aria-expanded", "false");
  }

  function mostraSuggerimenti(elenco) {
    el.suggerimenti.innerHTML = "";
    evidenziato = -1;
    elenco.forEach(function (comune) {
      var voce = document.createElement("li");
      voce.setAttribute("role", "option");
      voce.textContent = comune.nome + " (" + comune.provincia + ") · " + comune.regione;
      voce.addEventListener("mousedown", function (evento) { evento.preventDefault(); scegli(comune); });
      el.suggerimenti.appendChild(voce);
    });
    el.suggerimenti.hidden = elenco.length === 0;
    el.comune.setAttribute("aria-expanded", String(elenco.length > 0));
  }

  el.comune.addEventListener("input", function () {
    comuneScelto = null;
    el.derivato.textContent = "Determina le addizionali locali.";
    el.derivato.classList.remove("attivo");
    mostraSuggerimenti(filtra(el.comune.value));
  });
  el.comune.addEventListener("keydown", function (evento) {
    var voci = el.suggerimenti.querySelectorAll("li");
    if (!voci.length) return;
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      if (evidenziato >= 0) voci[evidenziato].removeAttribute("aria-selected");
      evidenziato = (evidenziato + (evento.key === "ArrowDown" ? 1 : -1) + voci.length) % voci.length;
      voci[evidenziato].setAttribute("aria-selected", "true");
    } else if (evento.key === "Enter" && evidenziato >= 0) {
      evento.preventDefault(); scegli(filtra(el.comune.value)[evidenziato]);
    } else if (evento.key === "Escape") el.suggerimenti.hidden = true;
  });
  el.comune.addEventListener("blur", function () { setTimeout(function () { el.suggerimenti.hidden = true; }, 120); });

  function numero(campo) { return Number(campo.value); }

  el.modulo.addEventListener("submit", function (evento) {
    evento.preventDefault();
    el.errore.hidden = true;
    if (!comuneScelto) return mostraErrore("Seleziona il comune dall'elenco dei suggerimenti.");
    if (!(numero(el.budget) > 0)) return mostraErrore("Inserisci un budget aziendale maggiore di zero.");
    if (!(numero(el.ral) >= Number(el.ral.dataset.minima))) return mostraErrore("Inserisci una RAL valida.");

    var payload = {
      budget: numero(el.budget), ral: numero(el.ral), comune: comuneScelto.codice,
      mensilita: numero(el.mensilita), figli_a_carico: el.figli.checked,
      fringe_usati: numero(el.fringeUsati), buono_pasto_attuale: numero(el.buonoPasto),
      welfare_attuale: numero(el.welfareAttuale), spese_welfare: numero(el.speseWelfare),
      aliquota_datore: numero(el.aliquotaDatore) / 100,
      aliquota_inail: numero(el.aliquotaInail) / 100, giorni_lavorativi: numero(el.giorni)
    };
    el.calcola.disabled = true;
    fetch("/api/ottimizza", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
      .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.errore || "Calcolo non riuscito"); return d; }); })
      .then(disegna).catch(function (errore) { mostraErrore(errore.message); })
      .finally(function () { el.calcola.disabled = false; });
  });

  function disegna(dati) {
    el.risultati.hidden = false;
    var raccomandato = dati.scenari.find(function (s) { return s.codice === dati.raccomandazione.codice; });
    $("titolo-raccomandazione").textContent = dati.raccomandazione.titolo;
    $("nota-raccomandazione").textContent = dati.raccomandazione.nota;
    $("valore-generato").textContent = euro.format(raccomandato.valore_totale);
    $("costo-evitato").textContent = euro.format(dati.raccomandazione.costo_evitato);
    $("efficienza").textContent = pct.format(raccomandato.efficienza);
    $("nota-risparmio").textContent = "* Costo aggiuntivo stimato per generare lo stesso valore con sola RAL: " + euro.format(dati.raccomandazione.costo_aumento_equivalente) + ".";

    el.scenari.innerHTML = "";
    dati.scenari.forEach(function (scenario) {
      var riga = document.createElement("tr");
      if (scenario.codice === dati.raccomandazione.codice) riga.className = "consigliato";
      var valori = [scenario.nome, euro.format(scenario.costo_allocato), euro.format(scenario.netto_cash),
        euro.format(scenario.valore_benefit), euro.format(scenario.valore_totale), pct.format(scenario.efficienza)];
      valori.forEach(function (valore, indice) {
        var cella = document.createElement(indice === 0 ? "th" : "td");
        cella.textContent = valore;
        riga.appendChild(cella);
      });
      el.scenari.appendChild(riga);
    });

    disegnaAllocazione(raccomandato, dati.input.budget);
    var costo = dati.baseline.costo_azienda;
    disegnaCostoAzienda(costo);
    disegnaConfrontoCosti(dati.confronto_costi);
    disegnaVistaDipendente(dati.baseline.dettaglio_fiscale);
    disegnaConfrontoDipendente(dati.confronto_dipendente);
    $("dipendente-aumento-mensile").textContent = "+" + euroPreciso.format(
      Math.max(0, dati.confronto_dipendente.incremento_netto_mensile)
    );
    el.risultati.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function disegnaAllocazione(scenario, budget) {
    el.allocazione.innerHTML = "";
    var voci = scenario.benefit.slice();
    if (scenario.incremento_ral > 0) voci.push({ etichetta: "Aumento RAL", importo: scenario.budget - scenario.valore_benefit });
    voci.forEach(function (voce) {
      var riga = document.createElement("div");
      riga.className = "voce-allocazione";
      var testa = document.createElement("div");
      testa.innerHTML = "<span></span><strong></strong>";
      testa.querySelector("span").textContent = voce.etichetta;
      testa.querySelector("strong").textContent = euro.format(voce.importo);
      var traccia = document.createElement("div");
      traccia.className = "traccia";
      var barra = document.createElement("i");
      barra.style.width = Math.min(100, voce.importo / budget * 100) + "%";
      traccia.appendChild(barra); riga.appendChild(testa); riga.appendChild(traccia); el.allocazione.appendChild(riga);
    });
  }

  function disegnaCostoAzienda(costo) {
    var componenti = [
      { codice: "ral", etichetta: "RAL", importo: costo.ral },
      { codice: "contributi", etichetta: "Contributi datore", importo: costo.contributi_datore },
      { codice: "inail", etichetta: "INAIL", importo: costo.inail },
      { codice: "tfr", etichetta: "TFR", importo: costo.tfr },
      { codice: "benefit", etichetta: "Benefit attuali", importo: costo.benefit }
    ];
    $("costo-totale-grafico").textContent = euro.format(costo.totale);
    el.costoStack.innerHTML = "";
    el.legendaCosto.innerHTML = "";
    el.costoStack.setAttribute(
      "aria-label",
      "Costo aziendale totale " + euro.format(costo.totale) + ": " +
        componenti.map(function (c) { return c.etichetta + " " + euro.format(c.importo); }).join(", ")
    );

    componenti.forEach(function (componente) {
      var quota = costo.totale > 0 ? componente.importo / costo.totale : 0;
      var segmento = document.createElement("div");
      segmento.className = "segmento-costo segmento-" + componente.codice;
      segmento.style.flexBasis = (quota * 100) + "%";
      abilitaTooltipGrafico(segmento, componente.etichetta, componente.importo, quota);
      if (quota >= 0.08) segmento.textContent = pct.format(quota);
      el.costoStack.appendChild(segmento);

      var legenda = document.createElement("div");
      legenda.className = "voce-legenda";
      var colore = document.createElement("i");
      colore.className = "colore-" + componente.codice;
      var nome = document.createElement("span");
      nome.textContent = componente.etichetta;
      var importo = document.createElement("strong");
      importo.textContent = euro.format(componente.importo);
      legenda.appendChild(colore); legenda.appendChild(nome); legenda.appendChild(importo);
      el.legendaCosto.appendChild(legenda);
    });
  }

  function disegnaVistaDipendente(fiscale) {
    $("dipendente-netto-annuo").textContent = euro.format(fiscale.risultato.netto_annuo);
    $("dipendente-netto-mensile").textContent = euro.format(fiscale.risultato.netto_mensile);
    $("dipendente-mensilita").textContent = "(" + fiscale.input.mensilita + " mensilità)";
    $("dipendente-tfr").textContent = euro.format(fiscale.risultato.tfr_annuo);
    disegnaWaterfallDipendente(fiscale.waterfall);
    disegnaDettaglioDipendente(fiscale);
  }

  function disegnaConfrontoCosti(confronto) {
    var componenti = [
      { codice: "ral", etichetta: "RAL", campo: "ral" },
      { codice: "contributi", etichetta: "Contributi datore", campo: "contributi_datore" },
      { codice: "inail", etichetta: "INAIL", campo: "inail" },
      { codice: "tfr", etichetta: "TFR", campo: "tfr" },
      { codice: "benefit", etichetta: "Benefit", campo: "benefit" }
    ];
    var massimo = Math.max(confronto.attuale.totale, confronto.dopo_budget.totale);

    $("incremento-costo-percentuale").textContent = "+" + pct.format(confronto.incremento_percentuale);
    $("incremento-costo-euro").textContent = "+" + euro.format(confronto.incremento);
    $("totale-costo-attuale").textContent = euro.format(confronto.attuale.totale);
    $("totale-costo-dopo").textContent = euro.format(confronto.dopo_budget.totale);

    function costruisciBarra(id, situazione) {
      var barra = $(id);
      barra.innerHTML = "";
      barra.style.height = (massimo > 0 ? situazione.totale / massimo * 100 : 0) + "%";
      componenti.forEach(function (componente) {
        var importo = situazione[componente.campo];
        if (!(importo > 0)) return;
        var quota = situazione.totale > 0 ? importo / situazione.totale : 0;
        var segmento = document.createElement("div");
        segmento.className = "segmento-costo segmento-" + componente.codice;
        segmento.style.flex = "0 0 " + (quota * 100) + "%";
        abilitaTooltipGrafico(segmento, componente.etichetta, importo, quota);
        if (quota >= 0.09) segmento.textContent = pct.format(quota);
        barra.appendChild(segmento);
      });
    }

    costruisciBarra("barra-costo-attuale", confronto.attuale);
    costruisciBarra("barra-costo-dopo", confronto.dopo_budget);

    var descrizione = "Costo attuale " + euro.format(confronto.attuale.totale) +
      ", costo dopo il budget " + euro.format(confronto.dopo_budget.totale) +
      ", aumento " + pct.format(confronto.incremento_percentuale) + ".";
    $("grafico-confronto-costi").setAttribute("aria-label", descrizione);

    var legenda = $("legenda-confronto-costi");
    legenda.innerHTML = "";
    componenti.forEach(function (componente) {
      var prima = confronto.attuale[componente.campo];
      var dopo = confronto.dopo_budget[componente.campo];
      if (!(prima > 0 || dopo > 0)) return;
      var voce = document.createElement("div");
      voce.className = "voce-legenda";
      var colore = document.createElement("i"); colore.className = "colore-" + componente.codice;
      var nome = document.createElement("span"); nome.textContent = componente.etichetta;
      var valori = document.createElement("strong"); valori.textContent = euro.format(prima) + " → " + euro.format(dopo);
      voce.appendChild(colore); voce.appendChild(nome); voce.appendChild(valori); legenda.appendChild(voce);
    });
  }

  function disegnaWaterfallDipendente(voci) {
    var scala = voci[0].importo;
    var cumulato = 0;
    el.waterfallDipendente.innerHTML = "";

    function percentualeBarra(valore) {
      if (!(scala > 0) || !isFinite(valore)) return 0;
      return Math.min(100, Math.max(0, valore / scala * 100));
    }

    voci.forEach(function (voce, indice) {
      var estremo = indice === 0 || indice === voci.length - 1;
      var larghezza = Math.abs(voce.importo);
      var inizio;
      if (estremo) {
        inizio = 0;
        cumulato = voce.importo;
      } else {
        inizio = voce.importo < 0 ? cumulato - larghezza : cumulato;
        cumulato += voce.importo;
      }

      var riga = document.createElement("div");
      riga.className = "riga-waterfall" + (estremo ? " totale" : "");
      var nome = document.createElement("span");
      nome.className = "voce"; nome.textContent = voce.etichetta;
      var traccia = document.createElement("span");
      traccia.className = "barra";
      if (voce.importo !== 0) {
        var barra = document.createElement("i");
        barra.className = voce.tipo;
        barra.style.left = percentualeBarra(inizio) + "%";
        barra.style.width = percentualeBarra(larghezza) + "%";
        traccia.appendChild(barra);
      }
      var importo = document.createElement("span");
      importo.className = "importo"; importo.textContent = euro.format(voce.importo);
      riga.appendChild(nome); riga.appendChild(traccia); riga.appendChild(importo);
      el.waterfallDipendente.appendChild(riga);
    });
  }

  function disegnaConfrontoDipendente(confronto) {
    var componenti = [
      { codice: "netto", etichetta: "Netto cash", campo: "netto_cash" },
      { codice: "contributi-dipendente", etichetta: "Contributi dipendente", campo: "contributi_dipendente" },
      { codice: "irpef", etichetta: "IRPEF netta", campo: "irpef_netta" },
      { codice: "addizionali", etichetta: "Addizionali", campo: "addizionali" },
      { codice: "benefit", etichetta: "Benefit", campo: "benefit" }
    ];
    var massimo = Math.max(confronto.attuale.totale_flusso, confronto.dopo_budget.totale_flusso);
    $("incremento-dipendente-percentuale").textContent = "+" + pct.format(confronto.incremento_percentuale);
    $("incremento-dipendente-euro").textContent = "+" + euro.format(confronto.incremento_valore);
    $("totale-dipendente-attuale").textContent = euro.format(confronto.attuale.totale_flusso);
    $("totale-dipendente-dopo").textContent = euro.format(confronto.dopo_budget.totale_flusso);

    function costruisciBarra(id, situazione) {
      var barra = $(id);
      barra.innerHTML = "";
      barra.style.height = (massimo > 0 ? situazione.totale_flusso / massimo * 100 : 0) + "%";
      componenti.forEach(function (componente) {
        var importo = situazione[componente.campo];
        if (!(importo > 0)) return;
        var quota = situazione.totale_flusso > 0 ? importo / situazione.totale_flusso : 0;
        var segmento = document.createElement("div");
        segmento.className = "segmento-costo segmento-" + componente.codice;
        segmento.style.flex = "0 0 " + (quota * 100) + "%";
        abilitaTooltipGrafico(segmento, componente.etichetta, importo, quota);
        if (quota >= 0.09) segmento.textContent = pct.format(quota);
        barra.appendChild(segmento);
      });
    }

    costruisciBarra("barra-dipendente-attuale", confronto.attuale);
    costruisciBarra("barra-dipendente-dopo", confronto.dopo_budget);
    $("grafico-confronto-dipendente").setAttribute(
      "aria-label",
      "Valore per il dipendente da " + euro.format(confronto.attuale.valore_totale) +
      " a " + euro.format(confronto.dopo_budget.valore_totale) +
      ", aumento " + pct.format(confronto.incremento_percentuale) + "."
    );

    var legenda = $("legenda-confronto-dipendente");
    legenda.innerHTML = "";
    componenti.forEach(function (componente) {
      var prima = confronto.attuale[componente.campo];
      var dopo = confronto.dopo_budget[componente.campo];
      if (!(prima > 0 || dopo > 0)) return;
      var voce = document.createElement("div"); voce.className = "voce-legenda";
      var colore = document.createElement("i"); colore.className = "colore-" + componente.codice;
      var nome = document.createElement("span"); nome.textContent = componente.etichetta;
      var valori = document.createElement("strong"); valori.textContent = euro.format(prima) + " → " + euro.format(dopo);
      voce.appendChild(colore); voce.appendChild(nome); voce.appendChild(valori); legenda.appendChild(voce);
    });
  }

  function disegnaDettaglioDipendente(fiscale) {
    var d = fiscale.dettaglio;
    var fonte = fiscale.fonti_dati;
    var voci = [
      ["RAL", d.imponibile_previdenziale, "Retribuzione annua lorda"],
      ["Contributi INPS dipendente", -d.contributi_inps, null],
      ["Imponibile fiscale", d.imponibile_fiscale, "RAL meno contributi"],
      ["IRPEF lorda", -d.irpef_lorda, "Scaglioni 23% / 33% / 43%"],
      ["Detrazione lavoro dipendente", d.detrazione_lavoro_applicata, "Quota utilizzata"],
      ["Detrazione aggiuntiva cuneo", d.detrazione_cuneo_applicata, "Applicata automaticamente"],
      ["IRPEF netta", -d.irpef_netta, "Dopo le detrazioni"],
      ["Addizionale regionale", -d.addizionale_regionale, fiscale.input.comune.regione],
      ["Addizionale comunale", -d.addizionale_comunale, fiscale.input.comune.nome],
      ["Trattamento integrativo", d.trattamento_integrativo, null],
      ["Somma esente cuneo", d.somma_cuneo, null],
      ["Netto annuo", fiscale.risultato.netto_annuo, null]
    ];
    el.dettaglioDipendente.innerHTML = "";
    voci.forEach(function (voce) {
      var riga = document.createElement("div"); riga.className = "voce-dettaglio";
      var dt = document.createElement("dt"); var dd = document.createElement("dd");
      dt.textContent = voce[0];
      if (voce[2]) {
        var notaVoce = document.createElement("span");
        notaVoce.className = "nota"; notaVoce.textContent = voce[2]; dt.appendChild(notaVoce);
      }
      dd.textContent = euroPreciso.format(voce[1]);
      riga.appendChild(dt); riga.appendChild(dd); el.dettaglioDipendente.appendChild(riga);
    });
    $("fonte-comunale").textContent = "Addizionale comunale: dato " +
      fonte.comunale_stato.replaceAll("_", " ") + " · anno fonte " + fonte.comunale_anno + ".";
  }
})();
