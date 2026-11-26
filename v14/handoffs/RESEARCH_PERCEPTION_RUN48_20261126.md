# Research & Perception — Run 48 Handoff (2026-11-26)

## Execution record

- Exact wall-clock start/end: UNKNOWN (not independently recorded).
- Repository: `RedMentos/Aii`.
- Working branch: `research-perception/v14-kv-snapshot-consumer-20261126-run35`.
- PR: #2524, DRAFT / NOT_RELEASED.
- Code/test head: `91cae713b409e1b5e95bc06c446a5152e726cbd9`.
- Utility blob: `7d90a187f537a62d08ae3d0b0eefa23e3536b81c`.
- Test blob: `fb559b3214df987695d1b5a48e3174681fe16302`.
- Docs/ledger/next-action commits follow the code/test head; they do not change the implementation.

## Implemented

`v13/code/v13/native_receiver_utility.py` now audits the existing OOD controls across the complete held-out task cohort. A donor permutation qualifies only when, within every session, each task's OOD source is another task's source, each donor is used exactly once, no task donates to itself, and donor task family differs from recipient family. External, duplicate, cross-session and same-family donors fail closed. Only aggregate counts are emitted; source IDs and hashes are not copied into the audit output.

The existing `information_use_audit` now reports `CONTENT_SPECIFIC_SIGNAL` only when all three gates pass: system gain vs `NO_MESSAGE`, entity-specific gain vs `ENTITY_SUBSTITUTION`, and positive candidate-vs-OOD teacher-forced target-logprob delta with a complete donor derangement. Otherwise it reports the narrower failure state `ENTITY_SPECIFIC_GAIN_WITHOUT_FULL_DERANGEMENT` or the existing system/holdout states. It continues to set semantic-use, generated-answer correctness, production routing, persistence and learning/receiver authority to false/zero.

## Test evidence

### LOCAL_LINUX

- Environment: CPython 3.13.5.
- Isolated derangement helper: 6/6 PASS (valid session-local cycle; fixed point; duplicate donor; cross-session donor; same-family donor; external donor).
- Isolated `py_compile`: 2/2 PASS.
- Full Aii checkout/pytest: NOT_RUN. No repository checkout was mounted; `git ls-remote` and raw GitHub access fail because `github.com` DNS cannot resolve.
- The local scratch reproduction is not the repository test suite and is not native/model evidence.

### CI

- Exact code/test head `91cae713b409e1b5e95bc06c446a5152e726cbd9`.
- Native receiver workflow 45861303391:
  - Perception condition-matrix + task-score tests: 49/49 PASS on Python 3.13 and 3.14.
  - One separate stage-composition test FAILS on both versions: Core-owned `integrated_observer_fair_budget_candidate_20261116.py` rejects current `v13/cognition.py` bytes with `observer fairness source changed: v13/cognition.py`.
  - Pinned Linux native API build PASS.
  - Android arm64 cross-compile PASS (compile only; no device execution).
  - Public privacy scan CLEAN.
- Staged/integrated workflow 45861303423: FAIL, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. The same Core-owned observer fairness pin causes the majority of failures; two migration assertions report PARTIAL rather than UPDATED.
- RuntimeDeploy offline integrity workflow 45861303433: PASS on Python 3.11 and 3.14. This is offline validation, not deployment.
- Earlier exact attempts found and corrected two test assertion/receipt-invariant issues and a pytest decorator-placement error. The final focused suite is 49/49 PASS; do not hide the remaining Core integration failure.

## Research

R-168 reviews the full arXiv preprint 2611.34278v1 (submitted 2026-11-25). Chasm reports that cross-model KV handoffs can undermine safety alignment and prompt-injection defence, leak mapped-cache contents, and degrade task capability after repeated remapping. Its experiments use H200 GPUs and 3B–32B model families; they do not establish LFM2 or Android feasibility. No official public code repository or licence was found. The paper reinforces that source hashes prove byte integrity, not producer identity. Future B3 gates need source/model/mapper provenance and authenticity, transport integrity, trust/consent labels, injection/jailbreak and mapper-backdoor red-teaming, cache-privacy checks, multi-hop retention and over-refusal/utility measurements.

## Integration and device state

- Whole-system P0 issue #1904 remains OPEN. This PR is a complementary diagnostic improvement, not a basic-chat, B1/B2 offer-delivery or normal-turn fix. The last available device snapshot remains historical and reports AI STOPPED_BY_USER with zero valid B1/B2 offers.

- Core PR #2525 remains DRAFT and mergeable=false. Last observed head: `9fdf321c9c14ab3b27d0d5947eaca443d5796df3`; base SHA remains stale at `b298719af8faf75811d03d486de7725395a590b0`. Core must rebase onto latest #2524 and refresh the source-pin/recovery/observer chain. Perception did not modify Core-owned files.
- The Core consumer was previously inspected to return the Perception task-score result unchanged; the new audit fields should pass through once #2525 is rebased. This is still a diagnostic opt-in, not a normal-turn route.
- B3 remains OFF. No real GGUF was run. No model/weight was downloaded or swapped.
- REDMI_UNVERIFIED. Last V13OBS #115 is historical (2026-11-24): updater enabled and runtime/dashboard UP_TO_DATE at release `8d93236`, but AI STOPPED_BY_USER and model process STOPPED. Read-only owner relay issues #978/#979 had NO_LIVE_RECEIPT at last poll. No UPDATE_REQUEST, CHAT_SEND, restart, shell command or deployment was sent. Current updater/device state is unverified.
- No app, permission, model, weight or user data was changed.

## Next executable action

1. Core rebases #2525 onto the latest #2524 head and refreshes only its owned source pins; rerun exact staged/integrated CI without weakening the pin.
2. Once integration is green, run a native diagnostic only on an already-present GGUF with separate explicit local approval; measure actual target scores and answer correctness, not just synthetic receipts.
3. Before any B3 activation, add source-authentication, mapper/backdoor, indirect-injection, cache-privacy and multi-hop retention/utility gates.
4. Keep Android/Redmi acceptance and updater state UNVERIFIED until a fresh authenticated device receipt exists.

**User action:** none required for this code/CI step.
