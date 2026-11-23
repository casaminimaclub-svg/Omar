"""Importa in Ecom Radar le ad viste su AdSpy, con i KPI reali che la Ad Library non dà fuori dall'UE.

Perché esiste: la Ad Library pubblica la reach solo per obbligo europeo, e le ad di questi brand sono
dark post, quindi like/commenti/condivisioni non esistono da nessuna parte pubblica. AdSpy quei numeri
ce li ha perché vede le ad servite in feed veri. Noi li prendiamo da lì e li rimettiamo sull'ad giusta.

Come lavora:
  1. `match(copy)` cerca l'ad nel nostro archivio dalla prima riga della copy. Le native si agganciano
     quasi sempre; i video no, perché il loro testo sta dentro il video.
  2. `from_facebook(url)` apre il post pubblico (funziona SENZA login) e ne tira fuori la primary intera,
     l'immagine o il video a piena risoluzione, la data e la pagina.
  3. `apply_kpi()` scrive i numeri sull'ad, esistente o appena creata, con lo stesso trattamento
     delle altre: formato, impronta, dominio, punteggio.
"""
import json, os, re, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())[:160].strip()


def match(c, copy_start, page_name=None, limit=5, fmt=None):
    """Trova nell'archivio le ad con questa copy. Con `fmt` mette in cima quelle dello stesso formato:
    la stessa storia gira sia in native sia in video, e i KPI di AdSpy valgono per UNA delle due."""
    frag = (copy_start or "").strip()[:70]
    if len(frag) < 20: return []
    q = "SELECT ad_archive_id,page_name,start_date,end_date,is_active,fmt,collation_count FROM ads WHERE body LIKE ?"
    args = [f"%{frag}%"]
    if page_name:
        q += " AND page_name=?"; args.append(page_name)
    q += " ORDER BY start_date DESC LIMIT ?"; args.append(limit)
    return [dict(r) for r in c.execute(q, args)]


def attach(c, post, kpi, page_name, log=print):
    """Il cuore dell'import. Aggancia il post alla famiglia di ad che condividono quella copy:
      - la copy INTEGRALE va su tutte le varianti (la Ad Library ce la dava tagliata);
      - i KPI di AdSpy vanno su UNA sola variante, quella dello stesso formato e con la data di
        partenza più vicina: la stessa storia gira in native e in video, e i numeri sono di una sola.
    Ritorna (ad_archive_id dei KPI, numero di varianti arricchite)."""
    import datetime as _dt
    hits = match(c, post["body"][:70], page_name=page_name, limit=40)
    if not hits: return None, 0
    for h in hits:
        c.execute("""UPDATE ads SET body=?, title=COALESCE(?,title), domain=COALESCE(?,domain), cta=COALESCE(?,cta),
                     link_url=COALESCE(?,link_url), post_url=COALESCE(post_url,?), image_url=COALESCE(image_url,?)
                     WHERE ad_archive_id=?""",
                  (post["body"], post.get("title"), post.get("domain"), post.get("cta"),
                   post.get("link_url"), post.get("post_url"), post.get("image_url"), h["ad_archive_id"]))
        refresh(c, h["ad_archive_id"])
    want = "video" if (kpi.get("media") == "video") else "native"
    def dist(h):
        try:
            a = _dt.date.fromisoformat(h["start_date"]); b = _dt.date.fromisoformat(kpi["created_on"])
            return abs((a - b).days)
        except Exception: return 9999
    same = [h for h in hits if h.get("fmt") == want] or hits
    # due ad diverse possono avere la STESSA copy (stesso prodotto, video diversi): non devono
    # finire sulla stessa riga, o la seconda cancella i numeri della prima. Chi ha già i KPI di
    # un altro post è escluso.
    presi = {r[0] for r in c.execute(
        "SELECT ad_archive_id FROM ads WHERE kpi_source='adspy' AND post_url IS NOT NULL AND post_url<>?",
        (post.get("post_url"),))}
    liberi = [h for h in same if h["ad_archive_id"] not in presi]
    if not liberi:
        log("  tutte le varianti hanno già i KPI di un altro post: creo un'ad a sé")
        return None, len(hits)
    best = min(liberi, key=dist)
    # la riga che porta i KPI deve portare anche il SUO post: prima restava il link di un altro post con la stessa copy
    # un post = una sola riga coi KPI: chi li aveva presi prima per lo stesso post li cede
    c.execute("""UPDATE ads SET reactions=NULL, reactions_n=0, comments=NULL, shares=NULL, kpi_source=NULL, kpi_checked=NULL, post_url=NULL
                 WHERE post_url=? AND ad_archive_id<>? AND kpi_source='adspy'""", (post.get("post_url"), best["ad_archive_id"]))
    c.execute("UPDATE ads SET post_url=? WHERE ad_archive_id=?", (post.get("post_url"), best["ad_archive_id"]))
    apply_kpi(c, best["ad_archive_id"], kpi)
    log(f"  copy integrale su {len(hits)} varianti · KPI su {best['ad_archive_id']} ({best['fmt']}, {best['start_date']})")
    return best["ad_archive_id"], len(hits)


