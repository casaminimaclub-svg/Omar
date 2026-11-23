#!/bin/bash
# Installa Ecom Radar in un container Linux (sessione cloud Claude Code) dalla copia nella repo.
# Uso: bash ecom-radar/setup_linux.sh   (dalla radice della repo)
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
rm -rf ~/ecom-radar && mkdir -p ~/ecom-radar && cp -R "$SRC"/. ~/ecom-radar/ && rm -rf ~/ecom-radar/kit-docs ~/ecom-radar/setup_linux.sh
mkdir -p ~/ecom-radar/data ~/bin /opt/homebrew/bin
# i segnaposto sono già sostituiti con /root: se la home è diversa li riallinea
if [ "$HOME" != "/root" ]; then grep -rl "/root/ecom-radar" ~/ecom-radar | xargs sed -i "s#/root/ecom-radar#$HOME/ecom-radar#g"; fi
ln -sf ~/ecom-radar/linux-shims/* /opt/homebrew/bin/          # caffeinate / taskpolicy / lockf per gli script macOS
cp ~/ecom-radar/radar_cli.sh ~/bin/radar && chmod +x ~/bin/radar ~/ecom-radar/scripts/*.sh
python3 -m pip install -q "playwright==1.63.0"                 # stessa versione del Chromium preinstallato in /opt/pw-browsers
command -v tesseract >/dev/null || apt-get install -y -q tesseract-ocr tesseract-ocr-eng
command -v zsh >/dev/null && command -v sqlite3 >/dev/null || apt-get install -y -q zsh sqlite3
cd ~/ecom-radar && (nohup python3 radar/server.py > data/server.log 2>&1 &)
sleep 3; curl -s localhost:8772/api/health && echo && echo "Ecom Radar pronto su http://localhost:8772"
