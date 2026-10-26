# WP-DS3d Vorregistrierung (2026-10-26, vor jeder frischen Aufnahme)

Die zweite feste Probe prüft, ob die Antwort die richtige **kleinste** Stelle nennt und ob jede Zahl zum richtigen Namen gehört. Erst danach greift der DS3c-Werkzeug-Satz.
Die Probe ist `ds3b_name_check.cross_check(full=True)` und wurde am 22.10. geschrieben, vor allen DS3c-Aufnahmen. Bisher wurde sie nur berichtet, jetzt wird sie gewertet.
Skript `code/scripts/ds3d_least_probe.py` (sha256 in `PREREG.json`).

**Daten.**
- Entwicklung: alle DS3c-Aufnahmen (R4 Seeds 61 + 67, Familie F Seeds 69, 71, 73).
- Frisch, noch nicht aufgenommen: R4 Seeds 79 + 83, F Seeds 89 + 97, je 120 Aufgaben.
- Aufgenommen wird mit `ds3c_tool_answer.py capture` auf der gleichen Laufzeit. Gewertet wird streng, λ = 1. Ausgewertet wird einmal, FAIL bleibt FAIL.

| Hypothese | Kriterium |
|---|---|
| H1 R4 Nutzen | mit zweiter Probe ≥ nur erste Probe + 5 Punkte |
| H2 R4 Fehler | mit zweiter Probe ≤ nur erste Probe − 3 Fehler |
| H3 F kein Verlust | mit zweiter Probe ≥ nur erste Probe − 1 Punkt |
| H4 Sicherheit | kein falscher Werkzeug-Satz bei richtig gelesenen Werten |

**Entwicklung:**
- R4: nur erste Probe 109/11 (98 Punkte), mit zweiter Probe 114/6 (108).
- F (180 Aufgaben): 176/4 (172) gegen 178/2 (176).
- Kein falscher Werkzeug-Satz.

**Vorhersage:** H1–H4 PASS. Risiko: Bei frischen Seeds gibt es auf R4 vielleicht weniger „kleinste Stadt falsch“-Fälle, dann verfehlt H1 die Marke von +5.
