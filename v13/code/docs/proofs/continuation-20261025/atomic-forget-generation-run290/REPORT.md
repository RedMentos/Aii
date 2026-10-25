# Run290 — source forget vs newly committed generation

Date 2026-10-25 UTC. Independent owner: `v13/code/v13/memory.py`, new `tests/test_atomic_forget_generation_run290.py`, CPU-only workflow and scoped proof. Base PR289 checkpoint `c712f8df2fc95e88c8ce4a0744e3acc250c2e71d`. PR284 Runtime, PR288 native workflow, PR289 Store and Canon untouched.

## Reproduced defect and repair

`Memory._forget_source` checked active weight lineage **before** its SQLite write transaction. A candidate trained from the source could commit in the gap. Forget then incorrectly reported success, deleted a source used by the newly active generation, quarantined the active update and unlinked its checkpoint. This is a real data-integrity race, not a theoretical argument.

Run290 records the observed `brain_generation_id` at preflight and compares it to `meta.active_generation` **inside the same BEGIN IMMEDIATE transaction** that deletes/quarantines the source. If the generation changed, forget fails without mutating source, update, or checkpoint. The user may retry after inspecting active lineage/rollback. This is a conservative fail-closed check; no new learning or unlearning authority.

Primary sources checked 2026-10-25: https://www.sqlite.org/isolation.html and https://www.sqlite.org/lang_transaction.html (SQLite write serialization and BEGIN IMMEDIATE).

## Closed RED -> GREEN

- RED exact source `a6e66b4200cac4b115711631aaf90538689dc942`, workflow `40196120488`: **70 tests, 1 FAIL, 67 PASS, 2 SKIP**. The new deterministic real Store/Memory interleaving did **not** raise ValueError; the two positive ordering controls passed. Official privacy CLEAN. Raw artifact `12599564807`, SHA256 `9576c069444611b55eff3b699d87988168df457dfd485955d8a5d5837ca5e8f1`.
- GREEN exact source `059c89f71afade06544c932e7f792dcb25d9457e`, workflow `40196200051`: **70 tests, 68 PASS, 2 SKIP (torch absent)**; all three Run290 tests PASS, official privacy CLEAN. Raw artifact `12600485799`, SHA256 `1926e87d48822cf038e30d266febb7d902dd436f1f63dfdbb10ddaea23e426c6`.
- Existing independent source/authority CI on the same source head: Run270 `40196200046` SUCCESS; Run203 `40196200041` SUCCESS; Run103 `40196200140` SUCCESS.
- Focused PR merge `40196200209`: **401/401 PASS**, extracted Phone **114/114 PASS** and restart PASS; privacy CLEAN. Phone ZIP 1002 files, independently verified SHA256 `d38e250d7e8bafd53604c1a8e2b119de0387a422e87f21964513cec9252af2f7`. Outer workflow artifact `12600380988` SHA256 `68a45651b0bfe1514a6efcb641dad9e2677e9fe9d2cd437fba494884dd4c316a`.
- Additional **independent local Linux/SQLite** review: extracted Run289 phone source, applied only Run290 memory patch, verified resulting `git hash-object` exactly `a6a1177d04ce361231f8fcbf343ec4f8ad0d09d0`, ran 53/53 existing source/memory/generation tests PASS and separately reproduced the interleaving refusal and preservation of live source and checkpoint. Raw local logs SHA256 `367b019cfc13f1d96c1f9a3811dd365cf99340d5928f528f14b2f2d694243558` (baseline) and `9f50aac45b3eb3013a1176eacfafbbc08438357ad43e7d57d139f331d91474f8` (independent interleaving, committed at `LOCAL_INDEPENDENT_RACE.log`).

## Hashes and backup

- Canon SHA256 unchanged `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.
- `v13/code/v13/memory.py` Git blob `a6a1177d04ce361231f8fcbf343ec4f8ad0d09d0` (prior `f1f329f181d69c96e253d05f7081afd72cca99dc`).
- New test Git blob `9089b6bb999cf194132eca9ad39128398b2813d0`; dedicated CI `24ba7c98330c5a93b6a423f7a557f9a1c80bf46f`.
- Raw RED, GREEN and complete model-free Phone source artifact ZIPs saved to **private ChatGPT Library** `/V13-Inquisition/Proofs/Run290/`; all three downloaded back and their SHA256 hashes verified byte-for-byte. Rejected anyone-writable Drive destination not used. GitHub Actions artifacts remain available as independent raw source.

## Claim limits / next step

Only Linux SQLite software/synthetic candidate artifacts; **not** native learned-weight unlearning, Redmi or general concurrency proof across external filesystem mutation. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE`. PR284 cancellation still RED/owned elsewhere. Run288 full 20-stage Linux-native acceptance is separately executing on the unchanged parent; inspect all raw stages before selecting next **substantive utility** fix, and do not treat any partial stage as whole-system acceptance. All original model/seed/threshold gates unchanged.
