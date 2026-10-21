# Verbote, Notaus, Vorabansage (2026-10-21)

Ziel des Nutzers: Die KI tut nichts, wovon er nichts weiß, sagt vorher, was sie tun würde, und legt seine Verbote nie falsch aus.

## Wo die Regelprüfung sitzt

| Schicht | Datei | Was sie tut |
|---|---|---|
| Feste Verbote + Notaus (neu) | `v13/prohibitions.py` | Tabelle mit Zeilen wie „Werkzeug sandbox_note verboten“. Wird nur über exakten Namensvergleich geprüft, kein Modell liest oder deutet sie. |
| Werkzeug-Regeln (IH-H29) | `v13/transaction.py` `authorize()` | Reihenfolge: **Verbote** → Argument-Schema → vom Nutzer freigeschaltet? → Risiko (Schreiben/Netz/Außenwirkung → Einzelfreigabe) → **Vorabansage** → Age-Recht. Reiner Code, kein Modell. |
| Letztes Tor | `v13/transaction.py` `Transactions.execute()` | Liest die Verbote direkt vor der Ausführung **noch einmal**. Wenn oben etwas fälschlich „erlaubt“ gesagt hat, wird hier trotzdem abgebrochen (`CANCELLED`, die Funktion läuft nie). |
| Werkzeug-Register | `v13/agi/tools.py` | Jeder Aufruf geht durch `authorize()`. Standard: kein Werkzeug freigeschaltet. |
| Aktionswahl C5 | `v13/focal.py` `ActionGate` | Ein Werkzeug, das die Regeln ablehnen, wird unterdrückt. Gelernte Punktzahlen (`actionlearn.py`) können Unterdrückungen nicht aufheben. |
| Befehle | `v13/operator.py` `run()` | Befehle (`:verbot`, `:notaus`, `:tx approve`) laufen nur von der Tastatur des Nutzers (`OPERATOR_TTY`). Modelltext wird nie als Befehl ausgeführt. |

Woher kommt ein Werkzeug-Vorschlag? Aus einer festen Textregel über die Nutzereingabe (`toolstep.py`, z. B. „48 mal 37“ → calc). Nur bei `list_arith` liest das Sprachmodell Zahlen aus dem Text, und ein fester Wächter prüft, dass jede Zahl wörtlich im Text steht. Modelle **schlagen höchstens vor**, sie **erlauben** nie.

## Verbote: fest, nicht gelernt

- Ein Verbot ist eine feste Zeile: `werkzeug <Name>`, `art READ_LOCAL|WRITE_LOCAL|NETWORK|EXTERNAL_EFFECT`, `unumkehrbar`, `alles`.
- Kein freier Text, also nichts, was falsch ausgelegt werden kann. Ein Tippfehler im Namen wird abgelehnt.
- Nach jeder Eingabe antwortet V13 in einfachem Deutsch, was **genau** jetzt verboten ist. Der Nutzer sieht die Auslegung sofort.
- Ändern kann es nur der Nutzer selbst (`authority=EXPLICIT_HUMAN`). Kein Modell, kein Selbst-Edit, kein Lernpfad.
- Ist die Tabelle beschädigt, gilt automatisch Notaus (alles gesperrt), bis der Nutzer sie neu setzt.
- Ein Verbot gilt auch dann, wenn der Nutzer später einen einzelnen Aufruf freigibt. Erst `:verbot weg V1` hebt es auf.
- Ein verbotenes Werkzeug läuft auch nicht heimlich „im Schatten“ mit.

Freitext-Regeln („sei höflich“) bleiben nur Hinweise im Prompt. Das steht ehrlich in `:permissions`.

## Befehle

```
:verbot                         Liste in einfachem Deutsch
:verbot werkzeug sandbox_note   ein Werkzeug verbieten
:verbot art NETWORK             alles mit Internet verbieten
:verbot unumkehrbar             alles verbieten, was man nicht rückgängig machen kann
:verbot alles                   alle Werkzeuge verbieten
:verbot weg V1                  Verbot V1 aufheben
:verbot ansage an|aus           jede Aktion vorher zeigen, erst nach :tx approve ausführen
:notaus                         sofort alles stoppen (auch offene Freigaben)
:notaus aus                     Notaus aufheben
```

## Tests (`tests/test_prohibitions.py`, 16 Tests, keine Modelle)

- Modell schlägt Ausnahme vor („der Nutzer erlaubt es heute“) → abgelehnt, für jede Herkunft (SYSTEM, SELF, USER).
- Einzelfreigabe nach dem Verbot → abgelehnt, Datei nicht geschrieben.
- Alles oberhalb sagt fälschlich „erlaubt“ → das letzte Tor stoppt, die Funktion läuft nie (`EXECUTING` wird nie erreicht).
- Ganzer Gesprächszug: Nutzertext bittet um Ausnahme, die (falsche) Modellantwort enthält `:verbot weg V1` und `:tx approve` → nichts passiert, das Verbot bleibt.
- Notaus: blockiert alle Aufrufe und offenen Freigaben; Rückgängig machen geht weiter.
- Vorabansage: selbst Rechnen wird erst gezeigt („Aktion wartet auf Freigabe“) und läuft erst nach `:tx approve`.
- Nur der Nutzer kann Verbote/Notaus ändern; beschädigte Tabelle → alles gesperrt.

## Neuromodulation und Selbst-Unsicherheit: wirkt es oder wird nur protokolliert?

- **Neuromodulations-Veto** (`neuromod.py` → `learning.py` → `plasticity.py`): wirkt echt, aber nur aufs **Lernen**. Ein Veto setzt den Lernfaktor auf 0 und bricht den Trainingsjob ab; sonst skaliert der Faktor Lernrate und Update-Größe. Einschränkungen: Im Standard (`learning_mode=RECORD_ONLY`) läuft gar kein Gewichtslernen, das Veto hat dann nichts zu sperren. Im Live-Betrieb setzt bisher nur ein C6-Regelverstoß das Veto; `safety_veto=True` kommt nur in Tests vor. Das Veto steuert **keine Aktionen**; dafür sind die festen Verbote da.
- **Selbst-Unsicherheit** (`agi/metacog.py`, `agi/live.py`): wirkt teilweise. Ist sie kalibriert, hebt sie live den Rechenaufwand (Effort-Modus `adaptive` ist Standard): mehr Körper wecken, zweiter Versuch. „Lieber nachfragen statt raten“ (ASK_USER) läuft im Standard nur im Beobachtungsmodus; aktiv nur nach ausdrücklicher Nutzerfreigabe.
- Gelernte Aktionswahl (`actionlearn.py`) steht im Beobachtungsmodus und kann Verbote ohnehin nie aufheben.

## Ehrliche Grenzen

- Die Risikoklasse eines Werkzeugs schreibt der Programmierer beim Registrieren hin; sie wird nicht nachgemessen. Neue Werkzeuge brauchen deshalb Code-Review.
- Notaus stoppt Werkzeuge und Freigaben, nicht das Schreiben von Antworttext (Text hat keine Außenwirkung; `:cancel` bricht den laufenden Zug ab, Notaus ruft das mit auf).
- Das Weltmodell kennt Verbote noch nicht als Vorhersage („wenn ich das täte, wäre es verboten“). Das ist nur ein Plan-Hinweis, kein Sicherheitsproblem, weil die Prüfung ohnehin im Code passiert.
