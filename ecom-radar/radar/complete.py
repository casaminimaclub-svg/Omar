#!/usr/bin/env python3
"""Completamento dell'archivio: per ogni pagina confronta il totale dichiarato da Meta con le ad in
archivio e, se manca più del 5%, ripete la lettura "peel" con la lista delle ad già note (seen) e un
budget ampio: le richieste vanno solo dove ci sono ad nuove. Solo Meta + DB (niente Claude).
  python3 radar/complete.py [brand_id …]      (default: tutti i brand pronti, pagine con più buco prima)
"""
import fcntl, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB, meta_lib as M, brand as B

def log(m): print(time.strftime("%H:%M:%S"), m, flush=True)

def main():
    DB.init()
    lock = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".batch.lock"), "w")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: log("un altro batch/refresh è in corso: esco"); return
    c = DB.conn()
    try: c.execute("ALTER TABLE pages ADD COLUMN declared INTEGER")
    except Exception: pass
    c.commit()
    ids = [int(x) for x in sys.argv[1:] if x.isdigit()] or [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='ready' ORDER BY id")]
    if not ids: log("nessun brand pronto"); c.close(); return
    pages = [dict(r) for r in c.execute(f"SELECT p.*, b.id bid FROM pages p JOIN brands b ON b.id=p.brand_id WHERE b.id IN ({','.join('?'*len(ids))}) ORDER BY p.n_ads DESC", ids)]
    # 1) totale dichiarato (1 richiesta per pagina) → buco
    todo = []
    for p in pages:
        try: declared, _ = M.count(page_id=p["page_id"], country="ALL", active="all")
        except M.Blocked as ex: log(f"  conteggio {p['name']}: BLOCCO {ex}, pausa 60s"); time.sleep(60); continue
        have = c.execute("SELECT COUNT(*) FROM ads WHERE page_id=?", (p["page_id"],)).fetchone()[0]
        c.execute("UPDATE pages SET declared=? WHERE page_id=?", (declared, p["page_id"])); c.commit()
        gap = (declared or 0) - have
        if gap > max(10, have * 0.05): todo.append((gap, p, declared, have))
    todo.sort(key=lambda x: -x[0])
    log(f"COMPLETE: {len(todo)} pagine con buco su {len(pages)} · mancanti stimate {sum(t[0] for t in todo)}")
    # 2) rilettura mirata
    for gap, p, declared, have in todo:
        b = B._brand(c, p["bid"])
        seen = {r[0] for r in c.execute("SELECT ad_archive_id FROM ads WHERE page_id=?", (p["page_id"],))}
        st = {}; n = new = 0; t0 = time.time()
        budget = min(1600, 80 + gap // 3)   # ~1 richiesta ogni 3 ad mancanti: The Health Haven ha reso 1514 ad con 729 richieste
        log(f"  {b['name']} · {p['name']}: dichiarate {declared}, in archivio {have}, buco {gap} → budget {budget} richieste")
        try:
            for ad in M.search_sliced(page_id=p["page_id"], country="ALL", active="all", max_requests=budget, seen=seen, stats=st, gql_fallback=False, guard=False):
                n += 1
                mine = B._matches_brand(ad, b) or (not ad.get("domain") and p.get("role") == "main")
                if DB.upsert_ad(c, ad, p["bid"] if mine else None, source=f"page:{p['page_id']}") == "new": new += 1
                c.commit()
        except M.Blocked as ex:
            c.commit(); log(f"    BLOCCO {ex} dopo {n} ad → pausa 120s"); time.sleep(120); continue
        have2 = c.execute("SELECT COUNT(*) FROM ads WHERE page_id=?", (p["page_id"],)).fetchone()[0]
        c.execute("UPDATE pages SET n_ads=? WHERE page_id=?", (have2, p["page_id"])); c.commit()
        log(f"    +{new} nuove ({n} lette) → {have2}/{declared} · {time.time()-t0:.0f}s · richieste {st.get('requests')} · persi {st.get('lost')} · esaurito={st.get('exhausted')}")
    for bid in ids:
        try: B.score(bid, log=log)
        except Exception as ex: log(f"score {bid}: {ex}")
    c.close(); log("COMPLETE FINITO")

if __name__ == "__main__":
    main()
