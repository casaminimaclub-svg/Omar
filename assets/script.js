/* ============================================================
   SCRATCHY — Product Page (PREVIEW v4)
   Galleria, selettore bundle (+ regali per tier), bottone "trova
   la dose", CTA sticky, scroll. Vanilla JS, zero dipendenze.
   ============================================================ */
(function () {
  "use strict";
  var euro = function (n) { return "€" + n.toFixed(2).replace(".", ","); };

  /* ---------- GALLERIA (swipe touch + drag mouse + frecce + zampe) ---------- */
  var slides = document.getElementById("slides");
  var paws = document.getElementById("paws");
  if (slides && paws) {
    var pawList = Array.prototype.slice.call(paws.children);
    var count = slides.children.length;
    var current = 0;

    var setActive = function (i) {
      current = i;
      pawList.forEach(function (p, idx) { p.classList.toggle("active", idx === i); });
    };
    var goTo = function (i) {
      i = Math.max(0, Math.min(count - 1, i));
      slides.scrollTo({ left: i * slides.clientWidth, behavior: "smooth" });
      setActive(i);
    };

    // zampe
    pawList.forEach(function (btn, i) { btn.addEventListener("click", function () { goTo(i); }); });

    // frecce
    var prev = document.getElementById("gPrev");
    var next = document.getElementById("gNext");
    if (prev) prev.addEventListener("click", function () { goTo(current - 1); });
    if (next) next.addEventListener("click", function () { goTo(current + 1); });

    // swipe/scroll (touch nativo) -> aggiorna la zampa
    var t;
    slides.addEventListener("scroll", function () {
      clearTimeout(t);
      t = setTimeout(function () { setActive(Math.round(slides.scrollLeft / slides.clientWidth)); }, 60);
    }, { passive: true });

    // drag col MOUSE (il touch usa lo scroll nativo)
    var down = false, startX = 0, startScroll = 0, moved = false;
    slides.addEventListener("pointerdown", function (e) {
      if (e.pointerType !== "mouse") return;
      down = true; moved = false; startX = e.clientX; startScroll = slides.scrollLeft;
      slides.classList.add("dragging");
      try { slides.setPointerCapture(e.pointerId); } catch (err) {}
    });
    slides.addEventListener("pointermove", function (e) {
      if (!down) return;
      var dx = e.clientX - startX;
      if (Math.abs(dx) > 4) moved = true;
      slides.scrollLeft = startScroll - dx;
    });
    var endDrag = function () {
      if (!down) return;
      down = false; slides.classList.remove("dragging");
      goTo(Math.round(slides.scrollLeft / slides.clientWidth));
    };
    slides.addEventListener("pointerup", endDrag);
    slides.addEventListener("pointercancel", endDrag);
    slides.addEventListener("pointerleave", endDrag);
    // evita che il drag selezioni/trascini le immagini
    slides.addEventListener("dragstart", function (e) { e.preventDefault(); });
  }

  /* ---------- BUNDLE ---------- */
  var bundles = Array.prototype.slice.call(document.querySelectorAll(".bundle"));
  var sumRate = document.getElementById("sum-rate");
  var stickyName = document.getElementById("sticky-name");
  var giftHint = document.getElementById("gift-hint");
  var gifts = Array.prototype.slice.call(document.querySelectorAll("#gift-list .gift"));

  function applyGifts(tier) {
    var heroTiers = (tier === "hero" || tier === "value");
    gifts.forEach(function (g) {
      var need = g.getAttribute("data-min");
      var on = (need === "all") || heroTiers;
      g.classList.toggle("locked", !on);
    });
    if (giftHint) {
      giftHint.textContent = (tier === "entry")
        ? "Passa al Kit 2+2 per sbloccare la Guida P.R.E.D.A. e la spedizione prioritaria"
        : "Inclusi con il kit selezionato";
    }
  }

  /* "Cosa ricevi": contenuto per kit (base prodotto + eventuali regali) */
  var receiveList = document.getElementById("receive-list");
  var receiveTotal = document.getElementById("receive-total");
  var GIFT_GUIDA = { name: "Guida P.R.E.D.A.", img: "assets/img/regalo-guida.webp", gift: true, was: "€19,90" };
  var GIFT_SPED = { name: "Spedizione espressa", img: "assets/img/regalo-spedizione.webp", gift: true, was: "€6,99" };
  var GIFT_MAPPA = { name: "La Mappa dei Punti Caldi", img: "https://cdn.shopify.com/s/files/1/0784/4790/2905/files/guidaim.png?v=1783271594", gift: true, was: "€14,90" };
  var RECEIVE = {
    entry: [
      { name: "2 Scratchy", img: "assets/img/regalo-scratchy.webp" },
      GIFT_GUIDA
    ],
    hero: [
      { name: "4 Scratchy", img: "assets/img/regalo-scratchy.webp" },
      GIFT_GUIDA,
      GIFT_MAPPA,
      GIFT_SPED
    ],
    value: [
      { name: "6 Scratchy", img: "assets/img/regalo-scratchy.webp" },
      GIFT_GUIDA,
      GIFT_MAPPA,
      GIFT_SPED
    ]
  };
  /* valore totale barrato = somma dei valori (Scratchy a €29,90/cad + bonus) -> prezzo di oggi */
  var TOTALS = {
    entry: { was: "€79,70", now: "€34,90" },
    hero:  { was: "€161,39", now: "€59,90" },
    value: { was: "€221,19", now: "€89,90" }
  };
  function renderReceive(tier) {
    if (!receiveList) return;
    var items = RECEIVE[tier] || [];
    var html = "";
    items.forEach(function (it) {
      var ico = it.img
        ? '<span class="r-ico"><img src="' + it.img + '" alt="" /></span>'
        : '<span class="r-ico gift"><svg class="gi"><use href="#' + it.icon + '"/></svg></span>';
      var tag = it.gift
        ? '<span class="r-tag">' + (it.was ? '<s class="r-was">' + it.was + '</s>' : '') + '<span class="r-free">Gratis</span></span>'
        : '<span class="r-tag"><span class="r-incl">Incluso</span></span>';
      html += '<li>' + ico +
        '<span class="r-txt"><span class="r-name">' + it.name + '</span>' +
        (it.sub ? '<span class="r-sub">' + it.sub + '</span>' : '') + '</span>' + tag + '</li>';
    });
    receiveList.innerHTML = html;
    var t = TOTALS[tier];
    if (receiveTotal) {
      receiveTotal.innerHTML = t
        ? '<span class="rt-lbl">Valore totale</span> <s class="rt-was">' + t.was + '</s> <span class="rt-arrow">→</span> <span class="rt-now">oggi ' + t.now + '</span>'
        : "";
    }
    if (window.__retranslateEl) window.__retranslateEl(receiveList);
    else if (window.__retranslate) window.__retranslate();
  }

  function selectBundle(b) {
    bundles.forEach(function (x) { x.classList.remove("selected"); });
    b.classList.add("selected");
    var input = b.querySelector("input");
    if (input) input.checked = true;
    var price = parseFloat(b.getAttribute("data-price"));
    var name = b.getAttribute("data-name");
    if (sumRate) sumRate.textContent = euro(price / 3);
    /* La barra fissa promuove sempre il Kit 2+2 (il più scelto), non cambia con la selezione */
    renderReceive(b.getAttribute("data-tier"));
  }

  bundles.forEach(function (b) {
    b.addEventListener("click", function () { selectBundle(b); });
    var input = b.querySelector("input");
    if (input) input.addEventListener("change", function () { if (input.checked) selectBundle(b); });
  });
  var pre = document.querySelector(".bundle.selected") || bundles[0];
  if (pre) selectBundle(pre);

  /* ---------- "Trova la tua dose" -> evidenzia il consigliato ---------- */
  var quiz = document.getElementById("quiz-btn");
  if (quiz) {
    quiz.addEventListener("click", function () {
      var hero = document.querySelector('.bundle[data-tier="hero"]');
      if (!hero) return;
      selectBundle(hero);
      hero.scrollIntoView({ behavior: "smooth", block: "center" });
      hero.animate(
        [{ transform: "scale(1)" }, { transform: "scale(1.03)" }, { transform: "scale(1)" }],
        { duration: 600, easing: "ease-in-out" }
      );
    });
  }

  /* ---------- SCROLL verso la buy box ---------- */
  var buybox = document.querySelector(".buybox");
  function scrollToBuy(e) {
    if (e) e.preventDefault();
    if (buybox) buybox.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  ["sticky-cta", "final-cta", "mid-cta"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("click", scrollToBuy);
  });

  /* ---------- BOTTONE ACQUISTO -> apre il carrello (gestito nell'IIFE CARRELLO in fondo) ---------- */

  /* ---------- STICKY CTA ---------- */
  var sticky = document.getElementById("sticky");
  var heroSec = document.querySelector(".hero");
  function onScroll() {
    if (!sticky || !heroSec) return;
    sticky.classList.toggle("show", heroSec.getBoundingClientRect().bottom < 0);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();

  /* ---------- RIVELAZIONE ALLO SCROLL (stagger morbido) ---------- */
  /* Rispetta prefers-reduced-motion; se IO non c'è, non nasconde nulla. */
  try {
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce && "IntersectionObserver" in window) {
      var sel = [
        ".sintomo", ".fase", ".beneficio", ".review", ".why li", ".tchip", ".feat",
        ".bundle", ".ba-item", ".img-slot", ".ifc-stat .cell", ".gifts", ".guarantee-box",
        ".assoluzione", ".fonti", ".rev-score", ".faq details", "table.compare",
        ".close-duro .box", ".body-img", ".eyebrow"
      ].join(",");

      var els = Array.prototype.slice.call(document.querySelectorAll(sel));
      els.forEach(function (el) {
        // stagger in base alla posizione tra i fratelli (max ~6 step)
        var parent = el.parentElement;
        var idx = parent ? Array.prototype.indexOf.call(parent.children, el) : 0;
        el.dataset.revDelay = Math.min(idx, 6) * 60;
        el.classList.add("reveal");
      });

      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          var t = e.target;
          io.unobserve(t);
          var d = parseInt(t.dataset.revDelay, 10) || 0;
          // ritardo applicato all'aggiunta della classe -> niente delay sui futuri hover
          setTimeout(function () { t.classList.add("in"); }, d);
        });
      }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });

      els.forEach(function (el) { io.observe(el); });
    }
  } catch (err) { /* in caso di errore non blocchiamo la pagina */ }
})();

/* ============================================================
   I18N — selettore lingua/paese cliccabile + traduzione live.
   Demo anteprima (IT/EN/FR/ES/DE). Rileva la lingua del browser.
   ============================================================ */
