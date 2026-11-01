# Run117CR BUILD_STATE — one exact reviewed-source drift isolated

2026-11-01 UTC. Review-only branch `assistant/v13-run117cr-source-chain-drift-audit-20261101-gpt6`, draft [PR #1570](https://github.com/RedMentos/Aii/pull/1570), parent Run117CQ `fa39f71c4eeb76620c062300a19988d8f42fe543`. Preregistration `PREREG_RUN117CR_SOURCE_CHAIN_DRIFT_20261101.md` committed `fcf005ef536f202a7b4beae314ce149ab528bcba` before code. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, frozen baseline/candidate tests and source acceptance unchanged.

## Original raw

[Actions 41260412225](https://github.com/RedMentos/Aii/actions/runs/41260412225) initial audit SUCCESS, 4/4 tests, original ZIP artifact `13064463949`, SHA256 `6c9ff57a567c535d963659a03a1f78549bf01e208819027069e97fcbc9f822c5`, CRC clean, 20/20 inner hashes verified, byte-identical private Library backup `/V13-Checkpoints/2026-11-01/Run117CR/RAW_GREEN_PRE_GUARD_41260412225_sha6c9ff57a.zip`.

[Actions 41260465132](https://github.com/RedMentos/Aii/actions/runs/41260465132) corrected audit SUCCESS, **5/5 tests** including source-tree/symlink report overwrite rejection, all eight `PINS/COMPILE/TEST/AUDIT/LINEAGE/NO_SOURCE_MUTATION/PRIVACY/DIFF` exits zero, privacy CLEAN. Original ZIP artifact `13064528947`, SHA256 `a3b393970854fccd08892e5808cdb4daaf71228336ad451375f6c7bc3c49b856`, CRC clean, **20/20** inner SHA verified. Private Library backup `/V13-Checkpoints/2026-11-01/Run117CR/RAW_GREEN_41260465132_shaa3b39397.zip` re-materialized and byte-identical. PR-event synthetic merge HEAD `dbad082770941c914dce284521b8eeba401fdafe`, source/test blobs pinned.

## Precise source finding

The complete `integrated_sources(ROOT)` chain agrees byte-for-byte with live `v13/runners.py`, `v13/memory_server.py`, and `v13/store.py`. **Only `v13/runtime.py` differs**, a **36-line unified diff** (758 expected lines vs 767 live). Expected SHA256 `3734a8c8f8951b619844abd125b223e5d1f6bee575c4bcb2edd99809c13a615f`, live SHA256 `8a403bffd1c2b14d9caa798cf17ea3c299cea5796115bad40cbaf9a2054072ed`, diff SHA256 `e4af02a7b896d2abebb6947d08190e828d78202f6307385d6763bc4892db2983`. Git lineage identifies exact original [Run12J commit `47b7825704970de86766c3a57fd9ee999ca199a4`](https://github.com/RedMentos/Aii/commit/47b7825704970de86766c3a57fd9ee999ca199a4) (2026-10-30), which replaces permissive recursive nested route extraction with an explicitly successful, validated, unique native `select_processing` call. The original commit diff matches the entire audited drift. This is a **safety hardening**, not a reason to revert live source.

No acceptance was modified in Run117CR. The unfiltered Run117CI full suite remains RED (5,331 tests, 4 failures, 75 errors, 28 skips). The read-only audit's GREEN does not promote the source chain.

## Exact next work

On a separate preregistered review child, append **only the exact Run12J transform** to `scripts.integrated_candidates._later` after `route_rule_lifecycle`, with strict one-occurrence anchor, full expected-vs-live SHA equality for all four NAMES, and negative tests for mixed/modified sources. Do not add arbitrary live-hash whitelisting. Run original source-handoff, integrated candidate, eligibility and native firing regressions; preserve raw RED if any. Do not claim whole full-suite PASS from focused tests. Reproduction for this audit: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest -v tests.test_run117cr_source_chain_drift_audit && PYTHONPATH=.:tests:scripts python3 scripts/run117cr_source_chain_drift_audit.py --diff-output /tmp/v13-run117cr-source.patch`.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no native/Redmi/learning/whole-system promotion. Remaining platform budget UNKNOWN.
