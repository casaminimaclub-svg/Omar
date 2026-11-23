#!/usr/bin/env python3
"""Ecom Radar — client per la Meta Ad Library pubblica (nessun login, nessun token).

Tre operazioni, tutte su sessione persistente (cookie datr/rd_challenge riusati,
fingerprint coerente) con rate limiter adattivo condiviso:

  search(query|page_id, country, ...)  -> iteratore di ad NORMALIZZATE, paginazione
                                          GraphQL completa (AdLibrarySearchPaginationQuery)
  details(ad_archive_id, page_id, cc)  -> trasparenza EU: reach totale, età/genere/paese,
                                          payer/beneficiary, info pagina (AdLibraryV3AdDetailsQuery)
  doc_ids()                            -> doc_id correnti letti dai bundle JS (Meta li ruota)

I doc_id vengono ri-scoperti dai bundle ad ogni sessione e cachati su disco; quelli
noti al 2026-09-05 fanno da fallback.
"""
import gzip, io, json, os, random, re, sys, threading, time, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone
from http.cookiejar import CookieJar

BASE = "https://www.facebook.com"
GRAPHQL = BASE + "/api/graphql/"
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "doc_ids.json")
FALLBACK_DOC_IDS = {
    "AdLibrarySearchPaginationQuery": "24922295957467452",
    "AdLibraryV3AdDetailsQuery": "25068828942793558",
    "AdLibraryTypeaheadSuggestionDataSourceQuery": "9755915494515334",
}
UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


class Blocked(Exception):
    pass


class Limiter:
    """Token bucket condiviso fra thread: >= gap secondi fra due richieste QUALSIASI
    (anche con più worker in parallelo). Accelera dopo 8 successi, rallenta ai blocchi
    senza esplodere (un blocco soft transitorio non deve costare minuti)."""
    def __init__(self, gap=1.5, gap_min=0.8, gap_max=8.0):   # oltre 8 s per richiesta un giro notturno dura ore: meglio fermarsi e riprendere
        self.gap, self.gap_min, self.gap_max = gap, gap_min, gap_max
        self.base = gap
        self.last = 0.0; self.lock = threading.Lock(); self.ok = self.blocked = 0
        self.soft_streak = 0; self.cooldown_until = 0.0
    LIMITE_GLOBALE = float(os.environ.get("RADAR_META_MAX_S", "900"))   # 15 min di attesa totale per fase

    def wait(self):
        with self.lock:
            now = time.time()
            if self.cooldown_until > now:              # Meta sta servendo solo il guscio: si aspetta davvero, non si striscia
                self.last = max(self.last, self.cooldown_until)
            sleep = max(0.0, self.last + self.gap - now)
            self.last = max(now, self.last + self.gap)
        if sleep > 0:
            # somma di tutte le attese: oltre il tetto Meta ci sta chiudendo la porta e continuare a
            # dormire congela l'intero giro (era rimasto fermo 6 ore su un brand). Meglio dichiararlo.
            self.dormito = getattr(self, "dormito", 0.0) + sleep
            if self.dormito > self.LIMITE_GLOBALE: raise Blocked("rate-limit-persistente")
            time.sleep(sleep + random.uniform(0, 0.2))
    def nuova_fase(self):
        """Azzera l'attesa accumulata: il tetto vale per fase (un brand, un passo), non per sempre."""
        self.dormito = 0.0

    def good(self):
        with self.lock:
            self.ok += 1; self.soft_streak = 0
            if self.ok % 4 == 0 and self.gap > self.base:
                self.gap = max(self.base, self.gap * 0.85)      # rientro dal rallentamento
            elif self.ok >= 20 and self.ok % 10 == 0:
                # Meta sta servendo pulito da un pezzo: si puo' stringere sotto il ritmo base.
                # Prima il gap non scendeva MAI sotto 1.5 s nemmeno con 200 richieste buone di fila.
                # Al primo intoppo bad() riporta comunque il ritmo a >= 3 s, quindi il rischio e' limitato.
                self.gap = max(1.0, self.gap * 0.9)
    def bad(self):
        with self.lock:
            self.blocked += 1; self.ok = 0
            self.gap = min(self.gap_max, max(self.gap * 1.6, 3.0)); return self.gap
    def soft(self):
        """Pagina servita senza risultati (guscio SPA): segnale di load-shedding. Rallenta un po';
        dopo 3 di fila fa una pausa vera di 90 s e riparte da un ritmo doppio del base."""
        with self.lock:
            self.blocked += 1; self.ok = 0; self.soft_streak += 1
            if self.soft_streak >= 3:
                self.cooldown_until = time.time() + 90; self.gap = min(self.gap_max, self.base * 2); self.soft_streak = 0
            else:
                self.gap = min(self.gap_max, max(self.gap * 1.25, self.base * 1.25))
            return self.gap


