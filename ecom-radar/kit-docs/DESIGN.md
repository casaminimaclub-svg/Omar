---
name: Ecom Radar
description: Il banco notturno — scrivania d'intelligence letta di notte. La ricerca è la prima cosa della home; nero inchiostro, un solo accento che si scalda per dire l'intensità, e carattere/accento/densità scelti dall'utente.
colors:
  ground: "#070809"
  plate: "#0d0f12"
  plate-2: "#14171c"
  plate-3: "#1c2027"
  sunk: "#0a0c0f"
  media-well: "#080a0d"
  line: "rgba(148,170,196,.13)"
  line-2: "rgba(148,170,196,.26)"
  ink: "#edf1f6"
  ink-2: "#9aa8b8"
  ink-3: "#6e7c8c"
  glass: "#4da3ff"
  glass-hover: "#7cbcff"
  glass-dim: "rgba(77,163,255,.20)"
  on-glass: "#04121f"
  dbz0: "#1b3a5c"
  dbz1: "#215a96"
  dbz2: "#1f79cf"
  dbz3: "#2f97f2"
  dbz4: "#5cb2ff"
  dbz5: "#96cfff"
  dbz6: "#dcefff"
  scrim: "rgba(5,8,12,.76)"
typography:
  display:
    fontFamily: "'Instrument Serif', Georgia, 'Times New Roman', serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1.05
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "'Instrument Serif', Georgia, serif"
    fontSize: "22px"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  metric:
    fontFamily: "'Instrument Serif', Georgia, serif"
    fontSize: "28px"
    fontWeight: 400
    letterSpacing: "-0.01em"
  body:
    fontFamily: "'Archivo', -apple-system, BlinkMacSystemFont, Arial, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tabular-nums"
  label:
    fontFamily: "'Archivo', sans-serif"
    fontSize: "9.5px"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "0.14em"
  readout:
    fontFamily: "'Geist Mono', ui-monospace, Menlo, monospace"
    fontSize: "11.5px"
    fontWeight: 400
rounded:
  sm: "4px"
  md: "8px"
  lg: "14px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "18px"
  xl: "26px"
  xxl: "30px"
---

# Design System: Ecom Radar

## L'architettura della home

La home **non è un cruscotto**: è una pagina di ricerca. Nell'ordine, dall'alto:

1. **Il campo di ricerca**, centrato e grande — l'unica cosa che l'occhio trova per prima. Cerca
   nell'archivio locale mentre si scrive, e raggruppa le risposte per *brand · pagine · domini ·
   landing · inserzioni*. Accanto, l'azione che impegna: **Scansiona la Ad Library**, che va a
   prendere fuori quello che dentro non c'è.
2. **Le scorciatoie**: le piu forti, lanciate a 7 giorni, native, video, statiche, con KPI reali.
3. **La riga dei numeri**, sottile: live, live da 30+ giorni, nuove 7 giorni, reach EU, spesa
   stimata, KPI reali.
4. **Il feed** delle piu forti in onda, griglia densa con i filtri di formato sulla stessa riga
   del titolo, e a destra un **binario** con i brand in classifica, i lanci della settimana e gli
   angoli vivi.

Quando si cerca, il feed si ritira e i risultati prendono il suo posto: una schermata sola, mai
una vista diversa in cui andare.

## Aspetto scelto dall'utente

Il bottone in barra apre **Aspetto** e ogni scelta resta (localStorage):

- **Carattere** — Geist (default) · Grotesque (Bricolage + Inter Tight) · Editoriale (Instrument
  Serif + Archivo) · Sistema · Mono. Il tema governa `--sans`, `--serif`, il peso e la crenatura
  del display: nessuna regola scrive un font a mano.
- **Accento** — azzurro · ciano · viola · verde · ambra. Cambiando l'accento cambia **anche la
  scala d'intensita**, che e sempre quella stessa tinta che si scalda.
- **Densita** — compatta · media · comoda: corpo del testo e respiro delle viste.

## Il mondo

**Il banco notturno.** Non un cruscotto: una scrivania d'intelligence letta di notte. La
superficie è nero inchiostro; le sezioni non sono card che galleggiano, sono **campi separati da
capelli**, come le colonne di una pagina stampata. Chi guarda deve poter leggere lo stato del
mercato in una frase prima di leggerlo in una tabella.

**Tre voci tipografiche, ognuna con un mestiere.**
- **Instrument Serif** dice *cosa sta succedendo*: i titoli, i numeri che contano, le testate di
  sezione. È la voce editoriale, l'unica che ha diritto di essere grande.
- **Archivo** dice *com'è fatto*: interfaccia, etichette, copy, tabelle.
- **Geist Mono** dice *quanto*: id, timestamp, tick, celle numeriche, basi di calcolo.

**Un solo colore.** Azzurro `#4da3ff`. È lo stato vivo del sistema — link, focus, il pulsante
che impegna, la voce attiva del menu, il cursore della timeline. E **la stessa tinta si scalda**
per dire l'intensità: la scala a sette passi va dal blu profondo (`dbz0`) al bianco d'azzurro
(`dbz6`). Nessun arcobaleno, nessun secondo accento: se una cosa è più forte, è più chiara.

## Regole con un nome

**Nessun colore senza un valore.** Una tinta compare solo se dietro c'è un numero. Un passo della
scala significa una fascia d'intensità; l'azzurro pieno significa "questo è vivo adesso".

**Il titolo prima del numero.** Ogni vista si apre con una frase in serif che dichiara lo stato
("23.848 inserzioni sono *in onda* adesso"), poi la riga dei numeri. Mai il contrario.

**Capello prima dell'ombra.** Si separa con 1px di `line`, poi con un gradino tonale, e solo
all'ultimo con un'ombra — che esiste in tre posti soli: la cella che si solleva, il pannello
laterale, il toast.

**Il pozzo scuro.** Ogni immagine sta su `media-well`, mai su `plate`: una miniatura che non
carica resta comunque una finestra, non un buco.

**Peso, non misura.** Nel corpo dell'interfaccia la scala tipografica è minuta e costante; la
gerarchia la fanno il serif e il peso, non il salto di dimensione.

## Struttura

Barra di stazione 58px (marchio, readout, ricerca, orologio Europe/Rome), rail di navigazione
232px con l'indicatore azzurro a filo sulla voce attiva, area principale che scorre con padding
`26px 30px 72px`. Un solo breakpoint a 900px: la rail diventa una riga orizzontale scorrevole, i
readout della home passano a griglia 3×2, il pannello laterale va a tutta larghezza.

**La home** è una pagina, non un cruscotto: titolo editoriale, occhiello di contesto, la riga dei
sei numeri su capelli, poi la griglia dei campi (le più forti in onda · brand · lanciate a 7
giorni · movimenti · angoli vivi) tenuti insieme da un bordo unico da 14px di raggio, divisi da
capelli da 1px.

## Da non fare

- Un secondo accento. Se serve distinguere, si usa un passo della scala o il peso.
- Card dentro card. I campi della home sono divisi da capelli, non da contorni annidati.
- Alzare la dimensione per dare importanza a un testo d'interfaccia: si cambia voce (serif) o peso.
- Fondi chiari, pannelli colorati, testo in gradiente, ombre colorate senza offset.
- Mono come costume "tecnico": è solo per numeri, id, orari e basi di calcolo.
