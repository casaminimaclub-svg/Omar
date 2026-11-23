#!/usr/bin/env python3
"""Completezza vera di ogni brand: ricerca profonda nella Ad Library (nome + domini, 200 richieste),
poi archivio intero di ogni pagina, anteprime, reach, landing, punteggi. Un brand alla volta,
il più grande scarto prima. Riprendibile: data/completa_fatti.json. Uso: completa_tutti.py [brand_id...]"""
import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "radar"))
import brand as B, db as DB
F = os.path.join(ROOT, "data", "completa_fatti.json")
fatti = set(json.load(open(F))) if os.path.exists(F) else set()
c = DB.conn(); ids = [int(a) for a in sys.argv[1:]] or [r[0] for r in c.execute("SELECT id FROM brands ORDER BY id")]; c.close()
for bid in ids:
    if bid in fatti and not os.environ.get("RADAR_FORZA"): continue
    t = time.time(); print(time.strftime("%H:%M"), "brand", bid, flush=True)
    for passo in (lambda: B.discover(bid, max_requests=200), lambda: B.pull_pages(bid, full=True), lambda: B.thumbs(bid),
                  lambda: B.enrich(bid, limit=100000), lambda: B.landings(bid, limit=500), lambda: B.score(bid)):
        try: passo()
        except Exception as e: print("  errore", e, flush=True)
    fatti.add(bid); json.dump(sorted(fatti), open(F, "w"))
    print(time.strftime("%H:%M"), "brand", bid, "FATTO in", int(time.time() - t), "s", flush=True)
print("TUTTI FATTI", flush=True)
