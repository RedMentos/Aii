# AG-Module im Live-Durchlauf (WP-N13) — 2026-10-09

Code `v13/agi/live.py`, Tests `tests/test_agi_live.py` (6), Befehl `:live`. Vier Ein-Zeilen-Hooks in `runtime._turn`,
je einer in `memory.feedback` und `inputs.record_rating`. Jeder Hook ist fail-open: Fehler → Telemetrie `agi_live_unavailable`, Turn läuft unverändert.

| Modul | Wo im Turn | Was passiert |
|---|---|---|
| AG4 Skills → C5 | nach `_route` | Ein vom Nutzer auf TRUSTED gesetzter Skill, der nur aus Routen-Schritten besteht und dessen Trigger-Wörter alle vorkommen, setzt die Route (prozeduraler Schnellweg). Ergebnis zählt in `skills.record`. |
| AG9 Metakognition → Effort | nach `effort.signals` | Rohe Antwort-Konfidenz = 1 − Unsicherheit. Erst wenn der Kalibrierer ≥ 20 Labels hat: „zweiter Versuch“ hebt `uncertainty` auf 0,6, „weiß ich nicht“ auf 0,8 + `metacog_abstain`. Routen-Konfidenz (kalibrierte Needle oder gelernter Kopf) genauso. Unkalibriert ändert nichts. |
| AG2 Grounding → Aktion | nach `start_action` / im `finally` | Vorhersage des Ergebnisses vor dem Handeln (Häufigkeits-Basis je Rolle+Route), danach echtes Ergebnis → Fehlerrate je Rolle. |
| AG11 Nutzer-Modell → C1 | `memory.feedback` | `:feedback preference/style` wird beleggebundene Annahme (geschützte Merkmale werden abgelehnt); der Turn trägt die Zusammenfassung (`meta['user_model']`). |
| AG0 Slots → ModelManager | im `finally` | Installierte Modelle werden in Slots gespiegelt; neue Revision (z. B. `:import`) → Tausch-Vorschlag mit Asset-Plan statt stillem Veralten. |

Labels für AG9: Bewertung `:note`/implizit (≥ 6 richtig, ≤ 4 falsch, 5 nichts), Faktenkorrektur = falsch, `:feedback route` = Routen-Label.

## Offen
- C1/Executive liest die Nutzer-Annahmen noch nicht in `constraints` (Besitzer WP-D/executive.py); Präferenzen kommen weiter als Erinnerungen in den Kontext.
- Abstention ist nur ein Flag; C5 `ASK_USER` ist bei BOOT unterdrückt (WP-N4).
- Tool-Skills (mit Werkzeug-Schritten) laufen nicht live, erst mit WP-K.
- Grounding-Vorhersage ist die Häufigkeits-Basis; World-JEPA steckt später über `predicted=` ein.

## WP-N13 rest (Pakete E, 2026-10-10)
- **AG11 → C1 + answer.** Beliefs with confidence ≥ 0.5 (`live.BELIEF_MIN`) go into `ExecState.user_beliefs` (labelled `BELIEF_NOT_FACT`, max 6) and the C2 control view. They never enter `constraints`: fixed rules stay the only constraints, so control admissibility is unchanged. The answer prompt gets a labelled `USER_MODEL` layer (`prompts.user_model`) only when such beliefs exist.
- **AG9 abstain → C5 ASK_USER.** A calibrated abstention (`metacog_abstain`) passes `clarify` to `ActionGate.select`. SHADOW (default) leaves ASK_USER suppressed (`WAIT_VS_ACT_BIAS_BOOT`) and records the hint in the ActionSelection packet and `meta['clarify']`. ACTIVE (`:live ask active`, explicit human only) un-suppresses ASK_USER with utility 1.0; C3 then voices one short clarifying question (`prompts.clarify`, layer `CLARIFY`). Exact/fixed outputs are never replaced.
- `:live [status|ask shadow|ask active]`. Tests: `tests/test_agi_live.py::ClarifyAndUserModel` (2). Full suite 788 green.
- Open: whether asking beats guessing must be measured on real turns (ratings after clarify turns); tool skills (AG4 → C5) stay with WP-K/AG10.
