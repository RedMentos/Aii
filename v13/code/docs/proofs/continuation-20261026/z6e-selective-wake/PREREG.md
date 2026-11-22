# WP-Z6e PREREG: §24.22 C-native vs. selective body wake (real models)

Written 2026-10-26 before the measurement run (seed 37). A smoke run on dev seed 5 with 5 tasks only checks that the
new one-body modes really wake that body; its numbers are not evidence.

## Arms (one fresh home each, same bench mode as Z6a/WP-T3b: temperature 0, greedy C3, 600 s deadline, 180 s observers,
post-commit observers cut after FINAL)
- C_native only = effort `disabled`
- A only = new effort mode `detail` (only B1 detail body, re-entry 0, all limits still bind)
- B only = new effort mode `gist` (only B2 gist body)
- A+B = effort `max`
- adaptive = shipped effort `adaptive` (scaffold signals choose none/one/both)

## Tasks: 5 classes x 12, seed 37
easy (small talk + polite rewrites, new), summary (factual/exact), long (long-context/global), compare (mixed reasoning),
notes (novelty/conflict). Regex checks on the final answer as in WP-T3b.

## Criteria (all for Z6E_SELECTIVE_WAKE_PASS)
- E1 easy tasks stay cheap: adaptive plans a body wake on <= 20 % of easy tasks and passes at most 1 fewer easy task
  than C_native.
- E2 few unnecessary wakes: adaptive wakes a body on <= 30 % of the tasks C_native already passes.
- E3 escalation recall: of the tasks C_native fails but A, B or A+B passes ("rescuable"), adaptive wakes a body set
  that contains a passing arm's bodies on >= 70 %. With fewer than 5 rescuable tasks E3 is NO_RESCUE_HEADROOM (not PASS).
- E4 adaptive passes at least (best fixed arm - 3).
- E5 adaptive mean time to answer <= 60 % of A+B.
Reported, not judged: false cheap-route rate, wake/pass/time per class, tasks a body fixes and tasks a body breaks.
Not measured: energy and unsupported factual claims (no checker); phone run (Z7). FAIL stays FAIL.
