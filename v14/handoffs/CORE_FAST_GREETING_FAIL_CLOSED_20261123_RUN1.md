# Core & Harness — greeting fastpath fail-closed correction

Date: 2026-11-23
Role: Core & Harness
Branch: `core/v14-fast-greeting-staged-overlay-20261123`
PR: #2445
Exact code/test head after this checkpoint: `1187a609f46e41f91a16bb481e816865417fdb1b`
PR base at readback: `gpt6/v13-private-remote-bridge-20261111` at `fb563d771fe2d493c4ec25abe94280981d24ef5c`
Current release-development branch read at session start: `8d93236c753f0194224c19edc7411d8d7082b1d6`

## Change

- `fast_greeting.is_text_only_event()` now accepts only a text SourceRef with `_audio_window` absent or explicitly `None`.
- Any non-null audio-window value is rejected, including malformed strings, bytes, lists, numbers, booleans and dictionaries. The previous `not isinstance(value, dict)` test incorrectly treated malformed non-dict values as proof that no audio window existed.
- Exact greeting matching, mixed-request fallthrough, user-policy precedence and the source-only/no-learning behavior are unchanged.
- No model, weight, permission, Android setting or user data was changed.

## Verification

- LOCAL_LINUX / CPython 3.13.5: `py_compile v13/fast_greeting.py` PASS in an isolated checkout-free harness.
- LOCAL_LINUX / CPython 3.13.5: isolated assertions PASS for exact greeting matching, mixed-request fallthrough, user-policy precedence, text-only admission, explicit `None`, and six malformed/non-null audio-window shapes.
- Full Aii checkout / repository pytest: BLOCKED / NOT_RUN; no checkout is mounted and `git ls-remote` could not resolve `github.com`.
- Exact PR-head GitHub Actions run `45283293852`: `startup_failure`; no jobs were created. This is not a test pass and does not establish a code regression.
- Redmi/Termux: REDMI_UNVERIFIED. No device access, capture, probe, update request or runtime deployment occurred.
- PR remains DRAFT / NOT_RELEASED.

## Integration boundary and next action

The PR base is stale relative to the current release-development HEAD. Do not merge it directly or claim the fastpath is installed. Boss/Integrator should recompose this staged overlay after the current fair B1/B2 and Boss source-pin chain is reconciled, then obtain exact-head staged/integrated CI and independent review. Only after that may the normal verified updater path be considered; no manual Termux command or user action is currently required.

This fix closes only the malformed audio-metadata admission edge. It does not prove Android audio capture, native model performance, B1/B2 use, JEPA/latent coupling or whole-system completion.
