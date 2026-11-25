# Research & Perception — current-base A4 / RAW EAR rebase (2026-11-24, run 16)

## Why the rebase was required

PR #2433 had accumulated a divergent history: its head was 43 commits ahead and 82 behind current gpt6 HEAD 8d93236. Its focused A4/RAW EAR jobs had passed on the old head, but staged/integrated checks failed because RECORD_ONLY controller guard accepted only the previous attention.py bytes. The current gpt6 branch changed only unrelated M1/World-JEPA/docs paths since the shared base, so the 14 Perception code/test/workflow files were transplanted onto a new branch directly from 8d93236. Old stale V14 ledger/Next Action files were deliberately not copied.

## Runtime scope transplanted

- Source-bound A4 AttentionRequest/AttentionResponse and outcome receipts retain SourceRef/provenance and route the bounded outcome to N10 attention_policy under the existing SHADOW/RECORD_ONLY gate.
- RAW EAR speaker-change evidence uses a pre-batch history snapshot, excludes non-voiced frames from speaker history, bounds process-local embeddings and avoids identity labels/vector persistence.
- Timed audio cues preserve prosody, voice onset/offset and non-speech/impulsive evidence separately from optional teacher-ear transcript provenance.
- Optional NumPy/FASTDIAR remains diagnostic/opt-in. Default Python path and installed models are unchanged.
- Caller-supplied PCM only. No Android AudioRecord provider or live microphone capture.

## Exact source pin

The current transplanted attention.py file SHA-256 is 58e68ce790c8754a4b5362e3e26f3ffbbdfe3455db99534ea518d1f58c5c280e. The RECORD_ONLY guard now adds this exact value while preserving the previous accepted pin 0d3c0d00492d809c818874cf83ddd723867e77cfc5c50236dac18eddc8422739. No wildcard, bypass or relaxed hash check.

## Current PR and base

- Current-base PR: https://github.com/RedMentos/Aii/pull/2472 (DRAFT).
- Branch: research-perception/v14-a4-audio-source-outcomes-current-20261124-run16.
- Base: gpt6/v13-private-remote-bridge-20261111 at 8d93236c753f0194224c19edc7411d8d7082b1d6.
- Guard pin commit: 35ba3fc0aad39bcc79193bb6b0311c354b567b07.
- Old #2433 remains open temporarily as the source branch; do not merge it. Close it as superseded only after #2472's exact CI is green and review is complete.

## Tests and device boundary

- Full local Aii pytest: BLOCKED / NOT_RUN; no checkout mounted and GitHub DNS unavailable.
- Prior #2433 focused passes are historical only; they are not acceptance for #2472.
- Exact current-base Python 3.13/3.14, A4, FASTDIAR, RAW EAR, consent-revocation, privacy, controller guard, runtime deployment and staged/integrated workflows are pending for #2472.
- TERMUX/REDMI: REDMI_UNVERIFIED. No microphone/provider test or handset action was performed.
- Latest available private V13OBS #115 snapshot (2026-11-24 09:28:11 UTC) predates this work: auto-update enabled, Runtime/Dashboard UP_TO_DATE at 8d93236; AI STOPPED_BY_USER/model STOPPED; B1/B2 TIME_BUDGET 53.2/54.2 s and zero valid offers. It does not prove either PR is installed. No UPDATE_REQUEST, CHAT_SEND, shell, restart, model/weight/permission change or user-data mutation.

## Next

1. Wait for exact current-base CI; fix any source-pin failures without weakening the guard.
2. After #2472 is green and independently reviewed, close #2433 as superseded and integrate only #2472.
3. Keep microphone capture OFF until QA's signed Android companion verifier, lifecycle, revocation and zeroization chain is integrated and tested.
4. Keep A4 outcomes in SHADOW; no neural weight update, learned speaker identity or native latent bridge is claimed.

User action: none required.