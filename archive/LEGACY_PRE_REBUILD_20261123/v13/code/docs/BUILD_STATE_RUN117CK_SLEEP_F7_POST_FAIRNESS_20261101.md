# Run117CK BUILD_STATE — post-fairness F7 Linux Store benchmark (review-only)

2026-11-01 UTC. Child of Run117CJ PR #1562, exact parent `e8fe3197aee1cd36cfa7bacc0619f36dc85cd886`. Owner: Run117CK. Source `sleep_offline.py` blob `dcaaf645d303fc4a4b18414fab4e3fa22957b41f`, unchanged original benchmark script blob `d42c93825298a02381eb362cd7d321cd4e7dc790`, test `896f81b20674e2aeeb7c1a1b14ec18f4354abf25`, Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Terminal original raw

[Actions 41258036470](https://github.com/RedMentos/Aii/actions/runs/41258036470) **SUCCESS**, exact workflow source `57ae58fbfeb11bcd589a8dd27b12d34b8dbbad34`. Original artifact `13063973355`, ZIP size 6,178 bytes, SHA256 `8977fea2a210c7b942bef977370cb8982e60152ab297639d23c9c02edd3b8b48`. Independently downloaded: CRC clean, **24/24** inner SHA256SUMS, all **10/10** stage exits zero, **7/7** software tests PASS, privacy CLEAN, diff check PASS, source pins match. Both benchmarks have `INTEGRITY_PASS`, exact turn totals, closed Store, zero native calls and no authority.

## Descriptive Linux-only comparison to Run117CE

| Workload | CE prior median / max | CK post-fairness median / max | CE / CK peak process RSS |
|---|---|---|---|
| 32 sessions × 70 turns | 28.552 / 163.851 ms | 27.732 / 158.160 ms | 27.39 / 27.35 MB |
| 128 sessions × 1 turn | 4.020 / 7.270 ms | 4.295 / 8.233 ms | 22.25 / 22.19 MB |

Both runs process 2,240 and 128 turns in 9 and 17 cycles respectively. Different GitHub runner conditions and single observations: **no reliable speedup or regression claim**, no performance threshold. This does not measure Redmi RAM/energy/latency, and does not prove any model or whole-system utility. The blocked-session query may add overhead for many sessions; a Redmi measurement remains necessary.

## Next and gates

No source/model/cohort/seed changes, no native inference. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, learning authority0, no whole-system promotion. Next: independently review original CI full-suite Run117CI, reconcile remaining frozen-source and missing-original-artifact failures without waivers; then perform Redmi-specific resource measurements when device access exists. Exact reproduction: `cd v13/code && python scripts/run117ce_sleep_f7_bounded_bench.py --sessions 32 --turns 70 --out /tmp/run117ck-32x70.json` (fresh output path). Platform budget UNKNOWN.
