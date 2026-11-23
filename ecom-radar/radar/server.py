#!/usr/bin/env python3
"""Ecom Radar — server locale (stdlib). Porta 8772.

  /                     UI
  /api/board            il report di mercato: KPI + lista ad filtrabile/ordinabile
  /api/brands           elenco brand con numeri
  /api/brand?id=        dossier: pagine, landing, stack, timeline lanci, hook ricorrenti
  /api/ad?id=           tutto su un'ad: media, copy, EU, landing, sorelle (stessa collation), storico
  /api/search?q=&live=1 ricerca locale FTS (+ live sulla Ad Library, salvata in archivio)
  /api/lps?brand=       landing page
  /api/events           movimenti (nuove ad, spente, nuove landing, nuove pagine)
  /api/jobs  POST       {kind: add_brand|refresh|live_search|enrich|landings|transcribe, arg}
  /media/thumb?id=      miniatura (cache disco, gli URL fbcdn scadono)
  /media/lp/<id>.jpg    screenshot landing
  /media/video?id=      proxy video (stream) per anteprima
"""
import threading, hashlib, json, os, sqlite3, sys, time, traceback, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import db as DB

import paths as P
PUBLIC = os.path.join(ROOT, "public")
THUMBS = P.THUMBS
PORT = int(os.environ.get("RADAR_PORT", "8772"))
os.makedirs(THUMBS, exist_ok=True)
JOBS_LOCK = threading.Lock()
RUNNING = {}

FORMAT_MAP = {"video": "video", "image": "image", "carousel": "carousel", "static": "image"}



def _int(v, d=0):
    try: return int(v)
    except (TypeError, ValueError): return d


def _batch_running():
    """Vero se batch/refresh tengono il lock: il server non deve fare richieste a Meta in parallelo."""
    import fcntl
    try:
        f = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".batch.lock"), "a")
        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError: return True
        fcntl.flock(f, fcntl.LOCK_UN); return False
    except Exception:
        return False

_LOCKF = os.path.join(ROOT, "data", "daily.lock")
_LAV = [0.0, False]
def lavoro_in_corso():
    """Il giro notturno e' un processo a parte: RUNNING non lo vede, il suo lucchetto si'.
    Mentre scrive, le cache durano di piu': meglio un dato di 5 minuti fa che 20 secondi d'attesa."""
    now = time.time()
    if now - _LAV[0] > 10:
        _LAV[0] = now
        _LAV[1] = os.path.exists(_LOCKF) or bool(RUNNING)
    return _LAV[1]


_STATC = {}; _STATL = threading.Lock()
def qa_cached(c, sql, pa=(), ttl=90):
    if lavoro_in_corso(): ttl = max(ttl, 600)
    k = hashlib.md5(('QA'+sql + repr(pa)).encode()).hexdigest()
    now = time.time()
    with _STATL:
        hit = _STATC.get(k)
        if hit and now - hit[0] < ttl: return hit[1]
    v = qa(c, sql, pa)
    with _STATL:
        _STATC[k] = (now, v)
        if len(_STATC) > 400: _STATC.clear()
    return v


def q1_cached(c, sql, pa=(), ttl=90):
    if lavoro_in_corso(): ttl = max(ttl, 600)
    """Le statistiche della board sono identiche a ogni caricamento: le teniamo per 90 s."""
    k = hashlib.md5((sql + repr(pa)).encode()).hexdigest()
    now = time.time()
    with _STATL:
        hit = _STATC.get(k)
        if hit and now - hit[0] < ttl: return hit[1]
    v = q1(c, sql, pa)
    with _STATL:
        _STATC[k] = (now, v)
        if len(_STATC) > 400: _STATC.clear()
    return v


def q1(c, sql, pa=()):
    r = c.execute(sql, pa).fetchone()
    return dict(r) if r else None


def qa(c, sql, pa=()):
    return [dict(r) for r in c.execute(sql, pa).fetchall()]


import re as _re_mod
_re_ph = _re_mod.compile(r"^\s*\{\{[^}]+\}\}\s*$")


def ad_public(a):
    """Riduce una riga ads per la lista (senza raw/testi enormi)."""
    keep = ["ad_archive_id", "brand_id", "page_id", "page_name", "collation_count", "start_date", "end_date", "is_active",
            "format", "fmt", "display_format", "n_cards", "image_url", "video_url", "thumb", "title", "body", "cta", "link_url", "domain", "lp_id",
            "platforms", "countries", "eu_total_reach", "reactions", "comments", "shares", "score", "est_spend", "est_spend_basis",
            "winner", "gender_audience", "age_min", "age_max", "transcript", "hook", "angle", "lang", "first_seen", "last_seen", "post_url", "n_pages_same", "phash", "kpi_source", "market_voice",
            "lib_rank", "page_rank", "mechanism", "persona", "awareness", "emotion", "creative_format", "cta_style", "reach_country", "country_sel", "mercato", "mkts"]
    o = {k: a.get(k) for k in keep}
    o["dynamic"] = bool(_re_ph.match(o.get("body") or "") or _re_ph.match(o.get("title") or ""))
    if _re_ph.match(o.get("body") or ""): o["body"] = None
    if _re_ph.match(o.get("title") or ""): o["title"] = None
    o["body"] = (o.get("body") or "")[:700]
    o["days"] = days_running(a)
    o["has_transcript"] = bool(a.get("transcript"))
    o.pop("transcript", None)
    return o


def days_running(a):
    if not a.get("start_date"): return 0
    try:
        s = date.fromisoformat(a["start_date"])
        e = date.fromisoformat(a["end_date"]) if (a.get("end_date") and not a.get("is_active")) else date.today()
        return max(1, (e - s).days + 1)
    except Exception:
        return 0


# ---------------- API ----------------
_CC = {"t": 0, "v": []}
def country_codes(c):
    """Codici paese presenti nella reach EU dichiarata (cache 10 min). Ripara anche le ad senza fmt."""
    import time as _t
    if _t.time() - _CC["t"] > 600:
        # dalla tabella per paese già pronta: rileggere il JSON di 350.000 ad costava 1 s a richiesta
        _CC["v"] = [r[0] for r in c.execute("SELECT cc FROM ad_reach_cc GROUP BY cc ORDER BY SUM(reach) DESC")]; _CC["t"] = _t.time()
    return _CC["v"]


