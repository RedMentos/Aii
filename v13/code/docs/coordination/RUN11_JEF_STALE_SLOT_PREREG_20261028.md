# Run11 JEF no-B proof: stale AG0 slot / manifest removal — prereg 2026-10-28

Owner: GPT-6, isolated review child of PR #844 at `af71f1ebc26d934a180db39f77a2978ced7b6261`. No parent/main overwrite. Source frozen to exact current catalog Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` and control tools blob `954a3f468f10195fbce12d27f68585ee7edee2c9`. No model changes or cohort substitutions.

## Observed RED before code change

Real pinned Ubuntu24.04 workflow 40632157217, artifact 12791672638 ZIP SHA256 `446ecaa32faf9703c4663590620a537ab29e45926e45ac65882d37d05c750ec0` (downloaded and SHA verified; ZIP CRC clean). Bootstrap exit0. JEF modes exit2 `JEF_MODES_PARTIAL`: C2_ONLY, C3_ONLY, C2 native, final output, C1 restart, no B manifest, integrity all true, but `combined_c3=false` and `no_b_dependency_proven=false`. All three combined turns have `runner.role=B1_DETAIL` and real B1 GGUF despite B1/B2 removal from installed manifest. STEP12/ask skipped. Preserve this as native FAIL, not a gate promotion. Full raw evidence remains in Actions artifact.

## Mechanism to test

`probe_jef_modes` constructs Runtime with B manifests then removes B entries from `runtime.models.installed`. `BodyFabric.sync` already installed AG0 active slots; `BodyFabric._committed` compares the slot revision to `_installed_revision(role)`, which becomes None after manifest removal and treats stale slot as a committed replacement. `ModelManager.path_for` asks router before checking installed. Thus a removed B manifest can still serve B1/B2 from a stale slot. A RAMP candidate may also survive manifest removal.

## Pre-registered repair / counterexamples

1. Add a regression that after removing B1/B2 manifest entries, both `ModelManager.path_for` and AG0 path/revision overrides refuse to serve either body, while C3 remains available; include a separate RAMP candidate missing-base case. Existing committed swap and RAMP-with-base tests must remain GREEN.
2. Narrowly require a present downloaded installed base role for AG0 `_committed` and `path_override`; never silently reactivate an orphaned B slot. Do not mutate the model catalog or the role-slot persistence schema. Missing base must fail closed; active swaps with an installed base remain unchanged.
3. Run focused synthetic tests first (RED then GREEN), full software suite, then a **serial** real pinned Linux rerun on a new child workflow/branch. Do not reclassify failed 40632157217. Inspect actual `runner.role` in all C2+C3 rows; verify C3 native and no B dependency only if every check passes.
4. Capture exit codes, raw stdout/stderr, hashes, negative gates and privacy scan; only public prompt diagnostics in GitHub Actions artifacts, never weights/private data.

No claim of STEP2 70-row four-arm utility, B3 L1, Body-JEPA, Redmi, phone thermal, semantic reliability, learning, or whole V13. Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY. No automatic tools or learning authority.

Next: create regression in `v13/code/tests/test_bodies.py`, capture focused RED, apply minimal `v13/code/v13/bodies.py` guard, run focused/full/native separately. Platform budget UNKNOWN.
