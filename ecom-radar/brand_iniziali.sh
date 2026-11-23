#!/bin/zsh
# Passi 6 e 8 del kit: PRIMA un brand di prova con la lettura completa e il controllo
# (ad, pagine, anteprime, reach EU, landing, score); SOLO se passa, gli altri uno alla volta.
# Un solo lettore Meta alla volta (lockf data/meta.lck). Log: data/brand_iniziali.log, esito prova: data/SMOKE.md
export PATH=/usr/sbin:/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin
R=$HOME/ecom-radar; cd $R; PY=/usr/bin/python3; L=data/brand_iniziali.log
caffeinate -i -w $$ &
log() { echo "$(date '+%d %H:%M') $*" >> $L; }
# SISTEMA_BRAND §1 (un 403 anti-bot vale come "risponde", conta solo che il sito esista): se il dominio non risponde prova le varianti (.co, www., try…)
risolvi() {
  local u=$1 d=${1#https://}; d=${d#http://}; d=${d#www.}; d=${d%%/*}; local n=${d%%.*}
  for c in "$d" "www.$d" "try$n.com" "$n.co" "get$n.com" "$n.us"; do
    curl -s -m 15 -L -o /dev/null -w '%{http_code}' "https://$c" | grep -vq '^000$' && { echo "https://$c"; return 0; }
  done; return 1
}
aggiungi() {   # $1 url  $2 nome  -> stampa l'id del brand
  local u; u=$(risolvi $1) || { log "SALTATO $2: nessun dominio risponde ($1)"; return 1; }
  [ "$u" != "$1" ] && log "$2: $1 non risponde, uso $u"
  local id; id=$($PY -c "import sys;sys.path.insert(0,'radar');import brand as B;print(B.add_brand('$u','$2',log=lambda *a:None))")
  log "BRAND #$id $2 ($u): radar add"
  lockf -k data/meta.lck $PY -u radar/brand.py add "$u" >> data/nuovo_$id.log 2>&1
  log "BRAND #$id $2: lettura completa (nuovo_brand.sh)"
  /bin/zsh scripts/nuovo_brand.sh $id
  echo $id
}
q() { sqlite3 data/radar.db "$1"; }
smoke() {   # passo 8: ci sono ad, pagine, anteprime, reach EU, landing e score?
  local b=$1 ok=1
  local ad=$(q "select count(*) from ads where brand_id=$b") pg=$(q "select count(*) from pages where brand_id=$b")
  local th=$(ls data/thumbs 2>/dev/null | wc -l | tr -d ' ') eu=$(q "select count(*) from ads where brand_id=$b and eu_total_reach>0")
  local lp=$(q "select count(*) from ads where brand_id=$b and lp_id is not null") sc=$(q "select count(*) from ads where brand_id=$b and score is not null")
  {
    echo "# Prova del primo brand (#$b) — $(date '+%d/%m %H:%M')"; echo
    for x in "ad:$ad" "pagine:$pg" "anteprime:$th" "ad con reach EU:$eu" "ad con landing:$lp" "ad con score:$sc"; do
      k=${x%%:*}; v=${x##*:}; [ "$v" -gt 0 ] && echo "- OK   $k: $v" || { echo "- MANCA $k: $v"; ok=0; }
    done
    echo; $PY scripts/verifica.py 2>&1 | head -40
  } > data/SMOKE.md
  return $((1-ok))
}
log "== inizio"
grep -v '^#' brands.txt | grep . > data/.coda_brand
primo=$(head -1 data/.coda_brand)
id=$(aggiungi ${=primo}) || { log "brand di prova non aggiunto: mi fermo"; exit 1; }
q "UPDATE brands SET pinned=1 WHERE id=$id"
if smoke $id; then log "PROVA SUPERATA (data/SMOKE.md): aggiungo gli altri"
else log "PROVA NON SUPERATA: vedi data/SMOKE.md. Gli altri brand NON vengono aggiunti."; exit 1; fi
tail -n +2 data/.coda_brand | while read u nome; do aggiungi $u "$nome" > /dev/null; done
log "== TUTTI I BRAND AGGIUNTI"
