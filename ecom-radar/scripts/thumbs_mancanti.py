"""Anteprime mancanti: ad della Home (lib_rank) di ogni brand + tutte le ad di Nuracalm."""
import os, sys, json, sqlite3, concurrent.futures
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar import paths as P, thumbs as T
have = set()
for b in (P.MEDIA, P.LEGACY):
    d = os.path.join(b, "thumbs")
    if os.path.isdir(d): have |= {f[:-4] for f in os.listdir(d)}
# brand fissati (📌) e brand passato da riga di comando: tutte le ad, non solo le top 100
BRAND = int(next((a for a in sys.argv[1:] if a.isdigit()), 0))
c = sqlite3.connect(os.path.join(P.LEGACY, "radar.db"), timeout=60)
jobs = []
# solo le top 100 di ogni brand, nello stesso ordine della bacheca (reach, poi punteggio)
# 19 nov (Chry): anteprime solo per le ad della Home (classifica impression, lib_rank) + Nuracalm (34) tutte
for aid, iu, m in c.execute("""SELECT ad_archive_id, image_url, media FROM ads WHERE brand_id IS NOT NULL
        AND (vetrina=1 OR brand_id=34) AND (?=0 OR brand_id=?)""", (BRAND, BRAND)):
    if aid in have: continue
    urls = [iu] + [x.get("thumb") or x.get("url") for x in json.loads(m or "[]")]
    urls = [u for u in urls if u][:3]
    if urls: jobs.append((aid, urls))
print("da scaricare", len(jobs), flush=True)
ok = ko = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for i, (aid, path, st) in enumerate(ex.map(lambda j: T.fetch(*j), jobs), 1):
        if path: ok += 1
        else: ko += 1
        if i % 2000 == 0: print(i, "ok", ok, "scaduti", ko, flush=True)
print("FINE ok", ok, "scaduti", ko, flush=True)
