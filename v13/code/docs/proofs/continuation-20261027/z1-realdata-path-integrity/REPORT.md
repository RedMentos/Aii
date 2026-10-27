# WP-Z1 real_data path integrity — closed software review checkpoint (2026-10-27)

Owner GPT-6 automation11, review PR #696, independent child of PR #695 head `6e10df6dafc433e668b1f28a1092e4c88d104aa3` and exact five-parent PR #672. Prereg committed `3677e6d6b232233f6cb86ed43a01cdc2563a6019` before code. Production main untouched.

`v13/code/v13/gates.py` now checks the **real_data** criterion for a regular, non-symlink file lexically and canonically inside the existing `docs/proofs`, `docs/canon`, or `../bench-results` roots. It rejects directory placeholders, path traversal into tests, symlink file/parent, absolute/non-string/NUL/missing paths. It does not authenticate native execution, prove provenance, or alter verdicts/specs/authority. Existing valid registered evidence paths remain accepted.

Original prospective software RED Actions [40489675117](https://github.com/RedMentos/Aii/actions/runs/40489675117) at `e072cd1b090f20c2e1d11afa10daf68703e96a9a`: **30 tests, 17 fixture errors** because the patched temporary `APP` lacked `specs/gate-graph.json`. Source guard not implicated; preserve RED. Original ZIP artifact `12728985351`, SHA256 `6ffdf34e3189c27cc99d9b137454d89561c7ee115dfff627b07e86ae9376e4aa`, CRC/HEAD/exits checked and privately backed up byte-identical `/V13-Checkpoints/2026-10-27/Z1-RealData-Path-Integrity/ORIGINAL-RED-40489675117.zip`.

Fixture repaired without relaxing any guard. Actions [40490160443](https://github.com/RedMentos/Aii/actions/runs/40490160443) at exact source `f069bc2eb4b9bc5f63df394e6b47fa6a51f65733`: **30/30 tests PASS** (new adversarial + original Z1 verdict + register/gates), compile0, privacy CLEAN. Original ZIP artifact `12728651014`, SHA256 `711252258157df34b906ea1ddf18d01e0497c404c7b25af476a39e50d879bfd3`, CRC/HEAD/exits independently audited, private Library backup byte-identical `/V13-Checkpoints/2026-10-27/Z1-RealData-Path-Integrity/ORIGINAL-GREEN-40490160443.zip`.

This is review-only software evidence, not a new native/Redmi run. Historical full suite remains RED (PR #672 baseline 5 FAIL/73 ERROR); do not promote whole-system status. STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, V13 incomplete.

Next independent work: finish BP1 V2 genuine 44-row native path (PR #697, activated serially), independently audit raw outcomes and near-miss/retention controls; separately review the historical broad-suite failures and five-way integration. No merge into production without review.
