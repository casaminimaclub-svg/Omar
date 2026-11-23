#!/bin/zsh
# Giro periodico (Chry 20 nov): ogni brand aggiornato con dati completi. Notte: attive + paesi + dettaglio attive.
# Domenica: anche archivio completo (attive+passate). Si mostrano solo le 20 per formato (vetrina), i dati restano tutti.
export PATH=/usr/sbin:/usr/bin:/bin:/opt/homebrew/bin
cd /root/ecom-radar
PY=/usr/bin/python3; L=data/giro.log
pgrep -f "ripristino2.sh|ripristino3.sh|ripristino4.sh|scripts/giro.sh .*running" >/dev/null && { echo "$(date '+%d %H:%M') ripristino in corso, salto" >> $L; exit 0; }
caffeinate -i -w $$ &
[ -f data/giro.pid ] && ps -p $(cat data/giro.pid) >/dev/null 2>&1 && exit 0
echo $$ > data/giro.pid
rete() { until curl -s -m 10 -o /dev/null https://www.facebook.com; do sleep 60; done; }
run() { rete; taskpolicy -c background nice -n 19 "$@" >> $L 2>&1; }
for b in $($PY -c "import sqlite3;c=sqlite3.connect('data/radar.db');print(' '.join(str(r[0]) for r in c.execute('select id from brands order by pinned desc, id')))"); do
  echo "$(date '+%d %H:%M') == brand $b" >> $L
  [ "$(date +%u)" = "7" ] && st=all || st=active
  run lockf -k data/meta.lck $PY -u scripts/pagine_browser.py $b $st
  run lockf -k data/meta.lck $PY -u scripts/top20.py $b
  run lockf -k data/meta.lck $PY -u scripts/paesi.py $b
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.enrich($b,limit=1000000,only_active=True,log=print)"
  run $PY -u scripts/thumbs_mancanti.py $b
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B,db as DB,lp as LP;B.landings($b,limit=100000,log=print);c=DB.conn();LP.link_ads_to_lps(c,$b);c.commit()"
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.score($b,log=print)"
done
rm -f data/giro.pid; echo "$(date '+%d %H:%M') GIRO FINITO" >> $L
