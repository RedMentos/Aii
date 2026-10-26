# Vorregistrierung WP-Z2i: aus welchen Sätzen B2 wählen darf (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2i_choices.py` (nutzt `step2_z2h_slots.py` als private Modulkopie),
Tests `code/tests/test_step2_z2i.py`, `code/tests/test_b2_quote_select.py`.

## Warum
WP-Z2h (`../step2-z2h-slots/BEFUND.md`): vier Plätze bringen nichts, weil B2 nach Position wählt — knapp die Hälfte der Nummern sind 1–3, die Sätze
der aktuellen Aufgabe (die C3 ohnehin bekommt); aus der Änderungsnotiz kamen 9 von 178 gewählten Sätzen.

## Änderung
Neuer Schalter `b2_quote_choices` = `all` (**Standard**, bisheriges Verhalten byte-gleich) | `earlier` (nur Sätze der früheren Quellen-Auszüge) |
`earlier_newest` (dieselben, jüngste frühere Quelle zuerst). Nur mit Zeiger; ohne frühere Quelle bleibt die alte Liste. Kettenglied
`integrated_candidates.b2_quote_choices`.

## Aufbau
- Zehn **frische** Episoden: REVISED ×5 (Hamal, Keid, Mebsuta, Nashira, Okab), TWICE ×2 (Pollux, Rasalas), LONG ×1 (Sadr), CONFIRM ×2 (Tureis, Wasat).
- Arme **A4** (`all`, = Z2h-P4), **E4** (`earlier`), **N4** (`earlier_newest`); alle Zeiger mit 4 Plätzen, `b2_context_chars` = 1536, Z2b-Frage.
- Seeds **32, 33, 34** (neu). 9 Läufe × 70 Zeilen. Wächter an im Replay wie Z2g/Z2h (und aus für die Konsistenz).

## Entscheidungsregel (in dieser Reihenfolge)
1. `Z2I_INVALID`: Strukturfehler, Wächter-aus nicht 100 % konsistent, oder E4/N4 zitieren in B2-Varianten Sätze der aktuellen Aufgabe.
2. `Z2I_NOT_TESTABLE`: Kickoff-Notiz in < 90 % der B2-Angebote eines Arms im Kontext.
3. `Z2I_UNSAFE`: mit Wächter > 0 falsche Festlegungen in einem Arm.
4. `Z2I_CHOICES_HELP`: für **mindestens einen** von E4/N4 gegen A4: B2-Regelquote-Differenz (Cluster-Bootstrap über 10 Episoden) untere CI-Grenze > 0
   **und** mehr exakte bewachte Entscheidungen in `both_exact` (alle Seeds). Welcher Arm, wird genannt; zwei Vergleiche, keine Korrektur — offen benannt.
5. `Z2I_CHOICES_PARTIAL`: Regelquote-CI > 0, aber nicht mehr exakte Entscheidungen. 6. sonst `Z2I_CHOICES_NO_GAIN`.
Sekundär: Herkunft der gewählten Sätze (aktuell/Kickoff/Notiz/Datenblatt) auf REVISED/TWICE, je Typ, überholte Werte, Tokens, Werkzeug-Nutzen.

## Erwartung vor dem Lauf
E4: weg von der aktuellen Aufgabe, aber Positionsneigung wählt dann Kickoff-Sätze (Kopfzeile + alte Regeln) → Notiz bleibt selten; N4: Datenblatt
steht vorn, danach die Notiz — kann die Änderung öfter bringen, aber Kickoff-Regeln seltener. Gut möglich: PARTIAL oder NO_GAIN.

## Grenzen
Linux-Cloud, 4 CPUs, kein Redmi. Schalter bleiben live Standard/aus. Diagnose, kein Kanon-PASS.
