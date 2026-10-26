# Run605 prospective exact-current B1 LFM2 native read-only latent tap

2026-10-26 UTC. Owner GPT automation11. Base verified Run604 PR599 checkpoint `f79e5d9156cd025364c357d61c0b545d1460066a`. Review-only branch `codex/automation11-run605-native-b1-latent-tap-20261026`, no main mutation.

Problem: Run604 proves B2 Qwen 1024-dim final-state native readout on current source, but the B1 LFM2.5-1.2B 2048-dim source half lacks an exact-current paired proof. This package adds an isolated read-only B1 tap protocol and tests to make the native B1/B2 latent prerequisite reviewable. It does not implement B3 latent injection or training.

Files owned: new `scripts/run605_b1_native_tap_probe.py`, new `tests/test_run605_b1_native_tap_probe.py`, new `.github/workflows/run605-native-b1-latent-tap.yml`, this proof folder. Preserve original Run179 B2 script, native runner and pinned registered model/source/seed bytes.

Protocol: source-only adversarial tests for wrong model/archive and locked role/spec/authority; exact current SHA-pinned original public B1 LFM2.5-1.2B QAD-Q4_0 model and b10964 runner; 3 real native read-only final-state taps of identical/identical/changed synthetic prompts, finite nonzero per-token 2048-dim vectors, repeatable token IDs and source sensitivity; no learned weights, no latent injection, no Age/learning promotion. Serialize in `v13-native-c3-run131-serialized`. Independent postflight, privacy and original raw SHA closure; preserve any RED attempt.

Evidence limits: Linux-native read-only B1 tap only; not Body-JEPA, not B3 L2, not B3 utility, not semantic complementarity, not Redmi, not sparse training. STEP2 UTILITY_FAIL, B3 L1 FAIL globally, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.