(function () {
  "use strict";

  var I18N = {
    en: {
      "Spedizione": "Shipping", "gratuita": "free", "in tutta Italia": "across Italy",
      "Garanzia": "Guarantee", "60 giorni": "60 days", "soddisfatti o rimborsati": "money-back", "Scorte limitate": "Limited stock",
      "Terapia ambientale per gatti": "Environmental therapy for cats",
      "Amato da migliaia di proprietari italiani": "Loved by thousands of Italian owners",
      "Non è cattiveria: al tuo gatto manca ciò che un appartamento non può dargli.": "It’s not bad behaviour: your cat is missing what an apartment can’t give.",
      "gli ridà l'istinto — e a te la pace in casa.": "gives him back his instinct — and you peace at home.",
      "Agisce sulla causa (IFC)": "Targets the cause (IFC)", "Graffio orizzontale naturale": "Natural horizontal scratching",
      "Notti di nuovo silenziose": "Quiet nights again", "Protocollo guidato incluso": "Guided protocol included",
      "Disponibilità limitata": "Limited availability", "Le scorte di questo lotto stanno finendo": "This batch is almost sold out",
      "Paghi 1, ricevi 2": "Pay 1, get 2", "Paghi 2, ricevi 4": "Pay 2, get 4", "Paghi 3, ricevi 6": "Pay 3, get 6",
      "1 gratis": "1 free", "2 gratis": "2 free", "3 gratis": "3 free", "Il più scelto": "Most chosen",
      "€14,95/cad.": "€14.95/ea.", "€11,65/cad.": "€11.65/ea.",
      "Caratteristiche": "Features", "È questo il tuo gatto?": "Is this your cat?", "Garanzia e resi": "Guarantee & returns",
      "Aggiungi al carrello": "Add to cart", "Reso gratuito entro 60 giorni": "Free returns within 60 days",
      "Metodo su": "Method based on", "fonti di comportamento felino": "feline-behaviour sources",
      "Reso gratuito 60 giorni": "Free returns 60 days", "— il rischio è nostro": "— the risk is ours",
      "Cosa ricevi": "What you get", "Gratis": "Free", "Incluso": "Included", "Spedizione prioritaria": "Priority shipping",
      "Riconosci il tuo gatto?": "Do you recognise your cat?",
      "Sono le 3 di notte e il tuo gatto corre all'impazzata per tutta la casa.": "It’s 3 a.m. and your cat is racing through the whole house.",
      "E ti chiedi: «cosa sto sbagliando?»": "And you wonder: “what am I doing wrong?”",
      "Hai comprato il tiragraffi. Hai provato i giochi. Gli hai dato più attenzioni. E ami il tuo gatto. Eppure qualcosa continua a non funzionare — e nessuno ti ha mai spiegato perché.": "You bought the scratching post. You tried the toys. You gave more attention. And you love your cat. Yet something still isn’t working — and no one ever explained why.",
      "I mobili a brandelli": "Shredded furniture",
      "Il bracciolo del divano sfilacciato, i fili tirati, l'angolo della libreria graffiato a sangue. Non lo fa per dispetto: sta cercando di scaricare un istinto che non trova altra via.": "The frayed sofa arm, pulled threads, the bookshelf corner clawed raw. He’s not doing it out of spite: he’s trying to release an instinct with no other outlet.",
      "Le corse all'impazzata di notte": "Frantic night runs",
      "Scatta nel buio, corre, salta, rovescia tutto. E tu ti svegli di colpo, un'altra volta. Non è gioco: è l'istinto di caccia che esce così, perché di giorno non ha trovato sfogo.": "He bolts in the dark, runs, jumps, knocks everything over. And you wake with a start, again. It’s not play: it’s the hunting instinct coming out this way, because by day it found no outlet.",
      "Si lecca fino a spelarsi": "Over-grooming until bald",
      "Quelle chiazze senza pelo sulle zampe e sulla pancia. Si lecca in modo ossessivo. È un nervosismo che rivolge contro sé stesso quando la tensione non ha dove andare.": "Those bald patches on the legs and belly. He grooms obsessively. It’s a nervousness he turns against himself when the tension has nowhere to go.",
      "Spento, fermo, assente": "Switched off, still, absent",
      "Lo trovi fermo dietro la porta, immobile, con gli occhi nel vuoto. «È un gatto tranquillo», ti dici. Ma la calma non è sempre pace: a volte è solo un gatto che si è arreso.": "You find him still behind the door, motionless, eyes blank. “He’s a calm cat,” you tell yourself. But calm isn’t always peace: sometimes it’s just a cat who has given up.",
      "Perché tutto ciò che hai provato": "Why everything you’ve tried", "non è bastato": "wasn’t enough",
      "Non hai sbagliato a provarci. Hai sbagliato bersaglio — senza saperlo.": "You weren’t wrong to try. You aimed at the wrong target — without knowing.",
      "La causa nascosta": "The hidden cause",
      "Tutti e quattro i sintomi hanno una sola origine:": "All four symptoms share one origin:",
      "l'Ipostimolazione Felina Cronica": "Chronic Feline Understimulation",
      "stimoli/ora di cui il suo cervello ha bisogno": "stimuli/hour his brain needs",
      "stimoli/ora che offre un appartamento": "stimuli/hour an apartment offers",
      "E ora la cosa più importante: non è colpa tua. E non è colpa del tuo gatto.": "And now the most important thing: it’s not your fault. And it’s not your cat’s fault.",
      "È colpa di una casa che non è pensata per un cacciatore — e di nessuno che te l'avesse mai spiegato. Hai fatto tutto quello che ti avevano detto. Ti mancava solo questo.": "It’s the fault of a home not built for a hunter — and of no one ever explaining it to you. You did everything you were told. This was the only thing missing.",
      "Il protocollo": "The protocol",
      "Come SCRATCHY riequilibra il tuo gatto,": "How SCRATCHY rebalances your cat,", "passo dopo passo": "step by step",
      "Giorni 1–3": "Days 1–3", "Giorni 4–7": "Days 4–7", "Da qui in poi": "From here on",
      "Diagnosi": "Diagnosis", "Installazione": "Setup", "Consolidamento": "Consolidation",
      "Osservi il tuo gatto e riconosci i sintomi. Nessuno strumento necessario: solo guardare con occhi nuovi. Puoi iniziare oggi, prima che il pacco arrivi.": "You observe your cat and recognise the symptoms. No tools needed: just look with fresh eyes. You can start today, before the parcel arrives.",
      "Posizioni SCRATCHY nelle zone chiave della casa. Il gatto comincia a sfogare lì il suo istinto, per terra, invece che sui mobili.": "You place SCRATCHY in the key areas of the home. The cat starts releasing its instinct there, on the floor, instead of on the furniture.",
      "Il comportamento si riequilibra: le notti si calmano, i mobili respirano, il gatto torna sé stesso. Ogni gatto ha i suoi tempi — c'è chi cambia in pochi giorni, chi in qualche settimana.": "Behaviour rebalances: nights calm down, the furniture breathes, the cat becomes itself again. Every cat has its own pace — some change in a few days, some in a few weeks.",
      "Come cambia la tua casa": "How your home changes", "Cosa cambia davvero": "What really changes", "quando la causa viene curata": "when the cause is treated",
      "I tuoi mobili tornano salvi": "Your furniture is safe again", "L'istinto ha finalmente dove sfogarsi. Il divano smette di essere il bersaglio.": "The instinct finally has an outlet. The sofa stops being the target.",
      "Le notti tornano silenziose": "Nights go quiet again", "Le corse notturne si calmano quando di giorno l'istinto trova sfogo. Torni a dormire.": "Night runs calm down when the instinct finds an outlet by day. You sleep again.",
      "Un gatto sereno e appagato": "A calm, fulfilled cat", "Non più teso, non più spento: un gatto che sfoga il suo istinto ed è in pace. Coi suoi tempi, senza forzature.": "No longer tense, no longer switched off: a cat that releases its instinct and is at peace. At his own pace, no forcing.",
      "Finalmente la proprietaria che merita": "Finally the owner he deserves", "Quella che ha capito la causa e l'ha curata — non quella che rincorre il sintomo con l'ennesimo acquisto.": "The one who understood the cause and treated it — not the one chasing the symptom with yet another purchase.",
      "Prima": "Before", "Dopo": "After", "Senza Scratchy": "Without Scratchy", "Con Scratchy": "With Scratchy",
      "Prova Scratchy oggi": "Try Scratchy today",
      "Storie vere": "Real stories",
      "Migliaia di proprietari italiani hanno già": "Thousands of Italian owners have already", "ridato equilibrio al loro gatto": "brought balance back to their cat",
      "su migliaia di proprietari italiani": "across thousands of Italian owners", "Acquisto verificato": "Verified purchase",
      "Cura la causa, non il sintomo": "Treat the cause, not the symptom", "Perché SCRATCHY è diverso": "Why SCRATCHY is different", "da tutto ciò che hai già provato": "from everything you’ve already tried",
      "Cura la causa (IFC)": "Treats the cause (IFC)", "Scarica l'istinto in orizzontale": "Releases instinct horizontally", "Agisce su tutti e 4 i sintomi": "Acts on all 4 symptoms", "Risultati reali e duraturi": "Real, lasting results", "Garanzia 60 giorni": "60-day guarantee",
      "Tiragraffi": "Scratching post", "Giochi": "Toys", "Diffusori": "Diffusers", "Più attenzioni": "More attention",
      "Gli altri non hanno fallito perché cattivi. Hanno fallito perché curano il sintomo, mentre la causa resta.": "The others didn’t fail because they’re bad. They failed because they treat the symptom, while the cause remains.",
      "Te lo diciamo senza filtri": "We’ll tell you straight", "Hai ancora un dubbio?": "Still have a doubt?", "È normale.": "That’s normal.",
      "«Ma è solo cartone?»": "“But it’s just cardboard?”", "«E se il mio gatto lo ignora?»": "“What if my cat ignores it?”", "«Funziona con un gatto anziano o spento?»": "“Does it work with an old or listless cat?”", "«Quanto dura un pannello?»": "“How long does a panel last?”", "«E se non funziona?»": "“And if it doesn’t work?”", "«Quando arriva?»": "“When does it arrive?”", "«Posso pagarlo a rate?»": "“Can I pay in instalments?”",
      "Garanzia soddisfatti o rimborsati 60 giorni": "60-day money-back guarantee", "Il tuo gatto": "Your cat", "non migliorerà da solo": "won’t get better on its own",
      "Senza una via per scaricare l'istinto, i mobili continueranno a sfilacciarsi. Le notti resteranno spezzate. Il leccarsi non si fermerà. E quel senso di colpa — «sto sbagliando qualcosa» — resterà lì, ogni volta che lo guardi.": "Without a way to release the instinct, the furniture will keep fraying. The nights will stay broken. The over-grooming won’t stop. And that guilt — “am I doing something wrong” — will stay there, every time you look at him.",
      "Voglio provarlo": "I want to try it", "Vedi le offerte": "See the offers", "a partire da": "from",
      "Assistenza Clienti": "Customer Support", "Scratchy — terapia ambientale": "Scratchy — environmental therapy",
      "Contatti e tracciamento": "Contact & tracking", "Informativa sulla privacy": "Privacy policy", "Informativa spedizioni": "Shipping policy", "Informativa resi e rimborsi": "Returns & refunds policy", "Termini e condizioni": "Terms & conditions",
      "Scratchy riporta in casa la stimolazione che manca al gatto d'appartamento: una": "Scratchy brings back home the stimulation an indoor cat is missing: an", "terapia ambientale": "environmental therapy", "che agisce sulla causa del comportamento — non un giocattolo.": "that targets the cause of the behaviour — not a toy.",
      "© 2026 Scratchy™ · Tutti i diritti riservati": "© 2026 Scratchy™ · All rights reserved",
      "Le informazioni su questa pagina descrivono una cornice di terapia ambientale ancorata a fonti di comportamento felino e non costituiscono diagnosi o parere veterinario. In presenza di sintomi persistenti, consulta sempre il tuo veterinario.": "The information on this page describes an environmental-therapy framework grounded in feline-behaviour sources and does not constitute a diagnosis or veterinary advice. If symptoms persist, always consult your vet."
    },
    fr: {
      "Spedizione": "Livraison", "gratuita": "gratuite", "in tutta Italia": "dans toute l’Italie",
      "Garanzia": "Garantie", "60 giorni": "60 jours", "soddisfatti o rimborsati": "satisfait ou remboursé", "Scorte limitate": "Stock limité",
      "Terapia ambientale per gatti": "Thérapie environnementale pour chats",
      "Amato da migliaia di proprietari italiani": "Adopté par des milliers de propriétaires italiens",
      "Non è cattiveria: al tuo gatto manca ciò che un appartamento non può dargli.": "Ce n’est pas de la méchanceté : il manque à votre chat ce qu’un appartement ne peut pas offrir.",
      "gli ridà l'istinto — e a te la pace in casa.": "lui redonne son instinct — et à vous la paix à la maison.",
      "Agisce sulla causa (IFC)": "Agit sur la cause (IFC)", "Graffio orizzontale naturale": "Griffade horizontale naturelle",
      "Notti di nuovo silenziose": "Des nuits à nouveau calmes", "Protocollo guidato incluso": "Protocole guidé inclus",
      "Disponibilità limitata": "Disponibilité limitée", "Le scorte di questo lotto stanno finendo": "Le stock de ce lot s’épuise",
      "Paghi 1, ricevi 2": "Payez 1, recevez 2", "Paghi 2, ricevi 4": "Payez 2, recevez 4", "Paghi 3, ricevi 6": "Payez 3, recevez 6",
      "1 gratis": "1 offert", "2 gratis": "2 offerts", "3 gratis": "3 offerts", "Il più scelto": "Le plus choisi",
      "€14,95/cad.": "14,95 €/pièce", "€11,65/cad.": "11,65 €/pièce",
      "Caratteristiche": "Caractéristiques", "È questo il tuo gatto?": "Est-ce votre chat ?", "Garanzia e resi": "Garantie et retours",
      "Aggiungi al carrello": "Ajouter au panier", "Reso gratuito entro 60 giorni": "Retour gratuit sous 60 jours",
      "Metodo su": "Méthode fondée sur", "fonti di comportamento felino": "des sources de comportement félin",
      "Reso gratuito 60 giorni": "Retour gratuit 60 jours", "— il rischio è nostro": "— le risque est pour nous",
      "Cosa ricevi": "Ce que vous recevez", "Gratis": "Offert", "Incluso": "Inclus", "Spedizione prioritaria": "Livraison prioritaire",
      "Riconosci il tuo gatto?": "Reconnaissez-vous votre chat ?",
      "Sono le 3 di notte e il tuo gatto corre all'impazzata per tutta la casa.": "Il est 3 h du matin et votre chat court partout dans la maison.",
      "E ti chiedi: «cosa sto sbagliando?»": "Et vous vous demandez : « qu’est-ce que je fais de mal ? »",
      "Hai comprato il tiragraffi. Hai provato i giochi. Gli hai dato più attenzioni. E ami il tuo gatto. Eppure qualcosa continua a non funzionare — e nessuno ti ha mai spiegato perché.": "Vous avez acheté le griffoir. Vous avez essayé les jouets. Vous avez donné plus d’attention. Et vous aimez votre chat. Pourtant quelque chose ne va toujours pas — et personne ne vous a jamais expliqué pourquoi.",
      "I mobili a brandelli": "Les meubles en lambeaux",
      "Il bracciolo del divano sfilacciato, i fili tirati, l'angolo della libreria graffiato a sangue. Non lo fa per dispetto: sta cercando di scaricare un istinto che non trova altra via.": "L’accoudoir du canapé effiloché, les fils tirés, le coin de la bibliothèque griffé à vif. Ce n’est pas par vengeance : il essaie de libérer un instinct sans autre issue.",
      "Le corse all'impazzata di notte": "Les courses folles la nuit",
      "Scatta nel buio, corre, salta, rovescia tutto. E tu ti svegli di colpo, un'altra volta. Non è gioco: è l'istinto di caccia che esce così, perché di giorno non ha trovato sfogo.": "Il bondit dans le noir, court, saute, renverse tout. Et vous vous réveillez en sursaut, encore. Ce n’est pas un jeu : c’est l’instinct de chasse qui ressort ainsi, faute d’exutoire le jour.",
      "Si lecca fino a spelarsi": "Il se lèche jusqu’à s’arracher les poils",
      "Quelle chiazze senza pelo sulle zampe e sulla pancia. Si lecca in modo ossessivo. È un nervosismo che rivolge contro sé stesso quando la tensione non ha dove andare.": "Ces plaques sans poils sur les pattes et le ventre. Il se lèche de façon obsessionnelle. C’est une nervosité qu’il retourne contre lui-même quand la tension n’a nulle part où aller.",
      "Spento, fermo, assente": "Éteint, immobile, absent",
      "Lo trovi fermo dietro la porta, immobile, con gli occhi nel vuoto. «È un gatto tranquillo», ti dici. Ma la calma non è sempre pace: a volte è solo un gatto che si è arreso.": "Vous le trouvez immobile derrière la porte, le regard vide. « C’est un chat tranquille », vous dites-vous. Mais le calme n’est pas toujours la paix : parfois c’est juste un chat qui a renoncé.",
      "Perché tutto ciò che hai provato": "Pourquoi tout ce que vous avez essayé", "non è bastato": "n’a pas suffi",
      "Non hai sbagliato a provarci. Hai sbagliato bersaglio — senza saperlo.": "Vous n’avez pas eu tort d’essayer. Vous avez visé la mauvaise cible — sans le savoir.",
      "La causa nascosta": "La cause cachée",
      "Tutti e quattro i sintomi hanno una sola origine:": "Les quatre symptômes ont une seule origine :",
      "l'Ipostimolazione Felina Cronica": "l’Hypostimulation Féline Chronique",
      "stimoli/ora di cui il suo cervello ha bisogno": "stimuli/heure dont son cerveau a besoin",
      "stimoli/ora che offre un appartamento": "stimuli/heure qu’offre un appartement",
      "E ora la cosa più importante: non è colpa tua. E non è colpa del tuo gatto.": "Et maintenant le plus important : ce n’est pas votre faute. Et ce n’est pas la faute de votre chat.",
      "È colpa di una casa che non è pensata per un cacciatore — e di nessuno che te l'avesse mai spiegato. Hai fatto tutto quello che ti avevano detto. Ti mancava solo questo.": "C’est la faute d’une maison qui n’est pas pensée pour un chasseur — et de personne qui ne vous l’avait jamais expliqué. Vous avez fait tout ce qu’on vous avait dit. Il ne vous manquait que ça.",
      "Il protocollo": "Le protocole",
      "Come SCRATCHY riequilibra il tuo gatto,": "Comment SCRATCHY rééquilibre votre chat,", "passo dopo passo": "étape par étape",
      "Giorni 1–3": "Jours 1–3", "Giorni 4–7": "Jours 4–7", "Da qui in poi": "À partir de là",
      "Diagnosi": "Diagnostic", "Installazione": "Installation", "Consolidamento": "Consolidation",
      "Osservi il tuo gatto e riconosci i sintomi. Nessuno strumento necessario: solo guardare con occhi nuovi. Puoi iniziare oggi, prima che il pacco arrivi.": "Vous observez votre chat et reconnaissez les symptômes. Aucun outil nécessaire : juste regarder avec un œil neuf. Vous pouvez commencer aujourd’hui, avant l’arrivée du colis.",
      "Posizioni SCRATCHY nelle zone chiave della casa. Il gatto comincia a sfogare lì il suo istinto, per terra, invece che sui mobili.": "Vous placez SCRATCHY dans les zones clés de la maison. Le chat commence à y libérer son instinct, au sol, plutôt que sur les meubles.",
      "Il comportamento si riequilibra: le notti si calmano, i mobili respirano, il gatto torna sé stesso. Ogni gatto ha i suoi tempi — c'è chi cambia in pochi giorni, chi in qualche settimana.": "Le comportement se rééquilibre : les nuits se calment, les meubles respirent, le chat redevient lui-même. Chaque chat a son rythme — certains changent en quelques jours, d’autres en quelques semaines.",
      "Come cambia la tua casa": "Comment votre maison change", "Cosa cambia davvero": "Ce qui change vraiment", "quando la causa viene curata": "quand la cause est soignée",
      "I tuoi mobili tornano salvi": "Vos meubles sont à nouveau saufs", "L'istinto ha finalmente dove sfogarsi. Il divano smette di essere il bersaglio.": "L’instinct a enfin un exutoire. Le canapé n’est plus la cible.",
      "Le notti tornano silenziose": "Les nuits redeviennent calmes", "Le corse notturne si calmano quando di giorno l'istinto trova sfogo. Torni a dormire.": "Les courses nocturnes se calment quand l’instinct trouve un exutoire le jour. Vous dormez de nouveau.",
      "Un gatto sereno e appagato": "Un chat serein et épanoui", "Non più teso, non più spento: un gatto che sfoga il suo istinto ed è in pace. Coi suoi tempi, senza forzature.": "Plus tendu, plus éteint : un chat qui libère son instinct et est en paix. À son rythme, sans forcer.",
      "Finalmente la proprietaria che merita": "Enfin le maître qu’il mérite", "Quella che ha capito la causa e l'ha curata — non quella che rincorre il sintomo con l'ennesimo acquisto.": "Celui qui a compris la cause et l’a soignée — pas celui qui poursuit le symptôme avec un énième achat.",
      "Prima": "Avant", "Dopo": "Après", "Senza Scratchy": "Sans Scratchy", "Con Scratchy": "Avec Scratchy",
      "Prova Scratchy oggi": "Essayez Scratchy aujourd’hui",
      "Storie vere": "Histoires vraies",
      "Migliaia di proprietari italiani hanno già": "Des milliers de propriétaires italiens ont déjà", "ridato equilibrio al loro gatto": "rééquilibré leur chat",
      "su migliaia di proprietari italiani": "sur des milliers de propriétaires italiens", "Acquisto verificato": "Achat vérifié",
      "Cura la causa, non il sintomo": "Soignez la cause, pas le symptôme", "Perché SCRATCHY è diverso": "Pourquoi SCRATCHY est différent", "da tutto ciò che hai già provato": "de tout ce que vous avez déjà essayé",
      "Cura la causa (IFC)": "Soigne la cause (IFC)", "Scarica l'istinto in orizzontale": "Libère l’instinct à l’horizontale", "Agisce su tutti e 4 i sintomi": "Agit sur les 4 symptômes", "Risultati reali e duraturi": "Résultats réels et durables", "Garanzia 60 giorni": "Garantie 60 jours",
      "Tiragraffi": "Griffoir", "Giochi": "Jouets", "Diffusori": "Diffuseurs", "Più attenzioni": "Plus d’attention",
      "Gli altri non hanno fallito perché cattivi. Hanno fallito perché curano il sintomo, mentre la causa resta.": "Les autres n’ont pas échoué parce qu’ils sont mauvais. Ils ont échoué parce qu’ils soignent le symptôme, alors que la cause demeure.",
      "Te lo diciamo senza filtri": "On vous le dit sans filtre", "Hai ancora un dubbio?": "Encore un doute ?", "È normale.": "C’est normal.",
      "«Ma è solo cartone?»": "« Mais ce n’est que du carton ? »", "«E se il mio gatto lo ignora?»": "« Et si mon chat l’ignore ? »", "«Funziona con un gatto anziano o spento?»": "« Ça marche avec un chat âgé ou apathique ? »", "«Quanto dura un pannello?»": "« Combien de temps dure un panneau ? »", "«E se non funziona?»": "« Et si ça ne marche pas ? »", "«Quando arriva?»": "« Quand est-ce que ça arrive ? »", "«Posso pagarlo a rate?»": "« Puis-je payer en plusieurs fois ? »",
      "Garanzia soddisfatti o rimborsati 60 giorni": "Garantie satisfait ou remboursé 60 jours", "Il tuo gatto": "Votre chat", "non migliorerà da solo": "ne s’améliorera pas tout seul",
      "Senza una via per scaricare l'istinto, i mobili continueranno a sfilacciarsi. Le notti resteranno spezzate. Il leccarsi non si fermerà. E quel senso di colpa — «sto sbagliando qualcosa» — resterà lì, ogni volta che lo guardi.": "Sans moyen de libérer l’instinct, les meubles continueront de s’effilocher. Les nuits resteront hachées. Le léchage ne s’arrêtera pas. Et cette culpabilité — « je fais quelque chose de mal » — restera là, chaque fois que vous le regardez.",
      "Voglio provarlo": "Je veux l’essayer", "Vedi le offerte": "Voir les offres", "a partire da": "à partir de",
      "Assistenza Clienti": "Service Client", "Scratchy — terapia ambientale": "Scratchy — thérapie environnementale",
      "Contatti e tracciamento": "Contact et suivi", "Informativa sulla privacy": "Politique de confidentialité", "Informativa spedizioni": "Politique de livraison", "Informativa resi e rimborsi": "Politique de retours et remboursements", "Termini e condizioni": "Conditions générales",
      "Scratchy riporta in casa la stimolazione che manca al gatto d'appartamento: una": "Scratchy ramène à la maison la stimulation qui manque au chat d’appartement : une", "terapia ambientale": "thérapie environnementale", "che agisce sulla causa del comportamento — non un giocattolo.": "qui agit sur la cause du comportement — pas un jouet.",
      "© 2026 Scratchy™ · Tutti i diritti riservati": "© 2026 Scratchy™ · Tous droits réservés",
      "Le informazioni su questa pagina descrivono una cornice di terapia ambientale ancorata a fonti di comportamento felino e non costituiscono diagnosi o parere veterinario. In presenza di sintomi persistenti, consulta sempre il tuo veterinario.": "Les informations de cette page décrivent un cadre de thérapie environnementale fondé sur des sources de comportement félin et ne constituent ni un diagnostic ni un avis vétérinaire. En cas de symptômes persistants, consultez toujours votre vétérinaire."
    },
    es: {
      "Spedizione": "Envío", "gratuita": "gratis", "in tutta Italia": "en toda Italia",
      "Garanzia": "Garantía", "60 giorni": "60 días", "soddisfatti o rimborsati": "satisfecho o reembolsado", "Scorte limitate": "Stock limitado",
      "Terapia ambientale per gatti": "Terapia ambiental para gatos",
      "Amato da migliaia di proprietari italiani": "Amado por miles de dueños italianos",
      "Non è cattiveria: al tuo gatto manca ciò che un appartamento non può dargli.": "No es maldad: a tu gato le falta lo que un piso no puede darle.",
      "gli ridà l'istinto — e a te la pace in casa.": "le devuelve el instinto — y a ti la paz en casa.",
      "Agisce sulla causa (IFC)": "Actúa sobre la causa (IFC)", "Graffio orizzontale naturale": "Rascado horizontal natural",
      "Notti di nuovo silenziose": "Noches tranquilas de nuevo", "Protocollo guidato incluso": "Protocolo guiado incluido",
      "Disponibilità limitata": "Disponibilidad limitada", "Le scorte di questo lotto stanno finendo": "Las existencias de este lote se están agotando",
      "Paghi 1, ricevi 2": "Paga 1, recibe 2", "Paghi 2, ricevi 4": "Paga 2, recibe 4", "Paghi 3, ricevi 6": "Paga 3, recibe 6",
      "1 gratis": "1 gratis", "2 gratis": "2 gratis", "3 gratis": "3 gratis", "Il più scelto": "El más elegido",
      "€14,95/cad.": "14,95 €/ud.", "€11,65/cad.": "11,65 €/ud.",
      "Caratteristiche": "Características", "È questo il tuo gatto?": "¿Es este tu gato?", "Garanzia e resi": "Garantía y devoluciones",
      "Aggiungi al carrello": "Añadir al carrito", "Reso gratuito entro 60 giorni": "Devolución gratis en 60 días",
      "Metodo su": "Método basado en", "fonti di comportamento felino": "fuentes de comportamiento felino",
      "Reso gratuito 60 giorni": "Devolución gratis 60 días", "— il rischio è nostro": "— el riesgo es nuestro",
      "Cosa ricevi": "Qué recibes", "Gratis": "Gratis", "Incluso": "Incluido", "Spedizione prioritaria": "Envío prioritario",
      "Riconosci il tuo gatto?": "¿Reconoces a tu gato?",
      "Sono le 3 di notte e il tuo gatto corre all'impazzata per tutta la casa.": "Son las 3 de la mañana y tu gato corre como loco por toda la casa.",
      "E ti chiedi: «cosa sto sbagliando?»": "Y te preguntas: «¿qué estoy haciendo mal?»",
      "Hai comprato il tiragraffi. Hai provato i giochi. Gli hai dato più attenzioni. E ami il tuo gatto. Eppure qualcosa continua a non funzionare — e nessuno ti ha mai spiegato perché.": "Compraste el rascador. Probaste los juguetes. Le diste más atención. Y amas a tu gato. Aun así algo sigue sin funcionar — y nadie te explicó por qué.",
      "I mobili a brandelli": "Los muebles destrozados",
      "Il bracciolo del divano sfilacciato, i fili tirati, l'angolo della libreria graffiato a sangue. Non lo fa per dispetto: sta cercando di scaricare un istinto che non trova altra via.": "El brazo del sofá deshilachado, los hilos tirados, la esquina de la estantería arañada a fondo. No lo hace por rencor: intenta liberar un instinto que no encuentra otra salida.",
      "Le corse all'impazzata di notte": "Las carreras locas de noche",
      "Scatta nel buio, corre, salta, rovescia tutto. E tu ti svegli di colpo, un'altra volta. Non è gioco: è l'istinto di caccia che esce così, perché di giorno non ha trovato sfogo.": "Salta en la oscuridad, corre, brinca, lo tira todo. Y te despiertas de golpe, otra vez. No es juego: es el instinto de caza que sale así, porque de día no encontró desahogo.",
      "Si lecca fino a spelarsi": "Se lame hasta pelarse",
      "Quelle chiazze senza pelo sulle zampe e sulla pancia. Si lecca in modo ossessivo. È un nervosismo che rivolge contro sé stesso quando la tensione non ha dove andare.": "Esas zonas sin pelo en las patas y la barriga. Se lame de forma obsesiva. Es un nerviosismo que vuelve contra sí mismo cuando la tensión no tiene salida.",
      "Spento, fermo, assente": "Apagado, quieto, ausente",
      "Lo trovi fermo dietro la porta, immobile, con gli occhi nel vuoto. «È un gatto tranquillo», ti dici. Ma la calma non è sempre pace: a volte è solo un gatto che si è arreso.": "Lo encuentras quieto tras la puerta, inmóvil, con la mirada perdida. «Es un gato tranquilo», te dices. Pero la calma no siempre es paz: a veces es solo un gato que se ha rendido.",
      "Perché tutto ciò che hai provato": "Por qué todo lo que has probado", "non è bastato": "no ha bastado",
      "Non hai sbagliato a provarci. Hai sbagliato bersaglio — senza saperlo.": "No te equivocaste al intentarlo. Apuntaste al objetivo equivocado — sin saberlo.",
      "La causa nascosta": "La causa oculta",
      "Tutti e quattro i sintomi hanno una sola origine:": "Los cuatro síntomas tienen un solo origen:",
      "l'Ipostimolazione Felina Cronica": "la Hipoestimulación Felina Crónica",
      "stimoli/ora di cui il suo cervello ha bisogno": "estímulos/hora que necesita su cerebro",
      "stimoli/ora che offre un appartamento": "estímulos/hora que ofrece un piso",
      "E ora la cosa più importante: non è colpa tua. E non è colpa del tuo gatto.": "Y ahora lo más importante: no es culpa tuya. Y no es culpa de tu gato.",
      "È colpa di una casa che non è pensata per un cacciatore — e di nessuno che te l'avesse mai spiegato. Hai fatto tutto quello che ti avevano detto. Ti mancava solo questo.": "Es culpa de una casa que no está pensada para un cazador — y de que nadie te lo hubiera explicado. Hiciste todo lo que te dijeron. Solo te faltaba esto.",
      "Il protocollo": "El protocolo",
      "Come SCRATCHY riequilibra il tuo gatto,": "Cómo SCRATCHY reequilibra a tu gato,", "passo dopo passo": "paso a paso",
      "Giorni 1–3": "Días 1–3", "Giorni 4–7": "Días 4–7", "Da qui in poi": "De aquí en adelante",
      "Diagnosi": "Diagnóstico", "Installazione": "Instalación", "Consolidamento": "Consolidación",
      "Osservi il tuo gatto e riconosci i sintomi. Nessuno strumento necessario: solo guardare con occhi nuovi. Puoi iniziare oggi, prima che il pacco arrivi.": "Observas a tu gato y reconoces los síntomas. Sin herramientas: solo mirar con ojos nuevos. Puedes empezar hoy, antes de que llegue el paquete.",
      "Posizioni SCRATCHY nelle zone chiave della casa. Il gatto comincia a sfogare lì il suo istinto, per terra, invece che sui mobili.": "Colocas SCRATCHY en las zonas clave de la casa. El gato empieza a desahogar allí su instinto, en el suelo, en vez de en los muebles.",
      "Il comportamento si riequilibra: le notti si calmano, i mobili respirano, il gatto torna sé stesso. Ogni gatto ha i suoi tempi — c'è chi cambia in pochi giorni, chi in qualche settimana.": "El comportamiento se reequilibra: las noches se calman, los muebles respiran, el gato vuelve a ser él mismo. Cada gato tiene su ritmo — algunos cambian en pocos días, otros en unas semanas.",
      "Come cambia la tua casa": "Cómo cambia tu casa", "Cosa cambia davvero": "Qué cambia de verdad", "quando la causa viene curata": "cuando se trata la causa",
      "I tuoi mobili tornano salvi": "Tus muebles vuelven a salvo", "L'istinto ha finalmente dove sfogarsi. Il divano smette di essere il bersaglio.": "El instinto por fin tiene dónde desahogarse. El sofá deja de ser el objetivo.",
      "Le notti tornano silenziose": "Las noches vuelven a ser tranquilas", "Le corse notturne si calmano quando di giorno l'istinto trova sfogo. Torni a dormire.": "Las carreras nocturnas se calman cuando de día el instinto se desahoga. Vuelves a dormir.",
      "Un gatto sereno e appagato": "Un gato sereno y satisfecho", "Non più teso, non più spento: un gatto che sfoga il suo istinto ed è in pace. Coi suoi tempi, senza forzature.": "Ya no tenso, ya no apagado: un gato que desahoga su instinto y está en paz. A su ritmo, sin forzar.",
      "Finalmente la proprietaria che merita": "Por fin el dueño que merece", "Quella che ha capito la causa e l'ha curata — non quella che rincorre il sintomo con l'ennesimo acquisto.": "El que entendió la causa y la trató — no el que persigue el síntoma con otra compra más.",
      "Prima": "Antes", "Dopo": "Después", "Senza Scratchy": "Sin Scratchy", "Con Scratchy": "Con Scratchy",
      "Prova Scratchy oggi": "Prueba Scratchy hoy",
      "Storie vere": "Historias reales",
      "Migliaia di proprietari italiani hanno già": "Miles de dueños italianos ya han", "ridato equilibrio al loro gatto": "devuelto el equilibrio a su gato",
      "su migliaia di proprietari italiani": "entre miles de dueños italianos", "Acquisto verificato": "Compra verificada",
      "Cura la causa, non il sintomo": "Trata la causa, no el síntoma", "Perché SCRATCHY è diverso": "Por qué SCRATCHY es diferente", "da tutto ciò che hai già provato": "de todo lo que ya has probado",
      "Cura la causa (IFC)": "Trata la causa (IFC)", "Scarica l'istinto in orizzontale": "Libera el instinto en horizontal", "Agisce su tutti e 4 i sintomi": "Actúa sobre los 4 síntomas", "Risultati reali e duraturi": "Resultados reales y duraderos", "Garanzia 60 giorni": "Garantía 60 días",
      "Tiragraffi": "Rascador", "Giochi": "Juguetes", "Diffusori": "Difusores", "Più attenzioni": "Más atención",
      "Gli altri non hanno fallito perché cattivi. Hanno fallito perché curano il sintomo, mentre la causa resta.": "Los demás no fallaron por ser malos. Fallaron porque tratan el síntoma, mientras la causa permanece.",
      "Te lo diciamo senza filtri": "Te lo decimos sin filtros", "Hai ancora un dubbio?": "¿Aún tienes dudas?", "È normale.": "Es normal.",
      "«Ma è solo cartone?»": "«¿Pero es solo cartón?»", "«E se il mio gatto lo ignora?»": "«¿Y si mi gato lo ignora?»", "«Funziona con un gatto anziano o spento?»": "«¿Funciona con un gato mayor o apático?»", "«Quanto dura un pannello?»": "«¿Cuánto dura un panel?»", "«E se non funziona?»": "«¿Y si no funciona?»", "«Quando arriva?»": "«¿Cuándo llega?»", "«Posso pagarlo a rate?»": "«¿Puedo pagar a plazos?»",
      "Garanzia soddisfatti o rimborsati 60 giorni": "Garantía satisfecho o reembolsado 60 días", "Il tuo gatto": "Tu gato", "non migliorerà da solo": "no mejorará solo",
      "Senza una via per scaricare l'istinto, i mobili continueranno a sfilacciarsi. Le notti resteranno spezzate. Il leccarsi non si fermerà. E quel senso di colpa — «sto sbagliando qualcosa» — resterà lì, ogni volta che lo guardi.": "Sin una vía para liberar el instinto, los muebles seguirán deshilachándose. Las noches seguirán rotas. El lamido no se detendrá. Y esa culpa — «estoy haciendo algo mal» — seguirá ahí, cada vez que lo miras.",
      "Voglio provarlo": "Quiero probarlo", "Vedi le offerte": "Ver las ofertas", "a partire da": "desde",
      "Assistenza Clienti": "Atención al Cliente", "Scratchy — terapia ambientale": "Scratchy — terapia ambiental",
      "Contatti e tracciamento": "Contacto y seguimiento", "Informativa sulla privacy": "Política de privacidad", "Informativa spedizioni": "Política de envíos", "Informativa resi e rimborsi": "Política de devoluciones y reembolsos", "Termini e condizioni": "Términos y condiciones",
      "Scratchy riporta in casa la stimolazione che manca al gatto d'appartamento: una": "Scratchy devuelve a casa la estimulación que le falta al gato de piso: una", "terapia ambientale": "terapia ambiental", "che agisce sulla causa del comportamento — non un giocattolo.": "que actúa sobre la causa del comportamiento — no un juguete.",
      "© 2026 Scratchy™ · Tutti i diritti riservati": "© 2026 Scratchy™ · Todos los derechos reservados",
      "Le informazioni su questa pagina descrivono una cornice di terapia ambientale ancorata a fonti di comportamento felino e non costituiscono diagnosi o parere veterinario. In presenza di sintomi persistenti, consulta sempre il tuo veterinario.": "La información de esta página describe un marco de terapia ambiental basado en fuentes de comportamiento felino y no constituye diagnóstico ni consejo veterinario. Si los síntomas persisten, consulta siempre a tu veterinario."
    },
    de: {
      "Spedizione": "Versand", "gratuita": "kostenlos", "in tutta Italia": "in ganz Italien",
      "Garanzia": "Garantie", "60 giorni": "60 Tage", "soddisfatti o rimborsati": "Geld zurück", "Scorte limitate": "Begrenzter Vorrat",
      "Terapia ambientale per gatti": "Umwelttherapie für Katzen",
      "Amato da migliaia di proprietari italiani": "Von Tausenden italienischen Besitzern geliebt",
      "Non è cattiveria: al tuo gatto manca ciò che un appartamento non può dargli.": "Es ist keine Bosheit: deiner Katze fehlt, was eine Wohnung nicht bieten kann.",
      "gli ridà l'istinto — e a te la pace in casa.": "gibt ihm seinen Instinkt zurück — und dir Ruhe zu Hause.",
      "Agisce sulla causa (IFC)": "Wirkt auf die Ursache (IFC)", "Graffio orizzontale naturale": "Natürliches horizontales Kratzen",
      "Notti di nuovo silenziose": "Wieder ruhige Nächte", "Protocollo guidato incluso": "Geführtes Protokoll inklusive",
      "Disponibilità limitata": "Begrenzte Verfügbarkeit", "Le scorte di questo lotto stanno finendo": "Der Vorrat dieser Charge geht zur Neige",
      "Paghi 1, ricevi 2": "Zahle 1, erhalte 2", "Paghi 2, ricevi 4": "Zahle 2, erhalte 4", "Paghi 3, ricevi 6": "Zahle 3, erhalte 6",
      "1 gratis": "1 gratis", "2 gratis": "2 gratis", "3 gratis": "3 gratis", "Il più scelto": "Am meisten gewählt",
      "€14,95/cad.": "14,95 €/St.", "€11,65/cad.": "11,65 €/St.",
      "Caratteristiche": "Eigenschaften", "È questo il tuo gatto?": "Ist das deine Katze?", "Garanzia e resi": "Garantie & Rückgabe",
      "Aggiungi al carrello": "In den Warenkorb", "Reso gratuito entro 60 giorni": "Kostenlose Rückgabe innerhalb 60 Tagen",
      "Metodo su": "Methode basiert auf", "fonti di comportamento felino": "Quellen zum Katzenverhalten",
      "Reso gratuito 60 giorni": "Kostenlose Rückgabe 60 Tage", "— il rischio è nostro": "— das Risiko liegt bei uns",
      "Cosa ricevi": "Das erhältst du", "Gratis": "Gratis", "Incluso": "Inklusive", "Spedizione prioritaria": "Prioritätsversand",
      "Riconosci il tuo gatto?": "Erkennst du deine Katze?",
      "Sono le 3 di notte e il tuo gatto corre all'impazzata per tutta la casa.": "Es ist 3 Uhr nachts und deine Katze rast durchs ganze Haus.",
      "E ti chiedi: «cosa sto sbagliando?»": "Und du fragst dich: «was mache ich falsch?»",
      "Hai comprato il tiragraffi. Hai provato i giochi. Gli hai dato più attenzioni. E ami il tuo gatto. Eppure qualcosa continua a non funzionare — e nessuno ti ha mai spiegato perché.": "Du hast den Kratzbaum gekauft. Du hast die Spielzeuge probiert. Du hast mehr Aufmerksamkeit geschenkt. Und du liebst deine Katze. Trotzdem stimmt etwas nicht — und niemand hat dir je erklärt, warum.",
      "I mobili a brandelli": "Zerfetzte Möbel",
      "Il bracciolo del divano sfilacciato, i fili tirati, l'angolo della libreria graffiato a sangue. Non lo fa per dispetto: sta cercando di scaricare un istinto che non trova altra via.": "Die zerfranste Sofalehne, gezogene Fäden, die blank gekratzte Regalecke. Er tut es nicht aus Trotz: Er versucht, einen Instinkt loszuwerden, der kein anderes Ventil findet.",
      "Le corse all'impazzata di notte": "Wilde Nachtläufe",
      "Scatta nel buio, corre, salta, rovescia tutto. E tu ti svegli di colpo, un'altra volta. Non è gioco: è l'istinto di caccia che esce così, perché di giorno non ha trovato sfogo.": "Er schießt im Dunkeln los, rennt, springt, wirft alles um. Und du wachst wieder erschrocken auf. Das ist kein Spiel: Es ist der Jagdinstinkt, der sich so entlädt, weil er tagsüber kein Ventil fand.",
      "Si lecca fino a spelarsi": "Leckt sich kahl",
      "Quelle chiazze senza pelo sulle zampe e sulla pancia. Si lecca in modo ossessivo. È un nervosismo che rivolge contro sé stesso quando la tensione non ha dove andare.": "Diese kahlen Stellen an Beinen und Bauch. Er leckt sich zwanghaft. Es ist eine Nervosität, die er gegen sich selbst richtet, wenn die Anspannung kein Ventil hat.",
      "Spento, fermo, assente": "Teilnahmslos, reglos, abwesend",
      "Lo trovi fermo dietro la porta, immobile, con gli occhi nel vuoto. «È un gatto tranquillo», ti dici. Ma la calma non è sempre pace: a volte è solo un gatto che si è arreso.": "Du findest ihn reglos hinter der Tür, mit leerem Blick. «Sie ist eine ruhige Katze», sagst du dir. Aber Ruhe ist nicht immer Frieden: Manchmal ist es nur eine Katze, die aufgegeben hat.",
      "Perché tutto ciò che hai provato": "Warum alles, was du versucht hast", "non è bastato": "nicht gereicht hat",
      "Non hai sbagliato a provarci. Hai sbagliato bersaglio — senza saperlo.": "Du hast nicht falsch gehandelt, es zu versuchen. Du hast nur das falsche Ziel anvisiert — ohne es zu wissen.",
      "La causa nascosta": "Die verborgene Ursache",
      "Tutti e quattro i sintomi hanno una sola origine:": "Alle vier Symptome haben einen Ursprung:",
      "l'Ipostimolazione Felina Cronica": "die chronische feline Unterstimulation",
      "stimoli/ora di cui il suo cervello ha bisogno": "Reize/Stunde, die sein Gehirn braucht",
      "stimoli/ora che offre un appartamento": "Reize/Stunde, die eine Wohnung bietet",
      "E ora la cosa più importante: non è colpa tua. E non è colpa del tuo gatto.": "Und jetzt das Wichtigste: Es ist nicht deine Schuld. Und es ist nicht die Schuld deiner Katze.",
      "È colpa di una casa che non è pensata per un cacciatore — e di nessuno che te l'avesse mai spiegato. Hai fatto tutto quello che ti avevano detto. Ti mancava solo questo.": "Es ist die Schuld eines Zuhauses, das nicht für einen Jäger gemacht ist — und dass es dir nie jemand erklärt hat. Du hast alles getan, was man dir gesagt hat. Nur das hat gefehlt.",
      "Il protocollo": "Das Protokoll",
      "Come SCRATCHY riequilibra il tuo gatto,": "Wie SCRATCHY deine Katze wieder ins Gleichgewicht bringt,", "passo dopo passo": "Schritt für Schritt",
      "Giorni 1–3": "Tage 1–3", "Giorni 4–7": "Tage 4–7", "Da qui in poi": "Ab jetzt",
      "Diagnosi": "Diagnose", "Installazione": "Installation", "Consolidamento": "Festigung",
      "Osservi il tuo gatto e riconosci i sintomi. Nessuno strumento necessario: solo guardare con occhi nuovi. Puoi iniziare oggi, prima che il pacco arrivi.": "Du beobachtest deine Katze und erkennst die Symptome. Kein Werkzeug nötig: einfach mit neuen Augen hinsehen. Du kannst heute beginnen, bevor das Paket ankommt.",
      "Posizioni SCRATCHY nelle zone chiave della casa. Il gatto comincia a sfogare lì il suo istinto, per terra, invece che sui mobili.": "Du platzierst SCRATCHY an den wichtigsten Stellen im Haus. Die Katze lebt dort ihren Instinkt aus, am Boden, statt an den Möbeln.",
      "Il comportamento si riequilibra: le notti si calmano, i mobili respirano, il gatto torna sé stesso. Ogni gatto ha i suoi tempi — c'è chi cambia in pochi giorni, chi in qualche settimana.": "Das Verhalten kommt wieder ins Gleichgewicht: Die Nächte beruhigen sich, die Möbel atmen auf, die Katze wird wieder sie selbst. Jede Katze hat ihr Tempo — manche ändern sich in wenigen Tagen, manche in einigen Wochen.",
      "Come cambia la tua casa": "Wie sich dein Zuhause verändert", "Cosa cambia davvero": "Was sich wirklich ändert", "quando la causa viene curata": "wenn die Ursache behandelt wird",
      "I tuoi mobili tornano salvi": "Deine Möbel sind wieder sicher", "L'istinto ha finalmente dove sfogarsi. Il divano smette di essere il bersaglio.": "Der Instinkt hat endlich ein Ventil. Das Sofa ist nicht mehr das Ziel.",
      "Le notti tornano silenziose": "Die Nächte werden wieder ruhig", "Le corse notturne si calmano quando di giorno l'istinto trova sfogo. Torni a dormire.": "Die nächtlichen Läufe lassen nach, wenn der Instinkt tagsüber ein Ventil findet. Du schläfst wieder.",
      "Un gatto sereno e appagato": "Eine ruhige, zufriedene Katze", "Non più teso, non più spento: un gatto che sfoga il suo istinto ed è in pace. Coi suoi tempi, senza forzature.": "Nicht mehr angespannt, nicht mehr teilnahmslos: eine Katze, die ihren Instinkt auslebt und in Frieden ist. Im eigenen Tempo, ohne Zwang.",
      "Finalmente la proprietaria che merita": "Endlich der Halter, den sie verdient", "Quella che ha capito la causa e l'ha curata — non quella che rincorre il sintomo con l'ennesimo acquisto.": "Der, der die Ursache verstanden und behandelt hat — nicht der, der dem Symptom mit dem nächsten Kauf hinterherjagt.",
      "Prima": "Vorher", "Dopo": "Nachher", "Senza Scratchy": "Ohne Scratchy", "Con Scratchy": "Mit Scratchy",
      "Prova Scratchy oggi": "Probiere Scratchy heute",
      "Storie vere": "Echte Geschichten",
      "Migliaia di proprietari italiani hanno già": "Tausende italienische Besitzer haben bereits", "ridato equilibrio al loro gatto": "ihrer Katze das Gleichgewicht zurückgegeben",
      "su migliaia di proprietari italiani": "über Tausende italienische Besitzer", "Acquisto verificato": "Verifizierter Kauf",
      "Cura la causa, non il sintomo": "Behandle die Ursache, nicht das Symptom", "Perché SCRATCHY è diverso": "Warum SCRATCHY anders ist", "da tutto ciò che hai già provato": "von allem, was du schon versucht hast",
      "Cura la causa (IFC)": "Behandelt die Ursache (IFC)", "Scarica l'istinto in orizzontale": "Lässt den Instinkt horizontal aus", "Agisce su tutti e 4 i sintomi": "Wirkt auf alle 4 Symptome", "Risultati reali e duraturi": "Echte, dauerhafte Ergebnisse", "Garanzia 60 giorni": "60-Tage-Garantie",
      "Tiragraffi": "Kratzbaum", "Giochi": "Spielzeug", "Diffusori": "Diffusoren", "Più attenzioni": "Mehr Aufmerksamkeit",
      "Gli altri non hanno fallito perché cattivi. Hanno fallito perché curano il sintomo, mentre la causa resta.": "Die anderen sind nicht gescheitert, weil sie schlecht sind. Sie sind gescheitert, weil sie das Symptom behandeln, während die Ursache bleibt.",
      "Te lo diciamo senza filtri": "Wir sagen es dir ehrlich", "Hai ancora un dubbio?": "Noch Zweifel?", "È normale.": "Das ist normal.",
      "«Ma è solo cartone?»": "«Aber es ist nur Karton?»", "«E se il mio gatto lo ignora?»": "«Und wenn meine Katze es ignoriert?»", "«Funziona con un gatto anziano o spento?»": "«Funktioniert es bei einer alten oder trägen Katze?»", "«Quanto dura un pannello?»": "«Wie lange hält eine Platte?»", "«E se non funziona?»": "«Und wenn es nicht funktioniert?»", "«Quando arriva?»": "«Wann kommt es an?»", "«Posso pagarlo a rate?»": "«Kann ich in Raten zahlen?»",
      "Garanzia soddisfatti o rimborsati 60 giorni": "60 Tage Geld-zurück-Garantie", "Il tuo gatto": "Deine Katze", "non migliorerà da solo": "wird nicht von allein besser",
      "Senza una via per scaricare l'istinto, i mobili continueranno a sfilacciarsi. Le notti resteranno spezzate. Il leccarsi non si fermerà. E quel senso di colpa — «sto sbagliando qualcosa» — resterà lì, ogni volta che lo guardi.": "Ohne ein Ventil für den Instinkt werden die Möbel weiter zerfasern. Die Nächte bleiben zerrissen. Das Lecken hört nicht auf. Und dieses Schuldgefühl — «mache ich etwas falsch» — bleibt da, jedes Mal, wenn du sie ansiehst.",
      "Voglio provarlo": "Ich will es ausprobieren", "Vedi le offerte": "Angebote ansehen", "a partire da": "ab",
      "Assistenza Clienti": "Kundenservice", "Scratchy — terapia ambientale": "Scratchy — Umwelttherapie",
      "Contatti e tracciamento": "Kontakt & Sendungsverfolgung", "Informativa sulla privacy": "Datenschutz", "Informativa spedizioni": "Versandinformationen", "Informativa resi e rimborsi": "Rückgabe & Erstattung", "Termini e condizioni": "AGB",
      "Scratchy riporta in casa la stimolazione che manca al gatto d'appartamento: una": "Scratchy bringt die Stimulation zurück, die einer Wohnungskatze fehlt: eine", "terapia ambientale": "Umwelttherapie", "che agisce sulla causa del comportamento — non un giocattolo.": "die auf die Ursache des Verhaltens wirkt — kein Spielzeug.",
      "© 2026 Scratchy™ · Tutti i diritti riservati": "© 2026 Scratchy™ · Alle Rechte vorbehalten",
      "Le informazioni su questa pagina descrivono una cornice di terapia ambientale ancorata a fonti di comportamento felino e non costituiscono diagnosi o parere veterinario. In presenza di sintomi persistenti, consulta sempre il tuo veterinario.": "Die Informationen auf dieser Seite beschreiben einen Rahmen der Umwelttherapie auf Basis von Quellen zum Katzenverhalten und stellen keine Diagnose oder tierärztliche Beratung dar. Bei anhaltenden Symptomen konsultiere immer deinen Tierarzt."
    }
  };

  var EXTRA = {
    en: {
      "«Il mio gatto si svegliava ogni notte alle 4 e correva per casa. Dopo dieci giorni con SCRATCHY dorme — e io con lui. Non ci credevo.»": "“My cat used to wake up every night at 4 and run around the house. After ten days with SCRATCHY he sleeps — and so do I. I couldn’t believe it.”",
      "«Avevo provato tre tiragraffi diversi, tutti ignorati. Questo lo usa in orizzontale da solo. Il divano è salvo dopo due anni di battaglia.»": "“I’d tried three different scratching posts, all ignored. This one he uses horizontally on his own. The sofa is safe after two years of battle.”",
      "«Il mio gatto era diventato spento, stava fermo tutto il giorno. Ora caccia, gratta, è di nuovo vivo. Non immaginavo fosse questo il problema.»": "“My cat had become listless, sitting still all day. Now he hunts, scratches, he’s alive again. I never imagined this was the problem.”",
      "Il posizionamento è tutto, e la Guida P.R.E.D.A. ti accompagna nell'introduzione passo-passo. La maggior parte dei gatti si attiva entro la fase di consolidamento. E in ogni caso hai 60 giorni per provarlo a casa tua: se non funziona, ti rimborsiamo.": "Placement is everything, and the Guida P.R.E.D.A. walks you through the step-by-step introduction. Most cats get going by the consolidation phase. And in any case you have 60 days to try it at home: if it doesn’t work, we refund you.",
      "Sì — anzi, il gatto spento e senza energie è proprio il segnale numero 4: vuol dire che il suo istinto è soffocato da tempo. La terapia ambientale serve proprio a riaccendere quell'istinto spento.": "Yes — in fact, the listless, low-energy cat is exactly symptom number 4: it means his instinct has been suppressed for a long time. Environmental therapy is precisely what reignites that switched-off instinct.",
      "I pannelli si consumano con l'uso: è il loro scopo, significa che il gatto li sta usando davvero. La terapia si mantiene riassortendoli nel tempo, così l'equilibrio raggiunto non si interrompe.": "The panels wear out with use: that’s their purpose, it means the cat is really using them. You keep the therapy going by restocking them over time, so the balance you’ve reached doesn’t break.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita. E puoi iniziare la Fase 1 (osservazione) oggi stesso.": "Free shipping across Italy, delivery usually in 5–9 working days. From the Kit 2+2, priority shipping is free. And you can start Phase 1 (observation) today.",
      "Sì. Puoi dividere l'importo in 3 rate senza interessi con Scalapay o Klarna, direttamente alla cassa.": "Yes. You can split the amount into 3 interest-free instalments with Scalapay or Klarna, right at checkout.",
      "Non conta di cosa è fatto: conta cosa": "It doesn’t matter what it’s made of: what matters is what", "fa": "does",
      ". SCRATCHY fa sfogare l'istinto di caccia in orizzontale, per terra, dove il gatto lo chiede. Il cartone a nido d'ape è scelto apposta perché ha la superficie giusta per graffiare e strappare. Un materiale costoso che lavora nel modo sbagliato non serve a niente; questo lavora nel modo giusto.": ". SCRATCHY lets the hunting instinct out horizontally, on the floor, where the cat asks for it. The honeycomb cardboard is chosen on purpose because it has the right surface to scratch and tear. An expensive material that works the wrong way is useless; this works the right way.",
      "Hai la garanzia soddisfatti o rimborsati": "You have the money-back guarantee",
      ". Provi la terapia a casa tua, con tutto il tempo per vederne gli effetti. Se non sei soddisfatta, ti restituiamo l'intero importo.": ". You try the therapy at home, with all the time to see the effects. If you’re not satisfied, we give you the full amount back.",
      "Il tuo gatto resta un cacciatore: il suo cervello è fatto per ricevere circa": "Your cat is still a hunter: his brain is built to take in about", "200 stimoli ogni ora": "200 stimuli every hour",
      ". Una casa, anche la più curata, gliene dà circa": ". A home, even the most well-kept, gives him about",
      "La caccia ha una sequenza naturale —": "Hunting has a natural sequence —", "cercare, inseguire, catturare, mordere": "search, chase, catch, bite",
      "— ma in casa resta sempre a metà. Quell'istinto non trova sfogo e deve uscire in qualche modo: così va a finire sui mobili, esplode di notte, si rivolta contro il suo corpo, oppure lo spegne. Questa è l'": "— but at home it always stays half-done. That instinct finds no outlet and has to come out somehow: so it ends up on the furniture, explodes at night, turns against his own body, or shuts him down. This is",
      "Ipostimolazione Felina Cronica (IFC)": "Chronic Feline Understimulation (IFC)",
      ", cioè un gatto che riceve troppi pochi stimoli ogni giorno: è l'unica causa che lega insieme tutti e quattro i segnali.": ", that is, a cat who gets far too few stimuli every day: it’s the only cause that ties all four signals together.",
      "SCRATCHY è il primo strumento di terapia ambientale pensato per far sfogare l'istinto di caccia": "SCRATCHY is the first environmental-therapy tool designed to let the hunting instinct out", "in orizzontale": "horizontally",
      ", cioè per terra, dove il gatto graffia davvero. Tre passi semplici. Ogni gatto ha i suoi tempi — per questo hai": ", that is, on the floor, where the cat really scratches. Three simple steps. Every cat has its own pace — that’s why you have",
      "per provarlo con calma, senza rischi.": "to try it calmly, with no risk.",
      "Il tiragraffi verticale": "The vertical scratching post", "non dà sfogo all'istinto: il 90% dei gatti graffia in": "doesn’t release the instinct: 90% of cats scratch", "orizzontale": "horizontally", ", cioè per terra, dove l'istinto lo chiede davvero.": ", that is, on the floor, where the instinct truly demands it.",
      "intrattengono cinque minuti, ma non completano il ciclo di caccia: la tensione resta.": "entertain for five minutes, but don’t complete the hunting cycle: the tension stays.",
      "agiscono sull'umore, non sull'istinto inappagato che genera il comportamento.": "act on mood, not on the unfulfilled instinct that drives the behaviour.",
      "aiutano te, non bastano a lui: il bisogno è ambientale, non affettivo.": "help you, but aren’t enough for him: the need is environmental, not emotional.",
      "Nessuna di queste cose ha fallito perché inutile. Hanno fallito perché curano il": "None of these failed because they’re useless. They failed because they treat the", "sintomo": "symptom", "e lasciano intatta la": "and leave the", "causa": "cause untouched",
      "Pannello in cartone resistente a nido d'ape, pensato per il graffio orizzontale che soddisfa il gesto naturale di graffiare e strappare. Sicuro, atossico, leggero e stabile. Pensato per il gatto che vive in casa.": "Sturdy honeycomb cardboard panel, designed for the horizontal scratch that satisfies the natural urge to scratch and tear. Safe, non-toxic, light and stable. Made for the cat that lives indoors.",
      "Distrugge i mobili, corre all'impazzata di notte, si lecca fino a spelarsi, oppure è spento e senza energie. Se riconosci anche solo uno di questi segnali, è il segnale che al tuo gatto manca lo sfogo del suo istinto.": "He destroys the furniture, runs frantically at night, over-grooms until bald, or is listless and low on energy. If you recognise even just one of these signs, it’s the sign your cat lacks an outlet for his instinct.",
      "60 giorni soddisfatti o rimborsati. Provi la terapia a casa tua: se non sei soddisfatta, ti restituiamo l'intero importo.": "60 days, satisfied or refunded. You try the therapy at home: if you’re not satisfied, we give you the full amount back.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita.": "Free shipping across Italy, delivery usually in 5–9 working days. From the Kit 2+2, priority shipping is free.",
      "oppure in 3 rate da": "or in 3 instalments of", "con": "with", "— senza interessi": "— interest-free",
      "Pagamento 100% sicuro · acquista anche con PayPal": "100% secure payment · pay with PayPal too", "Protezione acquirente PayPal inclusa": "PayPal Buyer Protection included",
      "GIORNI": "DAYS", "Soddisfatti o rimborsati, senza farti domande": "Satisfied or refunded, no questions asked",
      "Provalo a casa tua senza rischi: se non vedi il tuo gatto stare meglio, ti restituiamo l'intero importo. Tutto il rischio è nostro, non tuo.": "Try it at home with no risk: if you don’t see your cat doing better, we give you the full amount back. All the risk is ours, not yours.",
      "Il metodo SCRATCHY si appoggia su fonti reali di comportamento felino:": "The SCRATCHY method is grounded in real feline-behaviour sources:",
      "(2013) · Linee guida AAFP/ISFM (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. Il protocollo in 3 fasi e la": "(2013) · AAFP/ISFM guidelines (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. The 3-phase protocol and the",
      "sono gli strumenti del metodo. SCRATCHY è una cornice di terapia ambientale ancorata a queste fonti, non un referto medico.": "are the tools of the method. SCRATCHY is an environmental-therapy framework grounded in these sources, not a medical report.",
      "Oppure, col tempo, può essere tutto diverso — e hai": "Or, in time, it can all be different — and you have",
      "per provarlo senza rischi: se non vedi il tuo gatto stare meglio, ti rimborsiamo. La causa è una sola, e c'è una cosa che la risolve.": "to try it risk-free: if you don’t see your cat doing better, we refund you. There’s only one cause, and one thing that solves it."
    },
    fr: {
      "«Il mio gatto si svegliava ogni notte alle 4 e correva per casa. Dopo dieci giorni con SCRATCHY dorme — e io con lui. Non ci credevo.»": "« Mon chat se réveillait toutes les nuits à 4 h et courait dans la maison. Après dix jours avec SCRATCHY, il dort — et moi aussi. Je n’y croyais pas. »",
      "«Avevo provato tre tiragraffi diversi, tutti ignorati. Questo lo usa in orizzontale da solo. Il divano è salvo dopo due anni di battaglia.»": "« J’avais essayé trois griffoirs différents, tous ignorés. Celui-ci, il l’utilise à l’horizontale tout seul. Le canapé est sauvé après deux ans de bataille. »",
      "«Il mio gatto era diventato spento, stava fermo tutto il giorno. Ora caccia, gratta, è di nuovo vivo. Non immaginavo fosse questo il problema.»": "« Mon chat était devenu apathique, immobile toute la journée. Maintenant il chasse, il griffe, il revit. Je n’imaginais pas que c’était ça le problème. »",
      "Il posizionamento è tutto, e la Guida P.R.E.D.A. ti accompagna nell'introduzione passo-passo. La maggior parte dei gatti si attiva entro la fase di consolidamento. E in ogni caso hai 60 giorni per provarlo a casa tua: se non funziona, ti rimborsiamo.": "Le placement est essentiel, et la Guida P.R.E.D.A. vous accompagne dans l’introduction étape par étape. La plupart des chats s’y mettent dès la phase de consolidation. Et de toute façon vous avez 60 jours pour l’essayer chez vous : si ça ne marche pas, on vous rembourse.",
      "Sì — anzi, il gatto spento e senza energie è proprio il segnale numero 4: vuol dire che il suo istinto è soffocato da tempo. La terapia ambientale serve proprio a riaccendere quell'istinto spento.": "Oui — au contraire, le chat éteint et sans énergie est justement le signe numéro 4 : cela signifie que son instinct est étouffé depuis longtemps. La thérapie environnementale sert justement à raviver cet instinct éteint.",
      "I pannelli si consumano con l'uso: è il loro scopo, significa che il gatto li sta usando davvero. La terapia si mantiene riassortendoli nel tempo, così l'equilibrio raggiunto non si interrompe.": "Les panneaux s’usent à l’usage : c’est leur but, cela veut dire que le chat les utilise vraiment. On entretient la thérapie en les renouvelant au fil du temps, pour que l’équilibre atteint ne s’interrompe pas.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita. E puoi iniziare la Fase 1 (osservazione) oggi stesso.": "Livraison gratuite dans toute l’Italie, livraison généralement en 5–9 jours ouvrés. À partir du Kit 2+2, la livraison prioritaire est gratuite. Et vous pouvez commencer la Phase 1 (observation) dès aujourd’hui.",
      "Sì. Puoi dividere l'importo in 3 rate senza interessi con Scalapay o Klarna, direttamente alla cassa.": "Oui. Vous pouvez diviser le montant en 3 fois sans frais avec Scalapay ou Klarna, directement au paiement.",
      "Non conta di cosa è fatto: conta cosa": "Peu importe de quoi c’est fait : ce qui compte, c’est ce qu’il", "fa": "fait",
      ". SCRATCHY fa sfogare l'istinto di caccia in orizzontale, per terra, dove il gatto lo chiede. Il cartone a nido d'ape è scelto apposta perché ha la superficie giusta per graffiare e strappare. Un materiale costoso che lavora nel modo sbagliato non serve a niente; questo lavora nel modo giusto.": ". SCRATCHY laisse sortir l’instinct de chasse à l’horizontale, au sol, là où le chat le demande. Le carton alvéolaire est choisi exprès car il a la bonne surface pour griffer et déchirer. Un matériau coûteux qui fonctionne mal ne sert à rien ; celui-ci fonctionne bien.",
      "Hai la garanzia soddisfatti o rimborsati": "Vous avez la garantie satisfait ou remboursé",
      ". Provi la terapia a casa tua, con tutto il tempo per vederne gli effetti. Se non sei soddisfatta, ti restituiamo l'intero importo.": ". Vous essayez la thérapie chez vous, avec tout le temps d’en voir les effets. Si vous n’êtes pas satisfait, on vous rend la totalité du montant.",
      "Il tuo gatto resta un cacciatore: il suo cervello è fatto per ricevere circa": "Votre chat reste un chasseur : son cerveau est fait pour recevoir environ", "200 stimoli ogni ora": "200 stimuli par heure",
      ". Una casa, anche la più curata, gliene dà circa": ". Une maison, même la mieux aménagée, lui en donne environ",
      "La caccia ha una sequenza naturale —": "La chasse a une séquence naturelle —", "cercare, inseguire, catturare, mordere": "chercher, poursuivre, capturer, mordre",
      "— ma in casa resta sempre a metà. Quell'istinto non trova sfogo e deve uscire in qualche modo: così va a finire sui mobili, esplode di notte, si rivolta contro il suo corpo, oppure lo spegne. Questa è l'": "— mais à la maison elle reste toujours à moitié. Cet instinct ne trouve pas d’exutoire et doit ressortir d’une façon ou d’une autre : il finit sur les meubles, explose la nuit, se retourne contre son corps, ou l’éteint. C’est",
      "Ipostimolazione Felina Cronica (IFC)": "l’Hypostimulation Féline Chronique (IFC)",
      ", cioè un gatto che riceve troppi pochi stimoli ogni giorno: è l'unica causa che lega insieme tutti e quattro i segnali.": ", c’est-à-dire un chat qui reçoit bien trop peu de stimuli chaque jour : c’est la seule cause qui relie les quatre signaux.",
      "SCRATCHY è il primo strumento di terapia ambientale pensato per far sfogare l'istinto di caccia": "SCRATCHY est le premier outil de thérapie environnementale conçu pour libérer l’instinct de chasse", "in orizzontale": "à l’horizontale",
      ", cioè per terra, dove il gatto graffia davvero. Tre passi semplici. Ogni gatto ha i suoi tempi — per questo hai": ", c’est-à-dire au sol, là où le chat griffe vraiment. Trois étapes simples. Chaque chat a son rythme — c’est pourquoi vous avez",
      "per provarlo con calma, senza rischi.": "pour l’essayer tranquillement, sans risque.",
      "Il tiragraffi verticale": "Le griffoir vertical", "non dà sfogo all'istinto: il 90% dei gatti graffia in": "ne libère pas l’instinct : 90 % des chats griffent à", "orizzontale": "l’horizontale", ", cioè per terra, dove l'istinto lo chiede davvero.": ", c’est-à-dire au sol, là où l’instinct le réclame vraiment.",
      "intrattengono cinque minuti, ma non completano il ciclo di caccia: la tensione resta.": "amusent cinq minutes, mais ne complètent pas le cycle de chasse : la tension demeure.",
      "agiscono sull'umore, non sull'istinto inappagato che genera il comportamento.": "agissent sur l’humeur, pas sur l’instinct inassouvi qui génère le comportement.",
      "aiutano te, non bastano a lui: il bisogno è ambientale, non affettivo.": "vous aident, mais ne lui suffisent pas : le besoin est environnemental, pas affectif.",
      "Nessuna di queste cose ha fallito perché inutile. Hanno fallito perché curano il": "Aucune de ces choses n’a échoué parce qu’inutile. Elles ont échoué parce qu’elles soignent le", "sintomo": "symptôme", "e lasciano intatta la": "et laissent intacte la", "causa": "cause",
      "Pannello in cartone resistente a nido d'ape, pensato per il graffio orizzontale che soddisfa il gesto naturale di graffiare e strappare. Sicuro, atossico, leggero e stabile. Pensato per il gatto che vive in casa.": "Panneau en carton alvéolaire résistant, conçu pour la griffade horizontale qui satisfait le geste naturel de griffer et déchirer. Sûr, non toxique, léger et stable. Pensé pour le chat qui vit en intérieur.",
      "Distrugge i mobili, corre all'impazzata di notte, si lecca fino a spelarsi, oppure è spento e senza energie. Se riconosci anche solo uno di questi segnali, è il segnale che al tuo gatto manca lo sfogo del suo istinto.": "Il détruit les meubles, court frénétiquement la nuit, se lèche jusqu’à s’arracher les poils, ou est éteint et sans énergie. Si vous reconnaissez ne serait-ce qu’un de ces signes, c’est le signe qu’il manque à votre chat un exutoire pour son instinct.",
      "60 giorni soddisfatti o rimborsati. Provi la terapia a casa tua: se non sei soddisfatta, ti restituiamo l'intero importo.": "60 jours satisfait ou remboursé. Vous essayez la thérapie chez vous : si vous n’êtes pas satisfait, on vous rend la totalité du montant.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita.": "Livraison gratuite dans toute l’Italie, livraison généralement en 5–9 jours ouvrés. À partir du Kit 2+2, la livraison prioritaire est gratuite.",
      "oppure in 3 rate da": "ou en 3 fois de", "con": "avec", "— senza interessi": "— sans frais",
      "Pagamento 100% sicuro · acquista anche con PayPal": "Paiement 100 % sécurisé · payez aussi avec PayPal", "Protezione acquirente PayPal inclusa": "Protection des acheteurs PayPal incluse",
      "GIORNI": "JOURS", "Soddisfatti o rimborsati, senza farti domande": "Satisfait ou remboursé, sans vous poser de questions",
      "Provalo a casa tua senza rischi: se non vedi il tuo gatto stare meglio, ti restituiamo l'intero importo. Tutto il rischio è nostro, non tuo.": "Essayez-le chez vous sans risque : si vous ne voyez pas votre chat aller mieux, on vous rend la totalité du montant. Tout le risque est pour nous, pas pour vous.",
      "Il metodo SCRATCHY si appoggia su fonti reali di comportamento felino:": "La méthode SCRATCHY s’appuie sur de vraies sources de comportement félin :",
      "(2013) · Linee guida AAFP/ISFM (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. Il protocollo in 3 fasi e la": "(2013) · Recommandations AAFP/ISFM (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. Le protocole en 3 phases et la",
      "sono gli strumenti del metodo. SCRATCHY è una cornice di terapia ambientale ancorata a queste fonti, non un referto medico.": "sont les outils de la méthode. SCRATCHY est un cadre de thérapie environnementale fondé sur ces sources, pas un compte rendu médical.",
      "Oppure, col tempo, può essere tutto diverso — e hai": "Ou, avec le temps, tout peut être différent — et vous avez",
      "per provarlo senza rischi: se non vedi il tuo gatto stare meglio, ti rimborsiamo. La causa è una sola, e c'è una cosa che la risolve.": "pour l’essayer sans risque : si vous ne voyez pas votre chat aller mieux, on vous rembourse. Il n’y a qu’une seule cause, et une chose qui la résout."
    },
    es: {
      "«Il mio gatto si svegliava ogni notte alle 4 e correva per casa. Dopo dieci giorni con SCRATCHY dorme — e io con lui. Non ci credevo.»": "«Mi gato se despertaba cada noche a las 4 y corría por casa. Tras diez días con SCRATCHY duerme — y yo con él. No me lo creía.»",
      "«Avevo provato tre tiragraffi diversi, tutti ignorati. Questo lo usa in orizzontale da solo. Il divano è salvo dopo due anni di battaglia.»": "«Había probado tres rascadores distintos, todos ignorados. Este lo usa en horizontal solo. El sofá está a salvo tras dos años de batalla.»",
      "«Il mio gatto era diventato spento, stava fermo tutto il giorno. Ora caccia, gratta, è di nuovo vivo. Non immaginavo fosse questo il problema.»": "«Mi gato se había vuelto apático, quieto todo el día. Ahora caza, rasca, está vivo de nuevo. No imaginaba que el problema fuera este.»",
      "Il posizionamento è tutto, e la Guida P.R.E.D.A. ti accompagna nell'introduzione passo-passo. La maggior parte dei gatti si attiva entro la fase di consolidamento. E in ogni caso hai 60 giorni per provarlo a casa tua: se non funziona, ti rimborsiamo.": "La colocación lo es todo, y la Guida P.R.E.D.A. te acompaña en la introducción paso a paso. La mayoría de los gatos se activan en la fase de consolidación. Y en cualquier caso tienes 60 días para probarlo en casa: si no funciona, te reembolsamos.",
      "Sì — anzi, il gatto spento e senza energie è proprio il segnale numero 4: vuol dire che il suo istinto è soffocato da tempo. La terapia ambientale serve proprio a riaccendere quell'istinto spento.": "Sí — es más, el gato apagado y sin energía es justo la señal número 4: significa que su instinto lleva mucho tiempo ahogado. La terapia ambiental sirve precisamente para reavivar ese instinto apagado.",
      "I pannelli si consumano con l'uso: è il loro scopo, significa che il gatto li sta usando davvero. La terapia si mantiene riassortendoli nel tempo, così l'equilibrio raggiunto non si interrompe.": "Los paneles se desgastan con el uso: ese es su propósito, significa que el gato los está usando de verdad. La terapia se mantiene reponiéndolos con el tiempo, así el equilibrio logrado no se interrumpe.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita. E puoi iniziare la Fase 1 (osservazione) oggi stesso.": "Envío gratis en toda Italia, entrega normalmente en 5–9 días laborables. Desde el Kit 2+2, el envío prioritario es gratis. Y puedes empezar la Fase 1 (observación) hoy mismo.",
      "Sì. Puoi dividere l'importo in 3 rate senza interessi con Scalapay o Klarna, direttamente alla cassa.": "Sí. Puedes dividir el importe en 3 plazos sin intereses con Scalapay o Klarna, directamente en el pago.",
      "Non conta di cosa è fatto: conta cosa": "No importa de qué está hecho: importa lo que", "fa": "hace",
      ". SCRATCHY fa sfogare l'istinto di caccia in orizzontale, per terra, dove il gatto lo chiede. Il cartone a nido d'ape è scelto apposta perché ha la superficie giusta per graffiare e strappare. Un materiale costoso che lavora nel modo sbagliato non serve a niente; questo lavora nel modo giusto.": ". SCRATCHY deja salir el instinto de caza en horizontal, en el suelo, donde el gato lo pide. El cartón alveolar está elegido a propósito porque tiene la superficie justa para arañar y rasgar. Un material caro que funciona mal no sirve de nada; este funciona bien.",
      "Hai la garanzia soddisfatti o rimborsati": "Tienes la garantía de satisfecho o reembolsado",
      ". Provi la terapia a casa tua, con tutto il tempo per vederne gli effetti. Se non sei soddisfatta, ti restituiamo l'intero importo.": ". Pruebas la terapia en casa, con todo el tiempo para ver los efectos. Si no estás satisfecho, te devolvemos el importe íntegro.",
      "Il tuo gatto resta un cacciatore: il suo cervello è fatto per ricevere circa": "Tu gato sigue siendo un cazador: su cerebro está hecho para recibir unos", "200 stimoli ogni ora": "200 estímulos cada hora",
      ". Una casa, anche la più curata, gliene dà circa": ". Una casa, incluso la más cuidada, le da unos",
      "La caccia ha una sequenza naturale —": "La caza tiene una secuencia natural —", "cercare, inseguire, catturare, mordere": "buscar, perseguir, capturar, morder",
      "— ma in casa resta sempre a metà. Quell'istinto non trova sfogo e deve uscire in qualche modo: così va a finire sui mobili, esplode di notte, si rivolta contro il suo corpo, oppure lo spegne. Questa è l'": "— pero en casa siempre queda a medias. Ese instinto no encuentra salida y debe salir de algún modo: así acaba en los muebles, explota de noche, se vuelve contra su cuerpo, o lo apaga. Esta es",
      "Ipostimolazione Felina Cronica (IFC)": "la Hipoestimulación Felina Crónica (IFC)",
      ", cioè un gatto che riceve troppi pochi stimoli ogni giorno: è l'unica causa che lega insieme tutti e quattro i segnali.": ", es decir, un gato que recibe demasiados pocos estímulos cada día: es la única causa que une las cuatro señales.",
      "SCRATCHY è il primo strumento di terapia ambientale pensato per far sfogare l'istinto di caccia": "SCRATCHY es la primera herramienta de terapia ambiental pensada para liberar el instinto de caza", "in orizzontale": "en horizontal",
      ", cioè per terra, dove il gatto graffia davvero. Tre passi semplici. Ogni gatto ha i suoi tempi — per questo hai": ", es decir, en el suelo, donde el gato rasca de verdad. Tres pasos sencillos. Cada gato tiene su ritmo — por eso tienes",
      "per provarlo con calma, senza rischi.": "para probarlo con calma, sin riesgos.",
      "Il tiragraffi verticale": "El rascador vertical", "non dà sfogo all'istinto: il 90% dei gatti graffia in": "no da salida al instinto: el 90% de los gatos rasca en", "orizzontale": "horizontal", ", cioè per terra, dove l'istinto lo chiede davvero.": ", es decir, en el suelo, donde el instinto lo pide de verdad.",
      "intrattengono cinque minuti, ma non completano il ciclo di caccia: la tensione resta.": "entretienen cinco minutos, pero no completan el ciclo de caza: la tensión permanece.",
      "agiscono sull'umore, non sull'istinto inappagato che genera il comportamento.": "actúan sobre el humor, no sobre el instinto insatisfecho que genera el comportamiento.",
      "aiutano te, non bastano a lui: il bisogno è ambientale, non affettivo.": "te ayudan a ti, no le bastan a él: la necesidad es ambiental, no afectiva.",
      "Nessuna di queste cose ha fallito perché inutile. Hanno fallito perché curano il": "Ninguna de estas cosas falló por inútil. Fallaron porque tratan el", "sintomo": "síntoma", "e lasciano intatta la": "y dejan intacta la", "causa": "causa",
      "Pannello in cartone resistente a nido d'ape, pensato per il graffio orizzontale che soddisfa il gesto naturale di graffiare e strappare. Sicuro, atossico, leggero e stabile. Pensato per il gatto che vive in casa.": "Panel de cartón alveolar resistente, pensado para el rascado horizontal que satisface el gesto natural de arañar y rasgar. Seguro, atóxico, ligero y estable. Pensado para el gato que vive en casa.",
      "Distrugge i mobili, corre all'impazzata di notte, si lecca fino a spelarsi, oppure è spento e senza energie. Se riconosci anche solo uno di questi segnali, è il segnale che al tuo gatto manca lo sfogo del suo istinto.": "Destroza los muebles, corre como loco de noche, se lame hasta pelarse, o está apagado y sin energía. Si reconoces aunque sea una de estas señales, es la señal de que a tu gato le falta una salida para su instinto.",
      "60 giorni soddisfatti o rimborsati. Provi la terapia a casa tua: se non sei soddisfatta, ti restituiamo l'intero importo.": "60 días satisfecho o reembolsado. Pruebas la terapia en casa: si no estás satisfecho, te devolvemos el importe íntegro.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita.": "Envío gratis en toda Italia, entrega normalmente en 5–9 días laborables. Desde el Kit 2+2, el envío prioritario es gratis.",
      "oppure in 3 rate da": "o en 3 plazos de", "con": "con", "— senza interessi": "— sin intereses",
      "Pagamento 100% sicuro · acquista anche con PayPal": "Pago 100% seguro · paga también con PayPal", "Protezione acquirente PayPal inclusa": "Protección al comprador de PayPal incluida",
      "GIORNI": "DÍAS", "Soddisfatti o rimborsati, senza farti domande": "Satisfecho o reembolsado, sin preguntas",
      "Provalo a casa tua senza rischi: se non vedi il tuo gatto stare meglio, ti restituiamo l'intero importo. Tutto il rischio è nostro, non tuo.": "Pruébalo en casa sin riesgo: si no ves a tu gato mejor, te devolvemos el importe íntegro. Todo el riesgo es nuestro, no tuyo.",
      "Il metodo SCRATCHY si appoggia su fonti reali di comportamento felino:": "El método SCRATCHY se apoya en fuentes reales de comportamiento felino:",
      "(2013) · Linee guida AAFP/ISFM (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. Il protocollo in 3 fasi e la": "(2013) · Directrices AAFP/ISFM (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. El protocolo en 3 fases y la",
      "sono gli strumenti del metodo. SCRATCHY è una cornice di terapia ambientale ancorata a queste fonti, non un referto medico.": "son las herramientas del método. SCRATCHY es un marco de terapia ambiental basado en estas fuentes, no un informe médico.",
      "Oppure, col tempo, può essere tutto diverso — e hai": "O, con el tiempo, todo puede ser diferente — y tienes",
      "per provarlo senza rischi: se non vedi il tuo gatto stare meglio, ti rimborsiamo. La causa è una sola, e c'è una cosa che la risolve.": "para probarlo sin riesgo: si no ves a tu gato mejor, te reembolsamos. La causa es una sola, y hay una cosa que la resuelve."
    },
    de: {
      "«Il mio gatto si svegliava ogni notte alle 4 e correva per casa. Dopo dieci giorni con SCRATCHY dorme — e io con lui. Non ci credevo.»": "«Meine Katze wachte jede Nacht um 4 auf und rannte durchs Haus. Nach zehn Tagen mit SCRATCHY schläft sie — und ich auch. Ich konnte es nicht glauben.»",
      "«Avevo provato tre tiragraffi diversi, tutti ignorati. Questo lo usa in orizzontale da solo. Il divano è salvo dopo due anni di battaglia.»": "«Ich hatte drei verschiedene Kratzbäume probiert, alle ignoriert. Diesen benutzt er von allein horizontal. Das Sofa ist nach zwei Jahren Kampf gerettet.»",
      "«Il mio gatto era diventato spento, stava fermo tutto il giorno. Ora caccia, gratta, è di nuovo vivo. Non immaginavo fosse questo il problema.»": "«Meine Katze war teilnahmslos geworden, saß den ganzen Tag still. Jetzt jagt sie, kratzt, sie lebt wieder. Ich hätte nie gedacht, dass das das Problem war.»",
      "Il posizionamento è tutto, e la Guida P.R.E.D.A. ti accompagna nell'introduzione passo-passo. La maggior parte dei gatti si attiva entro la fase di consolidamento. E in ogni caso hai 60 giorni per provarlo a casa tua: se non funziona, ti rimborsiamo.": "Die Platzierung ist alles, und die Guida P.R.E.D.A. begleitet dich Schritt für Schritt bei der Einführung. Die meisten Katzen legen bis zur Festigungsphase los. Und in jedem Fall hast du 60 Tage, um es zu Hause zu testen: Wenn es nicht funktioniert, erstatten wir dir das Geld.",
      "Sì — anzi, il gatto spento e senza energie è proprio il segnale numero 4: vuol dire che il suo istinto è soffocato da tempo. La terapia ambientale serve proprio a riaccendere quell'istinto spento.": "Ja — im Gegenteil, die teilnahmslose, energielose Katze ist genau Symptom Nummer 4: Es bedeutet, dass ihr Instinkt seit Langem unterdrückt ist. Die Umwelttherapie weckt genau diesen erloschenen Instinkt wieder.",
      "I pannelli si consumano con l'uso: è il loro scopo, significa che il gatto li sta usando davvero. La terapia si mantiene riassortendoli nel tempo, così l'equilibrio raggiunto non si interrompe.": "Die Platten nutzen sich beim Gebrauch ab: Das ist ihr Zweck, es bedeutet, dass die Katze sie wirklich benutzt. Die Therapie hältst du aufrecht, indem du sie mit der Zeit nachkaufst, damit das erreichte Gleichgewicht nicht abbricht.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita. E puoi iniziare la Fase 1 (osservazione) oggi stesso.": "Kostenloser Versand in ganz Italien, Lieferung meist in 5–9 Werktagen. Ab dem Kit 2+2 ist der Prioritätsversand gratis. Und du kannst Phase 1 (Beobachtung) schon heute beginnen.",
      "Sì. Puoi dividere l'importo in 3 rate senza interessi con Scalapay o Klarna, direttamente alla cassa.": "Ja. Du kannst den Betrag in 3 zinsfreie Raten mit Scalapay oder Klarna aufteilen, direkt an der Kasse.",
      "Non conta di cosa è fatto: conta cosa": "Es kommt nicht darauf an, woraus es besteht: Entscheidend ist, was es", "fa": "tut",
      ". SCRATCHY fa sfogare l'istinto di caccia in orizzontale, per terra, dove il gatto lo chiede. Il cartone a nido d'ape è scelto apposta perché ha la superficie giusta per graffiare e strappare. Un materiale costoso che lavora nel modo sbagliato non serve a niente; questo lavora nel modo giusto.": ". SCRATCHY lässt den Jagdinstinkt horizontal heraus, am Boden, wo die Katze danach verlangt. Der Wabenkarton ist bewusst gewählt, weil er die richtige Oberfläche zum Kratzen und Reißen hat. Ein teures Material, das falsch arbeitet, nützt nichts; dieses arbeitet richtig.",
      "Hai la garanzia soddisfatti o rimborsati": "Du hast die Geld-zurück-Garantie",
      ". Provi la terapia a casa tua, con tutto il tempo per vederne gli effetti. Se non sei soddisfatta, ti restituiamo l'intero importo.": ". Du testest die Therapie zu Hause, mit aller Zeit, um die Wirkung zu sehen. Wenn du nicht zufrieden bist, erstatten wir dir den vollen Betrag.",
      "Il tuo gatto resta un cacciatore: il suo cervello è fatto per ricevere circa": "Deine Katze bleibt eine Jägerin: Ihr Gehirn ist darauf ausgelegt, etwa", "200 stimoli ogni ora": "200 Reize pro Stunde",
      ". Una casa, anche la più curata, gliene dà circa": ". Ein Zuhause, selbst das gepflegteste, bietet ihr etwa",
      "La caccia ha una sequenza naturale —": "Die Jagd hat eine natürliche Abfolge —", "cercare, inseguire, catturare, mordere": "suchen, jagen, fangen, beißen",
      "— ma in casa resta sempre a metà. Quell'istinto non trova sfogo e deve uscire in qualche modo: così va a finire sui mobili, esplode di notte, si rivolta contro il suo corpo, oppure lo spegne. Questa è l'": "— aber zu Hause bleibt sie immer auf halbem Weg. Dieser Instinkt findet kein Ventil und muss irgendwie heraus: So landet er auf den Möbeln, explodiert nachts, richtet sich gegen den eigenen Körper oder schaltet sie ab. Das ist",
      "Ipostimolazione Felina Cronica (IFC)": "die chronische feline Unterstimulation (IFC)",
      ", cioè un gatto che riceve troppi pochi stimoli ogni giorno: è l'unica causa che lega insieme tutti e quattro i segnali.": ", also eine Katze, die jeden Tag viel zu wenige Reize bekommt: Es ist die einzige Ursache, die alle vier Signale verbindet.",
      "SCRATCHY è il primo strumento di terapia ambientale pensato per far sfogare l'istinto di caccia": "SCRATCHY ist das erste Umwelttherapie-Werkzeug, das den Jagdinstinkt", "in orizzontale": "horizontal",
      ", cioè per terra, dove il gatto graffia davvero. Tre passi semplici. Ogni gatto ha i suoi tempi — per questo hai": ", also am Boden, austoben lässt, wo die Katze wirklich kratzt. Drei einfache Schritte. Jede Katze hat ihr Tempo — deshalb hast du",
      "per provarlo con calma, senza rischi.": "um es in Ruhe auszuprobieren, ohne Risiko.",
      "Il tiragraffi verticale": "Der vertikale Kratzbaum", "non dà sfogo all'istinto: il 90% dei gatti graffia in": "gibt dem Instinkt kein Ventil: 90 % der Katzen kratzen", "orizzontale": "horizontal", ", cioè per terra, dove l'istinto lo chiede davvero.": ", also am Boden, wo der Instinkt es wirklich verlangt.",
      "intrattengono cinque minuti, ma non completano il ciclo di caccia: la tensione resta.": "unterhalten fünf Minuten, vollenden aber den Jagdzyklus nicht: Die Anspannung bleibt.",
      "agiscono sull'umore, non sull'istinto inappagato che genera il comportamento.": "wirken auf die Stimmung, nicht auf den unerfüllten Instinkt, der das Verhalten auslöst.",
      "aiutano te, non bastano a lui: il bisogno è ambientale, non affettivo.": "helfen dir, reichen ihr aber nicht: Das Bedürfnis ist umweltbezogen, nicht emotional.",
      "Nessuna di queste cose ha fallito perché inutile. Hanno fallito perché curano il": "Keine dieser Sachen ist gescheitert, weil sie nutzlos wäre. Sie sind gescheitert, weil sie das", "sintomo": "Symptom", "e lasciano intatta la": "behandeln und die", "causa": "Ursache unberührt lassen",
      "Pannello in cartone resistente a nido d'ape, pensato per il graffio orizzontale che soddisfa il gesto naturale di graffiare e strappare. Sicuro, atossico, leggero e stabile. Pensato per il gatto che vive in casa.": "Robuste Wabenkartonplatte, konzipiert für das horizontale Kratzen, das den natürlichen Drang zu kratzen und zu reißen befriedigt. Sicher, ungiftig, leicht und stabil. Gemacht für die Wohnungskatze.",
      "Distrugge i mobili, corre all'impazzata di notte, si lecca fino a spelarsi, oppure è spento e senza energie. Se riconosci anche solo uno di questi segnali, è il segnale che al tuo gatto manca lo sfogo del suo istinto.": "Sie zerstört die Möbel, rast nachts wild umher, leckt sich kahl oder ist teilnahmslos und energielos. Wenn du auch nur eines dieser Zeichen erkennst, ist es das Zeichen, dass deiner Katze ein Ventil für ihren Instinkt fehlt.",
      "60 giorni soddisfatti o rimborsati. Provi la terapia a casa tua: se non sei soddisfatta, ti restituiamo l'intero importo.": "60 Tage zufrieden oder erstattet. Du testest die Therapie zu Hause: Wenn du nicht zufrieden bist, erstatten wir dir den vollen Betrag.",
      "Spedizione gratuita in tutta Italia, consegna in genere in 5–9 giorni lavorativi. Dal Kit 2+2 la spedizione prioritaria è gratuita.": "Kostenloser Versand in ganz Italien, Lieferung meist in 5–9 Werktagen. Ab dem Kit 2+2 ist der Prioritätsversand gratis.",
      "oppure in 3 rate da": "oder in 3 Raten zu je", "con": "mit", "— senza interessi": "— zinsfrei",
      "Pagamento 100% sicuro · acquista anche con PayPal": "100% sicherer Bezahlvorgang · auch mit PayPal", "Protezione acquirente PayPal inclusa": "PayPal-Käuferschutz inklusive",
      "GIORNI": "TAGE", "Soddisfatti o rimborsati, senza farti domande": "Zufrieden oder erstattet, ohne Nachfragen",
      "Provalo a casa tua senza rischi: se non vedi il tuo gatto stare meglio, ti restituiamo l'intero importo. Tutto il rischio è nostro, non tuo.": "Teste es zu Hause ohne Risiko: Wenn deine Katze nicht besser wird, erstatten wir dir den vollen Betrag. Das ganze Risiko liegt bei uns, nicht bei dir.",
      "Il metodo SCRATCHY si appoggia su fonti reali di comportamento felino:": "Die SCRATCHY-Methode stützt sich auf echte Quellen zum Katzenverhalten:",
      "(2013) · Linee guida AAFP/ISFM (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. Il protocollo in 3 fasi e la": "(2013) · AAFP/ISFM-Leitlinien (2013) · Mills (2013) · Wilbourn (2017) · Mikel Delgado, UC Davis. Das 3-Phasen-Protokoll und die",
      "sono gli strumenti del metodo. SCRATCHY è una cornice di terapia ambientale ancorata a queste fonti, non un referto medico.": "sind die Werkzeuge der Methode. SCRATCHY ist ein Rahmen der Umwelttherapie auf Basis dieser Quellen, kein medizinischer Befund.",
      "Oppure, col tempo, può essere tutto diverso — e hai": "Oder mit der Zeit kann alles anders sein — und du hast",
      "per provarlo senza rischi: se non vedi il tuo gatto stare meglio, ti rimborsiamo. La causa è una sola, e c'è una cosa che la risolve.": "um es risikofrei zu testen: Wenn deine Katze nicht besser wird, erstatten wir dir das Geld. Es gibt nur eine Ursache, und eine Sache, die sie löst."
    }
  };
  Object.keys(EXTRA).forEach(function (l) {
    Object.keys(EXTRA[l]).forEach(function (k) { I18N[l][k] = EXTRA[l][k]; });
  });

  /* Stringhe del CARRELLO (l'italiano resta la lingua sorgente) */
  var CART_I18N = {
    en: { "Carrello": "Cart", "Offerte riservate ancora per": "Offers reserved for", "Spedizione gratuita": "Free shipping", "Garanzia 60 giorni": "60-day guarantee", "Risparmi": "You save", "Spedizione in Italia": "Shipping in Italy", "Checkout sicuro": "Secure checkout", "Pagamento 100% sicuro": "100% secure payment", "Il carrello è vuoto": "Your cart is empty", "Scopri le offerte qui sotto e aggiungi il tuo Scratchy.": "Browse the offers below and add your Scratchy.", "Continua lo shopping": "Continue shopping" },
    fr: { "Carrello": "Panier", "Offerte riservate ancora per": "Offres réservées encore pour", "Spedizione gratuita": "Livraison gratuite", "Garanzia 60 giorni": "Garantie 60 jours", "Risparmi": "Vous économisez", "Spedizione in Italia": "Livraison en Italie", "Checkout sicuro": "Paiement sécurisé", "Pagamento 100% sicuro": "Paiement 100 % sécurisé", "Il carrello è vuoto": "Votre panier est vide", "Scopri le offerte qui sotto e aggiungi il tuo Scratchy.": "Découvrez les offres ci-dessous et ajoutez votre Scratchy.", "Continua lo shopping": "Continuer les achats" },
    es: { "Carrello": "Carrito", "Offerte riservate ancora per": "Ofertas reservadas aún por", "Spedizione gratuita": "Envío gratis", "Garanzia 60 giorni": "Garantía 60 días", "Risparmi": "Ahorras", "Spedizione in Italia": "Envío en Italia", "Checkout sicuro": "Pago seguro", "Pagamento 100% sicuro": "Pago 100% seguro", "Il carrello è vuoto": "Tu carrito está vacío", "Scopri le offerte qui sotto e aggiungi il tuo Scratchy.": "Descubre las ofertas abajo y añade tu Scratchy.", "Continua lo shopping": "Seguir comprando" },
    de: { "Carrello": "Warenkorb", "Offerte riservate ancora per": "Angebote reserviert noch für", "Spedizione gratuita": "Kostenloser Versand", "Garanzia 60 giorni": "60 Tage Garantie", "Risparmi": "Du sparst", "Spedizione in Italia": "Versand nach Italien", "Checkout sicuro": "Sicher bezahlen", "Pagamento 100% sicuro": "100% sichere Zahlung", "Il carrello è vuoto": "Dein Warenkorb ist leer", "Scopri le offerte qui sotto e aggiungi il tuo Scratchy.": "Entdecke die Angebote unten und füge deinen Scratchy hinzu.", "Continua lo shopping": "Weiter einkaufen" }
  };
  CART_I18N.en["Incluso nell'offerta"] = "Included in the offer";
  CART_I18N.fr["Incluso nell'offerta"] = "Inclus dans l'offre";
  CART_I18N.es["Incluso nell'offerta"] = "Incluido en la oferta";
  CART_I18N.de["Incluso nell'offerta"] = "Im Angebot enthalten";
  Object.keys(CART_I18N).forEach(function (l) {
    Object.keys(CART_I18N[l]).forEach(function (k) { I18N[l][k] = CART_I18N[l][k]; });
  });

  var COUNTRY = { it: "Italia", en: "International", fr: "France", es: "España", de: "Deutschland" };
  var CODE = { it: "IT", en: "EN", fr: "FR", es: "ES", de: "DE" };
  var origMap = new WeakMap();
  var LANG = "it";

  function translateRoot(root) {
    var dict = I18N[LANG];
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = walker.nextNode())) {
      var p = n.parentNode;
      if (!p) continue;
      var tag = p.nodeName;
      if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") continue;
      if (p.closest && p.closest(".no-i18n")) continue;
      if (!origMap.has(n)) origMap.set(n, n.nodeValue);
      var orig = origMap.get(n);
      var key = orig.replace(/\s+/g, " ").trim();
      if (!key) continue;
      if (LANG === "it" || !dict) { if (n.nodeValue !== orig) n.nodeValue = orig; continue; }
      var tr = dict[key];
      if (tr != null) {
        var lead = (orig.match(/^\s*/) || [""])[0];
        var trail = (orig.match(/\s*$/) || [""])[0];
        n.nodeValue = lead + tr + trail;
      } else if (n.nodeValue !== orig) { n.nodeValue = orig; }
    }
  }

  function setLang(lang) {
    LANG = (lang === "it" || I18N[lang]) ? lang : "it";
    translateRoot(document.body);
    document.documentElement.lang = LANG;
    var cl = document.getElementById("loc-country-lbl"); if (cl) cl.textContent = COUNTRY[LANG] || COUNTRY.it;
    var ll = document.getElementById("loc-lang-lbl"); if (ll) ll.textContent = CODE[LANG] || "IT";
    Array.prototype.forEach.call(document.querySelectorAll(".loc-menu li"), function (li) {
      li.classList.toggle("active", li.getAttribute("data-lang") === LANG);
    });
  }
  window.__retranslate = function () { translateRoot(document.body); };
  /* traduzione MIRATA su un sottoalbero: evita di ri-scansionare tutta la pagina ad ogni click (INP) */
  window.__retranslateEl = function (el) { if (el) translateRoot(el); };

  function closeAll() {
    Array.prototype.forEach.call(document.querySelectorAll(".loc-wrap.open"), function (w) {
      w.classList.remove("open");
      var b = w.querySelector(".loc-sel"); if (b) b.setAttribute("aria-expanded", "false");
    });
  }
  function setupMenu(btnId) {
    var btn = document.getElementById(btnId);
    if (!btn) return;
    var wrap = btn.closest(".loc-wrap");
    var menu = wrap.querySelector(".loc-menu");
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = wrap.classList.contains("open");
      closeAll();
      if (!open) { wrap.classList.add("open"); btn.setAttribute("aria-expanded", "true"); }
    });
    Array.prototype.forEach.call(menu.querySelectorAll("li"), function (li) {
      li.addEventListener("click", function (e) {
        e.stopPropagation();
        setLang(li.getAttribute("data-lang"));
        closeAll();
      });
    });
  }
  document.addEventListener("click", closeAll);
  setupMenu("loc-country");
  setupMenu("loc-lang");

  var nav = (navigator.language || "it").slice(0, 2).toLowerCase();
  setLang(I18N[nav] ? nav : "it");
})();

