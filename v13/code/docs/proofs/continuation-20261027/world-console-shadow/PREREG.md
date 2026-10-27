# Explicit V13 console bridge for calibrated World-JEPA SHADOW — prereg 2026-10-27

Base PR #653 exact `3d39a7e0663ffbf72b804e5926822f2c9ab2ec7f`; independent review-only child, no production merge. Ownership: narrow `v13/operator.py` `:world` branch and HELP entry, new `tests/test_world_console_shadow.py`, isolated workflow/proofs. Existing world-state command, Age-0 permissions, live models, Context OS, JEF/C2/C3/B1/B2, B3 and JEPA training untouched. Do not rewrite any canonical organ or registered cohort.

## Functional gap
A digest-bound v2 SlotWorldJEPA checkpoint can be trained and probed offline, but the V13 operator currently exposes only `:world` status; the isolated SHADOW probe is not reachable through the actual console. Add an **explicit local TTY-only read-only** subcommand, not an automatic live observer:
```
:world shadow <checkpoint.npz> <64-hex-SHA256> <expected-provenance.json> <observation.json>
```
The result is JSON from existing `world_jepa_shadow_probe.probe_checkpoint` and contains `authority=0`, `SHADOW_ONLY`, no executed action or learning. Input files are read only. The console has **no output path** for this command (no checkpoint overwrite, fact write or mutation). Existing `:world` without arguments still reports world-state exactly as before.

## Acceptance before source
1. Non-operator origins are rejected by the existing `Operator.run` origin gate; no model/tool-generated text can invoke this command. Wrong argument count, invalid SHA/provenance/checkpoint/input fail closed.
2. A calibrated v2 checkpoint plus explicit local observation yields the same deterministic JSON as direct read-only `probe_checkpoint`, including optional caller-supplied after-state marked unverified. No new model training, downloads, tools, external communications, Age or fact writes.
3. Original `:world` status is unchanged. Unknown `:world` subcommands fail rather than silently ignoring arguments. `:help` documents exact syntax and SHADOW limitations.
4. Unit tests include actual small NumPy fit/calibrate/save/reload, invalid input, origin denial and no writes to checkpoint/input/provenance; existing adjacent World-JEPA and operator regressions remain passing.
5. Preregistered RED before source, then GREEN Linux CI with raw logs/source hashes/privacy scan, private byte backup. No registered Z12c utility or B3/STEP2/Body-JEPA/Redmi promotion. This is an **explicit console bridge**, not a live turn observer or complete V13.

Model dependency only existing NumPy 2.3.5; no new paid/native provision.
