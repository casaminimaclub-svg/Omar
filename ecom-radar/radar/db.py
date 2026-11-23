#!/usr/bin/env python3
"""Ecom Radar — archivio SQLite. Tutto ciò che il radar vede resta per sempre
(Meta cancella le ad non attive dopo ~12 mesi, noi no). FTS5 su copy, titoli,
transcript, testo delle landing e nomi pagina: la ricerca "tutto" parte da qui.
"""
import json, os, sqlite3, time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBPATH = os.path.join(ROOT, "data", "radar.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS brands(
  id INTEGER PRIMARY KEY, name TEXT UNIQUE, url TEXT, domain TEXT, domains TEXT,
  niche TEXT, notes TEXT, added TEXT, last_scan TEXT, status TEXT DEFAULT 'new',
  stack TEXT, keywords TEXT, countries TEXT);
CREATE TABLE IF NOT EXISTS pages(
  page_id TEXT PRIMARY KEY, name TEXT, brand_id INTEGER, role TEXT,
  likes INTEGER, category TEXT, profile_uri TEXT, pic TEXT, ig_username TEXT, ig_followers INTEGER,
  verification TEXT, entity_type TEXT, first_seen TEXT, last_seen TEXT,
  n_ads INTEGER DEFAULT 0, n_active INTEGER DEFAULT 0, last_full_pull TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS ads(
  ad_archive_id TEXT PRIMARY KEY, brand_id INTEGER, page_id TEXT, page_name TEXT,
  collation_id TEXT, collation_count INTEGER,
  start_date TEXT, end_date TEXT, is_active INTEGER, total_active_time INTEGER,
  first_seen TEXT, last_seen TEXT,
  format TEXT, display_format TEXT, n_cards INTEGER,
  video_url TEXT, image_url TEXT, media TEXT, thumb TEXT,
  body TEXT, title TEXT, link_description TEXT, caption TEXT, cta TEXT, cta_type TEXT,
  link_url TEXT, domain TEXT, lp_id INTEGER,
  platforms TEXT, countries TEXT, country_iso TEXT, lang TEXT,
  is_aaa_eligible INTEGER, eu_total_reach INTEGER, reach_by_country TEXT, reach_by_age TEXT, reach_by_gender TEXT,
  gender_audience TEXT, age_min INTEGER, age_max INTEGER, location_audience TEXT, payer TEXT, beneficiary TEXT,
  details_checked TEXT, impressions_text TEXT, spend_text TEXT, reach_estimate TEXT,
  post_url TEXT, reactions INTEGER, comments INTEGER, shares INTEGER, kpi_checked TEXT, kpi_source TEXT,
  transcript TEXT, ocr TEXT, hook TEXT, angle TEXT, persona TEXT, analysis TEXT,
  score REAL, est_spend REAL, est_spend_basis TEXT, winner INTEGER DEFAULT 0,
  tags TEXT, source TEXT, raw TEXT);
CREATE INDEX IF NOT EXISTS ix_ads_brand ON ads(brand_id);
CREATE INDEX IF NOT EXISTS ix_ads_page ON ads(page_id);
CREATE INDEX IF NOT EXISTS ix_ads_active ON ads(is_active);
CREATE INDEX IF NOT EXISTS ix_ads_start ON ads(start_date);
CREATE INDEX IF NOT EXISTS ix_ads_domain ON ads(domain);
CREATE INDEX IF NOT EXISTS ix_ads_score ON ads(score);
CREATE INDEX IF NOT EXISTS ix_ads_coll ON ads(collation_id);
CREATE INDEX IF NOT EXISTS idx_ads_brand_reach ON ads(brand_id, eu_total_reach DESC, score DESC);
CREATE INDEX IF NOT EXISTS idx_ads_brand_stats ON ads(brand_id, start_date, is_active, end_date, fmt, est_spend, eu_total_reach, reactions, winner, page_id);
CREATE INDEX IF NOT EXISTS idx_ads_reach_order ON ads(eu_total_reach DESC, score DESC, start_date DESC);
CREATE INDEX IF NOT EXISTS idx_ads_noreach ON ads(eu_total_reach, lib_rank, score, start_date, end_date, is_active, brand_id, fmt, ad_archive_id);
CREATE INDEX IF NOT EXISTS idx_fac2_angle ON ads(angle, brand_id, start_date, end_date, is_active, eu_total_reach, fmt, lib_rank, winner, page_id) WHERE angle IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac2_emotion ON ads(emotion, brand_id, start_date, end_date, is_active, eu_total_reach, fmt, lib_rank, winner, page_id) WHERE emotion IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac2_cformat ON ads(creative_format, brand_id, start_date, end_date, is_active, eu_total_reach, fmt, lib_rank, winner, page_id) WHERE creative_format IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ads_id_stats ON ads(ad_archive_id, brand_id, start_date, end_date, is_active, fmt, est_spend, eu_total_reach, reactions, winner, page_id, score, lib_rank);
CREATE INDEX IF NOT EXISTS idx_ads_lite ON ads(brand_id, start_date, end_date, is_active, fmt, eu_total_reach, score, est_spend, reactions, reactions_n, winner, page_id, lib_rank, angle, emotion, creative_format, awareness, lang, mercato, collation_count, lp_id, noprev, ad_archive_id);
CREATE INDEX IF NOT EXISTS idx_ads_brand_agg ON ads(brand_id, is_active, start_date, est_spend, fmt, eu_total_reach, end_date, collation_count, page_id);
CREATE INDEX IF NOT EXISTS idx_ads_kpi ON ads(kpi_source) WHERE kpi_source IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ads_brand_lang ON ads(brand_id, lang, is_active);
CREATE INDEX IF NOT EXISTS idx_ads_brand_lp ON ads(brand_id, lp_id);
CREATE INDEX IF NOT EXISTS idx_ads_brand_domain2 ON ads(brand_id, domain, is_active);
CREATE INDEX IF NOT EXISTS idx_fac_angle ON ads(angle, start_date, is_active, end_date, fmt) WHERE angle IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac_emotion ON ads(emotion, start_date, is_active, end_date, fmt) WHERE emotion IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac_creative_format ON ads(creative_format, start_date, is_active, end_date, fmt) WHERE creative_format IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac_mechanism ON ads(mechanism, start_date, is_active, end_date, fmt) WHERE mechanism IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac_awareness ON ads(awareness, start_date, is_active, end_date, fmt) WHERE awareness IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac_persona ON ads(persona, start_date, is_active, end_date, fmt) WHERE persona IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fac_cta_style ON ads(cta_style, start_date, is_active, end_date, fmt) WHERE cta_style IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ads_brand_score_all ON ads(brand_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_ads_brand_rbc ON ads(brand_id, reach_by_country) WHERE reach_by_country IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ads_brand_rba ON ads(brand_id, reach_by_age, reach_by_gender) WHERE reach_by_age IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ads_brand_title ON ads(brand_id, title, is_active, score, start_date, page_id);
CREATE TABLE IF NOT EXISTS ad_daily(
  d TEXT, ad_archive_id TEXT, is_active INTEGER, eu_total_reach INTEGER, reactions INTEGER,
  PRIMARY KEY(d, ad_archive_id));
CREATE TABLE IF NOT EXISTS landing_pages(
  id INTEGER PRIMARY KEY, url TEXT UNIQUE, final_url TEXT, domain TEXT, brand_id INTEGER,
  kind TEXT, title TEXT, h1 TEXT, price TEXT, currency TEXT, offer TEXT, text TEXT,
  screenshot TEXT, stack TEXT, pixels TEXT, word_count INTEGER, n_reviews TEXT,
  status INTEGER, first_seen TEXT, last_seen TEXT, last_crawl TEXT, n_ads INTEGER DEFAULT 0, err TEXT, meta TEXT);
CREATE INDEX IF NOT EXISTS ix_lp_brand ON landing_pages(brand_id);
CREATE INDEX IF NOT EXISTS ix_lp_domain ON landing_pages(domain);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, brand_id INTEGER, ref TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_ev ON events(kind, ts);
CREATE TABLE IF NOT EXISTS searches(
  id INTEGER PRIMARY KEY, q TEXT, kind TEXT, country TEXT, created TEXT, last_run TEXT,
  total INTEGER, n_pages INTEGER, notes TEXT, monitor INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS search_hits(search_id INTEGER, ad_archive_id TEXT, PRIMARY KEY(search_id, ad_archive_id));
CREATE TABLE IF NOT EXISTS boards(id INTEGER PRIMARY KEY, name TEXT UNIQUE, created TEXT);
CREATE TABLE IF NOT EXISTS board_items(board_id INTEGER, ad_archive_id TEXT, note TEXT, added TEXT, PRIMARY KEY(board_id, ad_archive_id));
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, kind TEXT, arg TEXT, status TEXT, created TEXT, started TEXT, finished TEXT, progress TEXT, log TEXT);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
"""

FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS ads_fts USING fts5(
  ad_archive_id UNINDEXED, page_name, body, title, link_description, transcript, ocr, domain, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS fts_map(rowid INTEGER PRIMARY KEY, aid TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS lp_fts USING fts5(
  lp_id UNINDEXED, url, title, h1, text, tokenize='unicode61 remove_diacritics 2');
"""


def conn():
    os.makedirs(os.path.dirname(DBPATH), exist_ok=True)
    c = sqlite3.connect(DBPATH, timeout=300)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL"); c.execute("PRAGMA busy_timeout=300000")
    # senza questi il registro delle scritture cresce senza fine (era arrivato a 553 MB)
    # e ogni lettura deve scorrerselo tutto: disco pieno e piattaforma lenta.
    c.execute("PRAGMA journal_size_limit=67108864")   # 64 MB e poi si tronca
    c.execute("PRAGMA wal_autocheckpoint=400")        # compatta piu' spesso
    _trace_long_txn(c)
    return c


TXNLOG = os.path.join(os.path.dirname(DBPATH), "dblock.log")


def _trace_long_txn(c, limit_s=10):
    """Scrive in data/dblock.log lo stack di ogni transazione tenuta aperta più di limit_s secondi:
    è il modo per trovare chi blocca gli altri scrittori (WAL: un solo scrittore alla volta)."""
    if os.environ.get("RADAR_TXN_TRACE", "1") == "0": return
    import time as _t, traceback as _tb, threading as _th
    st = {"t": None, "stack": None, "first": None, "slow": ("", 0.0), "last": None}
    def trace(sql):
        s = sql.lstrip()[:6].upper(); tnow = _t.time()
        if st["last"] is not None:                      # durata dello statement precedente (approssimata: fino all'inizio del successivo)
            d = tnow - st["last"][1]
            if d > st["slow"][1]: st["slow"] = (st["last"][0], d)
        st["last"] = (sql[:220], tnow)
        if s.startswith("BEGIN"):
            st["t"] = tnow; st["stack"] = "".join(_tb.format_stack(limit=14)[:-1]); st["first"] = None; st["slow"] = ("", 0.0)
        elif st["t"] and st["first"] is None:
            st["first"] = sql[:220]
        if s.startswith("COMMIT") or s.startswith("ROLLBA"):
            if st["t"] and tnow - st["t"] > limit_s:
                try:
                    with open(TXNLOG, "a") as f:
                        f.write(f"{now()} transazione di {tnow-st['t']:.0f}s in {_th.current_thread().name}\n  primo statement: {st['first']}\n  statement più lento ({st['slow'][1]:.1f}s): {st['slow'][0]}\n{st['stack']}\n")
                except Exception: pass
            st["t"] = None
    c.set_trace_callback(trace)


# Colonne aggiunte nel tempo con ALTER TABLE (nei vari moduli o a mano nel database originale):
# su un database nuovo vanno create PRIMA degli indici che le usano.
EXTRA_COLS = {
    "ads": {"fmt": "TEXT", "lib_rank": "INTEGER", "reactions_n": "INTEGER", "mercato": "TEXT", "noprev": "INTEGER",
            "emotion": "TEXT", "creative_format": "TEXT", "awareness": "TEXT", "mechanism": "TEXT", "cta_style": "TEXT",
            "analyzed": "TEXT", "n_pages_same": "INTEGER", "phash": "TEXT", "ocr_done": "INTEGER", "storyboard": "TEXT",
            "brief": "TEXT", "market_voice": "TEXT", "gemelle": "TEXT", "famiglia": "TEXT",
            "vetrina": "INTEGER", "page_rank": "INTEGER"},
    "pages": {"declared": "INTEGER"},
    "brands": {"area": "TEXT", "pinned": "INTEGER DEFAULT 0"},
}


# Tabelle derivate che nel database originale esistevano già (create a mano o da script non inclusi).
# ad_reach_cc = reach per paese in righe, tenuta allineata a ads.reach_by_country da due trigger.
DERIVED = """
CREATE TABLE IF NOT EXISTS ad_reach_cc(ad_archive_id TEXT, cc TEXT, reach INTEGER, PRIMARY KEY(ad_archive_id, cc));
CREATE INDEX IF NOT EXISTS idx_reach_cc ON ad_reach_cc(cc, reach DESC);
CREATE TRIGGER IF NOT EXISTS trg_reach_cc_upd AFTER UPDATE OF reach_by_country ON ads BEGIN
  DELETE FROM ad_reach_cc WHERE ad_archive_id = NEW.ad_archive_id;
  INSERT OR REPLACE INTO ad_reach_cc(ad_archive_id, cc, reach)
    SELECT NEW.ad_archive_id, j.key, j.value FROM json_each(CASE WHEN json_valid(NEW.reach_by_country) THEN NEW.reach_by_country ELSE '{}' END) j
    WHERE j.key IS NOT NULL AND j.value > 0;
END;
CREATE TRIGGER IF NOT EXISTS trg_reach_cc_del AFTER DELETE ON ads BEGIN
  DELETE FROM ad_reach_cc WHERE ad_archive_id = OLD.ad_archive_id;
END;
CREATE TABLE IF NOT EXISTS traiettorie(
  ad_archive_id TEXT PRIMARY KEY, brand_id INTEGER, d0 TEXT, d1 TEXT, giorni REAL,
  reach0 INTEGER, reach1 INTEGER, nuova INTEGER, al_giorno REAL, letture INTEGER,
  stato TEXT, calcolata TEXT);
CREATE INDEX IF NOT EXISTS idx_tra_brand ON traiettorie(brand_id, al_giorno DESC);
CREATE INDEX IF NOT EXISTS idx_tra_giorno ON traiettorie(al_giorno DESC);
CREATE TABLE IF NOT EXISTS brand_markets(brand_id INT, cc TEXT, day TEXT, active INT, letti INT, PRIMARY KEY(brand_id, cc, day));
CREATE TABLE IF NOT EXISTS ad_markets(ad_archive_id TEXT, cc TEXT, rank INT, seen TEXT, PRIMARY KEY(ad_archive_id, cc));
CREATE INDEX IF NOT EXISTS idx_admk_cc ON ad_markets(cc, rank);
"""


def _ensure_cols(c):
    for t, cols in EXTRA_COLS.items():
        have = {r[1] for r in c.execute(f"PRAGMA table_info({t})")}
        for col, typ in cols.items():
            if col not in have:
                c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")


def init():
    c = conn()
    tables = ";\n".join(x for x in SCHEMA.split(";\n") if not x.strip().startswith("CREATE INDEX"))
    c.executescript(tables)
    _ensure_cols(c)
    c.executescript(SCHEMA)
    c.executescript(DERIVED)
    try:
        c.executescript(FTS)
    except sqlite3.OperationalError:
        pass
    c.commit(); c.close()


def today():
    return date.today().isoformat()


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log_event(c, kind, brand_id=None, ref=None, detail=None):
    c.execute("INSERT INTO events(ts,kind,brand_id,ref,detail) VALUES(?,?,?,?,?)", (now(), kind, brand_id, ref, detail))


AD_COLS = ["collation_id", "collation_count", "start_date", "end_date", "is_active", "total_active_time",
           "format", "display_format", "n_cards", "video_url", "image_url", "body", "title", "link_description",
           "caption", "cta", "cta_type", "link_url", "domain", "platforms", "countries", "country_iso",
           "is_aaa_eligible", "impressions_text", "spend_text", "reach_estimate", "post_url"]


def upsert_ad(c, ad, brand_id=None, source=None):
    """Inserisce o aggiorna. Ritorna 'new' | 'updated' | 'reactivated'."""
    aid = ad["ad_archive_id"]
    row = c.execute("SELECT is_active, brand_id, page_id FROM ads WHERE ad_archive_id=?", (aid,)).fetchone()
    media = json.dumps(ad.get("media") or [])
    t = today()
    if row:
        import formats as _F
        sets = ", ".join(f"{k}=COALESCE(?,{k})" for k in AD_COLS) + ", fmt=COALESCE(fmt, ?)"
        vals = [ad.get(k) for k in AD_COLS] + [_F.classify(ad) if (ad.get("body") or ad.get("video_url") or ad.get("media")) else None]
        # is_active e end_date devono aggiornarsi sempre (anche a 0/None -> tenere ultimo valore noto)
        c.execute(f"""UPDATE ads SET {sets}, is_active=?, media=?, last_seen=?, page_name=COALESCE(?,page_name),
                      brand_id=COALESCE(brand_id,?), source=COALESCE(source,?) WHERE ad_archive_id=?""",
                  vals + [ad.get("is_active"), media, t, ad.get("page_name"), brand_id, source, aid])
        refresh_fts(c, aid)
        c.execute("INSERT OR REPLACE INTO ad_daily(d,ad_archive_id,is_active,eu_total_reach,reactions) VALUES(?,?,?,(SELECT eu_total_reach FROM ads WHERE ad_archive_id=?),(SELECT reactions FROM ads WHERE ad_archive_id=?))",
                  (t, aid, ad.get("is_active"), aid, aid))
        if row["is_active"] == 0 and ad.get("is_active"):
            return "reactivated"
        return "updated"
    import formats as _F
    cols = ["ad_archive_id", "brand_id", "page_id", "page_name", "first_seen", "last_seen", "media", "source", "raw", "fmt"] + AD_COLS
    vals = [aid, brand_id, ad.get("page_id"), ad.get("page_name"), t, t, media, source,
            _pack_raw(json.dumps({k: v for k, v in ad.items() if k not in ("media",)}, ensure_ascii=False)), _F.classify(ad)] + [ad.get(k) for k in AD_COLS]
    c.execute(f"INSERT INTO ads({','.join(cols)}) VALUES({','.join('?'*len(cols))})", vals)
    c.execute("INSERT OR REPLACE INTO ad_daily(d,ad_archive_id,is_active) VALUES(?,?,?)", (t, aid, ad.get("is_active")))
    c.execute("DELETE FROM ads_fts WHERE rowid=?", (fts_rowid(aid),))
    _fts_map(c, aid)
    c.execute("INSERT INTO ads_fts(rowid,ad_archive_id,page_name,body,title,link_description,transcript,ocr,domain) VALUES(?,?,?,?,?,?,?,?,?)",
              (fts_rowid(aid), aid, ad.get("page_name"), ad.get("body"), ad.get("title"), ad.get("link_description"), None, None, ad.get("domain")))
    return "new"


def _pack_raw(txt):
    """`raw` si salva compresso: e' la copia integrale della risposta di Meta, nessuna query
    la legge, e in chiaro pesava 1 GB sul database. Si rilegge con raw_json()."""
    import zlib
    try: return zlib.compress(txt.encode("utf-8"), 6)
    except Exception: return txt


def raw_json(v):
    """Rilegge `raw`, compresso o in chiaro (righe scritte prima della compressione)."""
    import zlib
    if v is None: return None
    if isinstance(v, (bytes, bytearray)):
        try: v = zlib.decompress(v).decode("utf-8")
        except Exception: return None
    try: return json.loads(v)
    except Exception: return None


def fts_rowid(aid):
    """rowid dell'indice full-text = id dell'ad (16 cifre, entra in 64 bit): cancellazione O(1)."""
    # indice senza copia dei testi (contentless): l'id si ricava dal rowid; gli id non numerici passano da fts_map
    s = str(aid)
    if s.isdigit() and str(int(s)) == s: return int(s)
    import hashlib
    return int.from_bytes(hashlib.sha1(s.encode()).digest()[:7], "big") + (1 << 60)


def _fts_map(c, aid):
    r = fts_rowid(aid)
    if r >= (1 << 60): c.execute("INSERT OR IGNORE INTO fts_map(rowid, aid) VALUES(?,?)", (r, str(aid)))


def fts_id(c, rowid):
    if rowid < (1 << 60): return str(rowid)
    r = c.execute("SELECT aid FROM fts_map WHERE rowid=?", (rowid,)).fetchone()
    return r[0] if r else None


def rebuild_fts(c, log=print):
    """Ricostruisce ads_fts e lp_fts con rowid = id (una volta sola; vedi kv 'fts_rowid')."""
    import time as _t
    t0 = _t.time()
    c.execute("DELETE FROM ads_fts"); c.commit()
    rows = c.execute("SELECT ad_archive_id,page_name,body,title,link_description,transcript,ocr,domain FROM ads").fetchall()
    for i, r in enumerate(rows, 1):
        _fts_map(c, r["ad_archive_id"])
        c.execute("INSERT INTO ads_fts(rowid,ad_archive_id,page_name,body,title,link_description,transcript,ocr,domain) VALUES(?,?,?,?,?,?,?,?,?)",
                  (fts_rowid(r["ad_archive_id"]), r["ad_archive_id"], r["page_name"], r["body"], r["title"], r["link_description"], r["transcript"], r["ocr"], r["domain"]))
        if i % 500 == 0: c.commit()
    c.commit()
    c.execute("DELETE FROM lp_fts"); c.commit()
    for r in c.execute("SELECT id,url,title,h1,text FROM landing_pages").fetchall():
        c.execute("INSERT INTO lp_fts(rowid,lp_id,url,title,h1,text) VALUES(?,?,?,?,?,?)", (r["id"], r["id"], r["url"], r["title"], r["h1"], (r["text"] or "")[:20000]))
    c.commit()
    kv_set(c, "fts_rowid", 1); c.commit()
    log(f"FTS ricostruito: {len(rows)} ad in {_t.time()-t0:.0f}s")


def refresh_fts(c, aid):
    r = c.execute("SELECT page_name,body,title,link_description,transcript,ocr,domain FROM ads WHERE ad_archive_id=?", (aid,)).fetchone()
    if not r: return
    c.execute("DELETE FROM ads_fts WHERE rowid=?", (fts_rowid(aid),))
    _fts_map(c, aid)
    c.execute("INSERT INTO ads_fts(rowid,ad_archive_id,page_name,body,title,link_description,transcript,ocr,domain) VALUES(?,?,?,?,?,?,?,?,?)",
              (fts_rowid(aid), aid, r["page_name"], r["body"], r["title"], r["link_description"], r["transcript"], r["ocr"], r["domain"]))


def upsert_page(c, ad, brand_id=None, role=None):
    pid = ad.get("page_id")
    if not pid: return
    t = today()
    row = c.execute("SELECT page_id FROM pages WHERE page_id=?", (pid,)).fetchone()
    if row:
        c.execute("""UPDATE pages SET name=COALESCE(?,name), likes=COALESCE(?,likes), category=COALESCE(NULLIF(?,''),category),
                     profile_uri=COALESCE(?,profile_uri), pic=COALESCE(?,pic), last_seen=?, brand_id=COALESCE(brand_id,?),
                     role=COALESCE(role,?) WHERE page_id=?""",
                  (ad.get("page_name"), ad.get("page_likes"), ad.get("page_categories"), ad.get("page_profile_uri"),
                   ad.get("page_pic"), t, brand_id, role, pid))
    else:
        c.execute("""INSERT INTO pages(page_id,name,brand_id,role,likes,category,profile_uri,pic,first_seen,last_seen)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",
                  (pid, ad.get("page_name"), brand_id, role, ad.get("page_likes"), ad.get("page_categories"),
                   ad.get("page_profile_uri"), ad.get("page_pic"), t, t))


def recount_pages(c, brand_id=None):
    w = "WHERE brand_id=?" if brand_id else ""
    for r in c.execute(f"SELECT page_id FROM pages {w}", (brand_id,) if brand_id else ()).fetchall():
        n, a = c.execute("SELECT COUNT(*), COALESCE(SUM(is_active),0) FROM ads WHERE page_id=?", (r["page_id"],)).fetchone()
        c.execute("UPDATE pages SET n_ads=?, n_active=? WHERE page_id=?", (n, a, r["page_id"]))


def kv_get(c, k, default=None):
    r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return json.loads(r["v"]) if r else default


def kv_set(c, k, v):
    c.execute("INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)", (k, json.dumps(v)))


if __name__ == "__main__":
    init(); print("ok", DBPATH)