def refresh(c, aid):
    try: DB.refresh_fts(c, aid)
    except Exception: pass


def _count(s):
    """'26K' → 26000, '1.5K' → 1500, '2,488' → 2488."""
    if not s: return None
    s = s.strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([KMkm]?)$", s)
    if not m: return None
    n = float(m.group(1))
    return int(n * {"k": 1000, "m": 1000000}.get(m.group(2).lower(), 1))


def from_facebook(url, log=print):
    """Legge un post pubblico di Facebook (SENZA login). Ritorna dict o None se il post non c'è più.

    Il post dà più di AdSpy: la copy integrale, i numeri IN DIRETTA (AdSpy fotografa il giorno in cui
    l'ha vista), la durata del video, la destinazione e i commenti veri della gente — la voce del mercato.
    """
    from playwright.sync_api import sync_playwright
    out = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent=UA, viewport={"width": 1280, "height": 1800})
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(4500)
            txt = pg.inner_text("body")
            if len(txt) < 400 or "Content Not Found" in txt or "isn't available" in txt:
                log(f"  post non disponibile: {url}"); return None

            page = None
            mp = re.search(r"^(.*?)'s Post", txt, re.M)
            if mp: page = mp.group(1).strip()
            md = re.search(r"\n([A-Z][a-z]{2} \d{1,2}(?:, \d{4})?)\s*\n", txt)

            # corpo: da dopo l'intestazione fino al link di tracciamento (o alle reazioni)
            m = re.search(r"·\s*\n(.+?)(?:\nAll reactions|\nTutte le reazioni|\Z)", txt, re.S)
            body = re.sub(r"\n{3,}", "\n\n", (m.group(1) if m else txt).strip())

            tail = {}
            mt = re.search(r"\n(https?://\S+)\s*\n(?:(\d+:\d+)\s*/\s*(\d+:\d+)\s*\n)?([A-Z0-9.\-]+\.[A-Z]{2,})\s*\n(.+?)\s*\n([A-Za-z ]{3,20})\s*(?:\n|$)", body)
            if mt:
                tail = {"link_url": mt.group(1), "video_len": mt.group(3), "domain": mt.group(4).lower(),
                        "title": mt.group(5).strip(), "cta": mt.group(6).strip()}
                body = body[:mt.start()].strip()
            else:
                ml = re.search(r"\nhttps?://\S+", body)
                if ml: body = body[:ml.start()].strip()

            # numeri in diretta di Facebook
            live = {}
            mr = re.search(r"All reactions:\s*\n([\d.,KMkm]+)", txt)
            if mr: live["fb_reactions"] = _count(mr.group(1))
            mc = re.search(r"([\d.,KMkm]+)\s+comments?", txt)
            if mc: live["fb_comments"] = _count(mc.group(1))
            ms = re.search(r"([\d.,KMkm]+)\s+shares?", txt)
            if ms: live["fb_shares"] = _count(ms.group(1))

            # commenti veri: la voce del mercato, quella che nessuno strumento di spionaggio dà
            comments = []
            mm = re.search(r"Most relevant\ufeff?\n(.+)", txt, re.S)
            if mm:
                lines = [l.strip() for l in mm.group(1).split("\n") if l.strip()]
                i = 0
                while i < len(lines) - 1 and len(comments) < 40:
                    name, text = lines[i], lines[i + 1]
                    if re.match(r"^[A-Z][\w.'\-]*(?: [A-Z][\w.'\-]*){0,3}$", name) and not re.match(r"^(View|Like|Reply|Most|All|\d)", text):
                        comments.append({"autore": name, "testo": text}); i += 2
                    else: i += 1

            imgs = [i.get_attribute("src") for i in pg.query_selector_all("img")]
            imgs = [i for i in imgs if i and "scontent" in i and ("t45" in i or "t15" in i)] or [i for i in imgs if i and "scontent" in i]
            vids = [v.get_attribute("src") for v in pg.query_selector_all("video")]
            out = {"post_url": url, "page_name": page, "post_date": md.group(1) if md else None,
                   "body": body, "n_chars": len(body), "commenti": comments,
                   "image_url": imgs[0] if imgs else None, "video_url": next((v for v in vids if v), None)}
            out.update(tail); out.update(live)
        except Exception as ex:
            log(f"  errore su {url}: {ex}")
        finally:
            b.close()
    return out


