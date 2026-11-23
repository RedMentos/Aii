# WP-BP2b transfer cohort preregistration · 2026-10-27

Owner: automation11 BP2b transfer, **review-only child** of PR #705 exact `592e8975e52e3765e5acd893cd56aa69e936473f`; no native owner claimed. This is a *new* cohort, not a replay/relabel of BP2a seed1/2, BP1, or BJ1.

Goal: test whether the new question-only BP2b locality anchor generator transfers beyond the hand-written training forms. Original BP2a showed leak .75→.16 in a small fp32 B1 setting, but its heldout near misses shared question shapes with manually generated locality anchors.

Freeze **before data generation**: source `scripts.bj1_body_jepa.POOL` (24 invented facts, immutable on this branch), select 16 facts by NumPy default_rng(seed) for each seed in **41, 42, 43**; use 30 steps, B1 LFM2.5-1.2B FP32, CE+KL, jepa_weight=0, rank8, alpha16, lr5e-4, 10 anchor probes/step, 24-token base continuations, 48-token greedy test continuations. A later native run must pin exact FP32 master/source/tokenizer and runner hashes before starting; no unpinned native run is authorized by this prereg.

Four arms, identical facts and controls:
1. `legacy`: original BodyJepaTrainer, `locality_policy='legacy'`, locality_swaps=2.
2. `bp2b`: same with `locality_policy='bp2b'`, locality_swaps=2.
3. `bp2b_minor`: BP2b plus `lora_subspace='minor'`.
4. `manual_ref`: BP2a hand-written near-miss anchors + legacy default, as a separate reference.

Heldout: two **handwritten paraphrased** other-person questions per selected fact (32/seed), from new subject group `roommate, partner, niece, landlord, mentor, coach`, not used by either automatic generator or original BP2a training anchors; source question shape intentionally differs from training anchor grammar. The exact 48-item fixed candidate list is committed with a content hash before any native run. Model-facing heldout prompts must never contain target answer keys or the original answer. Separate scoring-only answer keys; source/evaluation hashes must be verified before training. No mixing train/eval labels or reusing failed run registration.

Prospective software checks: 24×2 heldout prompts unique, no reserved subject used by BP2b generator, no target text leakage, no overlap with generated BP2b/legacy/manual anchors or original BP2a heldout near misses, deterministic 16-item selection, fixed 3 seeds, SHA-bound `--prepare-only` JSON manifest and prompts, zero model downloads. Preserve failed attempts.

Native acceptance thresholds (provisional, must be locked to real gate before any activation): learned recall >=0.90, paraphrase recall >=0.85, heldout near-miss leak improvement >=0.25 absolute vs legacy in each seed, retention not worse than legacy, no source/target mismatch; separate Q4 verification mandatory. Negative gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1_NO_SIGNAL, jepa_weight=0, Redmi unmeasured, whole V13 incomplete.

First package: `v13/code/scripts/bp2b_transfer_cohort.py`, `v13/code/tests/test_bp2b_transfer_cohort.py`, Actions workflow, source-only manifest; **do not start heavy native training** while owner is unknown/occupied. Next command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_transfer_cohort`.