/* ============================================================
   PAGINE ASSISTENZA — apertura/chiusura overlay + hash routing
   ============================================================ */
(function () {
  "use strict";
  var cms = document.getElementById("cms");
  if (!cms) return;
  var PAGES = ["contatti", "privacy", "spedizioni", "resi", "termini", "revocazione"];

  function openPage(name) {
    var pages = cms.querySelectorAll(".cms-page");
    var found = false;
    Array.prototype.forEach.call(pages, function (pg) {
      var on = pg.getAttribute("data-page") === name;
      pg.classList.toggle("active", on);
      if (on) found = true;
    });
    if (!found && pages[0]) pages[0].classList.add("active");
    cms.hidden = false;
    document.body.style.overflow = "hidden";
    cms.scrollTop = 0;
    if (("#" + name) !== location.hash) { try { history.replaceState(null, "", "#" + name); } catch (e) {} }
  }
  function closePage() {
    cms.hidden = true;
    document.body.style.overflow = "";
    if (PAGES.indexOf(location.hash.replace("#", "")) >= 0) { try { history.replaceState(null, "", "#top"); } catch (e) {} }
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-open]"), function (a) {
    a.addEventListener("click", function (e) { e.preventDefault(); openPage(a.getAttribute("data-open")); });
  });
  Array.prototype.forEach.call(cms.querySelectorAll(".cms-back, .cms-logo"), function (b) {
    b.addEventListener("click", function (e) { e.preventDefault(); closePage(); });
  });
  Array.prototype.forEach.call(cms.querySelectorAll(".cms-submit"), function (b) {
    b.addEventListener("click", function (e) { e.preventDefault(); alert("ANTEPRIMA — In produzione il messaggio viene inviato al nostro supporto."); });
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !cms.hidden) closePage(); });

  function fromHash() {
    var h = location.hash.replace("#", "");
    if (PAGES.indexOf(h) >= 0) openPage(h); else if (!cms.hidden) closePage();
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
})();

