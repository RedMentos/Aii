# Run62 — original Cypress five-call Linux-native B1/B2/C3 → Run61 C6 v2 SHADOW preregistration

**Date:** 2026-10-31 UTC. **Owner:** GPT-6; review-only branch `assistant/v13-run62-native-c6-v2-gpt6-20261031`, exact base Run61 `0d0189d52c48af80c76e690e0bcf4904c7f3a459`. Preregistered **before** Run62 runner/verifier/tests/workflow. No modification to original Run59/Run61/seed607 or any registered source/model/seed/scorer.

## Hypothesis and purpose

Run61 has 63/63 software SHADOW tests but uses synthetic B1/B2 and C3. Run59 had five real pinned B1/B2/C3 calls but its original C6 v1 preflight returned **C6_GROUNDING_RED**. Test the new C6 v2 source-bound grammar and newer-USER/OfferPacket lifecycle in a **separate engineering replay** with the same original Run51 Cypress correction/followup fixture (seed467). This is not a disjoint utility cohort, not an independent second-attempt improvement, and cannot promote STEP2.

## Frozen source, model and procedure

- Original Run51 Cypress source, value `64 Euro`, seed467 fixture SHA256 `160128b2f5df2a5798ae7ec62687e6be5a8e61f6c6b2dad43f1ad253ee592ecc`; unchanged original Run59 prompts and C3 `seed=13`, `max_tokens=96`.
- Four real pinned Body calls: B1 LFM2.5-1.2B Q4 model SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`; B2 Qwen3.5-0.8B Q4 model SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`. Correction/current per role, exact OfferPacket/retained topic state, unload between calls.
- One real C3 LFM2.5-350M Q4 model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, frozen llama runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`.
- New `scripts/run62_crossorgan_c6_v2_native.py` derived as a **new file** from original Run59 runner, only stage function/claim/status/schema adapted to Run61 C6 v2. Independent `scripts/run62_crossorgan_c6_v2_verify.py` checks all original native, Store, SourceRef, prompt and process invariants plus new C6 v2 status. Preserve original Run59 files unmodified. No human TTY approval, no FINAL/output/tool/learning, no model weight changes.
- Run isolated GitHub Actions ubuntu-24.04 native under existing `v13-step2-budget-paired-native-20261030` serial concurrency group. Use pinned checkout, explicit source/fixture/model hashes, isolated dependencies, bounded native timeout, closed original raw logs and ZIP SHA256 manifest even on RED. No paid provisioning or private data.

## Registered outcomes and hard gates

**Structural PASS:** exactly 4 pinned real Body FINAL + 1 pinned real C3 FINAL, correct source/packet/retained state, 5/5 reaped, closed SQLite audit, no FINAL/output/TTY/tool/learning authority. If any structural check fails, `STRUCTURAL_RED`.

**C6 v2 result:** `C6_V2_PREFLIGHT_ONLY_NO_APPROVAL` only if the actual C3 candidate passes Run61 lifecycle and source-bound C6 v2; otherwise `C6_V2_GROUNDING_RED` (including non-lexical output). The workflow may fail on utility/grounding RED **while preserving a valid structural native proof**; no red re-score, no prompt/seed/model/scorer adjustment after seeing outputs. The original Run59 C6 RED and C3 seed607 utility RED remain frozen.

No comparative utility claim even if v2 preflight passes. No current Redmi measurements, B3/Body-JEPA/World-JEPA promotion, age change, or whole-system completion. Native runner and independent verifier are not evidence until original raw is downloaded, hash/CRC/manifest checked, and report replayed.

**Next after launch:** verify original ZIP and report, save private byte-identical backup, update scoped BUILD_STATE and proceed to another substantive Canon package. Never call a pending native run complete.
