# Run95 phone-source package preregistration — 2026-10-31

Owner GPT-6 Auto11, review-only child of Run94 source chain exact parent `8d3d4d28313394de7ec023fcd29497d56bfd3b81`. Do not change Runtime/Store/Canon/models/seed/cohorts/frozen proof. The goal is a **usable, inspectable Termux source ZIP** for the current partial Age0 implementation, not a claim of full blueprint completion.

Source pins verified against remote Git blobs: `scripts/package_source.py` `06167e0bcb82b36cb08841cd31b9618c4ba0926e`; `scripts/phone_release_audit_candidate.py` `0ee88aa7d470c9b7824bfb534214375f75a12dbe`; `STARTEN.sh` `25b7e8d6864cc84d6791bd638aabdf14a077852b`; Canon v10.16.1 `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Parent Run94 unfiltered original-artifact suite Actions `41200093567` IN_PROGRESS at prereg; package launch only after terminal GREEN and independent original ZIP audit.

## Plan and acceptance
- Use existing `package_source.py --root v13/code --phone-install` unchanged, output `V13-Redmi-Install-Run95.zip`, no GGUF/user DB/token/secret.
- Verify ZIP with existing `phone_release_audit_candidate.verify_archive` (CRC, exact manifest, hashes, regular-file/no-symlink/path traversal) plus source pin check for Canon and STARTEN.sh, required `v13/`, `tests/`, `scripts/` and `specs/`.
- Extract into a fresh scratch path and run **real model-free integration tests**: `tests.test_package_source`, `tests.test_source_handoff_candidate`, `tests.test_native_firing_runtime_candidate`, `tests.test_run34_c3_native_quote_intervention_pilot`, `tests.test_run37_c3_rule_use_native_pilot`, `tests.test_run83_native_driver_fake_c3`, `tests.test_run90_exact_route_lineage` with pinned isolated deps. Do not omit failures; all must pass for scoped package acceptance. Full unfiltered suite remains independently covered by Run94 with exact original ZIP prerequisites; do not call extracted focused suite full acceptance.
- Preserve pack stdout, test stdout/stderr, SHA256 manifest, ZIP outer SHA256, privacy/diff, stage exits and original ZIP artifact. Private Library backup byte-verified, public GitHub review-only source and CI (not model/data).
- Phone install is **not executed** here. Redmi RSS/thermal/battery, native body/model, STEP2/B3/JEPA and long-term learning remain unmeasured. Existing `STARTEN.sh` can install models only after user explicitly runs it; no automatic device action.

## Gates
Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight0, Redmi UNMEASURED, whole V13 INCOMPLETE. If Run94 full-suite RED, preserve RED and defer ZIP acceptance until root cause is understood. No merge to main.
