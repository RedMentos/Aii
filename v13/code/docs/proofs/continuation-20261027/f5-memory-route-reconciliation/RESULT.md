# F1/F5 memory and fast episodic route authority — verified software result

Date UTC: 2026-10-27. Review-only PR #793, base PR #791 at `6c5dbf145380956ac29bf2d5479ec489ebc7ef5a`. Prereg `e122aa58056b40de169e22dd648b7d775bcb773b` predates source commit `d3c9a042ea097ab981622b391e987f52adbd176e`.

## Functional change and newer-feature preservation
The previously validated F1/F5 `Memory._verified_rows` read-side authority proof (prior PR #270) now filters human correction recall before semantic ranking, and the prior Run279 F5 source/feedback verification now guards fast episodic route suggestions. Current `_stable_selection`, semantic query event reset and explicit rule/head `route_supersede` precedence were **preserved**, rather than replacing the entire current files with older snapshots. No write-side `_user_rule_guard` was imported; that remains a separate integration question.

Exact remote candidate blobs: `memory.py` `501c8f43c92f031e034e4b93f4adbd4c67b7edfe`; `episodic_route.py` `04161234548a26284a682a40da09d28242b89e71`; exact unchanged prior Run270 test `1871fed7bbb7fb279dcf86cec4f1ae44e52c1077`; Run279 test `a29b60c9775a72dd866e146a86f438b1d90c281e`.

## New exact-head Linux software proof
GitHub Actions run **40599666914 SUCCESS** at exact `893ae11f0b16ea3e39b56dc2c4a173ad794715b1`: **65/65 focused PASS**, **2050 full software tests OK (1 skipped)**. Raw `BLOBS=INSTALL=FOCUSED=FULL=COMPILE=PRIVACY=DIFF=0`; official privacy scan `CLEAN`. Artifact ID `12778111062`, ZIP SHA256 `5a67dedfe0ef3d7c0183b6eb800aeaf05019b20c13c7214dafa10f5afb9fcabd`, ZIP CRC PASS, internal SHA256SUMS PASS. Uploaded to private Library `/V13-Checkpoints/2026-10-27/Automation11-F5-Memory-Route-Reconciliation/v13-f5-memory-route-40599666914.zip`; materialized private copy and compared byte-exact, same SHA256. Historical RED evidence from PR270/279 remains unchanged.

## Boundaries, next step
Linux software/synthetic Runtime/SQLite only. No native/Redmi, learned utility, real-model improvement, automatic approval, new learning authority or production integration. STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; jepa_weight `0`; Age rights unchanged; V13 incomplete. Independent cross-review required before merge.

Next: source-exact integrate with disjoint Sleep PR #792 on preregistered child `assistant/v13-sleep-f5-crossreview-integration-20261027`, run a **new combined** full software suite and verify all negative gates. Separately, the `ContextOS.warm` path remains unguarded against F5 revocation on this branch; prior PR271 has a narrow candidate and dedicated child preregistration `assistant/v13-context-warm-f5-review-20261027`. It requires its own focused/full proof before integration. Do not conflate branch-scoped results.
