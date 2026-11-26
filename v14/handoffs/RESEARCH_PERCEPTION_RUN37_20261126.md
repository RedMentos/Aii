# Research & Perception — Run 37 handoff (2026-11-26)

## Source and ownership

- Repository: \`RedMentos/Aii\`
- Release-development branch readback: \`gpt6/v13-private-remote-bridge-20261111\` = \`8d93236c753f0194224c19edc7411d8d7082b1d6\` (latest readback; older than this lane's open PR stack).
- Active Perception branch current HEAD: \`b5fa240f4f29f562aa0a771f7187504a9757c273\` (code-bearing SHA \`8167033a8f133c8feb89c341df3720a5db765504\`; later commits are board/ledger/workplan/next-action/handoff documentation only).
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
