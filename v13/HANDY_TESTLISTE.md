# Handy-Testliste (Redmi, Termux) — Stand 2026-10-21

Reihenfolge = Wichtigkeit. Alles bleibt SHADOW: Es wird nichts eingeschaltet, keine Lernrechte vergeben.
Vor jedem Test: Handy ans Ladegerät, andere Apps zu, laufenden V13-Chat mit `:shutdown` beenden.
Ergebnisdatei (ZIP oder JSON) danach einfach hier im Projekt hochladen, den Rest mache ich.

## 1. Werkzeug-Vorhersage (fertiges Paket, wichtigster Test)
- Datei: `export/V13-Werkzeug-Handy-20261020.zip` aus dem Projekt in „Downloads“ speichern.
- Anleitung Schritt für Schritt: `WERKZEUG_ANLEITUNG.txt` im ZIP. Kurz:
  ```
  termux-setup-storage
  pkg install -y unzip
  mkdir -p ~/v13-werkzeug
  unzip -o ~/storage/downloads/V13-Werkzeug-Handy-20261020.zip -d ~/v13-werkzeug
  cd ~/v13-werkzeug/V13-Phone
  bash WERKZEUG_TESTEN.sh
  ```
- Dauer: geschätzt 30–90 min (beim ersten Mal plus Einrichtung, ca. 0,9 GB Download, WLAN an).
- Hochladen: `V13-Werkzeug-Ergebnis-*.zip` aus Downloads.
- Optional danach über Nacht: `bash WERKZEUG_TESTEN.sh voll`.
- Was wir lernen: Läuft die Werkzeug-Vorhersage auf dem echten Handy, wie schnell, wie viel RAM? Erst danach darf sie aus SHADOW raus.

## 2. RAM-Messung aller drei Modelle (WP-R, „braucht AGI 8 GB?“)
Im selben Ordner wie Test 1, nachdem V13 eingerichtet ist:
```
cd ~/v13-werkzeug/V13-Phone
python scripts/ram_budget_bench.py --binary ~/v13/bin/llama-server --models-dir ~/v13/models \
  --out ~/storage/downloads/ram-budget-redmi.json --scenarios single,variants,combo
```
- Hochladen: `ram-budget-redmi.json`.
- Was wir lernen: Cloud sagt C3+B1+B2 passen in ~2 GB (mit Repack) bzw. ~1 GB (ohne). Das Handy entscheidet, welche Variante gewinnt.

## 3. Gemeinsamer Selbsttest (Kurzlauf)
```
cd ~/v13-werkzeug/V13-Phone
bash TESTEN.sh --quick
```
- Hochladen: den neuesten Ordner `~/v13/exports/acceptance-<Zeit>` als ZIP (oder Screenshot der Zusammenfassung, falls Zippen umständlich ist).
- Was wir lernen: Laufen alle Bausteine auf dem Handy, nicht nur in der Cloud?

## 4. STEP2 auf dem Handy (lang, nur wenn 1–3 durch sind)
Kommt mit dem nächsten Handy-Paket (enthält die neuen Schalter vom 20./21.10.: Zitat als Zeiger + Eignungs-Werkzeug).
Noch nicht starten; ich sage Bescheid, sobald das Paket liegt.

## Was ich parallel weiterbaue
Eignungs-Werkzeug im echten Antwortpfad (Messung läuft), danach die nächsten offenen Pakete aus der ROADMAP.
