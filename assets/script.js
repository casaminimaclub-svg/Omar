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
  var RECEIVE = {
    entry: [
      { name: "2 Scratchy", sub: "il prodotto", img: "assets/img/scratchy-1.webp" }
    ],
    hero: [
      { name: "4 Scratchy", sub: "il prodotto", img: "assets/img/scratchy-2.webp" },
      { name: "Guida P.R.E.D.A.", sub: "il protocollo passo-passo", icon: "ic-book", gift: true, was: "€19,90" },
      { name: "Spedizione prioritaria", sub: "consegna più veloce", icon: "ic-truck", gift: true }
    ],
    value: [
      { name: "6 Scratchy", sub: "il prodotto", img: "assets/img/scratchy-3.webp" },
      { name: "Guida P.R.E.D.A.", sub: "il protocollo passo-passo", icon: "ic-book", gift: true, was: "€19,90" },
      { name: "Spedizione prioritaria", sub: "consegna più veloce", icon: "ic-truck", gift: true }
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
