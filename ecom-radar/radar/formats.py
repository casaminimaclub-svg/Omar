"""Tassonomia dei formati di Ecom Radar: video · statica · native (i caroselli non sono un formato).

Regola (dai mentori nel vault — Glenn Nieuwenhuis, Anthony Camacho, Alessio Cordeddu):
  - video   → c'è un video.
  - native  → immagine "da rullino" + primary text lungo (MSL: 1.000-4.000 parole; soglia operativa 500 caratteri),
              tipica delle pagine alias/persona. "Immagine + primary text lungo" è il filtro di Glenn.
  - statica → immagine promozionale con copy breve (Cordeddu: 29 concept, testo in immagine, offerta).
Un carosello/DCO si classifica dalla sua prima card (video → video, immagine → native/statica dal copy).
"""
import json, re

# Tratto 4 di Glenn: "non 10 frasi, una storia che tira avanti come un libro".
# La soglia va letta RISPETTO alle ad normali, non in assoluto: nell'archivio il corpo mediano
# di un'ad video e' 555 caratteri. 500 non era "lungo", era la norma — ed e' per questo che
# meta' archivio finiva fra le native. 2.000 caratteri sono ~350 parole: quattro volte un'ad
# normale, e il pavimento dell'MSL di Camacho (1.000-4.000 parole).
NATIVE_MIN_CHARS = 2000

# --- Cosa distingue una native da una statica (Glenn Nieuwenhuis, tratto 3) --------------------
# La native e' una FOTO: "deve sembrare la foto che una signora 50+ posta sul suo profilo".
# La statica e' una creativita' DISEGNATA (Cordeddu): prodotto, titolo in display, callout, offerta.
# Il segnale leggibile dai dati e' il testo dentro l'immagine (OCR). Non basta "c'e' del testo":
# molte native vere hanno una barra di testo sopra la foto ("Read my story, it's in the caption").
# Quindi si guardano tre cose diverse, non una sola.

# 1. Lingua da offerta/creativita' commerciale: se sta DENTRO l'immagine, e' disegnata.
PROMO_RX = re.compile(r"""(?ix)
    (sale|off|discount|save|free|bogo|deal|offer|coupon|promo|voucher|
       money[-\s]?back|guarantee|warranty|refund|garanzia|sconto|offerta|spedizione\s+gratis|
       buy\s+\w+|get\s+\d|shop\s+now|order\s+now|claim\s+(yours|now)|add\s+to\s+cart|
       limited\s+time|today\s+only|ends\s+(tonight|today|soon)|last\s+chance|while\s+supplies|
       bundle|best\s?seller|reviews?|five\s+star|rated|clinically\s+(proven|dosed|tested)|
       doctor\s+(recommended|approved|formulated)|money\s+back)\b
  | \d{1,3}\s?% | [$€£]\s?\d | \b\d+\s*(mg|ml|caps|capsule|bags?)\b""")

# 2. Quantita' di testo: una statica porta un impianto testuale, la native al massimo una riga o due.
OCR_MAX_NATIVE = 120

# 3. Titolo in maiuscolo: il display type tutto maiuscolo e' il marchio della creativita' disegnata.
#    Una native scritta a mano non urla in caps.
CAPS_RX = re.compile(r"[A-ZÀ-Ý][A-ZÀ-Ý0-9'\u2019 ,.!?:-]{14,}")


def promo_graphic(ocr):
    """True se il testo nell'immagine e' quello di una creativita' disegnata (offerta/badge/prezzo)."""
    o = (ocr or "").strip()
    if len(o) < 20: return False
    return bool(PROMO_RX.search(o))


def disegnata(ocr, marchi=None):
    """True se l'immagine e' una creativita' costruita, non una foto con una didascalia sopra.

    `marchi`: parole del brand (nome, dominio, prodotto). Se il MARCHIO sta dentro l'immagine
    la creativita' e' disegnata per definizione: una native non si firma — il suo vantaggio e'
    proprio non sembrare pubblicita' (Glenn, "il vantaggio algoritmico")."""
    o = (ocr or "").strip()
    if len(o) < 20: return False
    if marchi:
        bassa = o.lower()
        if any(m and len(m) >= 4 and m in bassa for m in marchi): return True
    if promo_graphic(o): return True          # parla di offerta, prezzo, recensioni: e' pubblicita' disegnata
    # il rumore di una foto dà "parole" inventate: contano solo parole vere (dizionario, 5+ lettere)
    import thumbs as _T
    vere = [w for w in o.split() if len(w) >= 5 and w.lower().strip("'’") in _T._dizionario()]
    return len(vere) >= 3


