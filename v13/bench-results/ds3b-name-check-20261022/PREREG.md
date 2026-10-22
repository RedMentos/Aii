# WP-DS3b Vorregistrierung (2026-10-22, vor dem Lesen der frischen Läufe)

Folgepaket zu WP-DS3 (NOT_SUPPORTED: Restfehler nach dem Rechenwerkzeug sind meist *selbstsicher falsche Namen*).
Skript `code/scripts/ds3b_name_check.py` (sha256 in `PREREG.json`), Tests `code/tests/test_ds3b_name_check.py`.

**Was neu ist**
- (a) **Namen-Unsicherheit:** kleinste Token-Wahrscheinlichkeit über die Namen in der Antwort (Städte, Personen, Monate: groß geschriebene Wörter, die im Aufgabentext mitten im Satz stehen), zusammen mit der Ziffern-Unsicherheit aus DS3; AG9-Kalibrierer je Bestandteil, Schwelle auf den Entwicklungsdaten gewählt (0,5).
- (b) **Feste Gegenprobe Antwort ↔ Werkzeug** (nichts gelernt, keine Schwelle), nur wenn das Werkzeug gerechnet hat: Die Antwort muss das Rechenergebnis enthalten; bei „größter minus kleinster“ muss der Satzteil mit „most/largest/highest …“ den vom Rezept bestimmten größten Posten nennen; fragt die Aufgabe „ist die Zahl richtig?“ und widerspricht das Rezept der genannten Zahl, muss die Antwort das sagen. Schlägt die Probe fehl, sagt V13 „unsicher“.
- Politik **ds3b** (Hauptpolitik) = „unsicher“ wenn Gegenprobe fehlschlägt ODER Namen/Ziffern-Unsicherheit zu hoch.
- Nur berichtet: `check` allein, `check_repair` (bei Fehlschlag feste Antwort aus dem Werkzeugergebnis), `check_full` (auch „least“-Stadt und Name–Zahl-Paare), **strenge Wertung** (auch eine falsche „least“-Stadt oder falsche Zahl zu einer Stadt zählt als falsch; die Bench-Regex prüft nur größte Stadt + Differenz).

**Daten.** Echte C3 LFM2.5-350M, Laufzeit Branch hmopsm, Cloud-CPU, Aufnahme mit Token-Wahrscheinlichkeiten. Entwicklung: neue Seeds 41 + 43 (`dev/`). Die Wortlaute der Gegenprobe wurden an den bereits benutzten R4-Läufen 7/11/17/31/37 geschrieben (nicht an 41/43 nachgestellt). Frisch: Seeds **47, 53, 59** (180 Aufgaben); deren Aufnahme lief beim Schreiben, die Dateien wurden vorher nicht gelesen. Einmalige Auswertung, FAIL bleibt FAIL.

Punkte: richtig +1, „unsicher“ 0, falsch −1 (λ = 2 nur berichtet).

| Hypothese | Kriterium (180 frische Aufgaben) |
|---|---|
| H1 Namen-Signal | AUROC (Ziffern+Namen) für „Antwort falsch“ ≥ 0,70 und ≥ AUROC (nur Ziffern) + 0,03 |
| H2 Gegenprobe | ≥ 70 % der Fehlschläge wären sonst falsch, und ≥ 50 % der falschen Werkzeug-Antworten werden erkannt |
| H3 Nutzen (ds3b) | ≥ „immer Rezept“ + 7 Punkte, falsche ≤ 0,7 × „immer Rezept“, beantworteter Anteil ≥ 70 % |
| H4 Richtige bleiben | ds3b richtig ≥ „immer Rezept“ richtig − 9 |

**Entwicklung (120 Aufgaben, Seeds 41+43):** immer Rezept 101/19 (82 Punkte); nur Ziffern 87; Ziffern+Namen 85; Gegenprobe allein 99/4/17× unsicher (**95**); ds3b 97/4/19 (93); check_repair 112. Gegenprobe: Treffsicherheit 0,88, erkennt 15 von 16 falschen Werkzeug-Antworten. Namen-Unsicherheit AUROC 0,73 gegen 0,83 nur Ziffern.

**Vorhersage (ehrlich, vor frisch):** H1 wird vermutlich **FAIL** (auf den Entwicklungsdaten macht der Namen-Teil das Signal schlechter, nicht besser); H2–H4 vermutlich PASS, getragen von der Gegenprobe. Die Hauptpolitik ds3b wurde vor den Entwicklungsdaten festgelegt und bleibt, obwohl `check` allein dort leicht besser ist.
