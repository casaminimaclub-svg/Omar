# Backup cloud del progetto Omar

Scopo: **non perdere niente** se il computer si rompe o si perde. Tutto quello che
oggi vive solo in locale (chat di Claude, analisi, store, file di lavoro) viene
copiato in questo repository GitHub privato. Da qualunque altro computer, o da
Claude Code sul web, basta aprire il repo e ritrovi tutto.

## Dove sono le chat di Claude sul tuo computer
Claude Code e l'app Claude Desktop salvano ogni conversazione in
`~/.claude/projects/<cartella-progetto>/<id-sessione>.jsonl`. Sono questi i file
che vanno salvati. Non vengono sincronizzati da Anthropic tra computer diversi.

## Primo avvio (una volta sola, sul tuo computer)
1. Apri il Terminale e scarica il repository (se non l'hai già):
   ```bash
   git clone https://github.com/casaminimaclub-svg/Omar.git ~/Omar
   cd ~/Omar
   ```
2. Apri `backup/cartelle.txt` e scrivi, una per riga, le cartelle di lavoro da
   salvare (Dropbox, Documenti, Desktop, ecc.).
3. Prova senza spingere nulla:
   ```bash
   DRY_RUN=1 bash backup/backup-locale.sh
   ```
4. Backup vero:
   ```bash
   bash backup/backup-locale.sh
   ```
Il primo push può essere lungo se le cartelle sono grandi. I successivi copiano
solo le differenze.

## Backup automatico ogni giorno (Mac)
```bash
crontab -e
```
e aggiungi questa riga (ogni giorno alle 20:00):
```
0 20 * * * /bin/bash "$HOME/Omar/backup/backup-locale.sh" >> "$HOME/Omar/backup/ultimo-backup.log" 2>&1
```
Su Windows: usa Git Bash per lanciare lo script, e l'Utilità di pianificazione
per programmarlo.

## Cosa viene salvato
| Cosa | Da dove | A dove nel repo |
|---|---|---|
| Chat (tutte le sessioni) | `~/.claude/projects` | `backup/claude/projects` |
| Skill, agenti, comandi, memoria, piani | `~/.claude/{skills,agents,commands,memory,plans,todos}` | `backup/claude/...` |
| Istruzioni globali e impostazioni | `~/.claude/CLAUDE.md`, `settings.json` | `backup/claude/` |
| Cartelle di lavoro | quelle in `backup/cartelle.txt` | `backup/cartelle/<nome>` |

Esclusi di proposito: file di credenziali (`~/.claude.json`, `.credentials.json`,
`.env`, chiavi), `node_modules`, cache, e file singoli oltre 95 MB (GitHub li rifiuta).

## Ripristino su un computer nuovo
```bash
git clone https://github.com/casaminimaclub-svg/Omar.git ~/Omar
cp -R ~/Omar/backup/claude/projects ~/.claude/projects
cp ~/Omar/backup/claude/CLAUDE.md ~/.claude/CLAUDE.md
```
Claude Code ritroverà tutte le chat con `claude --resume`.

## Attenzione
Le chat possono contenere dati sensibili (clienti, numeri, password scritte per
sbaglio). Tieni il repository **privato** e non condividerlo.
