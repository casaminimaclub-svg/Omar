#!/usr/bin/env python3
"""Scarica le miniature mancanti di TUTTE le ad, non una per brand.

Perche' serve: in piattaforma 103.359 ad su 140.747 non mostravano l'anteprima. Gli URL
fbcdn scadono: quelli delle ad ancora attive rispondono, quelli delle spente danno 403 e
si recuperano solo rileggendo la pagina dall'archivio (passo notturno separato).

Disco: le miniature vecchie pesavano 34 KB l'una perche' salvate prima della riduzione.
Qui si scrive a 360 px q55 (~10 KB) e si ricomprimono anche quelle gia' presenti: il
risultato e' copertura piena occupando MENO spazio di adesso.
"""
import concurrent.futures, json, os, sys, time, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "radar"))
import db as DB, paths as P

LARGH = 360
QUAL = 55


def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


def scarica(aid, urls):
    path = os.path.join(P.THUMBS, f"{aid}.jpg")
    for u in urls:
        if not u: continue
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.facebook.com/"})
            data = urllib.request.urlopen(req, timeout=15).read()
            if len(data) < 200: continue
            tmp = path + ".tmp"
            open(tmp, "wb").write(data)
            ok = P.shrink(tmp, path, max_w=LARGH, quality=QUAL)
            try: os.remove(tmp)
            except Exception: pass
            if ok: return aid, path
        except Exception:
            continue
    return aid, None


def comprimi(path):
    """Ricomprime sul posto una miniatura gia' scaricata. Ritorna i byte risparmiati."""
    try:
        prima = os.path.getsize(path)
        if prima < 18000: return 0
        tmp = path + ".rc"
        if not P.shrink(path, tmp, max_w=LARGH, quality=QUAL):
            try: os.remove(tmp)
            except Exception: pass
            return 0
        dopo = os.path.getsize(tmp)
        if dopo >= prima:
            os.remove(tmp); return 0
        os.replace(tmp, path)
        return prima - dopo
    except Exception:
        return 0


def main():
    solo_attive = "--tutte" not in sys.argv
    workers = int(os.environ.get("RADAR_THUMB_WORKERS", "6"))
    have = set(f[:-4] for f in os.listdir(P.THUMBS) if f.endswith(".jpg"))

    # 1) ricompressione di quelle esistenti: libera disco prima di scaricarne altre
    risparmio = n = 0
    for f in list(have):
        g = comprimi(os.path.join(P.THUMBS, f + ".jpg"))
        if g: risparmio += g; n += 1
        if n and n % 2000 == 0: log(f"  ricompresse {n} · {risparmio/1e6:.0f} MB liberati")
    log(f"ricompressione: {n} file, {risparmio/1e6:.0f} MB liberati")

    # 2) scarico delle mancanti
    c = DB.conn()
    q = "SELECT ad_archive_id, image_url, media, is_active FROM ads WHERE brand_id IS NOT NULL AND image_url IS NOT NULL"
    if solo_attive: q += " AND is_active=1"
    jobs = []
    # ordine per last_seen: l'URL fbcdn vale pochi giorni, quindi si parte dalle ad rilette
    # di recente. Quelle non toccate da un pezzo hanno l'URL gia' morto: inutile provarle,
    # le riprende il passo notturno subito dopo la rilettura dall'archivio.
    for r in c.execute(q + " ORDER BY last_seen DESC, is_active DESC"):
        aid = r["ad_archive_id"]
        if aid in have: continue
        urls = [r["image_url"]] + [m.get("thumb") or m.get("url") for m in json.loads(r["media"] or "[]")]
        jobs.append((aid, urls))
    log(f"da scaricare: {len(jobs)}")

    ok = fail = 0
    import thumbs as T
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (aid, path) in enumerate(ex.map(lambda j: scarica(*j), jobs), 1):
            if path:
                ok += 1
                c.execute("UPDATE ads SET phash=? WHERE ad_archive_id=?", (T.dhash(path), aid))
            else:
                fail += 1
            if i % 250 == 0:
                c.commit(); log(f"  {i}/{len(jobs)} · ok {ok} · scadute {fail}")
                time.sleep(1)   # respiro breve: il lavoro e' quasi tutto attesa di rete, non calcolo
    c.commit(); c.close()
    log(f"FINE: {ok} miniature nuove, {fail} URL scaduti")


if __name__ == "__main__":
    main()
