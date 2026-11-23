"""Traiettorie: non cosa esiste, ma cosa sta crescendo.

L'archivio dice quali ad ci sono. `ad_daily` dice come cambiano giorno per giorno: la reach
dichiarata da Meta e' cumulativa, quindi la differenza fra due letture e' reach NUOVA, cioe' soldi
messi in quell'ad in quei giorni. Da li' si legge chi sta scalando e chi sta morendo.

Onesto sui limiti:
  - la reach e' solo UE: le ad servite solo fuori UE non hanno traiettoria;
  - servono almeno due letture a giorni diversi, quindi le ad appena viste non ne hanno;
  - il ritmo e' reach nuova al giorno fra la prima e l'ultima lettura, non una curva.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

FINESTRA = 14          # giorni di storia considerati
MIN_LETTURE = 2


def calcola(c, log=print):
    """Riempie la tabella `traiettorie`: una riga per ad con almeno due letture di reach."""
    c.execute("""CREATE TABLE IF NOT EXISTS traiettorie(
        ad_archive_id TEXT PRIMARY KEY, brand_id INTEGER, d0 TEXT, d1 TEXT, giorni REAL,
        reach0 INTEGER, reach1 INTEGER, nuova INTEGER, al_giorno REAL, letture INTEGER,
        stato TEXT, calcolata TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tra_brand ON traiettorie(brand_id, al_giorno DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tra_giorno ON traiettorie(al_giorno DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ad_daily_reach ON ad_daily(ad_archive_id, d) WHERE eu_total_reach IS NOT NULL")
    c.commit()
    t = time.time()
    righe = c.execute(f"""
        SELECT dd.ad_archive_id aid, a.brand_id, a.is_active,
               MIN(dd.d) d0, MAX(dd.d) d1, COUNT(DISTINCT dd.d) letture,
               MIN(dd.eu_total_reach) r0, MAX(dd.eu_total_reach) r1
        FROM ad_daily dd JOIN ads a ON a.ad_archive_id = dd.ad_archive_id
        WHERE dd.eu_total_reach IS NOT NULL AND dd.d >= date('now','localtime','-{FINESTRA} day')
        GROUP BY dd.ad_archive_id HAVING letture >= {MIN_LETTURE}""").fetchall()
    log(f"traiettorie: {len(righe)} ad con storia ({time.time()-t:.1f}s)")
    oggi = DB.today(); n = 0
    c.execute("DELETE FROM traiettorie")
    for r in righe:
        giorni = max(0.5, (DB.gg(r["d1"]) - DB.gg(r["d0"])) if hasattr(DB, "gg") else _gg(r["d1"], r["d0"]))
        nuova = max(0, (r["r1"] or 0) - (r["r0"] or 0))
        al_giorno = nuova / giorni
        if not r["is_active"]:      stato = "spenta"
        elif al_giorno >= 2000:     stato = "scala"       # sta prendendo budget adesso
        elif al_giorno >= 300:      stato = "cresce"
        elif nuova > 0:             stato = "tiene"
        else:                       stato = "ferma"       # viva ma non consegna piu': budget tolto
        c.execute("""INSERT OR REPLACE INTO traiettorie
            (ad_archive_id,brand_id,d0,d1,giorni,reach0,reach1,nuova,al_giorno,letture,stato,calcolata)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["aid"], r["brand_id"], r["d0"], r["d1"], giorni, r["r0"], r["r1"], nuova,
             round(al_giorno, 1), r["letture"], stato, oggi))
        n += 1
        if n % 2000 == 0: c.commit(); time.sleep(0.15)
    c.commit()
    da = {s: k for s, k in c.execute("SELECT stato, COUNT(*) FROM traiettorie GROUP BY stato")}
    log(f"traiettorie: {n} scritte · {da}")
    return n


def _gg(d1, d0):
    from datetime import date
    try: return (date.fromisoformat(d1) - date.fromisoformat(d0)).days or 0.5
    except Exception: return 0.5


if __name__ == "__main__":
    c = DB.conn(); calcola(c); c.close()
