# Werkzeug-Vorhersage lernt weiter, Runde 2 — CONTINUAL_LEARNING_CONFIRMED

Stand 2026-10-13, Thread „Nächste offene Pakete M“, Linux-Cloud (nicht Redmi). Vorregistriert `5760bc7` vor dem Lauf; Piloten sind in der Vorregistrierung offen ausgewiesen. 610 Live-Aufrufe, alle SCORED, 38 min.

Idee (komplementäres Gedächtnis): Der gemessene Rest bleibt für bekannte Fälle unangetastet. Ein zweiter Rest lernt nur aus eigenen bewerteten Aufrufen, die das Kompetenz-Signal als „außerhalb der Domäne“ markiert, und wird nur für solche Fälle benutzt.

| Welt | verschobener Test: angepasst / gemessen | In-Welt-Test | Gate |
|---|---|---|---|
| calc_counter (1000..9999) | .54 / .66 / .60 / .73 (−7, +15, ÷4, ×2) | 1.00 (unverändert) | PASS, 4/4 Handlungen |
| note_edit (freie Notizen) | .70 / .69 / .88 (urgent, upper, done) | 1.00 (unverändert) | PASS, 3/3 Handlungen |

- Anteil an der besten Kontrolle auf dem verschobenen Test, vorher → nachher: Rechnen ÷4 1.66 → .99 (vorher schlechter als die Kontrolle), −7 .29 → .16, ×2 .35 → .25, +15 .62 → .41; Notizen .57–.93 → .50–.64.
- In der Welt bleibt jede Vorhersage exakt die gemessene (Quotient 1.00). Das Kompetenz-Signal markierte dort 0 von 50 Zuständen.
- Retention auf der Install-Retention-Menge: angepasst ≤ 1,02 × gemessen bei allen 7 Handlungen.

Grenzen:
- Für Rechnen markierte das Kompetenz-Signal nur 36 von 160 Erfahrungsaufrufen, also nur 9 Lernbeispiele je Handlung, knapp über dem Minimum von 8. Im Test wurden 43 % der verschobenen Zustände markiert; der Gewinn kommt nur von diesen.
- Zwei geschlossene Welten, ein Gerät (Cloud). Nur SHADOW: nichts in der Laufzeit liest eine der beiden Vorhersagen.
- Gelernt wird ein geschlossen lösbarer linearer Rest, kein Gewichts-Lernen im Körper.

Runde 1 (`f4a3c82`, NOT_CONFIRMED) steht unverändert in `../tool-forecast-learning/`.

Dateien: `preregistration.json`, `plan.json`, `learn.json`, `report.json`, `rows.json`.
