# C3 scoped correction integrity veto — preregistration (2026-10-28)

Independent review-only child of #892 head `6b4d99822e69ded08ddca3d9c9f4057fa09a351e`; frozen runtime, model catalog and registered cohorts untouched. Owner: ChatGPT continuation; new branch `assistant/v13-c3-scoped-unverifiable-veto-20261028`.

## Counterexample identified before edit
In `v13/code/v13/source_consumer.py`, `recall_and_admit` reads every active exact-key project-budget correction for conflict veto, but silently `continue`s when `memory.candidate` raises and does not independently verify the F1/F5 decision for scanned candidates. A valid first source plus an active same-project correction with corrupt SourceRef/lineage may therefore still be admitted, because the unreadable row vanishes from the conflict set. The original `Memory.recall` correctly filters unverified rows, but the exact-key conflict scan must not turn unverified competing evidence into permission to answer.

## Locked scope and verification
- For every active same-topic exact-key correction returned by the bounded conflict scan, require readable `memory.candidate` and verified live F1/F5 lineage before considering admission. If any row is unreadable or unverified, return deterministic `CLARIFY / UNVERIFIABLE_SCOPED_CORRECTION`, with no model messages. Do not promote invalid rows to facts or change the allowed source grammar.
- Add software counterexample: a valid 615 Euro source plus a second active same-project 700 Euro source whose stored blob is tampered. Actual `Memory.recall` can still return the valid row, but the full source consumer must abstain. Add a mocked F1/F5-verification failure on a competing row and preserve valid single-source behavior.
- Run exact-source focused tests, full software suite, compile, privacy/diff, original frozen blob checks in GitHub Actions; preserve raw evidence and failed attempts. No fake native execution.
- Preserve negative original Stage11/STEP2/B3/Body-JEPA/LP3/Age/Redmi gates; no Runtime integration, no source/model/seed changes. Remaining limitation: only bounded exact-key variants are conflict-vetoed; semantic aliases are still outside this candidate.

Next: independently review compatibility with #891/#893 CLI and #892 renderer, then integrate only through a separate audited branch.