#!/usr/bin/env python3
"""MAPPA DEL MERCATO: tutti i brand tracciati letti insieme dal modello più forte disponibile.
Chi copia chi, quali angoli/hook/formati dominano, quali pagine e mercati, dove c'è spazio.
Output: data/MARKET.md (+ brands.notes non toccati). Uso: python3 radar/market.py"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB, llm

def material():
    c = DB.conn(); L = ["# DATI DI MERCATO · tutti i brand tracciati · " + DB.today()]
    for b in c.execute("SELECT * FROM brands WHERE status='ready' ORDER BY id"):
        bid = b["id"]
        s = dict(c.execute("""SELECT COUNT(*) n, SUM(is_active) a, SUM(fmt='video') v, SUM(fmt='statica') st, SUM(fmt='native') na,
                              SUM(start_date>=date('now','localtime','-30 day')) n30, SUM(eu_total_reach) r, MIN(start_date) f,
                              AVG(CASE WHEN is_active=1 THEN julianday('now','localtime')-julianday(start_date) END) age FROM ads WHERE brand_id=?""", (bid,)).fetchone())
        pages = c.execute("SELECT name, role, n_ads, n_active, category FROM pages WHERE brand_id=? ORDER BY n_active DESC LIMIT 8", (bid,)).fetchall()
        angles = c.execute("SELECT angle, COUNT(*) n, SUM(is_active) live FROM ads WHERE brand_id=? AND angle IS NOT NULL GROUP BY angle ORDER BY live DESC LIMIT 8", (bid,)).fetchall()
        mech = c.execute("SELECT mechanism, COUNT(*) n FROM ads WHERE brand_id=? AND mechanism IS NOT NULL GROUP BY mechanism ORDER BY n DESC LIMIT 5", (bid,)).fetchall()
        hooks = c.execute("SELECT hook, COUNT(*) n FROM ads WHERE brand_id=? AND hook IS NOT NULL GROUP BY hook ORDER BY n DESC LIMIT 6", (bid,)).fetchall()
        lps = c.execute("SELECT kind, COUNT(*) n FROM landing_pages WHERE brand_id=? GROUP BY kind ORDER BY n DESC", (bid,)).fetchall()
        mk = {}
        for r in c.execute("SELECT reach_by_country FROM ads WHERE brand_id=? AND reach_by_country IS NOT NULL", (bid,)):
            for k, v in json.loads(r["reach_by_country"] or "{}").items(): mk[k] = mk.get(k, 0) + (v or 0)
        nb = DB.kv_get(c, f"neighbors:{bid}") or []
        L.append(f"\n## {b['name']} · {b['domain']} · stack {b['stack'] or '-'}")
        L.append(f"Ad {s['n']} (live {s['a']}, lanciate 30g {s['n30']}) · mix video {s['v']} / statiche {s['st']} / native {s['na']} · età media live {round(s['age'] or 0)} g · prima ad {s['f']} · reach EU {s['r'] or 0}")
        L.append("Pagine: " + "; ".join(f"{p['name']} [{p['role']}] {p['n_active']} live/{p['n_ads']} ({p['category'] or ''})" for p in pages))
        L.append("Angoli: " + "; ".join(f"{a['angle']} ({a['live']} live/{a['n']})" for a in angles))
        L.append("Meccanismi: " + "; ".join(f"{m['mechanism']} ({m['n']})" for m in mech))
        L.append("Hook: " + " | ".join(f"«{h['hook']}» ×{h['n']}" for h in hooks))
        L.append("Landing: " + ", ".join(f"{l['kind'] or 'altro'} {l['n']}" for l in lps) + " · Mercati EU: " + ", ".join(f"{k} {v}" for k, v in sorted(mk.items(), key=lambda x: -x[1])[:6]))
        L.append("Nei paraggi: " + ", ".join(f"{x.get('domain')} ({x.get('n')})" for x in nb[:10]))
    c.close(); return "\n".join(L)

PROMPT = """Sei il direttore strategico di un team di media buying DTC (scuola Nick Theriot, Luke Iha, Anthony Camacho, Glenn Nieuwenhuis, Alessio Cordeddu). Hai davanti i dati REALI (Meta Ad Library) di tutti i brand che il team spia. Scrivi la MAPPA DEL MERCATO in italiano, markdown, precisa e senza fuffa. Ogni affermazione deve poggiare sui numeri forniti; se un dato manca, dillo.

Sezioni obbligatorie:
1. **Chi domina e perché** (classifica dei brand per forza reale: live, ritmo di lancio, età media, mix formati, reach) — tabella.
2. **Le famiglie di angolo del mercato** (angoli/meccanismi ricorrenti fra più brand, chi li usa, chi li ha inventati per primo per data, dove sono saturi).
3. **Hook template** (10-15 strutture di hook che tornano fra i brand, con esempi citati).
4. **Modello di pagine e funnel** (uso delle pagine alias/persona, tipi di landing, mercati EU coperti, lingue).
5. **Chi copia chi** (sovrapposizioni: stesse pagine nei paraggi, stessi angoli, stessi hook, stessi domini).
6. **Spazi vuoti** (angoli, formati, mercati e funnel che nessuno sta usando: opportunità concrete).
7. **Cosa farebbe ognuno dei mentori** con questi dati (5 righe ciascuno).
8. **Le 10 mosse per il team** questa settimana, ordinate per impatto.

DATI:
{data}
"""

MENTORI = ""

def mentor_notes():
    """Le regole di consenso e la guida di orientamento dei mentori, lette dal vault (il CLI non le vede)."""
    out = []
    for f in ("Consensus rules.md", "Orientation guide.md"):
        try: out.append(f"### {f}\n" + open(os.path.join(MENTORI, f), encoding="utf-8").read()[:14000])
        except Exception: pass
    return "\n\n".join(out)

def run(log=print):
    data = material()
    notes = mentor_notes()
    if notes: data = data + "\n\n# NOTE DEI MENTORI (dal vault, usale per la sezione 7)\n" + notes
    log(f"MARKET: {len(data)} caratteri di materiale")
    out, model = llm.ask(PROMPT.format(data=data), log=log, timeout=1500)
    if not out: raise RuntimeError("MARKET: nessuna risposta da Claude")
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "MARKET.md")
    open(path, "w").write(f"<!-- generato {DB.now()} · modello {model} -->\n\n" + out)
    c = DB.conn(); DB.kv_set(c, "market_md", {"ts": DB.now(), "model": model}); c.commit(); c.close()
    log(f"MARKET: salvata {path} ({model})"); return path

if __name__ == "__main__":
    run()
