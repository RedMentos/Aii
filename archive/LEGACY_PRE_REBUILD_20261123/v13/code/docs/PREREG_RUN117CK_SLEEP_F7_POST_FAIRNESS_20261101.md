# Run117CK prereg — repeat F7 Sleep Linux Store benchmark after blocked-session fairness

2026-11-01 UTC. Review-only child of Run117CJ PR #1562 at exact parent `e8fe3197aee1cd36cfa7bacc0619f36dc85cd886`. Owner: Run117CK. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; no production code/model/seed/cohort changes. New comparison runs the **byte-identical** original Run117CE benchmark script `d42c93825298a02381eb362cd7d321cd4e7dc790` and tests `896f81b20674e2aeeb7c1a1b14ec18f4354abf25` against the post-Run117CF `sleep_offline.py` blob `dcaaf645d303fc4a4b18414fab4e3fa22957b41f`.

## Prior measured Linux-only baseline

Original Run117CE [Actions 41256398222](https://github.com/RedMentos/Aii/actions/runs/41256398222) SUCCESS, original ZIP artifact `13063182396`, SHA256 `1ec69300f46dfb03c4cb6b7880563d66cf8a9561248e55f354596eaf4a08dba9`, independently downloaded, CRC clean, 24/24 inner hashes and all stages 0. On Linux software Store only: 32×70 turns = 2,240 turns, nine cycles, median digest 28.552 ms, max 163.851 ms, peak process RSS 27.39 MB; 128×1 = 128 turns, 17 cycles, median 4.02 ms, max 7.27 ms, peak RSS 22.25 MB. **These are not Redmi measurements and are not acceptance thresholds.**

## Fixed protocol

Same synthetic source-bound real Store workloads, exact 32×70 and 128×1, no model downloads or native inference. Integrity: every source-valid turn exactly once, cursor catch-up, no duplicate, closed Store, no fact/learning authority, no Redmi claim. Report Linux walltime and process RSS descriptively. Runner noise, machine differences and the added blocked-session readiness query make any latency comparison approximate; do not claim a speedup/regression solely from one sample. Do not modify source/benchmark/cohort, no threshold, no waivers, preserve all raw including failures. Source pins: history `867d06c230ed3860f12cb7d256579c07cb214e91`, Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`; no native/Redmi/learning/whole-system promotion. Next: launch pinned CI, verify original ZIP/CRC/inner hashes, private backup; if overhead large, plan Redmi measurement before optimization. Remaining platform budget UNKNOWN.
