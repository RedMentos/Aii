# Run13O — independent exact-original Run13N full-suite closure (2026-10-30)

Review-only child of Run13N PR #1305, parent `117bfdcd1a722c9ca883d3ad76971bb0c3453522`. Original workflow Actions `41088780210` terminal **FAILURE**; no waiver, no code/Canon/model/seed/scorer changes.

## Original bytes and independent replay

Downloaded original GitHub artifact `12994050614` from the run and historical G14 artifact `12989104302` (Actions `41080416868`). Verified both full ZIP SHA256, unique names, ZIP CRC, complete inner `SHA256SUMS`, exact `HEAD.txt`, stage exits and unmodified `FULL_RAW.log`. Independent Python stdlib replay uses the G15 identity regex `^(ERROR|FAIL): (.+)$` with a multiset (not a deduplicated set); no test filtering, rewriting, xfail, skipped-error waiver or scorer change.

| Evidence | G14 historical | Run13N current chain |
| --- | --- | --- |
| HEAD | `4c789ae85758ca71bf86dd5067ab697913071a51` | `d883e8e9cc7b22966f862fad953939f112f8f6b9` |
| ZIP SHA256 | `77906cc480e18a7695b833896730dded1e5f881278966259a7725440d766c27f` | `4d4132478876762d14fd86d0acbd3632cdc4408988c81c363ceb8673f80c68fd` |
| ZIP bytes | 17130 | 16573 |
| CRC / inner SHA256 | PASS / 32 of 32 | PASS / 30 of 30 |
| Original unfiltered tests | 3987 | 4027 |
| Original final result | 4 failures, 65 errors, 15 skipped | 4 failures, 65 errors, 15 skipped |
| Full suite exit | 1 RED | 1 RED |
| Nested FAIL/ERROR identity entries | 120 | 120 |
| Unique identities | 86 | 86 |
| Added / removed identities | baseline | **0 / 0** |

All non-FULL stage exits were 0, including Canon, venv, dependencies, Torch/Transformers/PEFT import, compile, privacy and diff. Current run original unfiltered wall time 400.404 seconds. The historical source-handoff frozen-candidate refusal remains RED; no change to its original pins is authorized by this result.

**Verdict:** `HISTORICAL_RED_SAME_IDENTITIES` and `software_suite_gate_pass=false`. The 40 extra tests add no new FAIL/ERROR identity in this comparison. This is *not* a full-suite pass, not proof of absence of other functional defects, and not native/Redmi evidence.

## Durable backup and next action

Original ZIPs stored privately at `/V13-Checkpoints/2026-10-30/Run13N-Unfiltered-Independent/` as `run13n-original-41088780210.zip` and `g14-original-41080416868.zip`. Both materialized back and byte-compared with downloaded originals, **byte-identical**. Public GitHub contains only non-sensitive review metadata, no raw private data.

Next: prioritize a substantive new cross-organ source/answer utility package with independent held-out tests, not another unmotivated full-suite rerun. Keep historical G14/G15/Run13N RED and Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured and whole-system incomplete. No automatic delivery/learning/tool authority.