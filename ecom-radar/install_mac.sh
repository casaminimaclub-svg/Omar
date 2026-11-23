#!/bin/zsh
# Ecom Radar — installazione completa su macOS, passi 1-8 di LEGGIMI_PER_CLAUDE.md.
# Uso (Terminale, dalla cartella scaricata):   zsh install_mac.sh
# Rilanciarlo è sicuro: non tocca l'archivio esistente (ne fa solo un backup).
set -e
SRC=${0:A:h}; DEST=$HOME/ecom-radar; PY=/usr/bin/python3; UIDN=$(id -u)
say() { print -P "%F{cyan}▸%f $*"; }
[ "$(uname)" = Darwin ] || { echo "Questo script è per macOS."; exit 1; }

say "1. Copio il codice in $DEST"
mkdir -p $DEST/data
[ -f $DEST/data/radar.db ] && cp $DEST/data/radar.db $DEST/data/radar.db.bak-$(date +%Y%m%d%H%M) && say "   backup di radar.db fatto"
for x in radar public scripts tools radar_cli.sh esempio_server.plist esempio_sorvegliante.plist termico.plist brands.txt brand_iniziali.sh; do
  rm -rf $DEST/$x; cp -R $SRC/$x $DEST/
done
mkdir -p $DEST/kit-docs && cp $SRC/kit-docs/*.md $DEST/kit-docs/ 2>/dev/null || true

say "2. Sostituisco i segnaposto (__HOME__ → $HOME, __MENTORI__ → vuoto)"
grep -rl "__HOME__\|__MENTORI__" $DEST --exclude-dir=data --exclude-dir=kit-docs | while read f; do
  perl -pi -e "s#__HOME__#$HOME#g; s#__MENTORI__##g" "$f"; done
chmod +x $DEST/scripts/*.sh $DEST/brand_iniziali.sh $DEST/tools/* 2>/dev/null || true
xattr -dr com.apple.quarantine $DEST/tools 2>/dev/null || true

say "3. Dipendenze: Playwright + Chromium headless"
$PY -m pip install --user --upgrade pip >/dev/null 2>&1 || true
$PY -m pip install --user playwright
$PY -m playwright install chromium-headless-shell
if command -v brew >/dev/null; then
  say "   facoltativi: tesseract (OCR), ffmpeg + whisper-cpp (transcript)"
  brew install tesseract ffmpeg whisper-cpp || true
  if [ ! -f $HOME/ad-spy/models/ggml-small.bin ] && [ ! -f $HOME/ad-spy/models/ggml-large-v3-turbo.bin ]; then
    mkdir -p $HOME/ad-spy/models
    curl -L --fail -o $HOME/ad-spy/models/ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin || say "   modello whisper non scaricato (i transcript resteranno spenti)"
  fi
else
  say "   Homebrew non c'è: salto OCR e transcript (facoltativi). Per averli: https://brew.sh e rilancia."
fi
CL=$(command -v claude || true)
if [ -z "$CL" ]; then say "   ATTENZIONE: Claude CLI non trovata → analisi creativa e dossier spenti finché non la installi"
else for p in $HOME/.local/bin/claude /opt/homebrew/bin/claude /usr/local/bin/claude; do [ -e $p ] && break; done
     [ -e $p ] || { mkdir -p $HOME/.local/bin && ln -sf $CL $HOME/.local/bin/claude; }; say "   Claude CLI: $CL"; fi

say "4. Server sempre acceso (launchd, porta 8772)"
LA=$HOME/Library/LaunchAgents; mkdir -p $LA
cp $DEST/esempio_server.plist $LA/com.utente.ecom-radar.plist
cp $DEST/esempio_sorvegliante.plist $LA/com.utente.ecom-radar.sorvegliante.plist
cp $DEST/termico.plist $LA/com.utente.ecom-radar.termico.plist
for l in com.utente.ecom-radar com.utente.ecom-radar.termico; do
  launchctl bootout gui/$UIDN/$l 2>/dev/null || true; launchctl bootstrap gui/$UIDN $LA/$l.plist; done

say "5. CLI: ~/bin/radar"
mkdir -p $HOME/bin && cp $DEST/radar_cli.sh $HOME/bin/radar && chmod +x $HOME/bin/radar
grep -q 'HOME/bin' $HOME/.zshrc 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> $HOME/.zshrc

say "   aspetto il server…"
for i in {1..20}; do curl -s -m 3 localhost:8772/api/health >/dev/null && break; sleep 1; done
curl -s -m 3 localhost:8772/api/health >/dev/null && say "   server OK → http://localhost:8772" || { echo "Server non partito: vedi $DEST/data/server.log"; exit 1; }

say "7. Lavoro continuo: sorvegliante ogni 15 min + giro notturno alle 02:00"
launchctl bootout gui/$UIDN/com.utente.ecom-radar.sorvegliante 2>/dev/null || true
launchctl bootstrap gui/$UIDN $LA/com.utente.ecom-radar.sorvegliante.plist
( crontab -l 2>/dev/null | grep -v 'ecom-radar/scripts/giro.sh'; echo "0 2 * * * /bin/zsh $DEST/scripts/giro.sh" ) | crontab -

say "6+8. Brand: prima la prova (Heusom), poi tutti gli altri di brands.txt — in background"
if pgrep -f brand_iniziali.sh >/dev/null; then say "   già in corso"
elif [ -n "$(sqlite3 $DEST/data/radar.db 'select 1 from brands limit 1' 2>/dev/null)" ]; then say "   ci sono già brand nell'archivio: non rilancio (per rifarlo: zsh ~/ecom-radar/brand_iniziali.sh)"
else
  nohup /bin/zsh $DEST/brand_iniziali.sh >/dev/null 2>&1 < /dev/null &
  say "   avviato. Avanzamento: tail -f ~/ecom-radar/data/brand_iniziali.log"
fi

open http://localhost:8772 2>/dev/null || true
cat <<'FINE'

──────────────────────────────────────────────────────────────
 Ecom Radar installato.  Interfaccia: http://localhost:8772
 • Il Mac deve restare acceso, collegato alla corrente e sveglio
   (Impostazioni → Batteria/Alimentazione: impedisci lo stop automatico).
 • Avanzamento brand:   tail -f ~/ecom-radar/data/brand_iniziali.log
 • Esito della prova:   cat ~/ecom-radar/data/SMOKE.md
 • Stato del sistema:   cat ~/ecom-radar/data/STATO.md
──────────────────────────────────────────────────────────────
FINE
