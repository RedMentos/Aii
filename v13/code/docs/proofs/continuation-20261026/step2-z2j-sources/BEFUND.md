# Befund WP-Z2j: B2 wählt ganze frühere Quellen — Regeln kommen jetzt an, C3 liest den alten Wert (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `62972192`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 9 Läufe × 70 Zeilen (A4/O4/S4 × Seeds 35–37),
alle RECORDED. Panne: Neustart der Cloud-Umgebung während A4_s37 → Teillauf verworfen (Projektordner `partial/`), A4_s37 komplett neu (`run2.log`).

## Ergebnis laut Vorregistrierung: `Z2J_CHOICES_HELP` (bester Arm S4 = ganze Quellen)
| | A4 (alle Sätze) | O4 (älteste zuerst, Sätze) | **S4 (ganze Quellen)** |
|---|---|---|---|
| B2-Regelquote | .117 | .333 (+.217 [+.092, +.350]) | **.708 (+.592 [+.467, +.708])** |
| exakt bewacht `both_exact` (30 Zeilen) | 2 | 5 | **8** |
| alle Zeilen exakt (Wächter an) | 8/210 | 15/210 | **22/210** |
| falsch ohne → mit Wächter | 16 → **0** | 47 → **0** | 48 → **0** |
| Werkzeug-Nutzen `both_exact` / b1_only | .514 / .511 | .661 / .506 | **.683 / .528** |
| gewählte Einträge je Angebot | 2,28 | 2,83 | 1,81 |
| B2-Prompt-Tokens | ~893 | ~849 | ~811 |
Je Typ exakt (Wächter an) A4/O4/S4: LONG 1/5/9, CONFIRM 7/10/13, **REVISED 0/0/0, TWICE 0/0/0**. O4 wiederholt das Z2i-Ergebnis, jetzt mit korrekter
Anweisung. Gültigkeit, Konsistenz, Struktur erfüllt. Wächter zum vierten Mal auf frischen Daten: 111 falsche Festlegungen ohne, 0 mit.

## Wo es jetzt hängt (nachträglich, nicht vorregistriert) — `bench-results/.../c3_old_value.txt`
In `both_exact` auf REVISED/TWICE liefert S4 in **10/21** Zeilen alle aktuellen Regeln (A4, O4: 1/21). In **allen 10** zog C3 (LFM2.5-350M) für die
geänderte Regel den **alten** Wert aus dem Kickoff; der Wächter machte daraus UNKNOWN statt einer falschen Entscheidung. Der Engpass ist von B2 zu C3
gewandert: C3 nimmt den ersten genannten Wert, nicht den jüngsten.

## Empfehlung
- Schalter bleiben live Standard/aus. Für STEP2 mit größerem B2-Budget ist `sources` + Wächter der bisher beste Weg.
- Nächstes Paket **WP-Z2k**: Regelwerte nicht von C3, sondern deterministisch als **jüngsten** in den geprüften Zitaten genannten Wert lesen
  (Werkzeug-Schalter, Standard aus; Optionen bleiben bei C3). Erst explorativ auf vorhandenen Daten, dann vorregistriert auf frischen Episoden.
- Hinweis: Ein anderer Thread nennt sein Paket „body_question_mode=tool“ ebenfalls WP-Z2g; hier ist WP-Z2g der Aktualitäts-Wächter.

Daten: `code/bench-results/step2-z2j-sources-20261026/`; volle STEP2-Berichte im Projektordner `v13/bench-results/step2-z2j-sources-20261026/`.
