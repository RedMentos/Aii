# Run11 current integration — serial native Age0 JEF/STEP12/ask preregistration (2026-10-28)

**Owner:** GPT-6 independent review branch `assistant/v13-run11-jef-after-ag0-native-20261028-0805`; immutable parent `5ff280db555658d912b36f2a3189ecdb4efcff1e`, PR #868. Do not overwrite PR #868, sibling #847, Codex or Claude owners. No main merge. Existing active/queued GitHub Actions native jobs: none at prereg inspection. Native workflow uses existing shared concurrency group `v13-run11-age0-native-endtoend`, serial stages, and no paid provisioning.

**Why now:** Prior actual Linux native #844 run 40632157217 is RED: `JEF_MODES_PARTIAL`, combined C2+C3 selected B1 after B manifests were removed; STEP12 and public ask skipped by that workflow. PR #846 identified stale AG0 slots, and PR #868 integrated exact `bodies.py` blob `82fb81c8a98c51ca1c339737184e2fda8ab6a692` with F4 World, validated C2 benchmark and numeric C3 prompt. Combined software CI 40647087335 at `ac24a0b0c75bbb132db0557bd81b9c263927e284` completed GREEN, but **no integrated native rerun exists**. PR #847 C5+AG0 branch full suite 40633149062 RED on source-handoff frozen-runtime hash; do not silently import that runtime or weaken hash guards.

**Pinned source snapshot (Git blob IDs, verify before native):**
- `v13/code/v13/runtime.py` `68e7ed1352800174972558f1e0b0683a42c8689a`
- `v13/code/v13/focal.py` `2135f4404f241cfc198abd7fe2288f13a622f4fc`
- `v13/code/v13/bodies.py` `82fb81c8a98c51ca1c339737184e2fda8ab6a692`
- `v13/code/v13/world.py` `3799f84fdf52a82efe70e0e5e73bcfe4a95f0ac7`
- `v13/code/v13/prompts.py` `646c6f31b52ca2664c1952af7c7e842fc3e20885`
- `v13/code/specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`
- `v13/code/specs/control_tools.json` `954a3f468f10195fbce12d27f68585ee7edee2c9`

**Method / acceptance:** Fresh Ubuntu24.04 ephemeral V13_HOME, isolated dependencies, `v13.bootstrap` retrieves only the existing pinned public models/Needle/llama.cpp. No substitutions. Serial independent stage execution after bootstrap: `probe jef-modes`, `probe step12`, public `ask 'Budget 120 Euro. Berechne die Hälfte.'`; run STEP12 and ask even if JEF is RED, to preserve separate observations. Capture all stage exits, raw stdout/stderr, proof JSON, catalog/source hashes, `ModelManager.verify(deep=True)`, Age0 gates, privacy/diff checks, SHA256SUMS, and upload **reports only**, not model weights. Assert native JEF C2+C3 routes to C3 with no B manifest, actual B1 and B2 offers in STEP12, and a nonempty final ask. Numeric quality requires explicit check of final text; no assumed 60. A failed stage remains RED and never promotes any gate.

**Claims:** Linux-native bounded integration only; no Redmi/thermal, STEP2 four-arm utility, B3 L1, Body-JEPA, LP3 heldout gain, live JEPA training, AGI or full system. `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3 heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, whole-system incomplete.

**After run:** Independently inspect all raw logs/ZIP hashes and report failed stages. If native JEF still RED, implement a separate source-frozen, regression-backed remedy or a distinct canonical package; do not modify this registered run in place. Platform remaining budget UNKNOWN.
