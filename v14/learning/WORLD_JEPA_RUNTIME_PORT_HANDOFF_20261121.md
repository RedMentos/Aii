# V14 JEPA & Memory — deployable WorldJEPA runtime port (2026-11-21)

## Scope and ownership

This additive package ports the source/digest-disjoint WorldJEPA/EMA consumer from merged #2151/#2152 into the importable v13.v14_learning namespace so Core's staged Runtime can consume it without copying stale #2145 code. It does not edit frozen v13/runtime.py, the staged builder chain, deployer pins, installed models, or device state.

## Exact source provenance

- Release ancestor: c0cedbde718ede6107f4df1f1bf9c784df4e00cf.
- Learner source: v14/learning/world_jepa_consumer.py at blob 695f8e70a7b14347657165495654327fe2b4ad74; only its authority import is redirected to the deployable package.
- T8 authority base: Core's full-SourceRef correction from branch jepa-memory/v14-runtime-jepa-retention-20261121, blob 73dcbcb1355181fd623b6018e0726d7473fefa15. This keeps the full SourceRef span/modality attached to each verified receipt and retains oldest-first/censored-safe pagination.
- Test baseline: v14/learning/test_world_jepa_consumer.py at blob 91d15f490a260da8b3b113bad4cc52afaaae7c30; imports are redirected to the deployable package. Additional tests cover runtime gates and complete SourceRef.
- No third-party code, weights, model downloads, or new dependencies were added. The learner uses existing V13 WorldJEPA/EMA code and NumPy.

## New runtime API

- consume_after_commit(store, home, limit=64) reads v14.world_jepa.permissions on every call. Both learning_enabled is True and optimizer_permission is True are required; defaults are false. Invalid/non-boolean values fail closed. It then invokes the persistent Store-backed learner.
- receiver_readout(s) exposes the persisted B1_DETAIL, B2_GIST and SELF_MODEL numeric heads as SHADOW_READOUT_ONLY; memory_recall exposes source-linked numeric episodic recall. All have decision_authority=NONE and explicitly report that native body weights were not changed/consumed.
- The learner persists immutable checkpoints, Store CAS state, source/digest-disjoint train/holdout IDs, pending T8 cohorts, replay rows, role heads and rollback generation. It measures encoder/predictor and EMA parameter deltas, holdout utility, shuffled/zero-action negative controls, prior-cohort retention and replay-on/off ablation.
- Optimizer moments and the temporary inverse-dynamics optimizer head are not persisted by the existing WorldJEPA checkpoint format; the learner reports this limitation. Native B1/B2 GGUF weights remain untouched.

## Tests

The new workflow compiles the deployable package and runs the complete SQLite Store/ActionOutcome/WorldJEPA consumer tests on Python 3.13 and 3.14. Tests are synthetic experiences through the real V13 SQLite Store; they are not real-user data, normal Runtime integration, native B1/B2 inference, or Redmi proof.

The current worker has Python 3.13.5 but no local Aii checkout; git ls-remote is blocked by GitHub DNS resolution. Exact local repository tests are therefore BLOCKED. GitHub Actions is the next exact-branch test.

## Integration contract for Core

Core may import consume_after_commit, receiver_readouts, and memory_recall from v13.v14_learning.world_jepa_runtime in its post-action-commit Runtime overlay. Keep the call after durable ActionOutcome commit, use the existing local gate state, and attach the returned role readouts to a source-bound SHADOW packet before any World/Planner/B1/B2 decision influence. Do not reuse the temporal receiver's scalar checkpoint namespace. Keep the stage/deployer chain under Core ownership and rebuild its immutable pins semantically; this PR deliberately does not edit those files.

## Research note

- JEPA-TTT (arXiv:2610.00722; submitted 2026-09-30) supports persistent action-conditioned predictor adaptation and dense replay under one fixed dynamics shift. The authors report an 83% reduction in five-step latent prediction error after 500 episodes, but do not evaluate catastrophic forgetting, returning to prior dynamics, or sequences of shifts. It supports a predictor-only ablation, not a permanently frozen encoder.
- ER-JEPA (arXiv:2609.36952; submitted 2026-09-29) adds episodic replay of paired examples to LLM-JEPA. Its reported gains include 83.65% vs 68.75% exact match on NL-RX-SYNTH for a matched compute comparison; this is not an Android/continual-agent result. It reinforces testing content replay against uniform/no replay under matched compute and memory budgets.
- No code or model license was adopted from either paper; no official implementation repository was verified in this scan.

## Status boundary

CODE_PRESENT / TESTED_SYNTHETIC_PENDING_CI; normal Runtime consumer wiring is still owned by Core and not claimed here. No local exact-repository PASS, no native model-weight proof, no release, and no Redmi receipt. NOT_RELEASED / REDMI_UNVERIFIED.
