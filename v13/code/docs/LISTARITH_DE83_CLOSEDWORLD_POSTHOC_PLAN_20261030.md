# Original seed83 Linux-native raw → closed-world SHADOW posthoc replay plan

2026-10-30. Owner `assistant/v13-de83-closedworld-posthoc-run11b-20261030`, parent PR #1224 head `842f024b0b6a6ab47f0a9deb0d06558fcaf823bb`. Original seed83 native raw is **already known**, so this is explicitly **posthoc** (not blinded/preregistered efficacy). Freeze this plan before the audit implementation.

Original unmodified Linux-native Actions `41013265710`, artifact `12958586993`, ZIP SHA256 `e92fda4b20a0ba01e533d1b2a343091fb4f46bebe7c9e8a60efdf3f2ca667f57`, exact source HEAD `b0d81e4e811a7c9482a717fb03eea99a1d893b17`, 24 rows, original status `NATIVE_DE83_SHADOW_PILOT_SIGNAL`, supported 15/16, unsupported 8/8, no wrong emission, 24 reaped. Original ZIP CRC and 48/48 SHA256SUMS independently verified before this plan. Existing frozen audit `scripts/listarith_de83_native_shadow_audit.py` must run unchanged.

## Audit design and acceptance
- Download the **original** artifact, require exact ZIP SHA256, CRC, closed 48-member hash manifest, safe ZIP member paths and expected raw file count; never use an editable extracted directory as source of truth.
- Run the frozen independent seed83 native verifier against a fresh safe temporary extraction. Require original status/score and exact native model/seed/source/PID/age gates unchanged.
- Evaluate each original `raw_output` through the **new** seed101 closed-world candidate, record per-row original status, candidate status, operation/value correctness against frozen fixture, abstention reasons, and the delta. Do not alter original native rows, report, scorer, model or seed.
- Report exact coverage tradeoff and all failures, including conservative abstentions on metadata/year/aggregate/multiline. Do **not** require a predetermined success fraction or promote STEP2; report honest result. Preserve original raw and derived JSON as distinct evidence.
- Unit tests must include byte-tamper rejection, ZIP traversal/symlink rejection, inner hash tamper, missing row, original native score preservation and negative gates. Workflow stages capture raw, SHA256SUMS, privacy/diff and closed artifact.
- Linux native **historical input** replay; current execution is **software posthoc**, no new model calls or Redmi measurements.

Follow-up after verified save: improve general coverage only with **new disjoint preregistered** data; or prioritize a separate JEF/C2/Body/JEPA/Context OS canonical package. All original failures preserved. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA unavailable; jepa_weight=0; whole V13 incomplete.
