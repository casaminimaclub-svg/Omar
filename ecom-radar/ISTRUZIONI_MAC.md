# Ecom Radar sul Mac: installazione in 3 passi

È il kit di Chry, installato seguendo `kit-docs/LEGGIMI_PER_CLAUDE.md` alla lettera.

## 1. Scarica ed estrai
Scarica `ecom-radar-mac.zip` e fai doppio clic: nei Download compare la cartella `ecom-radar`.

## 2. Lancia l'installazione
Apri **Terminale** (Spotlight → «Terminale») e incolla:

```
zsh ~/Downloads/ecom-radar/install_mac.sh
```

Lo script fa tutti i passi del kit, da solo:
1. copia il codice in `~/ecom-radar`;
2. sostituisce i segnaposto (`__HOME__`, `__MENTORI__`);
3. installa Playwright + Chromium, e se c'è Homebrew anche tesseract (OCR) e whisper (transcript);
4. avvia il server sempre acceso: http://localhost:8772;
5. installa il comando `radar`;
6. e 8. aggiunge **Heusom come brand di prova**, ne fa la lettura completa e il controllo (ad, pagine, anteprime, reach EU, landing, score). **Solo se la prova passa** aggiunge gli altri brand di `brands.txt`, uno alla volta;
7. attiva il sorvegliante (ogni 15 minuti), il giro notturno (alle 02:00) e il freno termico.

Ti può chiedere la password del Mac (per Homebrew). La prima lettura dei brand richiede **ore**: è normale, Meta va letta piano per non bloccare l'IP.

## 3. Lascia il Mac acceso
Collegato alla corrente, con lo stop automatico disattivato:
Impostazioni di Sistema → Batteria (o Risparmio energia) → **Impedisci lo stop automatico quando lo schermo è spento**.

## Controllare come va
```
tail -f ~/ecom-radar/data/brand_iniziali.log     # avanzamento brand
cat ~/ecom-radar/data/SMOKE.md                   # esito della prova su Heusom
cat ~/ecom-radar/data/STATO.md                   # stato scritto dal sorvegliante
```

## Mercati
USA (prioritario), Italia e tutta l'Europa: UE27 + Regno Unito, Svizzera e Norvegia (`scripts/paesi.py`).
La reach esiste solo per l'UE (più UK e Brasile): per gli USA la classifica è l'ordine della Ad Library.

## Brand
In `brands.txt` ci sono tutti i brand citati nel kit. Il kit non contiene l'archivio di Chry, quindi non c'è la sua lista completa.
Per aggiungerne uno: `radar add https://dominio.com`, poi `zsh ~/ecom-radar/scripts/nuovo_brand.sh <id>`.
Pureveen e Metabolae non hanno un dominio nel kit: lo script prova le varianti e, se nessuna risponde, li salta (lo scrive nel log).
