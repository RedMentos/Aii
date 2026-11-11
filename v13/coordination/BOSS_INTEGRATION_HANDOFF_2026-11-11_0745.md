# Boss integration handoff — 2026-11-11 07:45 Europe/Berlin

## Verified inputs
- Boss #1738 pinned staged composite, #1742 subprocess E2E: head c20cf04ecaf712cdb10e21cdd3493cffeba8adab.
- Core #1744 E2E CI: head 83d148749554b6ead475e86cc7820f3a6962e9cf; run 42969652114 failed **before** runtime tests.
- QA #1745 test fix: head 7585bf80dfaab16c8b081e14c7496032d5b04bd8; test mkdir(exist_ok=True).
- JEPA #1737 head d00d6717b5b2619b55d648d533938a4053a7a209; run 42960032697 PASS, synthetic holdout 0.9094792858 -> 0.8644719075.
- JEPA #1746 head 7c2191dafa8a5c7db23cec2e426df1e9615e8764; run 42972774279 PASS, replay-on old loss 0.4955058173 vs replay-off 0.6964536196, synthetic, not native.
- Perception #1736/#1739/#1743 opt-in route and preflight still separate; no combined candidate verified.

## Work in this branch
Based **exactly** on QA #1745 head. Added Core #1744's CI workflow, with this independent Boss branch named in the push trigger and PR path filters. No changes to Core or QA branches. This is a real executable test runner (staging plus SQLite Runtime/World/T8 restart and revocation), not an evidence-only checker.

## Proof / blockers
GitHub commit and draft PR #1747 confirmed. Exact-head CI has not yet been observed; local git checkout fails with DNS resolution of github.com. Therefore staged E2E is **UNVERIFIED**, SHADOW/REVIEW_ONLY; do not merge or promote.
Next: inspect #1747 Actions logs. If green, pin the dependency chain and wire Perception A5 input and JEPA replay into the staged executable Runtime; do not conflate separate green CI runs with shared end-to-end evidence.

## Completion ledger (current proof level)
| Organ | Implemented | Wired | Tested | Android |
|---|---|---|---|---|
| A0-A5 Perception | partial opt-in candidate | separate PR only | partial synthetic | unverified |
| B1/B2 Body | candidate | pinned composite staging | shared E2E pending | unverified |
| C2/JEF and C3 Language | candidate | staged with synthetic C3 | native inference unverified | unverified |
| T8 SQLite memory/source lifecycle | yes in test candidate | yes | earlier isolated tests; combined pending | unverified |
| WorldJEPA online/EMA | yes synthetic | Runtime + T8 in #1737 | green isolated CI, holdout improvement | unverified |
| Replay/retention | yes synthetic | Runtime + T8 in #1746 | green isolated CI, replay advantage | unverified |
| PC harness permissioned tools | partial design/candidate | no full E2E proof | unverified | n/a |

## Non-overlapping next ownership
Core: native/synthetic C3 and B1/B2 operator output in integrated candidate.
JEPA: source-authorized replay/EMA restore integrated with Boss candidate; real sleep consumer.
QA: run full staged smoke and fix only consequential red failures; no hardware claims.
Perception: connect A5 PerceptPacket to the same candidate input path; verify source lineage.
Boss: coordinate one pinned executable chain, reconcile conflicts and update completion ledger; no unsafe merge.
