# WP-N7 Context OS warm F5 authority — preregistered review candidate

Date UTC: 2026-10-27. Review-only child of PR #793 at exact `893ae11f0b16ea3e39b56dc2c4a173ad794715b1`; **parent full software CI 40599666914 pending at preregistration**. Do not integrate on a failed parent. This branch is separate from Sleep PR #792 and its integration branch.

Previously verified prior art: PR #271 Run271 (dependent on PR #270). RED: warm path resurrected a correction after F5 HumanDecision/feedback revocation; GREEN: validate eligible warm memory pool through `Memory._verified_rows` before applying the 2-slot budget. Existing current `context_os.py` `07b46ade7a1dbefce01343c95ea822c8a6deca3e` has the older unguarded `warm` method. PR #793 adds the required F1/F5 `Memory._verified_rows` without removing current semantic-query reset, stable selection or route supersede. Do not copy all old Context OS code: merge only prior Run271 warm method, preserve other current modules byte-for-byte.

Owned paths: `v13/code/v13/context_os.py`, prior exact Run271 test file, this evidence directory, dedicated CI workflow. Freeze Memory, route, Sleep, C1, B3, World, HX, AG8 and canon. Verify the new method preserves SHADOW vs explicit ACTIVE and two-slot capacity. Run exact Run271 six cases, current ContextOS, semantic, memory, route, Sleep and full software suite. Preserve raw failures, artifact hashes, privacy and private backup. No claim before new exact-head GREEN.

No native/Redmi, new authority, weight update or JEPA utility. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, jepa_weight=0, Age/approval unchanged, whole V13 incomplete. Integrate with sibling Sleep only after both branches pass independently and a fresh combined full suite passes.
