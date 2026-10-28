# Needle3 primary-source routing interpretation — 2026-10-28

**Primary sources (read-only research, no new dependency or release promotion):**
- Cactus Compute official source and model contract: https://github.com/cactus-compute/needle
- Cactus Compute official pinned model page: https://huggingface.co/Cactus-Compute/needle3
- Cactus official porting/geometry notes: https://www.cactuscompute.com/blog/porting-needle

The official Needle3 docs describe **tool calling**, **structured extraction** and **text embeddings** as distinct functions. Their claimed calibrated confidence is for the model's native tool-calling regime; it is not proof of calibration for V13's custom four-way `select_processing` route labels. The official source also distinguishes a local LoRA path (confidence head left untouched and output confidence `None`) from platform fine-tuning (model/head recalibrated); do **not** use local-adapter confidence for approval or C2 authority. Native embeddings `needle_embed` may be useful for a separately trained route readout, but that would need a **disjoint training cohort, frozen hyperparameters, heldout retention and explicit approval**, not retroactive fitting on English96 or transfer64.

V13's exact installed Needle model remains the existing pinned `Cactus-Compute/needle3` revision `b274efcb211a9eef48c9a88da4b43bd569696a39`, `needle3.cact` SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`, Apache-2.0. The upstream docs can change after the pinned revision; no unverified current feature is assumed available in V13's pinned binary.

**Project evidence supersedes general vendor benchmarks for V13's specific routing task:** #850 native English96 Needle 15/96 and confidence AUROC about 0.4583, scaffold 46/96. The new frozen bilingual transfer64 is an independent evaluation, not an automatic confidence calibration or route-head promotion. Age0, Redmi, STEP2/B3/JEPA and whole-system negative gates remain unchanged.
