#!/usr/bin/env python3
"""Ecom Radar — transcript dei video con whisper locale (whisper-cli, modello in ~/ad-spy/models).
Video scaricato in temp → audio 16 kHz → whisper → testo nel DB (+FTS) → file cancellati.

  run("<ad_archive_id>")          una singola ad
  run("brand:<id>", limit=N)      i top N video del brand senza transcript (per score)
"""
import json, os, subprocess, sys, tempfile, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

MODELS = [os.path.expanduser("~/ad-spy/models/ggml-large-v3-turbo.bin"), os.path.expanduser("~/ad-spy/models/ggml-small.bin")]
WHISPER = "/opt/homebrew/bin/whisper-cli"


def model():
    for m in MODELS:
        if os.path.exists(m): return m
    raise RuntimeError("nessun modello whisper in ~/ad-spy/models")


def transcribe_one(aid, log=print):
    c = DB.conn(); a = c.execute("SELECT video_url, media, page_id FROM ads WHERE ad_archive_id=?", (aid,)).fetchone(); c.close()
    if not a: return None
    urls = [a["video_url"]] + [m.get("hd") or m.get("sd") for m in json.loads(a["media"] or "[]") if m.get("kind") == "video"]
    urls = [u for u in urls if u]
    if not urls: log(f"  {aid}: nessun video"); return None
    with tempfile.TemporaryDirectory() as td:
        mp4 = os.path.join(td, "v.mp4"); wav = os.path.join(td, "a.wav")
        ok = False
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=60).read()
                if len(data) > 10000: open(mp4, "wb").write(data); ok = True; break
            except Exception as ex:
                log(f"  {aid}: download fallito ({str(ex)[:60]})")
        if not ok:
            # URL scaduto: rinfresca dalla library
            try:
                import meta_lib as M
                for ad in M.search(page_id=a["page_id"], country="ALL", active="all", max_pages=4):
                    if ad["ad_archive_id"] == aid and ad["video_url"]:
                        c = DB.conn(); c.execute("UPDATE ads SET video_url=?, image_url=?, media=? WHERE ad_archive_id=?", (ad["video_url"], ad["image_url"], json.dumps(ad["media"]), aid)); c.commit(); c.close()
                        data = urllib.request.urlopen(urllib.request.Request(ad["video_url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
                        open(mp4, "wb").write(data); ok = True; break
            except Exception as ex:
                log(f"  {aid}: refresh URL fallito ({ex})")
        if not ok: return None
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp4, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
        # storyboard: 8 fotogrammi equidistanti in una striscia 4x2 (data/frames/<id>.jpg)
        try:
            import paths as P; frames_dir = P.FRAMES; os.makedirs(frames_dir, exist_ok=True)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4], capture_output=True, text=True).stdout.strip() or 0)
            step = max(0.5, dur / 8.5)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp4, "-vf", f"fps=1/{step:.3f},scale=360:-2,tile=4x2", "-frames:v", "1", "-q:v", "5", os.path.join(frames_dir, f"{aid}.jpg")], check=True, timeout=120)
            c0 = DB.conn(); c0.execute("UPDATE ads SET storyboard=? WHERE ad_archive_id=?", (f"frames/{aid}.jpg", aid)); c0.commit(); c0.close()
        except Exception as ex:
            log(f"  {aid}: storyboard non riuscito ({str(ex)[:60]})")
        out = os.path.join(td, "t")
        subprocess.run([WHISPER, "-m", model(), "-f", wav, "-l", "auto", "-otxt", "-of", out, "-np"], check=True, capture_output=True)
        txt = open(out + ".txt", encoding="utf-8", errors="replace").read().strip()
    txt = " ".join(txt.split())
    import sqlite3, time as _t
    for attempt in range(6):
        try:
            c = DB.conn(); c.execute("UPDATE ads SET transcript=? WHERE ad_archive_id=?", (txt, aid)); DB.refresh_fts(c, aid); c.commit(); c.close(); break
        except sqlite3.OperationalError:
            _t.sleep(15)
    log(f"  {aid}: {len(txt)} caratteri")
    return txt


def run(arg, limit=25, log=print):
    # RAM: whisper large occupa ~1,7 GB; non partire se il Mac è già in affanno (Chry: "non intasarmi la memoria")
    try:
        import subprocess as _sp
        free_pages = int([l for l in _sp.run(["vm_stat"], capture_output=True, text=True).stdout.splitlines() if "Pages free" in l][0].split()[-1].rstrip("."))
        if free_pages * 4096 < 1_500_000_000: log("TRANSCRIBE: RAM libera sotto 1,5 GB, rimando"); return 0
    except Exception: pass
    c0 = DB.conn()
    try: c0.execute("ALTER TABLE ads ADD COLUMN storyboard TEXT"); c0.commit()
    except Exception: pass
    c0.close()
    if str(arg).startswith("brand:"):
        bid = int(str(arg).split(":")[1]); c = DB.conn()
        ids = [r["ad_archive_id"] for r in c.execute("SELECT ad_archive_id FROM ads WHERE brand_id=? AND format='video' AND (transcript IS NULL OR transcript='') ORDER BY is_active DESC, score DESC LIMIT ?", (bid, limit))]
        c.close(); n = 0
        for aid in ids:
            if transcribe_one(aid, log): n += 1
        log(f"TRANSCRIBE brand {bid}: {n}/{len(ids)}"); return n
    return transcribe_one(str(arg), log)


if __name__ == "__main__":
    run(sys.argv[1], limit=int(sys.argv[2]) if len(sys.argv) > 2 else 25)
