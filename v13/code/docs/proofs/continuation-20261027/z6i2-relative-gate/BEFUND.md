# WP-Z6i2 Befund: Freigabe relativ zum aktiven Kopf — `Z6I2_PASS`

(Vor dem Lauf als „WP-Z6j“ vorregistriert, umbenannt wegen Namensgleichheit mit einem anderen Thread; in den JSONs `verdict_z6j`.)

Vorregistriert in `PREREG.md` (Commit vor dem Lauf, gepusht). Frische Seeds 97, 101, 103, Daten
`v13/bench-results/z6i2-relative-gate-20261027/seed{97,101,103}.json` (+ `run_seed*.log`; Vorläufe unter `dev/`).

| Seed | Arm | Kopf allein Hälfte | Behalten | falsche Freigaben | unnötige Updates | Übergabe | Laufzeit Hälfte / unverändert | nach Rücknahme Hälfte | ohne Regelwörter |
|---|---|---|---|---|---|---|---|---|---|
| 97 | adaptive+rel | 1,00 | 1,03 | 0 | 0 | 1 | 1,00 / 1,00 | 1,00 | 1,00 |
| 97 | fixed+rel | 1,00 | 1,03 | 0 | 5 | 1 | 1,00 / 1,00 | 1,00 | 1,00 |
| 97 | K1 fixed+now | 0,00 | 1,00 | 0 | 7 | – | 1,00 / 0,97 (Regel) | – | 0,00 |
| 101 | adaptive+rel | 1,00 | 1,00 | 0 | 0 | 1 | 1,00 / 0,94 | 1,00 | 1,00 |
| 101 | fixed+rel | 1,00 | 1,03 | 0 | 4 | 1 | 1,00 / 1,00 | 1,00 | 1,00 |
| 101 | K1 fixed+now | 0,00 | 1,00 | 0 | 4 | – | 1,00 / 0,84 (Regel) | – | 0,00 |
| 103 | adaptive+rel | 1,00 | 1,00 | 0 | 0 | 1 | 1,00 / 0,94 | 1,00 | 1,00 |
| 103 | fixed+rel | 1,00 | 1,00 | 0 | 1 | 1 | 1,00 / 0,94 | 1,00 | 1,00 |
| 103 | K1 fixed+now | 0,00 | 1,00 | 0 | 5 | – | 1,00 / 0,81 (Regel) | – | 0,00 |

Kriterien J1, J2, J3 in allen drei Seeds erfüllt. Urteil **`Z6I2_PASS`** (in den Daten `Z6J_PASS`). Berichtet: `fixed+rel` diesmal 0 falsche
Freigaben (Vorläufe 83/89: je 1), `adaptive` spart alle unnötigen Updates (0 vs. 1–5).

## Was damit gilt (Lern-Lebenszyklus, §24.32 L11)
Ein neuer menschlicher Hinweis wird jetzt wirklich gelernt und ersetzt den alten:
1. Mensch: `:ersetze route simple hälfte,halbiere,geteilt durch zwei --sofort --lehre` → alte widersprechende
   Korrekturen zählen nicht mehr (Z6c), die Regel wirkt sofort beim Antworten (Z6d), und ihre Fragen dürfen lehren.
2. `:learning shadow`, `:learn route` (danach `:learning commit`, `:approve <Update-Id>`) → der Routen-Kopf lernt mit dem festen Wortkanal die neue Grenze (Kopf allein 0 → 100 % in 3/3
   frischen Seeds; ohne Wortkanal 0 %), ohne Nachbarn mitzureißen (Anker) und ohne bekannte Fragen zu verlieren.
3. `:ersetze pruefe <Id>` → nach 8 Zustimmungen in Folge „gelernt“; `:ersetze gelernt <Id>` übergibt; die Regel
   springt bei einem Widerspruch, einer Rücknahme oder einem neuen Kopf ohne eigene Bestätigung von selbst wieder ein.
Der Kopf überträgt die neue Grenze auch auf Hälfte-Fragen ohne die Regelwörter (100 % vs. 0 % Kontrolle).

Entscheidung laut Vorregistrierung umgesetzt: Standard `route_head_words=true`, `route_head_gate=relative`. Ein schon
aktiver Kopf ohne Wortkanal wird beim nächsten `:learn route` mit Nullzeilen erweitert (gleiches Verhalten bis zur
Freigabe). Lernen bleibt manuell (`:learn route`) und freigabepflichtig. Ganze Testsuite grün (1784 Tests, 5 übersprungen).

Grenzen: nur Routen-Kopf (nicht Körper/Gewichte der Sprachmodelle), generierte deutsche Umschreibungen einer einzigen
verschobenen Grenze, Mensch durch Harness ersetzt (übergibt sobald „gelernt“), Cloud, keine Handy-Messung.
Handy-Test (kurz, braucht einen schon gelernten Routen-Kopf): `:ersetze route simple hälfte --sofort --lehre`, ein paar
Hälfte-Fragen stellen, `:learning shadow`, `:learn route`, `:learning commit`, `:approve <Update-Id>`, weitere Hälfte-Fragen,
`:ersetze pruefe <Regel-Id>`, bei „learned“ `:ersetze gelernt <Regel-Id>`.
