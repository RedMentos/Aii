# Perception A3 numeric learning prototype — 2026-11-12 00:56 CET

Owner: Research & Perception. Parent: PR #1806; no changes to Core/JEPA-owned files.

## Verified prior CI
GitHub Actions run 43116261314 for #1806 head 73f5b5d1b58c29ed882303fb8fa6236d437ee295 completed SUCCESS, including the synthetic acoustic and SQLite-restart test step. This is host CI only.

## Delivered
- v13/code/v13/a3_online_projector.py: small bounded float-master linear teacher/student projector with real numeric SGD weight changes, finite-input validation, gradient clipping, trusted=True training gate, atomic JSON checkpoint and reload.
- tests/test_a3_online_projector.py: holdout improvement, denied untrusted update, numerical weight change, restart equality and invalid-input rejection.
- Local standalone equivalent test exercised on Linux Python: 2 tests PASS. Repository-specific imports and complete CI on this branch are NOT YET verified.

## Limits and integration
This is an A3 *numeric learning kernel*, not the full A2 frozen teacher → A3 student modality adapter, not a JEPA predictor, not the B/C runtime, and not Android hardware proof. trusted=True is an experiment caller flag, NOT a cryptographic source receipt or Android permission. No action authority. Real teacher provenance, A5 PerceptPacket integration, durable master/quantized export, replay/retention and cross-organ learning remain OPEN.

## Next
1. Run tests.test_a3_online_projector in checkout CI and resolve failures.
2. Bind teacher target to verified A2 source refs and versioned training approval outside model control.
3. Connect A3 embeddings to A5/B1/B2/JEF and perform retention/restart tests.
4. Android Termux measurements and microphone/vision/UI permissions remain UNVERIFIED/OFF.
