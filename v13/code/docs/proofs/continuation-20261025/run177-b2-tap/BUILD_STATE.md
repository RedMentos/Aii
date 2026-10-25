# Run177 — B2 tap metrics provenance correction (2026-10-25)

Owner: `v13/code/v13/runners.py` **only the read-only `tap()` identity/dimension fallback**, new focused synthetic test, workflow and this proof. Base Run176 `ae81b5c322719281014c286846d24822b6306aa1`. Do not merge into production without independent review.

**Verified code defect before change:** `RunnerPool.TAP_SPECS` already registers `gist=('qwen35.result_norm.final.v1',1024)`, but `LlamaRunner.tap()` returned `metrics['tap_id']='lfm2.result_norm.final.v1'` for every role, and direct B2 runners defaulted to 2048D instead of 1024D. `cognition.tap()` used the pool's separate `tap_id` for the packet, so the packet and native metrics could disagree. This is a provenance inconsistency, not evidence that B2 learning worked.

Scoped correction: `tap()` metrics use the bound `self.tap_id` (or role-correct default); direct `B2_GIST` fallback dimension is 1024, while B1 stays LFM2 2048 and C3 stays LFM2 1024. No native loader, generated response, weight, JEPA, age gate or acceptance criterion changed.

New synthetic tests stub the native `/tokenize` and `/embeddings` endpoints and verify direct B1, direct B2, pool-bound B2 and C3 identity/dimension, token order and `CAN_TRAIN_BODY=False`. No actual Qwen model loaded, so B2 tap provenance is a **software-only candidate** until independently checked against the pinned native B2 revision/weights.

Source Git blob `37bf8e1c0222d4148dfbc3d2aedbef0c03adeac5`, test blob `159c8c9b4b05b40d7a9d873f93635ac1e64986b2`. Focused Linux CI pending until PR opened. Original full-suite Run173 remains FAIL (orphan descendant + optional restore PermissionError); Run176 test-only fix pending; Run174 B1 native larger cohort pending.

Gates: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

Next: run focused test, independently review `RunnerPool` tap metadata, then perform source-bound real B2 native 1024D tap proof before any cross-body JEPA training claim. No model swaps or unapproved learning. No retry of rejected Drive backup.
