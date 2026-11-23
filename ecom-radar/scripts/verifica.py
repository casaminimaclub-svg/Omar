#!/usr/bin/env python3
"""Controllo di completezza: cosa manca, brand per brand. Solo letture, zero costo."""
import os, sys, re, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "radar"))
import db as DB

c = DB.conn()
q1 = lambda s, a=(): c.execute(s, a).fetchone()[0]
print("=" * 72)
print("BRAND — copertura")
print("=" * 72)
righe = []
for b in c.execute("SELECT id,name,domain,niche,status FROM brands ORDER BY id"):
    bid = b["id"]
    n   = q1("SELECT COUNT(*) FROM ads WHERE brand_id=?", (bid,))
    pg  = q1("SELECT COUNT(*) FROM pages WHERE brand_id=?", (bid,))
    lp  = q1("SELECT COUNT(*) FROM landing_pages WHERE brand_id=?", (bid,))
    eu  = q1("SELECT COUNT(*) FROM ads WHERE brand_id=? AND is_aaa_eligible=1 AND details_checked IS NULL", (bid,))
    nt  = q1("SELECT COUNT(*) FROM ads WHERE brand_id=? AND fmt!='video' AND thumb IS NULL", (bid,))
    guai = []
    if not n: guai.append("NESSUNA AD")
    if not pg: guai.append("nessuna pagina")
    if not lp: guai.append("nessuna landing")
    if not b["niche"]: guai.append("senza nicchia")
    if eu: guai.append(f"{eu} ad UE da leggere")
    if nt: guai.append(f"{nt} senza miniatura")
    if b["status"] not in ("ready", "pronto"): guai.append(f"stato={b['status']}")
    righe.append((bid, b["name"], n, pg, lp, "; ".join(guai) or "ok"))
w = max(len(r[1]) for r in righe)
for bid, nm, n, pg, lp, g in righe:
    print(f"{bid:>3} {nm:<{w}}  {n:>6} ad {pg:>4} pag {lp:>3} lp   {g}")

print()
print("=" * 72)
print("ARCHIVIO — buchi trasversali")
print("=" * 72)
print(f"  ad senza brand:            {q1('SELECT COUNT(*) FROM ads WHERE brand_id IS NULL')}")
print(f"  ad senza pagina:           {q1('SELECT COUNT(*) FROM ads WHERE page_id IS NULL')}")
print(f"  pagine senza brand:        {q1('SELECT COUNT(*) FROM pages WHERE brand_id IS NULL')}")
print(f"  pagine senza nessuna ad:   {q1('SELECT COUNT(*) FROM pages p WHERE NOT EXISTS(SELECT 1 FROM ads a WHERE a.page_id=p.page_id)')}")
print(f"  ad UE dichiarate, mai lette: {q1('SELECT COUNT(*) FROM ads WHERE is_aaa_eligible=1 AND details_checked IS NULL')}")
_nc = q1("SELECT COUNT(*) FROM ads WHERE (body IS NULL OR body='') AND fmt!='video'")
print(f"  ad senza copy:             {_nc}")
print(f"  ad senza formato:          {q1('SELECT COUNT(*) FROM ads WHERE fmt IS NULL')}")
print(f"  landing senza screenshot:  {q1('SELECT COUNT(*) FROM landing_pages WHERE screenshot IS NULL')}")
for r in c.execute("SELECT fmt, COUNT(*) n FROM ads GROUP BY fmt ORDER BY n DESC"):
    print(f"    fmt {r['fmt']}: {r['n']}")

print()
print("=" * 72)
print("PULL — ad viste ma scartate (dai log di add)")
print("=" * 72)
for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "data", "add_*.log"))):
    txt = open(f, errors="ignore").read()
    sc = re.findall(r"(\d+)\s+(?:scartate|verso altri domini|fuori dominio)", txt)
    if sc: print(f"  {os.path.basename(f)}: {', '.join(sc)}")
c.close()
