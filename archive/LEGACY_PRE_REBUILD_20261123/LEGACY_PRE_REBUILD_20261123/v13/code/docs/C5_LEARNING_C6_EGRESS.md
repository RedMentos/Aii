# WP-N4 Rest: gelernte C5-Aktionsauswahl + C6-Egress (§6.4, §11.1–11.2, §85.5, IH-H29)

Code: `v13/actionlearn.py`, Hook in `focal.ActionGate.select` · Tests: `tests/test_actionlearn.py` (4) · Befehl: `:c5 [status|shadow|active]`

- **Zwei getrennte Pfade statt GO-Logit (§85.5)**: je (Kontext = Route + Effort-Band, Aktion) laufende Mittelwerte
  getrennter Modulatoren. *promote*: task_success, human_approval. *suppress*: cost_error, action_prediction_error
  (Fast-Forward-Überraschung), rule_violation (C6), human_correction, world_mismatch (WP-N9 MIXED). Verschiebung =
  promote − suppress, begrenzt auf ±0,2. `:c5` zeigt pro Aktion, warum sie gefördert oder gehemmt wird.
- **SHADOW** (Standard): ActionSelection-Paket enthält `learning` = gelernte Wahl neben BOOT-Wahl; Übereinstimmung in `:c5`.
  **ACTIVE** (`:c5 active`, Nutzer): Scores werden verschoben. Rechte/Unterdrückungsgründe gewinnen immer (Test).
- Bewertungen (`:note`, implizit) → human_approval bzw. human_correction für die tatsächlich gewählte Aktion.
- **C6-Egress**: typisierte Prüfung vor C7 je Aktionsart (TEXT_REPORT, EXACT_RENDER, CLARIFY, TOOL_CALL), Paket
  `EgressCheck`, schreibt nie um (`rewrites=0`). TOOL_CALL nur `{tool, args}` mit registriertem Werkzeug und
  einfachen Argumenten ohne Shell-Zeichen (für WP-K/IH-H29). Verstöße → rule_violation.

## Offen
- ASK_USER/Warten bleibt bei BOOT unterdrückt; erst lernen lassen, wenn Rückfragen gemessen werden können.
- Echte Tool-Ausführung + Transaktion (IH-H14) gehört zu WP-K.

Nachtrag WP-T7 (2026-10-10): weitere Egress-Arten SYSTEM_REPORT, SNAPSHOT, CORRECTION, ACTION_PREVIEW; der Turn prüft jetzt über `broker.Broker.finalize` mit der richtigen Art (CLARIFY statt immer TEXT_REPORT). Siehe `docs/OUTPUT_BROKER.md`.
