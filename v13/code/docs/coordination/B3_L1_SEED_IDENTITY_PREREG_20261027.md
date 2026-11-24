# B3 L1 paired-seed identity review — preregistration (2026-10-27)

Parent: PR #781, `6ce9754a418dc85204efed174c1b0ef23e0f8ae4`. Review-only child, not main and not production. Owner: GPT independent B3 gate review. File ownership: `v13/code/v13/b3bridge.py`, `tests/test_b3_l1_seed_identity_review.py`, the two existing synthetic-positive L1 fixtures, and this coordination record. Do not touch model/source cohorts, raw native evidence, or other owners' branches.

## Falsifiable defect

The current `l1_gate` checks only vector length, not which registered seed each channel row represents. It can return `PASS` with five values from different seeds, shuffled order, duplicated seed IDs or no seed identity whatsoever. Equal lengths do not prove a paired experiment. Run483 independently proposed SHA-pinned row alignment (PR #481, unmerged); this review adds a fail-closed guard at the actual L1 diagnostic boundary, without claiming external row authentication.

## RED tests before fix

1. Existing complete synthetic fixture with no per-channel seed identities must `FAIL` instead of `PASS`.
2. Seven arms with explicit matching ordered seed IDs and otherwise valid synthetic values may produce diagnostic `PASS` but grant no runtime LATENT authority.
3. Reorder LATENT IDs, replace a seed, duplicate an ID, supply a length mismatch, malformed type, blank or oversized ID: each must `FAIL`, never L2.
4. NO_MESSAGE must have zero byte cost (cost semantics), not silently accept positive bytes.
5. Existing negative controls (cheap EXACT, excessive role-drop, missing arms, nonfinite scores) remain `FAIL`; prior synthetic positive fixtures gain explicit five-seed IDs without changing scores.

## Implementation and evidence contract

Accept a `seed_ids` mapping with exactly one ordered vector per required channel, identical unique IDs across channels, each ID a bounded nonblank ASCII identifier. Missing/invalid/misaligned IDs fail closed. This validates declared identity, not independent provenance; real preregistered seed/source/model hashes and row pins remain separately required for an actual B3 L1 promotion. No native run or device proof is implied.

Commit tests first, run focused RED in CI, preserve failure. Then implement and run focused GREEN plus full software regression, preserving raw exits, privacy scan and all historical negative gates. No auto-merge, no LATENT authority, no age promotion, no `jepa_weight` change. B3 L1 canonical `FAIL`, STEP2 `UTILITY_FAIL`, LP1/LP2/BJ1 negatives and whole-system incomplete.
