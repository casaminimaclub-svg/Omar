"""Brief clean-room di un'ad: struttura, beat, meccanismo, hook, CTA — MAI le parole
(regola Glenn: scheletro sì, carne mai; DMCA clean room).

Ogni chiamata a `claude -p` paga ~60k token di contesto (system prompt, istruzioni, memoria)
per 4k di lavoro utile: un brief alla volta significa buttare il 93% della finestra in preamboli.
Perciò si lavora a LOTTI — più inserzioni nello stesso prompt, brief separati da un marcatore.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB, llm

HEAD = """Sei un creative strategist (scuola Luke Iha, Glenn Nieuwenhuis, Anthony Camacho, Sarah Levinger). Per OGNI inserzione qui sotto scrivi un BRIEF DI PRODUZIONE clean-room in italiano: si usa lo SCHELETRO, mai le parole. Vietato copiare frasi, nomi, numeri specifici: descrivi la struttura e il perché funziona.

Formato di ogni brief (markdown, max 45 righe):
**Formato e scena** · **Hook** (tipo di hook, cosa fa nei primi 2 secondi/prima riga, senza citare) · **Persona e stato mentale** (Sarah: valence/intensity, awareness) · **Big idea e meccanismo** (Luke/Camacho: il colpevole, il "non è colpa tua") · **Beat della storia** (elenco numerato dei passaggi con la funzione di ciascuno) · **Prove usate** (tipo di prova, non i numeri) · **CTA e passaggio alla landing** · **Perché regge** (3 punti) · **Come rifarla per un altro prodotto** (istruzioni operative, formato immagine/video, lunghezza copy, 3 varianti di hook da testare).

REGOLA DI FORMATO, obbligatoria: fai precedere ogni brief dalla riga esatta
===AD <id>===
usando l'id dell'inserzione. Nessun testo prima del primo marcatore, nessun commento finale.

"""
ONE = """===AD {aid}===
Formato: {fmt} · pagina: {page} · attiva da {days} giorni · CTA: {cta}
Titolo: {title}
Copy: {body}
Testo nell'immagine: {ocr}
Transcript: {transcript}
Analisi precedente: angolo {angle} · meccanismo {mechanism} · persona {persona} · emozione {emotion}

"""
BATCH = int(os.environ.get("RADAR_BRIEF_BATCH", "6"))


def _block(a):
    from score import days_running
    return ONE.format(aid=a["ad_archive_id"], fmt=a.get("fmt"), page=a.get("page_name"), days=days_running(a), cta=a.get("cta"),
                      title=a.get("title") or "-", body=(a.get("body") or "-")[:4000], ocr=(a.get("ocr") or "-")[:700],
                      transcript=(a.get("transcript") or "-")[:2500], angle=a.get("angle"), mechanism=a.get("mechanism"),
                      persona=a.get("persona"), emotion=a.get("emotion"))


def run_batch(aids, log=print):
    """Scrive i brief di più inserzioni in una sola chiamata. Ritorna quanti ne ha salvati."""
    c = DB.conn()
    try: c.execute("ALTER TABLE ads ADD COLUMN brief TEXT")
    except Exception: pass
    c.commit()
    ads = [dict(r) for r in c.execute(f"SELECT * FROM ads WHERE ad_archive_id IN ({','.join('?'*len(aids))})", list(aids))]
    c.close()
    if not ads: return 0
    prompt = HEAD + "INSERZIONI DA ANALIZZARE:\n\n" + "".join(_block(a) for a in ads)
    out, model = llm.ask(prompt, log=log, timeout=1800)
    if not out: raise RuntimeError("nessuna risposta da Claude (rete o piano): lotto di brief non scritto")
    parts = re.split(r"^===AD\s+(\S+?)\s*===\s*$", out, flags=re.M)
    got = {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    c = DB.conn(); n = 0
    for aid, txt in got.items():
        if len(txt) < 300: continue                     # risposta troncata o vuota: non la salvo
        c.execute("UPDATE ads SET brief=? WHERE ad_archive_id=?", (f"<!-- {model} · {DB.now()} -->\n" + txt, aid)); n += 1
    c.commit(); c.close()
    missing = [a["ad_archive_id"] for a in ads if a["ad_archive_id"] not in got]
    log(f"BRIEF lotto: {n}/{len(ads)} scritti ({model})" + (f" · mancanti {len(missing)}" if missing else ""))
    return n


def run(aid, log=print):
    """Un brief solo (usato dall'interfaccia: il costo del preambolo qui è inevitabile)."""
    return run_batch([aid], log=log)


def run_many(aids, log=print, batch=None):
    n = 0
    aids = list(aids); b = batch or BATCH
    for i in range(0, len(aids), b):
        n += run_batch(aids[i:i + b], log=log)
    return n
