#!/bin/zsh
# Freno del radar. Due meccanismi:
#  1. Ciclo di lavoro fisso: 20s acceso, 20s fermo. Il radar non usa mai piu' di mezzo core.
#     Non e' una reazione al calore: e' una garanzia che il calore non arrivi.
#  2. Freno d'emergenza: se il carico esplode o la CPU viene limitata, resta fermo.
ALTO=${RADAR_LOAD_ALTO:-8.0}
BASSO=${RADAR_LOAD_BASSO:-6.0}
P="(radar/brand.py|radar/score.py|enrich_all.py|riclassifica.py|ocr_dedup.py|disco.py|daily.py|scripts/heusom_|ui_sweep.py|radar/complete.py|thumbs_tutte.py|reach_uk.py|thumbs_top.py|scandi.py|rejuva.py|ultra.py|nura.py|finisci_brand.py|atria_thumbs.py|mercati.py|adspy_dom.py|verifica_adspy.py|atria_dom.py)"
freno=0
while true; do
  pids=$(pgrep -f "$P" | tr "\n" " ")
  if [ -z "$pids" ]; then sleep 20; continue; fi
  l=$(sysctl -n vm.loadavg | awk '{print $2}')
  t=$(pmset -g therm 2>/dev/null | awk -F= '/CPU_Speed_Limit/{gsub(/ /,"",$2);print $2}'); [ -z "$t" ] && t=100
  if [ "$(echo "$l > $ALTO" | bc -l)" = "1" ] || [ "$t" -lt 100 ] 2>/dev/null; then
    [ $freno -eq 0 ] && { echo "$(date '+%F %T') FRENO load=$l cpu=$t%"; freno=1; }
    kill -STOP $pids 2>/dev/null; sleep 30; continue
  fi
  if [ $freno -eq 1 ] && [ "$(echo "$l < $BASSO" | bc -l)" = "1" ]; then
    echo "$(date '+%F %T') via libera load=$l"; freno=0
  fi
  [ $freno -eq 1 ] && { kill -STOP $pids 2>/dev/null; sleep 30; continue; }
  kill -CONT $pids 2>/dev/null; sleep 40     # lavora
  kill -STOP $pids 2>/dev/null; sleep 15     # respira
done
