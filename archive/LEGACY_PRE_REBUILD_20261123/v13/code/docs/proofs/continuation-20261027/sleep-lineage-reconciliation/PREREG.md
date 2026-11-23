# V13 Sleep A / Context OS source-lineage reconciliation — preregistration

Date: 2026-10-27 UTC. Scope: **review-only** branch, not main or runtime promotion.
Base: PR #791 branch `assistant/v13-c1-world-b3-sleep-hx134-integration-20261027` at exact commit `6c5dbf145380956ac29bf2d5479ec489ebc7ef5a` (its full software result was measured at an earlier exact head, not at this new candidate).

## Why
The current branch still has `sleep_offline.py` Git blob `4deb3205b84e1fef5bcb0a65cbbe6abcb533ccaa`: cached Sleep digest text is exposed by `view` and `context_items`, and `stage_ttt` reads stored digest without complete source revalidation. Current `history.py` blob `05455f297205b40fe8e0f818c4657f1fedcd9fa3` lacks the previously reviewed complete-pair/source checks. This is **previously identified prior art**, not a new discovery.

## Exact prior-art candidates, no silent redesign
- PR #235 / Run207: staged TTT source revocation.
- PR #236 / Run208: live digest provenance and shared checked-entry function.
- PR #278 / Run278: operator `:sleep digest` provenance guard. Final prior-art source blob `e51766478fee915824853da7c8e73785b12e91b3`.
- PR #87 / Run53 and later integration: strict `native_history` source/role/event/session validation, prior-art blob `a7138080e19b439331bf4c5da68e7e62f823f169`.
- Tests from verified prior art: Run207 `783092f081ede8fbfb8de3fd9879816b560f2fb4`, Run208 `b80eeacc38375368d35bdb8041f52ec42a70cbc2`, Run278 `947286a7e2debd2795c77bf1efe1a2fa98000fe5`.

## Candidate owner and test plan
Owned paths only: `v13/code/v13/sleep_offline.py`, `v13/code/v13/history.py`, the three named old tests, this evidence directory and a dedicated GitHub Actions workflow. Other owners' C1, B3, World-JEPA, HX134, AG8 and Sleep A exact-ID source are frozen.
First import exact prior-art Git blobs without changing their content. Run original three test files plus `tests.test_sleep_offline`, `tests.test_history_lineage`, `tests.test_sleep_a_exact_recall_identity_review`, `tests.test_sleep_memory_c3_continuity_run205` if available, and the full `unittest discover` suite. Check byte identity, all negative gates, compileall, privacy. If a missing old test dependency exists, report it rather than silently invent a pass. Use Linux software/synthetic evidence only.

## Hard boundaries
No native inference, training, external tools, new authority, production merge or Redmi proof. STEP2 remains UTILITY_FAIL; B3 L1 FAIL; Body-JEPA unavailable; jepa_weight=0; age/human approval unchanged; canonical_architecture_complete=false and user_full_scope_complete=false. Preserve prior RED failures, source/model/seed hashes. Do not touch the concurrently owned strict AG8 merge branch. Any failed run remains evidence, not a promoted result.