/* ============================================================
   VIDEO PROOF — autoplay muto + loop infinito garantito
   ============================================================ */
(function () {
  "use strict";
  var vids = Array.prototype.slice.call(document.querySelectorAll(".vcard video"));
  if (!vids.length) return;
  vids.forEach(function (v) {
    v.muted = true; v.defaultMuted = true; v.setAttribute("muted", "");
    v.playsInline = true; v.setAttribute("playsinline", "");
    v.preload = "none"; v.setAttribute("preload", "none"); /* niente download finché non serve */
  });
  function play(v) { if (v.preload !== "auto") { v.preload = "metadata"; } var p = v.play(); if (p && p.catch) p.catch(function () {}); }
  /* riproduce SOLO i video visibili, mette in pausa quelli fuori schermo (perf/INP) */
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var v = e.target;
        if (e.isIntersecting && !document.hidden) play(v);
        else { try { v.pause(); } catch (err) {} }
      });
    }, { threshold: 0.25 });
    vids.forEach(function (v) { io.observe(v); });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) vids.forEach(function (v) { try { v.pause(); } catch (e) {} });
    });
  } else {
    vids.forEach(play);
  }
})();

/* ============================================================
   CARRELLO (drawer) — carrello con STATO (vuoto/pieno), regali
   GRATIS, cestino di rimozione, stepper, countdown, checkout.
   ============================================================ */
