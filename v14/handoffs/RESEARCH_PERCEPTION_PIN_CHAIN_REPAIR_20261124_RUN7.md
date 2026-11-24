# Perception/Core recovery pin-chain repair — 2026-11-24 run 7

**Stacked on:** PR #2472, branch `research-perception/v14-a4-audio-source-outcomes-current-20261124-run16`, exact base HEAD `cfb0beab5050acba6d01639d27c50d07475f0fa2`.
**Repair branch:** `research-perception/v14-a4-recovery-pin-chain-20261124-run7`.
**Scope:** source-integrity metadata only; no runtime capability, permission, model, weight, data, or deployment behavior changed.

## Reproduced failure

Exact PR #2472 head `cfb0beab5050acba6d01639d27c50d07475f0fa2` produced three related failures:
- controller guard workflow run 45489869257: `termux_runtime_recovery_candidate_20261112.py` rejected `record_only_controller_guard_20261116.py`;
- staged/integrated run 45489868951: same rejection through the pinned stage builder;
- Core same-turn B1/B2/C4/C3 run 45489869343 on Python 3.13 and 3.14: same composed-stage failure before downstream assertions.

The exact guard bytes on the PR branch have SHA-256 `9c901c4e5e3d3fd17c113a8e9458bcb32a30646593483202f1f472763435fa96`, while the recovery builder expected `86ad7838d15eb9a038fec629c340936edde78d65d921507e10cec29fed74b9d9`. The fix updates the exact dependent pins; it does not weaken or bypass verification.

## Pin chain updated

- `v13/code/scripts/termux_runtime_recovery_candidate_20261112.py`: guard SHA-256 now `9c901c4e5e3d3fd17c113a8e9458bcb32a30646593483202f1f472763435fa96`.
- Its Git blob SHA-1 changed from `546a811b998f7ddceff3a5334276bafb67b9afb8` to `9020bde1545779a72cc405ffc42a17f019417252`.
- `v13/code/scripts/termux_runtime_recovery_candidate_20261121.py`: BASE_BUILDER_BLOB_SHA1 updated to `9020bde1545779a72cc405ffc42a17f019417252`; new wrapper SHA-256 `9c32c91d04dc4b1be6647f58e20c8df144609ccbd1c554772d2dc28899ba6d93`.
- `v13/code/scripts/stage_integrated_candidate.py`: BUILDER_SHA updated from `a6af1c476c2bec51692e5c00f8995c7d592239f5b78b989fcf799edb6c9f75c9` to `9c32c91d04dc4b1be6647f58e20c8df144609ccbd1c554772d2dc28899ba6d93`.

All three complete files were read back from GitHub and matched the intended content hashes. No force-push.

## Tests / proof boundary

- Existing exact-head failures are confirmed from workflow logs; they remain failures.
- Local full Aii checkout/pytest: NOT_RUN/BLOCKED (no checkout mounted; earlier full-suite attempts report GitHub DNS failure).
- New exact-head CI: pending.
- Redmi/Termux: REDMI_UNVERIFIED; no private relay, microphone, model, weight, permission, updater, or device action was used.
- No trained A4 policy utility or native audio capture is claimed. Audio remains caller-supplied PCM; A4 outcomes remain SHADOW/RECORD_ONLY.

## Next

Run exact controller-guard, staged/integrated, Python 3.13/3.14 Core same-turn and privacy checks on this combined tree. Fix any subsequent source-pin or semantic failures without weakening hash verification; then request Core/Boss review and rebase Perception PR #2472 if its integration base advances.
