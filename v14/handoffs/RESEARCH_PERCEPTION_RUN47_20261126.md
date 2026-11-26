# Research & Perception Run 47 — 2026-11-26

## Scope and branch

- Repository: RedMentos/Aii
- Existing Perception PR: https://github.com/RedMentos/Aii/pull/2524
- Branch: research-perception/v14-kv-snapshot-consumer-20261126-run35
- Verified exact head: 7bd80e419c851471d95b44cc032efe205a23ab91
- Base PR branch: research-perception/v14-native-receiver-task-matrix-bridge-20261126-run34
- No force-push, merge, release or device action.

## Implemented function

v13/code/v13/native_receiver_utility.py now emits information_use_audit from the existing eight-condition task-utility result.

- system_gain_vs_no_message measures candidate improvement over the receiver-only condition.
- entity_specificity_gain_vs_counterfactual measures candidate improvement over the source-bound ENTITY_SUBSTITUTION condition.
- Both pass flags require the full crossed holdout. If system gain passes but specificity does not, status is SYSTEM_GAIN_WITHOUT_ENTITY_SPECIFIC_SIGNAL.
- Insufficient cohorts are explicitly INSUFFICIENT_HOLDOUT.
- The output says full_derangement_tested=false, semantic_use_proven=false, generated_answer_correctness_proven=false, production_route=false, training_authority=0, native_receiver_authority=0, and persisted=false.

The new tests in v13/code/tests/test_native_receiver_task_score.py cover:
1. System gain with no entity-specific gain.
2. Both gains present.
3. A single task group cannot pass the information-use gate.

Exact source blobs:
- utility: 10277a18634d37a3322289c12189f7b69b9b8ea7
- tests: 395b2d868718a4f94e2fe13b9d22e25c73aa5a37

## Research

- R-166: Full Draft-KV preprint arXiv:2609.34754v1 read. Official Svardfox/Draft-KV inspected at e369f1b2629875642fe5a87feb4d432c6f4971b8; Apache-2.0 code. It demonstrates why receiver accuracy/system gain is not enough: the matched message must outperform a no-fixed-point unrelated-question donor. Its Qwen/GPU setup is not a Redmi recipe. No code or weights reused.
- R-167: Full HST preprint arXiv:2611.08133 read. Qwen3.5-only evidence supports complete K/V+REC+Conv state mapping and continuation calibration; local reconstruction error alone can be misleading. Other architectures/MoE remain untested. No official OSS reuse found.

The Aii adaptation is intentionally narrower than Draft-KV. The current entity-only counterfactual is not a full unrelated-question derangement. A no-fixed-point cross-task donor permutation remains OPEN.

## Tests and environment

- LOCAL_LINUX / CPython 3.13.5: isolated information-use gate reproduction 3/3 PASS.
- Full local Aii checkout / exact repository pytest: NOT_RUN. No checkout is mounted; git ls-remote fails because github.com DNS is unavailable in this environment.
- Exact-head GitHub Actions at checkpoint:
  - 45856881120 V14 native latent receiver: IN_PROGRESS.
  - 45856880943 V13 staged context and integrated regression: IN_PROGRESS.
  - 45856880964 V13 runtime deployment integrity: PASS (offline integrity only).
- GitHub CI is not a local test. No native GGUF was loaded or scored.

## Consumer and user effect

The new field is part of the existing native receiver task-utility result returned by the Perception matrix bridge. It improves diagnostic interpretation only; it does not change normal chat routing, model weights, or installed runtime behavior. Core's Runtime consumer still needs to rebase and refresh its exact source pins before this can be accepted as an integrated diagnostic.

## Open failures / risks

- Core PR #2525 remains based on stale Perception head b298719af8faf75811d03d486de7725395a590b0; current Perception head is 7bd80e4. It must rebase and refresh source/event/Runtime pins.
- Real GGUF matched/negative-control cohort, generated-answer correctness, gradient/retention, restart/rollback and native RSS/TTFT are NOT_RUN.
- Full unrelated-question derangement is not implemented.
- Android microphone/provider, AudioRecord, Redmi native tests and updater deployment are not verified.
- B3 remains OFF; REDMI_UNVERIFIED; NOT_RELEASED.

## Next concrete action

1. Read exact results for workflows 45856881120 and 45856880943; repair any Perception-owned failure.
2. Core rebases #2525 onto 7bd80e4, updates source pins and exposes the audit result.
3. Only after integrated CI is green, request a separate explicit local approval for a diagnostic run on an already-present GGUF. Do not download or swap a model.
4. Add a true no-fixed-point unrelated-question donor permutation and generated-answer correctness before any semantic-use or B3 claim.

**User action:** none required now. No model, weight, permission, app, updater or user-data change occurred.
