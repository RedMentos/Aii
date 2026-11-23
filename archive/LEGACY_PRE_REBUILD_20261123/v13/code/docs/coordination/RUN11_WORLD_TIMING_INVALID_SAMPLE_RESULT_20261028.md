# Run11 World/Self timing evidence validity — 2026-10-28

**Scope:** Independent World/Self F4 software candidate, review-only child of #850 `b454f81da33de9d621af6417ed47ab55cba6263f`. Preregistration commit `bac0010b6e55c0addce23e888c7aeca38b81dcc8` precedes code. No native model execution, no new JEPA learning, no production/main integration.

## Functional change

`WorldState.forecast` formerly treated booleans and negative numeric `action_duration_s` as valid completed timing samples. `WorldState.observe` could score a completed action with negative elapsed seconds. These values are JSON-serializable, so the Store can durably retain them; NaN/Infinity are already rejected on Store write. The new `_valid_duration` rejects bool, negative, nonfinite and huge overflow values. Forecast now excludes malformed completed timing samples and malformed input-length metadata, records `invalid_timing_sample_count`, and leaves valid sample counts, median, range and profile/session coverage unchanged. Observe only scores comparable finite nonnegative predicted/actual durations and skips learned latent scoring on invalid duration; invalid raw outcomes remain observable and do not become success/learning rewards.

New synthetic Runtime/Store tests: [2,3,4] median3, negative and bool sample exclusion, unscored invalid current outcome, corrupt expected input length rejection and primitive duration edge cases. Existing World state/source/Corollary/JEPA authority and age gates unchanged.

Original `world.py` blob `b4ed658f2212c013b9c77285a3dc2d3dc5553758`; candidate `d9a5e9481acf8c644c956a26201a1eaeaa8baa7a`; new test `57a7758d4cca8195e9c1741566085e447874afcc`.

## Evidence and next proof

Source-pinned GitHub Actions focused/full Linux software workflow staged, **status pending** until raw checked. No actual corrupted production timing rows observed. Next: verify focused/full/compile/privacy/diff, preserve RED if any, byte-check closed raw artifact, review integration impact and only then consider source-bound rollout. No Redmi or sustained thermal proof.

Negative gates unchanged: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, `phone_measured=false`, `whole_system_complete=false`.
## Verified exact-source Linux software closure

GitHub Actions run **40643892257** at source `c31d6ac53f16cd7a8899f0b33b7df4d1d5b10eeb` **GREEN**: **21 focused PASS**, **2219 full PASS, 1 skipped** (159.721s), source blobs/install/compile/privacy scan CLEAN/diff exit0. Raw ZIP artifact `12796872195`, SHA256 `4bb3c4a288ce98d2e073ac431ccf615fb2519334e7cd05261d903b7893aed612`, CRC clean, **16/16** internal SHA256SUMS. Private Library backup `/V13-Checkpoints/2026-10-28/Run11-World-Integrity/WORLD_TIMING_INVALID_SOFTWARE_PASS_40643892257_sha4bb3c4a2.zip` re-materialized byte-exact at the same SHA256. Documentation-only commits after tested source are not separately represented as retested. No native/Redmi/JEPA promotion.