def api_board(p):
    c = DB.conn()
    days = _int(p.get("days"), 30); brand = p.get("brand"); fmt = p.get("format"); status = p.get("status", "all")
    country = p.get("country"); q = (p.get("q") or "").strip(); sort = p.get("sort", "reach"); page_id = p.get("page")
    min_days = _int(p.get("min_days")); limit = min(_int(p.get("limit"), 120), 600); offset = _int(p.get("offset"))
    only_winners = p.get("winners") == "1"; lang = p.get("lang"); kind = p.get("kind"); per_brand = _int(p.get("per_brand"))
    angle = p.get("angle"); awareness = p.get("awareness"); emotion = p.get("emotion"); cformat = p.get("cformat")
    w = ["brand_id IS NOT NULL"]; pa = []
    if angle: w.append("angle=?"); pa.append(angle)
    if awareness: w.append("awareness=?"); pa.append(awareness)
    if emotion: w.append("emotion=?"); pa.append(emotion)
    if cformat: w.append("creative_format=?"); pa.append(cformat)
    if brand: w.append("brand_id=?"); pa.append(int(brand))
    if page_id == "none": w.append("(page_id IS NULL OR page_id='')")   # ad senza pagina (vista brand)
    elif page_id: w.append("page_id=?"); pa.append(page_id)
    if fmt in ("video", "statica", "native", "ignoto"): w.append("fmt=?"); pa.append(fmt)
    if status == "active": w.append("is_active=1")
    elif status == "inactive": w.append("is_active=0")
    country = (country or "").upper()[:2] or None
    # Filtro paese = reach VERA in quel paese (dal dettaglio Meta), non "il paese compare in una lista":
    # prima 'IT' passava anche dentro 'UNITED KINGDOM' e l'ordine restava quello della reach totale.
    if country: w.append("ad_archive_id IN (SELECT ad_archive_id FROM ad_reach_cc WHERE cc=?)"); pa.append(country)
    # le ad tolte da Meta senza anteprima (immagine non più recuperabile) si nascondono di default
    if p.get("anteprima") != "tutte": w.append("noprev IS NOT 1")
    reach = p.get("reach")   # 'si' = con reach UE dichiarata · 'no' = senza (USA e resto del mondo)
    if reach == "si": w.append("eu_total_reach IS NOT NULL")
    elif reach == "no": w.append("eu_total_reach IS NULL")
    mercato = (p.get("mercato") or "").upper()
    if mercato == "EXTRA": w.append("(mercato='EXTRA' OR mercato LIKE '%US%' OR mercato LIKE '%AU%' OR mercato LIKE '%CA%')")
    elif mercato in ("US", "AU", "CA", "UK", "EU", "BR"): w.append("instr(mercato, ?) > 0"); pa.append(mercato)
    if lang: w.append("lang=?"); pa.append(lang)
    if only_winners: w.append("winner=1")
    if kind: w.append("lp_id IN (SELECT id FROM landing_pages WHERE kind=?)"); pa.append(kind)
    if days and days < 10000:
        since = (date.today() - timedelta(days=days)).isoformat()
        # "nel periodo" = attiva nel periodo: lanciata prima della fine e non finita prima dell'inizio
        # attiva nel periodo: lanciata entro oggi e non finita prima dell'inizio (le live hanno end_date NULL → oggi)
        # separare il NULL dal confronto lascia usare l'indice (COALESCE lo disattivava)
        # un'ad che Meta da' per ATTIVA e' nel periodo comunque: a volte porta una end_date vecchia
        # pur essendo ancora in onda, e cosi' spariva dalla finestra (743 ad perse sui 30 giorni)
        w.append("start_date <= date('now','localtime') AND (is_active=1 OR end_date IS NULL OR end_date >= ?)"); pa.append(since)
    started = _int(p.get("started"))
    if started: w.append("start_date >= ?"); pa.append((date.today() - timedelta(days=started)).isoformat())
    if q:
        ids = [DB.fts_id(c, r[0]) for r in c.execute("SELECT rowid FROM ads_fts WHERE ads_fts MATCH ? LIMIT 5000", (fts_query(q),))]
        if not ids: w.append("0")
        else: w.append("ad_archive_id IN (%s)" % ",".join("?" * len(ids))); pa += ids
    if min_days:
        w.append("julianday(CASE WHEN is_active=1 THEN date('now','localtime') ELSE COALESCE(end_date,date('now','localtime')) END) - julianday(start_date) + 1 >= ?"); pa.append(min_days)
    where = " AND ".join(w)
    order = {"score": "score DESC", "newest": "start_date DESC", "oldest": "start_date ASC", "days": "(julianday(CASE WHEN is_active=1 THEN date('now','localtime') ELSE COALESCE(end_date,date('now','localtime')) END)-julianday(start_date)) DESC",
             "reach": "eu_total_reach DESC, score DESC", "page_rank": "lib_rank IS NULL, lib_rank ASC, page_rank IS NULL, page_rank ASC", "meta": "lib_rank IS NULL, lib_rank ASC, eu_total_reach DESC", "variants": "collation_count DESC", "spend": "est_spend DESC", "reactions": "reactions_n DESC"}.get(sort, "eu_total_reach DESC, score DESC")
    # senza reach non c'e' numero da ordinare: si segue l'ordine dell'Ad Library (le sue top ad per prime)
    if reach == "no" and sort == "reach": order = "lib_rank IS NULL, lib_rank ASC, score DESC"
    # conteggi da un indice stretto che copre tutte le colonne: leggere le righe intere (corpo dell'ad)
    # costava 35 s su "senza reach". Solo se i filtri stanno nell'indice, altrimenti ogni riga va riletta.
    src_st = "ads INDEXED BY idx_ads_lite"   # copre ogni filtro e ogni colonna dei conteggi: mai le righe intere
    st = q1_cached(c, f"""SELECT COUNT(*) n, COALESCE(SUM(is_active),0) active, SUM(fmt='video') video, SUM(fmt='statica') statica, SUM(fmt='native') native,
                   COALESCE(SUM(est_spend),0) est_spend, COALESCE(SUM(eu_total_reach),0) eu_reach, SUM(eu_total_reach IS NOT NULL) n_eu,
                   COALESCE(SUM(reactions),0) reactions, SUM(winner) winners, COUNT(DISTINCT page_id) pages, COUNT(DISTINCT brand_id) brands,
                   SUM(start_date >= date('now','localtime','-7 day')) new7,
                   SUM(CASE WHEN is_active=1 AND julianday('now','localtime')-julianday(start_date) >= 30 THEN 1 ELSE 0 END) live_30 FROM {src_st} WHERE {where}""", pa)
    # Prima l'ordine sui soli id, poi le righe intere: ordinare SELECT * trascinava nel sort decine di
    # migliaia di righe con il corpo dell'ad (12 KB l'una in media) -> 5-15 s per aprire Esplora.
    # ordinando per reach su tutto l'archivio, l'indice dedicato legge in ordine e si ferma al LIMIT;
    # il pianificatore preferiva quello dei filtri e poi ordinava 58.000 righe a mano (6 s)
    src = "ads INDEXED BY idx_ads_lite"
    # l'indice per reach si ferma al LIMIT solo se quasi tutte le ad passano i filtri: con un filtro
    # stretto (mercato US, un angolo) scorreva l'archivio intero riga per riga (55-85 s)
    if order.startswith("eu_total_reach") and not page_id and not q and not (mercato or angle or awareness or emotion or cformat or lang or kind or reach == "no" or fmt or only_winners or min_days or started):
        src = "ads INDEXED BY idx_ads_brand_reach" if brand else "ads INDEXED BY idx_ads_reach_order"
    if country and order.startswith("eu_total_reach"):   # con un paese scelto, in cima chi ha piu' reach IN QUEL PAESE
        src = "ads"; order = f"(SELECT reach FROM ad_reach_cc WHERE cc='{country}' AND ad_archive_id=ads.ad_archive_id) DESC, score DESC"
    # 20 nov (Chry): si MOSTRANO solo le ad in vetrina (20 per formato); conteggi e numeri restano su tutto
    wv = where if p.get("tutte") == "1" else where + " AND vetrina=1"
    if per_brand > 0:
        # Home a feed per brand: al massimo per_brand ad per brand, nello stesso ordine del sort.
        # Il limite di pagina non si applica: il tetto e' per_brand x numero di brand.
        ids = [r[0] for r in c.execute(
            f"SELECT ad_archive_id FROM (SELECT ad_archive_id, brand_id, ROW_NUMBER() OVER (PARTITION BY brand_id ORDER BY {order}, start_date DESC) rn FROM {src} WHERE {wv}) WHERE rn <= ? ORDER BY brand_id, rn",
            pa + [per_brand])]
    else:
        ids = [r[0] for r in c.execute(f"SELECT ad_archive_id FROM {src} WHERE {wv} ORDER BY {order}, start_date DESC LIMIT ? OFFSET ?", pa + [limit, offset])]
    if ids:
        per_id = {r["ad_archive_id"]: r for r in qa(c, "SELECT * FROM ads WHERE ad_archive_id IN (%s)" % ",".join("?" * len(ids)), ids)}
        rows = [per_id[i] for i in ids if i in per_id]
        if country:
            for r in rows:
                try: r["reach_country"] = json.loads(r.get("reach_by_country") or "{}").get(country); r["country_sel"] = country
                except Exception: pass
    else:
        rows = []
    if rows:   # paesi in cui gira ogni ad (scripts/paesi.py), una query sola; rank NULL = gemella, in fondo
        mk = {}
        try:
            for m in qa(c, "SELECT ad_archive_id, cc FROM ad_markets WHERE ad_archive_id IN (%s) ORDER BY ad_archive_id, rank IS NULL, rank" % ",".join("?" * len(rows)),
                        [r["ad_archive_id"] for r in rows]):
                mk.setdefault(m["ad_archive_id"], []).append(m["cc"])
        except sqlite3.OperationalError:
            pass
        for r in rows: r["mkts"] = mk.get(r["ad_archive_id"], [])
    if p.get("facets") == "0":   # la Home non usa le facet: niente GROUP BY sull'archivio
        c.close()
        return {"countries": [], "stats": st, "ads": [ad_public(a) for a in rows], "total": st["n"],
                "formats": [], "kinds": [], "langs": [], "brands": [], "angles": [], "emotions": [], "cformats": []}
    import re as _re
    # Una faccetta non deve filtrare se stessa. La sostituzione va fatta a parola intera: 'angle=?'
    # dentro 'creative_format=?' non c'e', ma 'fmt=?' sta dentro altre colonne e 'format=?' spezzava
    # 'creative_format=?' in 'creative_(format=? OR 1)' -> SQLite lo leggeva come funzione creative_().
    def senza(colonna):
        return _re.sub(r"(?<![_a-z])" + colonna + r"=\?", f"({colonna}=? OR 1)", where)
    where_nofmt = senza("fmt")
    fmts = qa_cached(c, f"SELECT fmt AS format, COUNT(*) n FROM {src_st} WHERE {where_nofmt} GROUP BY fmt", pa, ttl=1800)   # i conteggi dei formati non dipendono dal formato scelto
    kinds = []; langs = []   # facet non usate dalla UI: due GROUP BY in meno per richiesta
    angles_f = qa_cached(c, f"SELECT angle, COUNT(*) n, SUM(is_active) live FROM ads INDEXED BY idx_ads_lite WHERE {senza('angle')} AND angle IS NOT NULL GROUP BY angle ORDER BY live DESC, n DESC LIMIT 40", pa, ttl=1800)
    emotions = qa_cached(c, f"SELECT emotion, COUNT(*) n FROM ads INDEXED BY idx_ads_lite WHERE {senza('emotion')} AND emotion IS NOT NULL GROUP BY emotion ORDER BY n DESC LIMIT 12", pa, ttl=1800)
    cformats = qa_cached(c, f"SELECT creative_format, COUNT(*) n FROM ads INDEXED BY idx_ads_lite WHERE {senza('creative_format')} AND creative_format IS NOT NULL GROUP BY creative_format ORDER BY n DESC LIMIT 14", pa, ttl=1800)
    brands = qa(c, "SELECT id, name, domain, status FROM brands ORDER BY pinned DESC, name")
    ccs = country_codes(c)
    c.close()
    return {"countries": ccs, "stats": st, "ads": [ad_public(a) for a in rows], "total": st["n"], "formats": fmts, "kinds": kinds, "langs": langs, "brands": brands,
            "angles": angles_f, "emotions": emotions, "cformats": cformats}


def fts_query(q):
    q = q.replace('"', " ").strip()
    toks = [t for t in q.split() if t]
    if not toks: return '""'
    return " ".join(f'"{t}"*' if len(t) > 2 else f'"{t}"' for t in toks)



# --- cache su disco: dopo un riavvio la home risponde subito con l'ultimo risultato e lo rinfresca in fondo
_CACHE_DIR = os.path.join(ROOT, "data", "cache"); os.makedirs(_CACHE_DIR, exist_ok=True)
_REFRESHING = set(); _REFRESH_LOCK = threading.Lock()

def _cache_save(name, obj):
    try:
        tmp = os.path.join(_CACHE_DIR, name + ".json.tmp")
        with open(tmp, "w") as f: json.dump(obj, f)
        os.replace(tmp, os.path.join(_CACHE_DIR, name + ".json"))
    except Exception: pass

def _cache_load(name):
    try:
        with open(os.path.join(_CACHE_DIR, name + ".json")) as f:
            v = json.load(f)
        return tuple(v) if isinstance(v, list) and len(v) == 2 and isinstance(v[0], (int, float)) else v
    except Exception: return None

def _stale_ok(name, refresh):
    """Vero se c'e' un valore stantio da servire: intanto parte UN solo rinfresco in fondo."""
    with _REFRESH_LOCK:
        if name in _REFRESHING: return True
        _REFRESHING.add(name)
    def run():
        try: refresh()
        except Exception: pass
        finally:
            with _REFRESH_LOCK: _REFRESHING.discard(name)
    threading.Thread(target=run, daemon=True).start()
    return True

_BR = {"t": 0, "v": _cache_load("brands")}


