# G13 scheduler active-dispatch capacity: preregistered independent review

Date: 2026-10-27 UTC. Owner: GPT-6 automation continuation; review-only child of PR #737 exact `3b6ce3fb75f99fb8b44ad555e34f30a29c9307e3`. Parent source blob `v13/code/v13/scheduler.py`: `16bc01f68c3e2e9456881262866c384ed9441809`.

## Counterexample / expected RED

`MAX_PENDING=256` is advertised as a bounded durable scheduler queue, but `_post` only counts `PENDING` and `HELD_AGE`. `DISPATCHED` records remain in `events` until `complete` or restart. A caller that dispatches without completing can add unlimited new `DISPATCHED` records, bypassing the memory bound. Use `unittest.mock.patch('v13.scheduler.MAX_PENDING', 3)` and real `post/next` to reproduce with three in-flight jobs, then assert fourth post is refused. Add second counterexample: two in-flight plus one lower-priority pending, high-priority post may evict pending but never an in-flight job. Retiring an in-flight job must release capacity.

## Proposed GREEN

Count all active records (including `DISPATCHED`) when enforcing `MAX_PENDING`; evict only eligible `PENDING/HELD_AGE` background victims, never `DISPATCHED` and never a foreground victim. Reject new posts when all slots are in-flight. No scheduler action, Age right, learning, privacy, model, source cohort or native runner change.

## Verification contract

Focused: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_sleep_scheduler.SchedulerTests`; compile; `public_repo_privacy_scan.py --base 3b6ce3fb75f99fb8b44ad555e34f30a29c9307e3 --head HEAD`; `git diff --check 3b6ce3fb75f99fb8b44ad555e34f30a29c9307e3 HEAD`. GitHub Actions must retain raw logs and exit codes for both RED and GREEN, with exact commit SHA. Later full-suite if dependencies available. Report negative gates unchanged: LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`, Age authority 0, Redmi unmeasured, V13 incomplete. This software test cannot promote them.

No main merge without independent review. Existing PR #737 full-suite result and original artifacts must remain unchanged.
