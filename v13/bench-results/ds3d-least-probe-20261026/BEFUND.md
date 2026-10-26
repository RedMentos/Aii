# WP-DS3d Befund: zweite Probe „kleinste Stelle / Name–Zahl“ vor dem Werkzeug-Satz (2026-10-26)

**Verdikt (vorregistriert): NOT_SUPPORTED wegen H4.** H1–H3 PASS. Vorregistrierung `PREREG.md`/`PREREG.json` (Commit b2dd2d07, vor jeder frischen Aufnahme), Bericht `report.json`, frische Aufnahmen `fresh/` (R4 Seeds 79 + 83, Familie F Seeds 89 + 97; je 120 Aufgaben; echte C3 LFM2.5-350M, Cloud-CPU).

Strenge Wertung, λ = 1:

| Politik | R4: richtig / falsch / Punkte | F: richtig / falsch / Punkte |
|---|---|---|
| immer Rezept | 93 / 27 / 66 | 105 / 15 / 90 |
| nur erste Probe → Werkzeug-Satz (DS3c) | 109 / 11 / 98 | 120 / 0 / 120 |
| **mit zweiter Probe → Werkzeug-Satz** | **115 / 5 / 110** | 120 / 0 / 120 |

- **H1 PASS:** +12 Punkte auf R4 (gefordert +5).
- **H2 PASS:** Fehler 11 → 5.
- **H3 PASS:** kein Verlust auf der neuen Familie.
- **H4 FAIL:** 1 Werkzeug-Satz war falsch, obwohl die Zahlen richtig gelesen waren. Das Modell hatte den **Namen** falsch abgeschrieben („Brmen“ statt „Bremen“), und der feste Satz übernahm den Tippfehler. Der Fehler steckt genauso in der DS3c-Politik ohne zweite Probe.

**Lesart.** Die zweite Probe wirkt wie erwartet. Die Sicherheitslücke liegt im Lesen: Der Zahlen-Wächter prüft jede Zahl gegen den Nutzertext, für Namen gibt es keinen solchen Wächter.

**Folge.** In der Laufzeit (Schalter `tool_answer_check`, Stufe `correct`, Standard aus) einen **Namen-Wächter** einbauen. Der feste Satz wird nur gesagt, wenn jeder Name wörtlich im Nutzertext steht, sonst kommt nur der „unsicher“-Hinweis (eingebaut, siehe ROADMAP). Die zweite Probe kommt erst nach einer neuen Vorregistrierung auf frischen Seeds mit Namen-Wächter in die Laufzeit. FAIL bleibt FAIL.

**Grenzen.** Generierte englische Aufgaben, strenge Regel-Prüfung, Cloud-CPU, ein einzelner Fall für H4.
