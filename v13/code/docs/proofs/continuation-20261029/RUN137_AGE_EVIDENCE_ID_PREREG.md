# Run137 — Age evidence identifier preflight (review-only prereg)

Date: 2026-10-29. Owner branch: `codex/age-evidence-id-preflight-20261029`. Exact verified parent: Run132 PR #1032 commit `fe36d3be24256c380c81812ec9f7f8ba1f585740`; original Actions `40815936157` ZIP SHA256 `6c004e3fd20a2d2456d4b8c2bb8b5b7622cd1ab554854e0d9b0408728b3cc103`, CRC CLEAN, 16/16 SHA256SUMS, all exits zero, focused 25, full exit zero, privacy CLEAN.

## Pre-existing observation (not a fresh hypothesis)

Static inspection before this prereg: `v13.age.AgeControl.record` computes `eid = evidence_id or uid('evidence')` and persists `eid` into `seen_evidence`, `pass_streak`, `last_evidence` without type checking. The separately imported Run132 read-only `age_state_quarantine_candidate.verify_state` requires nonempty **strings** in these fields. The Run131 finite-metric wrapper validates metrics and subject but does not validate `evidence_id`. Thus a truthy non-string `evidence_id=True` appears capable of creating a durable state that Run132 correctly quarantines. This is a source-derived hypothesis; a Store-backed reproduction is required.

## Locked package and acceptance

Implement **only a new isolated, default-off wrapper** `scripts/age_evidence_id_preflight_candidate.py` that rejects explicit `evidence_id` unless its exact type is `str` and it is nonempty; `None` delegates generation of a new ID. Delegate the actual metric/subject validation and write to the unchanged Run131 `age_evidence_finite_candidate.record`. Do not modify frozen `v13/age.py`, Run131/132 donor files, runtime, operator, model/cohort/seed sources, or any registered evidence.

Tests in `tests/test_age_evidence_id_preflight_candidate.py`: demonstrate original direct AgeControl plus finite wrapper can persist a boolean ID that Run132 flags as corrupt (isolated temp Store only); verify new wrapper refuses bool, numeric, empty, bytes, list/dict and NaN before durable state/telemetry changes; verify valid string/None and duplicate handling, Age0 ceiling/freeze unchanged, restart valid, Run132 guarded view valid. All negative gates retained.

Run isolated software-focused tests and full suite in a branch-only Linux CI with source pins, privacy/diff and SHA256SUMS raw artifact. No native model, Redmi or promotion. Do not retrofit or erase original failed Run135; this package is independent. Any failure remains RED and is preserved. A passing software test proves only this optional wrapper, **not production runtime containment**.

Acceptance: source pins exact, focused and full exit 0, privacy CLEAN, raw ZIP CRC and all inner hashes verified; Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 incomplete.
