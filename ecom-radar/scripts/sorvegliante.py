"""Sorvegliante di Ecom Radar (20 nov 2026, Chry: «metti qualcuno che controlla e risolve, non devo dirtelo io»).
Gira ogni 15 minuti (launchd com.utente.ecom-radar.sorvegliante). Controlla e RISOLVE da solo:
- server 8772 giù → lo riavvia;
- ripristino4 morto prima di «TUTTO FINITO» → lo rilancia;
- un lettore Meta (pagine_browser/top20/paesi/discover) fermo da oltre 2 ore → lo chiude, la coda va avanti;
- un brand nuovo con script morto prima di FINITO → lo rilancia;
- rete assente / CPU calda → lo scrive.
Ogni giro: una riga in data/sorvegliante.log, stato leggibile in data/STATO.md. Notifica macOS solo sugli allarmi."""
import os, subprocess, sqlite3, time, re, urllib.request
R = "__HOME__/ecom-radar"; os.chdir(R)
LOG = f"{R}/data/sorvegliante.log"; fatti = []; allarmi = []

def sh(cmd): return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
def lancia(cmd): subprocess.Popen(f"nohup {cmd} >/dev/null 2>&1 &", shell=True, cwd=R, start_new_session=True)
def etime_s(e):  # [[dd-]hh:]mm:ss
    d, _, e = e.rpartition("-"); p = [int(x) for x in e.split(":")]
    while len(p) < 3: p.insert(0, 0)
    return (int(d) if d else 0) * 86400 + p[0] * 3600 + p[1] * 60 + p[2]

# 0. browser di Playwright (21 nov: la cache è stata svuotata e per un giorno nessuna lettura ha funzionato)
import glob
if not glob.glob("__HOME__/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"):
    sh("/usr/bin/python3 -m playwright install chromium-headless-shell"); fatti.append("browser Playwright mancante: reinstallato")

# 1. server
try: urllib.request.urlopen("http://localhost:8772/api/brands", timeout=15)
except Exception:
    sh(f"launchctl kickstart -k gui/{os.getuid()}/com.utente.ecom-radar"); fatti.append("server riavviato")

# 2. rete
rete = sh("curl -s -m 10 -o /dev/null -w '%{http_code}' https://www.facebook.com").strip()
if rete in ("", "000"): allarmi.append("rete assente (i giri aspettano da soli)")

# 3. lettori Meta bloccati: python che legge Meta da oltre 2 ore
for line in sh("ps -Ao pid,etime,command").splitlines()[1:]:
    m = re.match(r"\s*(\d+)\s+(\S+)\s+(.*)", line)
    if not m: continue
    pid, et, cmd = int(m[1]), etime_s(m[2]), m[3]
    if cmd.startswith("lockf") or "Python" not in cmd and "python3" not in cmd: continue
    if re.search(r"scripts/(pagine_browser|top20|paesi)\.py|B\.discover", cmd) and et > 7200:
        os.kill(pid, 15); fatti.append(f"chiuso lettore fermo da {et//60} min: {cmd[-60:]}")

# 4. ripristino
r3 = open(f"{R}/data/ripristino3.log").read() if os.path.exists(f"{R}/data/ripristino3.log") else ""
if "TUTTO FINITO" not in r3 and not sh("pgrep -f scripts/ripristino4.sh").strip():
    lancia("/bin/zsh scripts/ripristino4.sh"); fatti.append("ripristino4 era morto: rilanciato")

# 4b. lavoro continuo (Chry 21 nov): finito il ripristino, il giro riparte appena finisce, sempre, finché il Mac è acceso
if "TUTTO FINITO" in r3 and not sh("pgrep -f 'scripts/(giro|ripristino4|nuovo_brand)'").strip():
    lancia("/bin/zsh scripts/giro.sh"); fatti.append("giro ripartito")

# 5. brand nuovi
c = sqlite3.connect(f"{R}/data/radar.db", timeout=30)
for (bid,) in c.execute("SELECT id FROM brands WHERE status='new'").fetchall():
    f = f"{R}/data/nuovo_{bid}.log"
    if not os.path.exists(f) or "FINITO" in open(f).read(): continue
    if not sh(f"pgrep -f 'nuovo_brand.sh {bid}$'").strip():
        lancia(f"/bin/zsh scripts/nuovo_brand.sh {bid}"); fatti.append(f"brand {bid}: lettura rilanciata")

# 6. temperatura
try:
    t = float(sh(f"{R}/tools/temp").strip() or 0)
    if t >= 60: allarmi.append(f"CPU calda ({t:.0f} sul sensore, ~{t+20:.0f}°C)")
except Exception: t = 0

# 7. stato
righe = c.execute("""SELECT b.name, COUNT(a.ad_archive_id), SUM(a.is_active), SUM(a.lib_rank IS NOT NULL)
                     FROM brands b LEFT JOIN ads a ON a.brand_id=b.id GROUP BY b.id ORDER BY b.id""").fetchall()
fase = (re.findall(r"== (ATTIVE|ARCHIVIO) brand (\d+)", r3) or [("—", "")])[-1]
ora = time.strftime("%d/%m %H:%M")
md = [f"# Stato Ecom Radar — {ora}", "", f"Ripristino: fase {fase[0]}, brand {fase[1]}", ""]
if fatti: md += ["Risolto da solo:"] + [f"- {x}" for x in fatti] + [""]
if allarmi: md += ["ALLARMI:"] + [f"- {x}" for x in allarmi] + [""]
md += ["| brand | ad | attive | ordine Meta |", "|---|---|---|---|"] + [f"| {n} | {a} | {s or 0} | {'sì' if r else 'no'} |" for n, a, s, r in righe]
open(f"{R}/data/STATO.md", "w").write("\n".join(md) + "\n")
with open(LOG, "a") as L:
    L.write(f"{ora} fase {fase[0]} {fase[1]} · {'; '.join(fatti) or 'tutto regolare'}{' · ALLARME ' + '; '.join(allarmi) if allarmi else ''}\n")
if allarmi or fatti:
    msg = "; ".join(allarmi + fatti).replace('"', "'")[:200]
    sh(f"osascript -e 'display notification \"{msg}\" with title \"Ecom Radar\"'")