def api_brands(p):
    # cache corta anche mentre un lavoro gira: prima si spegneva del tutto e la lista restava lenta per ore
    if _BR["v"] and p.get("fresh") != "1" and time.time() - _BR["t"] < (600 if lavoro_in_corso() else 30): return _BR["v"]
    if _BR["v"] and _stale_ok("brands", lambda: api_brands({"fresh": "1"})) and p.get("fresh") != "1": return _BR["v"]
    c = DB.conn()
    # una sola passata sulle ad invece di nove sottoquery per brand
    agg = {r["brand_id"]: r for r in qa(c, """SELECT brand_id, COUNT(*) n_ads, COALESCE(SUM(is_active),0) n_active,
              COALESCE(SUM(CASE WHEN is_active=1 THEN est_spend END),0) active_spend,
              SUM(start_date>=date('now','localtime','-7 day')) new7, MIN(start_date) first_ad,
              MAX(start_date) last_ad,
              SUM(fmt='video') n_video, SUM(fmt='statica') n_statica,
              SUM(fmt='native') n_native, SUM(fmt='ignoto') n_ignoto,
              COALESCE(SUM(eu_total_reach),0) eu_reach
              FROM ads WHERE brand_id IS NOT NULL GROUP BY brand_id""")}
    npag = {r["brand_id"]: r["n"] for r in qa(c, "SELECT brand_id, COUNT(*) n FROM pages GROUP BY brand_id")}
    nlp = {r["brand_id"]: r["n"] for r in qa(c, "SELECT brand_id, COUNT(*) n FROM landing_pages GROUP BY brand_id")}
    # una lettura indicizzata per brand: la finestra ROW_NUMBER su tutto l'archivio costava 3,5 s
    cov = {}
    for bid_ in [r["id"] for r in qa(c, "SELECT id FROM brands")]:
        r = q1(c, "SELECT image_url cover, ad_archive_id cover_id FROM ads WHERE brand_id=? AND image_url IS NOT NULL ORDER BY score DESC LIMIT 1", (bid_,))
        if r: cov[bid_] = r
    live = {r["brand_id"]: r["live_score"] for r in qa(c, """SELECT brand_id, AVG(score) live_score FROM (
              SELECT brand_id, score, ROW_NUMBER() OVER (PARTITION BY brand_id ORDER BY score DESC) rk
              FROM ads WHERE is_active=1 AND score IS NOT NULL AND brand_id IS NOT NULL) WHERE rk<=20 GROUP BY brand_id""")}
    rows = qa(c, "SELECT * FROM brands")
    for b in rows:
        a = agg.get(b["id"]) or {}
        b["n_ads"] = a.get("n_ads") or 0; b["n_active"] = a.get("n_active") or 0
        b["active_spend"] = a.get("active_spend") or 0; b["new7"] = a.get("new7") or 0
        b["first_ad"] = a.get("first_ad"); b["last_ad"] = a.get("last_ad")
        for k in ("n_video", "n_statica", "n_native", "n_ignoto"): b[k] = a.get(k) or 0
        b["eu_reach"] = a.get("eu_reach") or 0
        b["n_pages"] = npag.get(b["id"], 0); b["n_lps"] = nlp.get(b["id"], 0)
        cv = cov.get(b["id"]) or {}
        b["cover"] = cv.get("cover"); b["cover_id"] = cv.get("cover_id")
        b["live_score"] = round(live.get(b["id"]) or 0, 2)
        b["stack"] = json.loads(b.get("stack") or "{}")
        b["running"] = RUNNING.get(("brand", b["id"]))
    rows.sort(key=lambda b: (-(b.get("pinned") or 0), -(b["n_active"] or 0), -(b["n_ads"] or 0)))   # fissati sempre in cima
    c.close()
    res = {"brands": rows}
    _BR["t"] = time.time(); _BR["v"] = res; _cache_save("brands", res)
    return res


def api_page(p):
    """Report di una pagina (persona/alias): la unità base della rete di un brand."""
    pid = str(p.get("id") or ""); c = DB.conn()
    pg = q1(c, "SELECT * FROM pages WHERE page_id=?", (pid,))
    if not pg: c.close(); return {"error": "pagina non trovata"}
    b = q1(c, "SELECT id, name, domain FROM brands WHERE id=?", (pg.get("brand_id"),)) if pg.get("brand_id") else None
    st = q1(c, """SELECT COUNT(*) n, COALESCE(SUM(is_active),0) active, SUM(fmt='video') video, SUM(fmt='statica') statica, SUM(fmt='native') native,
                  MIN(start_date) first_ad, MAX(start_date) last_ad, SUM(start_date >= date('now','localtime','-7 day')) new7,
                  SUM(start_date >= date('now','localtime','-30 day')) new30, SUM(eu_total_reach) eu_reach, SUM(est_spend) est_spend,
                  AVG(CASE WHEN is_active=1 THEN julianday('now','localtime')-julianday(start_date) END) avg_age_active,
                  AVG(CASE WHEN is_active=0 AND end_date IS NOT NULL THEN julianday(end_date)-julianday(start_date)+1 END) avg_life_dead FROM ads WHERE page_id=?""", (pid,))
    timeline = qa(c, """SELECT strftime('%Y-%W', start_date) wk, MIN(start_date) d, COUNT(*) n, SUM(fmt='video') v, SUM(is_active) a FROM ads
                        WHERE page_id=? AND start_date IS NOT NULL GROUP BY wk ORDER BY wk""", (pid,))
    angles = qa(c, "SELECT angle, COUNT(*) n, SUM(is_active) live, MAX(score) s FROM ads WHERE page_id=? AND angle IS NOT NULL GROUP BY angle ORDER BY live DESC, n DESC LIMIT 20", (pid,))
    headlines = qa(c, "SELECT title h, COUNT(*) n, SUM(is_active) a FROM ads WHERE page_id=? AND title IS NOT NULL AND title!='' AND title NOT LIKE '{{%' GROUP BY title ORDER BY n DESC LIMIT 15", (pid,))
    domains = qa(c, "SELECT domain, COUNT(*) n, SUM(is_active) a FROM ads WHERE page_id=? AND domain IS NOT NULL GROUP BY domain ORDER BY n DESC LIMIT 10", (pid,))
    mk = {}
    for r in c.execute("SELECT reach_by_country FROM ads WHERE page_id=? AND reach_by_country IS NOT NULL", (pid,)):
        for k, v in json.loads(r["reach_by_country"] or "{}").items(): mk[k] = mk.get(k, 0) + (v or 0)
    markets = sorted(mk.items(), key=lambda x: -x[1])
    ctas = qa(c, "SELECT cta, COUNT(*) n FROM ads WHERE page_id=? AND cta IS NOT NULL GROUP BY cta ORDER BY n DESC LIMIT 6", (pid,))
    top = [ad_public(a) for a in qa(c, "SELECT * FROM ads WHERE page_id=? ORDER BY eu_total_reach DESC, score DESC LIMIT 18", (pid,))]
    newest = [ad_public(a) for a in qa(c, "SELECT * FROM ads WHERE page_id=? ORDER BY start_date DESC LIMIT 12", (pid,))]
    lps = qa(c, "SELECT lp.id, lp.url, lp.kind, lp.title, lp.screenshot, COUNT(*) n FROM ads a JOIN landing_pages lp ON lp.id=a.lp_id WHERE a.page_id=? GROUP BY lp.id ORDER BY n DESC LIMIT 12", (pid,))
    c.close()
    return {"page": pg, "brand": b, "stats": st, "timeline": timeline, "angles": angles, "headlines": headlines, "domains": domains, "markets": markets, "ctas": ctas, "top": top, "newest": newest, "lps": lps}


_BRD = {}


