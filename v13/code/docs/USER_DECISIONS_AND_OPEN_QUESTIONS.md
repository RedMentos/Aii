# V13 — User Decisions and Open Questions

## USER_DECISION_REQUIRED

- Age plasticity policy: keep boot or switch to noise_aware (measured in bench-results/age-noise-20261010).
- Run the acceptance on the Redmi itself (sustained thermal/RSS proof; Linux cloud runs do not count).
- Give real answer labels (:note 1-10, :feedback, :choose) so learning leaves INSUFFICIENT_LABELLED_COHORT.
- Rerun the 46-row native test on the phone after the SQLite close-boundary guard.
- Confirm the default body pair after measurement: B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B (scripts/timescale_gate.py).
- MobileMoE access: FAIR noncommercial + gated, no GGUF; only with your own access and a runner.

## RESEARCH_NEEDED

- Paired native C3 4+4 comparison complete; broader German quality and target-phone latency/memory comparison remain open.
- STEP2 semantic utility needs validated scoring; sparse-body/full A/B-JEPA, multimodal A3/receiver projectors, native confidence-head training, multi-position native output adaptation and parametric semantic/skill consolidation remain open. External first-route agreement calibration, dense local predictors and bounded wake/halt heads are separate implemented experiments.

## HARD_BLOCKER

- Target-phone sustained thermal/energy + RSS/KV pressure proof requires another real Redmi run.
- Native sparse-body training and B3 latent receiver-effect proof require capabilities not present in this Age-0 build.

## CAN_DECIDE_AUTONOMOUSLY

- Continue STEP1 JEF proof, STEP2 complementarity measurement, and STEP3 second-attempt proof without architecture redesign.
