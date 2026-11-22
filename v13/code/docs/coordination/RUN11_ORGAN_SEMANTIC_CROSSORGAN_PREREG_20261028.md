# Run11 V13 cross-organ checkpoint × F1/F5 semantic forget prereg (2026-10-28)

Owner: isolated automation review child of PR #921 at `c7a2e537b9892410bafc4f4a93c9cd44b2788a1c`. Merge independent verified source-only organ PR #920 current `2611a4b5b0c50158d2130b7a0b1cfc9f4e9036e1` as a second parent without changing either owner branch. Source parents remain branch-scoped, not main. Do not override current TP27 native owner.

## Binding behavior to verify
1. `:organ snapshot/restore B1_DETAIL` restores only that organ's component generation, **never** revives a human correction removed by `:forget`, never recreates its semantic key, and does not silently restore human feedback. Active component files must still pass Store hash validation.
2. A real thread can perform semantic recall while the encoder blocks; a concurrent completed `:forget` must win and the returning encoder must not recreate the cache or return the forgotten value. Use real SQLite and deterministic fake vectors, no native model or device claims.
3. Preserve original organ rollback safety tests and semantic revocation tests, plus all other software tests. No authorization, learning, source/model/seed/cohort, Age0 or Canon gate changes.

## Source and acceptance
Merge exact parent source/test blobs (organ donor Git blob `aa925d5d4128974c3e1aaf64e58d0e4310e5dfa1`; semantic fix Git blob `138df0bcf90b0f278294b940358e64fac5c93eb9`, memory fix `53dc948d0d360f94743ad996eb83ea0e85c2dd0b`). Add only `tests/test_organ_semantic_forget_crossorgan_20261028.py`, an isolated workflow, coordination/proof/BUILD_STATE updates. The two parent full-suite Actions `40689839187` and `40689975127` are still IN_PROGRESS at prereg time; do not claim them green until independently audited.

Expected focused: existing organ and semantic suites plus two new cross-organ cases. Expected full: source-pinned Linux software `unittest discover`, compile, official privacy/diff; closed raw artifact and private Library backup. No native/model inference, no Redmi measurements. A failure is preserved, not relabeled.

Negative gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi unmeasured, whole V13 incomplete. Remain review-only. Exact next command: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_organ tests.test_organ_artifact_integrity tests.test_organ_path_safety_run365 tests.test_run441_organ_bridge_symlinks tests.test_semantic_memory tests.test_semantic_forget_encoder_race_20261028 tests.test_organ_semantic_forget_crossorgan_20261028`. Remaining platform budget UNKNOWN.
