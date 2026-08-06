/* Frontend del calcolatore RAL -> netto.
 *
 * Nessun calcolo fiscale qui dentro: il JS raccoglie gli input, chiama /api/calcola e
 * disegna quello che l'API restituisce. L'unica logica locale e' il filtro dei comuni
 * per l'autocomplete e la formattazione degli importi.
 */

(function () {
  "use strict";

  var MAX_SUGGERIMENTI = 10;

  // useGrouping "always": senza, il separatore delle migliaia sparirebbe sui numeri di quattro
  // cifre e la colonna degli importi risulterebbe disallineata (35.000 accanto a 3217).
  var euro = new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
    useGrouping: "always"
  });
  var euroPreciso = new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: "always"
  });
  var percentuale = new Intl.NumberFormat("it-IT", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 3
  });

  var el = {
    modulo: document.getElementById("modulo"),
    ral: document.getElementById("ral"),
    comune: document.getElementById("comune"),
    suggerimenti: document.getElementById("suggerimenti"),
    derivato: document.getElementById("derivato"),
    mensilita: document.getElementById("mensilita"),
    calcola: document.getElementById("calcola"),
    errore: document.getElementById("errore"),
    risultati: document.getElementById("risultati"),
    nettoAnnuo: document.getElementById("netto-annuo"),
    nettoMensile: document.getElementById("netto-mensile"),
    etichettaMensilita: document.getElementById("etichetta-mensilita"),
    waterfall: document.getElementById("waterfall"),
    tfr: document.getElementById("tfr"),
    dettaglio: document.getElementById("dettaglio"),
    logo: document.getElementById("logo"),
    tema: document.getElementById("tema")
  };

  var comuni = [];          // elenco completo, caricato una volta sola
  var comuneScelto = null;  // comune attualmente selezionato
  var evidenziato = -1;     // indice del suggerimento evidenziato da tastiera

  /* ---------------- tema ---------------- */

  function applicaTema(tema) {
    document.documentElement.setAttribute("data-theme", tema);
    el.logo.src = tema === "dark" ? "/brand/JetHR%20Logo%20White.svg" : "/brand/JetHR%20Logo%20Dark.svg";
    el.tema.textContent = tema === "dark" ? "Tema chiaro" : "Tema scuro";
    localStorage.setItem("tema", tema);
  }

  var temaSalvato = localStorage.getItem("tema");
  var preferenzaScura = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applicaTema(temaSalvato || (preferenzaScura ? "dark" : "light"));

  el.tema.addEventListener("click", function () {
    var attuale = document.documentElement.getAttribute("data-theme");
    applicaTema(attuale === "dark" ? "light" : "dark");
  });

  /* ---------------- autocomplete comuni ---------------- */

  fetch("/api/comuni")
    .then(function (r) { return r.json(); })
    .then(function (dati) {
      comuni = dati.comuni;
      el.comune.placeholder = "Cerca tra " + dati.totale.toLocaleString("it-IT") + " comuni";
    })
    .catch(function () {
      mostraErrore("Non riesco a caricare l'elenco dei comuni. Ricarica la pagina.");
    });

  function filtra(testo) {
    var cercato = testo.trim().toLowerCase();
    if (cercato.length < 2) return [];

    var risultati = [];
    for (var i = 0; i < comuni.length && risultati.length < MAX_SUGGERIMENTI; i++) {
      if (comuni[i].nome.toLowerCase().indexOf(cercato) === 0) risultati.push(comuni[i]);
    }
    // Se i match dall'inizio del nome non bastano, si completa con i match interni.
    for (var j = 0; j < comuni.length && risultati.length < MAX_SUGGERIMENTI; j++) {
      var nome = comuni[j].nome.toLowerCase();
      if (nome.indexOf(cercato) > 0) risultati.push(comuni[j]);
    }
    return risultati;
  }

  function mostraSuggerimenti(elenco) {
    el.suggerimenti.innerHTML = "";
    evidenziato = -1;

    if (!elenco.length) {
      el.suggerimenti.hidden = true;
      el.comune.setAttribute("aria-expanded", "false");
      return;
    }

    elenco.forEach(function (comune, indice) {
      var voce = document.createElement("li");
      voce.setAttribute("role", "option");
      voce.dataset.indice = String(indice);
      voce.innerHTML = comune.nome + " <small>(" + comune.provincia + ") &middot; " + comune.regione + "</small>";
      voce.addEventListener("mousedown", function (evento) {
        evento.preventDefault(); // evita il blur prima del click
        scegli(comune);
      });
      el.suggerimenti.appendChild(voce);
    });

    el.suggerimenti.hidden = false;
    el.comune.setAttribute("aria-expanded", "true");
  }

  function evidenzia(indice) {
    var voci = el.suggerimenti.querySelectorAll("li");
    if (!voci.length) return;
    if (evidenziato >= 0) voci[evidenziato].removeAttribute("aria-selected");
    evidenziato = (indice + voci.length) % voci.length;
    voci[evidenziato].setAttribute("aria-selected", "true");
    voci[evidenziato].scrollIntoView({ block: "nearest" });
  }

  function scegli(comune) {
    comuneScelto = comune;
    el.comune.value = comune.nome + " (" + comune.provincia + ")";
    el.derivato.textContent = "Addizionale regionale: " + comune.regione;
    el.derivato.classList.add("attivo");
    el.suggerimenti.hidden = true;
    el.comune.setAttribute("aria-expanded", "false");
  }

  el.comune.addEventListener("input", function () {
    comuneScelto = null;
    el.derivato.textContent = "La regione si compila da sola in base al comune scelto.";
    el.derivato.classList.remove("attivo");
    mostraSuggerimenti(filtra(el.comune.value));
  });

  el.comune.addEventListener("keydown", function (evento) {
    if (el.suggerimenti.hidden) return;
    if (evento.key === "ArrowDown") { evento.preventDefault(); evidenzia(evidenziato + 1); }
    else if (evento.key === "ArrowUp") { evento.preventDefault(); evidenzia(evidenziato - 1); }
    else if (evento.key === "Enter" && evidenziato >= 0) {
      evento.preventDefault();
      scegli(filtra(el.comune.value)[evidenziato]);
    } else if (evento.key === "Escape") {
      el.suggerimenti.hidden = true;
    }
  });

  el.comune.addEventListener("blur", function () {
    setTimeout(function () { el.suggerimenti.hidden = true; }, 120);
  });

  /* ---------------- invio e rendering ---------------- */

  function mostraErrore(messaggio) {
    el.errore.textContent = messaggio;
    el.errore.hidden = false;
  }

  el.modulo.addEventListener("submit", function (evento) {
    evento.preventDefault();
    el.errore.hidden = true;

    if (!comuneScelto) {
      mostraErrore("Seleziona un comune dall'elenco dei suggerimenti.");
      el.comune.focus();
      return;
    }

    el.calcola.disabled = true;
    fetch("/api/calcola", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ral: Number(el.ral.value),
        comune: comuneScelto.codice,
        mensilita: Number(el.mensilita.value)
      })
    })
      .then(function (risposta) {
        return risposta.json().then(function (dati) {
          if (!risposta.ok) throw new Error(dati.errore || "Calcolo non riuscito");
          return dati;
        });
      })
      .then(disegna)
      .catch(function (errore) { mostraErrore(errore.message); })
      .finally(function () { el.calcola.disabled = false; });
  });

  function disegna(dati) {
    el.risultati.hidden = false;

    el.nettoAnnuo.textContent = euro.format(dati.risultato.netto_annuo);
    el.nettoMensile.textContent = euro.format(dati.risultato.netto_mensile);
    el.etichettaMensilita.textContent = "(" + dati.input.mensilita + " mensilità)";
    el.tfr.textContent = euro.format(dati.risultato.tfr_annuo);

    disegnaWaterfall(dati.waterfall);
    disegnaDettaglio(dati);

    el.risultati.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /* Waterfall costruito con div proporzionali: ogni barra parte dal livello cumulato
   * precedente e si estende per il proprio importo. La scala e' la RAL, cioe' la voce
   * piu' alta del grafico. */
  function disegnaWaterfall(voci) {
    var scala = voci[0].importo;
    var cumulato = 0;
    el.waterfall.innerHTML = "";

    voci.forEach(function (voce, indice) {
      var estremo = indice === 0 || indice === voci.length - 1;
      var inizio, larghezza;

      if (estremo) {
        inizio = 0;
        larghezza = Math.abs(voce.importo);
        cumulato = voce.importo;
      } else {
        // Le sottrazioni si disegnano appese alla fine del cumulato precedente,
        // le aggiunte a partire da li' verso destra.
        larghezza = Math.abs(voce.importo);
        inizio = voce.importo < 0 ? cumulato - larghezza : cumulato;
        cumulato += voce.importo;
      }

      var riga = document.createElement("div");
      riga.className = "riga-waterfall" + (estremo ? " totale" : "");
      // Una voce nulla (tipico del trattamento integrativo sopra i 28.000) non disegna nessuna
      // barra: altrimenti resterebbe una lineetta colorata che sembra un importo non zero.
      var barra = voce.importo === 0
        ? '<span class="barra"></span>'
        : '<span class="barra"><i class="' + voce.tipo + '" style="left:' +
          (inizio / scala * 100) + "%;width:" + (larghezza / scala * 100) + '%"></i></span>';
      riga.innerHTML =
        '<span class="voce">' + voce.etichetta + "</span>" + barra +
        '<span class="importo">' + euro.format(voce.importo) + "</span>";
      el.waterfall.appendChild(riga);
    });
  }

  function disegnaDettaglio(dati) {
    var d = dati.dettaglio;
    var comune = dati.input.comune;
    var modalita = dati.aliquote.regionale_modalita === "unica"
      ? "aliquota unica sull'intero imponibile"
      : "aliquote per scaglioni";

    var voci = [
      ["RAL (imponibile previdenziale)", d.imponibile_previdenziale, null],
      ["Contributi INPS", -d.contributi_inps, percentuale.format(dati.aliquote.inps) + " della RAL"],
      ["Imponibile fiscale", d.imponibile_fiscale, "RAL al netto dei contributi"],
      ["IRPEF lorda", -d.irpef_lorda, "scaglioni 23% / 33% / 43%"],
      ["Detrazione lavoro dipendente", d.detrazione_lavoro_dipendente, "art. 13 TUIR"],
      ["IRPEF netta", -d.irpef_netta, "lorda meno detrazioni, mai negativa"],
      ["Addizionale regionale", -d.addizionale_regionale, comune.regione + ", " + modalita],
      ["Addizionale comunale", -d.addizionale_comunale,
        comune.nome + ": " + percentuale.format(dati.aliquote.comunale) + " (media derivata dai dati MEF 2024)"],
      ["Trattamento integrativo", d.trattamento_integrativo, "somma erogata, non trattenuta"],
      ["Netto annuo", dati.risultato.netto_annuo, null]
    ];

    el.dettaglio.innerHTML = "";
    voci.forEach(function (voce) {
      var riga = document.createElement("div");
      riga.className = "voce-dettaglio";
      riga.innerHTML =
        "<dt>" + voce[0] + (voce[2] ? '<span class="nota">' + voce[2] + "</span>" : "") + "</dt>" +
        "<dd>" + euroPreciso.format(voce[1]) + "</dd>";
      el.dettaglio.appendChild(riga);
    });
  }
})();
