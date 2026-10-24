# Run42 preregistration — source-bound Sleep A TTT staging (isolated candidate)

Parent: 66114664c46f2b803f1c5619b54a7872c2d6d0e3 (newest verified Run41 at discovery). Ownership exclusively `v13/code/docs/proofs/continuation-20261024/sleep-ttt-lineage-run42/`. No changes to frozen production runtime, original cohorts, JEF/Body owners, or acceptance gates.

## Problem and expected checks

Current `v13/code/v13/sleep_offline.py:stage_ttt` stages digest-conditioned training candidates from cached digest entries. Unlike `context_items`, it does not revalidate each source lineage at export. Revoked input, removed fixed-answer dependency, or stale assistant messages may survive in both the target and earlier context. This is a static source-review finding; native exploitation not claimed.

Build a separate fail-closed staging candidate using `v13.history.native_history` to revalidate user/assistant pairs and all their transitive source refs at the time of staging. Include only matching FINAL user/assistant pairs within the currently verifiable bounded history, reject stale digest message IDs and modified digest text, require assistant metadata `model_generated`, and revalidate every context entry. Missing, revoked, malformed or truncated lineage means skip, never backfill with unverified digest text. No new learning or Age authority; staging only. Atomic output, deterministic bounded order, no publication of private user text.

Predeclared synthetic tests: valid two/three-turn case stages only eligible later targets; revoked target and revoked earlier context each yield zero candidates; missing/stale assistant or digest mismatch rejected; malformed lineage/JSON fail closed; cross-session isolation; repeated export deterministic; zero valid candidates replaces old export with empty file; no source or weights written. Test candidate against adversarial fake stores, preserving negative logs. No full-system, Linux-native, Redmi or training utility claim.

Original gates retained: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; full V13 INCOMPLETE. Independent runtime integration/review remains required.
