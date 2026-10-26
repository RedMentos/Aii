# Vorregistrierung WP-Z2-Q3 (Skript z2g): Körper-Frage aus dem ausgelösten Werkzeug (2026-10-26)

Vor jeder Inferenz geschrieben und gepusht. Linux-Cloud, gleiche Modelle/Runner, kein Redmi.

## Frage
Z2e: Eine allgemeine Frage hilft nicht. Z2f: Eine aus der Nachricht abgeleitete Frage war nicht auswertbar, weil ungültiges
Körper-JSON entstand. Die gezielte Frage hilft (+.23 bis +.33). Kann sie live laufen, ohne den normalen Chat zu berühren?
Dazu fragt das System die Körper nur dann, wenn die feste Auslöse-Regel eines Werkzeugs auf die aktuelle Nachricht passt.
Gefragt wird dann, was dieses Werkzeug braucht.

## Änderung (Schalter, Standard aus)
`cfg body_question_mode='tool'`: `bodyq.tool_focus` → `eligibility.question(text)` passt → `eligibility.BODY_QUESTIONS`
(Text = Z2b-Fragen). Passt keine Regel, wird nichts gefragt. Kettenglied `integrated_candidates.body_question_tool`,
Tests `tests/test_bodyq.py`. Auf den Z2-Episoden löst die Regel in 10/10 aktuellen Nachrichten aus, in 0/30 Vorrunden.

## Aufbau
`scripts/step2_z2g_tool.py`, Seeds **29/30/31**, Arme C (keine Frage), CL (Z2b-Fragen als fester Text, in jeder Runde),
CT (Werkzeug-Frage, nur bei Auslöser).

## Entscheidungsregel (fest)
TOOL_QUESTION_SUPPORTED genau dann, wenn (1) CT − C Mittel > 0 mit 95-%-KI-Untergrenze > 0, (2) CT − CL Mittel ≥ −0,05,
(3) 0 falsch festgelegte Werkzeug-Zeilen in CT, (4) alle CT-Läufe strukturell vollständig. Bricht ein Lauf am Werkzeug-
Replay ab, ist das Urteil NOT_SUPPORTED.

## Folge
Bei SUPPORTED schlage ich vor, `body_question_mode=tool` als Standard einzuschalten. Es wirkt nur bei Werkzeug-Fragen,
der Nutzer hat das Werkzeug fürs Handy gewählt.

> Paketname geändert (Name geändert: Thread „B2 zitiert Regel selten“ vergab Z2e/Z2f parallel; Code/Skripte heißen weiter z2e/z2f/z2g).
