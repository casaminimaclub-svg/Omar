"""Chiamata a Claude via CLI: sempre Haiku 5.5 (scelta di Chry, 19 nov: meno token).

Regola imparata la notte dell'8 settembre: un errore di RETE non è un modello mancante.
Prima bastava un ENOTFOUND per marcare tutti i modelli come non disponibili, e da lì in poi
ogni chiamata tornava vuota in 0 secondi: due ore di lavoro registrate come riuscite senza
che nulla venisse scritto. Ora la rete si aspetta e si ritenta; si esclude un modello solo
quando è davvero il modello a non esserci."""
import os, re, subprocess, time

BIN = next((p for p in (os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"), "/opt/homebrew/bin/claude", "/usr/local/bin/claude") if os.path.exists(p)), None)
ORDER = ["claude-haiku-5-5", "haiku"]   # 19 nov: Chry vuole il minimo di token, sempre Haiku 5.5
_ok = {}

# errori che passano: aspettare e riprovare li risolve
TRANSIENT = re.compile(r"(?i)ENOTFOUND|ECONNRESET|ETIMEDOUT|EAI_AGAIN|socket hang up|fetch failed|"
                       r"can'?t reach the api|network|timeout|502|503|504|overloaded|rate limit|too many requests")
NET_RETRIES = 6          # ~15 minuti di attesa complessiva
NET_WAIT = 45


def online(timeout=6):
    """La rete c'è? (una risposta qualsiasi dal server di Anthropic basta)"""
    try:
        import urllib.request
        urllib.request.urlopen("https://api.anthropic.com/v1/models", timeout=timeout)
        return True
    except Exception as ex:
        return not isinstance(ex, (OSError,)) or getattr(ex, "code", None) is not None


def wait_online(log=print, tries=20, wait=60):
    """Aspetta che la rete torni. False se non torna: chi chiama deve fermarsi, non correre a vuoto."""
    for i in range(tries):
        if online(): return True
        log(f"  rete assente, aspetto {wait}s ({i+1}/{tries})"); time.sleep(wait)
    return False


def ask(prompt, prefer=None, timeout=900, log=print):
    """Ritorna (testo, modello). ('', None) solo dopo aver davvero esaurito modelli e attese."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    if not BIN:
        log("  claude CLI non trovata"); return "", None
    for m in ([prefer] if prefer else []) + ORDER:
        if _ok.get(m) is False: continue
        for attempt in range(NET_RETRIES):
            try:
                p = subprocess.run([BIN, "-p", prompt, "--model", m, "--output-format", "text"],
                                   capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL, env=env)
            except subprocess.TimeoutExpired:
                log(f"  {m}: timeout dopo {timeout}s"); break
            out = (p.stdout or "").strip()
            err = (out or p.stderr or "")[:200]
            if p.returncode == 0 and out and not out.startswith("API Error"):
                _ok[m] = True; return out, m
            if TRANSIENT.search(err):                       # rete o server: si aspetta, il modello resta buono
                log(f"  {m}: problema passeggero ({err[:90]}) → riprovo fra {NET_WAIT}s ({attempt+1}/{NET_RETRIES})")
                time.sleep(NET_WAIT); continue
            _ok[m] = False; log(f"  modello {m} non disponibile: {err[:120]}")
            break
        else:
            log(f"  {m}: rete non tornata dopo {NET_RETRIES} tentativi")
    return "", None
