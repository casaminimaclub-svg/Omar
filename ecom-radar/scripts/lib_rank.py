"""Ordine dell'Ad Library per le ad di un brand: per ogni pagina si legge la vista di default
(attive, tutti i paesi, ordine di Meta) e si salva la posizione in ads.lib_rank.
Serve per le ad senza reach (USA e resto del mondo): non c'e' un numero, ma Meta le mette gia' in fila dalla migliore.
Uso: lib_rank.py <brand_id> [...]  (senza argomenti: tutti i brand)"""
import os, sys, sqlite3, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "radar"))
import meta_lib as M
DBP = os.path.join(os.path.dirname(__file__), "..", "data", "radar.db")
c = sqlite3.connect(DBP, timeout=600)
ids = [int(a) for a in sys.argv[1:]] or [r[0] for r in c.execute("SELECT id FROM brands ORDER BY id")]
for bid in ids:
    pagine = [r[0] for r in c.execute("SELECT page_id FROM ads WHERE brand_id=? AND is_active=1 GROUP BY page_id ORDER BY COUNT(*) DESC", (bid,))]
    pos = {}
    for pid in pagine:
        for tent in range(4):   # rate-limit di Meta: si aspetta e si riprova, mai una pagina persa
            try:
                for i, ad in enumerate(M.search(page_id=pid, active="active", max_ads=600)):
                    aid = str(ad.get("ad_archive_id") or "")
                    if aid and aid not in pos: pos[aid] = i
                break
            except Exception as e:
                print("  pagina", pid, "errore", e, "· riprovo", flush=True); time.sleep(60 * (tent + 1))
        time.sleep(10)   # ritmo lento: connessione condivisa con altre chat
    c.execute("UPDATE ads SET lib_rank=NULL WHERE brand_id=?", (bid,))
    c.executemany("UPDATE ads SET lib_rank=? WHERE ad_archive_id=? AND brand_id=?", [(r, a, bid) for a, r in pos.items()]); c.commit()
    print("brand", bid, ":", len(pos), "ad in ordine Ad Library su", len(pagine), "pagine", flush=True)