LIMITER = Limiter(gap=float(os.environ.get("RADAR_GAP", "1.5")))


class Session:
    """Una identità browser: cookie jar + UA + lsd + doc_id. Si scalda con un GET della
    library (risolve la challenge __rd_verify) e poi parla GraphQL."""
    def __init__(self):
        self.ua = random.choice(UAS)
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.lsd = None; self.warm = False; self.n = 0
        self.session_id = str(uuid.uuid4())
        self.referer = BASE + "/ads/library/"

    # ---- HTTP ----
    def _headers(self, extra=None):
        h = {"User-Agent": self.ua, "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip",
             "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
             "Sec-Fetch-Site": "same-origin" if self.warm else "none", "Sec-Fetch-Mode": "navigate",
             "Sec-Fetch-Dest": "document", "Upgrade-Insecure-Requests": "1"}
        if extra: h.update(extra)
        return h

    def _raw(self, url, data=None, headers=None, method=None):
        req = urllib.request.Request(url, data=data, headers=self._headers(headers), method=method)
        try:
            r = self.opener.open(req, timeout=25)
            status, raw, enc = r.status, r.read(), r.headers.get("Content-Encoding", "")
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read(); enc = e.headers.get("Content-Encoding", "") if e.headers else ""
        except Exception:
            return 0, ""
        if enc == "gzip" or raw[:2] == b"\x1f\x8b":
            try: raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            except Exception: pass
        return status, raw.decode("utf-8", errors="replace")

    def get_html(self, url):
        LIMITER.wait()
        status, body = self._raw(url)
        m = re.search(r"/__rd_verify_[^'\"]+", body)
        if m:
            self._raw(BASE + m.group(0), method="POST")
            status, body = self._raw(url)
            if re.search(r"/__rd_verify_", body):
                LIMITER.bad(); raise Blocked("challenge-loop")
        if status == 0: LIMITER.bad(); raise Blocked("network")
        if status != 200: LIMITER.bad(); raise Blocked(f"http-{status}")
        if '"xfb_ad_library_is_captcha_required":true' in body: LIMITER.bad(); raise Blocked("captcha")
        self.warm = True; self.n += 1; LIMITER.good()
        m = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', body) or re.search(r'"lsd":"([^"]+)"', body)
        if m: self.lsd = m.group(1)
        self.referer = url
        return body

    def gql(self, name, variables):
        if not self.lsd:
            self.get_html(BASE + "/ads/library/?active_status=all&ad_type=all&country=ALL&media_type=all")
        doc_id = doc_ids().get(name)
        p = {"lsd": self.lsd, "doc_id": doc_id, "fb_api_caller_class": "RelayModern",
             "fb_api_req_friendly_name": name, "variables": json.dumps(variables),
             "server_timestamps": "true", "__a": "1", "__comet_req": "1", "__user": "0", "av": "0", "dpr": "2"}
        LIMITER.wait()
        status, body = self._raw(GRAPHQL, data=urllib.parse.urlencode(p).encode(), headers={
            "Content-Type": "application/x-www-form-urlencoded", "X-FB-LSD": self.lsd,
            "X-FB-Friendly-Name": name, "Origin": BASE, "Referer": self.referer, "Accept": "*/*",
            "X-ASBD-ID": "359341", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"})
        if status != 200: LIMITER.bad(); raise Blocked(f"gql-http-{status}")
        try:
            j = json.loads(body.split("\n")[0])
        except Exception:
            LIMITER.bad(); raise Blocked("gql-parse:" + body[:80])
        errs = j.get("errors") or []
        if any(e.get("code") == 1675004 or "Rate limit" in str(e.get("message")) for e in errs):
            raise Blocked("rate-limit")     # limite del solo GraphQL: il ritmo HTML non c'entra
        if errs and not (j.get("data") or {}).get("ad_library_main"):
            LIMITER.bad(); raise Blocked("gql:" + str(errs)[:120])
        LIMITER.good(); self.n += 1
        return j.get("data") or {}


_TLS = threading.local()

def session(reset=False):
    if reset or not getattr(_TLS, "s", None):
        _TLS.s = Session()
    return _TLS.s


# ---------------- doc_id discovery ----------------
_DOC = {}

def doc_ids(refresh=False):
    global _DOC
    if _DOC and not refresh: return _DOC
    try:
        cached = json.load(open(CACHE))
        if not refresh and time.time() - cached.get("_ts", 0) < 86400 * 3:
            _DOC = {**FALLBACK_DOC_IDS, **{k: v for k, v in cached.items() if not k.startswith("_")}}
            return _DOC
    except Exception:
        pass
    _DOC = dict(FALLBACK_DOC_IDS)
    try:
        s = Session()
        html = s.get_html(BASE + "/ads/library/?active_status=all&ad_type=all&country=ALL&q=test&search_type=keyword_unordered&media_type=all")
        found = {}
        for u in list(dict.fromkeys(re.findall(r'https://[a-z0-9.\-]*fbcdn\.net/rsrc\.php/[^\s"\'<>]+\.js', html))):
            _, b = s._raw(u)
            for n in FALLBACK_DOC_IDS:
                if n in found: continue
                i = b.find(n)
                if i >= 0:
                    m = re.search(r'"(\d{15,20})"', b[i:i + 400]) or re.search(r'"(\d{15,20})"', b[max(0, i - 400):i])
                    if m: found[n] = m.group(1)
            if len(found) == len(FALLBACK_DOC_IDS): break
        _DOC.update(found)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump({**_DOC, "_ts": time.time()}, open(CACHE, "w"))
    except Exception:
        pass
    return _DOC


# ---------------- normalizzazione ----------------
def _iso(ts):
    if not ts: return None
    try: return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception: return None

def domain_of(u):
    m = re.match(r"https?://([^/?#]+)", u or "")
    if not m: return None
    d = m.group(1).lower()
    return d[4:] if d.startswith("www.") else d

def normalize(r):
    """Nodo grezzo (collated_result) -> dict piatto con tutto ciò che serve.
    Tiene anche `raw` compatto per non perdere nulla."""
    snap = r.get("snapshot") or {}
    cards = snap.get("cards") or []
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    media = []          # tutti i media, in ordine
    for v in videos:
        media.append({"kind": "video", "hd": v.get("video_hd_url"), "sd": v.get("video_sd_url"), "thumb": v.get("video_preview_image_url")})
    for im in images:
        media.append({"kind": "image", "url": im.get("original_image_url") or im.get("resized_image_url"), "thumb": im.get("resized_image_url") or im.get("original_image_url")})
    for c in cards:
        if c.get("video_hd_url") or c.get("video_sd_url"):
            media.append({"kind": "video", "hd": c.get("video_hd_url"), "sd": c.get("video_sd_url"), "thumb": c.get("video_preview_image_url"), "card": True})
        elif c.get("original_image_url") or c.get("resized_image_url"):
            media.append({"kind": "image", "url": c.get("original_image_url") or c.get("resized_image_url"), "thumb": c.get("resized_image_url") or c.get("original_image_url"), "card": True})
    first_video = next((m for m in media if m["kind"] == "video"), None)
    first_img = next((m for m in media if m["kind"] == "image"), None)
    video_url = (first_video or {}).get("hd") or (first_video or {}).get("sd")
    image_url = (first_video or {}).get("thumb") or (first_img or {}).get("url")
    body = (snap.get("body") or {}).get("text") or ""
    import re as _re
    _ph = lambda x: bool(_re.match(r"^\s*\{\{[^}]+\}\}\s*$", x or ""))
    if (not body or _ph(body)) and cards:      # DCO: il testo vero sta nelle card, non nel segnaposto {{product.brand}}
        cand = [(c or {}).get("body") or "" for c in cards if not _ph((c or {}).get("body") or "")]
        if cand: body = max(cand, key=len)
    title = snap.get("title") or (cards[0].get("title") if cards else None)
    if _ph(title) and cards:
        cand = [(c or {}).get("title") or "" for c in cards if not _ph((c or {}).get("title") or "")]
        title = max(cand, key=len) if cand else None
    link_url = snap.get("link_url") or (cards[0].get("link_url") if cards else None)
    link_desc = snap.get("link_description") or (cards[0].get("link_description") if cards else None)
    cta = snap.get("cta_text") or (cards[0].get("cta_text") if cards else None)
    fmt = snap.get("display_format") or ("VIDEO" if video_url else "IMAGE" if image_url else "UNKNOWN")
    if fmt in ("DCO", "DPA") and len(cards) > 1: fmt_norm = "carousel"
    elif fmt == "CAROUSEL": fmt_norm = "carousel"
    elif video_url: fmt_norm = "video"
    elif image_url: fmt_norm = "image"
    else: fmt_norm = "other"
    post_url = None
    rrp = snap.get("root_reshared_post")
    if isinstance(rrp, dict):
        post_url = rrp.get("url") or rrp.get("permalink_url")
    cc = snap.get("country_iso_code")
    tgt = list(r.get("targeted_or_reached_countries") or [])
    countries = sorted({c for c in ([cc] if cc else []) + tgt if c})
    imp = r.get("impressions_with_index") or {}
    sp = r.get("spend")
    return {
        "ad_archive_id": str(r.get("ad_archive_id")),
        "collation_id": r.get("collation_id"), "collation_count": r.get("collation_count") or 1,
        "page_id": str(r.get("page_id") or snap.get("page_id") or ""),
        "page_name": snap.get("page_name") or r.get("page_name"),
        "page_likes": snap.get("page_like_count"), "page_categories": ",".join(snap.get("page_categories") or []),
        "page_profile_uri": snap.get("page_profile_uri"), "page_pic": snap.get("page_profile_picture_url"),
        "start_date": _iso(r.get("start_date")), "end_date": _iso(r.get("end_date")),
        "is_active": 1 if r.get("is_active") else 0,
        "total_active_time": r.get("total_active_time"),
        "format": fmt_norm, "display_format": fmt, "n_cards": len(cards),
        "video_url": video_url, "image_url": image_url, "media": media,
        # niente taglio della copy: le native di questi brand arrivano a 40.000 caratteri e il testo È l'inserzione
        "body": body, "title": title, "link_description": link_desc, "caption": snap.get("caption"),
        "cta": cta, "cta_type": snap.get("cta_type"),
        "link_url": link_url, "domain": domain_of(link_url),
        "platforms": ",".join(r.get("publisher_platform") or []),
        "countries": ",".join(countries), "country_iso": cc,
        "is_aaa_eligible": 1 if r.get("is_aaa_eligible") else 0,
        "impressions_text": imp.get("impressions_text"), "impressions_index": imp.get("impressions_index"),
        "spend_text": (sp if isinstance(sp, str) else json.dumps(sp)) if sp else None,
        "reach_estimate": r.get("reach_estimate") if not isinstance(r.get("reach_estimate"), dict) else json.dumps(r.get("reach_estimate")),
        "post_url": post_url, "is_reshared": 1 if snap.get("is_reshared") else 0,
        "branded_content": json.dumps(snap.get("branded_content")) if snap.get("branded_content") else None,
        "extra_links": json.dumps(snap.get("extra_links") or []) if snap.get("extra_links") else None,
        "categories": ",".join(r.get("categories") or []),
        "ad_library_url": f"{BASE}/ads/library/?active_status=all&ad_type=all&country=ALL&id={r.get('ad_archive_id')}",
    }


# ---------------- search ----------------
def _url(query=None, page_id=None, country="ALL", active="all", media="all", since=None, until=None, sort_newest=True, platforms=None):
    p = {"active_status": active, "ad_type": "all", "country": country, "media_type": media}
    if sort_newest:
        p["sort_data[direction]"] = "desc"; p["sort_data[mode]"] = "relevancy_monthly_grouped"
    if page_id:
        p["view_all_page_id"] = str(page_id); p["search_type"] = "page"
    else:
        p["q"] = query; p["search_type"] = "keyword_unordered"
    if since:
        p["start_date[min]"] = since; p["start_date[max]"] = until or ""
    if platforms:
        for i, pl in enumerate(platforms): p[f"publisher_platforms[{i}]"] = pl
    return BASE + "/ads/library/?" + urllib.parse.urlencode(p)

def _extract(html):
    i = html.find('"search_results_connection":')
    if i < 0: return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(html, i + len('"search_results_connection":'))
        return obj
    except Exception:
        return None

def _config(html):
    i = html.find('"adType"')
    if i < 0: return None
    j = html.rfind("{", 0, i)
    for _ in range(40):
        if j < 0 or i - j > 4000: return None
        try:
            obj, _ = json.JSONDecoder().raw_decode(html, j)
            if isinstance(obj, dict) and "adType" in obj and "activeStatus" in obj: return obj
        except Exception:
            pass
        j = html.rfind("{", 0, j)
    return None

def _edges_to_ads(edges):
    for e in edges or []:
        n = e.get("node") or {}
        for r in (n.get("collated_results") or [n]):
            if r.get("ad_archive_id"):
                yield normalize(r)

def search(query=None, page_id=None, country="ALL", active="all", media="all", since=None, until=None,
           max_pages=200, max_ads=None, platforms=None, on_page=None, retries=4):
    """Iteratore su TUTTE le ad (paginazione completa). Ritorna anche il totale via
    on_page(count, page_index). Si ferma su has_next_page False, max_pages o max_ads."""
    s = session()
    url = _url(query, page_id, country, active, media, since, until, True, platforms)
    html = s.get_html(url)
    conn = _extract(html)
    if conn is None:
        raise Blocked("no-results-block")
    total = conn.get("count")
    cfg = _config(html) or {}
    n = 0
    if on_page: on_page(total, 0)
    for ad in _edges_to_ads(conn.get("edges")):
        yield ad; n += 1
        if max_ads and n >= max_ads: return
    pi = conn.get("page_info") or {}
    cursor = pi.get("end_cursor"); has_next = pi.get("has_next_page")
    page = 0
    while has_next and cursor and page < max_pages:
        page += 1
        variables = {"count": 30, "cursor": cursor, "params": {
            "activeStatus": cfg.get("activeStatus", active), "adType": cfg.get("adType", "all"),
            "audienceTimeframe": cfg.get("audienceTimeframe"), "collationToken": cfg.get("collationToken"),
            "contentLanguages": cfg.get("contentLanguages", []), "countries": cfg.get("countries"),
            "country": cfg.get("country", country), "excludedIDs": cfg.get("excludedIDs"), "location": cfg.get("location"),
            "mediaType": cfg.get("mediaType", media), "multiCountryFilterMode": cfg.get("multiCountryFilterMode"),
            "pageIDs": cfg.get("pageIDs", []), "potentialReachInput": cfg.get("potentialReach"),
            "publisherPlatforms": cfg.get("publisherPlatforms", []), "query": cfg.get("query", query or ""),
            "regions": cfg.get("regions"), "searchType": cfg.get("searchType", "page" if page_id else "keyword_unordered"),
            "sortData": cfg.get("sortData"), "startDate": cfg.get("startDate"), "viewAllPageID": cfg.get("viewAllPageID")}}
        data = None
        for attempt in range(retries):
            try:
                data = s.gql("AdLibrarySearchPaginationQuery", variables)
                break
            except Blocked as ex:
                if attempt >= retries - 1: raise
                # rate limit: pausa lunga crescente, poi nuova identità e ri-priming della pagina
                pausa = min(45 * (attempt + 1) if str(ex) == "rate-limit" else min(LIMITER.gap, 45), 120)
                time.sleep(pausa)
                s = session(reset=True); s.get_html(url)
        conn = ((data.get("ad_library_main") or {}).get("search_results_connection")) or {}
        if on_page: on_page(total, page)
        for ad in _edges_to_ads(conn.get("edges")):
            yield ad; n += 1
            if max_ads and n >= max_ads: return
        pi = conn.get("page_info") or {}
        cursor = pi.get("end_cursor"); has_next = pi.get("has_next_page")

def count(query=None, page_id=None, country="ALL", active="all"):
    """Solo il totale dichiarato da Meta (1 richiesta)."""
    s = session()
    html = s.get_html(_url(query, page_id, country, active))
    conn = _extract(html) or {}
    return conn.get("count"), list(_edges_to_ads(conn.get("edges")))


# ---------------- details (trasparenza EU) ----------------
def details(ad_archive_id, page_id, country="ALL", is_aaa_eligible=True):
    s = session()
    data = s.gql("AdLibraryV3AdDetailsQuery", {
        "adArchiveID": str(ad_archive_id), "pageID": str(page_id), "country": country,
        "sessionID": s.session_id, "source": None, "isAdNonPolitical": True,
        "isAdNotAAAEligible": not is_aaa_eligible})
    d = ((data.get("ad_library_main") or {}).get("ad_details")) or {}
    tl = d.get("transparency_by_location") or {}
    eu = tl.get("eu_transparency") or {}
    # Il Regno Unito pubblica la stessa trasparenza dell'UE (reach, eta', genere) ma in un blocco
    # suo: prima si leggeva solo quello UE, e i brand che vendono solo in UK (NuraCalm) restavano
    # a reach zero. Le due aree non si sovrappongono, quindi si sommano.
    uk = tl.get("uk_transparency") or {}
    br = tl.get("br_transparency") or {}     # il Brasile pubblica la reach come UE e UK (verificato 1 ott 2026; AU e US no)
    pinfo = (((d.get("advertiser") or {}).get("ad_library_page_info")) or {}).get("page_info") or {}
    aaa = d.get("aaa_info") or {}
    breakdown = (eu.get("age_country_gender_reach_breakdown") or []) + (uk.get("age_country_gender_reach_breakdown") or []) + (br.get("age_country_gender_reach_breakdown") or [])
    by_country, by_age, by_gender = {}, {}, {"male": 0, "female": 0, "unknown": 0}
    for c in breakdown:
        tot = 0
        for b in c.get("age_gender_breakdowns") or []:
            m, f, u = b.get("male") or 0, b.get("female") or 0, b.get("unknown") or 0
            tot += m + f + u
            by_age[b.get("age_range")] = by_age.get(b.get("age_range"), 0) + m + f + u
            by_gender["male"] += m; by_gender["female"] += f; by_gender["unknown"] += u
        by_country[c.get("country")] = tot
    return {
        "eu_total_reach": (None if eu.get("eu_total_reach") is None and uk.get("total_reach") is None and br.get("total_reach") is None
                           else (eu.get("eu_total_reach") or 0) + (uk.get("total_reach") or 0) + (br.get("total_reach") or 0)),
        "br_total_reach": br.get("total_reach"),
        "uk_total_reach": uk.get("total_reach"),
        "targets_eu": eu.get("targets_eu") or aaa.get("targets_eu"),
        "gender_audience": eu.get("gender_audience") or uk.get("gender_audience"),
        "age_min": (eu.get("age_audience") or uk.get("age_audience") or {}).get("min"), "age_max": (eu.get("age_audience") or uk.get("age_audience") or {}).get("max"),
        "location_audience": json.dumps((eu.get("location_audience") or []) + (uk.get("location_audience") or []) + (br.get("location_audience") or [])),
        "reach_by_country": json.dumps(by_country), "reach_by_age": json.dumps(by_age), "reach_by_gender": json.dumps(by_gender),
        "payer": ((aaa.get("payer_beneficiary_data") or [{}])[0]).get("payer"),
        "beneficiary": ((aaa.get("payer_beneficiary_data") or [{}])[0]).get("beneficiary"),
        "page": {"page_id": pinfo.get("page_id"), "name": pinfo.get("page_name"), "likes": pinfo.get("likes"),
                 "category": pinfo.get("page_category"), "ig_username": pinfo.get("ig_username"),
                 "ig_followers": pinfo.get("ig_followers"), "verification": pinfo.get("page_verification"),
                 "profile_uri": pinfo.get("page_profile_uri"), "profile_photo": pinfo.get("profile_photo"),
                 "entity_type": pinfo.get("entity_type"), "is_restricted": pinfo.get("page_is_restricted")},
        "raw": d,
    }


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "holior"
    t0 = time.time(); n = 0
    for ad in search(query=q, max_pages=1, on_page=lambda c, p: print("total", c, "page", p)):
        n += 1
        if n <= 3: print(json.dumps({k: ad[k] for k in ("ad_archive_id", "page_name", "domain", "format", "start_date", "collation_count", "total_active_time")}))
    print(n, "ads", f"{time.time()-t0:.1f}s", "doc_ids", doc_ids())


# ---------------- paginazione per finestre di data (solo HTML, niente GraphQL) ----------------
def _in_pausa():
    """Pausa condivisa (data/meta_blocco): dopo un blocco di Meta nessun lettore la interroga per 3 ore."""
    try: return time.time() - float(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "meta_blocco")).read() or 0) < 3 * 3600
    except (OSError, ValueError): return False

