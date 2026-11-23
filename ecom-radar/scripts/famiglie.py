#!/usr/bin/env python3
"""Lega l'ad vista su AdSpy (post con like/commenti, spesso mercato USA) alle stesse creatività in Meta
Ad Library (reach UE/UK/BR). Stessa creatività = stessa copy (primi 100 caratteri) E stessa immagine
(dHash a distanza <= 10). Scrive ads.gemelle sulla riga AdSpy (id delle ad Meta) e ads.famiglia sulle
ad Meta (id della riga AdSpy). Uso: famiglie.py [brand_id] [--prova]"""
import json, os, re, sqlite3, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "radar")); import thumbs as T
c = sqlite3.connect(os.path.join(ROOT, "data", "radar.db"), timeout=600)
for col in ("gemelle", "famiglia"):
    try: c.execute(f"ALTER TABLE ads ADD COLUMN {col} TEXT")
    except sqlite3.OperationalError: pass
prova = "--prova" in sys.argv; args = [a for a in sys.argv[1:] if not a.startswith("--")]
w = f" AND brand_id={int(args[0])}" if args else ""
chiave = lambda b: re.sub(r"\W+", " ", (b or "").lower()).strip()[:100]
H = {}
def h(aid):
    if aid not in H:
        p = os.path.join(T.THUMBS, f"{aid}.jpg"); H[aid] = int(T.dhash(p), 16) if os.path.exists(p) and T.dhash(p) else None
    return H[aid]
spy = c.execute(f"SELECT ad_archive_id, brand_id, body FROM ads WHERE source='adspy' AND body IS NOT NULL AND gemelle IS NULL{w}").fetchall()   # solo le nuove: le altre sono già legate
per_brand = collections.defaultdict(lambda: collections.defaultdict(list))
for bid in {b for _, b, _ in spy}:
    for aid, body in c.execute("SELECT ad_archive_id, body FROM ads WHERE brand_id=? AND COALESCE(source,'')<>'adspy' AND body IS NOT NULL", (bid,)):
        if aid.isdigit(): per_brand[bid][chiave(body)].append(aid)
legate = coppie = 0; esempi = []
for aid, bid, body in spy:
    k = chiave(body)
    if len(k) < 40: continue
    cand = per_brand[bid].get(k, [])
    hs = h(aid)
    if hs is None or not cand: continue
    gem = [x for x in cand if h(x) is not None and bin(hs ^ h(x)).count("1") <= 10]
    if not gem: continue
    legate += 1; coppie += len(gem)
    if len(esempi) < 5: esempi.append((aid, gem[:3]))
    if not prova:
        c.execute("UPDATE ads SET gemelle=? WHERE ad_archive_id=?", (json.dumps(gem), aid))
        c.executemany("UPDATE ads SET famiglia=? WHERE ad_archive_id=?", [(aid, x) for x in gem])
        if legate % 50 == 0: c.commit()   # lotti brevi: una transazione lunga bloccava tutti gli altri lavori
if not prova: c.commit()
print(f"ad AdSpy {len(spy)} · legate a Meta {legate} · ad Meta collegate {coppie}", esempi)
