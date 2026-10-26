# Vorregistrierung WP-Z2g: Aktualitäts-Wächter im Eignungs-Werkzeug, Bestätigung auf frischen Episoden (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2g_recency.py` (nutzt `step2_z2e_pointer_hard.py` als private Modulkopie),
Tests `code/tests/test_step2_z2g.py`, `code/tests/test_recency_guard.py`.

## Warum
WP-Z2f (`../step2-z2f-context/BEFUND.md`): mit `b2_context_chars` = 1536 zitiert B2 überholte Regeln exakt, das Werkzeug legte sich 27-mal falsch fest,
immer auf die Aktion der alten Regel. Ein nach Sicht dieser Fehler entworfener Wächter nahm alle 27 weg, ohne eine richtige Entscheidung zu verlieren.
Er ist jetzt `v13.agi.eligibility.decide(..., history=...)` (und `tool(..., history=...)`): ein Regelwert, den die aktuelle Quelle nicht nennt, zählt
nur, wenn die **jüngste** frühere Sitzungsquelle, die diese Regel nennt, genau diesen Wert nennt; sonst „nicht verfügbar“ (`<regel>:superseded`).
Leere Historie = Wächter aus = bisheriges Verhalten. Die Bibliotheksfassung reproduziert auf den Z2f-Daten das explorative Ergebnis exakt
(7/18/2 → 0/0/0 falsch, exakte Entscheidungen 32/37/25 unverändert, Konsistenz 630/630).

## Aufbau
- **Zehn frische Episoden**, nie gelaufen: REVISED ×6 (je eine Änderung, jede Regel einmal hoch und einmal runter; jede Änderung ändert die richtige
  Aktion), TWICE ×2 (dieselbe Regel zweimal geändert, jüngste gilt, jeder Wert gibt eine andere Aktion), CONFIRM ×2 (Statusnotiz wiederholt eine
  Kickoff-Regel mit gleichem Wert; der Wächter darf sie nicht verwerfen).
- Arme **CQ** (Zeiger aus) und **CQP** (Zeiger an), beide `b2_context_chars` = 1536, Z2b-Frage, Werkzeug-Replay unverändert (Wächter aus).
- Seeds **26, 27, 28** (neu). 6 Läufe × 70 Zeilen.
- Danach je Zeile mit aufgezeichneter Extraktion deterministisch zweimal entscheiden: Wächter **aus** (muss die aufgezeichnete Aktion reproduzieren)
  und Wächter **an**, Historie = frühere Sitzungsquellen als behaltene Auszüge (erste 240 Zeichen je Quelle, B2-Slot-Auszug §85.1).

## Entscheidungsregel (in dieser Reihenfolge)
1. `Z2G_INVALID`: ein Lauf strukturell fehlerhaft oder Wächter-aus reproduziert nicht 100 % der aufgezeichneten Aktionen.
2. `Z2G_NOT_TESTABLE`: Kickoff-Notiz in < 90 % der B2-Angebote eines Arms im Kontext, **oder** ohne Wächter < 5 falsche Festlegungen (alle Läufe
   zusammen) — dann gibt es nichts zu bestätigen.
3. `Z2G_GUARD_CONFIRMED`: mit Wächter **0** falsche Festlegungen **und** exakte Entscheidungen mit Wächter ≥ ohne Wächter (alle Läufe zusammen).
4. `Z2G_GUARD_SAFE_BUT_COSTLY`: 0 falsch, aber exakte Entscheidungen verloren (Anzahl und Typ werden genannt).
5. `Z2G_GUARD_PARTIAL`: weniger falsch als ohne Wächter, aber > 0. 6. sonst `Z2G_GUARD_FAILS`.
Sekundär: je Typ und Arm, Fehlverwerfungen bei CONFIRM, B2-Regelquote, überholte Werte in Zitaten, Werkzeug-Nutzen.

## Erwartung vor dem Lauf
Wächter ist deterministisch; bei exakt zitierten alten Regeln sollte er greifen. Risiken: (a) C3 extrahiert einen Wert, der weder alt noch neu ist —
dann greift schon die bestehende Prüfung; (b) TWICE: die mittlere Änderung zitiert, jüngste nicht — Wächter muss sie verwerfen; (c) CONFIRM:
Fehlverwerfung wäre ein Konstruktionsfehler. Möglich ist auch NOT_TESTABLE, falls C3/B2 auf diesen Episoden kaum alte Regeln weiterreicht.

## Grenzen
Linux-Cloud, 4 CPUs, kein Redmi. Die Historie im Replay kommt aus den Episoden (so, wie die Sitzung sie behalten hätte), nicht aus dem Live-Speicher;
der Live-Aufrufer muss sie selbst übergeben. Schalter bleiben aus (`b2_quote_select` aus, `b2_context_chars` live 768). Diagnose, kein Kanon-PASS.
