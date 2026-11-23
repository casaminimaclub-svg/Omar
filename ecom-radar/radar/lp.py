#!/usr/bin/env python3
"""Ecom Radar — landing page intelligence (Playwright headless).

Per ogni URL di destinazione delle ad: segue i redirect, scatta lo screenshot
full-page, estrae titolo/h1/testo/prezzo, riconosce il TIPO di pagina
(advertorial, listicle, quiz, VSL, PDP, home, collection, checkout/funnel),
rileva lo stack (Shopify + app, page builder, funnel builder, pixel/tracking).
"""
import json, os, re, sys, time, urllib.parse
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

import paths as P
SHOTS = P.LP
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"

TRACK_PARAMS = re.compile(r"^(utm_|fbclid|gclid|ttclid|msclkid|_kx|mc_|ref$|sfnsn|eab|c\d$|pb$|src$|source$|campaign|adset|ad_id|placement|site_source|trafficSource|n=|_ga)", re.I)

STACK_SIGNS = {
    "shopify": [r"cdn\.shopify\.com", r"Shopify\.theme", r"myshopify\.com"],
    "kaching": [r"kaching"], "gempages": [r"gempages"], "pagefly": [r"pagefly"], "replo": [r"replo"],
    "shogun": [r"getshogun"], "funnelish": [r"funnelish"], "clickfunnels": [r"clickfunnels"],
    "flexifunnels": [r"flexifunnels"], "webflow": [r"webflow"], "unbounce": [r"unbounce"], "wordpress": [r"wp-content"],
    "checkout-champ": [r"checkoutchamp|konnektive"], "sticky.io": [r"sticky\.io"], "recharge": [r"rechargepayments|recharge"],
    "klaviyo": [r"klaviyo"], "judge.me": [r"judge\.me|judgeme"], "loox": [r"loox\.io|loox"], "okendo": [r"okendo"],
    "yotpo": [r"yotpo"], "stamped": [r"stamped\.io"], "reviews.io": [r"reviews\.io"],
    "upcart": [r"upcart"], "aftersell": [r"aftersell"], "reconvert": [r"reconvert"], "rebuy": [r"rebuy"],
    "triplewhale": [r"triplewhale"], "elevar": [r"elevar"], "northbeam": [r"northbeam"], "hyros": [r"hyros"],
    "atria": [r"tryatria"], "vitals": [r"vitals\.co|appsvitals"], "gorgias": [r"gorgias"], "tidio": [r"tidio"],
    "hotjar": [r"hotjar"], "clarity": [r"clarity\.ms"], "gtm": [r"googletagmanager"], "ga4": [r"gtag/js"],
    "tiktok-pixel": [r"analytics\.tiktok\.com"], "pinterest-tag": [r"pintrk"], "snap-pixel": [r"sc-static\.net"],
    "meta-pixel": [r"connect\.facebook\.net|fbq\("], "vidalytics": [r"vidalytics"], "wistia": [r"wistia"], "vimeo": [r"player\.vimeo"],
    "convertbox": [r"convertbox"], "typeform": [r"typeform"], "outgrow": [r"outgrow"], "octane": [r"octaneai"],
    "revenuehunt": [r"revenuehunt"], "kickflip": [r"kickflip"], "postscript": [r"postscript"], "attentive": [r"attentive"],
    "stripe": [r"js\.stripe\.com"], "paypal": [r"paypal\.com/sdk"], "shop-pay": [r"shop\.app|shopify-pay"],
}

KIND_RULES = [
    ("checkout", r"/checkouts?/|/cart\b|/checkout"),
    ("quiz", r"quiz|/q/|survey"),
    ("collection", r"/collections?/"),
    ("pdp", r"/products?/|/product/|/p/[a-z0-9-]+"),
    ("home", r"^https?://[^/]+/?(\?.*)?$"),
]


KEEP_PARAMS = {"variant", "id", "p", "page", "v", "q", "product", "sku", "lang", "cat", "step", "offer", "bundle", "pack", "qty"}

def clean_url(u):
    """Toglie i parametri di tracking e normalizza la codifica così la stessa landing conta
    una volta sola (®, %C2%AE e %c2%ae sono la stessa pagina; http/https idem)."""
    if not u: return None
    try:
        u = u.strip().split()[0]                       # link_url malformati con due URL incollati
        p = urllib.parse.urlsplit(u)
        host = p.netloc.lower()
        if host.startswith("www."): host = host[4:]
        raw = urllib.parse.unquote(p.path or "/").split()[0]
        j = raw.find("http", 1)
        if j > 0: raw = raw[:j]                        # due URL incollati dentro il path
        path = urllib.parse.quote(raw, safe="/-._~!$&'()*+,;=:@")
        if path != "/" and path.endswith("/"): path = path[:-1]
        q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True) if k.lower() in KEEP_PARAMS]
        return urllib.parse.urlunsplit(("https", host, path, urllib.parse.urlencode(sorted(q)), ""))
    except Exception:
        return u


