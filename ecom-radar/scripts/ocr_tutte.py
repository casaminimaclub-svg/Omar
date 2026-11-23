#!/usr/bin/env python3
"""Legge (OCR locale, gratis) l'immagine di OGNI ad statica/native che non è mai stata letta, poi riclassifica.
Prima l'OCR si condivideva per phash, ma migliaia di immagini avevano phash vuoto (0000…): si passavano il testo
a vicenda. Ora si raggruppa per dHash calcolato sul file, e un hash nullo/vuoto non si condivide mai."""
import concurrent.futures, os, sys, time, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "radar"))
import db as DB, formats, paths as P
from thumbs import ocr, dhash
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
c = DB.conn()
# le letture "ereditate" da un phash vuoto non valgono: si rifanno
pass
ids = [r[0] for r in c.execute("SELECT ad_archive_id FROM ads WHERE brand_id IS NOT NULL AND (? = 0 OR brand_id = ?) AND fmt IN ('native','statica') AND ocr_done IS NULL", (int(sys.argv[1]) if len(sys.argv) > 1 else 0,)*2)]
ids = [a for a in ids if os.path.exists(os.path.join(P.THUMBS, f"{a}.jpg"))]
gruppi = collections.defaultdict(list)
for a in ids:
    h = dhash(os.path.join(P.THUMBS, f"{a}.jpg"))
    gruppi[h if h and h.strip("0") else "solo:" + a].append(a)
log(f"da leggere: {len(ids)} ad · {len(gruppi)} immagini distinte")
fatti = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get("RADAR_OCR_WORKERS", "3"))) as ex:
    for (h, membri), txt in zip(gruppi.items(), ex.map(lambda kv: ocr(os.path.join(P.THUMBS, f"{kv[1][0]}.jpg")), gruppi.items())):
        for _ in range(20):
            try:
                c.executemany("UPDATE ads SET ocr=?, ocr_done=1 WHERE ad_archive_id=?", [(txt or "", a) for a in membri]); break
            except Exception: time.sleep(5)
        fatti += 1
        if fatti % 20 == 0: c.commit()
        if fatti % 500 == 0: log(f"  {fatti}/{len(gruppi)}")
c.commit(); log("OCR finito, riclassifico"); formats.migrate(c, log=log); c.close(); log("FINITO")
