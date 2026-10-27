# World-JEPA real Linux file-world timing receipts — prereg 2026-10-27

Base PR #655 exact `8322c9ac51501144ae57e5b0e39f204b203ae66b`, review-only child, not main. Ownership: `v13/code/scripts/world_jepa_shadow_lifecycle.py`, `v13/code/tests/test_world_jepa_shadow_lifecycle.py`, new `tests/test_world_file_timing_receipts.py`, new CI workflow and scoped proof/BUILD_STATE. No registered Z12c seed/model/cohort changed, no active model/age/tool gate.

## Evidence gap
The current real-file-world exporter retains canonical `cohort.json` and independent process `world-<seed>.log/json`, but `_checked_rows` discards `a0/a1` timing windows before persistence. Thus an independent reviewer cannot recompute the claimed `world`/`world_changed` labels from the preserved world log. A malformed/forged collection can be labeled `LINUX_TEMP_FILE_WORLD_PROCESS` by a caller without timing validation. This is an evidence reproducibility issue, not a learned World-JEPA utility gain.

## Acceptance before code
1. For the actual `main` Linux file-world path, require nonempty valid world log, prefix-consistent schedule/log op+slot, valid finite ordered row intervals, and recomputed `z12b.touched(log,a0,a1)` equal to each row's `world` and `world_changed`. Any mismatch must fail BEFORE creating the export directory.
2. Preserve per-row interval receipts as a new `row_intervals.json` sidecar and SHA256 in manifest, aligned by row index/action and overlap labels to unchanged `cohort.json`. Do not modify the historical registered cohort or overwrite old outputs.
3. A read-only verifier can independently rehash and recompute receipts from the persisted export. Detect tampered sidecar, cohort, log or schedule. No claim of cryptographic attestation of physical OS actions.
4. Existing synthetic `export_from_rows` stays `CALLER_SUPPLIED_UNVERIFIED`; only the `main` subprocess path creates a verified timing receipt. Keep all SHADOW/authority=0 and negative gates.
5. Prospective RED before source, then GREEN Linux CI with focused tests, compile/privacy and actual new seed212 temporary file-world run (unregistered, 600 rows, 10 training steps). Capture raw ZIP/source hashes, failed attempts, private backup.

Claim limit: checks consistency of recorded timestamps/labels against preserved independent process log, not independent truth of each file mutation, semantic/causal World-JEPA utility, Redmi, native Body, STEP2/B3/age/approval. No automatic runtime observer.

Exact command: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_file_timing_receipts tests.test_world_jepa_shadow_lifecycle`.
