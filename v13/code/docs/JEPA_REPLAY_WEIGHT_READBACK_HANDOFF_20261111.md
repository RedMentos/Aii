# JEPA/Memory owner handoff — 2026-11-11 10:30 Europe/Berlin

## Verified dependency state
- #1758 `6502a1ec702a397d5615606805928f5acace1d78`: GitHub Actions `42987204375` SUCCESS (exact head); synthetic Android Notes→persisted simulator receipts→WorldJEPA replay on/off.
- #1759 Boss composite `1cf60224bbbf39e4c0e80f0c75c5ba8627687e1a` and #1761 Core Android typed action/outcome `b634889a3dd0d0d455872b400c41e6ffe4276d65`: parallel branches, do not overwrite. #1760 Research RAW EAR is a separate audio-contract branch.
- #1716 integrated Runtime `01890c92de9e0b3638899b2e2ecf4c8a84d1fac2` now records optimizer/EMA/RNG resume evidence in a staged copy, but has known red full suites. Do not conflate with #1758's simulation-only WorldJEPA.

## This branch
- #1762, atop #1758. `android_sim_jepa_probe.replay_ablation(..., checkpoint=...)` saves the **actual replay-trained** model after the on/off comparison and immediately verifies source-pinned inference reload on the old held-out cohort.
- `android_goal_replay_retention.run_goal_replay` now consumes the readback and returns its checkpoint SHA and loss. Negative test uses a wrong source SHA.
- The existing checkpoint export is **inference-only** and **exclusive-create**. It does not persist Adam/optimizer state, so it is NOT a training-resume or incremental multi-session model. A second call reusing the same checkpoint path cannot silently overwrite it. Do not claim continuous learning from this branch.
- New exact-head CI workflow `.github/workflows/v13-jepa-replay-weight-readback.yml`; CI was queued/in-progress when this note was authored. No new Android device evidence, no real T8 imports, no Body/C3/GGUF/voice weight changes, no permission promotion.

## Priority next integration, not more isolated guards
1. Reconcile #1716 optimizer-resume candidate with the real trusted T8 transition store and a fixed, held-out, source-disjoint replay/retention cohort; adopt one checkpoint generation+cursor+optimizer transaction and actual normal-runtime consumer.
2. Core owns B1/B2 target optimizers/float adapter and Android native companion receipts; JEPA supplies source-bound `LearningIntent`, numeric gradients/EMA/eligibility and forgetting metrics, **not** unscoped writes to other models. Boss integrates. QA verifies rollback and native Redmi CPU/RSS/PSS.
3. Audio mandatory open scope: #1760 RAW EAR contract should deliver timestamped acoustic features, consent and source lineage; JEPA must later add supervised acoustic/speech adapter update, aligned ActionOutcome/replay, before/after and timbre/prosody/ASR retention with restart. A text TTS chain is not learned voice.
4. Android background/API-first + authorized UI fallback; simulation cannot grant OS permissions. Full end goal is local Redmi Android, not desktop.
5. Preserve existing FAIL/SHADOW gates; no permanent freeze of allowable local model plasticity; no uncontrolled base-weight edits.

**Claim level:** SHADOW / SOFTWARE-SIMULATION / REVIEW-ONLY. Full blueprint, native Redmi, true cross-organ weight editing and active voice learning remain OPEN.
