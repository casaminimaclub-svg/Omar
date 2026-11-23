#!/bin/zsh
# Brand nuovo da cima a fondo (20 nov): pagine, attive+archivio, ordine Meta, paesi, reach, vetrina, landing, punteggi.
B=$1; cd /root/ecom-radar; export PATH=/usr/sbin:/usr/bin:/bin:/opt/homebrew/bin
caffeinate -i -w $$ &
PY=/usr/bin/python3; L=data/nuovo_$B.log
rete() { until curl -s -m 10 -o /dev/null https://www.facebook.com; do sleep 60; done; }
run() { rete; echo "$(date '+%H:%M') > $*" | cut -c1-120 >> $L; taskpolicy -c background nice -n 19 "$@" >> $L 2>&1; }
run lockf -k data/meta.lck $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.discover($B,max_requests=60,log=print)"
run lockf -k data/meta.lck $PY -u scripts/pagine_browser.py $B active   # archivio lo fa ripristino4 (fase ARCHIVIO)
run lockf -k data/meta.lck $PY -u scripts/top20.py $B
run lockf -k data/meta.lck $PY -u scripts/paesi.py $B
run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.enrich($B,limit=1000000,log=print)"
run $PY -u scripts/thumbs_mancanti.py $B
run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B,db as DB,lp as LP;B.landings($B,limit=100000,log=print);c=DB.conn();LP.link_ads_to_lps(c,$B);c.commit()"
run $PY -c "import sys;sys.path.insert(0,'radar');import brand as B;B.score($B,log=print)"
sqlite3 data/radar.db "UPDATE brands SET status='ready' WHERE id=$B"
echo "$(date '+%H:%M') FINITO: $(sqlite3 data/radar.db "select count(*)||' ad, '||sum(is_active)||' attive, rank '||sum(lib_rank is not null)||', pagine '||(select count(*) from pages where brand_id=$B) from ads where brand_id=$B")" >> $L
