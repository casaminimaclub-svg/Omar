"""Aggiornamento leggero di un brand (19 nov 2026, regola di Chry): di ogni brand si tengono solo
le prime 20 ad per formato (video · native · statica) nell'ordine «per impression» dell'Ad Library.
Pagine e landing si tengono tutte. Per ogni pagina: Ad Library ordinata per impression, video e
immagini a parte, si legge solo la testa. Poi si pota il brand a 20 per formato.
Ordine fra pagine diverse: posizione nella propria pagina, a parità la pagina più grande.
Uso: top20.py <brand_id>"""
import os, sys, json, time, sqlite3
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(R, "radar"))
import meta_lib as M, db as DB, brand as B
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.join(R, "scripts"))
from pagine_browser import bloccata, raffredda

TESTA = {"video": 25, "image": 50}   # 50 immagini per avere 20 native e 20 statiche
N = 20

def url_pagina(pid, media):
    u = M._url(page_id=pid, country="ALL", active="active", media=media)
    return u.replace("relevancy_monthly_grouped", "total_impressions")

def url(q, media, country="ALL"):
    # 19 nov sera (Chry): una sola ricerca per dominio del brand, solo attive, ordine impression = quello che vede lui in Ad Library
    u = M._url(query=q, country=country, active="active", media=media)
    return u.replace("relevancy_monthly_grouped", "total_impressions")

def ranghi(ads):
    """Posizione come la mostra Meta: le ad della stessa collation (\"N inserzioni con questa creatività\")
    sono UNA card. La prima del gruppo prende la posizione, le gemelle None."""
    visti, n = set(), 0
    for ad in ads:
        k = ad.get("collation_id") or ad["ad_archive_id"]
        if k in visti: yield None, ad; continue
        visti.add(k); n += 1; yield n, ad

def leggi(pg, pid, media, cap, country="ALL"):  # pid = keyword (dominio)
    seen = {}
    def grab(o):
        if isinstance(o, dict):
            src = o.get("search_results_connection")
            if src:
                for a in M._edges_to_ads(src.get("edges")): seen.setdefault(a["ad_archive_id"], a)
            for v in o.values(): grab(v)
        elif isinstance(o, list):
            for v in o: grab(v)
    def on_resp(r):
        if "graphql" in r.url:
            try:
                for line in r.text().splitlines():
                    try: grab(json.loads(line))
                    except Exception: pass
            except Exception: pass
    pg.on("response", on_resp)
    try:
        pg.goto(url_pagina(pid, media) if str(pid).isdigit() else url(pid, media, country), timeout=90000); pg.wait_for_timeout(4000)
        c = M._extract(pg.content()); declared = (c or {}).get("count")
        if c:
            for a in M._edges_to_ads(c.get("edges")): seen.setdefault(a["ad_archive_id"], a)
        last, still = 0, 0
        while len(seen) < cap and (declared is None or len(seen) < declared) and still < 5:
            # solo la rotella si bloccava a 200 ad (GB Nuracalm 200/913): fondo pagina + End + piccolo su-giù
            pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.keyboard.press("End")
            pg.mouse.wheel(0, -300); pg.mouse.wheel(0, 20000); pg.wait_for_timeout(2500)
            if len(seen) == last: still += 1
            else: still, last = 0, len(seen)
    finally:
        pg.remove_listener("response", on_resp)
    return declared, list(seen.values())[:cap]

def pota(c, bid):
    """Tiene le prime 20 per formato; le ad salvate nelle bacheche restano."""
    keep = {r[0] for r in c.execute("""SELECT ad_archive_id FROM (SELECT ad_archive_id, ROW_NUMBER() OVER (PARTITION BY fmt
              ORDER BY COALESCE(lib_rank,1e9), COALESCE(p.n_ads,0) DESC, COALESCE(eu_total_reach,0) DESC) rn
              FROM ads a LEFT JOIN pages p USING(page_id) WHERE a.brand_id=? AND fmt IN ('video','native','statica')
              AND (lib_rank IS NOT NULL OR NOT EXISTS (SELECT 1 FROM ads WHERE brand_id=? AND lib_rank IS NOT NULL))) WHERE rn<=?""", (bid, bid, N))}
    keep |= {r[0] for r in c.execute("""SELECT ad_archive_id FROM (SELECT ad_archive_id, ROW_NUMBER() OVER (PARTITION BY page_id, fmt
              ORDER BY page_rank) rn FROM ads WHERE brand_id=? AND page_rank IS NOT NULL) WHERE rn<=?""", (bid, N))}
    keep |= {r[0] for r in c.execute("SELECT bi.ad_archive_id FROM board_items bi JOIN ads a USING(ad_archive_id) WHERE a.brand_id=?", (bid,))}
    via = [r[0] for r in c.execute("SELECT ad_archive_id FROM ads WHERE brand_id=? OR (brand_id IS NULL AND page_id IN (SELECT page_id FROM pages WHERE brand_id=?))", (bid, bid)) if r[0] not in keep]
    for aid in via:
        for t in ("ads", "ad_daily", "ad_reach_cc", "traiettorie", "search_hits"):
            c.execute(f"DELETE FROM {t} WHERE ad_archive_id=?", (aid,))
        try: c.execute("DELETE FROM ads_fts WHERE rowid=?", (DB.fts_rowid(aid),))
        except Exception: pass
        f = os.path.join(R, "data", "thumbs", f"{aid}.jpg")
        if os.path.exists(f): os.remove(f)
    c.commit()
    return len(keep), len(via)

