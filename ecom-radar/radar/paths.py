#!/usr/bin/env python3
"""Ecom Radar — dove stanno i file. Regola di Chry: i media dei competitor (miniature,
screenshot, storyboard) NON restano sul Mac: vanno su Google Drive. Sul Mac restano
DB e codice. Se il mount di Drive non c'è, si ripiega su data/ (e alla prossima
esecuzione con Drive presente la migrazione sposta tutto).

  MEDIA_ROOT/thumbs/<ad_id>.jpg    miniatura ridotta (≤640 px, JPEG q80)
  MEDIA_ROOT/lp/<lp_id>.jpg        screenshot full-page della landing
  MEDIA_ROOT/frames/<ad_id>.jpg    storyboard 4x2 del video
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVE = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-datevifuocoora@gmail.com/Il mio Drive")
LEGACY = os.path.join(ROOT, "data")


def media_root():
    """Default: locale (data/), miniature ridotte. Drive SOLO se richiesto con RADAR_MEDIA:
    i processi avviati da launchd (server, refresh notturno) non possono leggere
    ~/Library/CloudStorage senza Full Disk Access a python3 (limite TCC di macOS)."""
    env = os.environ.get("RADAR_MEDIA")
    if env:
        try:
            os.makedirs(env, exist_ok=True); os.listdir(env); return env
        except Exception:
            pass
    return LEGACY


MEDIA = media_root()
THUMBS = os.path.join(MEDIA, "thumbs")
LP = os.path.join(MEDIA, "lp")
FRAMES = os.path.join(MEDIA, "frames")
for _d in (THUMBS, LP, FRAMES):
    try: os.makedirs(_d, exist_ok=True)
    except Exception: pass


def shrink(src, dst, max_w=360, quality=55, max_h=None):
    """Riduce un'immagine a miniatura leggera. Ritorna True se scritta.
    max_h: taglia le pagine lunghissime (screenshot di landing da 20.000 px): oltre quell'altezza
    non c'e' piu' niente da leggere in anteprima, e il file passava da 700 KB a ~120 KB."""
    try:
        from PIL import Image
        im = Image.open(src); im.load()
        if im.mode not in ("RGB", "L"): im = im.convert("RGB")
        w, h = im.size
        if w > max_w:
            im = im.resize((max_w, int(h * max_w / w)), Image.LANCZOS); w, h = im.size
        if max_h and h > max_h:
            im = im.crop((0, 0, w, max_h))
        im.save(dst, "JPEG", quality=quality, optimize=True)
        return True
    except Exception:
        return False


def find(kind, name):
    """Percorso di un file media, cercando anche nella posizione legacy (data/)."""
    for base in (MEDIA, LEGACY):
        p = os.path.join(base, kind, name)
        if os.path.exists(p) and os.path.getsize(p) > 200: return p
    return None


def migrate_legacy(log=print, src_root=None):
    """Sposta (riducendo) i file da src_root (default: la posizione non attiva) verso MEDIA."""
    src_root = src_root or (LEGACY if MEDIA != LEGACY else os.path.join(DRIVE, "Ecom Radar", "media"))
    # Drive si tocca SOLO se Chry l'ha chiesto con RADAR_MEDIA: sotto launchd macOS nega la lettura di
    # ~/Library/CloudStorage e l'eccezione faceva saltare l'intera rilettura notturna di ogni brand.
    if src_root.startswith(DRIVE) and not os.environ.get("RADAR_MEDIA"): return 0
    try:
        if src_root == MEDIA or not os.path.isdir(src_root): return 0
    except OSError:
        return 0
    n = 0
    for kind, do_shrink in (("thumbs", True), ("lp", False), ("frames", False)):
        src_dir = os.path.join(src_root, kind)
        if not os.path.isdir(src_dir): continue
        try: nomi = os.listdir(src_dir)
        except OSError: continue
        for f in nomi:
            s = os.path.join(src_dir, f); d = os.path.join(MEDIA, kind, f)
            if not os.path.isfile(s): continue
            try:
                if os.path.exists(d) and os.path.getsize(d) > 200:
                    os.remove(s); continue
                if do_shrink and shrink(s, d):
                    os.remove(s)
                else:
                    os.replace(s, d)
                n += 1
            except Exception as ex:
                log(f"  migrazione {f}: {ex}")
    if n: log(f"MEDIA: {n} file spostati da {src_root} a {MEDIA}")
    return n


if __name__ == "__main__":
    print("MEDIA_ROOT =", MEDIA); migrate_legacy()
