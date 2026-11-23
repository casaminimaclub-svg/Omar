#!/usr/bin/env python3
"""Ecom Radar — ingestione di un brand "fino al midollo".

  add_brand(url)      registra il brand (dominio, nome)
  discover(brand)     ricerche keyword (nome, dominio, alias) su più paesi → clustering
                      per dominio di destinazione → tutte le PAGINE che pubblicano per quel
                      dominio (pagina principale + pagine persona/alias)
  pull_pages(brand)   per ogni pagina: archivio COMPLETO (attive + non attive, tutti i paesi)
  enrich(brand)       trasparenza EU per le ad idonee (reach, età/genere/paese, payer)
  landings(brand)     crawl delle landing dietro le ad (screenshot, tipo, prezzo, stack)
  score(brand)        punteggio winner + spesa stimata

`python3 brand.py add <url>` fa tutto in sequenza e stampa il dossier.
"""
import json, os, re, sqlite3, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB
import meta_lib as M

MARKETS = ["ALL", "US", "GB", "AU", "CA", "DE", "FR", "IT", "ES", "NL"]
# Domini che NON identificano mai un brand: sono infrastruttura condivisa da chiunque.
# Averli presi per domini di Gundry MD ha attaccato al brand 6.987 ad altrui (Maroon 5,
# Warner Music, Dr. Marty Pets...): un accorciatore lo usano migliaia di inserzionisti.
GENERIC = {"bit.ly", "facebook.com", "instagram.com", "fb.me", "l.facebook.com", "linktr.ee", "amazon.com", "amzn.to", "youtube.com", "tiktok.com", "wa.me", "m.me",
           "rebrand.ly", "lnk.to", "tinyurl.com", "t.co", "ow.ly", "buff.ly", "shorturl.at", "cutt.ly", "smarturl.it", "found.ee", "ffm.to", "orcd.co", "backl.ink", "linkfire.com", "songwhip.com", "spoti.fi", "open.spotify.com", "submithub.com", "trib.al", "goo.gl", "is.gd", "rb.gy", "s.id", "bl.ink", "short.io"}


_SOCIAL = re.compile(r"^(www\.|m\.|l\.)?(facebook\.com|instagram\.com|fb\.com|m\.me|wa\.me|messenger\.com)$")

def _norm_txt(t):
    return re.sub(r"\W+", " ", (t or "").lower()).strip()[:160]


def generico(d):
    """Vero anche per i sottodomini: `filtr.lnk.to` e `maroon5.lnk.to` sono lo stesso accorciatore."""
    d = (d or "").lower()
    return any(d == g or d.endswith("." + g) for g in GENERIC)


def domain_of_url(u):
    d = M.domain_of(u) or u.lower().strip()
    return d


def brand_root(domain):
    """holior.com ← shop.holior.com / get.tryrosabella.com → tryrosabella.com"""
    parts = domain.split(".")
    if len(parts) >= 3 and parts[-2] not in ("co", "com", "org", "net") :
        return ".".join(parts[-2:])
    if len(parts) >= 3:
        return ".".join(parts[-3:])
    return domain


def brand_tokens(domain):
    """Termini di ricerca: 'tryrosabella' → ['tryrosabella','rosabella'] ; 'officialpurelia' → ['officialpurelia','purelia']"""
    core = brand_root(domain).split(".")[0]
    toks = [core]
    for pre in ("try", "get", "shop", "official", "the", "my", "go", "buy", "hello", "meet", "with"):
        if core.startswith(pre) and len(core) > len(pre) + 3:
            toks.append(core[len(pre):])
    for suf in ("official", "shop", "store", "usa", "uk", "co"):
        if core.endswith(suf) and len(core) > len(suf) + 3:
            toks.append(core[:-len(suf)])
    return list(dict.fromkeys(toks))


