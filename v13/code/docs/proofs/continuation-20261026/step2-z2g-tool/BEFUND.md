# Befund WP-Z2g: Körper-Frage aus dem ausgelösten Werkzeug (2026-10-26)

Vorregistriert in `09c7364`. Seeds 29/30/31, 10 Z2-Episoden, Arme C/CL/CT, 630 Zeilen + Werkzeug-Replay.
Lauf 1 stoppte am Zeitlimit im letzten Lauf (CT/31). Dieser lief unverändert von vorn (`run2_resume.log`).
Daten `bench-results/step2-z2g-tool-20261026/`.

## Urteil: **TOOL_QUESTION_SUPPORTED** (alle vier Kriterien)
| Arm | b1_only | b2_only | both_exact |
|---|---|---|---|
| C (keine Frage) | .342 | .250 | .342 |
| CL (fester Fragetext, jede Runde) | .569 | .189 | .622 |
| **CT (Werkzeug-Frage, nur bei Auslöser)** | .597 | .194 | **.608** |

- CT − C = **+.27**, 95-%-KI [+.09, +.46].
- CT − CL = −.01, KI [−.11, +.08]: so gut wie der feste Text.
- 0 falsch festgelegte Werkzeug-Zeilen; alle Läufe strukturell vollständig (kein ungültiges Körper-JSON).
- B1 zitiert die Optionswerte in 9–10 von 10 both_exact-Zeilen (C: 2–5).

## Was das heißt
Die gezielte Frage wirkt auch dann, wenn sie nur in der Runde gestellt wird, in der das Werkzeug auslöst. Damit kann sie
live laufen: Nachrichten ohne Werkzeug-Auslöser bekommen keine Frage, der normale Chat bleibt unverändert. Der Engpass auf
B2-Seite (Regelzitat) bleibt; dafür gibt es den B2-Zeiger (WP-Z2d, Thread „B2 zitiert Regel selten“).

## Grenzen
Nur STEP2-Episoden, englisch, ein Werkzeug (eligibility). Die Frage hängt nicht daran, ob der Nutzer das Werkzeug
freigegeben hat (gemessen ohne Freigabe). Linux-Cloud, kein Handy.

## Folge
Vorschlag an den Nutzer: `body_question_mode=tool` einschalten, am besten zusammen mit dem Eignungs-Werkzeug im Handy-Paket.
Bis zur Antwort bleibt der Standard aus.
