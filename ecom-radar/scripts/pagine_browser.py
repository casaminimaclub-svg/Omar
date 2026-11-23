"""Lettura COMPLETA delle pagine di un brand come un browser vero: apre la pagina nell'Ad Library
e scorre fino in fondo, raccogliendo ogni ad dalle risposte GraphQL.
Perché: il filtro data di Meta seleziona le ad IN ONDA nel periodo, non quelle lanciate, e un giorno
solo (min=max) viene ignorato. Le fette per data si sovrappongono e sulle pagine grandi si perdevano
fino al 40% delle ad (Everyday Women's Health: 265 lette su 444). Scorrendo: 444 su 444.
Uso: pagine_browser.py <brand_id> [active|all]"""
import os, sys, json, time, sqlite3
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(R, "radar"))
import meta_lib as M, db as DB, brand as B
from playwright.sync_api import sync_playwright
import time
def bloccata():
    """Pausa condivisa da tutti i lettori: dopo un blocco nessuno interroga Meta per 3 ore."""
    f = os.path.join(R, "data", "meta_blocco")
    try: return time.time() - float(open(f).read() or 0) < 3 * 3600
    except Exception: return False

# soglia 50 sul sensore tools/temp ≈ 70°C su Stats (il primo legge ~20°C in meno, 15 nov)
def raffredda(soglia=3.0):
    """Mai scaldare il Mac (4 nov: 90°C con due browser headless insieme): si aspetta che il carico scenda."""
    # temperatura vera della CPU (tools/temp, sensori HID); tetto 68°C per stare sotto i 70 nei picchi
    import subprocess
    while True:
        try: t = float(subprocess.run([os.path.join(R, "tools", "temp")], capture_output=True, text=True, timeout=5).stdout or 0)
        except Exception: t = 0
        if (t and t < 50) or (not t and os.getloadavg()[0] <= soglia): return
        time.sleep(15)


def leggi(pg, pid, active, media="all", platforms=None):
    seen = {}
    def grab(o):
        if isinstance(o, dict):
            src = o.get("search_results_connection")
            if src:
                for a in M._edges_to_ads(src.get("edges")): seen[a["ad_archive_id"]] = a
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
        pg.goto(M._url(page_id=pid, country="ALL", active=active, media=media, platforms=platforms), timeout=90000); pg.wait_for_timeout(5000)
        c = M._extract(pg.content()); declared = (c or {}).get("count")
        if c:
            for a in M._edges_to_ads(c.get("edges")): seen[a["ad_archive_id"]] = a
        last, still = 0, 0
        t_in = time.time()
        for k in range(3000):
            # 20 nov: mai più di 20 minuti su una fetta (Koriderm: 3 ore ferma su una pagina, tutto il resto in coda)
            if time.time() - t_in > 1200: print(f"    fetta interrotta dopo 20 min: lette {len(seen)}", flush=True); break
            if k % 40 == 39: raffredda()   # anche dentro le pagine lunghe (3.670 ad = ~120 scorrimenti)
            if declared is not None and len(seen) >= declared: break
            pg.mouse.wheel(0, 20000); pg.wait_for_timeout(2500)
            if len(seen) == last: still += 1
            else: still, last = 0, len(seen)
            if still >= 8: break
    finally:
        pg.remove_listener("response", on_resp)
    return declared, list(seen.values())