def add_brand(url, name=None, log=print):
    DB.init()
    c = DB.conn()
    dom = domain_of_url(url)
    root = brand_root(dom)
    name = name or brand_tokens(dom)[-1].capitalize()
    row = c.execute("SELECT id FROM brands WHERE domain=?", (root,)).fetchone()
    if row:
        bid = row["id"]
        c.execute("UPDATE brands SET url=COALESCE(url,?) WHERE id=?", (url, bid))
    else:
        bid = c.execute("INSERT INTO brands(name,url,domain,domains,added,status,keywords) VALUES(?,?,?,?,?,?,?)",
                  (name, url, root, json.dumps([root] + ([dom] if dom != root else [])), DB.today(), "new", json.dumps(brand_tokens(dom)))).lastrowid
        DB.log_event(c, "brand_added", bid, root, url)
    c.commit(); c.close()
    log(f"BRAND #{bid} {name} · {root} · keywords {brand_tokens(dom)}")
    return bid


def _brand(c, bid):
    b = dict(c.execute("SELECT * FROM brands WHERE id=?", (bid,)).fetchone())
    b["domains_l"] = json.loads(b.get("domains") or "[]")
    b["keywords_l"] = json.loads(b.get("keywords") or "[]")
    return b


def _matches_brand(ad, b):
    d = ad.get("domain") or ""
    cap = (ad.get("caption") or "").lower()
    for bd in b["domains_l"]:
        if d == bd or d.endswith("." + bd) or cap == bd or cap.endswith("." + bd):
            return True
    return False


