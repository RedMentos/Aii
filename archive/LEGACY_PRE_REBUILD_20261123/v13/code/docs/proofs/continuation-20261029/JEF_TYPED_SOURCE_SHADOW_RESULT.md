# JEF typed two-source Store SourceRef SHADOW — software result (2026-10-29)

Owner: GPT-6 isolated PR #1081, child of independently verified PR #1080. Prospective prereg `4feee2b612072340c96b974aa05b706e3313e451` preceded implementation and tests. No model calls, training, native execution, or production merge.

## Implemented

`v13/jef_typed_source_shadow.py` reads complete immutable current/policy/option-sheet SourceRefs through actual `Store.read_source`, checks project and domain identity, exact typed fields/units, two distinct source records, flags, bounded nonnegative integers and the original source hashes. It deterministically proposes the qualifying A/B/NONE action or UNKNOWN for missing, foreign, duplicated, deleted, partial, tampered, malformed or injected sources. No source text becomes an instruction; no Store mutation during reads. Source integrity is **not** F1/F5 human authorization: every result remains `SHADOW_NO_AUTHORITY` and cannot affect the user-visible answer.

## Measured software-only result

[Actions 40864073188](https://github.com/RedMentos/Aii/actions/runs/40864073188), exact head `0dc92b50f349e7d13a1a33d32fa2bda213435400`, **9/9 real-Store adversarial tests PASS**. The 36 P2X **calibration** IDs yielded **36/36 correct complete-source A/B/NONE** and **144/144 UNKNOWN** for four incomplete/foreign source arms. No frozen 72 validation IDs or P0X holdout were used. Additional real-Store tests passed persisted restart/replay, deleted SourceRef, modified blob, wrong hash, partial span, duplicate and wrong project/domain, malformed units/flags and appended instruction injection, unchanged Store source count during decisions and no native runner calls.

Original ZIP SHA256 `5b5a4700e28278b34806b0e6b1326507d3e963e90ca29b5fc31449c2ce29875c`, CRC CLEAN, **19/19 SHA256SUMS**, **8/8 stage exits zero**, privacy CLEAN, diff PASS. Exact ZIP privately backed up and byte-verified at `/V13-Checkpoints/2026-10-29/JEF-Typed-Source/SOURCE_GREEN_40864073188_sha5b5a4700.zip`.

**Claim limit:** This is deterministic bounded grammar and source integrity on synthetic tasks, **not learned C3 source use, not F1/F5 authorized source admission, not live JEF/Context OS integration, not Redmi, not native utility**. Next: independently implement and test actual active session-bound F1/F5 Memory.candidate admission for two sources, with conflict/revocation and no bypass, then a separately approved runtime integration only if authorized.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE.
