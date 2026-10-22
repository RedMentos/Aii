# WP-DS3 Vorregistrierung (vor dem Lesen der frischen Läufe, 2026-10-22)

Frage: Kann V13 mit einer kalibrierten Unsicherheit (AG9-Metakognition + Ziffern-Unsicherheit von C3 aus R4 Teil 3) sinnvoll wählen zwischen **antworten**, **mit dem lokalen Werkzeug nachrechnen** und **„unsicher“ sagen**?

- Skript `code/scripts/ds3_metacog_policy.py`, maschinenlesbare Vorregistrierung `PREREG.json` (Kalibrierer, Schwelle 0,5, Skript-sha256).
- Entwicklungsdaten: die drei aufgezeichneten R4-Teil-5-Läufe (Seeds 7, 11, 17; echte C3 LFM2.5-350M, Thread K), Kopie in `dev/`.
- Frisch: **Seeds 31 und 37** (120 Aufgaben), neu aufgenommen mit `scripts/r4_typed_recipe.py capture` (echtes Modell, Cloud-CPU, Laufzeit-Stand Branch hmopsm). Die Aufnahme lief beim Schreiben bereits, die Dateien wurden vor dem Commit dieser Registrierung nicht gelesen.
- **Ehrlichkeitshinweis:** Ein erster Entwurf (ein gemeinsamer Kalibrierer der Erst-Antwort) ergab auf den Entwicklungsdaten „nie unsicher sagen“, weil die unsicheren Erst-Antworten genau die Rechenaufgaben sind, die das Werkzeug ohnehin repariert. Ersetzt durch Kalibrierer je Bestandteil (nach Werkzeug / ohne Werkzeug) — nur auf Entwicklungsdaten entschieden.

Punkte: richtig +1, „unsicher“ 0, falsch −1 (λ = 1; λ = 2 nur berichtet).

| Hypothese | Kriterium (120 frische Aufgaben) |
|---|---|
| H1 Kalibrierung | AUROC „Antwort falsch“ ≥ 0,70 und ECE ≤ 0,15 |
| H2 Nutzen | DS3-Punkte ≥ „immer Rezept“ + 5, falsche Antworten ≤ 0,7 × „immer Rezept“, beantworteter Anteil ≥ 70 % |
| H3 Treffsicherheit von „unsicher“ | ≥ 60 % der „unsicher“-Fälle wären sonst falsch gewesen |
| H4 Richtige bleiben | DS3 richtig ≥ „immer Rezept“ richtig − 6 |

Entwicklung (180 Aufgaben): immer Rezept 156 richtig / 24 falsch (132 Punkte), DS3 155 / 16 / 9× unsicher (139 Punkte). Frisch wird genau einmal ausgewertet; FAIL bleibt FAIL.
