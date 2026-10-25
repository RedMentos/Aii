# Run274 preregistration — Sleep B dream input authority / Sleep A route retention

Base: PR273 exact head `0c58aa2ad9257aea67b5671b6b3aa69255cec539`. Depends on PR270–273. Run274 exclusively owns `v13/code/v13/sleep.py`, `v13/code/tests/test_sleep_memory_authority_run274.py`, `v13/code/docs/proofs/continuation-20261025/sleep-memory-authority-run274/*` and optionally new CI workflow. No edits to PR270–273, native model jobs or SSOT.

RED: Sleep B dream candidate generator directly enumerates active `memories` with readable sources, ignoring F5 HumanDecision/feedback revocation. Sleep A retention `_probe` can pass a route correction whose F5 authority is missing because route checks source bytes but not the human decision. This can generate stale dream hypotheses and false retention credit. Dream fact-write authority remains zero; do not elevate it.

Controls: actual Runtime+SQLite with synthetic route and fact corrections, operator-initiated Sleep A/B, no model/native/Redmi. Valid route/fact remains usable; delete F5 HumanDecision or feedback, change source kind, duplicate decision; Sleep B must not generate new hypotheses anchored solely in revoked memories; Sleep A must not mark revoked route as PASS. Preserve valid independent memories, SHADOW/record permissions, DREAM_HYPOTHESIS_NO_LEARNING and unchanged gates. Reuse Memory._verified_rows read-only, never duplicate authority logic. Test RED first, preserve raw failed attempts and exact exits, run Sleep/Replay/Homeostasis integrations and official privacy scan.

Original gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. Hypothesis validation neighbor path remains separate scope unless explicitly preregistered later.
