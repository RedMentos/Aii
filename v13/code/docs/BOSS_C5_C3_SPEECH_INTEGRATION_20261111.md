# Boss 2026-11-11 11:45 CET — C3 speech intent wired into Android simulated goal

Base: #1763 commit bf5881dd488313f96b0dfa1bd3add966b96c7916. Imported exact `v13/code/v13/speech_intent.py` and its original tests from Core #1765 commit 108d35aa007b95cef8258ef5b9d3c0abf57b960f. No changes to Core/JEPA/Research branches.

## Newly executable vertical slice
`run_integrated_goal(home)` now performs existing C5 typed OFF→SHADOW intent, fake Android Notes action, SQLite action-outcome, JEPA replay training + persisted restart readback, **then creates a C3 SpeechIntent sourced to that same synthetic goal**. The default C3 renderer remains OFF, with no native speech output. The existing JEF controller is still not autonomously planning these actions. This is a useful cross-organ API wiring step, not an actual phone voice assistant.

New `tests/test_c5_goal_c3_speech_e2e.py`, upstream C3 speech unit tests, and CI workflow `.github/workflows/v13-boss-c5-c3-speech-e2e.yml`. Verify CI on exact PR head before declaring PASS. Original Core #1765 must remain owner of speech queue; Boss changes only orchestration in own integration branch.

## Completion ledger: CODE / WIRED / SYNTHETIC / ANDROID / ACTIVE

| Organ/capability | CODE | WIRED | SYNTHETIC | ANDROID | ACTIVE | Next verified outcome |
|---|---|---|---|---|---|---|
| A0–A5 perception, multimodal | partial | A5→B staged | partial | NO | NO | Perception #1764 PCM features → bounded A5 acoustic source packet with real provenance |
| B1/B2 and B3 | partial | exact/source staged | partial | NO | frozen inference only | Core: actual B1/B2 float target adapter consumer and old-retention check |
| C2/JEF, C3 language | partial | C5 finite controller and C3 queue wired | partial | NO | limited | Core: source-grounded JEF plan → typed capability and verified action-outcome |
| T8 world memory | partial | SQLite simulated outcome | partial | NO | synthetic | JEPA: #1766 committed SQLite→numeric replay, target cross-organ optimizer |
| WorldJEPA/EMA | partial | simulated goal→replay checkpoint | partial | NO | shadow | JEPA: real target-organ learning delta and restart consumption |
| ANDROID_BACKGROUND_CONTROL | contract | fake executor | yes | NO | OFF | Core: isolated companion + permissioned intent broker |
| ANDROID_UI_CONTROL | contract | fake world | yes | NO | OFF | QA: real permission/lifecycle/revoke/stop Android instrumentation |
| VOICE_AUDIO | speech queue and PCM features separately | C3 queue after goal | yes, no audio | NO | renderer OFF | Research: timestamped RAW EAR → C3 input; Core: separately permissioned renderer |
| SELF_OPTIMIZATION | AG8 proposals, mini-head | partial | partial | NO | no live edits | JEPA/Core: numeric B1/B2/C3 updates, optimizer checkpoint, rollback |
| BEHAVIOR_JUDGE | 10-feature trainable head | synthetic Android path | yes | NO | advisory only | QA: verified intent feature input and OS-independent sandbox tests |
| REMOTE_MAINTENANCE | signed staging candidate #1756 | no live apply | partial | NO | OFF | Boss: local approval and rollback only after trusted companion |
| TECHNICAL_OS_SANDBOX | Python/broker contracts | simulation only | partial | NO | OFF | Core/QA: independent Android OS identity, egress and storage enforcement |

## Priority and conflict review
Five active roles only. Boss owns integration and completion ledger. Core owns Android background/API broker, B1/B2/JEF and C3 renderer; JEPA owns #1766 trusted SQLite replay/retention; QA owns Android device lifecycle/permission and falsified signal attacks; Research owns PCM RAW EAR and A5. Do not modify another agent's PR. No real Redmi proof or CPU/RAM measurements, no AGI claim, no native audio, no native Android action. Android remains the primary product target. All Canon v10.16.1 organs and voice G10C/G10D remain open until independently verified.
