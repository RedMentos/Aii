# WP-Z11b Befund: STEP4 Referenz-Lehrer, zweiter Versuch — `STEP4_EXIT_FAIL` (nur T2)

Vorregistriert in `PREREG.md`. Daten `v13/bench-results/z11b-reference-teacher-20261026/` (z11b.json, run-b.log).

| Prüfung | Z11 | Z11b | |
|---|---|---|---|
| T1 Self vor Lehrer festgehalten | 60/60 | 60/60 | PASS |
| T2 Lehrer-Text nie in der History | 1 Treffer | 1 Treffer (compare07) | **FAIL** |
| T3 Lehrer an/aus ändert Self nicht | 34/60 | **60/60** | PASS |
| T4 Präferenz und Fakt getrennt | 10/10 | 10/10 | PASS |
| T5 Fingerabdruck reproduzierbar | 10/20 | **20/20** | PASS |
| T6 keine Parameter geändert | ja | ja | PASS |

Urteil: **`STEP4_EXIT_FAIL`**, wie vorab festgelegt zählt der T2-Treffer, auch wenn er harmlos aussieht.

Der eine Treffer ist das Stück `"Malmo had the most rain (868 mm) compar`: der eigene Self-Satz, den der Lehrer in
Anführungszeichen zitiert. Die alte Prüfung verglich den Lehrer-Text mit der JSON-kodierten History und hielt das
Anführungszeichen für fremden Inhalt. Es ist kein Lehrer-Text in die History gelangt; die History nimmt
bauartbedingt nur user/assistant-Zeilen (`v13/history.py`). Dieselbe Prüfung hätte echte Lecks mit Umlauten oder
Zeilenumbrüchen übersehen können, weil JSON diese Zeichen umschreibt.
T3 und T5 sind mit sauberem Aufbau und Fingerabdruck-Fix grün: der eingeschaltete Lehrer verändert Self in 60/60
Aufgaben nicht. Beschreibend: Self 42/60, Lehrer 40/60, Lehrer besser 8, schlechter 10, Lehrer 33 s, Self 10,5 s.

Nächster Schritt **WP-Z11c** (neu vorregistriert): Leck-Prüfung v2 auf Klartext (Anführungszeichen/Markup ignoriert)
auf frischem Seed 29, sonst wie Z11b.
