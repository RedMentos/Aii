# WP-DS3c Befund: Werkzeug-Satz statt „unsicher“ bei fehlgeschlagener Gegenprobe (2026-10-22, ausgewertet 2026-10-26)

**Verdikt (vorregistriert): DS3C_SUPPORTED, H1–H4 PASS.** Vorregistrierung `PREREG.md`/`PREREG.json` (Commit 64fb713, vor dem Lesen der frischen Läufe), Bericht `report.json`, Aufnahmen `dev/` (Familie F Seed 69) und `fresh/` (R4 Seeds 61 + 67, neue Familie F Seeds 71 + 73; je 120 Aufgaben; echte C3 LFM2.5-350M, Cloud-CPU).

Strenge Wertung (Hauptwertung: auch falsche „meiste/wenigste“ Namen und falsche Zahl zu einem Namen zählen als Fehler), λ = 1:

| Politik | R4: richtig / falsch / Punkte | Familie F: richtig / falsch / Punkte |
|---|---|---|
| immer Rezept (C3 schreibt mit Werkzeug-Hinweis) | 98 / 22 / 76 | 102 / 18 / 84 |
| Gegenprobe → „unsicher“ (DS3b) | 98 / 11 / 87 (11× unsicher) | 101 / 3 / 98 (16× unsicher) |
| **Gegenprobe → fester Werkzeug-Satz** | **109 / 11 / 98** | **117 / 3 / 114** |

- **H1 PASS (R4):** Werkzeug-Satz +11 Punkte gegen „unsicher“, nicht mehr Fehler.
- **H2 PASS (F, neue Aufgaben):** Die Gegenprobe überträgt sich: 15 von 16 Fehlschlägen waren echte Fehler (94 %), 15 von 18 falschen Antworten erkannt (83 %).
- **H3 PASS (F):** 114 gegen 84 („immer Rezept“) und 98 („unsicher“).
- **H4 PASS:** Kein einziger Werkzeug-Satz war falsch (0 von 27).

**Lesart.** Wenn eine feste Probe zeigt, dass die eigene Antwort dem exakten Werkzeug widerspricht, ist es besser, das Werkzeugergebnis klar zu sagen, als nur „unsicher“. Das gilt auch für neue Aufgabenarten und unter strenger Wertung. Grenze bei R4: Streng gezählt erkennt die Gegenprobe nur 11 von 19 Fehlern, denn sie prüft die „wenigste“ Stadt nicht. Die übrigen 11 Fehler sind meist eine falsch genannte kleinste Stadt.

**Folge (Vorschlag).** Den Laufzeit-Schalter `tool_answer_check` um die Stufe `correct` erweitern: Bei fehlgeschlagener Probe wird der feste Werkzeug-Satz als Korrektur angehängt, Standard **aus**. Danach Handy-Messung. Optional eine zweite Probe für die „wenigste“-Angabe, mit eigener Vorregistrierung.

**Grenzen.** Generierte englische Aufgaben (8 Arten, 2 Familien), Regex und strenge Regel-Prüfung, nur die Rezepte Summe und größter minus kleinster. Der Satz ist fester Text, falsch gelesene Werte würden ihn falsch machen (kam hier nicht vor). Gemessen auf Cloud-CPU, nicht auf dem Handy. Keine Laufzeit-Änderung durch diese Messung.