def normalize_lps(c):
    """Riallinea le landing già salvate alla normalizzazione corrente: unisce i doppioni."""
    rows = c.execute("SELECT id, url FROM landing_pages").fetchall()
    for r in rows:
        nu = clean_url(r["url"])
        if nu == r["url"]: continue
        other = c.execute("SELECT id FROM landing_pages WHERE url=?", (nu,)).fetchone()
        if other:
            c.execute("UPDATE ads SET lp_id=? WHERE lp_id=?", (other["id"], r["id"]))
            c.execute("DELETE FROM lp_fts WHERE rowid=?", (r["id"],)); c.execute("DELETE FROM landing_pages WHERE id=?", (r["id"],))
        else:
            c.execute("UPDATE landing_pages SET url=? WHERE id=?", (nu, r["id"]))
    c.commit()


def classify(url, html, text, title):
    u = (url or "").lower(); t = (text or "").lower(); h = (html or "").lower()
    for kind, rx in KIND_RULES[:1]:
        if re.search(rx, u): return kind
    tt = (title or "").lower()
    if (re.search(r"quiz|questionn?aire|survey|assessment|take the quiz|find out which|which .* are you|what is your age|what's your age", tt + " " + u)
            or h.count('type="radio"') > 5 and len(t) < 4000
            or (len(re.findall(r"\b\d{2}\s?[-–]\s?\d{2} years old\b|\b\d{2}\+ years old\b|\byears old\b", t)) >= 3 and len(t) < 2500)):
        return "quiz"
    vsl = ("vidalytics" in h or "wistia" in h or ("<video" in h and t.count("watch") > 1)) and len(t) < 6000
    if vsl: return "vsl"
    words = len(t.split())
    numbered = len(re.findall(r"(?:^|\n)\s*(?:#?\s?\d{1,2}[\.\)]\s+\S)", text or ""))
    if numbered >= 3 and words > 300: return "listicle"
    article = bool(re.search(r"\b(min read|sponsored|advertisement|advertorial|by [A-Z][a-z]+ [A-Z][a-z]+|written by|medically reviewed|published|updated on)\b", text or "")) \
        or bool(re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2},? \d{4}\b", t))
    if re.search(r"/(blogs?|articles?|news|health|report|story|stories|advertorial|adv|ad|lp|go|try|read|pages)/", u) and words > 600 and article:
        return "advertorial"
    if re.search(r"/(blogs?|articles?|news|health|report|story|stories|advertorial|adv|ad|lp|go|try|read)/", u) and words > 700:
        return "advertorial"
    if article and words > 900 and not re.search(r"/products?/", u): return "advertorial"
    if words > 1500 and not re.search(r"/products?/", u) and ("add to cart" not in t and "aggiungi al carrello" not in t):
        return "advertorial"
    for kind, rx in KIND_RULES[1:]:
        if re.search(rx, u): return kind
    if re.search(r"add to cart|buy now|aggiungi al carrello|acquista ora|in den warenkorb|ajouter au panier", t): return "pdp"
    return "landing"


