# Run62 research — action-conditioned and compositional World-JEPA (2026-10-28)

**Evidence class: literature/architecture hypothesis only.** No model code imported or pretrained artifact downloaded. Canon and registered V13 cohorts unchanged. Source references are original papers (not third-party summaries).

1. V-JEPA 2, Assran et al. (2025), https://arxiv.org/abs/2506.09985 : action-free self-supervised latent representation followed by separate action-conditioned post-training for robotic planning. This supports V13's separate encoder/EMA target and action predictor architecture as a research direction, **not** a claim of equivalent V13 capability.
2. Slot Structured World Models, Collu et al. (2024), https://arxiv.org/abs/2402.03326 : object-centric slots and action-conditioned graph dynamics motivate sharing transition mechanisms across objects/slots. V13 Run60 is only a **supervised ridge** slot-local control on a six-file-slot world; it does not implement a neural slot-equivariant JEPA.
3. Delta-JEPA, Zhang et al. (2026), https://arxiv.org/abs/2606.31232 : latent-displacement action decoding is proposed as an alternative to endpoint-concatenation inverse decoding. V13 frozen `world_jepa.py` inverse head uses concatenated endpoints. A separately preregistered, exact-budget **delta-inverse vs endpoint-inverse** ablation on fresh real file-action states could test action sensitivity without altering original Z12b failure.
4. D-JEPA, Liu et al. (2026), https://arxiv.org/abs/2609.24749 : decision-aligned latent models motivate checking *actual action ranking/outcomes* rather than latent MSE alone. V13 Run59's synthetic supervised latent readout is action-swap sensitive but less accurate than direct state+action linear baseline; no causal utility claim follows.

## Preregister next, do not silently implement

A same-cohort, disjoint-state real file-action comparison of (i) Run60 slot-local ridge, (ii) frozen original global WorldJEPA, and (iii) an **isolated** slot-equivariant latent predictor with identical action/seed/step/compute budgets and no heldout label leakage. Add action-shuffle/no-action controls, real counterfactuals executed in copies, confidence calibration, heldout op×slot combinations, collapse/retention/rollback gates. Original WP-Z12b W1–W6 FAIL remains historical and is not retested into a pass. Only if same-cohort evidence is favorable should delta-inverse and decision-local objectives be separately preregistered. No Runtime, native Body, Redmi or age promotion.

All current gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0.
