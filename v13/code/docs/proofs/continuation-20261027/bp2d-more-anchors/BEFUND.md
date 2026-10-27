# WP-BP2d Befund: mehr erzeugte Anker (`locality_gen=4`) im AG6-Weg auf C3 350M — `BP2D_FAIL` (Tor-Durchgang nicht stabil), Leck-Gewinn bestätigt

Vorregistrierung `PREREG.md` (vor der Messung). Roh: `bench-results/bp2d-more-anchors-20261027/`. Neue Seeds 3 und 4, Aufbau wie BP2c (echte Pipeline, 8 Fakten, Q4-Tor, `gate_held_out`).

| Seed / Arm | Leck | Vergessen | KL | Tor-Status (was fällt durch) |
|---|---|---|---|---|
| 3 live | 0,286 | 0,033 | 0,012 | FAIL (Vergessen, Frozen-Drift, Retention, Spezifität) |
| 3 gen2 | 0,179 | 0 | 0,014 | FAIL (nur Frozen-Drift) |
| 3 gen4 | 0,214 | 0,033 | 0,017 | FAIL (Vergessen, Frozen-Drift, Spezifität, Unseen) |
| 4 live | 0,500 | 0 | 0,015 | FAIL (Spezifität) |
| 4 gen2 | 0,000 | **0,10** | 0,015 | FAIL (Vergessen, Retention) |
| 4 gen4 | 0,071 | 0 | 0,014 | **PENDING_USER (Tor bestanden)** |

Kriterien: K1 gen4 besteht das Tor in beiden Seeds: nein (Seed 3). K2 gen4-Leck <= 0,2 in beiden: nein (0,214). K4 gen4-Leck <= gen2-Leck: nein im Seed 3. -> `BP2D_FAIL`.
Gesamtbild über alle vier Seeds (BP2c + BP2d): **Leck**: live 0,52 / 0,52 / 0,29 / 0,50, mit erzeugten Ankern 0,21 / 0,18 / 0,18 / 0,00 (gen2) bzw. 0,21 / 0,07 (gen4): in jedem Seed klar niedriger, im Mittel 0,39 -> 0,13 (gen2 allein 0,14). **Tor**: live besteht in 0 von 4, mit erzeugten Ankern besteht 1 von 6 Läufen (Seed 4 gen4). Der Rest fällt nicht mehr am Lecken, sondern an **1-3 vergessenen von 30 Allgemeinfragen** und am Frozen-Drift-Maß durch (Tor-Schwelle Vergessen <= 0,02 heißt: schon eine vergessene Frage reicht), also an einem anderen, verrauschten Problem als dem Lecken. Mehr Anker (4 statt 2) hilft dabei nicht konsistent.
Schluss: Der Leck-Gewinn ist reproduziert (4 von 4 Seeds). Der Tor-Durchgang hängt jetzt an der Stabilität des Behaltens im neuen Trainer (Gesamtbatch-Schleife `BodyJepaTrainer`); body0 vergisst in BP2c Seed 2 dieselbe Frage. Empfehlung: `locality_gen=2` als Opt-in für Nutzer-Test behalten (senkt Leck), Standard unverändert; nächstes Paket WP-BP2e (Behalten im neuen Trainer, z. B. Einzelschritt-Schleife wie `LoraTrainer` + Anker; Tor-Schwellen bleiben). Grenzen: 4 Seeds, 8 erfundene Fakten, Cloud, kein Handy.