(function () {
  "use strict";
  var cart = document.getElementById("cart");
  var buy = document.getElementById("buy-btn");
  if (!cart || !buy) return;

  var euro = function (n) { return "€" + n.toFixed(2).replace(".", ","); };
  var UNIT = 29.90;
  var body = document.getElementById("cart-body");
  var elCount = document.getElementById("cart-count");
  var elTotal = document.getElementById("cart-total");
  var headerCart = document.getElementById("header-cart");
  var headerDot = document.getElementById("header-cart-dot");
  var checkout = document.getElementById("cart-checkout");
  var expressBtn = document.getElementById("express-toggle");
  var EXPRESS_VARIANT = 47792310714553, EXPRESS_PRICE = 2.99, express = false;
  function orderTotal() { return state.tier ? (DATA[state.tier].price + (express ? EXPRESS_PRICE : 0)) : 0; }

  var TIERS = ["entry", "hero", "value"]; /* ordine per lo stepper */
  var DATA = {
    entry: { units: 2, price: 34.90, gifts: ["guida"] },
    hero:  { units: 4, price: 59.90, gifts: ["guida", "mappa", "sped"] },
    value: { units: 6, price: 89.90, gifts: ["guida", "mappa", "sped"] }
  };
  var GIFTS = {
    guida: { name: "Guida P.R.E.D.A.", img: "assets/img/regalo-guida.webp", was: 19.90 },
    sped:  { name: "Spedizione espressa", img: "assets/img/regalo-spedizione.webp", was: 6.99 },
    mappa: { name: "La Mappa dei Punti Caldi", img: "https://cdn.shopify.com/s/files/1/0784/4790/2905/files/guidaim.png?v=1783271594", was: 14.90 }
  };

  /* stato: tier === null -> carrello vuoto */
  var state = { tier: null, removed: {} };

  function selectedTier() {
    var sel = document.querySelector(".bundle.selected");
    var t = sel ? sel.getAttribute("data-tier") : "hero";
    return DATA[t] ? t : "hero";
  }
  function activeGifts(tier) {
    return (DATA[tier].gifts || []).filter(function (g) { return !state.removed[g]; });
  }
  function count() {
    if (!state.tier) return 0;
    return DATA[state.tier].units + activeGifts(state.tier).length;
  }
  function syncBadges() {
    var n = count();
    if (elCount) elCount.textContent = "(" + n + ")";
    if (headerDot) { headerDot.textContent = n; headerDot.hidden = (n === 0); }
  }

  function render() {
    var empty = !state.tier;
    cart.classList.toggle("empty", empty);

    if (empty) {
      body.innerHTML =
        '<div class="cart-empty">' +
          '<span class="ce-ico"><svg class="gi"><use href="#ic-bag"/></svg></span>' +
          '<p class="ce-ttl">Il carrello è vuoto</p>' +
          '<p class="ce-sub">Scopri le offerte qui sotto e aggiungi il tuo Scratchy.</p>' +
          '<button class="ce-cta" type="button" data-cart-close>Continua lo shopping</button>' +
        '</div>';
      if (elTotal) elTotal.textContent = euro(0);
      if (checkout) checkout.disabled = true;
      syncBadges();
      if (window.__retranslateEl) window.__retranslateEl(body);
    else if (window.__retranslate) window.__retranslate();
      return;
    }

    var tier = state.tier, d = DATA[tier];
    var reg = d.units * UNIT, i = TIERS.indexOf(tier);
    /* risparmio TOTALE = sconto sugli Scratchy + valore dei regali inclusi */
    var giftsValue = activeGifts(tier).reduce(function (s, g) { return s + (GIFTS[g] && GIFTS[g].was ? GIFTS[g].was : 0); }, 0);
    var save = (reg - d.price) + giftsValue;
    var html = "";

    html += '<div class="c-item c-main">' +
      '<img class="c-thumb" src="assets/img/scratchy-1.webp" alt="Scratchy" />' +
      '<div class="c-mid"><div class="c-name">Scratchy</div>' +
        '<div class="c-qty">' +
          '<button class="c-step" type="button" data-step="-1" aria-label="Riduci"' + (i <= 0 ? ' disabled' : '') + '>−</button>' +
          '<span class="c-num">' + d.units + '</span>' +
          '<button class="c-step" type="button" data-step="1" aria-label="Aumenta"' + (i >= TIERS.length - 1 ? ' disabled' : '') + '>+</button>' +
        '</div>' +
      '</div>' +
      '<div class="c-right"><s class="c-was">' + euro(reg) + '</s><span class="c-now">' + euro(d.price) + '</span>' +
        '<span class="c-save">Risparmi <b>' + euro(save) + '</b></span>' +
        '<button class="c-del" type="button" data-remove="main" aria-label="Rimuovi dal carrello"><svg class="gi"><use href="#ic-trash"/></svg></button></div>' +
      '</div>';

    activeGifts(tier).forEach(function (g) {
      var gi = GIFTS[g];
      /* i regali NON sono rimovibili singolarmente: spariscono solo togliendo Scratchy */
      var gthumb = gi.img
        ? '<img class="c-thumb" src="' + gi.img + '" alt="" />'
        : '<span class="c-thumb c-thumb-ico"><svg class="gi"><use href="#' + gi.icon + '"/></svg></span>';
      html += '<div class="c-item c-gift"><span class="c-elbow"></span>' +
        gthumb +
        '<div class="c-mid"><div class="c-name">' + gi.name + '</div><span class="c-incluso">Incluso nell\'offerta</span></div>' +
        '<div class="c-right">' + (gi.was ? '<s class="c-was">' + euro(gi.was) + '</s>' : '') +
        '<span class="c-free">Gratis</span></div>' +
        '</div>';
    });

    body.innerHTML = html;
    if (elTotal) elTotal.textContent = euro(orderTotal());
    if (checkout) checkout.disabled = false;
    syncBadges();

    Array.prototype.forEach.call(body.querySelectorAll(".c-step"), function (btn) {
      btn.addEventListener("click", function () {
        var dir = parseInt(btn.getAttribute("data-step"), 10);
        var ci = TIERS.indexOf(state.tier);
        var ni = Math.max(0, Math.min(TIERS.length - 1, ci + dir));
        if (ni === ci) return;
        state.tier = TIERS[ni];
        state.removed = {};
        var lbl = document.querySelector('.bundle[data-tier="' + state.tier + '"]');
        if (lbl) lbl.click(); /* aggiorna anche la buy box + "Cosa ricevi" */
        render();
      });
    });
    Array.prototype.forEach.call(body.querySelectorAll(".c-del"), function (btn) {
      btn.addEventListener("click", function () {
        var what = btn.getAttribute("data-remove");
        if (what === "main") { state.tier = null; state.removed = {}; }
        else { state.removed[what] = true; }
        render();
      });
    });

    if (window.__retranslateEl) window.__retranslateEl(body);
    else if (window.__retranslate) window.__retranslate();
  }

  function show() {
    cart.hidden = false;
    cart.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    requestAnimationFrame(function () { cart.classList.add("show"); });
  }
  function open() { render(); show(); }                                   /* apre sempre (anche vuoto) */
  function addToCart() { state.tier = selectedTier(); state.removed = {}; render(); show(); }
  function close() {
    cart.classList.remove("show");
    cart.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    setTimeout(function () { cart.hidden = true; }, 300);
  }

  buy.addEventListener("click", function (e) { e.preventDefault(); addToCart(); });
  if (headerCart) headerCart.addEventListener("click", function (e) { e.preventDefault(); open(); });
  if (expressBtn) expressBtn.addEventListener("click", function () {
    express = !express;
    expressBtn.setAttribute("aria-checked", express ? "true" : "false");
    if (elTotal && state.tier) elTotal.textContent = euro(orderTotal());
  });
  cart.addEventListener("click", function (e) {
    if (e.target.closest("[data-cart-close]")) close();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !cart.hidden) close(); });
  if (checkout) checkout.addEventListener("click", function () {
    if (checkout.disabled) return;
    alert("ANTEPRIMA — In produzione qui parte il checkout sicuro.");
  });

  /* badge iniziale: all'ingresso il carrello è vuoto */
  syncBadges();

  /* countdown urgenza: 10:00 -> 0 -> riparte; persiste nella sessione */
  var clock = document.getElementById("cart-clock");
  if (clock) {
    var KEY = "scratchy_cart_deadline", LEN = 10 * 60 * 1000;
    var dl = parseInt(sessionStorage.getItem(KEY), 10);
    if (!dl || dl < Date.now()) { dl = Date.now() + LEN; try { sessionStorage.setItem(KEY, dl); } catch (e) {} }
    function tick() {
      var ms = dl - Date.now();
      if (ms <= 0) { dl = Date.now() + LEN; try { sessionStorage.setItem(KEY, dl); } catch (e) {} ms = LEN; }
      var s = Math.floor(ms / 1000), m = Math.floor(s / 60), ss = s % 60;
      clock.textContent = (m < 10 ? "0" : "") + m + ":" + (ss < 10 ? "0" : "") + ss;
    }
    tick(); setInterval(tick, 1000);
  }
})();