def _fb_date(s, fallback=None):
    """'May 23' o 'May 23, 2026' → ISO. Senza anno si assume l'anno in corso."""
    if not s: return fallback
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d", "%B %d"):
        try:
            d = datetime.datetime.strptime(s, fmt)
            if "%Y" not in fmt: d = d.replace(year=datetime.date.today().year)
            return d.date().isoformat()
        except ValueError: continue
    return fallback


def _vecchio_import_ad(row, brand_id, page_id=None, log=print):
    """row = riga di adspy_ads (dict). Aggancia o crea l'ad, poi ci scrive i KPI. Ritorna (aid, esito)."""
    c = DB.conn()
    copy_start = (row.get("fb_body") or row.get("body") or "").strip()
    hits = match(c, copy_start, page_name=row.get("page_name"))
    if hits:
        aid = hits[0]["ad_archive_id"]; esito = f"agganciata ({len(hits)} varianti in archivio)"
    else:
        # ad che non abbiamo: la creiamo dal post Facebook
        if not row.get("post_url"):
            c.close(); return None, "nessun aggancio e nessun link al post"
        aid = "adspy:" + re.sub(r"\D", "", row["post_url"])[-18:]
        ad = {"ad_archive_id": aid, "page_id": page_id, "page_name": row.get("page_name"),
              "body": row.get("fb_body") or row.get("body"), "title": row.get("headline"),
              "cta": row.get("cta"), "link_url": None, "domain": row.get("domain"),
              "start_date": row.get("created_on"), "end_date": row.get("last_seen"),
              "is_active": 0, "format": "video" if row.get("media") == "video" else "image",
              "image_url": row.get("image_url"), "video_url": row.get("video_url"),
              "countries": json.dumps((row.get("countries") or "").split(",")) if row.get("countries") else None,
              "post_url": row.get("post_url"), "collation_count": 1}
        DB.upsert_ad(c, ad, brand_id=brand_id, source="adspy")
        esito = "creata da AdSpy"
    apply_kpi(c, aid, row)
    c.commit(); c.close()
    return aid, esito


def apply_kpi(c, aid, row, post=None):
    """Scrive i KPI reali sull'ad. `kpi_source='adspy'` distingue il misurato dallo stimato.
    Se abbiamo anche il post, si aggiungono i numeri in diretta di Facebook e i commenti veri."""
    post = post or {}
    k = {"likes": row.get("likes"), "comments": row.get("comments"), "shares": row.get("shares")}
    if post.get("fb_reactions"): k["fb_reazioni"] = post["fb_reactions"]
    if post.get("fb_comments"): k["fb_commenti"] = post["fb_comments"]
    if post.get("fb_shares"): k["fb_condivisioni"] = post["fb_shares"]
    if post.get("video_len"): k["durata_video"] = post["video_len"]
    if post.get("commenti"):
        try: c.execute("ALTER TABLE ads ADD COLUMN market_voice TEXT")
        except Exception: pass
        c.execute("UPDATE ads SET market_voice=? WHERE ad_archive_id=?", (json.dumps(post["commenti"], ensure_ascii=False), aid))
    reactions = json.dumps(k)
    c.execute("""UPDATE ads SET reactions=?, comments=?, shares=?, kpi_source='adspy', kpi_checked=?,
                 gender_audience=COALESCE(?,gender_audience), countries=COALESCE(countries,?)
                 WHERE ad_archive_id=?""",
              (reactions, row.get("comments"), row.get("shares"), DB.now(), row.get("gender"),
               json.dumps((row.get("countries") or "").split(",")) if row.get("countries") else None, aid))
    c.execute("UPDATE ads SET reactions=? WHERE ad_archive_id=?", (reactions, aid))


