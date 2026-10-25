# Run278 — source-bound human-visible Sleep digest (2026-10-25)

## Owner and dependency
- Owner: Run278, exclusively `v13/code/v13/sleep_offline.py`, new Run278 test/workflow and this proof directory. No other active owner's file modified.
- Base: PR277 `93b15be78b000c2621b494d1623795e0e86afad6` (review chain PR270→271→272→273→274→275→276→277). Do not merge independently into old main.
- Canon untouched: `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Original `BUILD_STATE.json` untouched: Git blob `fdf0827d7c4af5cdb85b69cbe651ed52784a07b5`.

## RED-first observed actual software
- Test commit `0fcca40a33de03adddde282619dc78941ac802ac`; CI-workflow commit `6674f5657c4ece6999e9f75e8d5218669d7c745a`.
- GitHub Actions exact-head run `40191638988`: 24 tests, **4 FAIL / 20 PASS**; official public privacy scan CLEAN.
- Failures: deleted source leaked via `:sleep digest`, revoked earlier source leaked, forged persisted digest shown to operator, copied digest shown in unrelated session. Valid digest control PASS.
- Closed RED raw artifact `12598247205`, ZIP SHA256 `7060f38357de37e84c87ea184283df0709f12c2de4d64c032d030d3f326bac8d`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40191638988/artifacts/12598247205

## GREEN and review
- Production commit `c493b127f655b2bcb9b07a43904ebdd368bf2e28`: `view` uses existing read-only `_checked_digest_entries` lineage validation before presenting any persisted digest text. No change to C3 context, TTT, Sleep learning rights, weights, model pins or age.
- GitHub Actions exact-head run `40191704283`: **24/24 PASS**, compileall PASS, official privacy scan CLEAN, Linux/SQLite/software only.
- Closed GREEN raw artifact `12597738376`, SHA256 `c2873e60a095a498b6e744605c984aef5442450385f0b62a5e59121192c7e129`.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40191704283/artifacts/12597738376
- Remote blob readback: production `e51766478fee915824853da7c8e73785b12e91b3`, test `947286a7e2debd2795c77bf1efe1a2fa98000fe5`, CI `d4fc727335a5b978f6f3312194574540f1ceb77b`.
- Cross-review limitation: no independent external agent was available in this session. Reviewed against the existing Run207/208/219/274 source-bound paths, with adversarial RED/GREEN controls; no claim of full-suite or native proof.

## Separate parent finding
- PR277 exact-head CI `40189028071` is **FAIL** (offline diagnostic subprocess cannot install numpy from offline index). The source ZIP integrity and privacy checks pass. Independent review finding posted to PR277 comment `6397422423`. This does not invalidate Run278's separate source-bound software result; it blocks declaring PR277 parent CI green.

## Gates, blockers and exact next step
- STEP2 = `UTILITY_FAIL`; B3 L1 = `FAIL`; Body-JEPA = `UNAVAILABLE`; `jepa_weight=0`; V13 = `INCOMPLETE`. No Redmi measurement, actual model inference, native training or AGI claim.
- Open: full-suite exact-chain compatibility, parent PR277 offline diagnostic CI failure, real Redmi proof and all original canonical acceptance gates.
- Next independent package: audit `v13/code/v13/episodic_route.py` F5 feedback revocation path; preregister actual Runtime/SQLite RED before editing, use separate branch/ownership and do not overlap active native jobs. Keep this PR as a reviewable checkpoint.
