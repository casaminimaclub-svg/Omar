---
tags: [playbook, ad-spy, competitor, toolchain]
creato: 2026-09-05
---
# Ecom Radar

Il radar competitor di seconda generazione: **si dà un URL di un brand e lo mappa fino al midollo**. Sostituisce nell'uso quotidiano la vecchia piattaforma Ad Spy (`localhost:3107/adspy.html`). Ispirato all'*Ecom Radar* di Mattia Paganelli visto in storia il 4 settembre 2026 ("The ads worth stealing this month": spesa stimata, reazioni, soglia winner, format tab, winner videos / currently running).

## Dove
- Codice: `~/ecom-radar/` (`radar/` motore, `public/index.html` UI, `data/radar.db` archivio, `data/studies/` dossier; media su Drive, vedi sotto).
- UI: **http://localhost:8772** (launchd `com.utente.ecom-radar`, KeepAlive).
- Refresh notturno: launchd `com.utente.ecom-radar.refresh` alle 05:30 (`radar refresh all`).
- CLI: `~/bin/radar` (add · refresh · study · transcribe · dossier · search · serve).

## Cosa fa per ogni brand
1. **Discover** — cerca nome e dominio nella Ad Library (tutti i paesi, per finestre di data) e tiene solo le ad che puntano al dominio del brand → emergono **tutte le pagine** che pubblicano per lui, comprese le pagine-persona/alias (es. Pureveen = "Dr. Christi Thompson" + "Linda Carey"; Metabolae = 7 pagine fra medici finti e "Blood Sugar Balance Community").
2. **Pull** — archivio **completo** di ogni pagina (attive + spente) **"sbucciando" l'archivio dal più recente al più vecchio** (peel): ogni pagina HTML dà il totale della finestra + le 30 ad più recenti; la data più vecchia fra le 30 diventa la frontiera della fetta successiva (+1 giorno di margine per il fuso di Meta). 1 richiesta ≈ 30 ad nuove, zero fette vuote, 3 worker in parallelo con ritmo unico. Trucchi: l'ordine "per rilevanza" dà 30 ad diverse (chiude le finestre ≤60 con 1 richiesta); un giorno con >30 ad si spacca per stato → media (video/image/**meme/none**: caroselli e DCO stanno negli ultimi due) → paese; il residuo irraggiungibile è dichiarato. Nessun cursore GraphQL: niente rate-limit `1675004`. Una pagina da 120 ad = 5-12 richieste in ~20 s (prima: 143 richieste in 6 min).
3. **Enrich** — trasparenza EU (DSA) per ogni ad idonea: reach totale, età×genere×paese, payer/beneficiary, info pagina (IG, follower, verifica). Query `AdLibraryV3AdDetailsQuery` replicata senza browser.
4. **Landings** — Playwright su ogni URL di destinazione (parametri di tracking rimossi): screenshot full-page mobile, testo, H1, prezzo, tipo (advertorial/listicle/quiz/VSL/PDP/home), stack (Shopify, Kaching, GemPages, Funnelish, Judge.me, Triple Whale, pixel…).
5. **Score** — intensità 0-100 = longevità × varianti (collation) × reach EU × reazioni + live; **spesa stimata** con base dichiarata (`eu_reach` → reach×1,8/1000×12$; `reactions` → 19,6 $/reazione, rapporto della board di Paganelli; `runtime` → proxy debole, mostrato tratteggiato).
6. **Study** — `radar study <id>`: Claude (CLI locale, sonnet) legge tutto il materiale e scrive il dossier in 10 sezioni (meccanismo, famiglie di hook, funnel, audience reale, cosa testano ora, cosa rubare, punti deboli, limiti dei dati). Appare nel rapporto di stazione.
7. **Transcribe** — whisper-cli locale sui top video (modello in `~/ad-spy/models`), testo cercabile; nello stesso passaggio nasce lo **storyboard** (8 fotogrammi 4×2).
8. **Creative** — `radar creative <id>`: Claude (sonnet, lotti di 12 ad) assegna a ogni ad hook, **famiglia di angolo** (etichette riusate per brand, così si sommano), meccanismo, persona, awareness, emozione, formato creativo, CTA style, "perché funziona". Le varianti della stessa collation ereditano. Stadio di trend calcolato: battle-tested ≥30 g · gaining 14–29 · new-test <14.
9. **OCR** — tesseract sulle statiche/caroselli (filtro anti-rumore): il testo dentro l'immagine entra nella ricerca e nell'analisi creativa.
10. **Impronta visiva** — dHash delle miniature: la stessa creatività caricata su più pagine alias si riconosce (`n_pages_same`, badge sulla cella, bonus nello score).
11. **Nei paraggi** — durante la discovery si contano gli altri advertiser incontrati (cloni, concorrenti, affiliati): nel rapporto di stazione con tasto «aggiungi».
12. **Digest** — dopo il refresh notturno `data/DIGEST.md` (nuove/spente/landing/pagine/angoli per brand), in UI sotto Movimenti. **CSV** della board filtrata. Vista **Analytics** (brand uno accanto all'altro: lanci/settimana, mix, vita delle ad, landing, angoli).

## Vista UI (mondo "stazione radar meteo")
- **Board**: report di mercato, una sola scala colore (blu→magenta) = intensità; tab formato; filtri brand/stato/periodo/età/tipo landing/paese; tasto `l` = **loop** (scrub degli ultimi 90 giorni: quali celle erano live quel giorno).
- **Brand → rapporto di stazione**: rete di pagine, ritmo di lancio per settimana, audience EU, stack, CTA, hook ricorrenti, landing, celle più intense, ultime lanciate, dossier.
- **Cella (drawer)**: video/immagine, tutti i media, copy, KPI, breakdown EU, landing con screenshot, varianti della stessa creatività, ad con lo stesso copy, ad sulla stessa landing, note.
- **Landing**, **Cerca tutto** (FTS locale + scansione live archiviata), **Movimenti** (nuove ad, spente, dossier).

## Media
Regola di Chry: niente media pesanti sul Mac. Qui i media sono **leggeri per costruzione**: miniature ridotte a ≤640 px (~50 KB), screenshot landing a 720 px (~300 KB), storyboard 4×2; i video non si salvano mai (streaming per l'anteprima, temp per whisper). Posizione: `data/{thumbs,lp,frames}` (`radar/paths.py`).
**Drive come archivio è possibile ma bloccato da macOS:** i processi avviati da launchd (server 8772, refresh 05:30) non leggono `~/Library/CloudStorage` senza *Full Disk Access* a `/usr/bin/python3`. Se Chry lo concede (Impostazioni → Privacy e sicurezza → Accesso completo al disco), basta aggiungere `RADAR_MEDIA=<Il mio Drive>/Ecom Radar/media` nei due plist: alla prima esecuzione `paths.migrate_legacy` sposta tutto da solo.

## Limiti onesti
- Spesa e impression reali NON sono pubbliche per le ad commerciali: la spesa è una stima con base dichiarata.
- Reach solo per ad consegnate in UE. Le reazioni arrivano solo da post boostati/feed capture.
- La ricerca per keyword ha totali gonfiati (matcha il copy): la discovery legge le ~1.200 ad più recenti per query, poi il pull per pagina fa la copertura completa.
- Gli URL media di fbcdn scadono: miniature in cache, video in streaming rinnovato al volo.

## Lezioni tecniche
- Il filtro data della Ad Library **si spegne quando min == max**: la fetta minima è di 2 giorni. La data di Meta può essere **avanti** rispetto al nostro `start_date` UTC (un'ad "di ieri" per noi è "di oggi" per il filtro): ogni frontiera va spostata di +1 giorno, altrimenti si perdono le ad al confine.
- La pagina HTML a volte arriva **senza il blocco risultati** (`no-results-block`): è transitorio, si riprova subito con la stessa sessione (dormire o cambiare identità peggiora solo il ritmo).
- I filtri `media_type=image/video` **non includono caroselli e DCO** (stanno in `meme`/`none`); `publisher_platforms` non partiziona nulla; `sort_data[direction]` è ignorato ma l'assenza di sort (rilevanza) cambia l'ordine.
- Le pagine-editore che lanciano centinaia di ad al giorno saturano la fetta minima: il budget va prima all'archivio nel tempo (coda a priorità) e poi alla coda densa; il residuo si dichiara.
- Un solo IP regge ~1 richiesta HTML ogni 2-3 s senza blocchi; la paginazione GraphQL va in rate-limit dopo poche decine di pagine/ora.
- SQLite in WAL: uno scrittore continuo affama gli altri (busy_timeout non basta). Transazioni cortissime (commit ogni 5 righe + 20 ms di respiro) e MAI una transazione aperta mentre si aspetta Claude o la rete.
- Le pagine-editore con migliaia di ad (es. "The Health Haven", 6.122 ad, ospita più brand) si leggono solo per le 150 finestre più recenti, salvo la pagina main.
- Le keyword hanno totali gonfiati (34k per "rosabella"): la discovery legge le ~1.200 ad più recenti per query; la copertura completa la fa il pull per pagina.
- I doc_id GraphQL ruotano: letti dai bundle JS e cachati 3 giorni, con fallback ai valori del 2026-09-05.

Vedi anche → [[Skill ad-spy]] · [[Protocollo Ads]] · [[Toolchain Claude Code]] · [[Mappa Repository]]

## KPI reali (like · commenti · condivisioni) — come funziona davvero
La Ad Library (HTML, GraphQL `AdDetails`, `render_ad` con token) **non espone** post id, permalink né reazioni: verificato sul payload completo (0 occorrenze di `story_fbid`/`post_id`/`permalink`). AdSpy e BigSpy prendono le reazioni dalle ad **servite nel feed** dalla loro rete di account/estensioni. Ecom Radar fa lo stesso con l'estensione `~/ad-spy/feedcap-extension` (Chrome loggato di Chry): ogni ad vista nel feed manda like/commenti/condivisioni + permalink a `/api/feedcap`, agganciata all'archivio per permalink o per pagina + inizio copy. Nel drawer dell'ad compaiono come «reazioni · feed», commenti, condivisioni e link al post. Per farsi servire le ad di un brand: aprire le sue landing (pixel) e poi scrollare il feed con l'estensione attiva.

## Avvio della coda e guardia del piano (2026-09-05)
- `~/bin/radar-batch [file]` lancia la coda in background con ambiente pulito (`claude -p` non deve ereditare la sessione Claude Code) e `caffeinate`. Un solo processo alla volta (lock `data/.batch.lock`).
- `radar/plan.py` legge `~/bin/plan-usage`: sopra `RADAR_CLAUDE_MAX` (55%) analisi creativa, consolidamento e dossier si saltano e riprendono al giro dopo. Meta, landing, miniature e transcript non consumano il piano.
- Blocco Meta («BLOCCO network»): una scoperta a zero pagine lascia il brand in coda (`new`) e fa pausa 5 min; due di fila fermano il batch. Rilanciare più tardi con `~/bin/radar-batch`.
- Analisi creativa: dopo 3 lotti vuoti di fila si ferma (Claude non risponde) e logga l'errore reale.
- UI console v2 (2026-09-06): palette ⌘K, tastiera completa, vista a righe, inspector con ← →, toolbar fissa. Dettagli in `~/ecom-radar/DESIGN.md`.
- `radar/finish.py` (2026-09-06): completa i brand pronti senza toccare Meta (analisi creativa mancante → punteggi → dossier); lanciarlo dopo un giro con la guardia del piano attiva. Limiter Meta: gap massimo 8 s (oltre, il giro notturno durava ore).

## Tassonomia dei formati (2026-09-06)
Tre formati, nessun carosello: **video** · **statica** (immagine promozionale, copy breve) · **native** (foto "da rullino" + primary text lungo, soglia 500 caratteri; filtro di Glenn "immagine + primary text lungo", MSL di Camacho). Colonna `ads.fmt`, modulo `radar/formats.py`; i caroselli/DCO si classificano dalla prima card. Le ad DCO hanno testo segnaposto `{{product.brand}}`: la Ad Library non espone il testo vero (si prende dalle card quando c'è).

## Vista brand v2
Tab Panoramica · Creatività · Pagine · Mercati (paesi UE con reach, ad, live, durata media, pagine per paese) · Landing (per tipo) · Angoli & hook · Dossier. Mix formati nella testata. «Salvate»: raccolta personale (board `Salvate`, bottone nel dettaglio). Intensità: longevità, iterazioni, reach EU e reach/giorno, KPI reali (like+2×commenti+3×share) solo se visti nel feed, +30 g live, pagine con la stessa creatività; le ad spente da >90 g perdono il 15%. Nessuna etichetta «winner».

## KPI fuori UE: decisione (2026-09-06)
Meta non dichiara reach/impression fuori dall'UE (solo `impressions_text` per ad politiche). I competitor: AdSpy/BigSpy/Minea prendono like/commenti/share dalle ad **servite** alla loro rete di account; Atria mostra stime. Un modello di stima dalle sole variabili pubbliche (durata, varianti, pagine, formato) calibrato sulle 4.336 ad con reach EU spiega solo il 19% della varianza (errore mediano ×4): **non si espone come "impression"**. Sistema adottato: (1) KPI reali da feed FB+IG via FeedCap (v2, estensione riscritta); (2) **reach proxy** = reach EU della stessa creatività (stessa collation o stesso hash) quando esiste, etichettata come tale; (3) intensità 0-100 come misura di forza. `radar/complete.py` rilegge le pagine con buco rispetto al dichiarato Meta.

- **FeedCap v2**: legge il testo visibile (FB nasconde lettere in span invisibili), scanner Instagram; diagnostica in `document.documentElement.dataset.feedcap`. Per farsi servire le ad dei brand: aprire le loro landing (pixel) e seguire le loro pagine.

- FeedCap **modalità raccolta**: aprire `instagram.com/#feedcap-harvest` (o facebook) → la pagina scorre da sola 8 minuti e cattura le sponsorizzate. Claude la avvia via Chrome MCP con un semplice navigate.

- 2026-09-07: dettaglio ad con **scomposizione dell'intensità** (longevità, iterazioni, reach, KPI reali…); tab Angoli & hook con **Headline** e **Meccanismi/USP**; analisi creativa estesa a 400 ad live per brand; transcript top 40 video per brand.

- Regola RAM (2026-09-07): whisper (1,7 GB) non parte se la RAM libera è sotto 1,5 GB; mai in parallelo con l analisi Claude. Miniature 480px q62, screenshot landing 600px q52: media locali sotto ~1,5 GB.


## Intelligence di secondo livello (2026-09-07)
- `radar/llm.py`: chiama Claude via CLI col modello migliore disponibile (Fable 5.1 → Opus 5 → Sonnet). CLI aggiornata a 2.1.263 per Fable.
- `radar/market.py` → `data/MARKET.md`: **Mappa del mercato** (chi domina, famiglie di angolo, hook template, pagine/funnel, chi copia chi, spazi vuoti, cosa farebbe ogni mentore, 10 mosse). Pannello in Analytics con «rigenera» (job `market`).
- `radar/brief.py`: **brief clean-room** di un'ad (scheletro sì, parole mai; regola Glenn + DMCA) dal dettaglio ad (job `brief`, colonna `ads.brief`).

- market.py legge dal vault `Consensus rules.md` e `Orientation guide.md` e li passa al modello (il CLI da solo non vede il vault).

- **Report pagina** (2026-09-07): `/api/page?id=` e vista `v-page` (live, età, mix, ritmo, angoli, headline, mercati, domini, landing, top ad) — dalla tab Pagine del brand e dalla palette.

- `scripts/ui_sweep.py`: scansione Playwright di tutte le viste (0 errori JS il 2026-09-07 15:00).

## Card in stile Atria e velocità della home (2026-09-08)
- **Anatomia della card** (rifatta sul modello Atria, come chiesto da Chry): intestazione con foto e nome della **pagina** che pubblica, pallino verde/grigio con i **giorni** di vita e la **reach EU** al posto del conteggio varianti, a destra **segnalibro** e menu. Sotto: copy, creatività, e piede con dominio · titolo · CTA, come lo mostra la Ad Library. Formato e intensità non stanno più nell'anteprima: sono nelle info dell'ad.
- **Velocità**: home da ~10 s a ~1,2 s. Indice di copertura per le statistiche, parametro `facets=0` per chi non usa le facet, cache su analytics/brands/brand, lista alleggerita (niente transcript/analisi/OCR nel payload).
- **Formati**: la regola distingue ora la statica disegnata dalla native con i marcatori d'offerta nel testo dell'immagine (Cordeddu: l'offerta è nell'immagine; Glenn: la native è una foto non-polished). OCR deduplicato per phash — una lettura per creatività, propagata ai gemelli.
- Verifica: 111 rotte API con dati veri, 0 errori; sweep Playwright, 0 errori console.

## SP Nutrition e la lezione della notte dell'8 settembre
- **SP Nutrition** (spnutrition-us.com, magnesio bisglicinato) mappato l'8 settembre: 15 pagine, di cui una rete di **pagine-persona** (Deborah Rustad, Jacob Nash, Alice Williams, Dr. May Garcia, Master Chen Wellness Tips) che porta la maggior parte del volume. 3.200 ad, 62 landing: 39 advertorial, 10 listicle, 5 VSL, 2 quiz. La landing segnalata da Chry, *Consumer Tested Men Listicle*, regge **503 ad**: è il test principale in corso, seconda solo all'advertorial magnesio (1.280).
- **Lezione (costata due ore di lavoro finto)**: `llm.ask` escludeva un modello dopo *un solo* errore, e un `ENOTFOUND` di rete bastava a bruciare tutti i modelli. Da lì ogni chiamata tornava vuota in zero secondi e il runner segnava i passi come riusciti. Ora gli errori passeggeri (rete, 5xx, rate limit) si aspettano e si ritentano, si esclude un modello solo se manca davvero, e **un "nessuna risposta" solleva un errore** invece di restituire `None` in silenzio: un lavoro non fatto deve rompere, non passare inosservato.

## Aggiornamento 2026-09-14 — freno termico, nicchie, buchi
- **Il Mac non deve mai scaldare**: i job del radar girano sotto `scripts/termico.sh` (agente launchd `com.utente.ecom-radar.termico`, sempre acceso): 20 s di lavoro / 25 s di pausa via SIGSTOP/SIGCONT, stop d'emergenza sopra carico 4,5. Tutti i job a `nice -n 19`, analisi creativa a 1 processo Claude. Il tempo non conta, la salute del Mac sì.
- **Nicchie a due livelli** nella sezione Brand: verticale ecommerce con emoji (`brands.niche`) + categoria di prodotto (`brands.area`). Catalogo in `data/NICCHIE.md`.
- **`ignoto (rimossa)`** = ad bannate da Meta (nessuna creatività restituita). Si recuperano solo con AdSpy/Atria.
- **Ad senza brand**: le pagine-persona spingono anche offerte di altri. Un dominio si attacca a un brand solo dopo averne aperto la destinazione; poi va in `brands.domains`.
- **Referto di completezza** `scripts/verifica.py`, ogni notte nel giro `daily.py` → `data/verifica.log`.
- **Vecchia piattaforma** (`~/ad-spy/adspy.db`): tiene ad che Meta non serve più; per Heusom ne ha date 1.294. Vale la pena di confrontarla per ogni competitor diretto.
- Heusom = brand 29: 6 pagine, 4 specie (cani/gatti/uccelli/conigli), tutto in PDP, `tryheusom.com`.
