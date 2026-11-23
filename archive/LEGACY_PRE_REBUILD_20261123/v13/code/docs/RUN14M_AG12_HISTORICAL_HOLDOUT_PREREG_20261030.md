# Run14M prereg — retain AG12 historical holdout exclusions across seed rotation (2026-10-30)

Owner GPT-6, review-only AG12 integrity child of Run14L PR #1329 at `067920aa2d3896917e9cdd07e24b5ba0be28201c`. This document precedes test and implementation commits. Canon SHA blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Existing AG12 `generality.py` blob `357837d8dd312a3a511d96f6e9c320fcf9dc9708`, Run14H suite-identity tests blob `692fd80fb9c53e4f4a9b9053f3e27ce16f526d73`. Frozen suite generation, all old seeds, native experiments, AG9 feedback and negative gates remain unchanged.

## Problem and intended proof

Current `GeneralityEval._register` replaces the entire `holdout` set whenever the same-language seed changes. This permits a historical unseen prompt to enter training after rotation, despite historical `runs` remaining for audit. Fix this **without silent eviction** and without changing suite generation or curve semantics.

A per-language, durable, validated `holdout_registry` stores the exact hash of each registered suite and its unseen-prompt digests. `holdout` is the union of all registered unseen digests. Maximum **32 suites and 2048 unique digests** per language; if adding a suite would exceed either cap, reject rotation atomically and keep the previous active suite and protections. No auto-eviction. Validate registry, digest shapes, and union on every registration and training guard. Legacy one-suite state may migrate by preserving the prior active `holdout`; if historical `runs` mention a suite not reconstructible from the registry, persist `holdout_history_unknown=true` and **refuse training guard and practice export** rather than claiming historical exclusion. Never guess missing historical seeds or overwrite existing raw runs. Separate English/German slots remain isolated; cross-language contamination remains a separate open issue.

## Test-first acceptance

With real Runtime SQLite: seed13 unseen prompt is forbidden before and after seed17 rotation and restart; new seed17 unseen prompt is forbidden too; curves remain suite-scoped, old runs retained; a stale evaluator cannot use training guard. Rotate 32 unique suites, then 33rd fails without modifying StateBox. Simulate legacy multi-suite runs lacking historical digests: training/practice fail closed; original runs remain. Tampered registry, union, invalid digest and overflow fail closed. Existing Run14F/G/H/I/J tests and AG12 native solver boundaries unchanged. No production merge. Test-first original RED and candidate GREEN in source-only CI, exact source pins, raw artifacts, CRC/inner hashes, private permitted backup and remote byte verification.

No learned utility or native/Redmi proof. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; whole V13 incomplete. Native Run14L runs separately at frozen source commit; do not modify its runner, model or cohort.
