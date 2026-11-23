"""ads.noprev = 1 per le ad senza anteprima che Meta ha tolto dall'Ad Library (non viste da 3 giorni):
la loro immagine non è più recuperabile. La bacheca le nasconde di default (filtro "anche senza anteprima")."""
import os, sys, sqlite3
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, R)
from radar import paths as P
c = sqlite3.connect(os.path.join(R, "data", "radar.db"), timeout=300)
try: c.execute("ALTER TABLE ads ADD COLUMN noprev INTEGER")
except Exception: pass
have = set()
for b in (P.MEDIA, P.LEGACY):
    d = os.path.join(b, "thumbs")
    if os.path.isdir(d): have |= {f[:-4] for f in os.listdir(d)}
# "tolta da Meta" = assente dall'ULTIMA lettura del suo brand (non "non vista da 3 giorni": un brand non
# riletto da una settimana avrebbe perso tutte le anteprime mancanti, 322.000 ad il 4 nov)
import datetime as _dt
ultima = {b: m for b, m in c.execute("SELECT brand_id, MAX(last_seen) FROM ads WHERE brand_id IS NOT NULL GROUP BY brand_id")}
INTERI = {r[0] for r in c.execute("SELECT id FROM brands WHERE pinned=1")}
su, giu = [], []
for aid, ls, np_, bid, act in c.execute("SELECT ad_archive_id, last_seen, noprev, brand_id, is_active FROM ads"):
    soglia = ultima.get(bid)
    soglia = (_dt.date.fromisoformat(soglia[:10]) - _dt.timedelta(days=2)).isoformat() if soglia else ""
    # solo per i brand riletti PER INTERO (attive e passate, lettura via browser): per gli altri il giro
    # quotidiano rilegge solo le attive e "non vista" non vuol dire "tolta da Meta"
    v = 1 if (bid in INTERI and aid not in have and not act and (ls or "") < soglia) else 0
    if v != (np_ or 0): (su if v else giu).append(aid)
for val, ids in ((1, su), (0, giu)):
    for i in range(0, len(ids), 500):
        ch = ids[i:i+500]; c.execute(f"UPDATE ads SET noprev=? WHERE ad_archive_id IN ({','.join('?'*len(ch))})", [val] + ch); c.commit()
print("nascoste", c.execute("SELECT COUNT(*) FROM ads WHERE noprev=1").fetchone()[0], "· cambiate ora", len(su) + len(giu))
