# Run117BD — Body-JEPA source-group research checkpoint (2026-10-31 UTC)

**Review-only PR #1535**, branch `assistant/v13-run117bd-bjepa-grouped-source-20261031-hourly11`, exact parent Run117BC PR #1534 at `de28c4603573b70b3b65a26e24f8fb0ea4da602f`. This is not a production merge, a native training run, or a registered experiment. Canon and all earlier decisions/negative evidence remain unchanged.

## Implemented and remotely verified

- New **default-OFF**, research-only `v13/code/v13/body_jepa_grouped_source_candidate.py`, Git blob `823644a51acd1ea1ed2c8ed17452d0976a25778f`. Rejects mismatched context/target source SHA, source-ID rebind, source-hash alias, mixed B1/B2 path, duplicate views, zero genuine negatives, invalid eligibility, train/heldout source overlap. Masks same-source repeated views in existing `body_jepa_contrastive_shadow.loss_and_metrics`. Fingerprints exact row metadata, returns zero-authority metrics without raw source IDs.
- Tests `v13/code/tests/test_body_jepa_grouped_source_candidate.py`, Git blob `6223d24b84212693f843f833fcda09adeb01253c`. Exact workflow source `.github/workflows/v13-run117bd-bjepa-grouped-source.yml`.
- Original GitHub Actions **41246692916** at exact head `1c9b42dc064d1f54e06757de8e1ef28ce8cf7982` terminal **SUCCESS**. Focused **9 tests: 8 PASS, 1 SKIP** (Torch absent in CI), compileall PASS, privacy scan `de28c4603..HEAD: CLEAN`. Independently read job logs, not just green badge. Local isolated copy: 8/8 tests PASS including Torch on a *semantic replica* of upstream contrastive callback; **not** an exact upstream integration test or native model evidence.
- Original source and tests re-fetched from GitHub after push; hashes/lengths matched. No changes to frozen Body trainer, original cohorts, model pins, native runner, Runtime, age or learning authority.

## Claim boundaries and next command

**Important:** SHA256s are caller-provided metadata here, not authenticated against persisted Store. A future trusted consumer MUST bind them to actual SourceRefs and recheck after any callback before treating them as evidence. This is a guard candidate, not end-to-end JEPA training. Existing contrastive trainer does not yet consume this guard.

Next authorized package: wire this guard into **opt-in research-only** contrastive trainer (default unchanged), with same-source grouped-view tiny Torch/PEFT two-step test, plus explicit refusal for shuffled grouped controls and source metadata spoofing. Verify in an independent workflow and review before any native multi-step preregistered cohort. Do not change original frozen experiment source or fixtures; if current owner has an active native job, serialize it.

**Gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; runtime jepa_weight=0; no Redmi evidence; canonical_architecture_complete=false; user_full_scope_complete=false. Remaining platform budget UNKNOWN. Owner: Run117BD review branch. Remote GitHub checkpoint confirmed; private Library upload from this runtime was unavailable (`container_session_unavailable`), and the rejected anyone-writable Drive destination was not retried.