def _first_page(query, page_id, country, active, media, since, until, sort=True, platforms=None):
    if _in_pausa(): raise Blocked("pausa-blocco")
    s = session()
    html = s.get_html(_url(query, page_id, country, active, media, since, until, sort, platforms=platforms))
    conn = _extract(html)
    if conn is None:
        LIMITER.soft()
        raise Blocked("no-results-block")
    return conn.get("count") or 0, list(_edges_to_ads(conn.get("edges")))

def search_sliced(query=None, page_id=None, country="ALL", active="all", media="all", start="2019-01-01", end=None,
                  seen=None, on_slice=None, max_requests=400, newest_first=True, gql_fallback=False, workers=None, stats=None, guard=True):
    """Copertura COMPLETA senza cursore GraphQL, "sbucciando" l'archivio dal più recente al più
    vecchio (peel), in parallelo dove possibile.

    Ogni pagina server-rendered dà: il TOTALE della finestra + le 30 ad più recenti. Se il
    totale supera 30, la data più vecchia fra le 30 (d30) è la prossima frontiera: tutto ciò
    che è più nuovo di d30 è già in mano (le 30 sono le più recenti), quindi la fetta seguente
    è [inizio .. d30] e costa 1 richiesta per ~30 ad nuove. Zero fette vuote, zero bisezioni.
    Trucchi: per finestre ≤60 ad l'ordinamento "per rilevanza" restituisce 30 ad diverse (1
    richiesta chiude la finestra); un giorno con >30 ad si spacca per stato (attive/spente)
    e poi per tipo di media (video/image/meme/none: caroselli e DCO stanno negli ultimi due).
    Le partizioni disgiunte deducono il totale della sorella per differenza e saltano le vuote.
    Ogni worker ha la sua identità (cookie/UA); il ritmo verso Meta è unico e adattivo."""
    import queue as _q
    from datetime import date as _d, timedelta as _td
    workers = workers or int(os.environ.get("RADAR_WORKERS", "3"))
    today = _d.today(); end = end or today.isoformat()
    seen = seen if seen is not None else set()
    lock = threading.Lock(); out = _q.Queue(); tasks = _q.PriorityQueue()
    st = {"budget": 0, "pending": 0, "errors": [], "fetched": 0, "lost": 0, "seq": 0, "yield": []}   # yield: nuove ad per richiesta
    done = threading.Event()

    def emit(ads):
        fresh = []
        with lock:
            for a in ads:
                if a["ad_archive_id"] not in seen:
                    seen.add(a["ad_archive_id"]); fresh.append(a)
            st["yield"].append(len(fresh))
            # RENDIMENTO DECRESCENTE: dopo 75 richieste, se le ultime 50 hanno reso meno di
            # 0,8 ad nuove l'una, la coda densa non vale più il tempo: si dichiara il residuo
            if guard and len(st["yield"]) >= 150 and sum(st["yield"][-100:]) < 15:      # esaurimento solo se 100 richieste di fila non portano quasi nulla (prima: 50/<40 → tagliava un terzo dell'archivio)
                st["exhausted"] = True
        for a in fresh: out.put(a)
        return len(fresh)
    def emit_all(ads):
        return emit(ads) or 0   # solo le ad mai viste: le sovrapposizioni non contano come copertura

    def submit(t, prio=0):
        # priorità: 0 = sbucciatura (copertura in ampiezza) · 1 = stato · 2 = media.
        # Così su una pagina che lancia centinaia di ad al giorno il budget va prima
        # all'archivio nel tempo e poi alla coda densa.
        with lock: st["pending"] += 1; st["seq"] += 1; seq = st["seq"]
        tasks.put((prio, seq, t))

    def finish_task():
        with lock:
            st["pending"] -= 1
            if st["pending"] <= 0: done.set()

    def fetch(since, until, med, act, sort=True, cc=None, pls=None):
        with lock:
            if st["budget"] >= max_requests or st.get("exhausted"):
                st["exhausted"] = True; return None
            st["budget"] += 1; k = st["budget"]
        for attempt in range(3):
            try:
                total, ads = _first_page(query, page_id, cc or country, act, med, since, until, sort, platforms=pls)
                with lock: st["fetched"] += 1
                if on_slice: on_slice(since or start, until or end, total, len(ads), k)
                return total, ads
            except Blocked as ex:
                if os.environ.get("RADAR_DEBUG"): print(f"    anomalia {ex} su {since}..{until} {med}/{act} sort={sort} (tentativo {attempt+1})", file=sys.stderr, flush=True)
                if attempt == 2: raise
                if str(ex) == "no-results-block":
                    time.sleep(2.0 if attempt == 0 else 6.0)   # transitorio: riprova con la stessa identità
                else:
                    time.sleep(12 * (attempt + 1)); session(reset=True)

    def expected(group, key):
        """Partizioni DISGIUNTE (stato, media): SOLO l'ultima sorella (group['dep']) deduce il
        proprio totale = padre − somma delle altre; le altre leggono subito.
        None = sorelle ancora in volo; sentinella negativa = non deducibile (una sorella è fallita)."""
        if not group or key != group.get("dep"): return None
        done_others = [k2 for k2 in list(group.get("done", {})) if k2 != key]
        if len(done_others) < group["need"] - 1: return None
        vals = [group["known"].get(k2) for k2 in done_others]
        if any(v is None for v in vals): return -1_000_000
        return group["parent"] - sum(vals)

    def handle(total, ads, since, until, med, act):
        n_ads = len(ads); fresh = emit(ads)
        if total <= 30 or n_ads >= total or n_ads == 0: return
        a = _d.fromisoformat(since) if since else _d.fromisoformat(start)
        b = _d.fromisoformat(until) if until else today
        if total <= 60:
            alt = fetch(since, until, med, act, sort=False)   # ordine "per rilevanza": altre 30
            if alt is not None:
                fresh2 = emit(alt[1])
                if n_ads + fresh2 >= total or len({x["ad_archive_id"] for x in ads} | {x["ad_archive_id"] for x in alt[1]}) >= total: return
        dates = sorted(x["start_date"] for x in ads if x.get("start_date"))
        d30 = _d.fromisoformat(dates[0]) if dates else None
        # PEEL: tutto ciò che è più nuovo di d30 è già nelle 30; la prossima fetta finisce a
        # d30+1 (un giorno di margine: il filtro data di Meta e il nostro start_date UTC non
        # tagliano la mezzanotte nello stesso punto) e deve essere STRETTAMENTE più corta.
        # (la data di Meta può essere AVANTI rispetto al nostro UTC: d30 può cadere prima di a)
        cut = max(d30 + _td(days=1), a + _td(days=1)) if d30 else None
        if cut and cut < b:
            newer = sum(1 for x in dates if _d.fromisoformat(x) > cut)
            if total - n_ads > 0:
                submit((a.isoformat(), cut.isoformat(), med, act, None, None))
            return
        # coda densa: le 30 più recenti stanno negli ultimi 2 giorni (o niente di nuovo).
        # Il resto continua a sbucciarsi; la coda [b-1, b] si spacca in partizioni disgiunte.
        tail = max(a, b - _td(days=1))
        if a < tail:
            submit((a.isoformat(), (tail - _td(days=1)).isoformat(), med, act, None, None))
        since, until = tail.isoformat(), b.isoformat()
        if act == "all":
            grp = {"parent": total, "known": {}, "need": 2, "dep": "N"}
            submit((since, until, med, "active", grp, "A"), 1); submit((since, until, med, "inactive", grp, "N"), 1)
        elif med == "all":
            grp = {"parent": total, "known": {}, "need": 4, "dep": "Z"}
            for key, m in (("V", "video"), ("I", "image"), ("M", "meme"), ("Z", "none")):
                submit((since, until, m, act, grp, key), 2)
        else:
            # foglia satura (stato e media già fissati): ordine "per rilevanza" per altre 30,
            # poi un tentativo col cursore GraphQL; quel che resta è residuo dichiarato
            covered = n_ads
            if total > 60 and total - covered >= 6:
                alt = fetch(since, until, med, act, sort=False)
                if alt is not None: covered += emit_all(alt[1])
            # asse piattaforma: ogni piattaforma dà le sue 30 (+30 per rilevanza). Su un giorno da 80 ad
            # di una pagina grande (Bloomin, Everyday Women's Health: 183 perse) era il buco principale.
            for pl in ("facebook", "instagram", "messenger", "audience_network", "threads"):
                if covered >= total or total - covered < 3: break
                for srt in (True, False):
                    r = fetch(since, until, med, act, sort=srt, pls=[pl])
                    if r is None: break
                    covered += emit_all(r[1])
                    if not r[0] or r[0] <= 30: break
            # ultimo asse disponibile: il paese — solo se manca abbastanza da valerne la spesa
            for cc in ("US", "GB", "CA", "AU", "DE", "FR", "IT", "ES", "NL", "SE"):
                if covered >= total or total - covered < 3 or country != "ALL": break
                r = fetch(since, until, med, act, sort=True, cc=cc)
                if r is None: break
                if r[0] and r[0] > 0:
                    covered += emit_all(r[1])
                    if r[0] > 30:
                        r2 = fetch(since, until, med, act, sort=False, cc=cc)
                        if r2 is not None: covered += emit_all(r2[1])
            if gql_fallback and covered < total and total - covered >= 6 and not st.get("gql_dead"):
                buf = []
                try:
                    for ad in search(query=query, page_id=page_id, country=country, active=act, media=med, since=since, until=until, max_pages=12, retries=1):
                        buf.append(ad)
                except Blocked:
                    st["gql_dead"] = True      # il cursore è in rate-limit: non riprovarlo in questo giro
                if buf: covered += emit_all(buf)
            with lock: st["lost"] += max(0, total - covered)

    def worker():
        while not done.is_set():
            try: prio, _seq, t = tasks.get(timeout=0.4)
            except _q.Empty: continue
            since, until, med, act, grp, key = t
            requeued = False
            try:
                exp = expected(grp, key)
                if exp is None and grp is not None and key == grp.get("dep") and not st.get("exhausted"):
                    with lock: others_waiting = st["pending"] - 1 > 0 and not tasks.empty()
                    if others_waiting:
                        requeued = True; submit(t, prio); time.sleep(0.05)
                        with lock: st["pending"] -= 1          # il re-inserimento non è un task in più
                        continue
                if st.get("exhausted"): continue
                if exp is not None and -1_000_000 < exp <= 0:
                    if grp is not None: grp["known"][key] = 0
                    continue
                res = fetch(since, until, med, act)
                if res is None: continue
                total, ads = res
                if grp is not None: grp["known"][key] = total
                handle(total, ads, since, until, med, act)
            except Exception as ex:
                with lock: st["errors"].append(ex)
            finally:
                if not requeued:
                    if grp is not None: grp.setdefault("done", {})[key] = True
                    finish_task()

    root = fetch(None, None, media, active)      # T + le 30 più recenti, nessun filtro data
    if root is None: return
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, workers))]
    for th in ths: th.start()
    with lock: st["pending"] += 1               # la radice conta come task in corso
    try:
        handle(root[0], root[1], None, None, media, active)
    finally:
        finish_task()
    try:
        while True:
            try:
                yield out.get(timeout=0.3)
            except _q.Empty:
                if done.is_set() and out.empty(): break
    except GeneratorExit:
        with lock: st["exhausted"] = True     # il consumatore ha chiuso: i worker smettono di spendere richieste
        done.set(); raise
    for th in ths: th.join(timeout=1)
    if stats is not None:
        stats.update(exhausted=bool(st.get("exhausted")), lost=st["lost"], errors=len(st["errors"]), requests=st["budget"])
    if on_slice and st["lost"]: on_slice("residuo", "", st["lost"], 0, -1)
    if st["errors"]:
        if on_slice: on_slice("errori", "", len(st["errors"]), 0, -2)
        if st["fetched"] <= 1:
            e = st["errors"][0]; raise e if isinstance(e, Blocked) else Blocked(f"worker:{e!r}")


def sliced_stats():
    return {"gap": LIMITER.gap, "ok": LIMITER.ok, "blocked": LIMITER.blocked}
