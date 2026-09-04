#!/usr/bin/env bash
# =====================================================================
#  BACKUP LOCALE -> GITHUB (progetto "Omar")
#  Copia nel repository:
#    - le chat di Claude Code / Claude Desktop (~/.claude/projects)
#    - le impostazioni, skill, agenti e memoria di Claude (~/.claude/*)
#    - tutte le cartelle elencate in backup/cartelle.txt (analisi, store, ...)
#  poi fa commit + push. Da lanciare sul TUO computer (Mac/Linux).
#
#  Uso:   bash backup/backup-locale.sh
#  Prova senza push:   DRY_RUN=1 bash backup/backup-locale.sh
# =====================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_DIR/backup"
LISTA="$DEST/cartelle.txt"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
MAX_MB=95            # GitHub rifiuta file singoli > 100 MB
DRY_RUN="${DRY_RUN:-0}"

log() { printf '\033[1;34m[backup]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[errore]\033[0m %s\n' "$*" >&2; }

HAVE_RSYNC=1; command -v rsync >/dev/null || { HAVE_RSYNC=0; log "rsync non trovato: uso la copia semplice (più lenta ma funziona)"; }
command -v git   >/dev/null || { err "git non trovato"; exit 1; }

# Esclusioni comuni: roba pesante o rigenerabile, e file di credenziali.
EXCL=(
  --exclude '.git/' --exclude 'node_modules/' --exclude '.venv/' --exclude 'venv/'
  --exclude '__pycache__/' --exclude '.DS_Store' --exclude '*.log'
  --exclude '.env' --exclude '.env.*' --exclude '*.pem' --exclude '*.key'
  --exclude 'Thumbs.db' --exclude '.cache/' --exclude 'dist-cache/'
)

sync_dir() {  # sync_dir <sorgente> <destinazione>
  local src="$1" dst="$2"
  [ -e "$src" ] || { log "salto (non esiste): $src"; return 0; }
  mkdir -p "$dst"
  if [ "$HAVE_RSYNC" = 1 ]; then
    rsync -a --delete "${EXCL[@]}" --max-size="${MAX_MB}m" "$src/" "$dst/"
  else
    rm -rf "$dst"; mkdir -p "$dst"
    ( cd "$src" && find . -type f -size -"${MAX_MB}"M \
        ! -path '*/.git/*' ! -path '*/node_modules/*' ! -path '*/.venv/*' ! -path '*/venv/*' \
        ! -path '*/__pycache__/*' ! -path '*/.cache/*' ! -name '.DS_Store' ! -name '*.log' \
        ! -name '.env' ! -name '.env.*' ! -name '*.pem' ! -name '*.key' ! -name 'Thumbs.db' -print0 \
      | while IFS= read -r -d '' f; do mkdir -p "$dst/$(dirname "$f")"; cp -p "$f" "$dst/$f"; done )
  fi
  log "ok  $src  ->  ${dst#$REPO_DIR/}"
}

# ---------- 1. Chat e configurazione di Claude ----------
log "Claude home: $CLAUDE_HOME"
sync_dir "$CLAUDE_HOME/projects"  "$DEST/claude/projects"   # <-- QUI ci sono tutte le chat (file .jsonl)
for d in skills agents commands plans todos memory; do
  sync_dir "$CLAUDE_HOME/$d" "$DEST/claude/$d"
done
for f in CLAUDE.md settings.json keybindings.json; do
  if [ -f "$CLAUDE_HOME/$f" ]; then mkdir -p "$DEST/claude"; cp "$CLAUDE_HOME/$f" "$DEST/claude/$f"; log "ok  $CLAUDE_HOME/$f"; fi
done
# NB: ~/.claude.json e ~/.claude/.credentials.json NON vengono copiati: contengono token di accesso.

# Chat oltre il limite: salvate compresse (.jsonl.gz) in backup/claude/projects-grandi, nessuna perdita.
if [ -d "$CLAUDE_HOME/projects" ]; then
  find "$CLAUDE_HOME/projects" -type f -name '*.jsonl' -size +"${MAX_MB}"M -print0 2>/dev/null \
  | while IFS= read -r -d '' f; do
      rel="${f#$CLAUDE_HOME/projects/}"
      out="$DEST/claude/projects-grandi/$rel.gz"
      mkdir -p "$(dirname "$out")"
      gzip -c "$f" > "$out"
      log "ok  chat grande compressa: $rel ($(du -h "$out" | cut -f1))"
      if [ "$(du -m "$out" | cut -f1)" -ge "$MAX_MB" ]; then
        # Ancora troppo grande: spezzo in parti da 90 MB (ripristino: cat X.gz.part-* | gunzip > X)
        rm -f "$out".part-*
        split -b 90m -a 2 "$out" "$out.part-"
        rm -f "$out"
        log "    spezzata in $(ls "$out".part-* | wc -l | tr -d ' ') parti da 90 MB"
      fi
    done
fi

# ---------- 2. Cartelle di lavoro elencate in backup/cartelle.txt ----------
if [ -f "$LISTA" ]; then
  while IFS= read -r riga || [ -n "$riga" ]; do
    riga="${riga%%#*}"; riga="$(echo "$riga" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -z "$riga" ] && continue
    src="${riga/#\~/$HOME}"
    nome="$(basename "$src")"
    sync_dir "$src" "$DEST/cartelle/$nome"
  done < "$LISTA"
else
  log "nessun backup/cartelle.txt: salto le cartelle di lavoro"
fi

# ---------- 3. File troppo grandi (avviso) ----------
big=$(find "$DEST" -type f -size +"${MAX_MB}"M 2>/dev/null || true)
[ -n "$big" ] && { err "File > ${MAX_MB} MB esclusi dal push (GitHub li rifiuta):"; echo "$big"; }

# ---------- 4. Commit + push ----------
cd "$REPO_DIR"
git add -A backup
if git diff --cached --quiet; then log "nessuna modifica dall'ultimo backup"; exit 0; fi
n=$(git diff --cached --numstat | wc -l | tr -d ' ')
msg="Backup automatico $(date '+%Y-%m-%d %H:%M') ($n file)"
if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: avrei fatto commit \"$msg\" e push. Reset dello staging."
  git reset -q backup; exit 0
fi
git commit -q -m "$msg"
branch="$(git rev-parse --abbrev-ref HEAD)"
for tentativo in 1 2 3 4; do
  if git push -u origin "$branch"; then log "PUSH FATTO su origin/$branch: \"$msg\""; exit 0; fi
  err "push fallito (tentativo $tentativo), riprovo tra $((2**tentativo))s"; sleep $((2**tentativo))
done
err "push non riuscito: controlla la connessione, poi rilancia lo script"; exit 1
