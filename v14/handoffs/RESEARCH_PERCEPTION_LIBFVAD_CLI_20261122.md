# Research/Perception handoff — libfvad comparison CLI regression

Date: 2026-11-22  
Base: release-development `9097d634398817743ba6d09f233be523322db53c` (after merged Boss PR #2327)  
Branch: `research-perception/v14-libfvad-cli-smoke-20261122-run2`

## Change

- `v14/experiments/raw_ear_vad_compare.py`: imports `os`, which its libfvad CLI branch already uses.
- `v14/experiments/test_raw_ear_vad_compare.py`: adds an end-to-end CLI smoke using the workflow-built pinned libfvad shared library, a temporary synthetic mono PCM16 WAV and local speech interval annotations. It checks the command's exit code and exact backend revision.
- `v14/V14_RESEARCH_LEDGER.md`: adds R-079, including upstream revision/license and explicit evidence limits.

## Verification

- The parent integration #2327 is merged at `9097d634398817743ba6d09f233be523322db53c`; candidate CI was 27 SUCCESS / 1 expected SKIPPED. The first post-merge push-CI read had 39 checks queued/in progress and 0 failures; no phone installation is inferred.
- The previous stacked follow-up #2329 passed comparator CI run `45007987039` on code/workflow head `adcf619ea36b00daa7f68c81d4da6aa327f348cc`. This new branch is rebased onto the merged release head, so it requires its own exact-head CI before acceptance.
- Full local Aii checkout/test run: BLOCKED. `git ls-remote https://github.com/RedMentos/Aii.git` failed because GitHub DNS could not be resolved in the execution container.
- Android ARM64, Termux, AudioRecord and Redmi: NOT_RUN / REDMI_UNVERIFIED.

## Scope boundary

This repairs the offline comparison CLI only. It does not add libfvad to production, replace RAW EAR, install a dependency/model, capture microphone audio, update weights or change permissions. The fixture is synthetic; real speech-corpus quality remains unmeasured.

## Next step

Run exact-head comparator CI on the rebased PR. If green, keep libfvad research-only and continue with the Perception #2312 signed one-shot consumer only after QA supplies a current release-compatible companion verifier/provider stack. No user action is needed.
