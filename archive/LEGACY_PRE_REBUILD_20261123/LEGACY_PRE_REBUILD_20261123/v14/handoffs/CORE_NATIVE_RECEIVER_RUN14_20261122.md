# Core & Harness handoff — native receiver rebase / Run 14

**Base:** release-development `gpt6/v13-private-remote-bridge-20261111` at `c03ff0aa9e18b5ffebd1109f3c078105f53c6afe`
**Branch:** `core/v14-native-receiver-release-rebase-20261122-run14`
**Code checkpoint:** `60d716bedea5570577d40fb62f069323dca92483`
**State:** DRAFT / NOT_RELEASED / NOT_ANDROID_VERIFIED / EXACT-HEAD-CI-PENDING

## Actual change

Replayed the native llama.cpp input-embedding receiver candidate from the older Boss-base PR #2314 onto the current release head. The six source files pinned by the candidate's SHA-256 BASE_PINS have identical Git blob SHAs at the old base `1105ab56` and current release `c03ff0a`; the branch is now 19 commits ahead and 0 behind the release head.

Fixed the staged Callosum operator regression: the overlay previously replaced `c=controller(r)` with the native-probe branch, so the ordinary `:callosum` status command raised `NameError: c is not defined`. The inserted prefix now preserves `c=controller(r)` before the new explicit probe branch. The native probe remains one-shot, diagnostic-only, and does not enable production B3, semantic alignment, weight learning, model swaps or routing authority.

The native receiver is pinned to `ggml-org/llama.cpp` revision `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`; the repository LICENSE at that revision is MIT. The code still requires a real installed model and exact sender/receiver manifests at execution time.

## Exact source-pin readback

- Native receiver builder Git blob: `474ffc2bc1c37079863e721dc7da76d8b6fbcb51`
- Recovery builder's `NATIVE_RECEIVER_BLOB_SHA1`: matches the builder blob above
- Recovery builder SHA-256: `9f8f7723afc6694723fffb1e472c0ff17c37437f9d26d7f960933c4cfbf09f9c`
- Stage builder's `BUILDER_SHA`: matches the recovery builder SHA-256 above
- Stage builder SHA-256: `cb0a45a903aa190434fa9e84f6032fff6ff5672ebb242905e6d1066ded1a44a1`
- Runtime deployer's `STAGER_SHA256`: matches the stage builder SHA-256 above
- Re-read all three pin values from the branch after the final writes; all comparisons PASS.

## Tests and evidence

- **LOCAL_LINUX / CPython 3.13.5:** targeted operator-overlay regression PASS. The test first reproduced the old `NameError` as a negative control, then compiled the fixed operator function and verified `:callosum status` returns `OK`.
- **LOCAL_LINUX full Aii suite:** BLOCKED; no repository checkout is present and GitHub DNS resolution fails. The local test above is a focused source-level regression, not a full Runtime integration test.
- **LOCAL_LINUX / CPython 3.13.5:** a second focused check verified the recovery→stage→deployer SHA-256/Git-blob pin chain end-to-end; the SHA-256 implementation was checked against the standard `abc` vector. PASS.
- **Staged synthetic Runtime regression added:** `test_native_latent_receiver_stage.py` now asserts that the fair observer overlay is present and runs `observer_fair_budget_disposable_cases_20261116.py` inside the exact staged Runtime. That suite exercises sequential role slices, B1 timeout with B2 still reaching C4/C3, and two recent C3 zero-token failures where both source-bound B1/B2 offers enter the same C3 input. These are synthetic Runtime/SQLite results, not native model or Redmi results.
- **GitHub CI first pass:** Python 3.13 exposed two issues. (1) The builder raw string contained the two literal characters `\\n`, so the staged Callosum source failed compilation; corrected to a real newline and refreshed every dependent pin. (2) `test_callosum.py` was also run against the unstaged base Runtime, where its RECORD_ONLY assertion is not valid; it now runs only inside the exact staged Runtime subprocess, where the Record-Only guard is applied. The staged test additionally executes the fair-budget synthetic Runtime suite.
- **GitHub CI current head:** exact-head run for `60d716b` is queued/in progress; no PASS is claimed yet. Workflow compiles the staged receiver/deploy chain, runs native-tap + staged-receiver + staged Callosum + fair-budget regressions on Python 3.13/3.14, builds the pinned Linux receiver, cross-compiles Android arm64-v8a, and runs the public-repository privacy scan.
- **Android / Redmi:** REDMI_UNVERIFIED. No handset connection, APK install, model load, native receiver invocation, update request, shell, model/weight change or permission change occurred.

## Remaining limits

The probe consumes receiver input embeddings through the native llama.cpp API but does not demonstrate trained cross-model alignment, semantic usefulness, K/V transfer, production latent routing, native weight changes or AGI-like behavior. Android ARM64 cross-compilation is not Android execution. The P0 native B1/B2 → C4 → C3 correctness/latency acceptance remains open.

## Next action

Run and inspect every exact-head CI job. If all pass, send this current-release PR to Boss for source/privacy review and integration planning. Only after a separately authorized real-device test may the probe be invoked against existing installed models; no model download/swap or production latent enablement is implied.
