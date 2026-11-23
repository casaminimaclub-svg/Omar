#!/usr/bin/env python3
"""Ecom Radar — miniature permanenti + impronta visiva.

Gli URL fbcdn scadono in pochi giorni: se non salviamo la miniatura ORA, l'ad spenta
perde l'immagine per sempre. Qui si scaricano le miniature di tutte le ad di un brand
(cache data/thumbs/<id>.jpg) e si calcola un dHash 64 bit: creatività identiche caricate
su pagine diverse (alias) hanno lo stesso hash → "questa creatività gira su N pagine",
il segnale di iterazione/scala che le sole collation di Meta (per pagina) non danno.
"""
import concurrent.futures, json, os, re, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

import paths as P
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THUMBS = P.THUMBS


def dhash(path):
    try:
        from PIL import Image
        im = Image.open(path).convert("L").resize((9, 8), Image.LANCZOS)
        px = list(im.getdata())
        bits = 0
        for r in range(8):
            for c in range(8):
                bits = (bits << 1) | (1 if px[r * 9 + c] > px[r * 9 + c + 1] else 0)
        return f"{bits:016x}"
    except Exception:
        return None


def fetch(aid, urls):
    path = os.path.join(THUMBS, f"{aid}.jpg")
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return aid, path, "cached"
    for u in urls:
        if not u: continue
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.facebook.com/"})
            data = urllib.request.urlopen(req, timeout=25).read()
            if len(data) > 200:
                tmp = path + ".tmp"; open(tmp, "wb").write(data)
                if not P.shrink(tmp, path):
                    try: os.remove(tmp)
                    except Exception: pass
                    continue   # mai salvare l'originale a piena risoluzione: intasa il disco
                else:
                    try: os.remove(tmp)
                    except Exception: pass
                return aid, path, "ok"
        except Exception:
            continue
    return aid, None, "fail"


_DIZ = None
def _dizionario():
    global _DIZ
    if _DIZ is None:
        try: _DIZ = {w.strip().lower() for w in open("/usr/share/dict/words") if len(w.strip()) >= 4}
        except Exception: _DIZ = set()
    return _DIZ

def ocr(path):
    """Testo dentro l'immagine. Le anteprime sono piccole (360px): si ingrandiscono a 1080 e si leggono due
    volte (testo sparso + blocco), così le scritte di un pack-shot si vedono davvero. Vuoto se è solo una foto."""
    import subprocess, tempfile
    try:
        from PIL import Image
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        im = Image.open(path).convert("L"); k = 1080 / max(im.size)
        if k > 1: im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        im.save(tmp)
        parti = []
        for psm in ("11", "6"):
            p = subprocess.run(["tesseract", tmp, "stdout", "-l", "eng", "--psm", psm], capture_output=True, text=True, timeout=40)
            parti.append(p.stdout or "")
        os.remove(tmp)
        parole = []
        for t in parti:
            for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’]{3,}", t):
                if sum(ch.isalpha() for ch in w) >= 4 and not re.search(r"(.)\1\1", w.lower()) and w.lower() not in [x.lower() for x in parole]:
                    parole.append(w)
        # il rumore di una foto produce "parole" inventate: contano solo quelle del dizionario
        # si salvano tutte le parole lette; quanto "conta" lo decide formats.disegnata (dizionario + marchio)
        return " ".join(parole)[:1500] if parole else None
    except Exception:
        return None

