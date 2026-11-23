#!/usr/bin/env python3
"""Ecom Radar — punteggio winner e spesa stimata. Onesto: ogni numero dice da cosa deriva.

Segnali disponibili SENZA login (tutti pubblici):
  days       giorni di attività (start_date → end_date/oggi)             = Meta lo tiene acceso perché rende
  variants   collation_count (varianti della stessa creatività)           = il brand ci mette budget/test
  eu_reach   reach EU dichiarata da Meta (solo ad consegnate in EU)       = volume reale
  reactions  reazioni del post (quando l'ad è un post boostato o vista in feed)
  siblings   quante pagine del brand girano la stessa creatività
  page_scale ad attive della pagina (advertiser grande)

Spesa stimata (est_spend, USD):
  se eu_reach:   reach × freq 1.8 / 1000 × CPM 12 $        (basis 'eu_reach')
  altrimenti se reactions: reactions × 19.6 $             (basis 'reactions', rapporto della board di Paganelli: 2.28 B$ / 116.5 M reazioni)
  altrimenti:    days × variants × 25 $/g  (tetto 30 g)   (basis 'runtime')  ← proxy debole, mostrato tratteggiato
"""
import json, math, os, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

CPM = 12.0; FREQ = 1.8; USD_PER_REACTION = 19.6; USD_PER_DAY_VARIANT = 25.0


def days_running(a, today=None):
    today = today or date.today()
    if not a.get("start_date"): return 0
    try:
        s = date.fromisoformat(a["start_date"])
        e = date.fromisoformat(a["end_date"]) if (a.get("end_date") and not a.get("is_active")) else today
        return max(1, (e - s).days + 1)
    except Exception:
        return 0


def _reazioni(a):
    """Le reazioni possono essere un numero (vecchio formato) o l'oggetto salvato da AdSpy/Facebook.
    Si prende il conteggio più alto e più fresco: quello che Facebook mostra oggi batte la fotografia di AdSpy."""
    r = a.get("reactions")
    if isinstance(r, (int, float)): return int(r or 0)
    if isinstance(r, str) and r.strip().startswith("{"):
        try:
            d = json.loads(r)
            return int(max(d.get("likes") or 0, d.get("fb_reazioni") or 0))
        except Exception: return 0
    try: return int(r or 0)
    except (TypeError, ValueError): return 0


def estimate(a):
    d = days_running(a)
    v = max(1, a.get("collation_count") or 1)
    if a.get("eu_total_reach"):
        return a["eu_total_reach"] * FREQ / 1000.0 * CPM, "eu_reach"
    r = _reazioni(a)
    if r:
        return r * USD_PER_REACTION, "reactions"
    return min(d, 30) * v * USD_PER_DAY_VARIANT, "runtime"


def score_ad(a, page_active=1, today=None):
    """Intensità 0-100. Segnali pubblici (Ad Library) + KPI reali quando ci sono (feed).
    Longevità 0-40 · varianti 0-16 · reach EU 0-25 (+ reach/giorno 0-8) · reazioni/commenti/condivisioni reali 0-25
    · attiva ora +8 (+4 se attiva da ≥30 g: Glenn "viva da 30+ giorni") · stessa creatività su più pagine 0-10 · advertiser grande 0-5.
    Le ad spente da più di 90 giorni perdono il 15%: contano per la storia, non per "adesso"."""
    d = days_running(a, today)
    v = max(1, a.get("collation_count") or 1)
    s = 0.0
    s += min(40, 8 * math.log1p(d))                                   # 7g≈17, 30g≈27, 90g≈36
    s += min(16, 5 * math.log1p(v - 1))                               # iterazioni della stessa creatività
    reach = a.get("eu_total_reach") or 0
    if reach:
        s += min(25, 4 * math.log10(reach + 1))                        # 100k ≈ 20
        s += min(8, 3 * math.log10(reach / max(1, d) + 1))            # reach al giorno: 1k/g ≈ 9 → cap 8
    eng = _reazioni(a) + 2 * (a.get("comments") or 0) + 3 * (a.get("shares") or 0)
    if eng:
        # engagement MISURATO: è la prova migliore che abbiamo, e va pesata come tale.
        # Col vecchio tetto a 25 un'ad da 98.000 like valeva quanto una da 22.000: il logaritmo
        # schiacciava tutto. Ora la scala si apre fra 1.000 e 1.000.000 di punti di engagement.
        s += max(0.0, min(45.0, 45.0 * (math.log10(eng + 1) - 3.0) / 3.0))
    if a.get("is_active"):
        s += 8
        if d >= 30: s += 4
    if (a.get("fmt") or a.get("format")) == "video": s += 2
    if (a.get("n_pages_same") or 1) > 1: s += min(10, 4 * math.log1p((a.get("n_pages_same") or 1) - 1))
    s += min(5, math.log1p(page_active))
    if not a.get("is_active") and a.get("end_date"):
        try:
            from datetime import date as _dt
            if (( today or _dt.today()) - _dt.fromisoformat(a["end_date"])).days > 90: s *= 0.85
        except Exception: pass
    return round(min(100.0, s), 1)


