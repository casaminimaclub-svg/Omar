# SCRATCHY — Product Page (ANTEPRIMA / ricostruzione da zero)

Ricostruzione **da zero** della product page di SCRATCHY, costruita come **anteprima**.
Lo store attivo (tryscratchy.com) **non viene toccato**: resta online a vendere.
Quando questa pagina sarà approvata, la porteremo su Shopify.

## Come aprirla
Apri `index.html` in un browser (doppio clic), oppure servila in locale:

```bash
python3 -m http.server 8000
# poi apri http://localhost:8000
```

## Struttura file
- `index.html` — la pagina (9 sezioni, mobile-first)
- `assets/styles.css` — stile (palette terapia, CTA ad alto contrasto)
- `assets/script.js` — selettore kit, riepilogo prezzo/rate, CTA sticky

## Fedeltà ai brief
Costruita seguendo i due documenti operativi:

**Doc 1 — Il Messaggio**
- Frame **terapia ambientale**, mai giocattolo · zero anglicismi
- Causa radice unica: **IFC (Ipostimolazione Felina Cronica)**
- Regola **"perché" prima di "come"** (la prima metà spiega il perché; il "come" arriva alla sezione 3)
- **"Non è colpa tua"** solo dopo aver aperto la ferita
- Ogni claim ancorato a una spiegazione/fonte reale · nessun numero di prova sociale inventato

**Doc 2 — L'Esecuzione**
- Architettura a **9 sezioni** (hero → problema/causa → come funziona → benefici → CTA intermedio → prova/autorità → tabella comparativa → offerta/kit → FAQ/close)
- Hero completo nel primo schermo · CTA sticky guidata dal beneficio (mai "Aggiungi al carrello")
- Kit a 3 tier con **default sul 2+2** (€59,80, "Il più scelto"), risparmi in grassetto, costo-per-giorno, rate Scalapay/Klarna
- Tabella comparativa "cura la causa vs cura il sintomo" · FAQ dalle obiezioni reali · garanzia 60 giorni · close duro

## Da completare con dati reali (placeholder nel codice)
- **Recensioni**: ora sono di esempio → sostituire con recensioni reali (es. Judge.me)
- **Valutazione 4,8/5 e "migliaia di proprietari"**: confermare con i dati veri
- **Immagini hero**: ora usano le immagini prodotto Shopify esistenti → ideale una foto/video di vita reale del gatto che usa SCRATCHY (+133% conversione secondo il brief)
- **Prezzo barrato 3+3 (da €89,70)**: deve corrispondere a uno storico di prezzo reale (conformità AGCM)
- **Link checkout/carrello**: in anteprima i bottoni sono segnaposto; in produzione collegano al carrello Shopify del kit selezionato
