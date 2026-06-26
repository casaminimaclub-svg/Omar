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
  var GIFT_GUIDA = { name: "Guida P.R.E.D.A.", img: "assets/img/regalo-guida.webp", gift: true, was: "€19,90" };
  var GIFT_SPED = { name: "Spedizione prioritaria", img: "assets/img/regalo-spedizione.webp", gift: true };
  var RECEIVE = {
    entry: [
      { name: "2 Scratchy", img: "assets/img/regalo-scratchy.webp" }
    ],
    hero: [
      { name: "4 Scratchy", img: "assets/img/regalo-scratchy.webp" },
      GIFT_GUIDA,
      GIFT_SPED
    ],
    value: [
      { name: "6 Scratchy", img: "assets/img/regalo-scratchy.webp" },
      GIFT_GUIDA,
      GIFT_SPED
    ]
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
    if (window.__retranslate) window.__retranslate();
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

  /* ---------- BOTTONE ACQUISTO (anteprima) ---------- */
  var buy = document.getElementById("buy-btn");
  if (buy) {
    buy.addEventListener("click", function (e) {
      e.preventDefault();
      var sel = document.querySelector(".bundle.selected");
      var name = sel ? sel.getAttribute("data-name") : "Kit";
      alert("ANTEPRIMA — In produzione: aggiunta al carrello di " + name + ".");
    });
  }

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