def main():
    bid = int(sys.argv[1]); active = sys.argv[2] if len(sys.argv) > 2 else "active"
    c = DB.conn(); b = B._brand(c, bid)
    testi = {B._norm_txt(r[0]) for r in c.execute("SELECT body FROM ads WHERE brand_id=? AND domain IS NOT NULL AND body IS NOT NULL", (bid,))} - {""}
    pagine = c.execute("SELECT page_id, name FROM pages WHERE brand_id=? ORDER BY n_active DESC", (bid,)).fetchall()
    pulite = set()
    for pid, _ in pagine:
        if not c.execute("""SELECT COUNT(*) FROM ads WHERE page_id=? AND domain IS NOT NULL AND domain NOT IN ('facebook.com','instagram.com','fb.com','m.me','wa.me','messenger.com')
                            AND (brand_id IS NULL OR brand_id!=?)""", (pid, bid)).fetchone()[0]: pulite.add(pid)
    t = DB.today()
    with sync_playwright() as p:
        # niente immagini, video, font né GPU: servono solo i dati GraphQL. Il rendering dei video
        # del feed era ciò che scaldava il Mac (95°C il 4 nov).
        br = p.chromium.launch(args=["--disable-gpu", "--mute-audio", "--autoplay-policy=user-gesture-required"])
        pg = br.new_page(locale="en-US", viewport={"width": 800, "height": 600})
        pg.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image", "media", "font", "stylesheet") else r.continue_())
        zeri = 0
        for pid, name in pagine:
            if bloccata(): print("  Meta in pausa per blocco recente: mi fermo", flush=True); break
            raffredda()
            t0 = time.time()
            try:
                declared, ads = leggi(pg, pid, active)
                # oltre ~1.400 ad Meta smette di caricare scorrendo: si divide per stato e per tipo di media
                if declared and len(ads) < declared:
                    tutte = {a["ad_archive_id"]: a for a in ads}
                    for st_ in (("active", "inactive") if active == "all" else (active,)):
                        for med in ("video", "image", "meme", "none"):
                            d2, a2 = leggi(pg, pid, st_, med)
                            for a in a2: tutte[a["ad_archive_id"]] = a
                            print(f"    {st_}/{med}: Meta {d2} · lette {len(a2)}", flush=True)
                            # oltre ~1.400 anche la fetta si ferma: si divide ancora per piattaforma
                            if d2 and len(a2) < d2 - max(2, d2 // 100):
                                for pl in ("facebook", "instagram", "messenger", "audience_network", "threads"):
                                    d3, a3 = leggi(pg, pid, st_, med, [pl])
                                    for a in a3: tutte[a["ad_archive_id"]] = a
                                    print(f"      {pl}: Meta {d3} · lette {len(a3)}", flush=True)
                    ads = list(tutte.values())
            except Exception as e:
                print(f"  {name}: ERRORE {str(e)[:80]}", flush=True); continue
            new = mine_n = 0
            for j, ad in enumerate(ads, 1):
                if j % 50 == 0: c.commit()   # mai tenere il database bloccato per una pagina intera: l'altra corsia aspetta
                mine = B._matches_brand(ad, b) or (not ad.get("domain") and B._norm_txt(ad.get("body")) in testi) \
                       or (B._SOCIAL.match(ad.get("domain") or "") and pid in pulite)
                mine_n += bool(mine)
                for tent in range(20):   # due corsie scrivono insieme: un blocco breve non deve far cadere il brand
                    try:
                        if DB.upsert_ad(c, ad, bid if mine else None, source=f"page:{pid}") == "new": new += 1
                        break
                    except sqlite3.OperationalError as ex:
                        if "locked" not in str(ex) or tent == 19: raise
                        time.sleep(3)
            # 20 nov: lib_rank lo scrive SOLO top20.py (ordine impression sul dominio). Qui sovrascriveva
            # con la posizione nella singola pagina e la Home mostrava Heusom #3, #19, #21.
            for tent in range(20):
                try: c.commit(); break
                except sqlite3.OperationalError: time.sleep(3)
            # Meta conta spesso 1-2 ad che non mostra mai (rimosse/riservate): tolleranza dell'1%, minimo 2
            completa = declared is not None and len(ads) >= declared - max(2, declared // 100)
            if ads: zeri = 0
            # "0 ad" su una pagina che in archivio ne ha di attive = blocco di Meta, non pagina vuota
            # (13 nov sera: Meta rispondeva 0 ovunque e 556 ad di Nuracalm risultavano spente)
            if not ads and c.execute("SELECT COUNT(*) FROM ads WHERE page_id=? AND is_active=1", (pid,)).fetchone()[0]:
                completa = False
                print(f"  {name}: Meta risponde 0 ma in archivio ci sono attive → lettura sospetta, non spengo nulla", flush=True)
                zeri += 1
                if zeri >= 2:   # due pagine di fila a zero = blocco di Meta: ci si ferma tutti per 3 ore
                    open(os.path.join(R, "data", "meta_blocco"), "w").write(str(time.time()))
                    print("  BLOCCO META: interrompo e segnalo agli altri lettori (3 ore di pausa)", flush=True)
                    break
            spente = 0
            vive_db = c.execute("SELECT COUNT(*) FROM ads WHERE page_id=? AND is_active=1", (pid,)).fetchone()[0]
            if active == "active" and completa and vive_db >= 20 and len(ads) < vive_db * 0.4:
                completa = False   # più di metà delle attive sparite in un colpo: si rilegge, non si spegne
                print(f"  {name}: {len(ads)} attive su {vive_db} in archivio → calo sospetto, non spengo nulla", flush=True)
            if active == "active" and completa:
                vivi = {a["ad_archive_id"] for a in ads}
                for (aid,) in c.execute("SELECT ad_archive_id FROM ads WHERE page_id=? AND is_active=1", (pid,)).fetchall():
                    if aid not in vivi:
                        c.execute("UPDATE ads SET is_active=0, end_date=COALESCE(end_date,?) WHERE ad_archive_id=?", (t, aid)); spente += 1
                c.commit()
            print(f"  {name}: Meta {declared} · lette {len(ads)} · del brand {mine_n} · nuove {new} · spente {spente} · {'COMPLETA' if completa else 'INCOMPLETA'} · {time.time()-t0:.0f}s", flush=True)
        br.close()
    DB.recount_pages(c, bid); c.commit(); c.close()

if __name__ == "__main__":
    main()
