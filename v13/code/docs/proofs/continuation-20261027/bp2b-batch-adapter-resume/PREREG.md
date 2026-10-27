# BP2b batch restart: adapter and raw prediction integrity prereg · 2026-10-27

Owner GPT-6 independent review child of PR #713 exact `c13aee9b1ab29bb197b9a8c4a42bb664e1a353fc`. Own only `scripts/bp2b_native_batch.py`, `tests/test_bp2b_native_batch.py`, a new CI workflow and this proof folder. Separate PR #712 seed41 native model owner is running on its own isolated runner; do not modify or signal it.

Confirmed code-level gap: batch restart currently verifies the `RESULT.json` and raw-log SHA but **not** the exported GGUF adapter or raw `PREDICTIONS.jsonl`. If those files disappear or change after a successful arm, restart can skip the arm and count it as completed, leaving Q4 evaluation without usable weights and source evidence.

RED counterexamples: fake completed arm with valid synthetic adapter/prediction files; then delete adapter, change adapter bytes, or change predictions. Existing code incorrectly skips. GREEN: before checkpointing and before skipping, verify regular non-symlinked adapter inside that arm's isolated trainer dir, its exact streamed SHA256 matching `RESULT.adapter_sha256`, and raw predictions file SHA256; persist both file digests in fsynced state and refuse any missing/tampered files on restart. Do not modify source/model/cohort/hyperparameters or run a real model.

Test with software-only fake subprocess; preserve original RED/GREEN Actions ZIP, hashes, private byte-exact backup. No Age, STEP2, B3, BJ1, Body-JEPA, Q4, Redmi or full-system promotion.
