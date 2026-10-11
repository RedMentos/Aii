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
  - Köpfe ohne Vergleich (attention, deliberation, callosum, gist, neuromod_meta) bleiben ehrlich bei 0, bis ein Hook einspeist.
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

Tests: `tests/test_authority.py` (6).
