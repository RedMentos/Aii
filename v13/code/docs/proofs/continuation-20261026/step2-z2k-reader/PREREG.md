# Vorregistrierung WP-Z2k: jüngster zitierter Regelwert statt C3-Wert (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2k_reader.py` (nutzt `step2_z2i_choices.py` als private Modulkopie),
Tests `code/tests/test_step2_z2k.py`.

## Warum
WP-Z2j (`../step2-z2j-sources/BEFUND.md`): mit ganzen Quellen als B2-Wahl kommen die Regeln an (Regelquote .71), aber C3 (LFM2.5-350M) nimmt bei
geänderten Regeln den alten Wert (10/10); der Wächter macht daraus UNKNOWN.

## Änderung
`eligibility.decide/tool(..., rule_reader='newest_quoted')` (Standard `model` = bisher; wirkt nur mit `history`): Für jede Regel gilt der Wert, den die
aktuelle Quelle eindeutig nennt; sonst der Wert der **jüngsten** früheren Sitzungsquelle, die die Regel nennt — **nur wenn** dieser Wert in einem
geprüften Zitat oder der aktuellen Quelle steht. Nur dann ersetzt er den C3-Wert (auch einen leeren). Sonst gilt alles wie bisher (Wächter).

## Explorativ vorab (gesehene Daten, zählt nicht) — `explore_seen_data.txt`
Z2j S4: exakt 22 → 48 / 210, geänderte Regeln 0 → 25, falsch 0 → 0. Alle anderen Arme Z2f–Z2j: exakt steigt oder bleibt, falsch überall 0.

## Aufbau
- Zehn **frische** Episoden: REVISED ×6 (Kaus, Lucida, Maia, Nekkar, Peacock, Rukbat), TWICE ×2 (Sargas, Thuban), CONFIRM ×2 (Vindemiatrix, Zosma).
- Arme **A4** (Zeiger, alle Sätze, 4 Plätze) und **S4** (Zeiger, ganze frühere Quellen); `b2_context_chars` = 1536, Z2b-Frage, Werkzeug-Replay.
- Seeds **38, 39, 40** (neu). 6 Läufe × 70 Zeilen. Jede Extraktion dreimal entschieden: Wächter aus (Konsistenz), Wächter an, Wächter an + Leser.

## Entscheidungsregel (in dieser Reihenfolge)
1. `Z2K_INVALID`: Strukturfehler oder Wächter-aus nicht 100 % konsistent. 2. `Z2K_NOT_TESTABLE`: Kickoff < 90 % im Kontext eines Arms.
3. `Z2K_UNSAFE`: mit Leser > 0 falsche Festlegungen in einem Arm.
4. `Z2K_READER_CONFIRMED`: S4, exakte Entscheidungen Leser − nur Wächter (je Episode, über Seeds gemittelt, alle Varianten), Cluster-Bootstrap über die
   10 Episoden, untere CI-Grenze > 0 **und** keine Zeile, die nur mit Wächter exakt war und mit Leser nicht mehr.
5. `Z2K_READER_PARTIAL`: mehr exakte, aber CI schließt 0 ein oder Verluste. 6. sonst `Z2K_READER_NO_GAIN`.
Sekundär: A4 ebenso, je Typ, `both_exact`, Zeilen mit ersetztem Wert, falsch ohne Wächter, Werkzeug-Nutzen.

## Erwartung vor dem Lauf
S4 deutlich mehr exakte bei geänderten Regeln (Zitate tragen Kickoff + Notiz); A4 kaum Gewinn (Notiz selten zitiert). Risiko: Notiz-Satz wird zitiert,
aber in einer Form, die die Regel-Erkennung nicht liest — dann bleibt es UNKNOWN (sicher).

## Grenzen
Linux-Cloud, 4 CPUs, kein Redmi. Der Leser ist ein festes Regelwort-Muster (Budget/Deadline/Local-only), kein allgemeiner Leser; er gilt nur für das
Eignungs-Werkzeug. Schalter bleiben live Standard/aus. Diagnose, kein Kanon-PASS.