def ingest(post, kpi, brand_id, page_name=None, page_id=None, log=print, attacca=True):
    """Porta in Ecom Radar un'ad vista su AdSpy, con tutto il corredo delle altre.

    Se la copy esiste già in archivio si aggancia (e tutte le varianti ricevono la copy integrale);
    se non esiste — è il caso dei video, il cui testo la Ad Library non ci ha mai dato — l'ad viene
    creata da zero con l'id del post Facebook.
    Ritorna (ad_archive_id, esito).
    """
    import formats as F
    c = DB.conn()
    page_name = page_name or post.get("page_name")
    # GUARDIA DELL'OMONIMIA: AdSpy cerca per nome, e i nomi si ripetono. Prima di scrivere qualsiasi
    # cosa si controlla che la destinazione del post appartenga al brand. Senza questo controllo un
    # inserzionista svedese di tutt'altro prodotto finiva dentro Pipitea solo perché la persona-pagina
    # si chiamava uguale.
    dom = (post.get("domain") or "").lower()
    if dom and brand_id:
        b = c.execute("SELECT domain, domains FROM brands WHERE id=?", (brand_id,)).fetchone()
        noti = set()
        if b:
            noti.add((b["domain"] or "").lower())
            try: noti |= {str(x).lower() for x in json.loads(b["domains"] or "[]")}
            except Exception: pass
        noti |= {r[0].lower() for r in c.execute(
            "SELECT DISTINCT domain FROM ads WHERE brand_id=? AND domain IS NOT NULL", (brand_id,)) if r[0]}
        radice = lambda d: (lambda p: ".".join(p[-3:] if len(p) >= 3 and p[-2] in ("co", "com", "org", "net", "gov", "ac") and len(p[-1]) == 2 else p[-2:]))(d.lower().removeprefix("www.").split("."))
        if noti and not any(radice(dom) == radice(n) or radice(dom) in n or radice(n) in dom for n in noti if n):
            c.close()
            return None, f"OMONIMA: il post porta a {dom}, che non è del brand — non importata"
    # attacca=False: l'ad di AdSpy diventa una riga a sé, con la SUA creatività e i SUOI numeri.
    # Agganciarla a una variante Meta con la stessa copy metteva 138k like su un'ad con 45 di reach.
    aid, n = attach(c, post, kpi, page_name, log=log) if attacca else (None, 0)
    esito = f"agganciata a {n} varianti" if aid else None
    if not aid:
        aid = ("fb" + re.sub(r"\D", "", post["post_url"]).split("posts")[-1][-18:]) if "facebook.com" in post["post_url"] else ("ig" + re.sub(r"[^\w]", "", post["post_url"].rstrip("/").split("/")[-1]))
        ad = {"ad_archive_id": aid, "page_id": page_id, "page_name": page_name,
              "body": post.get("body"), "title": post.get("title"), "cta": post.get("cta"),
              "link_url": post.get("link_url"), "domain": post.get("domain"),
              "start_date": kpi.get("created_on"), "end_date": kpi.get("last_seen"),
              "is_active": 1 if kpi.get("last_seen", "") >= DB.today()[:7] else 0,
              "format": "video" if (post.get("video_len") or kpi.get("media") == "video") else "image",
              "image_url": post.get("image_url"), "video_url": post.get("video_url"),
              "post_url": post["post_url"], "collation_count": 1,
              "countries": json.dumps([x for x in (kpi.get("countries") or "").split(",") if x]) or None}
        _assicura_pagina(c, page_id, page_name, brand_id)
        DB.upsert_ad(c, ad, brand_id=brand_id, source="adspy")
        c.execute("UPDATE ads SET fmt=? WHERE ad_archive_id=?", (F.classify(ad), aid))
        esito = "creata (non era in archivio)"
    apply_kpi(c, aid, kpi, post)
    c.commit(); c.close()
    return aid, esito


def _assicura_pagina(c, page_id, page_name, brand_id):
    """Un'ad senza la sua pagina in archivio è un'ad monca: niente avatar, niente scheda pagina,
    niente conteggi. Le pagine che AdSpy ci fa scoprire vanno registrate come le altre."""
    if not page_id: return
    if c.execute("SELECT 1 FROM pages WHERE page_id=?", (page_id,)).fetchone(): return
    cols = {r[1] for r in c.execute("PRAGMA table_info(pages)")}
    campi = {"page_id": page_id, "name": page_name, "brand_id": brand_id}
    for k, v in (("first_seen", DB.today()), ("last_seen", DB.today()), ("source", "adspy"), ("n_ads", 0), ("n_active", 0)):
        if k in cols: campi[k] = v
    c.execute(f"INSERT INTO pages({','.join(campi)}) VALUES({','.join('?'*len(campi))})", list(campi.values()))
