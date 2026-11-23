"""Completa i brand pronti: analisi creativa dove manca, punteggi, dossier. Solo Claude + DB (niente Meta)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB, brand as B, study

def log(m): print(m, flush=True)

c = DB.conn()
ids = [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='ready' ORDER BY id")]
for bid in ids:
    an, live, notes = c.execute("SELECT SUM(analyzed IS NOT NULL), SUM(is_active), (SELECT length(notes) FROM brands WHERE id=?) FROM ads WHERE brand_id=?", (bid, bid)).fetchone()
    try:
        if not an:
            B.creative(bid, limit=max(150, min(400, live or 0)), log=log); B.score(bid, log=log)
        if not notes:
            study.run(bid, log=log)
    except Exception as ex:
        log(f"finish {bid} errore {ex}")
c.close(); log("FINISH COMPLETATO")
