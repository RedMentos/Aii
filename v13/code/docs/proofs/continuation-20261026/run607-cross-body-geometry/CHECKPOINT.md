# Run607 verified checkpoint (2026-10-26 UTC)

Owner GPT automation11. Review-only PR602, branch `codex/automation11-run607-cross-body-geometry-20261026` at source commit `9b095d3aa389450a2b21570ec488ebe83b751987` (child of Run606 PR601 head `786ca4d1d6df1a33837768ed008cf19d36023130`). This checkpoint document is added after that verified source commit; the branch head will therefore advance without altering its code blobs.

## Exact observed execution and closed evidence

- Run607 Actions `40401075954` **success**; source-only fixtures **6/6 PASS**; original Run606 artifact downloaded; independent offline analysis, privacy scan, and SHA closure all exit 0.
- Artifact `12689036705`, downloaded ZIP SHA256 `6ab74b8793eca949d07f3792bdacb6af863a55cbf1f76160d0b8a09175ea50c6`, 4,672 bytes. `RUN607_SHA256SUMS.txt` verified locally for every entry, including report and original raw references.
- Original input Run606 Actions `40399494903` artifact `12688127140`, native states SHA256 `368efacc04860ca6407aa9296f188a8aa6c3d7760ff44b2724231079b89a62c0`. Original Run606 native status **NO_EXPLORATORY_SIGNAL**: top1 0.30; preregistered 100-shuffle empirical p=0.05940594, failing its p<=.05 gate.
- Run607 **POSTHOC_GEOMETRY_ONLY**: heldout train-mean-centered B1/B2 similarity Pearson RSA **0.8595194881**; token-count/topic residualized RSA **0.7138771714**; within-topic RSA **0.7684301198**; nearest-neighbor agreement **0.30**. Exploratory row-label permutation p (1000) 0.000999 / 0.003996 / 0.001998 respectively. **These are posthoc exploratory values, not confirmatory evidence**; only 10 heldout prompts and no causal receiver/task test. A separate independent local recomputation confirmed raw Pearson RSA 0.8595194881003682.
- Source blob SHAs: `scripts/run607_cross_body_geometry.py` `5fc0030644f6a7b67437a08569a83127f76060a9`; `tests/test_run607_cross_body_geometry.py` `ee825e0ecead20b3939ba444b5273fff365681f0`; workflow `2966f6e9393b67c9b52004adee94a071d45bd5bc`; plan `0d662d5d8ccd9043d2a2114f8ddbd43b6a70ac19`.
- Private permitted Library backup (not the rejected anyone-writable Drive): `/V13-Checkpoints/2026-10-26/Run607/run607-posthoc-geometry-raw.zip`, uploaded successfully. Raw input Run606 already separately backed up under `Run606`.

## Gates, scope, next command

STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; canonical architecture/user full scope INCOMPLETE. No model weights, runtime, approvals, learning age, or registered cohorts changed. A high RSA does not establish usable B1→B2 message transport or JEPA.

Next: independently review PR602 exact source and artifact, then preregister a **fresh** length/syntax-controlled independent cohort before model calls, and/or implement source-bound B3 receiver injection as SHADOW with NO_MESSAGE/EXACT/CONTROL baselines, semantic task utility and restart checks. Native jobs must serialize with current owner. Never promote any original gate on this evidence. Exact source-only test command from `v13/code`: `PYTHONPATH=.:scripts python -m unittest -v tests.test_run607_cross_body_geometry`. Exact offline replay: `PYTHONPATH=.:scripts python scripts/run607_cross_body_geometry.py --artifact <unpacked original Run606 artifact> --out <report.json>`.

No local commit alone is counted as backup; verified GitHub code and private Library raw are durable. Any failed attempts and original negative findings remain preserved.
