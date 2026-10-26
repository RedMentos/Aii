# Befund WP-Z2i: Auswahlliste für den B2-Zeiger (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `b3bfa25a`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 9 Läufe × 70 Zeilen (A4/E4/N4 × Seeds 32–34),
alle RECORDED, kein Abbruch. Zeiger mit 4 Plätzen, `b2_context_chars` = 1536, Wächter an (Replay).

## Ergebnis laut Vorregistrierung: `Z2I_CHOICES_HELP` (Arm N4) — praktisch aber klein, und mit einem Benennungsfehler
| | A4 (alle Sätze) | E4 (nur frühere) | N4 (nur frühere, umgekehrt) |
|---|---|---|---|
| B2-Regelquote | .125 | .150 (+.025 [−.083, +.167]) | **.392 (+.267 [+.116, +.442])** |
| exakt bewacht `both_exact` (30 Zeilen) | 3 | 4 | 4 |
| alle Zeilen exakt (Wächter an) | 7/210 | 12/210 | 14/210 |
| falsch ohne → mit Wächter | 11 → **0** | 18 → **0** | 43 → **0** |
| Werkzeug-Nutzen `both_exact` / b1_only | .561 / .486 | .639 / .519 | .661 / .519 |
| gewählte Sätze (REVISED/TWICE): aktuell/Kickoff/Notiz/Datenblatt | 79/35/87/7 | 0/85/63/63 | 0/222/19/31 |
Je Typ exakt (Wächter an): REVISED 0/0/1, TWICE 0/0/0, LONG 1/4/3, CONFIRM 6/8/10. Gültigkeit, Konsistenz, Struktur erfüllt; E4/N4 zitierten nie die
aktuelle Aufgabe.

## Benennungsfehler, nach dem Lauf gefunden (offen genannt)
`body_context` liefert die früheren Quellen **jüngste zuerst**. Damit war `earlier` (E4) schon „jüngste zuerst“, und der Arm `earlier_newest` (N4)
war in Wahrheit **älteste zuerst** (Kickoff vorn) — mit einer Anweisung an B2, die fälschlich „newest first“ sagte. Die Daten bleiben gültig für die
tatsächlich gezeigte Reihenfolge; die Anweisung war irreführend. Behoben: Modus heißt jetzt `earlier_oldest`, Anweisungen nennen die echte Reihenfolge
(`earlier`: „newest first“, `earlier_oldest`: „oldest first“). Die aufgezeichneten Läufe sind damit nicht byte-gleich wiederholbar.

## Einordnung
- Die höhere Regelquote kommt fast ganz aus LONG/CONFIRM: B2 wählt bei Kickoff-vorn die Kickoff-Sätze (Positionsneigung). Bei **geänderten Regeln**
  bleibt es bei ~0 exakt: die Änderungsnotiz wird kaum gewählt (19 von 272 Sätzen), dafür mehr alte Regeln (überholte Werte in Zitaten 22/45/74).
  Ohne Wächter wäre N4 der unsicherste Arm (43 falsch); mit Wächter 0.
- Der formale Gewinn bei den exakten Entscheidungen ist **eine** Zeile (4 vs 3). Werkzeug-Nutzen steigt (.561 → .661), weil UNKNOWN mit mehr
  belegten Feldern teilweise Punkte bringt.
- Kern bleibt: Qwen-B2 wählt nach Position, nicht nach Inhalt.

## Empfehlung
- Schalter bleiben Standard (`b2_quote_choices` all, `b2_quote_slots` 2, `b2_quote_select` aus, Budget 768).
- Nächstes Paket **WP-Z2j**: (a) Wiederholung von „älteste zuerst“ mit **korrekter** Anweisung auf frischen Episoden und (b) B2 wählt ganze
  frühere Quellen statt Sätze (`b2_quote_choices=sources`) — bei Positionsneigung bekommt C3 dann Kickoff **und** Änderung; der Wächter fängt alte Werte.

Daten: `code/bench-results/step2-z2i-choices-20261026/`; volle STEP2-Berichte im Projektordner `v13/bench-results/step2-z2i-choices-20261026/`.