def api_brand(p):
    bid = _int(p.get("id"), -1)
    hit = _BRD.get(bid) or _cache_load(f"brand_{bid}")
    if hit and time.time() - hit[0] < (600 if lavoro_in_corso() else 120): return hit[1]
    # scheda gia' vista: si serve subito com'e' e si rinfresca in fondo. Aprire un brand non deve
    # mai far aspettare, nemmeno mentre il giro notturno scrive (Ultimapeak stava a 5,5 s).
    if hit and p.get("fresh") != "1" and _stale_ok(f"brand_{bid}", lambda: api_brand({"id": str(bid), "fresh": "1"})):
        _BRD[bid] = hit; return hit[1]
    c = DB.conn()
    if bid < 0: c.close(); return {"error": "id mancante"}
    b = q1(c, "SELECT * FROM brands WHERE id=?", (bid,))
    if not b: c.close(); return {"error": "brand non trovato"}
    b["stack"] = json.loads(b.get("stack") or "{}"); b["domains"] = json.loads(b.get("domains") or "[]")
    pages = qa(c, "SELECT * FROM pages WHERE brand_id=? ORDER BY n_active DESC, n_ads DESC", (bid,))
    agg = {r["page_id"]: r for r in qa(c, "SELECT page_id, MIN(start_date) first_ad, COALESCE(SUM(est_spend),0) est_spend FROM ads WHERE brand_id=? GROUP BY page_id", (bid,))}
    # una lettura indicizzata per pagina (idx_ads_brand_page_cover): la finestra ROW_NUMBER rileggeva tutto l'archivio del brand
    cov = {}
    for pg in pages:
        r = q1(c, "SELECT ad_archive_id FROM ads WHERE brand_id=? AND page_id=? AND image_url IS NOT NULL ORDER BY score DESC LIMIT 1", (bid, pg["page_id"]))
        if r: cov[pg["page_id"]] = r["ad_archive_id"]
    for pg in pages:
        a = agg.get(pg["page_id"]) or {}
        pg["first_ad"] = a.get("first_ad"); pg["est_spend"] = a.get("est_spend") or 0; pg["cover"] = cov.get(pg["page_id"])
    lps = qa(c, "SELECT id,url,final_url,domain,kind,title,h1,price,currency,screenshot,stack,pixels,word_count,n_reviews,n_ads,first_seen,last_crawl,err FROM landing_pages WHERE brand_id=? ORDER BY n_ads DESC", (bid,))
    for l in lps: l["stack"] = json.loads(l.get("stack") or "[]"); l["pixels"] = json.loads(l.get("pixels") or "[]")
    timeline = qa(c, """SELECT strftime('%Y-%W', start_date) wk, MIN(start_date) d, COUNT(*) n, SUM(fmt='video') v, SUM(is_active) a
                        FROM ads WHERE brand_id=? AND start_date IS NOT NULL GROUP BY wk ORDER BY wk""", (bid,))
    stats = q1(c, """SELECT COUNT(*) n, COALESCE(SUM(is_active),0) active, SUM(fmt='video') video, SUM(fmt='statica') statica, SUM(fmt='native') native,
                     COALESCE(SUM(est_spend),0) est_spend, COALESCE(SUM(CASE WHEN is_active=1 THEN est_spend END),0) active_spend,
                     COALESCE(SUM(eu_total_reach),0) eu_reach, MIN(start_date) first_ad, MAX(start_date) last_ad,
                     SUM(start_date >= date('now','localtime','-7 day')) new7, SUM(start_date >= date('now','localtime','-30 day')) new30,
                     AVG(CASE WHEN is_active=1 THEN julianday('now','localtime')-julianday(start_date) END) avg_age_active FROM ads WHERE brand_id=?""", (bid,))
    countries = {}; markets = {}
    for r in c.execute("""SELECT ad_archive_id, page_id, page_name, is_active, score, reach_by_country, fmt, start_date, end_date
                          FROM ads WHERE brand_id=? AND reach_by_country IS NOT NULL""", (bid,)):
        rc = json.loads(r["reach_by_country"] or "{}")
        for k, v in rc.items():
            countries[k] = countries.get(k, 0) + (v or 0)
            m = markets.setdefault(k, {"cc": k, "reach": 0, "n": 0, "live": 0, "pages": {}, "top": None, "top_score": -1, "video": 0, "native": 0, "statica": 0, "days": 0.0})
            m["reach"] += (v or 0); m["n"] += 1; m["live"] += 1 if r["is_active"] else 0
            m["pages"][r["page_name"] or r["page_id"]] = m["pages"].get(r["page_name"] or r["page_id"], 0) + (v or 0)
            m[r["fmt"] or "statica"] = m.get(r["fmt"] or "statica", 0) + 1
            m["days"] += days_running(dict(r))
            if (r["score"] or 0) > m["top_score"]: m["top_score"] = r["score"] or 0; m["top"] = r["ad_archive_id"]
    for m in markets.values():
        m["pages"] = sorted(m["pages"].items(), key=lambda x: -x[1])[:8]
        m["avg_days"] = round(m["days"] / m["n"], 1) if m["n"] else 0; m.pop("days", None)
    markets = sorted(markets.values(), key=lambda x: -x["reach"])
    langs = qa(c, "SELECT lang, COUNT(*) n, SUM(is_active) live FROM ads WHERE brand_id=? AND lang IS NOT NULL GROUP BY lang ORDER BY n DESC LIMIT 8", (bid,))
    ages = {}; genders = {"male": 0, "female": 0, "unknown": 0}
    for r in c.execute("SELECT reach_by_age, reach_by_gender FROM ads WHERE brand_id=? AND reach_by_age IS NOT NULL", (bid,)):
        for k, v in json.loads(r["reach_by_age"] or "{}").items(): ages[k] = ages.get(k, 0) + (v or 0)
        for k, v in json.loads(r["reach_by_gender"] or "{}").items(): genders[k] = genders.get(k, 0) + (v or 0)
    headlines = qa(c, """SELECT title h, COUNT(*) n, SUM(is_active) a, MAX(score) s, MIN(start_date) f, COUNT(DISTINCT page_id) pg FROM ads
                         WHERE brand_id=? AND title IS NOT NULL AND title!='' AND title NOT LIKE '{{%' GROUP BY title ORDER BY n DESC, s DESC LIMIT 30""", (bid,))
    # hook = titolo se c'e', altrimenti l'attacco del body. Le due meta' separate: la prima sta tutta nell'indice dei titoli,
    # la seconda legge il body solo delle (poche) ad senza titolo. Insieme in una query costavano 0,7 s di letture di riga.
    hooks = [dict(h=r["h"], n=r["n"], a=r["a"], s=r["s"], f=r["f"]) for r in headlines]
    hooks += qa(c, """SELECT substr(body,1,90) h, COUNT(*) n, SUM(is_active) a, MAX(score) s, MIN(start_date) f FROM ads
                      WHERE brand_id=? AND (title IS NULL OR title='') AND body IS NOT NULL GROUP BY h ORDER BY n DESC, s DESC LIMIT 30""", (bid,))
    hooks.sort(key=lambda r: (-(r["n"] or 0), -(r["s"] or 0))); hooks = hooks[:30]
    ctas = qa(c, "SELECT cta, COUNT(*) n FROM ads WHERE brand_id=? AND cta IS NOT NULL GROUP BY cta ORDER BY n DESC LIMIT 8", (bid,))
    domains = qa(c, "SELECT domain, COUNT(*) n, SUM(is_active) a FROM ads WHERE brand_id=? AND domain IS NOT NULL GROUP BY domain ORDER BY n DESC LIMIT 20", (bid,))
    top = [ad_public(a) for a in qa(c, "SELECT * FROM ads WHERE brand_id=? ORDER BY eu_total_reach DESC, score DESC LIMIT 24", (bid,))]
    newest = [ad_public(a) for a in qa(c, "SELECT * FROM ads WHERE brand_id=? ORDER BY start_date DESC LIMIT 24", (bid,))]
    events = qa(c, "SELECT * FROM events WHERE brand_id=? ORDER BY id DESC LIMIT 60", (bid,))
    try:
        import creative as C
        angles_l = C.angles(c, bid)
    except Exception:
        angles_l = []
    # mercati per paese, Ad Library letta paese per paese (scripts/paesi.py). 'paesi' e' distinto da 'markets' (reach UE).
    try:
        paesi = qa(c, """SELECT b.cc, b.active, b.day FROM brand_markets b WHERE b.brand_id=?
                         AND b.day=(SELECT MAX(day) FROM brand_markets WHERE brand_id=b.brand_id AND cc=b.cc) ORDER BY b.active DESC, b.cc""", (bid,))
    except sqlite3.OperationalError:
        paesi = []
    neighbors = DB.kv_get(c, f"neighbors:{bid}") or []
    tracked ={r["domain"]: r["id"] for r in c.execute("SELECT id, domain FROM brands")}
    for nb in neighbors: nb["tracked_id"] = tracked.get(nb["domain"])
    facets = {}
    for col in ("awareness", "emotion", "creative_format", "persona", "cta_style", "mechanism"):
        facets[col] = qa(c, f"SELECT {col} k, COUNT(*) n, SUM(is_active) live FROM ads WHERE brand_id=? AND {col} IS NOT NULL GROUP BY {col} ORDER BY n DESC LIMIT 10", (bid,))
    n_analyzed = (q1(c, "SELECT COUNT(*) n FROM ads WHERE brand_id=? AND angle IS NOT NULL", (bid,)) or {}).get("n", 0)
    try: analisi_lp = json.loads(DB.kv_get(c, f"analisi_lp_{bid}") or "null")
    except Exception: analisi_lp = None
    c.close()
    res = {"brand": b, "pages": pages, "lps": lps, "timeline": timeline, "stats": stats, "countries": countries, "markets": markets, "langs": langs, "ages": ages, "genders": genders,
            "hooks": hooks, "headlines": headlines, "ctas": ctas, "domains": domains, "top": top, "newest": newest, "events": events, "running": RUNNING.get(("brand", bid)),
            "angles": angles_l, "neighbors": neighbors, "facets": facets, "n_analyzed": n_analyzed, "analisi_lp": analisi_lp, "paesi": paesi}
    _BRD[bid] = (time.time(), res); _cache_save(f"brand_{bid}", _BRD[bid])
    return res

def api_ad(p):
    aid = p.get("id") or ""; c = DB.conn()
    a = q1(c, "SELECT * FROM ads WHERE ad_archive_id=?", (aid,))
    if not a: c.close(); return {"error": "ad non trovata"}
    a["media"] = json.loads(a.get("media") or "[]"); a.pop("raw", None)
    a["dynamic"] = bool(_re_ph.match(a.get("body") or "") or _re_ph.match(a.get("title") or ""))
    for k in ("body", "title", "link_description"):
        if _re_ph.match(a.get(k) or ""): a[k] = None
    a["saved"] = bool(q1(c, "SELECT 1 x FROM board_items bi JOIN boards b ON b.id=bi.board_id WHERE b.name='Salvate' AND bi.ad_archive_id=?", (aid,)))
    try:
        import score as _S
        pa = q1(c, "SELECT n_active FROM pages WHERE page_id=?", (a.get("page_id"),)) or {}
        a["score_parts"] = _S.score_parts(a, pa.get("n_active") or 1)
    except Exception: a["score_parts"] = {}
    if not a.get("eu_total_reach"):
        # fuori UE Meta non dichiara nulla: come proxy onesto, la reach EU della STESSA creatività (stessa collation o stesso hash) nel brand
        pr = q1(c, """SELECT MAX(eu_total_reach) r, COUNT(*) n FROM ads WHERE eu_total_reach>0 AND ad_archive_id!=? AND
                      brand_id=? AND ((collation_id IS NOT NULL AND collation_id=?) OR (phash IS NOT NULL AND phash=?))""",
                (aid, a.get("brand_id"), a.get("collation_id"), a.get("phash")))
        if pr and pr.get("r"): a["reach_proxy"] = pr["r"]; a["reach_proxy_n"] = pr["n"]
    for k in ("reach_by_country", "reach_by_age", "reach_by_gender", "location_audience"):
        try: a[k] = json.loads(a[k]) if a.get(k) else None
        except Exception: pass
    a["days"] = days_running(a)
    # la stessa creatività in altri mercati: AdSpy (like reali, spesso USA) <-> Meta (reach UE/UK/BR)
    try:
        if a.get("gemelle"):
            ids = json.loads(a["gemelle"])
            r = q1(c, f"SELECT COUNT(*) n, SUM(eu_total_reach) reach, MIN(start_date) da, MAX(is_active) attiva, GROUP_CONCAT(DISTINCT mercato) merc FROM ads WHERE ad_archive_id IN ({','.join('?'*len(ids))})", ids)
            a["gemella_meta"] = dict(r or {}, ids=ids[:20])
        elif a.get("famiglia"):
            a["gemella_spy"] = q1(c, "SELECT ad_archive_id, reactions, comments, shares, countries, post_url, reactions_n FROM ads WHERE ad_archive_id=?", (a["famiglia"],))
    except Exception: pass
    a["lp"] = q1(c, "SELECT * FROM landing_pages WHERE id=?", (a["lp_id"],)) if a.get("lp_id") else None
    if a["lp"]:
        a["lp"]["stack"] = json.loads(a["lp"].get("stack") or "[]"); a["lp"]["text"] = (a["lp"].get("text") or "")[:3000]
        fu = (a["lp"].get("final_url") or "").split(); a["lp"]["final_url"] = fu[0] if fu else None
    a["page"] = q1(c, "SELECT * FROM pages WHERE page_id=?", (a["page_id"],))
    a["brand"] = q1(c, "SELECT id,name,domain FROM brands WHERE id=?", (a["brand_id"],)) if a.get("brand_id") else None
    sib = []
    if a.get("collation_id"):
        sib = qa(c, "SELECT * FROM ads WHERE collation_id=? AND ad_archive_id!=? ORDER BY start_date", (a["collation_id"], aid))
    if a.get("phash"):
        seen = {x["ad_archive_id"] for x in sib} | {aid}
        sib += [x for x in qa(c, "SELECT * FROM ads WHERE phash=? AND brand_id=? ORDER BY start_date LIMIT 60", (a["phash"], a.get("brand_id"))) if x["ad_archive_id"] not in seen]
    same_copy = qa(c, "SELECT * FROM ads WHERE brand_id=? AND ad_archive_id!=? AND ((title IS NOT NULL AND title=?) OR (length(body)>40 AND substr(body,1,120)=?)) ORDER BY start_date LIMIT 40",
                   (a.get("brand_id"), aid, a.get("title"), (a.get("body") or "")[:120]))
    a["siblings"] = [ad_public(s) for s in sib]
    a["same_copy"] = [ad_public(s) for s in same_copy]
    a["daily"] = qa(c, "SELECT * FROM ad_daily WHERE ad_archive_id=? ORDER BY d", (aid,))
    a["same_lp"] = [ad_public(s) for s in qa(c, "SELECT * FROM ads WHERE lp_id=? AND ad_archive_id!=? ORDER BY eu_total_reach DESC, score DESC LIMIT 24", (a.get("lp_id"), aid))] if a.get("lp_id") else []
    c.close()
    return a


