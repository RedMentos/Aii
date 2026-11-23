# G15 — exact-original full-suite diagnostic verdict, no waiver (preregistered 2026-10-30)

Review-only child of Run13H #1296 at `129f1b20ee855335225334e0e47d8206da486de6`; owner GPT-6; isolated paths `scripts/g15_fullsuite_diagnostic.py`, `tests/test_g15_fullsuite_diagnostic.py`, own workflow/docs. No Runtime, models, learning, scorer, frozen source-handoff, Canon or prior evidence changes.

## Frozen original artifacts before implementation

- G13 baseline Actions 41069560040, source HEAD `86c706eba2ece7da3234e245a8e3e8860e607b7e`, original ZIP SHA256 `a3f9c4ea76a59865886eb759e9039c6840f0f6f2a009d7e4948ba9fd9c0a0ed1`; CRC clean, 30/30 inner hashes, 3972 tests, FULL_EXIT=1, 4 FAIL/65 ERROR/15 skipped, 120 nested FAIL/ERROR identity entries.
- G14 candidate Actions 41080416868, source HEAD `4c789ae85758ca71bf86dd5067ab697913071a51`, original ZIP SHA256 `77906cc480e18a7695b833896730dded1e5f881278966259a7725440d766c27f`; CRC clean, 32/32 inner hashes, 3987 tests, FULL_EXIT=1, 4 FAIL/65 ERROR/15 skipped, same 120 nested identities SHA256 `e85743aad6bb69a8c319daa93228d7fb0cc8d24a43e5f1a1c41526a1a2b8a3e7`. G14 job terminal FAILURE, not GREEN. Exact original G14 raw is privately byte-backed up. Prior G14 workflow erroneously makes a clean full-suite run mutually exclusive with historical identity match; review comment recorded on #1295.

## Prospective acceptance

Build a **read-only offline ZIP comparator** that validates both user-supplied expected outer SHA256s, ZIP CRC, unique safe filenames, inner SHA256SUMS, HEAD and FULL_EXIT, parses unfiltered raw failure identities as a **multiset**, and reports added/removed identities and suite counts. Do not waive failures or conflate diagnostic success with suite acceptance. States: `HISTORICAL_RED_SAME_IDENTITIES` (suite_gate_pass false), `RED_CHANGED_IDENTITIES` (false), `FULL_PASS` only when candidate FULL_EXIT=0 and zero FAIL/ERROR identities (still software-only), `INTEGRITY_RED` for corrupt/missing/contradictory evidence. All outputs include negative gate nonpromotion. Test-first malformed ZIP/CRC/hash, missing manifest, duplicate names, added/removed identities, false-green exit, and valid synthetic clean suite. Compare exact G13/G14 original ZIPs separately and bind result to hashes. No native inference or model downloads. Unit CI and privacy/diff/Canon pin must pass.

Original RED remains RED. A no-new-identity result is useful to isolate regressions, **not** a complete acceptance gate, native utility, or production integration. Next substantive package remains measured C2/C3/B1/B2 and JEPA utility under registered cohorts, not repeated fullsuite-only work.
