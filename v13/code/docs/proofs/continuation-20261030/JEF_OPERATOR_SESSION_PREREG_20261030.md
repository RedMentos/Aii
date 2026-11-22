# JEF operator current-chat boundary — preregistration 2026-10-30

Base: PR #1166, commit `59943da7b0d835988637f095f5ec671fdf4a6985`. Review-only child; no production merge. File ownership for this package: `v13/code/v13/jefbridge.py`, new `test_jef_operator_session_20261030.py`, new CI workflow and this evidence note. No other owners' files or registered cohorts are changed.

## Problem and invariant
`:jef last` currently reads the globally latest `JEFBridgeTurn`, including another session's payload. `:jef outcome <event> <score>` accepts foreign event IDs and can alter global JEF shadow utility weights. These explicit operator commands must operate on the current chat only. The automatic internal `on_rating` hook is deliberately out of scope; it is not an operator command.

## Predeclared verification
- In one real isolated Runtime/Store with two sessions, make a JEF turn in the current session and then a newer foreign session; `:jef last` must return only the current session turn.
- With only a foreign turn, `:jef last` must return JSON null, not a foreign payload.
- `:jef outcome` on foreign or unknown event must raise before calling `JEFBridge.outcome` or changing the stored learning state.
- A current-session selected-offer turn must accept a finite explicit rating in [0,1], increment the expected shadow update once, and remain Age0 RECORD_ONLY.
- Nonfinite, out-of-range or malformed operator ratings must fail without state mutation. No model calls.
- Run existing `tests.test_jefbridge` plus the new test in isolated Python; hash-bind raw CI, Canon SHA, privacy and diff checks.
- No STEP2/B3/LP3/Body-JEPA/World-JEPA, native JEF/C2 or Redmi gate promotion. Preserve all existing failures.

## Next after this package
Reassess whether the same-session outcome label is idempotent on duplicate operator submission. Treat duplicate learning as a separate behavioral package with its own proof; do not silently alter historical label semantics here.
