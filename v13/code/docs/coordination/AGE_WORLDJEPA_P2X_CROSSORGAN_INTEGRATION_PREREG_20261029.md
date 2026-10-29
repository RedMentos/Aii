# Cross-organ V13 Age0 / World-JEPA / P2X native-launch integration review — 2026-10-29

Parent PR #1092 exact head `3686f6303bf6d38f53f5e553accd5f51aafc553a` (includes World-JEPA donor PR #1091). Independent donor P2X LoRA argv repair PR #1093 exact candidate head `0e5e8351df7cd3a3bc9b90678d76a0415ba0f5a5`. Both source-only exact-head GREEN CI currently pending; do not integrate or promote based on prereg alone. All changes remain review-only and branch-scoped; production main and original owner PR #1090 remain unchanged.

Scope after donor verification: transplant **unchanged Git blobs** from PR #1093 into this integration branch for `scripts/p2x_candidate360_standalone.py`, `tests/test_p2x_candidate360_standalone.py`, `tests/test_p2x_lora_scaled_cli_review.py`, plus its prereg/failed evidence note. Existing AgeControl and WorldJEPA code from parent must remain byte-identical. No source/model/seed/adapter/cohort/Canon edits. Retain source hashes, original negative controls, full failed native RED 40872516890, Age RED 40874866326, P2X CLI RED 40875212641 and donor WorldJEPA Run49 RED 40752223744.

Acceptance: exact source blob equality to donors, focused Age + WorldJEPA + P2X tests, full Linux software suite, privacy/diff, raw SHA256SUMS, no changed age authority or false model/Redmi evidence. Verify upstream GREEN before merge-ready status; run a separate isolated native candidate360 only after serial heavy job ownership and pinned binary/model/adapter admission. No cross-organ software test promotes STEP2/B3/Body-JEPA/LP3/AG6.

Negative gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Redmi UNMEASURED, whole V13 INCOMPLETE. Platform remaining budget UNKNOWN.
