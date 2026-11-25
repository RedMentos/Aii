# Research & Perception handoff — run 26 (2026-11-25)

## Branch / release
- Repo: RedMentos/Aii
- Work branch: `research-perception/v14-a4-audio-source-outcomes-current-20261124-run16`
- Release base verified identical to `gpt6/v13-private-remote-bridge-20261111`: `8d93236c753f0194224c19edc7411d8d7082b1d6`
- Perception code commit: `9e3c5719a4dfbc70f3869aa7a3ac7e541bb736ee`
- Perception regression commit: `c655b1e75c6a1db6cbbfa181d7675c7939c05fb5`
- Exact source blob: `ceef8d8a2f26ec3f4a447ae8037ca51027d133af`
- Comparator workflow pin correction: `b54354ebd95d066a637303ce852831c2549300e9`
- PR #2472 remains DRAFT / NOT_RELEASED.

## Implemented
`audio_consent_generation_scope()` now accepts an optional existing `AudioConsentLease`. When absent, it retains the previous owned-lease behavior. When supplied, it validates exact Runtime/source/generation/receipt/temporal-state/VAD-stream and active/thread binding, then borrows with `nullcontext` rather than reacquiring the provider guard. The outer Runtime context remains sole owner.

The regression verifies:
- valid borrowed lease remains active across PCM16 ingress, A5/A4 result, and full C3 iterator exhaustion/close;
- no second consent-check or provider-guard entry;
- source, generation, receipt and temporal-state mismatch fail before PCM persistence/C3;
- old owned-lease behavior still works.

## Tests
- LOCAL_LINUX isolated contract harness: PASS. It is not a full project checkout.
- GitHub Actions exact PR branch:
  - FASTDIAR adapter consumer: 2/2 PASS (Python 3.13/3.14), run 45535817025.
  - A4 source-bound outcomes: 2/2 PASS, run 45535816824.
  - RAW EAR prosody: 2/2 PASS, run 45535816801.
  - RAW EAR optional NumPy: 2/2 PASS, run 45535816783.
  - consent revocation: 1/1 PASS, run 45535816926.
  - RAW EAR/WebRTC/libfvad comparator: 2/2 PASS after exact V3 source pin update, run 45535816776.
  - runtime deployment integrity: 2/2 PASS, run 45535816788.
  - privacy scan: PASS, run 45535816863.
- Remaining failures:
  - controller guard run 45535816785: Core-owned recovery builder still expects guard SHA-256 `86ad7838d15eb9a038fec629c340936edde78d65d921507e10cec29fed74b9d9`;
  - staged/integrated run 45535816718: same stale nested guard pin stops composition before downstream tests;
  - Core same-turn run 45535816831: Python 3.13 fails on the same source-pin chain; Python 3.14 was still in progress at last poll.
- #2482/#2483 are the stacked recovery/guard pin-repair dependencies. Perception did not modify Core-owned recovery/stage/deployer files.
- Full local Aii suite: BLOCKED / NOT_RUN (no local checkout; GitHub DNS unavailable).
- Termux/Redmi: NOT TESTED.

## Runtime / device truth
Core PR #2478 currently wraps the complete Runtime turn and C3 iterator in a Runtime-wide audio lease and does not import `audio_consent_generation_scope()`. The new borrowed-lease API prevents deadlock if a distinct A4/A5 composition consumer later uses it; it does not create a new user-visible Runtime effect today.

Latest available authenticated V13OBS #115 (2026-11-24 09:28 UTC) reports release `8d93236c753f0194224c19edc7411d8d7082b1d6` installed, updater enabled, Runtime/Dashboard UP_TO_DATE, last_error NONE; AI STOPPED_BY_USER and model process STOPPED. Last stored C3 turn: 6.30 s / 2.05 s TTFT / 1.87 s prefill / 358 admitted tokens / 7 generated; correctness unknown. B1/B2 each had two failed attempts and zero valid offers. No 20-turn acceptance. No device action, update request, model/weight/permission/data mutation.

## Research
- R-119 Palimpsa: full arXiv HTML / ICML 2026 paper reviewed. Metaplastic precision/forgetting is a research hypothesis; GPU-heavy implementation, repo MIT badge but no root LICENSE text; no reuse.
- R-120 Mistake Gating: full arXiv HTML reviewed; journal online 2026-11-05. Update sparsity results are supervised-classification results, not JEPA/mobile evidence. Public repo has README only and no LICENSE/code; no reuse.
- Future experiment: source-bound prediction-error gating on deterministic A4 outcomes, with stable event identity, source/session-disjoint holdout, parameter/update-count evidence, retention, bounded replay, restart and rollback. Not implemented or activated.

## Next
1. Boss/Core integrates and verifies #2482/#2483 on one exact source-pin chain.
2. Rebase #2472 onto that exact head and re-run the full matrix.
3. Only if a distinct A4/A5 composition seam needs this helper, pass the existing Runtime lease from Core; do not duplicate or reacquire the Runtime-wide lease.
4. Keep AudioRecord/microphone OFF until signed companion, lifecycle, revocation and zeroization gates pass.
5. Continue whole-Canon work; this PR is one supporting audio-perception seam, not P0 basic-chat completion.