def score_brand(bid=None):
    c = DB.conn()
    w = "WHERE brand_id=?" if bid else ""
    pa = {r["page_id"]: r["n_active"] for r in c.execute("SELECT page_id, n_active FROM pages")}
    try: c.execute("ALTER TABLE ads ADD COLUMN n_pages_same INTEGER")
    except Exception: pass
    c.commit()
    rows = [dict(r) for r in c.execute(f"SELECT ad_archive_id, page_id, start_date, end_date, is_active, collation_count, eu_total_reach, reactions, comments, shares, format, fmt, n_pages_same, score, est_spend, est_spend_basis FROM ads {w}", (bid,) if bid else ())]
    changed = 0
    for a in rows:
        sc = score_ad(a, pa.get(a["page_id"], 1)); est, basis = estimate(a); est = round(est, 2)
        if a.get("score") == sc and a.get("est_spend") == est and a.get("est_spend_basis") == basis: continue   # riga invariata: non riscriverla
        c.execute("UPDATE ads SET score=?, est_spend=?, est_spend_basis=? WHERE ad_archive_id=?", (sc, est, basis, a["ad_archive_id"]))
        changed += 1
        if changed % 200 == 0: c.commit()      # lotti brevi: mai un lock lungo
    # winner = top 10% per brand o soglia assoluta, oppure 1000+ reazioni reali (regola di Chry: sopra i mille like è forte)
    if bid:
        c.execute("CREATE TEMP TABLE IF NOT EXISTS _win(ad_archive_id TEXT PRIMARY KEY)"); c.execute("DELETE FROM _win")
        c.execute("""INSERT OR IGNORE INTO _win SELECT ad_archive_id FROM ads WHERE brand_id=? AND (score >= 54 OR COALESCE(reactions_n,0) >= 1000 OR ad_archive_id IN (
                     SELECT ad_archive_id FROM ads WHERE brand_id=? AND score IS NOT NULL ORDER BY score DESC LIMIT MAX(3, (SELECT COUNT(*)/10 FROM ads WHERE brand_id=?))))""", (bid, bid, bid))
        c.execute("UPDATE ads SET winner=0 WHERE brand_id=? AND winner=1 AND ad_archive_id NOT IN (SELECT ad_archive_id FROM _win)", (bid,))
        c.execute("UPDATE ads SET winner=1 WHERE brand_id=? AND COALESCE(winner,0)=0 AND ad_archive_id IN (SELECT ad_archive_id FROM _win)", (bid,))
    c.commit(); c.close()
    return len(rows)


if __name__ == "__main__":
    print(score_brand(int(sys.argv[1]) if len(sys.argv) > 1 else None))


def score_parts(a, page_active=1, today=None):
    """Scomposizione dell'intensità (stessa formula di score_ad) per spiegare il numero all'utente."""
    d = days_running(a, today); v = max(1, a.get("collation_count") or 1)
    P = {"longevità": min(40, 8 * math.log1p(d)), "iterazioni": min(16, 5 * math.log1p(v - 1))}
    reach = a.get("eu_total_reach") or 0
    if reach: P["reach EU"] = min(25, 4 * math.log10(reach + 1)) + min(8, 3 * math.log10(reach / max(1, d) + 1))
    eng = _reazioni(a) + 2 * (a.get("comments") or 0) + 3 * (a.get("shares") or 0)
    if eng: P["KPI reali"] = min(25, 5 * math.log10(eng + 1))
    if a.get("is_active"): P["attiva ora"] = 8 + (4 if d >= 30 else 0)
    if (a.get("fmt") or a.get("format")) == "video": P["video"] = 2
    if (a.get("n_pages_same") or 1) > 1: P["più pagine"] = min(10, 4 * math.log1p((a.get("n_pages_same") or 1) - 1))
    P["advertiser"] = min(5, math.log1p(page_active))
    return {k: round(v, 1) for k, v in P.items() if v}
