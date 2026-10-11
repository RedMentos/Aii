# WP-T10 Lern-Autorität und Beförderung Schatten → aktiv (§88.1, §17A, §14.1–14.6, IH-H25)

## Beförderungsweg (`v13/authority.py`)
Stufen je gelerntem Kopf: 0 SHADOW → 1 CANDIDATE → 2 ACTIVE.
- **Köpfe:** c5_action, jef_bridge, fast_forward, context_policy, admission, attention, deliberation, callosum, gist, neuromod_meta. Jeder hat Modus-Lesen/-Setzen, Nachweis, Lernziel (IH-H25), Gate-Graph-Knoten und Age-Fähigkeit.
- **Eigenes Gate (`verdict`).** FAIL bei Regression (gelernte Fehlerquote > Scaffold + 0,05). PASS bei Kopf-Gate (Held-out PASS, Prozedur READY, stabile Recall) oder bei ≥ 20 Schattenentscheidungen mit besseren Ergebnissen als das Scaffold oder ≥ 90 % Übereinstimmung mit ihm (§17A erste Phase). Sonst HOLD (NO_COMPARISON, TOO_FEW_SHADOW_DECISIONS, BELOW_AGREEMENT).
- **CANDIDATE** braucht zusätzlich: Lernziel IMPLEMENTED und Gate-Graph-Knoten in GREEN/PARTIAL/BLOCKED_BY_DEP, also ohne messend durchgefallenes Verdikt. Das Scaffold handelt weiter.
- **ACTIVE** nur mit `promote(…,'EXPLICIT_HUMAN')` (`:authority promote <Kopf>`) und nur aus CANDIDATE. Danach ist das Scaffold der Rückfallweg. Automatische Beförderung gibt es nicht: Age 0 hat kein Recht `safe_self_edit_without_dialog` (Age 3, BUILD_CEILING 0).
- **`review()` (mittlere Zeitskala):**
  - 0 → 1 bei bestandenem Gate.
  - 1 → 0, wenn der Nachweis wegfällt.
  - ACTIVE mit Regression → SHADOW, automatisch. Die sichere Richtung braucht keinen Menschen.
  - Telemetrie `authority_change`.
- **`observe(store, head, scaffold, learned, scaffold_ok, learned_ok)`:** generisches Schatten-Ledger für Hooks.
  - Seit 2026-10-11 speisen die vorhandenen Attention-, Deliberation- und Callosum-Controller ihre trainierten Schattenvorschläge ein. Untrainierte Rückfälle zählen nicht als gelernter Vergleich. Für gist und neuromod_meta fehlen diese Hooks weiterhin.
- **Operator:** `:authority [status|review|promote <Kopf>|demote <Kopf>|<Kopf>]`, `:objectives`.

## Lernziel-Plugin (`v13/objectives.py`, IH-H25)
- `ObjectiveAdapter` mit den zehn Vertragsfeldern plus status, reason, implementation_files, learning_rate_config_key und optional einem aufrufbaren `loss`.
- `registry()` validiert jede Zeile aus `specs/learning-objectives.json`. IMPLEMENTED braucht loss_terms, eval_metrics, update_scope, target_builder, credit_mapper und vorhandene Dateien. UNAVAILABLE/PARTIAL hat learn_gain 0, RECORD_ONLY ebenfalls 0.
- `register()` nimmt Code-Plugins auf. `verification.objective_registry` validiert über den Adapter.
- Neue Zeilen für die Köpfe:
  - IMPLEMENTED: c5-action-values, jef-bridge-utility, fast-forward-proceduralization, context-policy-recall, memory-admission-heldout-logistic, neuromod-metaplasticity-retention.
  - PARTIAL: attention-policy, deliberation-mode-values, callosum-channel-utility.
  - UNAVAILABLE: gist-readout-grouping.
- world-digital-action-latent-v1 hat jetzt seine Implementierungsdateien.

## Lernzeitskalen als geplante Jobs (§14.3/§14.4)
- **`learn_medium`** (Scheduler-Aktion; IDLE ab `wake_replay_idle_s`, höchstens alle 30 min): `review()`, und Admission-Neutraining, wenn neue Labels da sind.
- **`learn_slow`** (nach jeder vollen Nacht mit Status DONE): `review()` und Lernziel-Bericht. Außerhalb von RECORD_ONLY wird zusätzlich `growth_consolidate` für einen schon gestageten AG6-Batch eingeplant; Training bleibt hinter den AG6/Drift-Gates. Die Pause `training` gilt weiter.
- Schnelle Zeitskala (§14.1/14.2) bleibt in den Köpfen selbst, also pro Turn.

## Live-Vergleiche (WP-T10, 2026-10-11)

- Attention vergleicht Scaffold- und gelernte Rangfolge derselben gültigen Anfragen, sobald mindestens ein beteiligter Prior fünf Outcomes hat. Fremde, abgelaufene und für das aktuelle Age verbotene Teacher-Anfragen zählen nicht. Das ist ein Rangvergleich, kein Beleg für erfolgreiche Zustellung unter dem Budget; die tatsächlichen Provider laufen weiterhin nur im bestehenden Zustellungspfad.
- Deliberation vergleicht die bestehende Modusliste mit dem gelernten Vorschlag, sobald ein beteiligter Modus den vorhandenen Mindestumfang erreicht. HYPOTHESIS bleibt zuerst, Zahl der Schritte und Age-Rechte bleiben bestehen.
- Callosum vergleicht den konfigurierten Kanal mit der trainierten Wahl nur bei ausreichend gemessenem NO_MESSAGE und einem zulässigen trainierten Kanal. Die Revision des Empfängers setzt weiterhin die Kanal-Policy zurück. Das generische Ledger aggregiert Vergleiche; es ist kein revisionsgebundener Nutzen-Nachweis. LATENT bleibt gesperrt.

Die Hooks geben keine erfundenen Scaffold-/Learned-Outcome-Labels an `observe`: `n_out` bleibt ohne einen tatsächlich gemessenen Paarvergleich unverändert. Übereinstimmung beweist keine Antwortqualität. Die PARTIAL-Lernziele und bestehenden Gate-Verdikte verhindern weiterhin eine Beförderung dieser drei Köpfe. Keine zusätzliche Modellinferenz, kein Body-Gewichtstraining und kein aktueller Redmi-Nachweis in dieser Änderung.

Tests: 46 gezielte Softwaretests PASS: `test_authority_live`, `test_authority`, `test_attention`, `test_deliberation`, `test_callosum`, `test_local_updates`. Darunter sechs neue Integrationsprüfungen mit Runtime/SQLite, Wiederanlauf, Provider-Aufrufzahl und blockierter Beförderung. Bericht: `docs/proofs/authority-live-20261011/report.json`.

Zusätzlich wurde der Installations-ZIP-Einstieg `python3 -m v13 ... selftest` aus der entpackten ZIP geprüft: 946 Tests, 942 PASS, vier explizite PyTorch-Skips. Beim ersten Versuch fehlten im GitHub-Import die feste Native46-Fixture und der Norm-Poll-Header. Diese und die zugehörige Norm-Port-Quelle wurden bytegleich gegen den Manifest-Hash aus dem früher gesicherten Installationspaket wiederhergestellt. Der zweite Lauf bestand. Beide Testlogs und der Wiederherstellungsnachweis bleiben erhalten. Kein Modell- oder Redmi-Nachweis durch diesen Selbsttest.
