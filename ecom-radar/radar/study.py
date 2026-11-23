#!/usr/bin/env python3
"""Ecom Radar — STUDIO di un brand: Claude legge i dati raccolti (pagine, ad, hook, copy,
transcript, landing, EU audience, ritmo) e scrive il dossier di intelligence in markdown:
posizionamento, meccanismo unico, angoli e hook che scalano, struttura del funnel, offerta,
audience reale, cosa stanno testando ora, cosa rubare per primo. Salvato in
data/studies/<brand>.md e nel campo brands.notes (mostrato nella UI).

Usa la CLI `claude` locale (nessuna API key): modello sonnet, effort medio.
"""
import json, os, re, subprocess, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "studies")


def claude_bin():
    for p in (os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"), "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        if os.path.exists(p): return p
    return None


def material(bid):
    c = DB.conn(); b = dict(c.execute("SELECT * FROM brands WHERE id=?", (bid,)).fetchone())
    L = [f"# DATI RACCOLTI · {b['name']} · {b['domain']} · stack {b.get('stack')}"]
    s = dict(c.execute("""SELECT COUNT(*) n, SUM(is_active) a, SUM(fmt='video') v, SUM(fmt='statica') i, SUM(fmt='native') k, MIN(start_date) f,
                          SUM(start_date>=date('now','localtime','-30 day')) n30, SUM(eu_total_reach) r, SUM(est_spend) sp FROM ads WHERE brand_id=?""", (bid,)).fetchone())
    L.append(f"Ad totali {s['n']} (live {s['a']}) · video {s['v']} statiche {s['i']} native {s['k']} · prima ad {s['f']} · lanciate ultimi 30g {s['n30']} · reach EU {s['r']} · spesa stimata ${round(s['sp'] or 0):,}")
    L.append("\n## PAGINE (rete)")
    for p in c.execute("SELECT * FROM pages WHERE brand_id=? ORDER BY n_ads DESC", (bid,)):
        L.append(f"- {p['name']} [{p['role']}] {p['n_ads']} ad / {p['n_active']} live · like {p['likes']} · {p['category']} · {p['entity_type'] or ''}")
    L.append("\n## AUDIENCE EU (somma reach dichiarata)")
    cc = Counter(); ag = Counter(); g = Counter()
    for r in c.execute("SELECT reach_by_country, reach_by_age, reach_by_gender FROM ads WHERE brand_id=? AND reach_by_country IS NOT NULL", (bid,)):
        for k, v in json.loads(r["reach_by_country"] or "{}").items(): cc[k] += v or 0
        for k, v in json.loads(r["reach_by_age"] or "{}").items(): ag[k] += v or 0
        for k, v in json.loads(r["reach_by_gender"] or "{}").items(): g[k] += v or 0
    L.append(f"paesi {dict(cc.most_common(8))} · età {dict(ag)} · genere {dict(g)}")
    L.append("\n## LANDING (tipo · n ad · prezzo · titolo · url)")
    for l in c.execute("SELECT * FROM landing_pages WHERE brand_id=? ORDER BY n_ads DESC LIMIT 25", (bid,)):
        L.append(f"- [{l['kind']}] {l['n_ads']} ad · {l['price'] or ''} · {(l['title'] or l['h1'] or '')[:90]} · {l['url'][:110]}")
    top_lp = c.execute("SELECT text, kind, url FROM landing_pages WHERE brand_id=? AND text IS NOT NULL ORDER BY n_ads DESC LIMIT 3", (bid,)).fetchall()
    for l in top_lp:
        L.append(f"\n### TESTO LANDING [{l['kind']}] {l['url'][:100]}\n{(l['text'] or '')[:3500]}")
    L.append("\n## FAMIGLIE DI ANGOLO (analisi creativa per ad) · n ad · live · durata max · stadio")
    try:
        import creative as C
        for a in C.angles(c, bid)[:25]:
            L.append(f"- {a['angle']}: {a['n']} ad · {a['live']} live · max {int(a['max_days'] or 0)} g · {a['stage']} · es. «{a['top_hook']}» (id {a['top_id']})")
    except Exception as ex:
        L.append(f"(non disponibile: {ex})")
    L.append("\n## HOOK / TITOLI PIÙ USATI")
    for h in c.execute("SELECT COALESCE(NULLIF(title,''), substr(body,1,100)) h, COUNT(*) n, SUM(is_active) a FROM ads WHERE brand_id=? GROUP BY h ORDER BY n DESC LIMIT 40", (bid,)):
        L.append(f"- ({h['n']} ad, {h['a']} live) {h['h']}")
    L.append("\n## TOP 25 AD PER INTENSITÀ (score · formato · giorni · varianti · reach · titolo · copy · transcript)")
    for a in [dict(r) for r in c.execute("SELECT * FROM ads WHERE brand_id=? ORDER BY score DESC LIMIT 25", (bid,))]:
        L.append(f"\n### {a['ad_archive_id']} · score {a['score']} · {a['format']} · dal {a['start_date']} {'LIVE' if a['is_active'] else 'spenta '+str(a['end_date'])} · x{a['collation_count']} · reach EU {a['eu_total_reach']} · CTA {a['cta']} · pagina {a['page_name']}")
        if a["title"]: L.append(f"TITOLO: {a['title']}")
        L.append(f"COPY: {(a['body'] or '')[:1200]}")
        if a["transcript"]: L.append(f"TRANSCRIPT: {a['transcript'][:1500]}")
        if a.get("angle"): L.append(f"ANALISI: angolo={a['angle']} · meccanismo={a.get('mechanism')} · persona={a.get('persona')} · awareness={a.get('awareness')} · emozione={a.get('emotion')} · formato={a.get('creative_format')} · perché: {a.get('analysis')}")
    L.append("\n## ULTIME 15 LANCIATE (cosa testano ora)")
    for a in c.execute("SELECT * FROM ads WHERE brand_id=? ORDER BY start_date DESC LIMIT 15", (bid,)):
        L.append(f"- {a['start_date']} {a['format']} x{a['collation_count']} · {a['page_name']} · {(a['title'] or '')[:80]} · {(a['body'] or '')[:200]}")
    c.close()
    return b, "\n".join(L)


PROMPT = """Sei un creative strategist e media buyer senior (scuola Nick Theriot, Luke Iha, Spencer Pawlin, Sarah Levinger, Anthony Camacho). Hai davanti TUTTI i dati pubblici raccolti dal nostro radar su un brand DTC competitor. Scrivi il DOSSIER DI INTELLIGENCE in italiano, markdown, denso e concreto, citando sempre i dati (numeri, ID ad, pagine, URL) che sostengono ogni affermazione. Niente frasi generiche.

Struttura obbligatoria:
1. **In una frase** — cosa vende, a chi, con quale promessa.
2. **Architettura dell'advertiser** — rete di pagine (main vs pagine persona/alias, come le usano), ritmo di lancio, quota video/statiche, età media delle live: cosa dice della loro macchina.
3. **Meccanismo unico e big idea** — il "colpevole nuovo" che dichiarano (UMP/UMS), come lo provano, quali credenze attaccano.
4. **Angoli e hook che scalano** — raggruppa gli hook in famiglie; per ogni famiglia: esempi testuali, quante ad, quante live, da quando, perché funziona (stato mentale/awareness).
5. **Funnel e offerta** — tipi di landing (advertorial/listicle/quiz/VSL/PDP), stack, prezzo/bundle visto, prove (recensioni, garanzie), dove sta la leva di conversione.
6. **Audience reale** — da reach EU (paesi, età, genere): chi comprano davvero vs a chi sembrano parlare.
7. **Cosa stanno testando adesso** — dalle ultime lanciate: nuovi angoli/format/landing.
8. **Cosa rubare, in ordine** — 5 mosse concrete con l'ID/URL dell'esempio da copiare, adattabili a un altro brand della stessa categoria.
9. **Punti deboli** — dove sono attaccabili (angoli scoperti, claim fragili, funnel lenti).
10. **Limiti dei dati** — cosa NON sappiamo (niente spesa reale, reach solo EU, ecc.).

DATI:
"""


def run(bid, log=print):
    import plan
    if not plan.allow_claude(log, "dossier"): return None
    b, mat = material(bid)
    bin_ = claude_bin()
    if not bin_: log("claude CLI non trovata"); return None
    os.makedirs(OUT, exist_ok=True)
    import llm
    log(f"STUDY {b['name']}: {len(mat)} caratteri di materiale → modello migliore disponibile")
    md, model_used = llm.ask(PROMPT + mat[:180000], log=log, timeout=1500)
    md = (md or "").strip()
    if md: md = f"<!-- {model_used} · {DB.now()} -->\n" + md
    if len(md) < 600 or md.startswith("API Error") or "Can't reach the API" in md:
        log(f"  dossier {b['name']}: risposta non valida da claude ({md[:120]!r}), non salvo"); return None
    if not md:
        raise RuntimeError("STUDY: nessuna risposta da Claude (rete o piano): dossier non scritto")
    fp = os.path.join(OUT, re.sub(r"[^a-z0-9]+", "-", b["name"].lower()) + ".md")
    open(fp, "w", encoding="utf-8").write(f"# {b['name']} — dossier di intelligence ({DB.today()})\n\n" + md)
    c = DB.conn(); c.execute("UPDATE brands SET notes=? WHERE id=?", (md, bid)); DB.log_event(c, "study", bid, None, f"dossier scritto ({len(md)} caratteri)"); c.commit(); c.close()
    log(f"STUDY {b['name']}: dossier salvato in {fp}")
    return fp


if __name__ == "__main__":
    run(int(sys.argv[1]))
