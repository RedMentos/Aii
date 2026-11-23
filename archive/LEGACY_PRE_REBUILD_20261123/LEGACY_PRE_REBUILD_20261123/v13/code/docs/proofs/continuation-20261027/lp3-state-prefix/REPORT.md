# WP-LP3 predicted-state-to-answer soft-prefix mechanism — 2026-10-27

**Review-only research candidate** `codex/automation11-lp3-state-conditioned-prefix-20261027`, exact parent BJ1+N7 integration `5bbcd8e7f8b1d4518fb2de45edc70b6350bdd068`. Roadmap WP-LP3 follows LP1 `NO_ATTRIBUTABLE_GAIN` and LP2 `ALIGNS_NO_GAIN`. Those failed/negative experiments and frozen cohorts are untouched.

## New functional path

`v13/lp3_state_prefix.py` implements a frozen causal decoder whose answer-token logits consume a **trainable soft prefix derived from a predictor of prompt-only hidden state**. The actual answer cross-entropy backpropagates through prefix projector and predictor, not through frozen base weights. Teacher forcing uses logits at t-1 to predict each answer token at t. The mechanism has explicit `own`, `shift` (wrong assignment) and `zero` controls, strict shapes/finite inputs, no base dropout in training, and an API that extracts state from prompt only.

`tests/test_lp3_state_prefix.py` uses a randomly initialized tiny frozen GPT2 decoder (no downloaded model) to check nonzero answer-CE gradients into predictor/projector, frozen base parameters, swapped/zero-state logit effects, causal alignment, target-free prompt-state extraction, deterministic mode and invalid-input rejection. This is a **real differentiable consumer in a tiny synthetic HF model**, not a production C3/B1/B2 integration, useful answer accuracy or JEPA proof.

## Evidence / gates

- Focused workflow `.github/workflows/lp3-state-prefix-review.yml` pins CPU Torch 2.14.1 and Transformers 5.20.2. **CI pending at checkpoint; no PASS claimed.**
- Next real study needs an independent preregistered C3 source/cohort with frozen LP2 heldout, five known failed questions, fresh harder paraphrases, wrong-assignment control, base CE/retention/drift comparisons and a genuinely source-valid inference route. Do not silently reuse LP2 results or claim a gain from gradient flow alone.
- `jepa_weight=0` in registered paths, STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1 NO_SIGNAL, Age authority 0, Redmi unmeasured, whole V13 incomplete.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_lp3_state_prefix`.
**Next prerequisite:** verify exact-head synthetic CI and independent review; only then design a new source-hashed real-model preregistration without overlapping the active BP2b native owner.
