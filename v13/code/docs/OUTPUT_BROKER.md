# WP-T7: Action Gate mit Vorschau, Egress, Output-Broker (§6.4, §11, C6/C7). Übergabe von Pakete A, 2026-10-10

Code:
- `v13/broker.py` (neu)
- `v13/toolstep.py` (Notiz-Vorschlag, `propose_call`, `pending_layer`)
- `v13/agi/tools.py` (`ToolSpec.preview`, `ToolRegistry.preview`)
- `v13/transaction.py` (Dry-Run für `sandbox_note`, `:tx broker`)
- `v13/actionlearn.egress` (neue Egress-Arten)
- Hooks in `runtime._turn` und `runtime.force_report`

Tests: `tests/test_broker.py` (10).
Paket: `OutputBrokerDecision` (contracts; `rewrites` muss 0 sein, nur bekannte Autoritäten).

## Aktion im Sandbox-Modus: Vorschau, Freigabe, Rücknahme
1. **Vorschlag.** Der BOOT-Proposer `boot-arith-note-v2` erkennt ausdrückliche Notiz-Bitten und schlägt `sandbox_note` vor (WRITE_LOCAL, schreibt nur nach `data/tool_sandbox/<name>.txt`, rücknehmbar). Beispiele:
   - „Save a note called shopping: buy milk“
   - „note down: call Anna“, Name aus den ersten Wörtern
   Rechnen (`calc`) bleibt wie bisher.
2. **Politik nach IH-H29.**
   - Ohne `:growth enable sandbox_note` lautet das Ergebnis `DENIED TOOL_NOT_ENABLED_BY_USER`. Es gibt dann keine Vorschau und keine Nachricht.
   - Mit Erlaubnis lautet es `PROPOSED NEEDS_PER_CALL_APPROVAL`. Schreiben braucht immer eine Freigabe pro Aufruf, und C5 unterdrückt den Kandidaten mit `TOOL_POLICY:`.
3. **Vorschau.**
   - `ToolStep.propose_call` legt den Aufruf als PROPOSED im Werkzeug-Register an, mit `preview`. Der Dry-Run zeigt CREATE oder REPLACE, das Ziel, alte und neue Länge und die ersten 200 Zeichen.
   - Es gibt keinen Schreibzugriff. Secrets werden nie aufgelöst.
   - Werkzeuge ohne Dry-Run melden `UNKNOWN_NO_DRY_RUN`.
4. **Körper.** Die Schicht `TOOL_PENDING` sagt dem antwortenden Modell: „Not executed … do not say it was done“.
5. **Nachricht.**
   - Nach der Antwort zeigt der Broker eine eigene Nachricht mit Rolle `broker`: „[Aktion wartet auf Freigabe] … Freigeben: `:tx approve <id>` · danach rücknehmbar: `:tx undo <id>`“.
   - Die Freigabe läuft als IH-H14-Transaktion. Dabei wird die Kopie vor der Wirkung gespeichert, EXECUTING wird festgehalten, und die Rücknahme ist eine eigene Transaktion.

## Output-Broker: wer die sichtbare Ausgabe besitzt
Rangfolge vor dem Commit-Punkt (IH-H12):
1. `APPROVED_FIXED_RULE`
2. `EXPLICIT_EXACT_COPY`
3. `MODEL_ANSWER`
4. `SOURCE_SYSTEM_REPORT`

Eine feste Regel schlägt also auch „Copy exactly:“. Teil-Text des Modells schlägt den Diagnosebericht.

Nach dem Commit wird nichts ersetzt. Späteres Material erscheint nur als eigene Nachricht mit Rolle `broker`:
- **CORRECTION**
  - Fall: Ein ausgeführtes Werkzeug-Ergebnis fehlt in der FINAL-Antwort (`ANSWER_OMITS_TOOL_RESULT`). Der Broker zeigt dann den exakten Wert.
  - Flag `tool_conflict_policy`: `correct` (Standard) oder `log` (nur protokollieren). **Bitte prüfen.**
- **ACTION_PREVIEW**: der oben beschriebene Vorschlag.

`broker`-Zeilen zählen nie als Antwort. Native History, Memory-Spuren, `last_answer` und Trainingszeilen lesen nur user/assistant.

Behauptet die Antwort, eine ausstehende Aktion sei erledigt, wird das als Konflikt `ANSWER_CLAIMS_PENDING_ACTION_DONE` protokolliert. Die Vorschau-Nachricht stellt es richtig. Der Modelltext selbst wird nie umgeschrieben (`rewrites=0`).

SNAPSHOT (`force_report`) ist nur lesend. Er bekommt eine eigene C6-Prüfung, aber keine neue Nachricht.

## Egress-Arten (C6, je eine Prüfung pro sichtbarer Ausgabe)
| Art | Wann | Prüft |
|---|---|---|
| TEXT_REPORT | Modellantwort | Text, nicht leer, keine Steuerzeichen, Länge |
| CLARIFY | C5 hat ASK_USER gewählt | wie oben + endet mit „?“ (früher als TEXT_REPORT geprüft) |
| EXACT_RENDER | feste Regel / exakte Kopie | gleich der Quelle |
| SYSTEM_REPORT | Fehler-/Fristbericht ohne Modelltext | Text |
| SNAPSHOT | `force_report` | Marker `[CURRENT_OUTPUT_SNAPSHOT` |
| CORRECTION | späte Korrektur | Text, `correction_of`, Grund |
| ACTION_PREVIEW | ausstehender Aufruf | bekanntes Werkzeug, Status PROPOSED, Vorschau, `:tx approve <id>` im Text |
| TOOL_CALL | (WP-K) | registriertes Werkzeug, typisierte Argumente |

Der Broker ersetzt den alten Einzelaufruf `check_output` im Turn. C5 lernt `rule_violation` jetzt aus der richtigen Art.
Die Übersicht liefert `:tx broker`: Autoritäten, Konflikte und späte Nachrichten der letzten 200 Turns.

## Grenzen / offen
- Der Proposer ist Regex und nicht gelernt. Es gibt nur zwei Werkzeuge (calc, sandbox_note). Netz und externe Wirkungen bleiben reine Vorschläge ohne Werkzeug.
- `ANSWER_OMITS_TOOL_RESULT` prüft nur Zahlen bzw. skalare Werte. Ob die Antwort *inhaltlich* stimmt, beurteilt der Broker nicht.
- Ein PROPOSED-Aufruf aus einem abgebrochenen Turn bleibt im Register (`:growth tools`) und wird nicht angezeigt. Ein Ablauf (TTL) für offene Vorschläge fehlt.
