# Ecom Radar — istruzioni per Claude (ricostruzione da zero)

Ricevi un sistema già funzionante di competitor intelligence sulla Meta Ad Library. Il tuo compito è installarlo per il tuo utente con i SUOI brand.
Qui c'è il motore, non i dati: il database è vuoto e si crea da solo al primo avvio.

## Cosa contiene
- `codice/radar/`: il motore Python, scritto solo con la libreria standard più Playwright. Contiene:
  - discover delle pagine e lettura dell'archivio (`meta_lib.py`, `brand.py`);
  - trasparenza EU (`complete.py`, `market.py`), landing (`lp.py`), score (`score.py`);
  - analisi creativa e dossier con Claude CLI (`creative.py`, `study.py`, `llm.py`), transcript con whisper (`transcribe.py`);
  - il server dell'interfaccia (`server.py`, porta 8772).
- `codice/public/index.html`: l'interfaccia, un solo file.
- `codice/scripts/`: lo strato operativo. Contiene:
  - lettura dell'archivio via browser headless (`pagine_browser.py`) e ordine di Meta (`top20.py`);
  - lettura per paese (`paesi.py`), EU reach (`enrich_all.py`), anteprime (`thumbs_mancanti.py`);
  - la pipeline di un brand nuovo (`nuovo_brand.sh`) e il giro continuo (`giro.sh`);
  - il sorvegliante autonomo (`sorvegliante.py`).
- `PLAYBOOK.md`: come funziona ogni pezzo, con le lezioni tecniche: limiti di Meta, rate limit, trucchi di paginazione. **Leggilo per intero prima di toccare il codice.**
- `SISTEMA_BRAND.md`: la procedura per mappare un brand e le regole di qualità.
- `PRODUCT.md` / `DESIGN.md`: scopo del prodotto e sistema visivo della UI.

## Installazione (macOS)
1. Copia `codice/` in `~/ecom-radar`.
2. Sostituisci i segnaposto in tutti i file:
   - `__HOME__` diventa la home dell'utente;
   - `__MENTORI__` diventa la cartella delle note di riferimento dell'utente, oppure lascialo vuoto se non ne ha.
   ```bash
   grep -rl __HOME__ ~/ecom-radar | xargs sed -i '' "s#__HOME__#$HOME#g"
   ```
3. Installa le dipendenze:
   ```bash
   /usr/bin/python3 -m pip install --user playwright && /usr/bin/python3 -m playwright install chromium-headless-shell
   ```
   Facoltativi: `brew install tesseract` per l'OCR delle statiche e `whisper-cpp` per i transcript. Serve anche la Claude CLI per analisi creativa e dossier.
4. Server: `python3 ~/ecom-radar/radar/server.py`, poi apri http://localhost:8772. Per tenerlo sempre acceso adatta `esempio_server.plist` e mettilo in `~/Library/LaunchAgents`.
5. CLI: `radar_cli.sh` (comandi `add`, `refresh`, `study`, `creative`, `search`…). Mettila in `~/bin/radar`.
6. Il primo brand si aggiunge con `radar add https://dominio.com`. Per la lettura completa usa `scripts/nuovo_brand.sh <id>`.
7. Lavoro continuo:
   - adatta `esempio_sorvegliante.plist`, che lancia `sorvegliante.py` ogni 15 minuti;
   - aggiungi un cron notturno, `0 2 * * * /bin/zsh ~/ecom-radar/scripts/giro.sh`.
8. Fai uno smoke test: aggiungi 1 brand e verifica che ci siano ad, pagine, anteprime, reach EU, landing e score. Solo dopo aggiungi gli altri.

**Prima di tutto chiedi al tuo utente:** la lista dei suoi brand competitor (URL), i mercati che gli interessano e se ha la Claude CLI.

## Regole che abbiamo imparato a caro prezzo
- **Mai login e mai credenziali.** Si usa solo la Ad Library pubblica.
- **Un solo lettore Meta alla volta**, serializzato con `lockf data/meta.lck`. Se va oltre, Meta blocca l'IP per ore con un 403 anche dal browser normale. Il blocco va scritto in `data/meta_blocco` e la pipeline aspetta 3 ore, non salta.
- **Le ricerche per paese consumano molto.** Il giro completo dei 31 paesi va fatto solo la prima volta; dopo si cercano solo i paesi già visti, più US e GB.
- **Mai azzerare una classifica prima di aver letto quella nuova.** Se la rete cade, l'ordine resta com'era.
- **Ogni lettura ha un tetto di tempo** (20 minuti per fetta, 2 ore per processo). Il sorvegliante chiude i processi bloccati e rilancia la coda.
- **Prima di ogni cancellazione fai il backup di `data/radar.db`.**
- **Il sorvegliante deve anche** reinstallare Playwright se la cache viene svuotata, riavviare il server e aspettare la rete. Il lavoro riprende da solo quando il Mac si risveglia.
- **Media leggeri.** Si salvano solo miniature (≤640 px) e screenshot ridotti, mai video.
- **Il Mac deve restare acceso e sveglio:** usa `caffeinate -i -w $$` negli script lunghi. Tieni la CPU sotto i 70 °C, con `scripts/termico.sh`.
- **SQLite in WAL:** transazioni corte, mai una transazione aperta mentre si aspetta la rete o Claude.
- **Un'ad entra in un brand solo se porta a un suo dominio.** Le pagine omonime si distinguono col dominio, mai col nome.
- **Per risparmiare token:** gli agenti delegati usano un modello economico, i controlli si fanno con script e mai interrogando la chat a ripetizione.

## Cosa adattare
- `radar/llm.py`: il modello usato per l'analisi.
- `radar/market.py`: legge le note di riferimento dell'utente (`MENTORI`). È facoltativo.
- I nomi dei plist (`com.utente.*`) e la porta, se 8772 è occupata (`RADAR_PORT`).
- Gli script citano a volte gli id dei brand originali, per esempio "34": sono esempi da ignorare o generalizzare.
