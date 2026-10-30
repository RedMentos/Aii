# STEP2 fresh paired Linux-native v2 — independent raw audit (2026-10-30)

**Scope:** Read-only review child of PR #1200, original pinned native workflow [40992102064](https://github.com/RedMentos/Aii/actions/runs/40992102064), tested HEAD `382990040c770a89116099d05b60dc87c269d864`. This review did **not** rerun inference, alter the scorer/fixtures/model/source/seed, or promote a gate. Source parent PR #1200 HEAD at review: `e16cea704e079193e08c556d03cebb1fa3a01b45`. The older original seed-13 pilot remains RED and untouched.

## Immutable original evidence and independent checks

- Artifact ID **12949862379**, size **150488 bytes**, ZIP SHA256 **`22c1661038d02219fcd84163b78f428df511811055575cf206df8b90c9b113c4`**. The downloaded ZIP digest independently matches GitHub's artifact digest. ZIP CRC clean; **38/38** inner `SHA256SUMS` hashes match, all 39 members accounted for, no missing or duplicate members.
- Original exact HEAD, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, model catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, tools `954a3f468f10195fbce12d27f68585ee7edee2c9`, source blobs `6bd49f34c0abba03bf459a2031d2fe19ac290bcf`, `ff39f76dd2551b945a9f928b5b53f0918225e0b3`, `fcd44ccce3b8b40d65a25187a78b0a8d49d9609d` match preregistration/workflow pins.
- Fixture canonical JSON recomputed independently from the ZIP with compact separators: SHA256 `b8dba3465d80aa90142065550a6d1b6770b562fd852e25f598ec8260d2bf6cf4`, matching the preregistration. Seed **29**, four distinct new fixtures Solace/Tundra/Harbor/Atlas, three arms each, **12/12** unique raw native records. All report `event_id` and `final_output` bytes match their corresponding raw JSON. **156/156** raw structural check flags true; **16/16** recorded B1/B2 native process releases reaped. C3-only process close is not separately established by those 16 body receipts.
- Original stages **10/10 exit 0**: PINS, VENV, DEPS, FOCUSED, BOOTSTRAP, PILOT, REPORT_CHECK, COMPILE, PRIVACY, DIFF. Privacy scan `CLEAN`. The original GitHub Actions job completed `success` on 2026-10-30 02:38:12 UTC; this means successful *execution*, not STEP2 acceptance.
- **Private persistent copy** `/V13-Checkpoints/2026-10-30/Run11-STEP2-PairedNativeV2/step2-v2-40992102064.zip` was uploaded through the private file Library, materialized again, SHA256-verified and byte-compared identical to the original download. Do not publish the ZIP or private Library URL.

## Exact frozen observed semantic result

| Fixture (expected A/B) | C3 only | Default B1+B2 | Arithmetic-question B1+B2 |
| --- | --- | --- | --- |
| Solace (55/18) | 2/2 | 1/2 | 1/2 |
| Tundra (69/33) | 0/2 | 1/2 | 2/2 |
| Harbor (42/17) | 0/2 | 1/2 | 1/2 |
| Atlas (68/32) | 0/2 | 0/2 | 1/2 |
| **Total** | **2/8** | **3/8** | **5/8** |

The predeclared *small pilot signal* criterion (C at least +2/8 over B and +2/8 over A, all 12 native rows valid) is met: **+2/8 vs B, +3/8 vs A**. It is **not** a STEP2 gate. No inference of statistical generalization or body complementarity follows from four fixtures, a fixed arm order and one seed. The C3-only Solace row itself got both exact remainders correct.

**Observed failure modes:** C on Solace said Quartz **118** instead of 18; C on Harbor said Flint **117** instead of 17; C on Atlas said Bronze **132** instead of 32. C was fully correct only on Tundra. Default B on Solace first said Quartz **68**, then also showed the mathematically correct `167 - 149 = 18`; the frozen lexical scorer does not credit the conflicting output. This is a conservative scoring limitation, not a reason to alter the frozen result. Other wrong or missing second-option values remain visible in original raw.

## Gates, owners, exact next work

Original native route provenance is `route.source=OPERATOR_ROUTE_OVERRIDE`, **not a demonstrated native C2/Needle route**; `native_c2_control_proven=false`. This is **Linux-native**, not Redmi. `learning_mode=RECORD_ONLY`, `jepa_weight=0`, `redmi_measured=false`, `comparative_step2_gate_promoted=false`. **STEP2 UTILITY_FAIL**, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, LP3/JEPA not promoted and whole-system completion false remain. The separate full unfiltered software suite 40991785171 remains **RED** (3425 tests, 2 inherited frozen source-pin errors, 11 skipped).

**Owner:** independent read-only review; PR #1200 owns original pilot source and evidence, PR #1201 owns the JEF software full-suite branch. **Next authorized package:** preregister a larger source-disjoint, counterbalanced paired native comparison with genuine C2 route proof and source-exact two-option arithmetic/error analysis; alternatively implement a strictly read-only native-output-versus-human-F1/F5 arithmetic discrepancy diagnostic with focused tests and no live output authority. Preserve all original evidence and the old frozen scorer. Exact repeatable audit entry: download Actions artifact `12949862379`, verify its ZIP SHA256, CRC and every `SHA256SUMS` entry, then compare `pilot/report.json` to all 12 `pilot/raw/*.json`; never rerun native as a substitute for the original ZIP.
