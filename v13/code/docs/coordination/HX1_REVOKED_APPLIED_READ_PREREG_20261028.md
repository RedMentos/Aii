# HX1 applied harness read after AG8 revocation — preregistration, 2026-10-28

Parent exact verified Linux software head: `5aa5888e32c158aab67ed5d8d1b9f6b19c1b70eb` (PR #806; Actions 40609405189 2102 OK/1 skipped). This is an independent sibling of F5/HX3 cross-organ PR #807, not a replacement for it. Source owner: `v13/code/v13/agi/harness.py` and a new HX1 test only. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Observed read-side gap

`HarnessLibrary.apply()` verifies an AG8 durable approved request before storing a SHADOW override, but `resolve()`, `overlay()`, `manifest_fields()` and `report()` read the persisted override without rechecking the AG8 approval. If the operator later revokes the request, evaluators can still receive the withdrawn override (no live runtime consumer currently exists, so this is evaluator/read-side authority only). HX3 already rejects revoked AG8 read authority; HX1 should not contradict it.

## Registered contract before source edit

- Create two independently approved harness proposals on the same allow-listed target and apply both, plus an independently approved second target.
- Before revocation, newest target wins. Revoke the newest AG8 request; the effective read must fall back to the previous **still-approved** target value (not the revoked value). Revoke the older approval too; fall back to the live default. An unrelated approved target remains available.
- `resolve`, `overlay`, `manifest_fields` and `report` must agree on the same effective approved view, including after Runtime restart; no live code is rewritten, no automatic persistence mutation or learning update.
- History truncation/missing provenance must fail closed to default, never to a withdrawn override; manual rollback remains available.
- Run test-only RED on unchanged parent source first, preserve raw CI evidence and hashes; then narrow fix + focused and full Linux software tests. No native/Redmi, Age promotion, HX2 gate, live harness consumer or JEPA utility claim.

The parent PR #804 full test failure (B3 pressure fixture) remains recorded, and the independent PR #807 cross-organ test is not overwritten. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and whole V13 incomplete. Next command after test commit: GitHub Actions focused run, inspect raw log and SHA before editing source.