def vetrina(c, bid):
    """Cosa si MOSTRA (Chry 20 nov): prime 20 per formato del brand (lib_rank, Home) + prime 20 per formato
    di ogni pagina (page_rank, sezione Brand) + salvate. I dati restano tutti: vetrina=0 = solo nei numeri."""
    c.execute("UPDATE ads SET vetrina=0 WHERE brand_id=?", (bid,))
    # 20 nov (Chry): MASSIMO 20 per formato per brand in tutto (20 video, 20 statiche, 20 native), ordine impression
    c.execute("""UPDATE ads SET vetrina=1 WHERE ad_archive_id IN (SELECT ad_archive_id FROM (SELECT ad_archive_id,
        ROW_NUMBER() OVER (PARTITION BY fmt ORDER BY lib_rank IS NULL, lib_rank, page_rank IS NULL, page_rank, is_active DESC, COALESCE(eu_total_reach,0) DESC) rn
        FROM ads WHERE brand_id=? AND fmt IN ('video','statica','native')) WHERE rn<=?)""", (bid, N))
    c.commit()

def main():
    if sys.argv[1] == "--vetrina":
        c = DB.conn()
        for (b,) in c.execute("SELECT id FROM brands").fetchall(): vetrina(c, b)
        print("vetrina:", c.execute("SELECT SUM(vetrina), COUNT(*) FROM ads").fetchone()); return
    bid = int(sys.argv[1])
    c = DB.conn(); b = B._brand(c, bid)
    testi = {B._norm_txt(r[0]) for r in c.execute("SELECT body FROM ads WHERE brand_id=? AND domain IS NOT NULL AND body IS NOT NULL", (bid,))} - {""}
    pagine = c.execute("SELECT page_id, name FROM pages WHERE brand_id=? ORDER BY n_active DESC, n_ads DESC", (bid,)).fetchall()
    print(f"{b['name']}: {len(pagine)} pagine", flush=True)
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--disable-gpu", "--mute-audio", "--autoplay-policy=user-gesture-required"])
        pg = br.new_page(locale="en-US", viewport={"width": 800, "height": 600})
        pg.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image", "media", "font", "stylesheet") else r.continue_())
        dom = (b.get("domain") or b["domains_l"][0])
        declared, ads = leggi(pg, dom, "all", 160)
        if not ads: print("  nessuna ad letta (rete/Meta): classifica lasciata com'era", flush=True); br.close(); return
        c.execute("UPDATE ads SET lib_rank=NULL, page_rank=NULL WHERE brand_id=?", (bid,)); c.commit()
        mine_n = 0
        for i, ad in ranghi(ads):
            mine = B._matches_brand(ad, b) or (not ad.get("domain") and B._norm_txt(ad.get("body")) in testi)
            if not mine: continue
            mine_n += 1
            for tent in range(20):
                try:
                    DB.upsert_ad(c, ad, bid, source=f"top20:{dom}")
                    c.execute("UPDATE ads SET lib_rank=? WHERE ad_archive_id=?", (i, ad["ad_archive_id"])); break
                except sqlite3.OperationalError as ex:
                    if "locked" not in str(ex) or tent == 19: raise
                    time.sleep(3)
        c.commit()
        print(f"  {dom}: Meta {declared} · lette {len(ads)} · del brand {mine_n}", flush=True)
        for pid, name in pagine:   # sezione Brand: top 20 per formato di ogni pagina, ordine impression
            if bloccata(): print("  Meta in pausa per blocco: mi fermo", flush=True); break
            raffredda()
            for media, cap in (("all", 100),):   # una sola lista = un solo ordine, niente pareggi video/immagini
                try: declared, ads = leggi(pg, pid, media, cap)
                except Exception as e: print(f"  {name}/{media}: ERRORE {str(e)[:80]}", flush=True); continue
                n = 0
                for i, ad in ranghi(ads):
                    if not (B._matches_brand(ad, b) or (not ad.get("domain") and B._norm_txt(ad.get("body")) in testi)): continue
                    n += 1
                    for tent in range(20):
                        try:
                            DB.upsert_ad(c, ad, bid, source=f"top20:{pid}")
                            c.execute("UPDATE ads SET page_rank=? WHERE ad_archive_id=?", (i, ad["ad_archive_id"])); break
                        except sqlite3.OperationalError as ex:
                            if "locked" not in str(ex) or tent == 19: raise
                            time.sleep(3)
                c.execute("UPDATE pages SET declared=COALESCE(?,declared), last_full_pull=? WHERE page_id=?", (declared, DB.today(), pid)); c.commit()
                print(f"  {name}/{media}: Meta {declared} · lette {len(ads)} · del brand {n}", flush=True)
        br.close()
    vetrina(c, bid); tenute, tolte = 0, 0   # 19 nov 21:55 (Chry): NON si cancella più niente, le 20 sono solo cosa si mostra
    DB.recount_pages(c, bid); c.execute("UPDATE brands SET last_scan=? WHERE id=?", (DB.today(), bid)); c.commit(); c.close()
    print(f"FINE {b['name']}: tenute {tenute} · tolte {tolte}", flush=True)

if __name__ == "__main__":
    main()