def detect_stack(html):
    h = html or ""
    found = [k for k, pats in STACK_SIGNS.items() if any(re.search(p, h, re.I) for p in pats)]
    pixels = sorted(set(re.findall(r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d{8,20})", h)))
    theme = re.search(r'Shopify\.theme\s*=\s*\{[^}]*"name":"([^"]+)"', h)
    return found, pixels, (theme.group(1) if theme else None)


def extract_price(text, html):
    cands = re.findall(r"(?:€|\$|£|USD|EUR|GBP|CHF|kr|zł)\s?\d{1,4}(?:[.,]\d{2})?|\d{1,4}(?:[.,]\d{2})?\s?(?:€|\$|£|USD|EUR|zł|kr)", text or "")
    m = re.search(r'"price"\s*:\s*"?(\d+(?:\.\d+)?)"?', html or "")
    cur = re.search(r'"priceCurrency"\s*:\s*"([A-Z]{3})"', html or "")
    return (cands[0].strip() if cands else (m.group(1) if m else None)), (cur.group(1) if cur else None), cands[:12]


def crawl(urls, brand_id=None, timeout=45000, shots=True, max_n=None, log=print, workers=None):
    """Crawla una lista di URL (già puliti) e salva in landing_pages. N browser in parallelo."""
    workers = workers or int(os.environ.get("RADAR_LP_WORKERS", "3"))
    urls = list(urls)[:max_n] if max_n else list(urls)
    if len(urls) <= 2 or workers <= 1:
        return _crawl_serial(urls, brand_id, timeout, shots, None, log)
    import concurrent.futures
    parts = [urls[i::workers] for i in range(workers)]
    total = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for n in ex.map(lambda part: _crawl_serial(part, brand_id, timeout, shots, None, log), parts):
            total += n
    return total


_JS_POPUP = r"""() => {
  const W = innerWidth, H = innerHeight; let n = 0;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'absolute') continue;
    const r = el.getBoundingClientRect(); const area = (Math.min(r.right, W) - Math.max(r.left, 0)) * (Math.min(r.bottom, H) - Math.max(r.top, 0));
    const t = (el.id + ' ' + el.className + ' ' + (el.getAttribute('role') || '') + ' ' + (el.getAttribute('aria-modal') || '')).toLowerCase();
    const testo = (el.innerText || '').toLowerCase();
    const modale = /popup|modal|klaviyo|newsletter|overlay|backdrop|dialog|attentive|privy|needsclick|signup|subscribe|lightbox|spin|cookie|consent|onetrust|cmp/.test(t) || el.getAttribute('aria-modal') === 'true';
    const invito = /(email|e-mail|subscribe|sign up|unlock|% off|discount|code|spin|join|cookie|privacy)/.test(testo) && testo.length < 1500;
    if (cs.position === 'fixed' && area > W * H * 0.25 && (modale || invito || parseInt(cs.zIndex || 0) > 999)) { el.remove(); n++; }
    else if (modale && cs.position === 'fixed' && area > W * H * 0.08 && invito) { el.remove(); n++; }
  }
  for (const f of document.querySelectorAll('iframe')) { if (/klaviyo|attentive|privy|justuno|popup/i.test(f.src || f.id || '')) { f.remove(); n++; } }
  for (const e of [document.documentElement, document.body]) { if (e) { e.style.overflow = 'auto'; e.style.position = ''; e.classList.remove('modal-open', 'no-scroll', 'overflow-hidden'); } }
  return n;
}"""


def _via_popup(pg):
    """Chiude/toglie i popup (email, sconto, cookie a tutto schermo) prima della lettura e dello screenshot."""
    try: pg.keyboard.press("Escape")
    except Exception: pass
    for sel in ["[aria-label='Close']", "[aria-label='close']", "[aria-label='Close dialog']", ".klaviyo-close-form", "button:has-text('No thanks')", "button:has-text('No, thanks')", "button:has-text('×')", "button:has-text('✕')",
                "button:has-text('Reject All')", "button:has-text('Reject all')", "button:has-text('Decline')", "#onetrust-reject-all-handler", "button:has-text('Rifiuta')"]:
        try: pg.locator(sel).first.click(timeout=500)
        except Exception: pass
    try: pg.evaluate(_JS_POPUP)
    except Exception: pass


def _crawl_serial(urls, brand_id=None, timeout=45000, shots=True, max_n=None, log=print):
    from playwright.sync_api import sync_playwright
    os.makedirs(SHOTS, exist_ok=True)
    c = DB.conn(); done = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(user_agent=UA, viewport={"width": 430, "height": 932}, device_scale_factor=1.5, is_mobile=True, locale="en-US")
        ctx.set_default_timeout(timeout)
        # popup email/sconto: si bloccano gli script che li disegnano (l'anteprima deve mostrare la pagina vera)
        ctx.route(re.compile(r"(klaviyo\.com/onsite|static\.klaviyo\.com/.*(forms|onsite)|attn\.tv|attentive|privy\.com|justuno|omnisend.*form|wisepops|optimonk|getsitecontrol|popupsmart|sleeknote|amped\.io|postscript.*popup|recart.*popup|spin-?a-?sale|wheelio)", re.I), lambda r: r.abort())
        for url in urls:
            if max_n and done >= max_n: break
            row = c.execute("SELECT id FROM landing_pages WHERE url=?", (url,)).fetchone()
            lp_id = row["id"] if row else None
            pg = ctx.new_page()
            rec = {"final_url": None, "status": None, "err": None}
            try:
                resp = pg.goto(url, wait_until="domcontentloaded")
                rec["status"] = resp.status if resp else None
                try: pg.wait_for_load_state("networkidle", timeout=12000)
                except Exception: pass
                # chiudi popup ovvi
                for sel in ["[aria-label='Close']", "[aria-label='close']", ".klaviyo-close-form", "button:has-text('No thanks')", "button:has-text('×')"]:
                    try: pg.locator(sel).first.click(timeout=800)
                    except Exception: pass
                pg.mouse.wheel(0, 2500); pg.wait_for_timeout(700); pg.mouse.wheel(0, -2500)
                pg.wait_for_timeout(2500)   # molti popup compaiono dopo qualche secondo
                _via_popup(pg)
                html = pg.content()
                rec["final_url"] = pg.url
                title = pg.title()
                text = pg.evaluate("() => document.body ? document.body.innerText : ''") or ""
                h1 = pg.evaluate("() => { const h=document.querySelector('h1'); return h? h.innerText.trim() : null }")
                stack, pixels, theme = detect_stack(html)
                price, cur, prices = extract_price(text, html)
                kind = classify(rec["final_url"], html, text, title)
                n_rev = re.search(r"(\d[\d.,]*)\s*(?:reviews|recensioni|avis|bewertungen|reseñas)", text, re.I)
                shot = None
                if shots:
                    shot = os.path.join("lp", f"{lp_id or abs(hash(url))}.jpg")
                    try:
                        _via_popup(pg)
                        pg.screenshot(path=os.path.join(P.MEDIA, shot), full_page=True, type="jpeg", quality=58)
                        # leggera davvero: larghezza 600 e altezza tagliata a 2400 px (~120 KB); prima le pagine da 20.000 px
                        # pesavano 700 KB, il tetto del disco le cancellava e la vista Landing restava piena di 404
                        P.shrink(os.path.join(P.MEDIA, shot), os.path.join(P.MEDIA, shot), max_w=600, quality=52, max_h=2400)
                    except Exception: shot = None
                meta = {"theme": theme, "prices": prices, "len_html": len(html), "og_image": (re.search(r'property="og:image"\s+content="([^"]+)"', html) or [None, None])[1] if re.search(r'property="og:image"\s+content="([^"]+)"', html) else None}
                dom = urllib.parse.urlsplit(rec["final_url"] or url).netloc.lower().replace("www.", "")
                t = DB.today()
                if lp_id:
                    c.execute("""UPDATE landing_pages SET final_url=?,domain=?,kind=?,title=?,h1=?,price=?,currency=?,text=?,screenshot=COALESCE(?,screenshot),
                                 stack=?,pixels=?,word_count=?,n_reviews=?,status=?,last_seen=?,last_crawl=?,err=NULL,meta=?,brand_id=COALESCE(brand_id,?) WHERE id=?""",
                              (rec["final_url"], dom, kind, title, h1, price, cur, text[:20000], shot, json.dumps(stack), json.dumps(pixels),
                               len(text.split()), n_rev.group(1) if n_rev else None, rec["status"], t, DB.now(), json.dumps(meta), brand_id, lp_id))
                else:
                    c.execute("""INSERT INTO landing_pages(url,final_url,domain,brand_id,kind,title,h1,price,currency,text,screenshot,stack,pixels,word_count,n_reviews,status,first_seen,last_seen,last_crawl,meta)
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (url, rec["final_url"], dom, brand_id, kind, title, h1, price, cur, text[:20000], shot, json.dumps(stack), json.dumps(pixels),
                               len(text.split()), n_rev.group(1) if n_rev else None, rec["status"], t, t, DB.now(), json.dumps(meta)))
                    lp_id = c.execute("SELECT id FROM landing_pages WHERE url=?", (url,)).fetchone()["id"]
                    if brand_id and c.execute("SELECT COUNT(*) FROM landing_pages WHERE brand_id=? AND id!=?", (brand_id, lp_id)).fetchone()[0] > 0 and c.execute("SELECT status FROM brands WHERE id=?", (brand_id,)).fetchone()[0] == "ready":
                        DB.log_event(c, "new_lp", brand_id, str(lp_id), f"nuova landing [{kind}] {title or url}")
                    if shot:
                        new_shot = os.path.join("lp", f"{lp_id}.jpg")
                        try:
                            os.replace(os.path.join(P.MEDIA, shot), os.path.join(P.MEDIA, new_shot)); shot = new_shot
                            c.execute("UPDATE landing_pages SET screenshot=? WHERE id=?", (shot, lp_id))
                        except Exception: pass
                c.execute("DELETE FROM lp_fts WHERE rowid=?", (lp_id,))
                c.execute("INSERT INTO lp_fts(rowid,lp_id,url,title,h1,text) VALUES(?,?,?,?,?,?)", (lp_id, lp_id, url, title, h1, text[:20000]))
                c.commit(); done += 1
                log(f"  LP {kind:11s} {price or '':>9s} {len(stack):2d} app  {url[:90]}")
            except Exception as ex:
                err = str(ex).split("\n")[0][:200]
                if lp_id:
                    c.execute("UPDATE landing_pages SET err=?, last_crawl=?, status=? WHERE id=?", (err, DB.now(), rec["status"], lp_id))
                else:
                    c.execute("INSERT OR IGNORE INTO landing_pages(url,domain,brand_id,err,first_seen,last_seen,last_crawl,status) VALUES(?,?,?,?,?,?,?,?)",
                              (url, urllib.parse.urlsplit(url).netloc.lower().replace("www.", ""), brand_id, err, DB.today(), DB.today(), DB.now(), rec["status"]))
                c.commit()
                log(f"  LP ERR {url[:80]} → {err[:80]}")
            finally:
                pg.close()
        b.close()
    c.close()
    return done


def link_ads_to_lps(c, brand_id=None):
    """Collega ogni ad alla sua landing (per URL pulito) e conta le ad per landing."""
    normalize_lps(c)
    w = "WHERE link_url IS NOT NULL" + (" AND brand_id=?" if brand_id else "")
    rows = c.execute(f"SELECT ad_archive_id, link_url FROM ads {w}", (brand_id,) if brand_id else ()).fetchall()
    cache = {}
    for r in rows:
        cu = clean_url(r["link_url"])
        if cu not in cache:
            lp = c.execute("SELECT id FROM landing_pages WHERE url=?", (cu,)).fetchone()
            cache[cu] = lp["id"] if lp else None
        if cache[cu]:
            c.execute("UPDATE ads SET lp_id=? WHERE ad_archive_id=?", (cache[cu], r["ad_archive_id"]))
    c.commit()
    # ricalcolo mirato: solo le landing il cui conteggio cambia (l'UPDATE correlato su tutta la tabella teneva il lock 10+ s)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ads_lp ON ads(lp_id)")
    rows = c.execute("""SELECT l.id, COUNT(a.ad_archive_id) n FROM landing_pages l LEFT JOIN ads a ON a.lp_id=l.id
                        GROUP BY l.id HAVING COALESCE(l.n_ads,-1) != n""").fetchall()
    for i, r in enumerate(rows, 1):
        c.execute("UPDATE landing_pages SET n_ads=? WHERE id=?", (r["n"], r["id"]))
        if i % 200 == 0: c.commit()
    c.commit()


def pending_urls(c, brand_id=None, recrawl_days=30, limit=200):
    """URL puliti delle ad del brand non ancora crawlati (o vecchi), ordinati per numero di ad."""
    w = "WHERE link_url IS NOT NULL" + (" AND brand_id=?" if brand_id else "")
    rows = c.execute(f"SELECT link_url, COUNT(*) n, MAX(is_active) act FROM ads {w} GROUP BY link_url ORDER BY act DESC, n DESC",
                     (brand_id,) if brand_id else ()).fetchall()
    agg = {}
    for r in rows:
        cu = clean_url(r["link_url"])
        if not cu or cu.startswith("https://facebook.com") or cu.startswith("https://instagram.com") or "fb.me" in cu: continue
        agg[cu] = agg.get(cu, 0) + r["n"]
    out = []
    for cu, n in sorted(agg.items(), key=lambda x: -x[1]):
        lp = c.execute("SELECT last_crawl, err FROM landing_pages WHERE url=?", (cu,)).fetchone()
        if lp and lp["last_crawl"] and (not lp["err"]) and lp["last_crawl"][:10] >= (date.fromordinal(date.today().toordinal() - recrawl_days)).isoformat():
            continue
        out.append(cu)
        if len(out) >= limit: break
    return out


if __name__ == "__main__":
    DB.init()
    urls = [clean_url(u) for u in sys.argv[1:]]
    crawl(urls)


def reclassify(c, log=print):
    """Riclassifica le landing già salvate usando url/testo/titolo (senza ricrawl)."""
    rows = c.execute("SELECT id, url, final_url, title, h1, text, kind FROM landing_pages WHERE err IS NULL").fetchall()
    n = 0
    for r in rows:
        k = classify(r["final_url"] or r["url"], "", r["text"] or "", r["title"] or r["h1"] or "")
        if k and k != r["kind"]:
            c.execute("UPDATE landing_pages SET kind=? WHERE id=?", (k, r["id"])); n += 1
    c.commit(); log(f"LANDING: {n} riclassificate su {len(rows)}"); return n
