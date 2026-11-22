# TOOL_CALL als C5-Kandidat im Live-Turn (WP-K-Rest, WP-AG10, WP-N4) — Übergabe

Code `v13/toolstep.py`, Tests `tests/test_toolstep.py`, Paket `ToolProposal` (contracts), Hooks in `runtime._turn` und `focal.ActionGate`.

Ablauf je Turn (nicht bei exakter Kopie/fester Regel):
1. **Vorschlag (C2-artig, BOOT-Regex `boot-arith-v1`)**: konkrete Rechnung → `calc` mit Ausdruck (`48 times 37`, `17% of 2,340`, `(12+8)*3`, `2 to the power of 20`). Daten/IDs/Jahreszahlen werden nicht geraten.
2. **IH-H29-Politik** über `ToolRegistry._policy(origin='SYSTEM')`: Schema → vom Nutzer erlaubt (`:growth enable calc`) → Risiko → Bestätigung → Age-Recht `simple_tool_choice` (Age 1). Ergebnis als `ToolProposal` (truth_authority 0).
3. **C5**: der Vorschlag ist der `EXTERNAL_TOOL`-Kandidat (Nutzen .5+.5·Konfidenz, Klasse `local_tool` für READ_LOCAL). Verweigert → unterdrückt mit `TOOL_POLICY:<Grund>`.
4. **Gewinnt TOOL_CALL**: Ausführung als IH-H14-Transaktion (idempotent je Event), Ergebnis als Schicht `TOOL_RESULT` für den antwortenden Körper (nächstbeste Alternative), `meta.tool_call`. Grounding-Ergebnis über AG2 (provisional bis FINAL).
5. **Verweigert (Age 0 Standard)**: SHADOW. Nur reine READ_LOCAL-Werkzeuge (calc) werden abseits gerechnet, nie gezeigt; nach der Antwort Vergleich „stand das Ergebnis in der Antwort?“. Zählung im State `TOOL_SHADOW_AGREEMENT`, `toolstep.report(store)`. Das ist Beleg für ein späteres Age-1-Werkzeugrecht, keine Erlaubnis.

Offen: Needle/C2-Werkzeugwahl statt Regex (siehe `bench-results/c2-benchmark-20261010`), weitere Werkzeuge, Operator-Ansicht.

Nachtrag WP-T7 (2026-10-10): Proposer jetzt `boot-arith-note-v2` (auch `sandbox_note` für ausdrückliche Notiz-Bitten). Ein erlaubtes Schreib-Werkzeug wird im Turn als PROPOSED mit Dry-Run-Vorschau angelegt und vom Output-Broker mit `:tx approve <id>` gezeigt; Details `docs/OUTPUT_BROKER.md`.
