# STEP2 original real-native output semantic-gap audit — verified 2026-10-30

## Exact source and fixed scorer
Preregistered `25cee7edb95b50853d72095dfd2d05026b75d074`, parent `3efc8da2b1b74ecb62992c4efafc55391c2c2924`, Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Read-only scorer `scripts/step2_currentchain_native_semantic_gap_20261030.py` blob `63b75c73eabdbcf1633eb32875f16c38e7b8c1e1`, tests blob `249064f44e5cd0af6cd20aab1f1d5b24adeace1e`. No model call, model/cohort/seed edit, runtime change or gate promotion.

Input: the **original** Linux-native current-chain ZIP from Actions **40987192595**, exact SHA256 `ad961abb8eea8d567f58cbc4f1fed67f7a79920e36564bb5527b7ea08fa4f3f7`, pinned tested HEAD `3c9e961d123e5bed1826802fc3e236c19078f5ee`, frozen `v13/proofs.py` SHA256 `c757aac40a4a267ad7dd338042fb7a2a02fb0de395c7543ef77a4e3d55b2ce9b`. Independently downloaded by read-only CI; ZIP digest, CRC, 27/27 inner hashes, source/model/tool blobs, exact proof scope, Age0 and FINAL checks validated before scoring.

## Original scorer RED, repaired scorer GREEN, **native semantic FAIL remains**
- Original scorer CI Actions **40988628552 RED** at head `de889da9c861487d4626465dc3207c1cfe5686ee`: 5 tests, 4 failures. Scorer mistakenly rejected correct positive text when the explicit word *left/remain/Rest* came **after** the currency. The original native output was still successfully audited and scored 0/2.
- Narrow regex repair `ffe84e972021a3e34c62e9cfe8291b053d2e8de9` permits an explicit remainder phrase after the amount while stopping at the other option/sentence boundary. No fixture/threshold edit.
- Actions **40988786202 GREEN**: **5/5 scorer tests PASS**, all **8/8** stages exit0 (CANON, FOCUSED, DOWNLOAD, AUDIT, NEGATIVE_EXPECTATION, COMPILE, PRIVACY, DIFF), privacy CLEAN.
- **Actual real-native answer scored 0/2 required budget remainders**. It repeated the 120 Euro budget, Rot cost 80 Euro and 2 days, Blau cost 110 Euro and 1 day, but did **not** state the requested **Rot 40 Euro left** or **Blau 10 Euro left**. STEP12 structural status remains `VERTICAL_CHECKS_PASS`; semantic status is **`SEMANTIC_REQUIREMENT_FAIL`**. The separate ordinary `ask` from the same original proof also made an unsupported preference for the 110 Euro option; no utility claim follows.
- This is a **single-arm diagnostic**, not a paired no-body/one-body/both experiment and not evidence of B1/B2 complementarity. `comparative_utility_proven=false`, `step2_gate_promoted=false`, `native_executed_here=false`, `redmi_measured=false`, `jepa_weight=0`.

## Durable evidence
- Original scorer RED ZIP artifact **12948450852**, SHA256 `4e44cfcf9062ffc8431240a2eab2fe18647f49014dedd299abb6d403c3126db7`, CRC clean, **19/19** inner hashes.
- Scorer GREEN / original native semantic-negative ZIP artifact **12948207008**, SHA256 `b928fbb619bd19bc523566a253ae96bdc50f8cf035ee524c442dc4dd0c88bdd0`, CRC clean, **19/19** inner hashes.
- Both private Library backups byte-reverified at `/V13-Checkpoints/2026-10-30/Run11-STEP2-NativeSemanticGap/`. Original native ZIP remains separately backed up under `Run11-CurrentChain-Age0-Connected/`.

## Next implementation
Owner: V13 hourly automation, review-only. The next substantive STEP2 package should test **actual source-grounded computation** of the two remainders in the output path, not just run more structural smokes. Preregister a fresh paired native no-body/one-body/both comparison with disjoint tasks, exact fixed scorer, same pinned models/seed, controlled C3 output and no changed original cohorts. No STEP2, B3, Body-JEPA, JEPA, Age or whole-system promotion.
