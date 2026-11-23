# V14 JEPA & Memory — deployable WorldJEPA runtime port (2026-11-21)

## Scope

This additive port moves the merged #2151/#2152 Store-backed WorldJEPA consumer into importable V13 runtime modules. It is deliberately limited to three direct V13 modules, one regression test file, and this handoff. It does not edit Runtime, staged builder files, deployer pins, updater, installed models, or device state.

## Source provenance

- Release ancestor: c0cedbde718ede6107f4df1f1bf9c784df4e00cf.
- Learner source: v14/learning/world_jepa_consumer.py at blob 695f8e70a7b14347657165495654327fe2b4ad74; only its T8 authority import is redirected.
- T8 authority source: Core's full-SourceRef correction from branch jepa-memory/v14-runtime-jepa-retention-20261121, blob 73dcbcb1355181fd623b6018e0726d7473fefa15. Its ActionOutcome packet identity/time and complete source span/modality checks are retained. Its temporal-only page is kept separate.
- Cursor behavior: verify_committed_transition_page is restored to the exact #2151 oldest-first observed-outcome contract, including separate censored counting. Censored-only pages do not advance the JEPA learning cursor; this preserves the existing strict-gate regression.
- Test baseline: v14/learning/test_world_jepa_consumer.py at blob 91d15f490a260da8b3b113bad4cc52afaaae7c30; imports are redirected. Additional tests cover default-off runtime gates, explicit numeric learning, B1/B2/SELF readouts, memory recall, and complete SourceRef.
- No third-party code, model weights, downloads, or new dependencies.

## Runtime API

- consume_after_commit(store, home, limit=64) reads v14.world_jepa.permissions on every call. Both learning_enabled and optimizer_permission must be strict booleans set true; defaults are false. A value such as integer 1 does not pass. Page size is bounded to 16..256 and steps to 1..2000.
- receiver_readout(s) exposes persisted B1_DETAIL, B2_GIST and SELF_MODEL numeric heads as SHADOW_READOUT_ONLY. memory_recall exposes source-linked numeric episodic recall.
- The JEPA consumer persists immutable numeric checkpoints, Store CAS state, source/digest-disjoint holdout IDs, pending T8 cohorts, replay rows, receiver heads and rollback generations. It measures parameter and EMA deltas, holdout utility, shuffled/zero-action negative controls, prior-cohort retention and replay ablation.
- Optimizer moments and the temporary inverse-dynamics optimizer head are not persisted by the existing checkpoint format. Native B1/B2 GGUF weights are not changed or consumed. Decision authority remains NONE.

## Validation

The repository's safe-additive CI compiles the new modules and runs this SQLite Store/ActionOutcome/WorldJEPA integration test on the exact PR head. The tests use synthetic experiences through the real V13 SQLite Store; they are not real user data, normal Runtime integration, native B1/B2 inference, or Redmi proof.

The current worker has Python 3.13.5 but no local Aii checkout; git ls-remote is blocked by GitHub DNS resolution. Exact local repository tests are BLOCKED. No local repository PASS is claimed.

## Core integration contract

Core can import consume_after_commit, receiver_readouts and memory_recall from v13.world_jepa_runtime. Call the learner only after durable ActionOutcome commit. Attach role readouts to a source-bound SHADOW packet and deliver them to a real World/Planner/B1/B2 receiver before any routing influence. Keep the JEPA checkpoint namespace separate from TemporalT8Bridge. Stage/deployer chain ownership remains with Core; this PR does not modify those files.

## Research note

- JEPA-TTT (arXiv:2610.00722, submitted 2026-09-30) supports persistent action-conditioned predictor adaptation and dense replay under one fixed dynamics shift. The paper reports an 83% reduction in five-step latent prediction error after 500 episodes, but does not test catastrophic forgetting, return to earlier dynamics, or sequences of shifts. This supports a predictor-only ablation, not a permanently frozen encoder.
- ER-JEPA (arXiv:2609.36952, submitted 2026-09-29) adds episodic replay of paired examples to LLM-JEPA. Its reported NL-RX-SYNTH exact-match comparison is 83.65% vs 68.75% under matched compute; this is not an Android or continual-agent result. It supports comparing content replay with uniform/no replay under matched compute and memory budgets.
- No code or model license was adopted from either paper; no maintained official implementation repository was verified in this scan.

## Status boundary

CODE_PRESENT / CI_PENDING; normal Runtime consumer wiring remains a Core follow-up and is not claimed here. No local exact-repository PASS, native model-weight proof, release, or Redmi receipt. NOT_RELEASED / REDMI_UNVERIFIED.
