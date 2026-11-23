"""Mercati di un brand (trucco di Chry, 20 nov): Ad Library cercata sul dominio del brand, solo attive,
ordine impression, UN PAESE ALLA VOLTA. Dice quante ad attive ha il brand in ogni paese, in quali paesi
gira ogni ad e la classifica per paese. Tabelle: brand_markets (conteggio per paese per giorno),
ad_markets (ad × paese con posizione). Uso: paesi.py <brand_id>"""
import os, sys, time, sqlite3
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(R, "radar")); sys.path.insert(0, os.path.join(R, "scripts"))
import db as DB, brand as B
from top20 import leggi, ranghi
from pagine_browser import bloccata, raffredda
from playwright.sync_api import sync_playwright

PAESI = ["US", "GB", "CA", "AU", "NZ", "IE", "DE", "AT", "CH", "FR", "BE", "NL", "IT", "ES", "PT",
         "SE", "NO", "DK", "FI", "PL", "CZ", "GR", "RO", "HU", "BR", "MX", "AE", "SA", "ZA", "JP", "SG"]

def main():
    bid = int(sys.argv[1]); c = DB.conn(); b = B._brand(c, bid); t = DB.today()
    c.executescript("""CREATE TABLE IF NOT EXISTS brand_markets(brand_id INT, cc TEXT, day TEXT, active INT, letti INT, PRIMARY KEY(brand_id, cc, day));
        CREATE TABLE IF NOT EXISTS ad_markets(ad_archive_id TEXT, cc TEXT, rank INT, seen TEXT, PRIMARY KEY(ad_archive_id, cc));
        CREATE INDEX IF NOT EXISTS idx_admk_cc ON ad_markets(cc, rank);""")
    testi = {B._norm_txt(r[0]) for r in c.execute("SELECT body FROM ads WHERE brand_id=? AND domain IS NOT NULL AND body IS NOT NULL", (bid,))} - {""}
    dom = b.get("domain") or b["domains_l"][0]
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--disable-gpu", "--mute-audio", "--autoplay-policy=user-gesture-required"])
        pg = br.new_page(locale="en-US", viewport={"width": 800, "height": 600})
        pg.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image", "media", "font", "stylesheet") else r.continue_())
        # 22 nov: 31 ricerche per brand facevano bloccare l'IP da Meta. Giro completo solo la prima volta;
        # poi i paesi dove il brand è già stato visto + US e GB (dove Meta mostra le non-UE).
        noti = {r[0] for r in c.execute("SELECT DISTINCT cc FROM brand_markets WHERE brand_id=? AND active>0", (bid,))}
        fatto = c.execute("SELECT COUNT(DISTINCT cc) FROM brand_markets WHERE brand_id=?", (bid,)).fetchone()[0] >= len(PAESI)
        lista = [x for x in PAESI if x in noti | {"US", "GB"}] if fatto else PAESI
        for cc in lista:
            if bloccata(): print("  Meta in pausa per blocco: mi fermo", flush=True); break
            raffredda()
            try: declared, ads = leggi(pg, dom, "all", 1500, country=cc)
            except Exception as e: print(f"  {cc}: ERRORE {str(e)[:80]}", flush=True); continue
            n = 0
            c.execute("DELETE FROM ad_markets WHERE cc=? AND ad_archive_id IN (SELECT ad_archive_id FROM ads WHERE brand_id=?)", (cc, bid))
            for rk, ad in ranghi(ads):
                if not (B._matches_brand(ad, b) or (not ad.get("domain") and B._norm_txt(ad.get("body")) in testi)): continue
                n += 1
                for tent in range(20):
                    try:
                        DB.upsert_ad(c, ad, bid, source=f"paesi:{cc}")
                        c.execute("INSERT OR REPLACE INTO ad_markets VALUES (?,?,?,?)", (ad["ad_archive_id"], cc, rk, t)); break
                    except sqlite3.OperationalError as ex:
                        if "locked" not in str(ex) or tent == 19: raise
                        time.sleep(3)
            c.execute("INSERT OR REPLACE INTO brand_markets VALUES (?,?,?,?,?)", (bid, cc, t, declared or 0, n)); c.commit()
            print(f"  {b['name']} {cc}: Meta {declared} · lette {len(ads)} · del brand {n}", flush=True)
        br.close()
    c.close()

if __name__ == "__main__":
    main()
