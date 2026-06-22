/* ============================================================
   SCRATCHY — Product Page (PREVIEW)
   Interazioni: selettore kit, riepilogo prezzo/rate, CTA sticky.
   Vanilla JS, zero dipendenze (priorità velocità < 2s su mobile).
   ============================================================ */
(function () {
  "use strict";

  var euro = function (n) {
    return "€" + n.toFixed(2).replace(".", ",");
  };

  var form = document.getElementById("kit-form");
  var kits = Array.prototype.slice.call(document.querySelectorAll(".kit"));
  var sumName = document.getElementById("sum-name");
  var sumTotal = document.getElementById("sum-total");
  var sumRate = document.getElementById("sum-rate");
  var stickyName = document.getElementById("sticky-name");

  function selectKit(kit) {
    kits.forEach(function (k) { k.classList.remove("selected"); });
    kit.classList.add("selected");
    var input = kit.querySelector("input");
    if (input) input.checked = true;

    var price = parseFloat(kit.getAttribute("data-price"));
    var name = kit.getAttribute("data-name");

    if (sumName) sumName.textContent = name + " GRATIS";
    if (sumTotal) sumTotal.textContent = euro(price);
    if (sumRate) sumRate.textContent = euro(price / 3);
    if (stickyName) stickyName.textContent = name + " · " + euro(price);
  }

  kits.forEach(function (kit) {
    kit.addEventListener("click", function () { selectKit(kit); });
    var input = kit.querySelector("input");
    if (input) {
      input.addEventListener("change", function () {
        if (input.checked) selectKit(kit);
      });
    }
  });

  // inizializza sul kit di default (2+2)
  var pre = document.querySelector(".kit.selected") || kits[0];
  if (pre) selectKit(pre);

  // bottone acquisto: in anteprima porta semplicemente all'offerta
  var buy = document.getElementById("buy-btn");
  if (buy) {
    buy.addEventListener("click", function (e) {
      e.preventDefault();
      // In produzione qui parte l'aggiunta al carrello Shopify del kit selezionato.
      var sel = document.querySelector(".kit.selected");
      var name = sel ? sel.getAttribute("data-name") : "Kit";
      alert("ANTEPRIMA — In produzione: aggiunta al carrello di " + name + ".");
    });
  }

  // ===== Sticky CTA: compare dopo l'hero, si nasconde sopra l'offerta =====
  var sticky = document.getElementById("sticky");
  var hero = document.querySelector(".hero");
  var offerta = document.getElementById("offerta");

  function onScroll() {
    if (!sticky || !hero) return;
    var heroBottom = hero.getBoundingClientRect().bottom;
    var pastHero = heroBottom < 0;

    var beforeOffer = true;
    if (offerta) {
      var oTop = offerta.getBoundingClientRect().top;
      beforeOffer = oTop > window.innerHeight; // offerta non ancora visibile
    }
    if (pastHero && beforeOffer) sticky.classList.add("show");
    else sticky.classList.remove("show");
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();
})();
