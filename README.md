# SCRATCHY — Product Page (ANTEPRIMA / ricostruzione da zero)

Ricostruzione **da zero** della product page di SCRATCHY, costruita come **anteprima**.
Lo store attivo (tryscratchy.com) **non viene toccato**: resta online a vendere.
Struttura e design **ispirati ad Argos Pets** (stesso framework dei brief), con identità SCRATCHY.

## Come aprirla
Apri `index.html` in un browser, oppure servila in locale:

```bash
python3 -m http.server 8000   # poi apri http://localhost:8000
```

## Struttura file
- `index.html` — la pagina · `assets/styles.css` — stile · `assets/script.js` — interazioni

## Struttura pagina (ispirata ad Argos)
- **Hero con buy-box completa** nel primo schermo: galleria + thumbnail, titolo, stelle,
  riquadro 4 icone, barra scarsità, **selettore bundle compatto** (default 2+2),
  **regali "GRATIS €valore"** che si sbloccano per tier, CTA, accordion (caratteristiche, garanzia, ecc.)
- Problema + 4 sintomi → perché ha fallito → **diagnosi IFC** + assoluzione
- Come funziona (3 fasi) → benefici → CTA intermedio
- Prova: **barre distribuzione recensioni** (5★→1★) + recensioni + fonti reali
- Tabella comparativa → FAQ → close duro + CTA finale → footer scuro

## Fedeltà ai brief
- Frame **terapia ambientale**, mai giocattolo · zero anglicismi · garanzia **60 giorni** · SCRATCHY ovunque
- Causa radice unica **IFC** · regola **"perché" prima di "come"** · **"non è colpa tua"** dopo la ferita
- Kit a 3 tier, **default 2+2** (€59,80), rate Scalapay/Klarna, costo/valore esplicitato
- Titoli con enfasi corsivo-colorata stile Argos · CTA guidate dal beneficio (mai "Aggiungi al carrello")

## Confermato dal cliente
- **Numeri** (4,8/5, "migliaia di proprietari italiani") → mantenuti
- **Recensioni** → mantenute così come sono (non sostituite)

## Da rifinire più avanti
- **Immagini**: da realizzare (foto/video di vita reale del gatto che usa SCRATCHY → +133% conversione).
  Per ora la galleria usa le immagini prodotto già su Shopify.
- **Prezzo barrato 3+3 (da €89,70)**: deve avere storico di prezzo reale (conformità AGCM).
- **Link checkout/carrello**: in anteprima i bottoni sono segnaposto; in produzione collegano al carrello Shopify del kit selezionato.
