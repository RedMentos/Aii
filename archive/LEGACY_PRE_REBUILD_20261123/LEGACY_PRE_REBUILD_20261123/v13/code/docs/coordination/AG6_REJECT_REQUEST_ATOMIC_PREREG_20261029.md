# AG6 rejection/request atomicity — preregistration (2026-10-29)

Parent: PR #1117 exact head `7bab483e8e92916f3aa74a51102dc54ffd02235c` (review-only; not production-integrated). Owner: this branch only, `v13/code/v13/agi/weights.py`, one new regression test, one scoped workflow, this prereg/handoff. Do not change registered cohorts, model/seed/source pins, or approval authority.

## Independent finding / original counterexample

`WeightConsolidation.reject` currently invokes `StateBox.mutate(fn)`. Inside `fn`, it independently commits `UPDATE requests SET status='REJECTED'` through `Store.tx`, then `StateBox.mutate` persists the AG6 batch state in a separate write. An injected SQLite trigger aborting that second write leaves an existing human request REJECTED while the batch remains PENDING_USER. A stale retry can also race with an approval because the two writes are not serialized as one operation.

## Predeclared RED / GREEN / no-promotion tests

- Real SQLite Store, synthetic trainer only. Stage, train, gate with valid metrics; require PENDING_USER and exactly one PENDING request.
- Install `BEFORE INSERT ON states` trigger for `G6_WEIGHT_CONSOLIDATION` that raises ABORT. Call `reject`: original must leave request REJECTED and batch PENDING_USER (test asserts both remain PENDING; original RED expected). Drop trigger and retry: batch REJECTED, request REJECTED. Restart: both still REJECTED.
- Inject a request-status mismatch (no PENDING request) and assert a rejection cannot commit the batch alone; no fabricated approval/activation.
- Retain legacy ability to reject an unrequested STAGED batch and to repeat rejection; disallow APPROVED/ROLLED_BACK rejection.
- Candidate: put request update and batch state change in a single `Store.tx`, validate current state under lock, require exactly one pending request for a PENDING_USER batch. Never create a request or activate an adapter.
- Run focused tests, full unittest discovery, compileall, public privacy scan, git diff --check on the exact candidate head. Preserve original RED and any inherited RED (notably parent full-suite frozen-source identity failures). Raw logs and source hashes required before any GREEN claim.

Evidence classes: software/real SQLite only, **no native model, no Redmi, no AG6 human approval**. Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 unapproved; V13 incomplete.
