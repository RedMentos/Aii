# Termux: no-input operation and runtime recovery

The existing Runtime already schedules sleep and authority review without new
chat input. Its default budget, however, stops after twelve background jobs
until a genuine user turn arrives. An open dashboard alone is not a running
Runtime. Repeated startup greetings were replayed saved messages, not evidence
of new autonomous model calls.

The reviewed recovery composes with the existing integrated builder. It leaves
frozen source files unchanged and stages a SHA-bound runtime copy. The explicit
local activation switches only `~/v13/bin/v13` to this copy. It first requires
V13 to be stopped, validates every staged file and saves private launcher,
settings and SQLite snapshots under `~/v13/recovery-state/`. Models are not
redownloaded. Rollback restores the launcher only, preserving later data.

## Install on the phone

First send `:shutdown` in the V13 chat and wait for exit. In Termux:

```bash
pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/RedMentos/Aii/gpt6/v13-private-remote-bridge-20261111/v13/code/scripts/termux_runtime_recovery.sh -o "$HOME/v13-runtime-recovery.sh" && bash "$HOME/v13-runtime-recovery.sh"
```

Then start the chat from the existing dashboard. Send separately:

```text
:idle on
:idle status
```

`worker_alive: true` and `enabled: true` show that the Runtime worker and new
policy are active. The policy allows at most twelve existing background jobs
per rolling hour, preserving a smaller `:pause budget`, pauses, resource
limits, quiet hours and Age restrictions. It renews without manufacturing a
user turn. `:idle off` restores the original per-input budget. Status includes
the actual last small world-model fit, sample count, sleep cycles, quota and
blocked reason. Waiting for more data is reported, not relabelled as learning.

This command does not change the learning mode or activate new model weights.
`:learning` now reports the current mode even during a job. Existing SHADOW
work can be enabled separately with `:learning shadow`; it does not create a
native training port for B1/B2. No large GGUF weight update, full-brain learning
or general utility claim follows from a running scheduler. Android may still
stop Termux; target-phone background lifetime must be checked separately.

## B1 diagnosis

The native probe calls each body twice: a 48-token smoke generation under
`deadline_seconds`, then a structured offer under `observer_seconds` (35s in
the reported configuration). The old report discarded successful smoke
results if the offer timed out. The recovery preserves separate phase results,
budgets and runner metrics while keeping overall failure visible.

For a bounded diagnostic, send these separately and await completion:

```text
:budget observer_seconds 90
:probe
```

This changes the offer budget, not the schema or token count. It is not proof
that B1 passes on the phone. Foreground chat also has a shared observer window
of 45% of `deadline_seconds`; increasing only the observer knob does not remove
that separate limit. Do not run overlapping probes. `:cancel` stops a job.

## Validation scope

Tests use the real coordinator, SQLite persistence and existing scheduled
jobs, accelerated clocks, and disposable model-process fixtures. No private
phone log is committed. No native model or actual Redmi lifetime test was run
by the repair process. The original negative gates remain unchanged.
