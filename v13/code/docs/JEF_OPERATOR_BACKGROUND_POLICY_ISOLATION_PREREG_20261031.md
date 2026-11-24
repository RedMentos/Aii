# JEF operator diagnostic background/sleep-policy isolation — prereg (2026-10-31)

Owner GPT-6 scheduled continuation. Independent review of PR #1413 exact `2c0ddbf22b6a92f9e0760cbf9af5f8ddd6e51ca9`; commit and remotely read back before implementation/tests. Preserve original native Run65 C3 strict 1/3, fallback 2/3 and all negative gates.

## Observed defect

The default-OFF opt-in JEF diagnostic `scripts/jef_c3_c5_c6_operator_cli.py` constructs a normal `Runtime`, which immediately starts a coordinator thread, then calls `runtime.sleep.cycle.set_policy("enabled", "off")`. `SleepCycle.set_policy` writes the persistent `SLEEP_POLICY` Store state, so even a successful **synthetic** diagnostic can silently disable a user's preexisting sleep schedule after exit. The coordinator may tick before the policy write. A diagnostic must not modify a user's durable policy or run unrelated queued turns.

## Bounded remedy

Do not change frozen `v13/runtime.py` or `v13/sleep.py`. In the isolated CLI, construct a subclass of Runtime whose coordinator worker only waits for the Runtime stop event (no queue processing, no sleep ticks). Remove the persistent `set_policy` call entirely. The diagnostic's synchronous JEF/Store/C3/DRAFT/C6 path remains unchanged. Runtime.close must wake/join the inert worker; pending turns stay durable for the normal owner. No new model/TTY/output/tool/learning authority. This does not claim full read-only Runtime initialization; the diagnostic's intentional Store staging still occurs.

## Tests and acceptance

- A real SQLite home with explicit SLEEP_POLICY enabled True and a nondefault value: compare exact policy and version before/after successful synthetic_exact diagnostic and failing synthetic_wrong diagnostic.
- Ensure no background SleepRuntime.tick and no queued turn execution while the diagnostic runs; original pending event remains pending.
- Existing regular-file, bounded input, native cleanup and six Store synthetic tests remain green. Include a fail-closed test if Runtime startup/cleanup fails.
- Independent pinned Linux software workflow, original raw artifact and hashes, privacy/diff checks. No native inference or Redmi.
- The review stays a child branch/PR of #1413, no auto-merge or production claim. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0 unchanged.