# Tratto 2 di Glenn: la native e' scritta in prima persona, dal punto di vista di una persona.
PRIMA_PERSONA = re.compile(r"""(?ix)(?:^|[\s"'(\u201c])(i|i'm|i've|i'd|my|me|mine|myself|
    io|ho|sono|mio|mia|miei|mie|mi)\b""")


def voce_personale(body):
    return bool(PRIMA_PERSONA.search((body or "")[:800]))


def classify(ad, marchi=None, pagina_persona=None):
    """ad: dict con format/video_url/media/body/display_format. Ritorna 'video' | 'native' | 'statica' | 'ignoto'."""
    if ad.get("format") == "video" or ad.get("video_url"):
        return "video"
    media = ad.get("media") or []
    if isinstance(media, str):
        try: media = json.loads(media)
        except Exception: media = []
    if any((m or {}).get("kind") == "video" for m in media):
        return "video"
    body = (ad.get("body") or "").strip()
    ocr = (ad.get("ocr") or "").strip()
    # Meta a volte non restituisce nessuna creativita' (display_format UNKNOWN, niente immagine ne' media):
    # senza immagine non si puo' dire se e' native o statica. Meglio dichiararlo che tirare a indovinare.
    if not ad.get("image_url") and not media and (ad.get("display_format") or "").upper() == "UNKNOWN":
        return "ignoto"
    # L'immagine viene PRIMA della lunghezza del copy: una creativita' disegnata resta una statica
    # anche con 3.000 parole di primary text. (Era l'errore: bastava il copy lungo per farla native.)
    # Per dire "native" servono prove positive, non l'assenza di prove: e' l'errore che aveva
    # reso native meta' archivio (bastava un copy lungo). I tratti di Glenn, nell'ordine:
    #  3. la foto non e' disegnata e non porta il marchio
    #  4. il copy e' lungo
    #  1-2. la pagina e' una persona, oppure il copy parla in prima persona
    if disegnata(ocr, marchi): return "statica"
    if len(body) >= NATIVE_MIN_CHARS and (pagina_persona or voce_personale(body)): return "native"
    if len(body) >= 1000 and pagina_persona and voce_personale(body) and len(ocr) < 20: return "native"
    # foto vera (immagine LETTA e senza scritte) + copy lungo = native, anche se il copy non dice "io"
    if ad.get("ocr_done") and len(ocr) < 20 and len(body) >= 1000: return "native"
    return "statica"


def migrate(c, log=print, chunk=300):
    """Aggiunge/riempie la colonna fmt su tutte le ad (solo le righe che cambiano, a lotti brevi)."""
    try: c.execute("ALTER TABLE ads ADD COLUMN fmt TEXT")
    except Exception: pass
    c.commit()
    c.execute("CREATE INDEX IF NOT EXISTS idx_ads_fmt ON ads(brand_id, fmt)"); c.commit()
    marchi = {}
    for b in c.execute("SELECT id, name, domain FROM brands").fetchall():
        m = {(b["name"] or "").lower()}
        d = (b["domain"] or "").lower()
        if d: m.add(d.split(".")[0])
        marchi[b["id"]] = {x for x in m if x}
    rows = c.execute("SELECT ad_archive_id, brand_id, page_name, format, video_url, media, body, ocr, ocr_done, fmt, image_url, display_format FROM ads").fetchall()
    n = 0
    for i, r in enumerate(rows, 1):
        pp = None
        if r["brand_id"] in marchi:
            pn = (r["page_name"] or "").lower()
            pp = not any(m and m in pn for m in marchi[r["brand_id"]])
        f = classify(dict(r), marchi.get(r["brand_id"]), pp)
        if f != r["fmt"]:
            c.execute("UPDATE ads SET fmt=? WHERE ad_archive_id=?", (f, r["ad_archive_id"])); n += 1
            if n % chunk == 0: c.commit()
    c.commit()
    log(f"FORMATI: {n} ad riclassificate su {len(rows)}")
    return n


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import db as DB
    c = DB.conn(); migrate(c); c.close()