def api_search(p):
    q = (p.get("q") or "").strip(); c = DB.conn()
    out = {"q": q, "ads": [], "pages": [], "lps": [], "brands": []}
    if not q: c.close(); return out
    fq = fts_query(q)
    ids = [DB.fts_id(c, r[0]) for r in c.execute("SELECT rowid FROM ads_fts WHERE ads_fts MATCH ? LIMIT 400", (fq,))]
    if ids:
        out["ads"] = [ad_public(a) for a in qa(c, "SELECT * FROM ads WHERE ad_archive_id IN (%s) ORDER BY score DESC LIMIT 200" % ",".join("?" * len(ids)), ids)]
    like = f"%{q}%"
    out["pages"] = qa(c, "SELECT p.*, b.name brand FROM pages p LEFT JOIN brands b ON b.id=p.brand_id WHERE p.name LIKE ? OR p.page_id=? ORDER BY n_ads DESC LIMIT 30", (like, q))
    lp_ids = [r["lp_id"] for r in c.execute("SELECT lp_id FROM lp_fts WHERE lp_fts MATCH ? LIMIT 100", (fq,))]
    if lp_ids:
        out["lps"] = qa(c, "SELECT id,url,domain,kind,title,price,screenshot,n_ads,brand_id FROM landing_pages WHERE id IN (%s) ORDER BY n_ads DESC" % ",".join("?" * len(lp_ids)), lp_ids)
    out["lps"] += qa(c, "SELECT id,url,domain,kind,title,price,screenshot,n_ads,brand_id FROM landing_pages WHERE url LIKE ? AND id NOT IN (%s) LIMIT 30" % (",".join("?" * len(lp_ids)) or "0"), [like] + lp_ids)
    out["brands"] = qa(c, "SELECT id,name,domain FROM brands WHERE name LIKE ? OR domain LIKE ?", (like, like))
    out["domains"] = qa(c, "SELECT domain, COUNT(*) n, COUNT(DISTINCT page_id) pages, SUM(is_active) a FROM ads WHERE domain LIKE ? GROUP BY domain ORDER BY n DESC LIMIT 20", (like,))
    c.close()
    return out


