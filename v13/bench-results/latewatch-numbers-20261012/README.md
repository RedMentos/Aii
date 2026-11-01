# Kandidat: Zahlen-Lesen in `latewatch.disagreement` — **PASS**, übernommen (Thread L, 2026-10-12)

Skript `code/scripts/latewatch_numbers_candidate.py`, Vorregistrierung `preregistration.json` (Commit `75c888b`, vor dem Lauf gepusht), Rohdaten `report.json`. Gleicher Generator, gleiche Wertung und Kontrollen wie `latewatch-20261012`.
Zwei Änderungen, beide unabhängig vom Generator: (1) Tausender-Komma (1,234 / 12,345,678) wird als ganze Zahl gelesen, andere Kommas bleiben Dezimalkomma; (2) eine Zahl am Ende des Teiltexts, die noch wächst, zählt erst beim nächsten Blick. `BODY_REENTRY` unverändert.

| Strom | bisher | Kandidat | nie | immer | zufällig (Kandidat-Zahl) |
|---|---|---|---|---|---|
| standard | .064 | **.070** | 0 | −.295 | −.084 |
| format | −.081 | **+.057** | 0 | −.329 | −.105 |

- Kriterien: format besser als bisher 5/5, standard nie schlechter (0/5), schlägt nie/immer/zufällig je 5/5 auf beiden Strömen, alle Reinprüfungen wahr → **PASS**.
- Übernommen in `v13/latewatch.py` (`nums`, neues `complete`) mit Tests in `tests/test_latewatch.py`. Modus bleibt shadow.
- Der Bericht `latewatch-20261012/report.json` wurde vor dieser Änderung erzeugt (alte Regel).
- Grenze: synthetische Rechenrunden; „1,234“ als deutsche Dezimalzahl (1,234 = 1.234) wird jetzt als Tausend gelesen.
