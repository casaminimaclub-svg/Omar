#!/usr/bin/env python3
"""Ecom Radar — ricerca LIVE sulla Ad Library ("cerca tutto").

arg = JSON {"q": "...", "countries": ["ALL","US"], "pages": 5, "active": "all"} oppure stringa semplice.
Ogni ad trovata entra in archivio (brand_id NULL, source='search:<q>') così resta
cercabile per sempre; le pagine trovate entrano in `pages` senza brand.
Ritorna un riepilogo: totale dichiarato, domini, pagine, ad.
"""
import json, os, sys, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB
import meta_lib as M


def run(arg, log=print):
    try: spec = json.loads(arg) if isinstance(arg, str) and arg.strip().startswith("{") else {"q": arg}
    except Exception: spec = {"q": arg}
    q = spec.get("q", "").strip(); countries = spec.get("countries") or ["ALL"]; pages = int(spec.get("pages") or 5)
    active = spec.get("active") or "all"; page_id = spec.get("page_id")
    c = DB.conn()
    c.execute("INSERT INTO searches(q,kind,country,created,last_run) VALUES(?,?,?,?,?)", (q or page_id, "page" if page_id else "keyword", ",".join(countries), DB.now(), DB.now()))
    sid = c.execute("SELECT last_insert_rowid() i").fetchone()["i"]; c.commit()
    doms = Counter(); pgs = Counter(); n = 0; new = 0; total = None
    for cc in countries:
        try:
            def on_page(t, k):
                nonlocal total
                if k == 0: total = (total or 0) + (t or 0); log(f"  live {q or page_id} {cc}: {t} ad dichiarate")
            for ad in M.search(query=q or None, page_id=page_id, country=cc, active=active, max_pages=pages, on_page=on_page):
                n += 1
                st = DB.upsert_ad(c, ad, None, source=f"search:{q or page_id}")
                if st == "new": new += 1
                DB.upsert_page(c, ad, None, None)
                c.execute("INSERT OR IGNORE INTO search_hits(search_id, ad_archive_id) VALUES(?,?)", (sid, ad["ad_archive_id"]))
                doms[ad.get("domain") or "?"] += 1; pgs[(ad["page_id"], ad.get("page_name"))] += 1
                if n % 5 == 0: c.commit()
            c.commit()
        except M.Blocked as ex:
            log(f"  live {cc}: BLOCCO {ex}"); time.sleep(30)
    c.execute("UPDATE searches SET total=?, n_pages=?, last_run=? WHERE id=?", (total, len(pgs), DB.now(), sid)); c.commit()
    DB.recount_pages(c)
    import score as S
    for aid, in [(r["ad_archive_id"],) for r in c.execute("SELECT ad_archive_id FROM search_hits WHERE search_id=?", (sid,))]:
        a = dict(c.execute("SELECT ad_archive_id, page_id, start_date, end_date, is_active, collation_count, eu_total_reach, reactions, format FROM ads WHERE ad_archive_id=?", (aid,)).fetchone())
        sc = S.score_ad(a); est, basis = S.estimate(a)
        c.execute("UPDATE ads SET score=?, est_spend=?, est_spend_basis=? WHERE ad_archive_id=?", (sc, round(est, 2), basis, aid))
    c.commit(); c.close()
    log(f"LIVE {q or page_id}: {n} ad lette ({new} nuove), {len(pgs)} pagine, top domini {dict(doms.most_common(6))}")
    return {"search_id": sid, "n": n, "new": new, "total": total, "domains": doms.most_common(20), "pages": [(p[0], p[1], k) for p, k in pgs.most_common(30)]}


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), indent=1, ensure_ascii=False))
