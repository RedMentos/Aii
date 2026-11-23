# Kandidat: höhere Schnittschwelle für Event-Segmente — **FAIL** (Thread L, 2026-10-12)

Skript `code/scripts/event_segments_threshold_candidate.py`, Vorregistrierung `preregistration.json` (Commit `6a8fa1f`, vor dem Lauf gepusht), Rohdaten `report.json`. `episodes.py` unverändert; nur das Argument `threshold` von `text_segments` wird erhöht.
Kalibrierung auf Saaten 101–105 (flat): .6 → F1 .305, .65–.8 → .232 → gewählt **.6**. Test auf Saaten 13–17, gleiche Texte/Wertung wie `event-segments-20261012`.

| Bedingung | Kandidat .6 | aktuell .5 | gleichmäßig (gleiche Zahl) | zufällig | Schnitte Kandidat |
|---|---|---|---|---|---|
| flat | .244 | .263 | **.292** | .148 | 1.95 |
| para (Leerzeile) | **.725** | .513 | .661 | .434 | 2.26 |

- Kriterien: flat schlägt .5 nur in 1/5, schlägt gleichmäßige Schnitte nur in 1/5 → **FAIL** (para nie schlechter als .5: erfüllt).
- Ohne Absatz reicht der lexikalische Themenwechsel nicht: weniger Längenschnitte, aber die übrigen treffen die Themengrenze nicht öfter als gleichmäßige Satzschnitte.
- Mit Absatz hilft die höhere Schwelle deutlich (.72 statt .51, auch über gleichmäßig .66): Das Absatzsignal kommt dann nicht mehr unter den Längenschnitten unter.
- Folge: Schwelle bleibt .5 (nichts wird live geändert). Eine Absatz-Schwelle allein wäre ein eigener Kandidat; für flache Texte braucht es ein stärkeres Themensignal (z. B. Einbettungs-Distanz), nicht nur eine andere Schwelle.
- Grenze: kurze synthetische Themenmischungen aus einem Korpus, nur lexikalische Signale, Breite 240.
