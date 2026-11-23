# Ecom Radar: come si lavora un brand nuovo

Questo è il manuale per un'altra chat che deve rifare lo stesso lavoro su brand diversi, con un altro scopo e su una piattaforma separata. Contiene la procedura che uso io su Ecom Radar.

## 0. Piattaforma dedicata, senza toccare la mia
Non lavorare su `~/ecom-radar/data/radar.db` né sulla porta 8772. Copia il codice e partì da un database vuoto:
```
cp -R ~/ecom-radar/radar ~/ecom-radar/public ~/ecom-radar/scripts <NUOVA_CARTELLA>/
mkdir <NUOVA_CARTELLA>/data
```
Il database è sempre `data/radar.db` dentro la cartella in cui sta il codice, quindi la copia lavora su un database suo senza modificare niente. Avvia il server su un'altra porta con `RADAR_PORT=8773 python3 radar/server.py`. Lo schema del database si crea da solo al primo avvio.

## 1. Aggiungere un brand
```
python3 -u radar/brand.py add https://dominio.com      # da dentro la nuova cartella (non ~/bin/radar: punta alla mia)
```
- Usa il dominio pulito. Togli i parametri di tracking (utm, fbclid, ad_id…).
- Se il dominio non risponde, prova le varianti `.co`, `www.` e così via, come è successo con radivy.co.
- `add` crea il brand e fa un primo giro: discover, pull, enrich, landing, score.

## 2. Completamento approfondito (obbligatorio)
```
RADAR_FORZA=1 python3 scripts/completa_tutti.py <brand_id>
```
I passi, in ordine (`scripts/completa_tutti.py`):
1. **discover(max_requests=200)**: cerca nell'Ad Library il nome, il dominio, i domini alias e le keyword del brand. Trova tutte le pagine collegate, comprese quelle "persona" (Dr. X, Margaret Davis…).
2. **pull_pages(full=True)**: scarica l'archivio completo di ogni pagina, ad attive e non attive, tutti i paesi.
3. **thumbs**: un'anteprima JPG a 360px per ogni ad. Per i video si salva solo il primo frame, mai il video intero: il video si guarda dal link all'Ad Library.
4. **enrich**: reach EU, età, genere e paesi, dal dettaglio Meta.
5. **landings**: legge le landing (testo, h1, stack) e le collega alle ad.
6. **score**: punteggio delle ad.

## 3. Se l'utente ti dà altre pagine, landing o domini
Aggiungili al brand e rilancia il passo 2:
- **domini** → `brands.domains` (JSON). Es. morningvitality.com per Peak Health Research.
- **nomi pagina / prodotti** → `brands.keywords` (JSON), che diventano ricerche del discover.
- **page id** → `INSERT INTO pages(page_id, brand_id, role) VALUES(?, ?, 'alias')`.

Per andare veloce su un brand urgente, lancia `pull_pages(..., page_filter={id…})` in 3-4 processi paralleli, ciascuno su un gruppo di pagine, e fai girare thumbs, enrich e landings in parallelo. **Oltre 4-5 processi Meta risponde rate-limit**: non serve aggiungerne.

## 4. Regole di qualità (non negoziabili)
- **Nessuna ad di altri brand.** Un'ad entra nel brand solo se porta a un dominio del brand, o se il suo testo compare nell'archivio Meta del brand. I link social (facebook, instagram) non contano come dominio.
- **Pagine omonime.** "Margaret Davis" può essere di dieci inserzionisti diversi: decide il dominio, mai il nome.
- **Domini secondari dello stesso operatore** (es. ouravive.com che vende OsteoShield): si tengono nel brand solo dopo aver verificato sul sito che vende un prodotto del brand.
- **Un post = una riga di KPI.** I like di un post non si attaccano a una variante con reach diversa.
- **Formato** (`radar/formats.py`, `classify`):
  - un video è sempre `video`;
  - un'immagine con scritte disegnate o il marchio del brand (letto con OCR via tesseract) è `statica`, anche se il testo è lungo;
  - una foto pulita con testo di almeno 1000 caratteri, oppure testo di almeno 2000 caratteri in prima persona o da pagina "persona", è `native`.
- **Mercato.** La reach esiste solo per l'UE, quindi le ad USA e del resto del mondo non hanno reach. La bacheca ha il filtro "con reach / senza reach". Le ad senza reach si ordinano come le mostra l'Ad Library (`scripts/lib_rank.py <brand_id>`, colonna `lib_rank`).
- **Controllo finale** prima di dire "fatto":
  - numero di ad e di pagine;
  - quante ad sono senza anteprima e quante senza landing;
  - elenco dei domini, ciascuno verificato;
  - nessun dominio estraneo.

## 5. Cosa NON fare
- Non inserire mai credenziali e non fare mai login. Meta Ads è solo lettura.
- Mai `pkill` per nome: si ferma per PID.
- Non saturare il Mac. Massimo un brand pesante alla volta; il freno termico è `scripts/termico.sh`.
- Non salvare video o media pesanti sul Mac: solo database e anteprime piccole.
- AdSpy e Atria (tramite GinsBrowser) solo se l'utente li chiede. GinsBrowser lo usano anche altre chat.

## File chiave
`radar/brand.py` (discover/pull/enrich/landings/score) · `radar/meta_lib.py` (Ad Library) · `radar/formats.py` · `radar/thumbs.py` (anteprime + OCR) · `radar/server.py` + `public/index.html` (UI) · `scripts/completa_tutti.py` · `scripts/lib_rank.py` · `scripts/togli_brand.py` (rimuovere un brand ovunque).
