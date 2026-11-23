#!/bin/zsh
# 20 nov 14:35: prima le ATTIVE di tutti i brand (numeri live + ordine Meta + paesi, veloce), poi l'ARCHIVIO completo.
# Se manca la rete aspetta. Il Mac resta sveglio finché gira.
export PATH=/usr/sbin:/usr/bin:/bin:/opt/homebrew/bin
cd /root/ecom-radar
caffeinate -i -w $$ &
PY=/usr/bin/python3; L=data/ripristino3.log
rete() { until curl -s -m 10 -o /dev/null https://www.facebook.com; do echo "$(date '+%H:%M') rete assente, aspetto" >> $L; sleep 60; done; }
blocco() { while [ -f data/meta_blocco ] && [ $(( $(date +%s) - $(cut -d. -f1 data/meta_blocco) )) -lt 10800 ]; do sleep 300; done; }
run() { rete; blocco; taskpolicy -c background nice -n 19 "$@" >> $L 2>&1; }
stato() { echo "$(date '+%d %H:%M') $1 brand $2: $(sqlite3 data/radar.db "select count(*)||' ad, '||sum(is_active)||' attive, rank '||sum(lib_rank is not null) from ads where brand_id=$2")" >> $L; }
dopo() {
  run lockf -k data/meta.lck $PY -u scripts/top20.py $1
  run lockf -k data/meta.lck $PY -u scripts/paesi.py $1
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.enrich($1,limit=1000000,log=print)"
  run $PY -u scripts/thumbs_mancanti.py $1
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B,db as DB,lp as LP;B.landings($1,limit=100000,log=print);c=DB.conn();LP.link_ads_to_lps(c,$1);c.commit()"
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.score($1,log=print)"
}
ALTRI=$($PY -c "import sqlite3;c=sqlite3.connect('data/radar.db');print(' '.join(str(r[0]) for r in c.execute('select id from brands where id!=34 order by pinned desc, id')))")
for b in $=ALTRI; do echo "$(date '+%d %H:%M') == ATTIVE brand $b" >> $L
  run lockf -k data/meta.lck $PY -u scripts/pagine_browser.py $b active; dopo $b; stato ATTIVE $b; done
for b in $=ALTRI; do echo "$(date '+%d %H:%M') == ARCHIVIO brand $b" >> $L
  run lockf -k data/meta.lck $PY -u scripts/pagine_browser.py $b all
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.enrich($b,limit=1000000,log=print)"
  run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B,db as DB,lp as LP;B.landings($b,limit=100000,log=print);c=DB.conn();LP.link_ads_to_lps(c,$b);c.commit()"
  stato ARCHIVIO $b; done
echo "$(date '+%d %H:%M') TUTTO FINITO" >> $L
