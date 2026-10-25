# Run201 BUILD_STATE — Age evidence integrity (2026-10-25)

## Parent, ownership and exact source
- Parent: Run200 PR228 `af3aace8d73b23d22d64eec4f56a094aa36519bd` (verified 20/20 Age tests and 401+114 focused/Phone software tests; original red evidence retained). This is a *sequential* edit of `age.py` under the same Age owner, not parallel native work.
- Owns only `v13/code/v13/age.py`, `tests/test_age_evidence_finite_run201.py`, dedicated CI workflow, and this proof folder. No ContextOS Run198/199, B2/C3 native owner, Body/JEPA, Phone production, Canon, Age rights, learning permissions or model cohort edits.
- Full binding Canon blob remains `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Production `BUILD_CEILING=0` unchanged. Tests with ceiling=5 use isolated ephemeral Store and **cannot grant production rights**.
- This work is **software/synthetic**, with real full-checkout AgeControl execution in GitHub Actions, local exact-source cross-review and extracted Phone ZIP source checks. Not a model, JEPA, Linux-native model or Redmi test.

## Actual-source RED (before fix)
- Preregistered tests at `e5bc38dccba4c30183479a7ce69fd116265c84c1`, original Run200 age.py unchanged.
- GitHub Actions `40175611884` / job `121115497380`: **24 tests, 12 FAIL + 1 ERROR**. `experience=NaN` / Infinity, booleans, negative/fractional counts and invalid quality metrics were not rejected; `gate_pass` could treat NaN experience as meeting the threshold. Missing `experience=None` caused TypeError.
- Original raw failure retained: `https://github.com/RedMentos/Aii/actions/runs/40175611884/job/121115497380`.

## Narrow correction
- `_valid_metrics` checks canonical experience as nonnegative integer (or None/missing), each measured quality metric as finite non-boolean 0..1 (or None/missing), and regression_pass as true/false/None. No extra synthetic labels or authority added.
- `record` rejects malformed evidence before reading/mutating persisted stage, hysteresis, noise or maturity. `gate_pass` returns False for malformed/unknown measurements instead of allowing NaN count comparisons or raising on None. Severe regression handles missing retention without a TypeError; two maintenance failures still demote.
- Corrected exact remote age.py Git blob: `7c47181c2a655e31865047fc53a817ae2ac35385`; Run200 parent blob `988f5d97a5c958d1091c61a1b90824f68f690dfb`.
- No new learned policy, model, stage ceiling, rights, default mode or runtime job.

## Verified GREEN and independent review
- GitHub Actions `40175651064` / job `121115623328`: **24/24 PASS**, original Age and Run200 regressions included; compileall PASS; official privacy scan CLEAN. `https://github.com/RedMentos/Aii/actions/runs/40175651064/job/121115623328`.
- Run200 regression workflow on same corrected source `40175651061`: SUCCESS.
- Focused full-checkout source CI `40175651051` / job `121115639858`: **401/401 PASS**, official privacy scan CLEAN; model-free Phone ZIP manifest **951/951** and independent archive audit PASS (SHA-256 `c53859c04b44ce172d55e04e8c9d0958ac6b606acbe4644a282e7e0f87fdf51e`); extracted Phone smoke **114/114 PASS**, Runtime restart PASS.
- Independently downloaded prior Run200 Phone source artifact 12592105617, verified all 950 original file hashes, copied to local sandbox, applied Run201 patch; `git hash-object v13/age.py` exactly matched remote blob. Local original Age/rights/Run200 tests **20/20 PASS**; seven separate adversarial checks PASS. Raw cross-review transcript `LOCAL_CROSSREVIEW.log`.
- No full repository test suite or real model inference claimed. Original red results and connector newline serialization failure from Run200 remain in their respective CI history.

## Original negative gates and next command
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; full V13 `INCOMPLETE`. These were not touched.
- Next: verify PR229 remote head and all owned blobs after this doc commit. Continue a **different canonical organ/package** (e.g. World/JEF/Memory second-attempt source integrity) after inspecting current owner and source, rather than repeatedly hardening Age. Do not overlap active native B2/C3 owner. Native/Redmi prerequisites remain independent.
- No user decision or device action required for these software packages. Do not use rejected anyone-writable Drive destination.
