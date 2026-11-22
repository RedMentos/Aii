# Research/Perception handoff — libfvad comparison CLI regression

Date: 2026-11-22  
Base: Boss RAW EAR integration candidate `d47e80a7c844ffeaa022a71edb92bec76deb70f8` (PR #2327 branch; exact staged/integrated CI was green at the last read)  
Branch: `research-perception/v14-libfvad-cli-smoke-20261122`

## Change

- `v14/experiments/raw_ear_vad_compare.py`: imports `os`, which its libfvad CLI branch already uses for `V14_LIBFVAD_VERSION`.
- `v14/experiments/test_raw_ear_vad_compare.py`: adds an end-to-end CLI smoke using the workflow-built, pinned libfvad shared library, a temporary synthetic mono PCM16 WAV and local speech interval annotations. It checks that the command emits the exact backend revision.
- `v14/V14_RESEARCH_LEDGER.md`: adds R-079, including upstream revision/license and explicit evidence limits.

## Verification

- Exact PR #2327 parent CI (before this follow-up): staged context/integrated regression PASS; audio/arithmetic runtime PASS; RAW EAR prosody-to-attention PASS; RAW EAR vs WebRTC/libfvad comparison PASS; privacy scan PASS; consent-revocation QA PASS; Python 3.13/3.14 jobs PASS. This evidence belongs to #2327's exact head, not this follow-up.
- Local full checkout/test run: BLOCKED. `git ls-remote https://github.com/RedMentos/Aii.git` failed because `github.com` DNS could not be resolved in the execution container. No full Aii checkout was available.
- New exact-head CI: pending PR creation; do not claim it passed yet.
- Android ARM64, Termux, AudioRecord and Redmi: NOT_RUN / REDMI_UNVERIFIED.

## Scope boundary

This repairs the offline comparison CLI only. It does not add libfvad to production, replace RAW EAR, install a dependency/model, capture microphone audio, update weights or change permissions. The fixture is synthetic; real speech-corpus quality remains unmeasured.

## Next step

Run the exact-head comparison workflow after PR creation. If green, retain libfvad as a research-only comparator and prioritize the Perception #2312 signed one-shot consumer once QA's closed companion parent stack has a current release-compatible replacement. No user action is needed.
