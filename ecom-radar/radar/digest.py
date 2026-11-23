#!/usr/bin/env python3
"""Ecom Radar — digest delle ultime 24 ore (dopo il refresh notturno): per ogni brand
cosa ha lanciato, cosa ha spento, quali landing/pagine nuove, quali angoli crescono.
Scrive data/DIGEST.md e lo espone alla UI (/api/digest). Nessun modello: solo dati.
"""
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "DIGEST.md")


def build(days=1):
    c = DB.conn()
    since = (date.today() - timedelta(days=days)).isoformat()
    L = [f"# Ecom Radar · digest {DB.today()} (ultimi {days} g)\n"]
    tot_new = tot_stop = 0
    for b in c.execute("SELECT * FROM brands ORDER BY name"):
        bid = b["id"]
        new = c.execute("SELECT * FROM ads WHERE brand_id=? AND start_date>=? ORDER BY score DESC", (bid, since)).fetchall()
        stopped = c.execute("SELECT COUNT(*) FROM events WHERE brand_id=? AND kind='ad_stopped' AND substr(ts,1,10)>=?", (bid, since)).fetchone()[0]
        new_lps = c.execute("SELECT detail FROM events WHERE brand_id=? AND kind='new_lp' AND substr(ts,1,10)>=?", (bid, since)).fetchall()
        new_pages = c.execute("SELECT detail FROM events WHERE brand_id=? AND kind='new_page' AND substr(ts,1,10)>=?", (bid, since)).fetchall()
        live = c.execute("SELECT COUNT(*) FROM ads WHERE brand_id=? AND is_active=1", (bid,)).fetchone()[0]
        tot_new += len(new); tot_stop += stopped
        if not new and not stopped and not new_lps and not new_pages:
            L.append(f"## {b['name']} — nessun movimento · {live} live\n"); continue
        L.append(f"## {b['name']} — +{len(new)} nuove · {stopped} spente · {live} live")
        if new:
            vid = sum(1 for a in new if a["format"] == "video")
            L.append(f"- Nuove: {len(new)} ({vid} video, {len(new)-vid} statiche/caroselli) su {len({a['page_id'] for a in new})} pagine")
            angles = {}
            for a in new:
                if a["angle"]: angles[a["angle"]] = angles.get(a["angle"], 0) + 1
            if angles:
                L.append("- Angoli delle nuove: " + ", ".join(f"{k} ({v})" for k, v in sorted(angles.items(), key=lambda x: -x[1])[:6]))
            for a in new[:5]:
                L.append(f"  - [{a['format']}] «{(a['title'] or a['hook'] or (a['body'] or '')[:80]).strip()}» · {a['page_name']} · x{a['collation_count']} · id {a['ad_archive_id']}")
        for e in new_lps: L.append(f"- Landing nuova: {e['detail']}")
        for e in new_pages: L.append(f"- Pagina nuova: {e['detail']}")
        L.append("")
    L.insert(1, f"**Totale: {tot_new} ad nuove, {tot_stop} spente.**\n")
    c.close()
    md = "\n".join(L)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(md)
    c = DB.conn(); DB.log_event(c, "digest", None, None, f"{tot_new} nuove · {tot_stop} spente"); c.commit(); c.close()
    return md


if __name__ == "__main__":
    print(build(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
