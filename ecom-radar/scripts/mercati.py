#!/usr/bin/env python3
"""Mercato di ogni ad (colonna ads.mercato): US, AU, CA, UK, BR, EU separati da virgola,
oppure EXTRA = Meta non mostra reach in UE/UK/BR, quindi gira fuori (USA/AU/CA…) senza sapere dove.
Fonti: paesi AdSpy, location_audience e reach_by_country della trasparenza Meta."""
import json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMI = {"united states": "US", "usa": "US", "us": "US", "australia": "AU", "au": "AU", "canada": "CA", "ca": "CA",
        "united kingdom": "UK", "uk": "UK", "gb": "UK", "brazil": "BR", "br": "BR", "new zealand": "NZ", "nz": "NZ"}
UE = {"austria","belgium","bulgaria","croatia","cyprus","czech republic","czechia","denmark","estonia","finland","france","germany","greece","hungary","ireland","italy","latvia","lithuania","luxembourg","malta","netherlands","poland","portugal","romania","slovakia","slovenia","spain","sweden"}
ORD = ["US", "AU", "CA", "NZ", "UK", "EU", "BR", "ALTRI"]
def cod(x, ue=False):
    x = x.strip().lower()
    if not x or x.isdigit(): return None
    return NOMI.get(x, ("EU" if ue or x in UE else "ALTRI") if len(x) > 1 else None)

c = sqlite3.connect(os.path.join(ROOT, "data", "radar.db"), timeout=600)
try: c.execute("ALTER TABLE ads ADD COLUMN mercato TEXT")
except sqlite3.OperationalError: pass
spy = {}
for aid, ps in c.execute("SELECT ad_archive_id, countries FROM adspy_ads WHERE ad_archive_id IS NOT NULL AND countries!=''"):
    spy.setdefault(aid, set()).update(filter(None, (cod(p) for p in ps.split(","))))
agg, n = [], 0
for aid, paesi, loc, rbc, chk, reach in c.execute(
        "SELECT ad_archive_id, countries, location_audience, reach_by_country, details_checked, eu_total_reach FROM ads"):
    s = set(spy.get(aid, ()))
    if paesi:
        try: v = json.loads(paesi) if paesi.startswith("[") else paesi.split(",")
        except Exception: v = []
        s.update(filter(None, (cod(p) for p in v if isinstance(p, str) and "paesi" not in p and "-" not in p)))
    for blob, key in ((loc, "name"), (rbc, None)):
        if not blob: continue
        try: d = json.loads(blob)
        except Exception: continue
        for x in (d if key is None else [i.get(key, "") for i in d if not i.get("excluded")]):
            if isinstance(x, str) and cod(x, True): s.add(cod(x, True))
    m = ",".join(k for k in ORD if k in s) or ("EXTRA" if chk and not reach else None)
    agg.append((m, aid))
c.executemany("UPDATE ads SET mercato=? WHERE ad_archive_id=?", agg); c.commit()
c.execute("CREATE INDEX IF NOT EXISTS idx_ads_mercato ON ads(mercato)"); c.commit()
for r in c.execute("SELECT mercato, COUNT(*) FROM ads GROUP BY 1 ORDER BY 2 DESC LIMIT 15"): print(*r)
