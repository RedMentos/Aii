# Vorregistrierung WP-Z2h: B2-Zeiger mit vier statt zwei Sätzen, Aktualitäts-Wächter an (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2h_slots.py` (nutzt `step2_z2g_recency.py` als private Modulkopie),
Tests `code/tests/test_step2_z2h.py`, `code/tests/test_b2_quote_select.py::test_pointer_slots`.

## Warum
WP-Z2g (`../step2-z2g-recency/BEFUND.md`): Wächter bestätigt (falsch 24 → 0), aber 412/420 Zeilen UNKNOWN. Bei geänderten Regeln muss B2 die
unveränderten Kickoff-Regeln **und** die Änderung liefern, bei langen Notizen stehen die drei Regeln in drei Sätzen; zwei Zeiger-Plätze reichen kaum.

## Änderung
Neuer Schalter `b2_quote_slots` (2..4, **Standard 2** = bisheriges Verhalten, Prompt und Schema byte-gleich), wirkt nur mit `b2_quote_select=pointer`:
Schema `maxItems` und Anweisung „at most N choices“; Kettenglied `integrated_candidates.b2_quote_slots`.

## Aufbau
- Zehn **frische** Episoden: LONG ×3 (Wezen, Yed, Zaniah), REVISED ×4 (Acrux, Botein, Caph, Diphda; jede Änderung ändert die Aktion),
  TWICE ×1 (Errai, gleiche Regel zweimal, jeder Wert andere Aktion), CONFIRM ×2 (Furud, Gienah).
- Arme **P2** (Zeiger, 2 Plätze = Z2g-Zeiger) und **P4** (Zeiger, 4 Plätze); beide `b2_context_chars` = 1536, Z2b-Frage, Werkzeug-Replay.
- Seeds **29, 30, 31** (neu). 6 Läufe × 70 Zeilen. Jede aufgezeichnete Extraktion wird mit Wächter **an** (und aus, Konsistenz) neu entschieden,
  Historie wie Z2g (frühere Quellen, je 240 Zeichen).

## Entscheidungsregel (in dieser Reihenfolge)
1. `Z2H_INVALID`: Strukturfehler oder Wächter-aus reproduziert nicht 100 % der aufgezeichneten Aktionen.
2. `Z2H_NOT_TESTABLE`: Kickoff-Notiz in < 90 % der B2-Angebote eines Arms im Kontext.
3. `Z2H_UNSAFE`: mit Wächter > 0 falsche Festlegungen in einem Arm.
4. `Z2H_SLOTS_HELP`: B2-Regelquote (B2-Zitate nennen alle aktuellen Regeln, 4 B2-Varianten) P4 − P2, Cluster-Bootstrap über die 10 Episoden,
   untere CI-Grenze > 0 **und** mehr exakte bewachte Entscheidungen in `both_exact` (P4 > P2, alle Seeds zusammen).
5. `Z2H_SLOTS_PARTIAL`: Regelquote-CI > 0, aber nicht mehr exakte Entscheidungen. 6. sonst `Z2H_SLOTS_NO_GAIN`.
Sekundär: je Typ, gewählte Sätze je Angebot, überholte Werte in Zitaten, B2-Prompt-Tokens, Werkzeug-Nutzen, CI der exakten Entscheidungen.

## Erwartung vor dem Lauf
P4 sollte bei LONG und REVISED öfter alle Regeln liefern. Risiken: B2 wählt trotz vier Plätzen nur ein bis zwei Sätze (dann NO_GAIN, Messgröße
„gewählte Sätze“ zeigt es); mehr Sätze bringen mehr überholte Werte mit (der Wächter muss sie abfangen); C3 extrahiert aus mehr Text schlechter.

## Grenzen
Linux-Cloud, 4 CPUs, kein Redmi. Keine Kontrolle ohne Zeiger in diesem Lauf (Z2g hat sie). Schalter bleiben live aus/Standard
(`b2_quote_select` aus, `b2_quote_slots` 2, `b2_context_chars` 768). Diagnose, kein Kanon-PASS.