def api_saved(p):
    c = DB.conn()
    rows = qa(c, """SELECT a.*, bi.note AS saved_note, bi.added AS saved_at FROM board_items bi JOIN boards b ON b.id=bi.board_id JOIN ads a ON a.ad_archive_id=bi.ad_archive_id
                    WHERE b.name=? ORDER BY a.is_active DESC, COALESCE(a.eu_total_reach,0) DESC, bi.added DESC LIMIT 500""", (p.get("board") or "Salvate",))
    brands = {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM brands")}
    out = []
    for a in rows:
        o = ad_public(a); o["saved_note"] = a.get("saved_note"); o["saved_at"] = a.get("saved_at"); o["brand_name"] = brands.get(a.get("brand_id")); out.append(o)
    boards = [r[0] for r in c.execute("SELECT b.name FROM boards b WHERE EXISTS (SELECT 1 FROM board_items i WHERE i.board_id=b.id) ORDER BY b.name='Salvate' DESC, b.name")]
    c.close(); return {"ads": out, "n": len(out), "boards": boards}


def api_lps(p):
    c = DB.conn(); w = "WHERE 1=1"; pa = []
    if p.get("brand"): w += " AND brand_id=?"; pa.append(_int(p["brand"]))
    if p.get("kind"): w += " AND kind=?"; pa.append(p["kind"])
    rows = qa(c, f"SELECT id,url,final_url,domain,brand_id,kind,title,h1,price,currency,screenshot,stack,pixels,word_count,n_reviews,n_ads,first_seen,last_crawl,err FROM landing_pages {w} ORDER BY n_ads DESC LIMIT 400", pa)
    for l in rows: l["stack"] = json.loads(l.get("stack") or "[]")
    kinds = qa(c, f"SELECT kind, COUNT(*) n FROM landing_pages {w} GROUP BY kind", pa)
    c.close()
    return {"lps": rows, "kinds": kinds}


def api_lp(p):
    c = DB.conn(); l = q1(c, "SELECT * FROM landing_pages WHERE id=?", (_int(p.get("id"), -1),))
    if l:
        l["stack"] = json.loads(l.get("stack") or "[]"); l["pixels"] = json.loads(l.get("pixels") or "[]")
        l["ads"] = [ad_public(a) for a in qa(c, "SELECT * FROM ads WHERE lp_id=? ORDER BY eu_total_reach DESC, score DESC LIMIT 60", (l["id"],))]
    c.close(); return l or {"error": "landing non trovata"}


_ANA = {"t": 0, "v": _cache_load("analytics")}


def api_analytics(p):
    """Vista trasversale: come si comportano i brand tracciati, uno accanto all'altro."""
    # i dati cambiano una volta a notte: 30 minuti di cache, e comunque scaldata all'avvio
    if _ANA["v"] and time.time() - _ANA["t"] < 1800 and p.get("fresh") != "1": return _ANA["v"]
    if _ANA["v"] and _stale_ok("analytics", lambda: api_analytics({"fresh": "1"})) and p.get("fresh") != "1": return _ANA["v"]
    c = DB.conn()
    brands = qa(c, "SELECT id, name, domain, status FROM brands ORDER BY name")
    out = []; matrix = {}
    MK = {}   # reach per paese di ogni brand: una sola lettura dell'archivio invece di una per brand
    for r in c.execute("SELECT brand_id, reach_by_country FROM ads WHERE brand_id IS NOT NULL AND reach_by_country IS NOT NULL"):
        d = MK.setdefault(r["brand_id"], {})
        for k, v in json.loads(r["reach_by_country"] or "{}").items(): d[k] = d.get(k, 0) + (v or 0)
    for b in brands:
        bid = b["id"]
        wk = qa(c, """SELECT strftime('%Y-%W', start_date) wk, MIN(start_date) d, COUNT(*) n, SUM(fmt='video') v FROM ads
                      WHERE brand_id=? AND start_date >= date('now','localtime','-84 day') GROUP BY wk ORDER BY wk""", (bid,))
        st = q1(c, """SELECT COUNT(*) n, SUM(is_active) live, SUM(fmt='video') video, SUM(fmt='statica') statica, SUM(fmt='native') native,
                      AVG(CASE WHEN is_active=0 AND end_date IS NOT NULL THEN julianday(end_date)-julianday(start_date)+1 END) avg_life_dead,
                      AVG(CASE WHEN is_active=1 THEN julianday('now','localtime')-julianday(start_date)+1 END) avg_age_live,
                      SUM(CASE WHEN is_active=1 AND julianday('now','localtime')-julianday(start_date) >= 30 THEN 1 ELSE 0 END) live_30,
                      SUM(start_date >= date('now','localtime','-7 day')) new7, SUM(start_date >= date('now','localtime','-30 day')) new30,
                      SUM(CASE WHEN is_active=1 THEN est_spend END) live_spend, COUNT(DISTINCT page_id) pages,
                      AVG(collation_count) avg_variants, SUM(eu_total_reach) eu_reach FROM ads WHERE brand_id=?""", (bid,))
        kinds = qa(c, "SELECT lp.kind, COUNT(*) n FROM ads a JOIN landing_pages lp ON lp.id=a.lp_id WHERE a.brand_id=? GROUP BY lp.kind ORDER BY n DESC", (bid,))
        life = qa(c, """SELECT CASE WHEN d<4 THEN '1-3' WHEN d<8 THEN '4-7' WHEN d<15 THEN '8-14' WHEN d<31 THEN '15-30' WHEN d<61 THEN '31-60' ELSE '60+' END bucket, COUNT(*) n
                        FROM (SELECT julianday(CASE WHEN is_active=1 THEN date('now','localtime') ELSE COALESCE(end_date,date('now','localtime')) END)-julianday(start_date)+1 d FROM ads WHERE brand_id=? AND start_date IS NOT NULL) GROUP BY bucket""", (bid,))
        top_angles = qa(c, "SELECT angle, COUNT(*) n, SUM(is_active) live FROM ads WHERE brand_id=? AND angle IS NOT NULL GROUP BY angle ORDER BY live DESC, n DESC LIMIT 5", (bid,))
        mk = MK.get(bid, {})
        markets = sorted(mk.items(), key=lambda x: -x[1])[:6]
        for k, v in mk.items(): matrix.setdefault(k, {})[b["name"]] = v
        top = q1(c, "SELECT ad_archive_id, score FROM ads WHERE brand_id=? AND is_active=1 ORDER BY score DESC LIMIT 1", (bid,))
        med = q1(c, "SELECT AVG(score) s FROM (SELECT score FROM ads WHERE brand_id=? AND is_active=1 ORDER BY score DESC LIMIT 20)", (bid,))
        out.append({**b, "weeks": wk, "stats": st, "kinds": kinds, "life": life, "angles": top_angles, "markets": markets, "top_ad": top, "top20_score": round((med or {}).get("s") or 0, 1)})
    tot = q1(c, """SELECT COUNT(*) n, SUM(is_active) live, SUM(fmt='video') video, SUM(fmt='statica') statica, SUM(fmt='native') native,
                   SUM(start_date >= date('now','localtime','-7 day')) new7, SUM(eu_total_reach) eu_reach, COUNT(DISTINCT page_id) pages
                   FROM ads WHERE brand_id IS NOT NULL""")
    # a parte: kpi_source non sta nell'indice di copertura e dentro la stessa query costava 5 s di scansione
    tot["kpi_real"] = q1(c, "SELECT COUNT(*) n FROM ads WHERE kpi_source='feed' AND brand_id IS NOT NULL")["n"]
    countries = sorted(matrix.items(), key=lambda kv: -sum(kv[1].values()))[:12]
    c.close()
    res = {"brands": out, "total": tot, "matrix": [{"cc": k, "by": v, "reach": sum(v.values())} for k, v in countries]}
    _ANA["t"] = time.time(); _ANA["v"] = res; _cache_save("analytics", res)
    return res


def api_movimenti(p):
    """Cosa sta prendendo budget adesso: le ad con piu' reach NUOVA al giorno.
    Niente stime: e' la differenza fra due letture vere della reach dichiarata da Meta."""
    bid = _int(p.get("brand"), -1); lim = min(_int(p.get("limit"), 24), 100)
    stato = p.get("stato") or ""
    k = f"mov_{bid}_{lim}_{stato}"
    hit = _STATC.get(k)
    if hit and time.time() - hit[0] < 300: return hit[1]
    c = DB.conn()
    w = ["t.al_giorno > 0"]; pa = []
    if bid > 0: w.append("t.brand_id=?"); pa.append(bid)
    if stato: w.append("t.stato=?"); pa.append(stato)
    rows = qa(c, f"""SELECT t.*, a.page_name, a.title, a.body, a.fmt, a.is_active, a.start_date,
                     a.link_url, a.domain, a.collation_count, b.name brand
                     FROM traiettorie t JOIN ads a ON a.ad_archive_id=t.ad_archive_id
                     JOIN brands b ON b.id=t.brand_id
                     WHERE {' AND '.join(w)} ORDER BY t.al_giorno DESC LIMIT ?""", pa + [lim])
    from datetime import date as _d
    oggi = _d.today()
    for r in rows:
        r["body"] = (r.get("body") or "")[:400]
        try: r["days"] = (oggi - _d.fromisoformat(r["start_date"])).days + 1   # la card lo mostra: senza usciva "0 g"
        except Exception: r["days"] = 0
    per_brand = qa(c, f"""SELECT b.name, t.brand_id, COUNT(*) n, SUM(t.nuova) nuova,
                          ROUND(SUM(t.al_giorno)) al_giorno, SUM(t.stato='scala') scala
                          FROM traiettorie t JOIN brands b ON b.id=t.brand_id
                          WHERE t.al_giorno > 0 GROUP BY t.brand_id ORDER BY al_giorno DESC LIMIT 20""")
    quando = q1(c, "SELECT MAX(calcolata) d, COUNT(*) n FROM traiettorie") or {}
    c.close()
    res = {"ads": rows, "brands": per_brand, "aggiornato": quando.get("d"), "totale": quando.get("n")}
    _STATC[k] = (time.time(), res)
    return res


def api_market(p):
    path = os.path.join(ROOT, "data", "MARKET.md")
    try: md = open(path, encoding="utf-8").read()
    except Exception: md = ""
    c = DB.conn(); meta = DB.kv_get(c, "market_md") or {}; c.close()
    return {"md": md, "meta": meta}


def api_digest(p):
    try:
        md = open(os.path.join(ROOT, "data", "DIGEST.md"), encoding="utf-8").read()
    except Exception:
        import digest; md = digest.build(_int(p.get("days"), 1))
    if p.get("rebuild"):
        import digest; md = digest.build(_int(p.get("days"), 1))
    return {"md": md}


def api_feedcap(body):
    """Reazioni viste nel feed (estensione feedcap di Chry, Chrome loggato). Le ad servite nel
    feed mostrano like/commenti/condivisioni: si agganciano alle ad in archivio per permalink
    o per pagina + inizio del copy. È l'unica fonte pubblica di 'reazioni' per le dark ads."""
    import hashlib
    items = body.get("items") or []
    c = DB.conn()
    c.execute("""CREATE TABLE IF NOT EXISTS sightings(sid TEXT PRIMARY KEY, first_ts TEXT, last_ts TEXT, platform TEXT, page_id TEXT, page_name TEXT,
                 post_url TEXT, text TEXT, likes INTEGER, comments INTEGER, shares INTEGER, n INTEGER DEFAULT 1, ad_archive_id TEXT)""")
    c.commit()
    matched = 0; matched_ids = set()
    for it in items:
        purl = it.get("post_url") or None
        if purl:   # tieni story_fbid/id (identità del dark post), butta i parametri di tracking
            import urllib.parse as _up
            u = _up.urlsplit(purl); q = [(k, v) for k, v in _up.parse_qsl(u.query) if k in ("story_fbid", "id", "v", "fbid")]
            purl = _up.urlunsplit((u.scheme, u.netloc, u.path, _up.urlencode(q), "")) or None
        txt = (it.get("text") or "").strip()
        key = purl or hashlib.sha1(((it.get("page_name") or "") + txt[:120]).encode()).hexdigest()
        aid = None
        if purl:
            r = q1(c, "SELECT ad_archive_id FROM ads WHERE post_url=? OR post_url=? LIMIT 1", (purl, purl.rstrip("/")))
            aid = r["ad_archive_id"] if r else None
        if not aid and txt:
            pref = txt[:90].replace("\n", " ")
            pa = []
            w = "substr(replace(body, char(10), ' '),1,90)=?"; pa.append(pref)
            if it.get("page_id"): w += " AND page_id=?"; pa.append(str(it["page_id"]))
            elif it.get("page_name"):
                # nome pagina FB, oppure username Instagram (pages.ig_username) → page_id
                pg = q1(c, "SELECT page_id FROM pages WHERE name=? OR ig_username=? OR lower(ig_username)=lower(?)", (it["page_name"], it["page_name"], it["page_name"].lstrip("@")))
                if not pg:   # handle IG ≈ nome pagina FB senza spazi/punteggiatura (sandrakeller_rn ~ "Sandra Keller, RN")
                    import re as _re
                    norm = lambda x: _re.sub(r"[^a-z0-9]", "", (x or "").lower())
                    want = norm(it["page_name"])
                    if len(want) >= 5:
                        for r0 in c.execute("SELECT page_id, name, ig_username FROM pages"):
                            if norm(r0["name"]) == want or norm(r0["ig_username"]) == want: pg = {"page_id": r0["page_id"]}; break
                if pg: w += " AND page_id=?"; pa.append(pg["page_id"])
                else: w += " AND page_name=?"; pa.append(it["page_name"])
            r = q1(c, f"SELECT ad_archive_id FROM ads WHERE {w} ORDER BY is_active DESC, start_date DESC LIMIT 1", pa)
            if not r:   # stessa creatività su un'altra pagina alias: basta il copy
                r = q1(c, "SELECT ad_archive_id FROM ads WHERE substr(replace(body, char(10), ' '),1,90)=? AND brand_id IS NOT NULL ORDER BY is_active DESC, start_date DESC LIMIT 1", (pref,))
            aid = r["ad_archive_id"] if r else None
        if aid:
            matched_ids.add(aid)
            c.execute("""UPDATE ads SET reactions=MAX(COALESCE(reactions,0), COALESCE(?,0)), comments=MAX(COALESCE(comments,0), COALESCE(?,0)),
                         shares=MAX(COALESCE(shares,0), COALESCE(?,0)), kpi_checked=?, kpi_source='feed', post_url=COALESCE(post_url,?) WHERE ad_archive_id=?""",
                      (it.get("likes"), it.get("comments"), it.get("shares"), DB.today(), purl, aid))
            matched += 1
        row = q1(c, "SELECT sid FROM sightings WHERE sid=?", (key,))
        if row:
            c.execute("UPDATE sightings SET last_ts=?, likes=COALESCE(?,likes), comments=COALESCE(?,comments), shares=COALESCE(?,shares), n=n+1, ad_archive_id=COALESCE(?,ad_archive_id) WHERE sid=?",
                      (DB.now(), it.get("likes"), it.get("comments"), it.get("shares"), aid, key))
        else:
            c.execute("INSERT INTO sightings(sid,first_ts,last_ts,platform,page_id,page_name,post_url,text,likes,comments,shares,ad_archive_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (key, DB.now(), DB.now(), it.get("platform"), str(it.get("page_id") or ""), it.get("page_name"), purl, txt[:1500], it.get("likes"), it.get("comments"), it.get("shares"), aid))
    c.commit()
    if matched:
        import score as S
        for it_aid in matched_ids:
            a = dict(c.execute("SELECT ad_archive_id, page_id, start_date, end_date, is_active, collation_count, eu_total_reach, reactions, comments, shares, format, fmt, n_pages_same FROM ads WHERE ad_archive_id=?", (it_aid,)).fetchone())
            sc = S.score_ad(a); est, basis = S.estimate(a)
            c.execute("UPDATE ads SET score=?, est_spend=?, est_spend_basis=? WHERE ad_archive_id=?", (sc, round(est, 2), basis, it_aid))
        c.commit()
    c.close()
    return {"ok": 1, "n": len(items), "matched": matched}


def api_events(p):
    c = DB.conn(); days = _int(p.get("days"), 7)
    rows = qa(c, "SELECT e.*, b.name brand FROM events e LEFT JOIN brands b ON b.id=e.brand_id WHERE substr(e.ts,1,10) >= date('now','localtime',?) ORDER BY e.id DESC LIMIT 400", (f"-{days} day",))
    c.close(); return {"events": rows}


def api_jobs(p):
    c = DB.conn(); rows = qa(c, "SELECT * FROM jobs ORDER BY id DESC LIMIT 40"); c.close()
    return {"jobs": rows, "running": {f"{k[0]}:{k[1]}": v for k, v in list(RUNNING.items())}}


# ---------------- jobs (thread in background) ----------------
def run_job(kind, arg):
    import brand as B
    c = DB.conn()
    c.execute("INSERT INTO jobs(kind,arg,status,created) VALUES(?,?,?,?)", (kind, arg, "running", DB.now()))
    jid = c.execute("SELECT last_insert_rowid() i").fetchone()["i"]; c.commit(); c.close()
    lines = []
    def log(msg):
        lines.append(str(msg)); print(f"[job {jid}] {msg}", flush=True)
        try:
            cc = DB.conn(); cc.execute("UPDATE jobs SET progress=?, log=? WHERE id=?", (str(msg)[:200], "\n".join(lines[-80:]), jid)); cc.commit(); cc.close()
        except Exception: pass
    key = None
    try:
        if kind == "add_brand":
            bid = B.add_brand(arg, log=log); key = ("brand", bid); RUNNING[key] = "discover"
            B.discover(bid, log=log); RUNNING[key] = "pull"; B.pull_pages(bid, log=log)
            RUNNING[key] = "enrich"; B.enrich(bid, log=log); RUNNING[key] = "landings"; B.landings(bid, log=log)
            RUNNING[key] = "score"; B.score(bid, log=log)
            cc = DB.conn(); cc.execute("UPDATE brands SET status='ready', last_scan=? WHERE id=?", (DB.now(), bid)); cc.commit(); cc.close()
        elif kind == "refresh":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "refresh"; B.refresh(bid, log=log)
        elif kind == "enrich":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "enrich"; B.enrich(bid, limit=2000, log=log); B.score(bid, log=log)
        elif kind == "landings":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "landings"; B.landings(bid, limit=400, log=log)
        elif kind == "pull":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "pull"; B.pull_pages(bid, log=log, full=True); B.score(bid, log=log)
        elif kind == "live_search":
            import live; live.run(arg, log=log)
        elif kind == "transcribe":
            import transcribe; transcribe.run(arg, log=log)
        elif kind == "transcribe_brand":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "transcribe"
            import transcribe; transcribe.run(f"brand:{bid}", limit=25, log=log)
        elif kind == "thumbs":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "thumbs"; B.thumbs(bid, log=log); B.score(bid, log=log)
        elif kind == "creative":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "creative"; B.creative(bid, limit=200, log=log); B.score(bid, log=log)
        elif kind == "market":
            import market; key = ("market", 0); RUNNING[key] = "market"; market.run(log=log)
        elif kind == "brief":
            import brief; brief.run(str(arg), log=log)
        elif kind == "study":
            bid = int(arg); key = ("brand", bid); RUNNING[key] = "study"
            import study; study.run(bid, log=log)
        elif kind == "refresh_all":
            cc = DB.conn(); ids = [r["id"] for r in cc.execute("SELECT id FROM brands")]; cc.close()
            for bid in ids:
                key = ("brand", bid); RUNNING[key] = "refresh"
                try: B.refresh(bid, log=log)
                except Exception as ex: log(f"refresh {bid} errore: {ex}")
                RUNNING.pop(key, None)
        status = "done"
    except Exception as ex:
        log("ERRORE " + str(ex)); log(traceback.format_exc()[-1500:]); status = "error"
    finally:
        if key: RUNNING.pop(key, None)
    c = DB.conn(); c.execute("UPDATE jobs SET status=?, finished=?, log=? WHERE id=?", (status, DB.now(), "\n".join(lines[-120:]), jid)); c.commit(); c.close()


def start_job(kind, arg):
    c = DB.conn(); dup = q1(c, "SELECT id FROM jobs WHERE status='running' AND kind=? AND COALESCE(arg,'')=?", (kind, str(arg or ""))); c.close()
    if dup: return {"ok": 0, "error": f"{kind} {arg} già in corso (job {dup['id']})"}
    t = threading.Thread(target=run_job, args=(kind, arg), daemon=True); t.start()
    return {"ok": 1, "kind": kind, "arg": arg}


# ---------------- media ----------------
def avatar(page_id):
    """Foto profilo della pagina, cache su disco (gli URL fbcdn scadono)."""
    if not (page_id or "").isdigit(): return None
    path = os.path.join(THUMBS, f"pg{page_id}.jpg")
    found = P.find("thumbs", f"pg{page_id}.jpg")
    if found: return found
    c = DB.conn(); r = q1(c, "SELECT pic FROM pages WHERE page_id=?", (page_id,)); c.close()
    if not r or not r.get("pic"): return None
    try:
        req = urllib.request.Request(r["pic"], headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.facebook.com/"})
        data = urllib.request.urlopen(req, timeout=15).read()
        if len(data) < 200: return None
        open(path, "wb").write(data)
        return path
    except Exception:
        return None


def api_saved_ids(p):
    c = DB.conn()
    ids = [r["ad_archive_id"] for r in qa(c, "SELECT bi.ad_archive_id FROM board_items bi JOIN boards b ON b.id=bi.board_id WHERE b.name='Salvate'")]
    c.close(); return {"ids": ids}


_THUMB_NEG = {}   # ad_archive_id -> ultimo tentativo fallito
_THUMB_INLINE = False          # True solo dentro il lavoratore di fondo
_THUMB_Q = []; _THUMB_QSET = set(); _THUMB_LOCK = threading.Lock()

def _thumb_enqueue(aid):
    with _THUMB_LOCK:
        if aid in _THUMB_QSET or len(_THUMB_Q) > 2000: return
        _THUMB_Q.append(aid); _THUMB_QSET.add(aid)

def _thumb_worker():
    """Un solo download alla volta, con una pausa: le miniature arrivano al caricamento successivo."""
    global _THUMB_INLINE
    while True:
        with _THUMB_LOCK:
            aid = _THUMB_Q.pop(0) if _THUMB_Q else None
            if aid: _THUMB_QSET.discard(aid)
        if not aid: time.sleep(1.0); continue
        try:
            _THUMB_INLINE = True; thumb(aid)
        except Exception: pass
        finally: _THUMB_INLINE = False
        time.sleep(0.4 if not lavoro_in_corso() else 1.5)

threading.Thread(target=_thumb_worker, daemon=True).start()

def thumb(aid):
    """Miniatura cache su disco. Gli URL fbcdn scadono: se il download fallisce si prova
    a rinfrescare l'URL leggendo la pagina dell'ad in Ad Library."""
    path = os.path.join(THUMBS, f"{aid}.jpg")
    found = P.find("thumbs", f"{aid}.jpg")
    if found: return found
    # memoria dei fallimenti: un URL scaduto non si riprova a ogni caricamento di pagina
    # (prima: fino a 3 URL x 20 s + una richiesta a Meta, e la richiesta restava appesa oltre i 2 minuti)
    now = time.time(); last = _THUMB_NEG.get(aid)
    if last and now - last < 3600: return None
    # La richiesta HTTP non aspetta mai la rete: si risponde subito col segnaposto e il download
    # va in una coda a un solo lavoratore. Con 6 connessioni per host il browser restava bloccato
    # dietro alle miniature scadute e la home "non caricava".
    if not _THUMB_INLINE:
        _thumb_enqueue(aid); return None
    c = DB.conn(); a = q1(c, "SELECT image_url, page_id, media FROM ads WHERE ad_archive_id=?", (aid,)); c.close()
    if not a: return None
    urls = [a.get("image_url")] + [m.get("thumb") or m.get("url") for m in json.loads(a.get("media") or "[]")]
    for u in [x for x in urls if x][:2]:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.facebook.com/"})
            data = urllib.request.urlopen(req, timeout=6).read()
            if len(data) > 200:
                open(path + ".tmp", "wb").write(data)
                if not P.shrink(path + ".tmp", path):
                    try: os.remove(path + ".tmp")
                    except Exception: pass
                    continue   # mai la piena risoluzione sul disco
                else:
                    try: os.remove(path + ".tmp")
                    except Exception: pass
                return path
        except Exception:
            continue
    # URL scaduto: NON si va a rileggere la Ad Library dentro una richiesta HTTP. Con il limitatore
    # di Meta occupato da un job la risposta restava appesa per minuti; l'URL nuovo lo porta il passo
    # notturno delle miniature. Qui si risponde subito col segnaposto.
    _THUMB_NEG[aid] = now
    return None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        o = self.headers.get("Origin") or ""
        if o and self._origin_ok(o): self.send_header("Access-Control-Allow-Origin", o); self.send_header("Vary", "Origin")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)

    def _origin_ok(self, o):
        return (not o) or o in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}") or o.startswith("chrome-extension://")

    def do_OPTIONS(self):
        o = self.headers.get("Origin") or ""
        self.send_response(204)
        if o and self._origin_ok(o):
            self.send_header("Access-Control-Allow-Origin", o); self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode())

    def _file(self, path, ctype, cache=False):
        try:
            data = open(path, "rb").read()
        except Exception:
            return self._send(404, b"not found", "text/plain")
        self._send(200, data, ctype, {"Cache-Control": "public, max-age=604800"} if cache else {"Cache-Control": "no-store"})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); p = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"): return self._file(os.path.join(PUBLIC, "index.html"), "text/html; charset=utf-8")
            if u.path.startswith("/public/"):
                ext = u.path.rsplit(".", 1)[-1]; ct = {"js": "application/javascript", "css": "text/css", "svg": "image/svg+xml", "png": "image/png", "woff2": "font/woff2"}.get(ext, "application/octet-stream")
                return self._file(os.path.join(PUBLIC, os.path.basename(u.path)), ct)
            if u.path == "/media/thumb":
                path = thumb(p.get("id", ""))
                if not path:
                    # URL fbcdn scaduto e niente cache: un fondo neutro invece di un 404 a ogni caricamento
                    # (la home ne produceva 91 nel registro della console per una sola ad)
                    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">'
                           '<rect width="320" height="320" fill="#0d1218"/>'
                           '<path d="M104 200l44-56 32 40 20-24 36 40z" fill="#1f2731"/>'
                           '<circle cx="118" cy="118" r="16" fill="#1f2731"/></svg>')
                    return self._send(200, svg.encode(), "image/svg+xml")
                return self._file(path, "image/jpeg", cache=True)
            if u.path == "/media/avatar":
                path = avatar(p.get("page", ""))
                if not path:
                    # pagina senza foto (tipico di quelle scoperte da AdSpy): iniziale su fondo neutro,
                    # meglio di un'icona rotta e di un 404 nel registro
                    c2 = DB.conn(); r2 = q1(c2, "SELECT name FROM pages WHERE page_id=?", (p.get("page", ""),)); c2.close()
                    ini = ((r2 or {}).get("name") or "?").strip()[:1].upper()
                    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
                           f'<rect width="64" height="64" rx="32" fill="#2a3038"/>'
                           f'<text x="32" y="41" font-family="system-ui,sans-serif" font-size="26" fill="#8d97a5" '
                           f'text-anchor="middle">{ini}</text></svg>')
                    return self._send(200, svg.encode(), "image/svg+xml")
                return self._file(path, "image/jpeg", cache=True)
            if u.path.startswith("/media/lp/"):
                f = P.find("lp", os.path.basename(u.path))
                if not f:
                    # screenshot potato dal tetto del disco: un segnaposto, non un 404 per ogni landing
                    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="240" viewBox="0 0 360 240">'
                           '<rect width="360" height="240" fill="#0d1218"/><rect x="24" y="28" width="312" height="14" rx="3" fill="#1f2731"/>'
                           '<rect x="24" y="56" width="220" height="10" rx="3" fill="#1a212a"/><rect x="24" y="76" width="260" height="10" rx="3" fill="#1a212a"/>'
                           '<rect x="24" y="110" width="312" height="96" rx="6" fill="#141a22"/></svg>')
                    return self._send(200, svg.encode(), "image/svg+xml")
                return self._file(f, "image/jpeg", cache=True)
            if u.path == "/media/video":
                c = DB.conn(); a = q1(c, "SELECT video_url FROM ads WHERE ad_archive_id=?", (p.get("id"),)); c.close()
                if not a or not a.get("video_url"): return self._send(404, b"no video", "text/plain")
                req = urllib.request.Request(a["video_url"], headers={"User-Agent": "Mozilla/5.0", "Range": self.headers.get("Range") or "bytes=0-"})
                try:
                    r = urllib.request.urlopen(req, timeout=30)
                except (urllib.error.URLError, OSError):
                    return self._send(410, b"video non disponibile", "text/plain")
                self.send_response(r.status)
                for k in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                    if r.headers.get(k): self.send_header(k, r.headers[k])
                self.end_headers()
                try:
                    while True:
                        chunk = r.read(65536)
                        if not chunk: break
                        self.wfile.write(chunk)
                except Exception:
                    pass
                return
            api = {"/api/board": api_board, "/api/brands": api_brands, "/api/brand": api_brand, "/api/ad": api_ad, "/api/search": api_search,
                   "/api/lps": api_lps, "/api/saved": api_saved, "/api/saved_ids": api_saved_ids, "/api/market": api_market, "/api/page": api_page, "/api/lp": api_lp, "/api/events": api_events, "/api/jobs": api_jobs, "/api/analytics": api_analytics, "/api/digest": api_digest, "/api/movimenti": api_movimenti}
            if u.path == "/api/board.csv":
                d = api_board({**p, "limit": "600"}); import csv, io
                buf = io.StringIO(); wr = csv.writer(buf)
                cols = ["ad_archive_id", "page_name", "domain", "format", "start_date", "end_date", "is_active", "days", "collation_count", "n_pages_same", "eu_total_reach", "score", "est_spend", "est_spend_basis", "winner", "angle", "emotion", "creative_format", "hook", "title", "cta", "link_url", "body"]
                wr.writerow(cols)
                for a in d["ads"]: wr.writerow([(a.get(k) if a.get(k) is not None else "") for k in cols])
                return self._send(200, buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", {"Content-Disposition": "attachment; filename=ecom-radar-board.csv"})
            if u.path.startswith("/media/frames/"):
                return self._file(P.find("frames", os.path.basename(u.path)) or "", "image/jpeg", cache=True)
            if u.path in api: return self._json(api[u.path](p))
            if u.path == "/api/health": return self._json({"ok": 1, "db": DB.DBPATH, "running": len(RUNNING)})
            self._send(404, b"not found", "text/plain")
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:
            traceback.print_exc(); self._json({"error": str(ex)}, 500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/chrome_in":
            # Lettura dell'Ad Library dal Chrome dell'utente (quando Meta blocca il browser headless):
            # la pagina raccoglie le ad scorrendo e le deposita qui; scripts/chrome_ingest.py le salva.
            o = self.headers.get("Origin") or ""
            if o and o != "https://www.facebook.com": return self._send(403, b"forbidden", "text/plain")
            n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n)
            d = os.path.join(os.path.dirname(DB.DBPATH), "chrome_in"); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{int(time.time()*1000)}.json"), "wb").write(raw)
            return self._send(200, b"ok", "text/plain", {"Access-Control-Allow-Origin": "https://www.facebook.com"})
        if not self._origin_ok(self.headers.get("Origin") or ""):
            return self._send(403, b"forbidden", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            try: body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError: return self._json({"error": "JSON non valido"}, 400)
            if not isinstance(body, dict): return self._json({"error": "il corpo deve essere un oggetto JSON"}, 400)
            if u.path == "/api/jobs":
                return self._json(start_job(body.get("kind"), body.get("arg")))
            if u.path == "/api/feedcap":
                return self._json(api_feedcap(body))
            if u.path == "/api/board_item":
                c = DB.conn()
                c.execute("INSERT OR IGNORE INTO boards(name,created) VALUES(?,?)", (body.get("board", "Swipe"), DB.now()))
                bid = c.execute("SELECT id FROM boards WHERE name=?", (body.get("board", "Swipe"),)).fetchone()["id"]
                if body.get("remove"): c.execute("DELETE FROM board_items WHERE board_id=? AND ad_archive_id=?", (bid, body["id"]))
                else: c.execute("INSERT OR REPLACE INTO board_items(board_id,ad_archive_id,note,added) VALUES(?,?,?,?)", (bid, body["id"], body.get("note"), DB.now()))
                c.commit(); c.close(); return self._json({"ok": 1})
            if u.path == "/api/ad_note":
                c = DB.conn(); c.execute("UPDATE ads SET tags=?, hook=COALESCE(?,hook), angle=COALESCE(?,angle) WHERE ad_archive_id=?", (body.get("tags"), body.get("hook"), body.get("angle"), body["id"])); c.commit(); c.close()
                return self._json({"ok": 1})
            if u.path == "/api/brand_note":
                c = DB.conn(); c.execute("UPDATE brands SET notes=?, niche=COALESCE(?,niche) WHERE id=?", (body.get("notes"), body.get("niche"), int(body["id"]))); c.commit(); c.close()
                return self._json({"ok": 1})
            self._send(404, b"", "text/plain")
        except Exception as ex:
            traceback.print_exc(); self._json({"error": str(ex)}, 500)


def main():
    DB.init()

    def ripulisci_job():
        """Segna come persi i job morti col processo. E' una SCRITTURA: se un lavoro notturno tiene
        il database, aspettava fino a 5 minuti PRIMA di aprire la porta e la piattaforma risultava
        irraggiungibile. Ora si fa in fondo, con poca attesa, e se non riesce pazienza."""
        try:
            c = DB.conn(); c.execute("PRAGMA busy_timeout=4000")
            c.execute("UPDATE jobs SET status='lost', finished=? WHERE status='running'", (DB.now(),)); c.commit(); c.close()
        except Exception as e:
            print(f"ripulitura job rimandata: {e}", flush=True)
    threading.Thread(target=ripulisci_job, daemon=True).start()
    def warm():
        """Scalda tutto quello che la home e le viste principali chiedono, prima che le apra qualcuno,
        e lo tiene caldo: cosi' anche mentre un lavoro notturno scrive sul database la UI resta pronta."""
        SCALDA = [
            (api_analytics, {}), (api_brands, {}),
            (api_board, {"days": "10000", "limit": "1", "facets": "0"}),                                   # testata della home
            (api_board, {"days": "30", "status": "active", "sort": "score", "min_days": "3", "limit": "48", "facets": "0"}),
            (api_board, {"days": "30", "limit": "120"}),                                                    # Esplora
        ]
        for f in ("video", "statica", "native"):
            SCALDA.append((api_board, {"days": "30", "status": "active", "sort": "score", "min_days": "3", "limit": "48", "format": f, "facets": "0"}))
        try:
            cw = DB.conn()
            for r in cw.execute("SELECT id FROM brands ORDER BY (SELECT COUNT(*) FROM ads WHERE brand_id=brands.id) DESC"):
                SCALDA.append((api_brand, {"id": str(r[0])}))     # le schede brand, dalla piu' grande
            cw.close()
        except Exception: pass
        # le schede brand (29 letture da 0,2 s) si scaldano all'avvio e poi ogni 30 minuti: rifarle ogni
        # 2 minuti teneva il database e la CPU sempre occupati per niente. Le viste della home ogni 2 minuti.
        giro = 0
        while True:
            for fn, arg in SCALDA:
                if fn is api_brand and giro % 15: continue
                try: fn(dict(arg))
                except Exception: pass
                time.sleep(0.3)          # a passo lento: non deve rubare il database ai lavori in corso
            giro += 1
            time.sleep(120)
    threading.Thread(target=warm, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H); srv.daemon_threads = True
    # "localhost" in Chrome risolve prima a ::1: senza un ascolto IPv6 ogni fetch della home partiva
    # con un rifiuto e poi ripiegava su 127.0.0.1 — a volte troppo tardi, e la pagina restava vuota.
    # Secondo ascolto su ::1 (solo loopback, come il primo).
    import socket
    class H6(ThreadingHTTPServer): address_family = socket.AF_INET6
    try:
        srv6 = H6(("::1", PORT), H); srv6.daemon_threads = True
        threading.Thread(target=srv6.serve_forever, daemon=True).start()
    except OSError as e:
        print(f"ascolto IPv6 non disponibile: {e}", flush=True)
    print(f"Ecom Radar · http://localhost:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
