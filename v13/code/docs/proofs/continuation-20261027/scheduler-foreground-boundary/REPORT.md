# G13 foreground-kind action boundary — independent RED/GREEN review 2026-10-27

**Owner:** GPT-6 continuation, review-only child of PR #738 exact `a76badb3b19ed9ae332174acd2089fdd5e153c26`. Preregistration `34d817510b5fd41aa79e2d0d2229a765390fc261` predates tests and patch.

## Defect and contract

`_allowed` immediately permitted all `FOREGROUND` kinds, including under CRITICAL resources, non-idle execution, quiet hours and burn-out. `_post` previously accepted executable background actions on those kinds, so SYSTEM `TOOL_EVENT(action='sleep_full')` or `RESOURCE_CHANGE(action='growth_practice')` could bypass background guards. SYSTEM `USER_INPUT` also impersonated the foreground priority class. The patch restricts foreground kinds to `action=None|'notice'` and `USER_INPUT` to `origin='USER'`, rejecting invalid events before state mutation. Legitimate SYSTEM `RESOURCE_CHANGE`, TOOL_EVENT notice and USER-origin input signals retain priority/preemption. Actual user turns and user TIMER sleep requests remain unchanged.

## Preserved exact-source evidence

Initial RED test-only commit `32f679b9c1cae6473b198cf20c213f28dac67353` had Actions `40532662414` **CANCELLED before jobs** because a newer queued run replaced it within GitHub Actions' pending concurrency slot. Preserve this failed attempt, not a software FAIL. The exact RED source was rerun on separate immutable proof branch `codex/automation11h-red-evidence-20261027` at `ce307f1f8790f6425f59e00e570076a8922c3544`, unchanged scheduler blob `e1704de76e77947849c5b0a9b2f174ce47f1a29e`. Actions `40532785137`: **12 tests, 2 expected FAIL** (both missing ValueError guards), 10 PASS; INSTALL/COMPILE/PRIVACY/DIFF exits 0, UNIT exit 1. Artifact `12745224872`, ZIP SHA256 `161b5dd317dd4fc92c74281e3ad0be2c1d06e9ed71a30a420bcae7b9e4485daf`, CRC/HEAD/exits verified, privately backed up byte-identically at `/V13-Checkpoints/2026-10-27/Automation11H-Scheduler-Foreground/RED-40532785137.zip`.

GREEN source `0fa5b73a18e4851bf1d7cdeb5c1ee2dc0a2d2942`, scheduler blob `4054f2a5dbc2e441a3acc87eea423b70dd9cc760`. Focused Actions `40532699100`: **12/12 PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF all exit 0; artifact `12746867808`, ZIP SHA256 `86bb1bf9da16f2e6baf7a919512588f8c3e475ed4e968bf254308b7b361ee68e`. CRC/HEAD/source blob/exits verified, private Library backup byte-identical at `/V13-Checkpoints/2026-10-27/Automation11H-Scheduler-Foreground/GREEN-40532699100.zip`.

Full software suite at exact source/workflow head `f9731f7cdf79bb59ae01093a3c6c682b63757231`, Actions `40533054552`: **1906 tests OK (1 skipped)** in 243.015 s, INSTALL/UNIT/COMPILE/PRIVACY/DIFF all exit 0. Artifact `12746768324`, ZIP SHA256 `3f6d20890fb934044b5f1738c25055d5261bb3e9419fd9196d3b5767fa46e561`; CRC, exact HEAD, scheduler blob and exits verified; private Library backup re-downloaded byte-identical at `/V13-Checkpoints/2026-10-27/Automation11H-Scheduler-Foreground/FULL-40533054552.zip`. This is software-only evidence, not native or Redmi proof.

## Gates and next

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority 0; Redmi unmeasured; V13 incomplete. No native/model or production-main changes. Independent review required; no automatic merge. **Next:** independently review exact full-suite-passing diff, then switch to an independent substantive blueprint package (e.g. World/Self or learning proof) rather than repeatedly hardening scheduler helpers. Preserve all existing owner branches and frozen registered cohorts.
