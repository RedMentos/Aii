# Perception handoff – 2026-11-11 15:00 Europe/Berlin

Owner: research-perception. Base: research-perception/audio-timed-consumer-20261111-1400 (PR #1776).

## Change
A5 acoustic segments and RAW EAR original frames are now checked for matching frame counts and matching timestamp, RMS, pitch, voiced and non-speech fields before B1/B2/JEF acoustic shadow views are constructed. A nested RAW EAR native verification claim is also rejected. Adds a negative regression for modified RMS, shortened RAW EAR frames and forged nested Android capture authority.

## Evidence / gates
GitHub commit verification only; tests NOT EXECUTED in this run. Required check from repository root:
`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_audio_views.py' -v`
Then run full suite and restart integration test on the merged branch. No Android microphone permission or hardware measurement, no native inference, no learning/ASR/voice authority. A3 projector and productive B/C runtime wiring remain OPEN. Preserve Age-0/STEP2/B3 gates. This does not prove cryptographic authenticity of a caller-provided packet: real source authenticity must be enforced by the store/OS bridge, not a Python dict check.

## Next
Verify the regression in CI, test persisted A5 after Store reopen, connect to actual B/C contracts and implement authorized Android PCM ingress under Core/QA companion permission checks. Keep Android 13 Redmi Note 10 Pro primary and native performance UNVERIFIED.
