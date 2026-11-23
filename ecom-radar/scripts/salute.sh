#!/bin/zsh
# Stato del Mac in una riga: carico, memoria, swap, disco, limite CPU termico, piano Claude.
l=$(sysctl -n vm.loadavg | awk '{print $2}')
mp=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{print $2}')
sw=$(sysctl -n vm.swapusage | awk '{print $6}')
df=$(df -h / | awk 'NR==2{print $4}')
th=$(pmset -g therm 2>/dev/null | awk -F= '/CPU_Speed_Limit/{gsub(/ /,"",$2);print $2}'); th=${th:-100}
pl=$(~/bin/plan-usage 2>/dev/null | awk '/7 giorni/{print $3}')
echo "$(date '+%H:%M') load=$l memlibera=$mp swap=$sw disco=$df cpu_limit=${th}% piano7g=$pl"
