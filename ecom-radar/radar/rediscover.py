#!/usr/bin/env python3
"""Seconda scoperta delle pagine: oltre a nome e dominio, cerca con i nomi dei prodotti (dai titoli
delle landing) e con budget doppio. Le pagine nuove entrano nel pull del prossimo giro."""
import fcntl, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB, brand as B, meta_lib as M

def log(m): print(time.strftime("%H:%M:%S"), m, flush=True)

STOP = {"the","and","for","with","your","you","our","of","to","a","in","on","by","at","from","is","are","official","store","shop","buy","get","now","free","best","new","home","page","quiz","offer","order","sale"}

def product_terms(c, bid, domain):
    terms = {}
    for r in c.execute("SELECT title, h1, n_ads FROM landing_pages WHERE brand_id=? ORDER BY n_ads DESC LIMIT 40", (bid,)):
        for t in (r["title"] or "", r["h1"] or ""):
            t = re.split(r"[|–—:•·]", t)[0]
            words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9®™'-]{2,}", t) if w.lower() not in STOP]
            if 2 <= len(words) <= 3:
                k = " ".join(words).lower().replace("®", "").replace("™", "")
                terms[k] = terms.get(k, 0) + (r["n_ads"] or 1)
    root = domain.split(".")[0]
    return [k for k, _ in sorted(terms.items(), key=lambda x: -x[1]) if k != root][:6]

def main():
    DB.init()
    lock = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".batch.lock"), "w")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: log("un altro batch è in corso: esco"); return
    c = DB.conn()
    ids = [int(x) for x in sys.argv[1:]] or [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='ready' ORDER BY id")]
    for bid in ids:
        b = B._brand(c, bid)
        extra = product_terms(c, bid, b["domain"])
        before = c.execute("SELECT COUNT(*) FROM pages WHERE brand_id=?", (bid,)).fetchone()[0]
        kws = list(dict.fromkeys(b["keywords_l"] + extra))
        log(f"REDISCOVER {b['name']}: keyword {kws}")
        try: B.discover(bid, max_requests=80, log=log, extra_queries=extra)
        except Exception as ex: log(f"  errore {ex}")
        after = c.execute("SELECT COUNT(*) FROM pages WHERE brand_id=?", (bid,)).fetchone()[0]
        log(f"  pagine {before} → {after}")
    c.close(); log("REDISCOVER FINITO")

if __name__ == "__main__":
    main()
