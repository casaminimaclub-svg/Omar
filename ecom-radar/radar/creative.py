#!/usr/bin/env python3
"""Ecom Radar — analisi creativa per ad (Claude CLI, sonnet). Il motore che trasforma
l'archivio in intelligence: per ogni ad rilevante estrae hook, FAMIGLIA di angolo,
meccanismo, persona, awareness, leva emotiva, formato creativo e "perché funziona".

Lotti di ~12 ad per chiamata (economico). Le famiglie di angolo vengono normalizzate
sul brand: la stessa etichetta si riusa se già esiste (così i conteggi si sommano).
Stadio di trend (calcolato, non chiesto al modello):
  battle-tested ≥30 g · gaining 14-29 g · new-test <14 g
"""
import json, os, re, subprocess, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

BIN = next((p for p in (os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"), "/opt/homebrew/bin/claude", "/usr/local/bin/claude") if os.path.exists(p)), None)
BATCH = 12

PROMPT = """Sei un creative strategist senior (scuola Luke Iha, Sarah Levinger, Anthony Camacho, Spencer Pawlin). Analizza queste inserzioni Meta del brand {brand} ({domain}). Per OGNI ad rispondi con un oggetto JSON. Rispondi SOLO con un array JSON valido, niente testo prima o dopo.

Famiglie di angolo GIÀ usate per questo brand (riusa ESATTAMENTE la stessa etichetta quando l'ad appartiene a una di queste; crea una nuova etichetta corta in italiano solo se davvero diversa):
{families}

Schema per ogni ad:
{{"id":"<ad_archive_id>",
 "hook":"la frase di apertura effettiva, max 15 parole (dal titolo, dalla prima riga del copy o dal transcript)",
 "angle":"famiglia di angolo, 2-5 parole (es. 'colpevole nascosto: fegato', 'storia della sorella', 'paura diagnosi tardiva', 'us vs them medici')",
 "mechanism":"il meccanismo/colpevole che l'ad dichiara, max 12 parole, o null",
 "persona":"a chi parla (età/genere/situazione), max 8 parole",
 "awareness":"unaware|problem|solution|product|most",
 "emotion":"leva emotiva dominante in 1-2 parole (paura, sollievo, rabbia, curiosità, orgoglio, vergogna, speranza)",
 "creative_format":"UGC selfie|talking head|founder|testimonial|listicle statica|native/screenshot|meme|prodotto|us-vs-them|storia lunga|demo|animazione|altro",
 "cta_style":"soft (learn more/leggi)|hard (compra/sconto)|curiosity (scopri)",
 "why":"perché può funzionare, 1 frase concreta e specifica"}}

INSERZIONI:
{ads}
"""


def _families(c, bid):
    rows = c.execute("SELECT angle, COUNT(*) n FROM ads WHERE brand_id=? AND angle IS NOT NULL GROUP BY angle ORDER BY n DESC LIMIT 40", (bid,)).fetchall()
    return "\n".join(f"- {r['angle']} ({r['n']} ad)" for r in rows) or "- (nessuna ancora)"


def _material(a):
    L = [f"### id {a['ad_archive_id']} · {a['format']} · {'live' if a['is_active'] else 'spenta'} · dal {a['start_date']} · x{a['collation_count']} · pagina {a['page_name']} · CTA {a['cta']}"]
    if a["title"]: L.append(f"TITOLO: {a['title']}")
    if a["body"]: L.append(f"COPY: {a['body'][:900]}")
    if a["transcript"]: L.append(f"TRANSCRIPT: {a['transcript'][:900]}")
    if a["ocr"]: L.append(f"TESTO NELL'IMMAGINE: {a['ocr'][:400]}")
    return "\n".join(L)


def analyze_batch(brand, ads, families):
    prompt = PROMPT.format(brand=brand["name"], domain=brand["domain"], families=families, ads="\n\n".join(_material(a) for a in ads))
    p = subprocess.run([BIN, "-p", prompt, "--model", "claude-haiku-5-5", "--output-format", "text"], capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL, env={**os.environ, "VANGELO": "off"})
    m = re.search(r"\[.*\]", p.stdout or "", re.S)
    if not m:
        err = ((p.stderr or "") + " " + (p.stdout or "")).strip().replace("\n", " ")[:200]
        raise RuntimeError(f"risposta vuota da claude (rc {p.returncode}): {err or 'nessun output'}")
    try:
        return json.loads(m.group(0))
    except Exception:
        # tenta di recuperare oggetti singoli
        out = []
        for mm in re.finditer(r"\{[^{}]*\}", m.group(0), re.S):
            try: out.append(json.loads(mm.group(0)))
            except Exception: pass
        return out


def _write(bid, chunk, res):
    """Scrive i risultati di un lotto con una connessione propria e transazione breve."""
    c = DB.conn(); by_id = {str(r.get("id")): r for r in res if isinstance(r, dict)}; n = 0
    for a in chunk:
        r = by_id.get(str(a["ad_archive_id"]))
        if not r: continue
        vals = (r.get("hook"), (r.get("angle") or "").strip().lower() or None, r.get("mechanism"), r.get("persona"), r.get("awareness"), r.get("emotion"),
                r.get("creative_format"), r.get("cta_style"), r.get("why"), DB.today())
        c.execute("""UPDATE ads SET hook=?, angle=?, mechanism=?, persona=?, awareness=?, emotion=?, creative_format=?, cta_style=?, analysis=?, analyzed=?
                     WHERE ad_archive_id=? OR (collation_id IS NOT NULL AND collation_id=?)""", vals + (a["ad_archive_id"], a.get("collation_id")))
        n += 1
    c.commit(); c.close(); return n


def run(bid, limit=120, only_missing=True, log=print, workers=None):
    if not BIN: log("claude CLI non trovata"); return 0
    import plan
    if not plan.allow_claude(log, "analisi creativa"): return 0
    workers = workers or int(os.environ.get("RADAR_CLAUDE_WORKERS", "1"))   # 1 di default: il Mac non deve scaldare (era 3)
    c = DB.conn()
    for col in ("mechanism", "awareness", "emotion", "creative_format", "cta_style", "analyzed"):
        try: c.execute(f"ALTER TABLE ads ADD COLUMN {col} TEXT")
        except Exception: pass
    c.commit()   # mai tenere una transazione aperta mentre si aspetta Claude
    b = dict(c.execute("SELECT * FROM brands WHERE id=?", (bid,)).fetchone())
    w = "AND (analyzed IS NULL)" if only_missing else ""
    # priorità: live per score, poi le spente più forti; una sola ad per collation (le varianti ereditano)
    rows = [dict(r) for r in c.execute(f"""SELECT * FROM ads WHERE brand_id=? {w}
              AND ad_archive_id IN (SELECT ad_archive_id FROM ads a2 WHERE a2.brand_id=? GROUP BY COALESCE(a2.collation_id, a2.ad_archive_id) HAVING a2.ad_archive_id=MAX(a2.ad_archive_id))
              ORDER BY is_active DESC, score DESC LIMIT ?""", (bid, bid, limit))]
    c.close()
    chunks = [rows[i:i + BATCH] for i in range(0, len(rows), BATCH)]
    log(f"CREATIVE {b['name']}: {len(rows)} ad da analizzare in {len(chunks)} lotti ({workers} in parallelo)")
    done = 0

    empty = {"n": 0}
    def process(chunk):
        if empty["n"] >= 3: return 0          # Claude non risponde: non bruciare altri lotti
        cc = DB.conn(); fam = _families(cc, bid); cc.close()
        try:
            res = analyze_batch(b, chunk, fam)
        except Exception as ex:
            empty["n"] += 1; log(f"  lotto: errore {ex}"); return 0
        n = _write(bid, chunk, res)
        empty["n"] = 0 if n else empty["n"] + 1
        return n

    if chunks:
        done += process(chunks[0])                      # il primo da solo: semina le famiglie di angolo
        log(f"  lotto 1/{len(chunks)}: {done} analizzate (famiglie seminate)")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for i, n in enumerate(ex.map(process, chunks[1:]), start=2):
                done += n; log(f"  lotto {i}/{len(chunks)}: {n} analizzate")
    if done: consolidate(bid, log=log)
    log(f"CREATIVE {b['name']}: {done} ad analizzate")
    return done


CONSOLIDATE_PROMPT = """Queste sono le etichette di "famiglia di angolo" assegnate alle ad del brand {brand}, con il numero di ad per ciascuna. Molte sono sinonimi o varianti della stessa famiglia. Unificale in al massimo {k} famiglie canoniche (etichette corte in italiano, 2-5 parole, riusa le etichette esistenti più frequenti come nomi canonici). Rispondi SOLO con un oggetto JSON {{"etichetta originale": "etichetta canonica", ...}} che copra TUTTE le etichette elencate.

ETICHETTE:
{labels}
"""


def consolidate(bid, k=12, log=print):
    """Unifica le etichette sinonime (i lotti paralleli non si vedono a vicenda)."""
    c = DB.conn()
    rows = c.execute("SELECT angle, COUNT(*) n FROM ads WHERE brand_id=? AND angle IS NOT NULL GROUP BY angle ORDER BY n DESC", (bid,)).fetchall()
    if len(rows) <= 8: c.close(); return 0
    import plan
    if not plan.allow_claude(log, "consolidamento"): c.close(); return 0
    b = dict(c.execute("SELECT name FROM brands WHERE id=?", (bid,)).fetchone())
    labels = "\n".join(f"- {r['angle']} ({r['n']})" for r in rows)
    p = subprocess.run([BIN, "-p", CONSOLIDATE_PROMPT.format(brand=b["name"], k=k, labels=labels), "--model", "claude-haiku-5-5", "--output-format", "text"],
                       capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL, env={**os.environ, "VANGELO": "off"})
    m = re.search(r"\{.*\}", p.stdout or "", re.S)
    if not m: c.close(); return 0
    try: mapping = json.loads(m.group(0))
    except Exception: c.close(); return 0
    n = 0
    for old, new in mapping.items():
        new = (new or "").strip().lower(); old = (old or "").strip().lower()
        if new and old and new != old:
            n += c.execute("UPDATE ads SET angle=? WHERE brand_id=? AND angle=?", (new, bid, old)).rowcount
    c.commit()
    left = c.execute("SELECT COUNT(DISTINCT angle) FROM ads WHERE brand_id=? AND angle IS NOT NULL", (bid,)).fetchone()[0]
    c.close()
    log(f"  famiglie consolidate: {len(rows)} → {left} ({n} ad rietichettate)")
    return n


def angles(c, bid=None):
    """Famiglie di angolo con conteggi, live, durata massima, stadio di trend, esempi."""
    w = "WHERE angle IS NOT NULL" + (" AND brand_id=?" if bid else " AND brand_id IS NOT NULL")
    rows = c.execute(f"""SELECT angle, COUNT(*) n, SUM(is_active) live, MIN(start_date) first, MAX(start_date) last, MAX(score) best,
                         MAX(julianday(CASE WHEN is_active=1 THEN date('now','localtime') ELSE COALESCE(end_date,date('now','localtime')) END)-julianday(start_date)+1) max_days,
                         AVG(julianday(CASE WHEN is_active=1 THEN date('now','localtime') ELSE COALESCE(end_date,date('now','localtime')) END)-julianday(start_date)+1) avg_days,
                         SUM(est_spend) spend, COUNT(DISTINCT page_id) pages, COUNT(DISTINCT brand_id) brands,
                         (SELECT ad_archive_id FROM ads a2 WHERE a2.angle=ads.angle {'AND a2.brand_id=?' if bid else ''} ORDER BY score DESC LIMIT 1) top_id,
                         (SELECT hook FROM ads a2 WHERE a2.angle=ads.angle {'AND a2.brand_id=?' if bid else ''} ORDER BY score DESC LIMIT 1) top_hook
                         FROM ads {w} GROUP BY angle ORDER BY live DESC, n DESC""", ((bid, bid, bid) if bid else ())).fetchall()
    out = []
    for r in rows:
        d = dict(r); md = d.get("max_days") or 0
        d["stage"] = "battle-tested" if md >= 30 else "gaining" if md >= 14 else "new-test"
        out.append(d)
    return out


if __name__ == "__main__":
    run(int(sys.argv[1]), limit=int(sys.argv[2]) if len(sys.argv) > 2 else 120)
