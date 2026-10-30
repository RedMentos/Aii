# STEP2 v3 counterbalanced 9-task Linux-native result — VERIFIED, pilot signal NEGATIVE (2026-10-30)

**Scope:** preregistered new seed41, nine source-disjoint budget tasks, 27 isolated native turns, three arms A_C3_ONLY/B_DEFAULT_BOTH/C_ARITH_BOTH in a balanced Latin-square order. Review-only PR #1204, source HEAD `5e802d235c9501879a3aff07e5134c1455e1769b` on Actions **40996792157**. This is **Linux-native**, not Redmi, and all routes are operator overrides, not native C2 selection.

## Original closed evidence and independent verification

- GitHub Actions run **success** on 2026-10-30 03:31:04 UTC; **10/10** stages exit0 (PINS, VENV, DEPS, FOCUSED, BOOTSTRAP, PILOT, REPORT_CHECK, COMPILE, PRIVACY, DIFF). Privacy `CLEAN`. Native success means the experiment executed, **not** that the utility hypothesis passed.
- Original artifact **12951963045**, ZIP **297655 bytes**, SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46`. Independently downloaded, ZIP CRC clean, **53/53** inner `SHA256SUMS` entries correct, 54/54 members accounted for, no duplicate/traversal paths. **27/27** raw native event/FINAL output byte matches, **351/351** structural flags true, **36/36** B1/B2 process releases reaped. Each original row has valid model role, native runner/model identity, source/route override, and no source errors.
- Original Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, tools `954a3f468f10195fbce12d27f68585ee7edee2c9`, v3 source `dc0c46fc66c6547bca2f22a9eb7dd2cda2c9d279`, tests `57cf6adfa5fce1d1594bfadd25c9b111e105926c`, original scorer `fcd44ccce3b8b40d65a25187a78b0a8d49d9609d`. New fixed fixture SHA256 `fe9b86fdf561778ad540dd4767111f04c10a147a8a44cf783fa16f0d2c8a45ca`, seed41, nine exact fixtures and balanced order verified.
- **Private durable backup** `/V13-Checkpoints/2026-10-30/Run11-STEP2-V3-Counterbalanced/NATIVE_40996792157.zip` was uploaded, materialized again, SHA256 checked and byte-compared identical to original. The preflight ZIP was separately byte-verified. Do not publish private evidence.

## Frozen preregistered lexical score (out of 18 per arm)

| Arm | Option A correct /9 | Option B correct /9 | Total /18 |
| --- | ---: | ---: | ---: |
| A — C3 only | 0 | 0 | **0** |
| B — default B1+B2 | 9 | 1 | **10** |
| C — arithmetic-question B1+B2 | 8 | 1 | **9** |

The predeclared exploratory signal required C >= B+3 and C >= A+3 with all 27 native rows valid. **`pilot_gain=false`**: C is **1/18 worse than B**, so this counterbalanced cohort **does not replicate** the smaller seed29 v2 pilot signal (v2 A2/8, B3/8, C5/8). Neither experiment establishes statistical generalization, body complementarity, a STEP2 acceptance gate or mobile utility.

**Critical scorer limitation (posthoc, not a rescore):** the frozen lexical scorer recognizes certain option-bound `leaves/remaining` claims but **does not credit bare arithmetic equations**. C3-only on Prism actually printed `196 - 137 = 59` and `196 - 185 = 11`, both numerically correct, yet both frozen labels are `MISSING`. C3-only Meridian printed a correct Amber `214 - 127 = 87` but a wrong Indigo `214 - 192 = 72` (expected22), also both scored `MISSING`. Therefore **0/18 is a frozen lexical metric, not proof that C3 made zero correct arithmetic statements**. Boreal's C3-only expression `244 - 305 = 61` has the right magnitude but wrong operand order and must not be silently credited. Preserve original frozen scores and raw outputs; any expanded equation-aware semantic scorer needs separate preregistration and source-disjoint validation.

**Observed model failure:** second-option remainders are particularly weak: B and C each get only **1/9** B-option exact remainders, often emitting spurious leading 1xx amounts (e.g. 118 instead of18, 123 instead23, 122 instead22). B got first-option 9/9, C 8/9. These are model-output observations, not exact source arithmetic capability. Native elapsed sum recorded per arm: A ~16.2 s, B ~298.2 s, C ~267.9 s across nine isolated turns; different routes and workloads prevent treating these as a matched latency speedup.

## Gates and next authorized work

`native_c2_control_proven=false` (all routes `OPERATOR_ROUTE_OVERRIDE`), `comparative_step2_gate_promoted=false`, STEP2 **UTILITY_FAIL**, B3 **NO_PROMOTION**, Body-JEPA **UNAVAILABLE**, `learning_mode=RECORD_ONLY`, `jepa_weight=0`, Redmi unmeasured, historical Run34/Run37 full-suite pin RED, whole-system incomplete. No registered v2/v3 scorer/model/seed/hash is changed. All original failed and successful attempts remain.

**Next command:** independently compare 27 `pilot/raw/*.json` against `pilot/report.json`, retain original ZIP SHA256 and source blobs, then develop a separately preregistered **equation-aware contradiction-vetoing semantic scorer** on new held-out source-disjoint outputs and test a genuine native C2 route path. The isolated C2 `Runtime._route` preflight is GREEN on PR #1205; now that v3 native owner has terminated, its native pilot may run serially. Do not use any posthoc rescore to retroactively promote v3.
