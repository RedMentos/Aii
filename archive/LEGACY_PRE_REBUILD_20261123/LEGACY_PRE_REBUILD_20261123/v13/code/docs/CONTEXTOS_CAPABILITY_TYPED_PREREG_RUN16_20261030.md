# Run16 preregistration — ContextOS G6B capability/digest typed admission (2026-10-30)

Parent: Run15 review branch `codex/v13-run15-fullsuite-pin-recovery-20261030` exact `a35813a2cbf051d9bed004bca5be06fb8c81a079`; review-only, no production merge. Owner: GPT-6 scheduled continuation. Scope exclusively `v13/code/v13/context_os.py`, new test `v13/code/tests/test_contextos_capability_typed_run16.py`, isolated workflow/checkpoint. Other owners and registered cohorts untouched.

## Hypothesis and counterexamples

G6B `consecutive_user` must be a genuine boolean, not Python truthiness. Currently `set_capability(..., "false")` records True; a persisted `{"value":"false"}` is treated as True by both `capability()` and `plan()`, enabling `stable_prefix`/append-only layout without a successful template probe or intentional typed operator choice. `set_digest("off")` similarly stores True. These are unsafe authority/capability interpretations, not proof of any native template defect.

Frozen tests before implementation:
1. Direct setter rejects `"false"`, `"off"`, `0`, `1`, `None` and arbitrary objects; state/version unchanged. Exact `True` and `False` remain supported.
2. Real SQLite injected legacy malformed persisted `capabilities[C3_LANGUAGE][consecutive_user].value` values `"false"`, `"true"`, `1`, `[]`, `None` must fail closed in both `capability()` and `plan()`; the requested stable_prefix falls back to legacy, and no append-only reentry.
3. Exact bool True survives Store restart and allows requested stable_prefix; False disables. Existing operator `:ctxos capability ... on|off` and `:ctxos probe` pass actual bool and remain compatible.
4. `set_digest` rejects non-bools including `"off"` and `0`, preserving stored value; bool True/False work.
5. Existing ContextOS/Sleep/warm and replay regression tests must remain unchanged and pass.

No model calls or native claims. Software tests on GitHub Actions Linux SQLite only. No changes to learning authority, `Age0 RECORD_ONLY`, `STEP2 UTILITY_FAIL`, `B3 NO_PROMOTION`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, or whole-system completion. Preserve RED attempts, exact Git blobs, raw CI and stage exits. Independent review after candidate. Next: substantive other-organ package after checkpoint.
