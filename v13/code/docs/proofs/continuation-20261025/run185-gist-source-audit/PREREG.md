# Run185 — independent B2 Gist offer source-support audit (diagnostic only)

Parent: Run184 verified CI success `40169536016`, remote head `f291aa9e736a4f0fe81087fcc4fce7b25aefbe90`, PR213. Run181 native 36x3 B2 offer job `40168581804` was still IN_PROGRESS at registration. File ownership exclusively new `scripts/run185_gist_source_support_audit.py`, `tests/test_run185_gist_source_support_audit.py`, this proof folder, and dedicated source-bound workflow. Do not touch Run181 script, report, cohort, model, seeds, acceptance or active native process.

## Why independent audit is needed

The frozen Run181 B2 offer scorer marks a `hit` when the key is a substring of summary, even if a budget is a substring of a different number. It marks `quotes_valid=True` when the quote list is empty (vacuous `all([])`). Its original preregistered acceptance remains binding and must **not** be retuned post hoc. This separate audit reports conservative *additional diagnostics*, not a replacement verdict.

For each of the fixed 36 memos x 3 arms, parse raw JSON, require unique keys, whole-token owner/budget/date mention in the summary, at least one nonempty exact source quote containing the answer key, and flag old deadline mentions even when the new deadline is also present. Require all 108 rows, unique indices, original kinds, positive prompt tokens, pinned model SHA and source-bound fixed corpus digest. Compare source-supported paired wins/losses, quote coverage and tokens as an explicitly **posthoc diagnostic**. The original `GIST_HELPS_CANDIDATE` / `GIST_NO_GAIN` decision is copied unchanged. Never activate Gist from either result.

Local software tests were exploratory **before** this registration: 11/11 PASS. CI must verify unchanged original `gist_utility_bench.py` Git blob `f2b6d00cbe100152bb77a3b04187324eb379abd6`, unchanged Run181 auditor Git blob `30b4f32893ec505e7c3035e76523389233121e9a`, run focused tests and official public-repo privacy scan. No native inference in this package; when Run181 job finishes, independently download/hash/audit the raw report and execute this source-support audit. Preserve failures and raw classifications. No unapproved model/job overlap.

Gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE. Source-supported B2 offer utility does not prove C3 final-answer benefit, B1/B2 complementarity, Redmi performance, JEPA learning or full scope. Rejected anyone-writable Drive destination must not be retried.
