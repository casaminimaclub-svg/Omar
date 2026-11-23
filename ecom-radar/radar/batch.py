#!/usr/bin/env python3
"""Ecom Radar — coda di brand: li mappa uno dopo l'altro (un solo IP: niente parallelismo
verso Meta). Salta i brand già 'ready'. Poi, per ognuno, transcript dei top video e dossier.

  python3 batch.py urls.txt            (una URL per riga, # commenti)
  python3 batch.py --study             (solo dossier per i brand ready senza dossier)
"""
import os, sys, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB
import brand as B


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def main():
    DB.init()
    # un solo processo alla volta verso Meta (coda + refresh notturno non devono sovrapporsi)
    import fcntl
    lock_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".batch.lock")
    lock = open(lock_path, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("un altro batch/refresh è in corso: esco"); return
    c = DB.conn()
    import formats; formats.migrate(c, log=log)      # ad senza fmt (inserite da processi vecchi) → classificate
    if not DB.kv_get(c, "fts_rowid"):
        log("indice full-text: ricostruzione una tantum con rowid = id (rende istantanei gli aggiornamenti)"); DB.rebuild_fts(c, log=log)
    c.close()
    if "--refresh" in sys.argv:
        import digest
        c = DB.conn(); ids = [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='ready' ORDER BY id")]; c.close()
        for bid in ids:
            try: B.refresh(bid, log=log)
            except Exception as ex: log(f"refresh {bid} errore {ex}"); time.sleep(60)
        log(digest.build(1)); return
    if "--study" in sys.argv:
        import study, transcribe
        c = DB.conn(); ids = [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='ready' AND (notes IS NULL OR notes='')")]; c.close()
        for bid in ids:
            try:
                transcribe.run(f"brand:{bid}", limit=15, log=log); B.creative(bid, log=log); B.score(bid, log=log); study.run(bid, log=log)
            except Exception as ex:
                log(f"study {bid} errore {ex}")
        return
    urls = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
    # PIPELINE PARALLELA PER RISORSA: lo stadio Meta (discover+pull) resta seriale perché il ritmo
    # verso Meta è un solo rubinetto (Limiter globale, un IP). Ogni brand che esce dal pull entra
    # in un proprio thread "post" e i passi si contendono solo la risorsa che usano davvero:
    #   net    (miniature fbcdn)                       → 2 alla volta
    #   pw     (landing Playwright)                    → 1 alla volta
    #   cpu    (whisper)                               → 1 alla volta
    #   claude (analisi creativa, dossier)             → 2 alla volta, con guardia del piano
    # Così miniature del brand 5, landing del 4, transcript del 3 e Ad Library del 6 girano insieme.
    import threading
    import study, transcribe
    SEM = {"net": threading.Semaphore(2), "pw": threading.Semaphore(1), "cpu": threading.Semaphore(1), "claude": threading.Semaphore(2), "meta": threading.Semaphore(1)}
    def step(kind, fn):
        with SEM[kind]: return fn()

    def post_brand(bid):
        lg = lambda m: log(f"[#{bid}] {m}")
        try:
            step("net", lambda: B.thumbs(bid, log=lg))
            step("meta", lambda: B.enrich(bid, log=lg))    # un enrich alla volta: meno scrittori concorrenti sul DB (starvation WAL)
            step("pw", lambda: B.landings(bid, limit=80, log=lg))   # un solo Playwright alla volta
            B.score(bid, log=lg)
            c = DB.conn()
            live = c.execute("SELECT COUNT(*) FROM ads WHERE brand_id=? AND is_active=1", (bid,)).fetchone()[0]; c.close()
            step("claude", lambda: B.creative(bid, limit=max(150, min(500, live)), log=lg))
            B.score(bid, log=lg)
            try: step("cpu", lambda: transcribe.run(f"brand:{bid}", limit=15, log=lg))
            except Exception as ex: lg(f"transcribe: {ex}")
            c = DB.conn(); c.execute("UPDATE brands SET status='ready', last_scan=? WHERE id=?", (DB.now(), bid)); c.commit(); c.close()
            step("claude", lambda: study.run(bid, log=lg))
            lg(B.dossier(bid))
        except Exception as ex:
            lg(f"POST ERRORE: {ex}\n{traceback.format_exc()[-600:]}")

    threads = []
    def post_start(bid):
        t = threading.Thread(target=post_brand, args=(bid,), daemon=True, name=f"post-{bid}"); t.start(); threads.append(t)

    # brand rimasti a metà da giri precedenti: partono subito in parallelo
    c = DB.conn(); leftover = [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='pulled' OR (status='ready' AND (notes IS NULL OR notes=''))")]; c.close()
    for bid in leftover:
        log(f"#{bid} ripreso dallo stadio post (era a metà)"); post_start(bid)

    zero = 0
    for u in urls:
        try:
            bid = B.add_brand(u, log=log)
            c = DB.conn(); st = c.execute("SELECT status FROM brands WHERE id=?", (bid,)).fetchone()["status"]; c.close()
            if st == "ready" or bid in leftover:
                log(f"skip #{bid} ({'già ready' if st == 'ready' else 'già nello stadio post'})"); continue
            if st == "discovered":
                log(f"#{bid} già scoperto: riprendo dal pull")
            else:
                B.discover(bid, log=log)
                c = DB.conn(); npg = c.execute("SELECT COUNT(*) FROM pages WHERE brand_id=?", (bid,)).fetchone()[0]
                if not npg:
                    # zero pagine: blocco Meta oppure keyword/dominio che non compaiono in nessuna ad
                    import meta_lib as M
                    try:
                        probe = sum(1 for _ in M.search(query="vitamin", country="US", active="active", max_pages=1, retries=1))
                    except Exception:
                        probe = 0
                    if probe:
                        c.execute("UPDATE brands SET status='empty' WHERE id=?", (bid,)); c.commit(); c.close()
                        log(f"#{bid} nessuna ad trovata per {u}: la Ad Library risponde, quindi il brand pubblica sotto un altro dominio/nome. Servono keyword o dominio alternativi (radar add <url delle ad>)")
                        continue
                    c.execute("UPDATE brands SET status='new' WHERE id=?", (bid,)); c.commit(); c.close()
                    zero += 1; log(f"#{bid} zero pagine e Ad Library muta: blocco Meta, resta in coda, pausa 5 min")
                    if zero >= 2: log("due brand a zero di fila: Meta blocca, fermo lo stadio Meta (rilanciare più tardi)"); break
                    time.sleep(300); continue
                c.close(); zero = 0
            B.pull_pages(bid, log=log, skip_fresh_hours=12)    # una coda riavviata non rilegge ciò che ha letto poche ore fa
            post_start(bid)
        except Exception as ex:
            log(f"ERRORE su {u}: {ex}\n{traceback.format_exc()[-800:]}")
            time.sleep(120)
    for t in threads: t.join()
    # dossier ancora mancanti (es. saltati dalla guardia del piano): ultimo tentativo
    c = DB.conn(); ids = [r["id"] for r in c.execute("SELECT id FROM brands WHERE status='ready' AND (notes IS NULL OR notes='')")]; c.close()
    for bid in ids:
        try: study.run(bid, log=log)
        except Exception as ex: log(f"study {bid} errore {ex}")

def checkpoint():
    try:
        c = DB.conn(); c.execute("PRAGMA wal_checkpoint(TRUNCATE)"); c.close()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    finally:
        checkpoint()