def discover(bid, markets=None, max_requests=40, log=print, extra_queries=None):
    """Trova le pagine del brand: keyword = nome/dominio/alias, su più mercati.
    Le ad che puntano al dominio del brand rivelano le pagine; le pagine rivelano altri
    domini (redirect/alias) che vengono aggiunti al brand e cercati a loro volta."""
    M.LIMITER.nuova_fase()
    c = DB.conn(); b = _brand(c, bid)
    markets = markets or ["ALL"]   # la ricerca ALL copre tutti i paesi; le fette per data danno la profondità
    # nome/alias del brand (budget pieno) + dominio radice (metà budget: ridondante coi token del nome)
    queries = list(dict.fromkeys(b["keywords_l"] + [b["domain"]] + [d for d in b["domains_l"] if d != b["domain"]] + list(extra_queries or [])))   # anche i domini alias (es. calmicollar.com)
    page_hits = Counter(); page_meta = {}; new_domains = Counter(); n_seen = 0; n_new = 0
    neighbors = Counter(); neigh_meta = {}      # altri advertiser incontrati cercando questo brand: cloni, concorrenti, affiliati
    known_pages = {r["page_id"] for r in c.execute("SELECT page_id FROM pages WHERE brand_id=?", (bid,))}
    first_discover = not known_pages
    for q in queries:
        for cc in markets:
            try:
                total_holder = {}
                def on_page(total, p): total_holder["t"] = total
                got = 0
                def on_slice(si, un, tot, g, k):
                    if k == 1: total_holder["t"] = tot; log(f"  discover q={q!r} cc={cc}: {tot} risultati dichiarati (rumore incluso)")
                    elif k % 10 == 0: log(f"    ...{k} richieste, {n_seen} ad del brand finora")
                for ad in M.search_sliced(query=q, country=cc, start="2024-01-01", max_requests=(max_requests if q in b["keywords_l"] else max(6, max_requests // 2)), on_slice=on_slice, gql_fallback=False):
                    got += 1
                    if not _matches_brand(ad, b):
                        d = ad.get("domain")
                        if d and not generico(d):
                            neighbors[d] += 1; neigh_meta.setdefault(d, {"page_name": ad.get("page_name"), "page_id": ad.get("page_id"), "title": ad.get("title") or (ad.get("body") or "")[:80], "active": 0})
                            if ad.get("is_active"): neigh_meta[d]["active"] += 1
                        continue
                    if True:
                        n_seen += 1
                        if ad["page_id"] not in known_pages:
                            known_pages.add(ad["page_id"])
                            if not first_discover: DB.log_event(c, "new_page", bid, ad["page_id"], f"nuova pagina: {ad.get('page_name')}")
                        page_hits[ad["page_id"]] += 1; page_meta[ad["page_id"]] = ad
                        DB.upsert_page(c, ad, bid, None)
                        st = DB.upsert_ad(c, ad, bid, source=f"discover:{q}:{cc}")
                        if st == "new": n_new += 1
                        c.commit()   # una transazione per ad: il lock si libera a ogni attesa di rete
                log(f"  discover q={q!r} cc={cc}: total={total_holder.get('t')} letti={got} del-brand={n_seen}")
                c.commit()
                # su ALL basta se il totale è piccolo: gli altri mercati non aggiungono nulla
                if cc == "ALL" and (total_holder.get("t") or 0) <= got:
                    break
            except M.Blocked as ex:
                log(f"  discover q={q!r} cc={cc}: BLOCCO {ex} → pausa 60s"); time.sleep(60)
    # pagine del brand: quelle che hanno pubblicato ≥1 ad verso il dominio
    for pid, n in page_hits.most_common():
        nm = (page_meta[pid].get("page_name") or "").lower().replace(" ", "").replace("'", "").replace(".", "")
        role = "main" if any(t in nm for t in b["keywords_l"]) else "alias"
        c.execute("UPDATE pages SET brand_id=?, role=CASE WHEN role='main' THEN 'main' ELSE ? END WHERE page_id=?", (bid, role, pid))
    # alias domain: altri domini usati dalle stesse pagine (redirect tracker, funnel host)
    for pid in page_hits:
        for r in c.execute("SELECT domain, COUNT(*) n FROM ads WHERE page_id=? AND domain IS NOT NULL GROUP BY domain", (pid,)):
            if not any(r["domain"] == bd or r["domain"].endswith("." + bd) for bd in b["domains_l"]) and not generico(r["domain"]) and r["n"] >= 3:
                new_domains[r["domain"]] += r["n"]
    c.execute("UPDATE brands SET status=CASE WHEN status IN ('new','') OR status IS NULL THEN 'discovered' ELSE status END, last_scan=? WHERE id=?", (DB.now(), bid))
    if neighbors:
        prev = {x["domain"]: x for x in (DB.kv_get(c, f"neighbors:{bid}") or [])}
        merged = []
        for d, n in neighbors.most_common(40):
            m = neigh_meta[d]; old = prev.get(d, {})
            merged.append({"domain": d, "n": max(n, old.get("n", 0)), "active": m["active"], "page_name": m["page_name"], "page_id": m["page_id"], "title": m["title"]})
        DB.kv_set(c, f"neighbors:{bid}", merged)
    DB.recount_pages(c, bid)
    c.commit()
    log(f"DISCOVER {b['name']}: {len(page_hits)} pagine, {n_seen} ad del brand viste ({n_new} nuove). Domini collegati candidati: {dict(new_domains.most_common(8))}")
    c.close()
    return dict(page_hits), dict(new_domains)


def pull_pages(bid, only_new=False, max_pages=400, log=print, page_filter=None, full=False, skip_fresh_hours=0):
    """Archivio completo di ogni pagina del brand (attive+non attive, country=ALL).
    Le ad della pagina verso ALTRI domini (dropshipper multi-store) restano in archivio
    ma senza brand_id, così la pagina è letta tutta e il brand resta pulito."""
    M.LIMITER.nuova_fase()
    c = DB.conn(); b = _brand(c, bid)
    pages = [dict(r) for r in c.execute("SELECT * FROM pages WHERE brand_id=? ORDER BY n_ads DESC", (bid,))]
    if page_filter: pages = [p for p in pages if p["page_id"] in page_filter]
    tot_new = 0; run_seen = set(); pulled = set(); rimandate = []
    # pagine usate SOLO dal brand (nessuna ad verso domini di altri): lì anche le ad che portano
    # a facebook/instagram (like, post, messaggi) sono del brand. Heusom: 36 attive perse così.
    pagine_pulite = set()
    for (pid_,) in c.execute("SELECT page_id FROM pages WHERE brand_id=?", (bid,)).fetchall():
        altri = c.execute("""SELECT COUNT(*) FROM ads WHERE page_id=? AND domain IS NOT NULL AND domain NOT IN ('facebook.com','instagram.com','fb.com','m.me','wa.me','messenger.com')
                             AND (brand_id IS NULL OR brand_id!=?)""", (pid_, bid)).fetchone()[0]
        if not altri: pagine_pulite.add(pid_)
    testi_brand = {_norm_txt(r[0]) for r in c.execute("SELECT body FROM ads WHERE brand_id=? AND domain IS NOT NULL AND body IS NOT NULL", (bid,))} - {""}
    # Una pagina bloccata dal rate-limit non va persa: si rimette in coda e si rilegge alla fine,
    # dopo una pausa vera. Prima restava a meta' (NuraCalm: "Harriet Whitcombe" letta 0 ad su 147).
    giri = [pages]
    for giro_i, giro in enumerate(giri):
      for p in giro:
        if only_new and p.get("last_full_pull"): continue
        if skip_fresh_hours and p.get("last_full_pull"):
            try:
                age_h = (time.time() - time.mktime(time.strptime(p["last_full_pull"], "%Y-%m-%d %H:%M:%S"))) / 3600
                if age_h < skip_fresh_hours:
                    log(f"  PULL {p['name']}: letta {age_h:.1f} h fa, salto"); continue
            except Exception:
                pass
        n = new = other = 0; t0 = time.time(); blocked0 = M.LIMITER.blocked
        try:
            def on_page(total, k):
                if k == 0: log(f"  PULL {p['name']} ({p['page_id']}): {total} ad dichiarate")
            def on_slice(si, un, tot, g, k):
                if k == 1: log(f"  PULL {p['name']} ({p['page_id']}): {tot} ad dichiarate")
                elif k % 25 == 0: log(f"    ...{k} richieste, {n} ad")
            declared, _ = M.count(page_id=p["page_id"], country="ALL", active="all")
            cap = max_pages if (declared or 0) <= 800 or p.get("role") == "main" else 400   # anche le pagine alias grandi vanno lette per intero (complete.py rifinisce)
            if p.get("last_full_pull") and not full:
                # REFRESH: (1) tutte le ad ATTIVE ora (poche richieste) → chi manca è spenta;
                #          (2) le ad lanciate dall'ultimo passaggio (qualsiasi stato)
                from datetime import date as _d, timedelta as _td
                since = (_d.fromisoformat(p["last_full_pull"][:10]) - _td(days=3)).isoformat()
                seen_ids = set()
                import itertools
                s1, s2 = {}, {}
                stream = itertools.chain(M.search_sliced(page_id=p["page_id"], country="ALL", active="active", max_requests=cap, on_slice=on_slice, seen=seen_ids, stats=s1, gql_fallback=True),
                                         M.search_sliced(page_id=p["page_id"], country="ALL", active="all", start=since, max_requests=cap // 2, seen=seen_ids, stats=s2, gql_fallback=True))
            else:
                s1, s2 = {}, {}
                stream = M.search_sliced(page_id=p["page_id"], country="ALL", active="all", max_requests=cap, on_slice=on_slice, stats=s1, gql_fallback=True)
            for ad in stream:
                n += 1; run_seen.add(ad["ad_archive_id"])
                # senza link: solo se il testo è già usato dal brand sui suoi domini
                # (le pagine persona vengono riciclate: la "main" di Nuracalm ora gira ad di AqualityPets)
                mine = _matches_brand(ad, b) or (not ad.get("domain") and _norm_txt(ad.get("body")) in testi_brand) \
                    or (_SOCIAL.match(ad.get("domain") or "") and p["page_id"] in pagine_pulite)
                for _try in range(4):   # un lock lungo non deve far saltare l'intero brand
                    try: st = DB.upsert_ad(c, ad, bid if mine else None, source=f"page:{p['page_id']}"); break
                    except sqlite3.OperationalError as ex:
                        if "locked" not in str(ex) or _try == 3: raise
                        log(f"  db locked, riprovo ({_try+1})"); time.sleep(15)
                if not mine: other += 1
                if st == "new":
                    new += 1
                    if mine and p.get("last_full_pull"):
                        DB.log_event(c, "new_ad", bid, ad["ad_archive_id"], f"{p['name']}: {ad.get('format')} {ad.get('title') or (ad.get('body') or '')[:80]}")
                if n % 40 == 0: c.commit()    # a gruppi: una commit per ad teneva il database occupato in continuazione
            complete = not (s1.get("exhausted") or s2.get("exhausted") or s1.get("errors") or s2.get("errors") or s1.get("lost") or s2.get("lost"))
            # Meta a volte dichiara il totale ma consegna zero ad (blocco morbido): non è una lettura completa,
            # altrimenti tutte le ad attive della pagina risultano spente (Nuracalm 28 ott: 927 -> 2)
            if n == 0 and (declared or 0) > 0: complete = False
            if complete:
                c.execute("UPDATE pages SET last_full_pull=? WHERE page_id=?", (DB.now(), p["page_id"])); pulled.add(p["page_id"])
            else:
                log(f"  PULL {p['name']}: lettura INCOMPLETA (budget/residuo/errori) → non segnata come completa")
            c.commit()
            log(f"  PULL {p['name']}: {n} ad lette, {new} nuove, {other} verso altri domini, {time.time()-t0:.0f}s · ritmo {M.LIMITER.gap:.1f}s · anomalie {M.LIMITER.blocked - blocked0}")
            tot_new += new
        except M.Blocked as ex:
            c.commit(); log(f"  PULL {p['name']}: BLOCCO {ex} dopo {n} ad → pausa 90s, la rileggo alla fine"); time.sleep(90)
            M.LIMITER.nuova_fase()      # senza questo, dopo un blocco TUTTE le pagine successive bloccavano a 0 ad
            if giro_i == 0: rimandate.append(p)
      if giro_i == 0 and rimandate:
          log(f"  PULL: {len(rimandate)} pagine bloccate, pausa 180s e secondo giro"); time.sleep(180)
          M.LIMITER.nuova_fase(); giri.append(rimandate)
    # ad diventate inattive: quelle del brand non viste oggi ma attive in archivio
    t = DB.today()
    # spente = attive in archivio che NON sono comparse in questo giro, solo per pagine lette COMPLETAMENTE
    killed = [k for k in c.execute(f"""SELECT ad_archive_id, page_name, title FROM ads WHERE brand_id=? AND is_active=1
                                      AND page_id IN ({','.join('?'*len(pulled))})""", (bid, *pulled)).fetchall()
              if k["ad_archive_id"] not in run_seen] if pulled else []
    attive = c.execute("SELECT COUNT(*) FROM ads WHERE brand_id=? AND is_active=1", (bid,)).fetchone()[0]
    if attive >= 40 and len(killed) > attive * 0.5:
        log(f"PULL {b['name']}: {len(killed)}/{attive} ad risulterebbero spente in un giro solo: lettura sospetta, non spengo nulla")
        killed = []
    for k in killed:
        c.execute("UPDATE ads SET is_active=0, end_date=COALESCE(end_date,?) WHERE ad_archive_id=?", (t, k["ad_archive_id"]))
        DB.log_event(c, "ad_stopped", bid, k["ad_archive_id"], f"{k['page_name']}: {k['title'] or ''}")
    DB.recount_pages(c, bid)
    c.execute("UPDATE brands SET status=CASE WHEN status='ready' THEN 'ready' ELSE 'pulled' END, last_scan=? WHERE id=?", (DB.now(), bid))
    c.commit(); c.close()
    log(f"PULL {b['name']}: {tot_new} ad nuove in archivio")
    return tot_new


def enrich(bid, limit=400, only_active=False, log=print):
    """Trasparenza EU (reach totale, età/genere, paesi, payer) per le ad idonee non ancora lette."""
    M.LIMITER.nuova_fase()
    c = DB.conn(); b = _brand(c, bid)
    w = "AND is_active=1" if only_active else ""
    # due lettori in parallelo (sessioni Meta separate) si dividono le ad per ultima cifra dell'id
    sh = os.environ.get("RADAR_SHARD")
    if sh: w += f" AND (CAST(substr(ad_archive_id,-1) AS INTEGER) % 2) = {int(sh) % 2}"
    rows = c.execute(f"""SELECT ad_archive_id, page_id, is_aaa_eligible FROM ads WHERE brand_id=?
                         AND (details_checked IS NULL OR (is_active=1 AND details_checked < date('now','localtime'))) {w}
                         ORDER BY is_active DESC, start_date DESC LIMIT ?""", (bid, limit)).fetchall()
    n = 0; blocks = 0
    for r in rows:
        try:
            d = M.details(r["ad_archive_id"], r["page_id"], "ALL", True)   # 20 nov: la reach UK (es. 202k Nuracalm) stava su ad "non idonee" mai rilette
        except M.Blocked as ex:
            blocks += 1
            log(f"  enrich: BLOCCO {ex} ({blocks}/3)")
            if blocks >= 3: log("  enrich: 3 blocchi di fila, stop"); break
            time.sleep(60); M.LIMITER.nuova_fase(); M.session(reset=True); continue   # sessione nuova: quella vecchia Meta la lascia appesa per ore
        blocks = 0; letti = locals().get('letti', 0) + 1
        # il tetto di attesa conta anche il ritmo normale (1 s a richiesta): su una lettura lunga
        # scattava dopo ~15 minuti anche senza nessun blocco vero, e poi bloccava ogni richiesta.
        if letti % 100 == 0: M.LIMITER.nuova_fase()
        pg = d.pop("page") or {}; d.pop("raw", None)
        c.execute("""UPDATE ads SET eu_total_reach=?, reach_by_country=?, reach_by_age=?, reach_by_gender=?, gender_audience=?,
                     age_min=?, age_max=?, location_audience=?, payer=?, beneficiary=?, details_checked=? WHERE ad_archive_id=?""",
                  (d["eu_total_reach"], d["reach_by_country"], d["reach_by_age"], d["reach_by_gender"], d["gender_audience"],
                   d["age_min"], d["age_max"], d["location_audience"], d["payer"], d["beneficiary"], DB.today(), r["ad_archive_id"]))
        if pg.get("page_id"):
            c.execute("""UPDATE pages SET ig_username=COALESCE(?,ig_username), ig_followers=COALESCE(?,ig_followers), verification=COALESCE(?,verification),
                         entity_type=COALESCE(?,entity_type), likes=COALESCE(?,likes), category=COALESCE(?,category) WHERE page_id=?""",
                      (pg.get("ig_username"), pg.get("ig_followers"), pg.get("verification"), pg.get("entity_type"), pg.get("likes"), pg.get("category"), pg["page_id"]))
        c.execute("INSERT OR REPLACE INTO ad_daily(d,ad_archive_id,is_active,eu_total_reach,reactions) VALUES(?,?,(SELECT is_active FROM ads WHERE ad_archive_id=?),?,(SELECT reactions FROM ads WHERE ad_archive_id=?))",
                  (DB.today(), r["ad_archive_id"], r["ad_archive_id"], d["eu_total_reach"], r["ad_archive_id"]))
        n += 1
        # una commit ogni 25 ad invece che a ogni riga: il database resta libero per chi legge
        if n % 25 == 0:
            c.commit()
            log(f"  enrich {n}/{len(rows)}")
            time.sleep(0.2)   # un respiro: la UI deve poter leggere mentre il giro lavora
    c.commit(); c.close()
    log(f"ENRICH {b['name']}: {n} ad con trasparenza EU")
    return n


def landings(bid, limit=120, log=print):
    import lp as LP
    c = DB.conn()
    urls = LP.pending_urls(c, bid, limit=limit)
    c.close()
    log(f"LANDINGS: {len(urls)} URL da crawlare")
    n = LP.crawl(urls, brand_id=bid, log=log) if urls else 0
    c = DB.conn(); LP.link_ads_to_lps(c, bid)
    # stack del brand = unione degli stack delle sue landing
    st = Counter()
    for r in c.execute("SELECT stack FROM landing_pages WHERE brand_id=? AND stack IS NOT NULL", (bid,)):
        for s in json.loads(r["stack"] or "[]"): st[s] += 1
    c.execute("UPDATE brands SET stack=? WHERE id=?", (json.dumps(dict(st.most_common())), bid))
    c.commit(); c.close()
    return n


def score(bid, log=print):
    import score as S
    for _try in range(4):
        try: n = S.score_brand(bid); break
        except sqlite3.OperationalError as ex:
            if "locked" not in str(ex) or _try == 3: raise
            log(f"  score: db occupato, riprovo ({_try+1})"); time.sleep(20)
    log(f"SCORE: {n} ad valutate")
    return n


def thumbs(bid, log=print):
    import thumbs as T
    return T.run(bid, log=log)


def creative(bid, limit=120, log=print):
    import creative as C
    return C.run(bid, limit=limit, log=log)


def full(url, log=print, lp_limit=120, enrich_limit=400):
    bid = add_brand(url, log=log)
    discover(bid, log=log)
    pull_pages(bid, log=log)
    thumbs(bid, log=log)
    enrich(bid, limit=enrich_limit, log=log)
    landings(bid, limit=lp_limit, log=log)
    score(bid, log=log)
    creative(bid, log=log)
    score(bid, log=log)
    c = DB.conn()
    c.execute("UPDATE brands SET status='ready', last_scan=? WHERE id=?", (DB.now(), bid)); c.commit(); c.close()
    log(dossier(bid))
    return bid


def refresh(bid, log=print):
    """Giro quotidiano: nuove ad dalle pagine note, stato attivo/inattivo, EU reach delle attive, landing nuove, score."""
    discover(bid, max_requests=40, log=log)   # 8 ricerche lasciavano fuori pagine intere (Nuracalm, 13 ott)
    pull_pages(bid, log=log, skip_fresh_hours=20)   # un brand interrotto riparte dalle pagine non ancora lette
    thumbs(bid, log=log)
    enrich(bid, limit=200, only_active=True, log=log)
    landings(bid, limit=40, log=log)
    score(bid, log=log)
    # analisi creativa: solo sulle ad LIVE non ancora analizzate, e poche. E' l'unico passo che consuma
    # il piano Claude; le ad gia' spente non servono a nessuna decisione, quindi non si pagano.
    creative(bid, limit=int(os.environ.get("RADAR_CREATIVE_LIMIT", "12")), log=log)
    c = DB.conn(); c.execute("UPDATE brands SET status='ready', last_scan=? WHERE id=?", (DB.now(), bid)); c.commit(); c.close()


def dossier(bid):
    c = DB.conn(); b = _brand(c, bid)
    L = [f"\n=== {b['name']} · {b['domain']} ==="]
    s = c.execute("SELECT COUNT(*) n, COALESCE(SUM(is_active),0) a, SUM(format='video') v, SUM(format='image') i, SUM(format='carousel') k, MIN(start_date) f, SUM(eu_total_reach) r FROM ads WHERE brand_id=?", (bid,)).fetchone()
    L.append(f"ad: {s['n']} ({s['a']} attive) · video {s['v']} · immagini {s['i']} · caroselli {s['k']} · prima ad {s['f']} · EU reach totale {s['r'] or 0:,}")
    L.append("pagine:")
    for p in c.execute("SELECT * FROM pages WHERE brand_id=? ORDER BY n_ads DESC", (bid,)):
        L.append(f"  - {p['name']} [{p['role'] or '?'}] {p['n_ads']} ad ({p['n_active']} attive) · likes {p['likes']} · {p['category']} · {p['profile_uri']}")
    L.append("landing:")
    for l in c.execute("SELECT * FROM landing_pages WHERE brand_id=? ORDER BY n_ads DESC LIMIT 25", (bid,)):
        L.append(f"  - [{l['kind']}] {l['n_ads']} ad · {l['price'] or ''} · {l['url'][:100]}")
    L.append(f"stack: {b.get('stack')}")
    L.append("top ad:")
    for a in c.execute("SELECT * FROM ads WHERE brand_id=? ORDER BY score DESC LIMIT 10", (bid,)):
        L.append(f"  - {a['score']:.0f} {a['format']:8s} {a['start_date']} {'ON ' if a['is_active'] else 'off'} x{a['collation_count']} reach {a['eu_total_reach'] or '-'} · {(a['title'] or a['body'] or '')[:90]!r}")
    c.close()
    return "\n".join(L)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "discover", "pull", "enrich", "landings", "score", "refresh", "dossier"])
    ap.add_argument("arg")
    ap.add_argument("--lp-limit", type=int, default=120)
    a = ap.parse_args()
    if a.cmd == "add":
        full(a.arg, lp_limit=a.lp_limit)
    else:
        bid = int(a.arg)
        {"discover": discover, "pull": pull_pages, "enrich": enrich, "landings": landings, "score": score, "refresh": refresh,
         "dossier": lambda b: print(dossier(b))}[a.cmd](bid)
