#!/bin/zsh
# Ecom Radar CLI
#   radar add <url>            mappa un brand fino al midollo (pagine, archivio ad, EU, landing, score)
#   radar refresh <id|all>     giro di aggiornamento
#   radar study <id>           dossier di intelligence scritto da Claude
#   radar transcribe <id> [n]  transcript whisper dei top n video
#   radar dossier <id>         riepilogo testuale
#   radar search "<q>"         scansione live della Ad Library (archiviata)
#   radar serve                server UI su http://localhost:8772
#   radar creative <id> [n]    analisi creativa (hook/angolo/persona) delle top n ad
#   radar digest [giorni]      digest dei movimenti
#   radar batch <file.txt>     coda di brand (una URL per riga)
R=/root/ecom-radar/radar
case "$1" in
  add) shift; python3 -u $R/brand.py add "$@";;
  refresh)
    if [ "$2" = "all" ]; then RADAR_GAP=${RADAR_GAP:-3} python3 -u $R/batch.py --refresh
    else python3 -u $R/brand.py refresh "$2"; fi;;
  digest) python3 $R/digest.py "${2:-1}";;
  creative) python3 -u $R/creative.py "$2" "${3:-120}";;
  batch) shift; RADAR_GAP=${RADAR_GAP:-2} python3 -u $R/batch.py "$@";;
  study) python3 -u $R/study.py "$2";;
  dossier) python3 $R/brand.py dossier "$2";;
  search) python3 $R/live.py "$2";;
  transcribe) python3 $R/transcribe.py "brand:$2" "${3:-25}";;
  serve) python3 $R/server.py;;
  *) sed -n 2,13p "$0";;
esac
