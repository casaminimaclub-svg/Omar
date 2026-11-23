"""Guardia del piano Claude: i passaggi che chiamano `claude -p` (analisi creativa, dossier, digest)
consumano la finestra di 5 ore dell'abbonamento. Sopra la soglia si saltano e si riprendono al giro dopo."""
import json, os, subprocess, time

_cache = {"t": 0, "v": None}


def usage():
    """Percentuale usata della finestra 5 ore (None se non leggibile). Cache 2 minuti."""
    if time.time() - _cache["t"] < 120: return _cache["v"]
    v = None
    try:
        out = subprocess.run([os.path.expanduser("~/bin/plan-usage"), "--json"], capture_output=True, text=True, timeout=25).stdout
        j = json.loads(out.strip().splitlines()[-1]); v = float((j.get("five_hour") or {}).get("utilization") or 0)
    except Exception:
        pass
    _cache.update(t=time.time(), v=v); return v


def allow_claude(log=print, what="Claude"):
    mx = float(os.environ.get("RADAR_CLAUDE_MAX", "35"))   # tetto di Chry per il lavoro pesante in automatico
    u = usage()
    if u is not None and u >= mx:
        log(f"  {what}: piano al {u:.0f}% (soglia {mx:.0f}%), salto per non consumare la finestra di Chry"); return False
    return True
