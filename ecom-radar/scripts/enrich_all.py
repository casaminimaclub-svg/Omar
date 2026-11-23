#!/usr/bin/env python3
"""Chiude il buco della trasparenza UE: arricchisce OGNI ad idonea, brand per brand,
finche' non ne resta nessuna. Un brand alla volta, niente carico in parallelo."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "radar"))
import db as DB, brand as B

def log(m): print(time.strftime("%H:%M:%S"), m, flush=True)

def restano(c, bid):
    return c.execute("""SELECT COUNT(*) FROM ads WHERE brand_id=? AND is_aaa_eligible=1
                        AND details_checked IS NULL""", (bid,)).fetchone()[0]

def main():
    c = DB.conn()
    brands = c.execute("SELECT id,name FROM brands ORDER BY id").fetchall()
    tot0 = sum(restano(c, b["id"]) for b in brands)
    log(f"da arricchire in totale: {tot0}")
    for b in brands:
        n = restano(c, b["id"])
        if not n: continue
        log(f"=== {b['name']}: {n} da leggere")
        giri = 0
        while restano(c, b["id"]) and giri < 60:
            prima = restano(c, b["id"])
            B.enrich(b["id"], limit=400, log=log)
            dopo = restano(c, b["id"])
            giri += 1
            log(f"  {b['name']}: {prima} -> {dopo}")
            if dopo >= prima:
                log(f"  {b['name']}: nessun progresso, passo al prossimo"); break
        log(f"=== {b['name']} chiuso, restano {restano(c, b['id'])}")
    log(f"FINITO. residuo totale: {sum(restano(c, b['id']) for b in brands)}")
    c.close()

main()
