# A5 admission adversarial regression handoff — 2026-11-14

Owner: Forschung & Perception. P0: issue #1904 documents native C3 prefill timeout and absent B1/B2 offers. The release branch ALREADY contains `v13/percept_admission.py` and its nine original tests. This PR does not duplicate or replace those existing contracts.

Added `tests/test_percept_admission_adversarial.py` with six extra synthetic regression cases: denied consent, provisional evidence, multibyte budget, priority order, exact budget boundary and oversized input rejection.

Run from `v13/code`: `PYTHONPATH=. python -m unittest discover -s tests -p 'test_percept_admission*.py'`.

**Evidence status:** Source inspection complete; CI execution pending. This does NOT fix native C3 prefill, integrate A5 into C4, validate Android, prove A3 learning, or enable microphone/screen. A3 trained projector UNAVAILABLE, RAW EAR and voice effector OPEN, Redmi native result UNVERIFIED for this change. No private data or phone commands.

Boss: low-risk additive tests only; release queue can evaluate exact PR head. Next higher-risk task: explicit runtime A5→C4/C3 admission, exact tokenizer counts and real Redmi first-token measurement with independent review.
