# Run172 — LP3 exact-source CLI isolation diagnostic (2026-10-25)

Owner: new Run172 script, tests, workflow and this document only. Base: Run171 head `c8a79a5a8859753b6d736b7b297c63d7ecd91c7c`. This is **not** a production fix, native run or full-suite pass.

Problem: Run164 full-suite on Linux (`40164614779`) ran 2358 tests, **4 FAIL, 11 skipped**: three `test_default_cli_read_only_blocks_missing_assets` saw CLI returncode 1 rather than expected 2; `test_successful_leader_with_live_descendant_is_not_success` found a surviving child. Run167 diagnostic workflow was cancelled before jobs ran, so no stderr from those failures. Preserve them unchanged.

Reconstructed exact Run21 helper from original code archive and post-reap patch, helper SHA-256 `05e5bf300f582a03efeaae0133c8e20bf60948a2fa4e05a4867924ac4dc4b831`. Local Python 3.13 no-native probe:
- **With exact helper plus all sibling modules:** CLI exits **2** and returns JSON `status=BLOCKED`; no native execution.
- **When helper copied without siblings and PYTHONPATH emptied:** CLI exits **1**, stderr contains `ModuleNotFoundError`. This is a reproduced *possible mechanism*, not proof of the original Run164 cause.
- Initial local test with helper alone: **1/2 FAIL** (rc1 vs rc2); raw log SHA-256 `473e2cb323d4725ed6eb5bfc1870c5fdf390a2b02bfe1e2565ba292099509e4a`. After staging siblings: **2/2 PASS**, raw log SHA-256 `1b3b16f2a20fa84362df68f3b7e5543600aa2a4db4c0c3f4eba6d55`. After adding explicit missing-sibling negative control in repository-style layout: **3/3 PASS**, raw log SHA-256 `217995b6f9e4a59dcd0395c0f330690e556b332bc6342c1b199f256ef4e53e9d`.
- New Run172 source Git blob `0ebb7376887d7dcbe1ae89c8c11cf59e55d6d0de`; test Git blob `6d5092c4914bb8d025cdc09591cfa7d44fd7a534`.

CI reconstructs exact Run21 source in temp, executes only stdlib read-only blocked CLI, records bounded stderr digest/excerpt, and official privacy scan. No model download, training, process signals or production modifications. CI result must be verified separately.

**Gates unchanged:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight 0; DS2_H2 FAIL; V13 INCOMPLETE.

Exact next step: if focused Linux rc2 passes, isolate full-suite cross-test contamination with the already-defined Run167 full-suite stderr diagnostic (or equivalent independent source-preserving replay), then fix verified root cause without suppressing any test or altering expected blocked behavior. Surviving-descendant failure remains separate until independently proven contained. No Drive retry.

## Confirmed CI import failure and bounded correction

First Run172 CI `40166518201`, job `121088579905` **FAIL**: exact reconstructed Run21 `lp3_serial_cohort.py` returned **1**, stderr explicitly `ModuleNotFoundError: No module named 'lp3_native_readiness'` at line 24. This reproduces the same rc1 symptom as Run164, not proof of the *entire* Run164 failure until full suite reruns. Root cause in the CI reconstruction: Run20 code-only archive does not include the two sibling audit modules that exist in the canonical repository. Locally, removing `lp3_native_readiness.py` and `lp3_closed_evidence_audit.py` from the otherwise exact helper also produced rc1/ModuleNotFoundError; restoring them produced rc2/BLOCKED.

Correction is restricted to **CI temp staging**: copy the exact registered repository `lp3_native_readiness.py` (Git blob `2dfa7099541d3f8940817d43b97746c1d4d27092`) and `lp3_closed_evidence_audit.py` (Git blob `6068ddafa2ae319f66a1cfcd7fb50127372e20a8`) into the temporary helper directory. Do not change the frozen helper, test expectations or production runtime. The original failed workflow and stderr remain retrievable; the corrected workflow must be verified separately. Live-descendant failure remains open.

## Corrected Linux CI independently verified

Run172 `40166585040` **SUCCESS** after temp staging exact two omitted sibling modules. Read-only helper returns `returncode=2`, `reported_status=BLOCKED`, `reported_reason=CANDIDATE_SOURCE_UNREADABLE`, no stderr, `native_executed=false`. Artifact ID `12588103272`, ZIP SHA-256 `3c967c5d7b3ac71916495add7cdc291bd5cdf8bd03150fd8fa60849e1a25c376`. This closes the *focused* missing-import cause, not the full-suite or orphan-descendant acceptance. Run173 full-suite independent recheck is registered in PR203; no result claimed until completed.
