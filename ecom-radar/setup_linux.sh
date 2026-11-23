#!/bin/bash
# Installa Ecom Radar in un container Linux (sessione cloud Claude Code) dalla copia nella repo.
# Il kit è pensato per macOS (vedi install_mac.sh): qui servono gli shim di caffeinate/taskpolicy/lockf.
# Uso: bash ecom-radar/setup_linux.sh   (dalla radice della repo)
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"; DEST=$HOME/ecom-radar
mkdir -p $DEST/data ~/bin /opt/homebrew/bin
for x in radar public scripts tools linux-shims radar_cli.sh brands.txt brand_iniziali.sh; do rm -rf $DEST/$x; cp -R "$SRC/$x" $DEST/; done
grep -rl "__HOME__\|__MENTORI__" $DEST --exclude-dir=data | while read f; do perl -pi -e "s#__HOME__#$HOME#g; s#__MENTORI__##g" "$f"; done
ln -sf $DEST/linux-shims/* /opt/homebrew/bin/                 # caffeinate / taskpolicy / lockf
command -v claude >/dev/null && [ ! -e /usr/local/bin/claude ] && ln -sf "$(command -v claude)" /usr/local/bin/claude || true
cp $DEST/radar_cli.sh ~/bin/radar && chmod +x ~/bin/radar $DEST/scripts/*.sh $DEST/brand_iniziali.sh
python3 -m pip install -q "playwright==1.63.0"                 # stessa versione del Chromium preinstallato in /opt/pw-browsers
command -v tesseract >/dev/null || apt-get install -y -q tesseract-ocr tesseract-ocr-eng
{ command -v zsh && command -v sqlite3; } >/dev/null || apt-get install -y -q zsh sqlite3
curl -s -m 3 localhost:8772/api/health >/dev/null || (cd $DEST; nohup python3 radar/server.py > data/server.log 2>&1 < /dev/null &)
sleep 3; curl -s localhost:8772/api/health && echo && echo "Ecom Radar pronto su http://localhost:8772"
