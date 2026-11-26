# Research & Perception — Run 37 handoff (2026-11-26)

## Source and ownership

- Repository: \`RedMentos/Aii\`
- Release-development branch readback: \`gpt6/v13-private-remote-bridge-20261111\` = \`8d93236c753f0194224c19edc7411d8d7082b1d6\` (latest readback; older than this lane's open PR stack).
- Active Perception branch current HEAD: \`393bf150d4ebcec786f5f9ee4f1bea0f8f46dd6f\` (code-bearing SHA \`8167033a8f133c8feb89c341df3720a5db765504\`; later commits are board/ledger/workplan/next-action/handoff documentation only).
- Existing PR [#2498](https://github.com/RedMentos/Aii/pull/2498) was extended in place; no duplicate PR or force-push.
- Whole-Canon epic: [#1984](https://github.com/RedMentos/Aii/issues/1984). Runtime/chat blocker: [#1904](https://github.com/RedMentos/Aii/issues/1904).

## Actual code change

1. \`v13/code/v13/audio_event_expectation.py\` — module commit \`2b7fa35f0769333942fbd1e8bb072929b9852a42\`, blob \`4571b12aeb665f2865d53c54561cacd2562d6f95\`.
   - UNCERTAIN and low-confidence FINAL windows now censor the sample, clear pending expected events and onset anchors, and preserve only bounded historical interval samples.
   - A non-target window only proves an omission if it begins at/before the expected onset and extends through the tolerance interval. A late window after an uncovered gap is not accepted as negative evidence.
2. \`v13/code/scripts/integrated_audio_context_candidate_20261121.py\` — composer commit \`516df12482def70f4cc32f329c303e32d1589555\`, blob \`d6d634857b42fc9dd29fa9bb2481220fd414e8bf\`; exact module pin updated to \`4571b12aeb665f2865d53c54561cacd2562d6f95\`.
3. \`v13/code/tests/test_audio_temporal_prediction.py\` — test commit \`8167033a8f133c8feb89c341df3720a5db765504\`, blob \`36731e6c498b63a6642b3277d1428dd4572e5537\`.
   - Added uncertainty-crossing, low-confidence-silence and uncovered-gap negatives.
   - Existing positive event-omission consumer test now uses a high-confidence silence fixture.

## Test evidence

- LOCAL_LINUX CPython 3.13.5: exact fetched \`audio_event_expectation.py\` syntax compile PASS.
- LOCAL_LINUX CPython 3.13.5: exact fetched module runtime checks 5/5 PASS: valid expected omission positive; uncertain window crossing expected time negative; low-confidence silence negative; late non-target window after a gap negative; provisional window ignored/no state.
- Full Aii checkout and full pytest: BLOCKED/NOT_RUN because no repository checkout is mounted and GitHub DNS is unavailable in the container. The module checks are not the full A5→A4→C3 consumer integration test.
- Exact GitHub CI readback for code SHA \`8167033a8f133c8feb89c341df3720a5db765504\`: RAW EAR vs WebRTC/libfvad run 45730324785 **9/9 PASS** on Python 3.13 and 3.14; runtime deployment integrity run 45730324780 **41/41 PASS** on Python 3.11 and 3.14; optional NumPy/RAW EAR fastpath run 45730324844 **138/138 PASS** on Python 3.13 and 3.14, py_compile PASS and privacy CLEAN. Staged/integrated run 45730324811 **FAIL**: 16 failed, 237 passed, 10 skipped, 2 errors, 47 subtests; root cause is exact recovery pin mismatch expected 831080bceec90711bd42e0fa4eba47c669975c98 vs actual composer blob \`d6d634857b42fc9dd29fa9bb2481220fd414e8bf\`. Two-checkout migration is PARTIAL.

## Research

R-164 records Aurich et al., “Neural Correlates of Dynamic Predictions and Prediction Errors in Response to Unexpected Silence and Sound,” *European Journal of Neuroscience* 63(4), e70422, first published 2026-02-25. Full text reviewed. N=41; action-conditioned 80/20, 20/80 and 50/50 sound/omission conditions. The results caution that silence-as-prediction may require higher-level context. A4 remains a low-level, non-calibrated timing novelty signal; semantic/action omission requires a future source-bound action/outcome context path. Exact reuse license was not independently verified; no data/code/weights reused.

## Consumer and Canon impact

- A5 RAW EAR → A4 timed expectation → attention novelty remains the consumer path; contribution is still capped at 0.05 and does not alter external_interrupt, C3 text, speaker identity, learning/action authority or model weights.
- This is a reliability fix within the A0–A5 audio/perception family. It does not complete voice I/O, AudioRecord, Android UI, B3 latent exchange, whole-Canon acceptance or basic chat.
- Redmi/Termux/microphone: REDMI_UNVERIFIED. No handset was connected; no Android test or deployment claim.

## Integration blocker and next owner

- Current Perception composer blob: \`d6d634857b42fc9dd29fa9bb2481220fd414e8bf\`.
- Current event module blob: \`4571b12aeb665f2865d53c54561cacd2562d6f95\`.
- Core/QA and Boss must compose #2482/#2483 A4 guard, #2485 Runtime allowlist and #2498 audio composer on one reviewed base; then set \`AUDIO_BUILDER_BLOB_SHA1\` to the final composed builder's exact blob, recompute wrapper/stage/deployer pins in dependency order and rerun staged-runtime, integrated-regression and two-checkout migration. The current intermediate Perception composer blob is \`d6d634857b42fc9dd29fa9bb2481220fd414e8bf\` and its event module pin is \`4571b12aeb665f2865d53c54561cacd2562d6f95\`; do not blindly pin a sibling branch's intermediate tree or weaken the hash gate.
- After exact-head CI and downstream integration are green, Perception should run held-out periodic/omitted/shuffled timing cohorts, uncertainty-gap and consent-rotation controls. No new device permission is required for those synthetic/local tests.

## User action

None. No manual Termux command, model download/swap, permission change, weight change, remote shell, chat send or device mutation was performed.


## Additional cross-organ research — R-165 (B3 input-tap boundary)

Reviewed upstream `ggml-org/llama.cpp` commit `2851b3bcbf8d993a2243ae751c0a7dfa8e944a40` (2026-10-15T23:46:42Z), MIT. The selected-row function is in [src/llama-ext.h](https://github.com/ggml-org/llama.cpp/blob/2851b3bcbf8d993a2243ae751c0a7dfa8e944a40/src/llama-ext.h) and [src/llama-model.cpp](https://github.com/ggml-org/llama.cpp/blob/2851b3bcbf8d993a2243ae751c0a7dfa8e944a40/src/llama-model.cpp#L3910-L3971); the header explicitly labels itself staging/WIP. The function reads static `model->tok_embd` rows, dequantizes to F32, and returns an element count. It does not return contextual hidden states. It may partially write rows before a later invalid ID returns 0, so Core must prevalidate every ID, enforce exact count/overflow/memory bounds, verify model/vocab/tensor and binary hashes, and discard all output on failure. Current V14 pin `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` predates the API.

PR #2503's typed receipt contract is correctly marked STAGING_WIP; exact run 45658242985 passes 66 tests on Python 3.13 and 3.14. Runtime-integrity 45658242958 and staged regression 45658243238 also pass. These are CI/Python contract tests only; no native GGUF or Android ABI proof. Static input embeddings are a baseline, not B3. True B3 requires sender contextual activations + trainable projection + receiver injection and held-out task utility/negative controls/retention/rollback. B3 remains OFF.


## Private device receipt readback (2026-11-26)

- Private V13OBS issue #115 last updated `2026-11-24T09:28:11Z`; it is metadata-only, not a live receipt for this run. Last recorded `pipeline.auto_enabled=true`, dashboard/runtime `UP_TO_DATE`, `last_error=NONE`, installed commit `8d93236c753f0194224c19edc7411d8d7082b1d6`. App service/dashboard were RUNNING, but the AI runtime was `STOPPED_BY_USER`, autostart false, model process STOPPED and native residency UNAVAILABLE.
- The latest recorded simple C3 turn generated 7 tokens (TTFT 2.05s); prompt inclusion and semantic use were not proven. B1/B2 had zero valid offers and previous native attempts timed out. Native latent exchange was false.
- New read-only owner relay request `PIPELINE_STATUS`: private issue #938, created `2026-11-26T00:54:31Z`, expires after 600 seconds. Last poll: issue OPEN, no device comment — `NO_LIVE_RECEIPT`. No further polling or LOG_PAGE request was made.
- Therefore current installed release/updater/runtime remains **UNVERIFIED**. No UPDATE_REQUEST, manual Termux command, chat send, shell, model/weight/permission change or device mutation was made. The previously observed `auto_enabled=true` is historical only.
