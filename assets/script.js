/* ============================================================
   SCRATCHY — Product Page (PREVIEW v4)
   Galleria, selettore bundle (+ regali per tier), bottone "trova
   la dose", CTA sticky, scroll. Vanilla JS, zero dipendenze.
   ============================================================ */
(function () {
  "use strict";
  var euro = function (n) { return "€" + n.toFixed(2).replace(".", ","); };

  /* ---------- GALLERIA (navigazione a zampe) ---------- */
  var mainImg = document.getElementById("main-img");
  var paws = document.getElementById("paws");
  if (paws && mainImg) {
    paws.addEventListener("click", function (e) {
      var btn = e.target.closest(".paw");
      if (!btn) return;
      var src = btn.getAttribute("data-src");
      if (src) mainImg.src = src;
      Array.prototype.forEach.call(paws.children, function (c) { c.classList.remove("active"); });
      btn.classList.add("active");
    });
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

  function selectBundle(b) {
    bundles.forEach(function (x) { x.classList.remove("selected"); });
    b.classList.add("selected");
    var input = b.querySelector("input");
    if (input) input.checked = true;
    var price = parseFloat(b.getAttribute("data-price"));
    var name = b.getAttribute("data-name");
    if (sumRate) sumRate.textContent = euro(price / 3);
    if (stickyName) stickyName.textContent = name + " · " + euro(price);
    applyGifts(b.getAttribute("data-tier"));
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
})();
