/* ============================================================
   SCRATCHY — Product Page (PREVIEW v2)
   Galleria, selettore bundle (+ regali per tier), CTA sticky, scroll.
   Vanilla JS, zero dipendenze.
   ============================================================ */
(function () {
  "use strict";

  var euro = function (n) { return "€" + n.toFixed(2).replace(".", ","); };

  /* ---------- GALLERIA ---------- */
  var mainImg = document.getElementById("main-img");
  var thumbs = document.getElementById("thumbs");
  if (thumbs && mainImg) {
    thumbs.addEventListener("click", function (e) {
      var t = e.target;
      if (t.tagName !== "IMG") return;
      mainImg.src = t.src;
      Array.prototype.forEach.call(thumbs.children, function (c) { c.classList.remove("active"); });
      t.classList.add("active");
    });
  }

  /* ---------- BUNDLE ---------- */
  var bundles = Array.prototype.slice.call(document.querySelectorAll(".bundle"));
  var sumRate = document.getElementById("sum-rate");
  var stickyName = document.getElementById("sticky-name");
  var giftHint = document.getElementById("gift-hint");
  var gifts = Array.prototype.slice.call(document.querySelectorAll("#gift-list .gift"));

  function applyGifts(tier) {
    // regali "hero" (Guida P.R.E.D.A. + prioritaria) attivi solo per 2+2 e 3+3
    var heroTiers = (tier === "hero" || tier === "value");
    gifts.forEach(function (g) {
      var need = g.getAttribute("data-min");
      var on = (need === "all") || heroTiers;
      g.classList.toggle("locked", !on);
    });
    if (giftHint) {
      if (tier === "entry") giftHint.textContent = "Passa al Kit 2+2 per sbloccare la Guida P.R.E.D.A. e la spedizione prioritaria";
      else giftHint.textContent = "Inclusi con il kit selezionato";
    }
  }

  function selectBundle(b) {
    bundles.forEach(function (x) { x.classList.remove("selected"); });
    b.classList.add("selected");
    var input = b.querySelector("input");
    if (input) input.checked = true;

    var price = parseFloat(b.getAttribute("data-price"));
    var name = b.getAttribute("data-name");
    var tier = b.getAttribute("data-tier");

    if (sumRate) sumRate.textContent = euro(price / 3);
    if (stickyName) stickyName.textContent = name + " · " + euro(price);
    applyGifts(tier);
  }

  bundles.forEach(function (b) {
    b.addEventListener("click", function () { selectBundle(b); });
    var input = b.querySelector("input");
    if (input) input.addEventListener("change", function () { if (input.checked) selectBundle(b); });
  });

  var pre = document.querySelector(".bundle.selected") || bundles[0];
  if (pre) selectBundle(pre);

  /* ---------- SCROLL verso la buy box (CTA "#top") ---------- */
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
      // In produzione: aggiunta al carrello Shopify del kit selezionato.
      alert("ANTEPRIMA — In produzione: aggiunta al carrello di " + name + ".");
    });
  }

  /* ---------- STICKY CTA ---------- */
  var sticky = document.getElementById("sticky");
  var hero = document.querySelector(".hero");
  function onScroll() {
    if (!sticky || !hero) return;
    var pastHero = hero.getBoundingClientRect().bottom < 0;
    sticky.classList.toggle("show", pastHero);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();
})();
