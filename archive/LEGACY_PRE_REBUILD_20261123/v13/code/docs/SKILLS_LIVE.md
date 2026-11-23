# WP-T6 Skills und Prozeduralisierung live (§6.1–6.3, §41.6, §75, F2) — Übergabe

Code `v13/skilllive.py`, Haken in `runtime._turn` (Routing, nach dem Turn), `agi/live.on_feedback` und `operator.py` (`:skilllive`). Tests `tests/test_skilllive.py` (6).

## Automatischer Pfad ohne C_fast
- Passt der Auslöser eines TRUSTED- oder INTERNALISED-Skills, der nur eine Route setzt, gilt diese Route vor der C2-Steuerung. Der Turn ruft Needle dann gar nicht auf (`TRUSTED_SKILL_AUTOMATIC`, `skipped: C2_CONTROL`).
- Das gilt nur bei `route_override auto`. Eine Operator-Route geht immer vor.
- Rückfall auf den vollen Pfad in drei Fällen:
  - Ein freigegebener Skill-Kopf (WP-T1) legt sein Veto ein. Dann läuft der volle C_fast-Pfad.
  - Der Turn endet nicht mit FINAL (Fehler, Deadline). Der Skill fällt auf SHADOW zurück (`skills.reopen`).
  - Eine Routen-Korrektur des Nutzers (`:feedback route …`) widerspricht der Skill-Route. Auch dann fällt der Skill zurück.

## Skill-Selector im normalen Turn
- Passende CANDIDATE- oder SHADOW-Skills werden mit der Route verglichen, die der volle Pfad gewählt hat. Das ergibt die Parität, gebucht mit dem Turn-Ergebnis.
- So steigen Skills durch normale Nutzung auf, nicht nur über `:growth`. Es gilt der übliche Lebenszyklus: 3 bzw. 8 Erfolge, Parität ≥ 0,95. TRUSTED für Skills mit Herkunft SELF braucht Age procedural_memory oder den Nutzer.

## Gewohnheiten
- Der Cue-Schlüssel sind die ersten 3 Inhaltswörter einer Frage. Kommt derselbe Schlüssel 5-mal mit FINAL-Antwort vor und nimmt in mindestens 90 % der Fälle dieselbe Route, entsteht ein CANDIDATE-Skill `habit_<hash>` (Herkunft SELF, ein Route-Schritt).
- Höchstens 200 Schlüssel werden gezählt. Bei gemischten Routen entsteht kein Habit.

## Offen
- „Spätes internes Offer unterbricht laufende Ausgabe“ ist seit WP-U3 gebaut (`latewatch.py`, Standard SHADOW), siehe `LATE_WATCH.md`.
- Skills mit Werkzeug-Schritten laufen weiter nur über `:growth` und die ToolRegistry-Gates.
