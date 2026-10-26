# Run604 prospective exact-current B2 native read-only latent tap

2026-10-26 UTC. Owner GPT automation11. Base verified Run603 PR598 checkpoint `9bed17826270f4b97b89d3b17b69b75ade236ed3`. New review-only branch `codex/automation11-run604-native-b2-latent-tap-20261026`, no main mutation.

Problem: Run603 established real distinct B1/B2 native text offers, but did not establish that current B2 Qwen's per-token latent readout is physically available. B3/Jepa needs real source-bound latent taps; do not substitute synthetic arrays or imply receiver injection.

Files owned: new `.github/workflows/run604-native-b2-latent-tap.yml` and this proof folder. Reuse unchanged SHA-pinned `scripts/run179_b2_native_tap_probe.py`, `tests/test_run179_b2_native_tap_probe.py`, `v13/runners.py`, original public Qwen3.5-0.8B GGUF and llama.cpp b10964. No changes to registered cohorts, models, source, seed, Age, learning or approvals.

Protocol: exact current source/Canon/model/runner hashes; model-free adversarial tests; isolated pinned deps and original bootstrap; three real Qwen B2 native token-state readouts (identical/identical/changed synthetic prompt) with per-token 1024-dim finite nonzero vectors, repeatability and source sensitivity; metrics require CAN_LATENT_TAP true, CAN_LATENT_INJECT false, CAN_TRAIN_BODY false. Native execution serialized in `v13-native-c3-run131-serialized`; original report and bounded raw SHA closure, privacy. Failures kept RED.

Evidence limits: this is Linux-native **read-only final-state tap**, not B3 channel utility, learned B3 cross-body alignment, latent injection, Body-JEPA, sparse body weight training, semantic complementarity or Redmi. STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.