# Run306 — WorldModel holdout independence across repeated exact source bytes (2026-10-25)

Owner: GPT-6 automation, new review branch from verified Run305 checkpoint `e73b10853fe74712aa3a49e3f53f3f63fa450235`. Separate from Run303 Budget, Run297 native Context OS, Runtime/Store/Model owners. Own only `v13/code/v13/world_model.py`, new `tests/test_world_source_disjoint_run306.py`, dedicated CPU workflow and this proof folder. Preserve Run301's `world_model.py` source until RED evidence.

## Hypothesis / defect

Run301 correctly made heldout **event**-disjoint, but distinct USER_TEXT events can contain the exact same original text (new source IDs, same SHA256). Those repeated source bytes currently enter both train and heldout as independent event groups, so a fitted WorldModel can report out-of-sample scores without any independent source content. This is source-level leakage, not causal generalization.

## Preregistered actual Store tests (RED first)

1. 12 distinct actual USER_TEXT events, each with two valid closed action outcomes, **all 12 carrying identical source text**. `transitions()` should return 24 valid rows, but `fit()` must return `INSUFFICIENT_INDEPENDENT_GROUPS` and never persist `FITTED` or a heldout metric. Old code is expected to fail this test.
2. 12 distinct actual events, six repeating exact source A and six repeating exact source B (different source IDs, optionally across sessions). Fit must split **whole source-hash groups**: no hash may occur in both train and heldout, `group_split=SOURCE_HASH_DISJOINT`, train/heldout group counts sum to two, and the persisted fitted model must survive restart while source lineage remains live. Old code is expected to fail.
3. 12 unique source texts, two actions each: original Run301 deterministic event-group split, metrics, revision and fitted-state source lineage must remain unchanged. Existing Run301 and WorldModel source/revocation tests run unchanged.
4. Synthetic SQLite test doubles without a production `read_source()` remain labelled `SYNTHETIC_TEST_ONLY`; never gain production authority.

Candidate after RED: on actual Store only, resolve the original EventEnvelope's already validated `sources.hash` for each event; when repeated across events, group all rows by this exact hash, otherwise keep original Run301 event grouping byte-for-byte. Revalidate live bindings before persisting. Never change registered source/model/seed cohorts, thresholds, user approval/age gates, native/Redmi evidence or frozen Canon.

Claim limit: **actual Runtime/Store SQLite statistical holdout correctness only**; no new native model, counterfactual utility, causal generalization or full-system completion. Preserve failures. Exact next command after RED: minimal `world_model.py` patch, Run301+Run298+source-integrity focused CI, official privacy scan, raw hashes and durable checkpoint.
