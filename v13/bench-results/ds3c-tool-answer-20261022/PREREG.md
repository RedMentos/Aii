# WP-DS3c Vorregistrierung (2026-10-22, vor dem Lesen der frischen Läufe)

Folgepaket zu WP-DS3b: Schlägt die feste Gegenprobe Antwort ↔ Werkzeug fehl, gibt V13 **einen festen Satz aus dem Werkzeugergebnis** („X hat den größten Wert …, die Differenz ist …“ / „Nein, die genannte Zahl N ist falsch. Die exakte Summe ist …“) statt „unsicher“ zu sagen.
Skript `code/scripts/ds3c_tool_answer.py` (sha256 in `PREREG.json`), Tests `code/tests/test_ds3c_tool_answer.py`.

**Gegen die Schwächen von DS3b abgesichert**
- Der Satz hat keine Einheit (in DS3b stand „euros“) und ist für alle Aufgabenarten gleich.
- **Strenge Wertung ist die Hauptwertung.** Eine falsche „meiste“ oder „wenigste“ Stadt zählt als Fehler, ebenso eine falsche Zahl zu einem Namen. Der Satz muss also inhaltlich stimmen und nicht nur die Regex treffen.
- **Neue Aufgabenfamilie F**, die kein früheres Skript gesehen hat: Bäckereien, Reisekosten mit falscher Angabe, Mannschaftspunkte mit 4 Teams, Paketgewichte. Neue Wörter und Einheiten.

**Daten.** Echte C3 LFM2.5-350M, Laufzeit Branch hmopsm, Cloud-CPU.
- Entwicklung: nur Familie F Seed 69. Damit wurden Generator und Prüfungen auf Plausibilität angeschaut. Es gibt nichts anzupassen, weil die Politik keine Schwelle hat.
- Frisch: R4 Seeds 61 + 67 und Familie F Seeds 71 + 73, je 120 Aufgaben. Die Aufnahme lief beim Schreiben, die Dateien wurden nicht gelesen.
- Ausgewertet wird einmal, FAIL bleibt FAIL.

| Hypothese | Kriterium (streng, λ = 1) |
|---|---|
| H1 R4: Werkzeug-Satz statt „unsicher“ | Punkte ≥ „unsicher“ + 6, falsche ≤ „unsicher“ + 2 |
| H2 F: Gegenprobe überträgt sich | ≥ 70 % der Fehlschläge wären falsch, ≥ 50 % der falschen Werkzeug-Antworten erkannt |
| H3 F: Nutzen | Werkzeug-Satz ≥ „immer Rezept“ + 5 Punkte und ≥ „unsicher“ |
| H4 Sicherheit | Jeder falsche Werkzeug-Satz kommt von einem falsch gelesenen Wert (nie bei richtigem Lesen) |

**Entwicklung (F Seed 69, 60 Aufgaben, streng):** immer Rezept 48/12 (36 Punkte), „unsicher“ 48/1/11× (47), Werkzeug-Satz 59/1 (58). Gegenprobe 11 von 11 Treffern, sie erkennt 11 der 12 Fehler. Keiner der Werkzeug-Sätze war falsch.
**Vorhersage:** H1 bis H4 PASS. Das größte Risiko sind falsch gelesene Werte: Dann ist auch der Werkzeug-Satz falsch, und zwar selbstsicher.