def run(bid=None, limit=12000, workers=6, log=print, do_ocr=True, ocr_limit=1200):
    os.makedirs(THUMBS, exist_ok=True)
    P.migrate_legacy(log)
    c = DB.conn()
    try: c.execute("ALTER TABLE ads ADD COLUMN phash TEXT")
    except Exception: pass
    c.commit()
    w = "WHERE image_url IS NOT NULL" + (" AND brand_id=?" if bid else "")
    rows = c.execute(f"SELECT ad_archive_id, image_url, media, phash FROM ads {w} ORDER BY is_active DESC, start_date DESC LIMIT ?", ((bid, limit) if bid else (limit,))).fetchall()
    jobs = []
    for r in rows:
        path = os.path.join(THUMBS, f"{r['ad_archive_id']}.jpg")
        if r["phash"] and os.path.exists(path): continue
        urls = [r["image_url"]] + [m.get("thumb") or m.get("url") for m in json.loads(r["media"] or "[]")]
        jobs.append((r["ad_archive_id"], urls))
    ok = fail = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for aid, path, st in ex.map(lambda j: fetch(*j), jobs):
            if path:
                h = dhash(path); c.execute("UPDATE ads SET phash=? WHERE ad_archive_id=?", (h, aid)); ok += 1
            else:
                fail += 1
            c.commit()
    c.commit()
    # creatività condivise fra pagine: quante pagine distinte usano lo stesso hash
    try: c.execute("ALTER TABLE ads ADD COLUMN n_pages_same INTEGER")
    except Exception: pass
    c.commit()
    # aggregato una volta sola (la subquery correlata su migliaia di ad teneva il lock di scrittura per minuti)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ads_brand_phash ON ads(brand_id, phash)")
    c.execute("CREATE TEMP TABLE IF NOT EXISTS _nps(brand_id INTEGER, phash TEXT, n INTEGER, PRIMARY KEY(brand_id, phash))")
    c.execute("DELETE FROM _nps")
    c.execute("INSERT INTO _nps SELECT brand_id, phash, COUNT(DISTINCT page_id) FROM ads WHERE phash IS NOT NULL" + (" AND brand_id=?" if bid else "") + " GROUP BY brand_id, phash", (bid,) if bid else ())
    c.commit()
    # solo le righe che cambiano davvero, a lotti brevi: un UPDATE di massa riscrive righe da decine di KB
    # e tiene il lock di scrittura per minuti (era la causa dei "database is locked")
    todo_nps = c.execute("""SELECT a.ad_archive_id, x.n FROM ads a JOIN _nps x ON x.brand_id=a.brand_id AND x.phash=a.phash
                            WHERE a.phash IS NOT NULL AND COALESCE(a.n_pages_same,-1) != x.n""" + (" AND a.brand_id=?" if bid else ""), (bid,) if bid else ()).fetchall()
    for i, r in enumerate(todo_nps, 1):
        c.execute("UPDATE ads SET n_pages_same=? WHERE ad_archive_id=?", (r["n"], r["ad_archive_id"]))
        if i % 100 == 0: c.commit()
    c.commit()
    # OCR: solo statiche/caroselli (nei video la miniatura è un frame qualsiasi), una volta sola
    n_ocr = 0
    if do_ocr:
        try: c.execute("ALTER TABLE ads ADD COLUMN ocr_done INTEGER")
        except Exception: pass
        c.commit()
        todo = c.execute(f"""SELECT ad_archive_id FROM ads WHERE format IN ('image','carousel') AND ocr_done IS NULL {'AND brand_id=?' if bid else ''}
                             ORDER BY is_active DESC, score DESC LIMIT ?""", ((bid, ocr_limit) if bid else (ocr_limit,))).fetchall()
        paths = [(r["ad_archive_id"], os.path.join(THUMBS, f"{r['ad_archive_id']}.jpg")) for r in todo]
        paths = [(a, pth) for a, pth in paths if os.path.exists(pth)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            for aid, txt in ex.map(lambda j: (j[0], ocr(j[1])), paths):
                c.execute("UPDATE ads SET ocr=?, ocr_done=1 WHERE ad_archive_id=?", (txt, aid)); DB.refresh_fts(c, aid); n_ocr += 1
                c.commit()
        c.commit()
    c.close()
    log(f"THUMBS: {ok} salvate, {fail} non scaricabili (URL scaduti), {len(rows)-len(jobs)} già in cache · OCR {n_ocr} statiche")
    return ok


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
