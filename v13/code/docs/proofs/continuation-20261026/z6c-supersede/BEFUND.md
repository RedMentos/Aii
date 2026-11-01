# WP-Z6c Befund: Mensch ersetzt alte Korrekturen — `Z6C_SUPERSEDE_FAIL`

Vorregistriert in `PREREG.md` (vor dem Lauf committet und gepusht). Seed 73. Daten `v13/bench-results/z6c-supersede-20261026/`.

| | fixed (ohne Regel) | fixed+sup | adaptive+sup |
|---|---|---|---|
| ersetzte alte Korrekturen je Shadow-Job in Phase 2 | – | 6 | 6 |
| Hälfte-Fragen am Ende | 0 % | 0 % | 0 % |
| Behalten unveränderter Fragen | 93 % | 100 % | 100 % |
| falsche Freigaben | 3 | 2 | 0 |
| Rücknahme stellt her | ja | ja | ja |
| Held-out Ende | 0,70 | 0,75 | 0,80 |

Kriterien: **S1 FAIL** (Hälfte-Fragen 0 % statt ≥ 80 %), S2 PASS, S3 PASS (Rücknahme jetzt gemessen: exakt), **S4 FAIL**
(fixed+sup 2 falsche Freigaben, beide schon in Phase 1 vor der Regel), S5 PASS. Urteil **`Z6C_SUPERSEDE_FAIL`**.

Was passiert ist: Die Regel wirkt mechanisch richtig (je Job 6 alte Hälfte→detail-Korrekturen raus, im Manifest
benannt). Die Kandidaten lernen die Hälfte-Fragen dann zu 100 %, ziehen aber alle anderen Rechenfragen mit
(detail 0 %, Held-out 0,40–0,68). Die eingebaute Prüfung im Worker hat jeden dieser Kandidaten richtig abgelehnt
(EVALUATED_FAIL), darum blieb der alte Kopf aktiv und es gab durch die Regel keine falsche Freigabe.
Ursache: der eingefrorene Needle-Encoder trennt Hälfte-Fragen nicht von anderen Rechenfragen (Z6b-Nachtrag), ein
linearer Kopf darauf kann die neue Grenze nicht lernen. Das Lebenszyklus-Problem ist damit zweigeteilt: (1) Ersetzen
alter Korrekturen — jetzt gelöst und rücknehmbar; (2) Darstellung — der Kopf sieht den Unterschied nicht.
Nächster Schritt (neu vorregistrieren): die vom Menschen genannten Wörter zusätzlich als feste, rücknehmbare
Routen-Vorgabe beim Antworten anwenden (wie die Nutzer-Regeln, ohne Lernen), oder ein Encoder, der die Grenze trägt.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, ein Seed, Mensch durch Regel ersetzt, Cloud.
