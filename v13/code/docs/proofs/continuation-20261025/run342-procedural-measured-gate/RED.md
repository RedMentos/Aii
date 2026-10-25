# Run342 source-only RED — preserved before implementation

- Branch head: `493e159c2b4bfa9232b5bdbaa6759ca50136ae88`.
- GitHub Actions run: `40221687671`, job `121254415396`, terminal **FAILURE**.
- Exact-head isolated Runtime/SQLite FastForward tests: **32 executed, 3 failures**; failures all new adversarial tests:
  1. `test_predicted_only_ready_must_not_gain_action_authority`: current `procedural()` returned `apply=True` despite `canonical_gate_pass=False`.
  2. `test_boolean_only_spoof_does_not_turn_prediction_into_measurement`: `apply=True` with fake gate Boolean and unchanged unmeasured predictor evidence.
  3. `test_missing_gate_stays_untrusted_after_restart`: `apply=True` with missing gate after SQLite restart.
- Existing tests in this focused selection passed; source-only, no model or hardware. The separate legacy focused workflow has historical source-handoff hash failures; it is **not** relabeled green.
- Original raw log remains at GitHub Actions run above, including failed assertions; no negative gates changed.
- Next command: apply only the measured-gate authority check in `v13/fastforward.py` and adjust the two historical unsafe ACTIVE assertions, then rerun exact-head Run342 CI.
