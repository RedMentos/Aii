# Vorregistrierung WP-Z2j: B2 wählt ganze frühere Quellen; „älteste zuerst“ mit korrekter Anweisung (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2j_sources.py` (nutzt `step2_z2i_choices.py` als private Modulkopie, gleiche
Auswertung und Entscheidungsregel), Tests `code/tests/test_step2_z2j.py`, `code/tests/test_b2_quote_select.py::test_choice_lists_with_earlier_sources`.

## Warum
WP-Z2i (`../step2-z2i-choices/BEFUND.md`): formal `HELP`, aber über einen falsch benannten Arm (Liste älteste zuerst, Anweisung „newest first“),
Gewinn nur bei LONG/CONFIRM, geänderte Regeln weiter ~0 exakt, weil B2 nach Position wählt und die Änderungsnotiz kaum nimmt.

## Änderung
`b2_quote_choices` bekommt den Modus `sources`: jede frühere Quelle (Auszug ≤ 240 Zeichen) ist **eine** Wahl, älteste zuerst. Wählt B2 wie bisher die
vorderen Nummern, bekommt C3 Kickoff **und** Änderungsnotiz; der Wächter macht alte Werte zu UNKNOWN. `earlier_oldest` (früher `earlier_newest`)
sagt jetzt korrekt „oldest first“. Standard bleibt `all`.

## Aufbau
- Zehn **frische** Episoden: REVISED ×5 (Alcor, Baham, Chara, Dabih, Elnath), TWICE ×2 (Fafnir, Grumium), LONG ×1 (Heze), CONFIRM ×2 (Iklil, Jishui).
- Arme **A4** (`all`), **O4** (`earlier_oldest`), **S4** (`sources`); Zeiger, 4 Plätze, `b2_context_chars` = 1536, Z2b-Frage.
- Seeds **35, 36, 37** (neu). 9 Läufe × 70 Zeilen. Wächter an im Replay (aus für Konsistenz).

## Entscheidungsregel
Wie WP-Z2i mit Präfix `Z2J_` und Kandidaten O4, S4 gegen A4: `INVALID` → `NOT_TESTABLE` (< 90 % Kickoff im Kontext) → `UNSAFE` (> 0 falsch mit
Wächter) → `CHOICES_HELP` (für mindestens einen Kandidaten: Regelquote-CI > 0 **und** mehr exakte bewachte `both_exact`) → `CHOICES_PARTIAL` →
`CHOICES_NO_GAIN`. Zwei Vergleiche, keine Korrektur. Sekundär **ausdrücklich**: exakte bewachte Entscheidungen auf REVISED+TWICE je Arm (das eigentliche
Ziel), Herkunft der Zitate, überholte Werte, Tokens, Werkzeug-Nutzen.

## Erwartung vor dem Lauf
S4: Regelquote bei REVISED/TWICE deutlich höher (Kickoff + Notiz). Ob exakte Entscheidungen steigen, hängt an C3: es muss aus „Budget 60 … New budget
80“ den neuen Wert ziehen; zieht es den alten, wird es UNKNOWN (sicher, aber kein Gewinn). Mehr B2-Zitat-Text (bis 3 × 240 Zeichen) kostet
C3-Prompt-Tokens. O4 sollte Z2i-N4 ungefähr wiederholen.

## Grenzen
Linux-Cloud, 4 CPUs, kein Redmi. Schalter bleiben live Standard/aus. Diagnose, kein Kanon-PASS.
