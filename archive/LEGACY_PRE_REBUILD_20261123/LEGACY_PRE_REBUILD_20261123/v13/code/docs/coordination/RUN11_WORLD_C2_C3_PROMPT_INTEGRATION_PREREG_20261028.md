# Run11 World F4 + C2 + C3 numeric-prompt review integration — prereg 2026-10-28

**Owner:** GPT-6, review-only branch `assistant/v13-run11-world-c2-c3-prompt-integration-20261028`, exact parent `ba72b8464fa72d860aa05afacf19df6a080952a9` (PR #866 F4 World + C2 scorer candidate, its combined CI pending at prereg). No production/main merge or sibling overwrite.

## Exact inputs and scope

- Preserve parent #866 World source `3799f84fdf52a82efe70e0e5e73bcfe4a95f0ac7`, C2 scorer `12fe792cacd2dc92c2b3c5c33e01424e20a148e4` and tests `48554fd86c985fab520888af8bd7910236589683`. All frozen registered model/seed/source cohorts and negative gates remain unchanged.
- Sibling PR #849 is a **separate** exact native Linux one-case numeric prompt candidate, software GREEN 40633968988, native GREEN 40634460512: one public arithmetic question `Budget 120 Euro. Berechne die Hälfte.` yielded 60 under new generic prompt, but final runner was B1_DETAIL and no paired/general utility was proven. Import **only** its disjoint `v13/prompts.py` Git blob `646c6f31b52ca2664c1952af7c7e842fc3e20885` and `tests/test_prompts.py` blob from exact PR head (resolve before import). Current baseline prompt blob `a74d7517a7ab70e801e177b58da057e57fd3460c`.
- Exclude sibling #860 runtime native route candidate (full suite RED on frozen hashes). Do not turn prompt change into hard-coded 120/60 or claim general arithmetic reliability.

## Plan / acceptance

Preregister first, import exact two prompt/test blobs and verify remote Git hashes. Run source-pinned focused prompt + World F4 + C2 suites and full Linux software suite with compile/privacy/diff and closed raw hashes. Only if parent #866 and this combined branch are GREEN can this be a reviewable cross-organ software candidate; native single-case PR #849 remains independent evidence, not a native test of combined source. Do not rerun native/model jobs while other owners active. No STEP2/B3/Body-JEPA/LP3/jepa_weight/Age or whole-system promotion; Age0 RECORD_ONLY, phone unmeasured. Remaining platform budget UNKNOWN.
