# WP-HX2 Befund: **HX2_INVALID** (vorregistrierte Regel 1), beschreibend ohne Gewinn

Vorregistrierung `PREREG.md` (Commit f94bb84, vor jedem Modelllauf). Linux-Cloud, 4 CPUs, keine Redmi-Messung.
Kanonisches STEP2-Gate bleibt UTILITY_FAIL. Ergebnis `run/hx2_result.json`, Auswahl `run/hx2_compose.json`, Zusammenfassungen
`run/summary_*.json`; Rohberichte, Werkzeug-Nachspiel und B2-Mitschnitte im Projektordner
`v13/bench-results/hx2-same-task-probe-20261022/` (54 MB).

## Stufe 1 Probe (Seed 20, ohne Lösungen ausgewählt)
Goldfreie Zahl = Anteil der B2-Zitate, die die exakte Quellenprüfung bestehen (Probe-Episoden P):
REF .35, V1 (allgemein) .625, V2 (fachlich) .625, V3 (beides) .65 -> **V3 gewählt** (+.30 ≥ .05).
Verhalten: V1 änderte die B2-Zitate in 21/35 Aufgaben der P-Episoden.
Aber schon auf Seed 20 (beschreibend): both_exact REF .617, V1 .633, V2 .583, V3 .592; b2_only REF .242 -> V3 .158.

## Stufe 2 Prüfung (Seeds 21–23, REF / V3 / U, zurückgehaltene Episoden H)
- **V3_s23 strukturell gescheitert:** in der Vorbereitung von Nimbus gab B2 unter V3 ungültiges JSON aus
  (`JSONDecodeError`), 7 Zeilen nicht aufgezeichnet, das Werkzeug-Nachspiel verweigert den Bericht. Regel 1 -> **HX2_INVALID**.
  Nicht neu gewürfelt (das wäre Seed-Auswahl). In allen anderen 11 Läufen 0 ungültige B2-Ausgaben (je 80 Aufrufe).
- Ablauf-Hinweise: ein erster REF_s20-Versuch brach durch ein Zeitbudget ab, weil gleichzeitig die Testsuite lief; ein
  REF_s21-Versuch starb beim Neustart der Maschine. Beide aufbewahrt (`aborted-runs/`), frisch neu gestartet, Kriterien unverändert.

## Beschreibend, nicht entscheidend (fertige Seeds 21, 22)
| Achse (H-Episoden) | V3 − REF | KI 95 % | U − REF |
|---|---|---|---|
| both_exact (Haupt) | +.008 | [−.125, +.150] | −.025 |
| b2_only | −.042 | [−.133, +.033] | −.008 |
| b1_only | +.008 | [.000, +.025] | +.008 |
| B2 volle Regel | .000 | [−.281, +.344] | +.094 |
Falsch übernommene Antworten 0/0/0. B2-Prompt-Token: REF 613, V3 680 (+11 %), U 639.
Auch dort wäre das Ergebnis HX2_AXIS_WORSE (b2_only < −.02) und ohne Gewinn. Alle 10 Episoden: both_exact +.013 [−.054, +.079].

## Lehre
Die goldfreie Probe-Zahl stieg kräftig (.35 -> .65), der Nutzen nicht: B2 zitiert unter V3 öfter wortgetreu, aber nicht
öfter die *richtige Regel*. Die Zahl „Zitat besteht die Prüfung“ ist also ein schlechter Stellvertreter für das Ziel
(Goodhart). Der Code-Schalter Zeiger (Z2d, live an, .97) bleibt der wirksame Weg; eine Textänderung ersetzt ihn nicht.
Für die nächste Harness-Probe braucht die goldfreie Zahl einen Bezug zum Zweck (z. B. „Zitat stammt aus dem früheren
Quelltext, wenn die aktuelle Frage die Regel nicht nennt“), vorab gegen gespeicherte Läufe geprüft.

## Folgen
Nichts ändert sich live. Kein AG8-Vorschlag. **WP-HX5 bleibt gesperrt** (Export verlangt HX2_PASS). Der HX5-Baustein wurde
an den Mitschnitten trocken geprüft: 80 V3-Aufrufe der fertigen Seeds, 5 wären als gute Beispiele angenommen worden.
