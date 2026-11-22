# STEP2 v3 counterbalanced 9-task Linux-native paired pilot — preregistration 2026-10-30

**Owner:** independent follow-up to PR #1202 at exact parent `4030bd528b670d251960c0f630dd6411e8c006a3`, branch `assistant/v13-step2-v3-counterbalanced-20261030-0419`. Original v2 Actions `40992102064` is fixed, 12/12 native rows and C3-only 2/8, default both 3/8, arithmetic both 5/8 (small signal, no gate); its source, seed 29, fixtures, scorer and raw remain unchanged. Earlier original seed13 pilot remains RED. This is a **new** cohort with source/seed/fixture identities, not a rescore.

## Frozen before implementation

New seed **41**, nine distinct unseen project tasks, fixed source-text grammar, both options local/no cloud, one question per fixture asks the two named remaining Euro budgets and time/cost tradeoff. Canonical JSON fixture SHA256 **`fe9b86fdf561778ad540dd4767111f04c10a147a8a44cf783fa16f0d2c8a45ca`**, calculated using `json.dumps(fixtures, sort_keys=True, separators=(',', ':')).encode()` before source. Do not leak expected remainders in prompts or body questions.

| Project | Budget | A name/cost/days | B name/cost/days | Expected A/B |
| --- | ---: | --- | --- | --- |
| Meridian | 214 | Amber /127 /3 | Indigo /192 /6 | 87/22 |
| Boreal | 305 | Pine /244 /8 | Slate /287 /2 | 61/18 |
| Nimbus | 178 | Pearl /139 /2 | Copper /164 /5 | 39/14 |
| Delta | 267 | Moss /201 /6 | Coral /249 /1 | 66/18 |
| Orchid | 352 | Silver /286 /4 | Onyx /329 /7 | 66/23 |
| Prism | 196 | Dawn /137 /7 | Dusk /185 /3 | 59/11 |
| Summit | 421 | Ruby /344 /2 | Topaz /399 /9 | 77/22 |
| Fjord | 233 | Ash /172 /9 | Birch /221 /4 | 61/12 |
| Helix | 319 | Cobalt /268 /5 | Ivory /301 /2 | 51/18 |

Fixed arms **A_C3_ONLY**, **B_DEFAULT_BOTH**, **C_ARITH_BOTH**. Preserve the v2 B1/B2 arithmetic-question candidate texts and pinned models/catalog/tool hashes. Each of **27** turns gets a new isolated Age0 Runtime, no history or learned state, same native runner/seed and source grammar, strictly serialized heavy calls. **Counterbalanced Latin-square arm order:** fixture indices 0,3,6: A/B/C; 1,4,7: B/C/A; 2,5,8: C/A/B. Every arm appears first, second and third exactly three times. Original v2 had fixed A/B/C order. This removes a major fixed-order confound, but does not establish causal complementarity.

**Preregistered primary outcome:** two option-bound exact remainders per fixture, each scored 0/1 with the unchanged contradiction-vetoing `semantic_diagnostic` source blob `fcd44ccce3b8b40d65a25187a78b0a8d49d9609d`; total out of **18** per arm. `PILOT_SIGNAL` only if all 27 native records valid and C exceeds B by >=3/18 and A by >=3/18. This is exploratory, not a STEP2 gate. Missing/contradictory claims receive no credit. No posthoc thresholds, changed registered model/seed, or automatic promotion. Preserve every raw response, including failed turns.

**Evidence contract:** Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, tools `954a3f468f10195fbce12d27f68585ee7edee2c9`, exact v3 source/test/workflow pins to be frozen after implementation and before native run. The v2 route provenance is `OPERATOR_ROUTE_OVERRIDE`, not native Needle/C2 control. v3 must continue to set `native_c2_control_proven=false`; do not claim C2 route proof. Required native evidence: exact source/model hashes, per-turn event/FINAL/SourceRef links, 27 raw records, 13 structural checks each, 36 B1/B2 release receipts, stage exits, privacy scan, SHA256SUMS, original ZIP digest, private byte-verified Library backup. If any native turn fails, status RED; do not replace failed rows.

**Gates:** Linux-native only, no Redmi, no learned body weights, no latent receiver, Age0 RECORD_ONLY, jepa_weight=0. STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, historical Run34/Run37 full-suite RED and whole-system incomplete remain. Larger disjoint acceptance, native C2 control, independent scorer and target-phone sustained proof still needed.

**Execution plan:** first add v3 script + pure software tests + pinned isolated CI and close its raw. Only after preflight GREEN and an exclusive native owner (no competing heavy job) launch one 45-minute-capped Actions workflow with serialized 27 turns. If native run cannot finish, preserve progress and failure; continue another independent package. Never edit v2 files.
