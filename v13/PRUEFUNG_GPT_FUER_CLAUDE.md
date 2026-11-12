# 2026-11-12 — no-input scheduler and actual runtime recovery

Source parent: `0d6bd47b116f89c44c94c4d5ac6308afd604bac7`. User supplied
phone measurements and reiterated that ongoing work without input is required.
No raw phone transcript, device process identifier or private chat was committed.

Confirmed gaps and repairs in the isolated, composed runtime copy:

- Original scheduler stops after 12 background dispatches until a new accepted
  user turn. New explicit `:idle on` renews at most 12 existing jobs per rolling
  hour (or a smaller configured budget), without fabricated input. Default
  remains unchanged. Retries count; quota persists; clock rollback, corrupt
  state, pauses, resources, quiet hours, input priority and Age remain binding.
  `:idle status` is read-only and reports the worker, quota, cycles, block reason
  and actual small world-model fit/sample state. This is not large-body training.
- The B1 smoke probe used a separate 35s structured-offer deadline after its
  90s smoke call, then erased successful smoke evidence if the offer failed.
  Phase results, budgets, durations and metrics now survive failure. Overall
  failure still fails. Increasing observer_seconds is a diagnostic, not a claim
  that B1 now passes on the phone.
- Plain chat reprinted persisted assistant messages at every process start.
  It now identifies saved history without presenting it as fresh output, while
  new messages and ongoing streams still render. Bare `:learning` is a read-only
  mode query before the idle mutation guard; explicit mode changes retain it.
- The bridge installer did not switch the actual model-runtime launcher.
  `scripts/termux_runtime_recovery.sh` stages the entire pinned composed build
  and uses explicit `--activate`. The helper verifies all staged source hashes
  and syntax, requires the model runtime stopped, backs up the launcher/settings
  and SQLite privately, then atomically switches the launcher. Rollback changes
  only the launcher and preserves later messages/settings. No model download or
  learning permission is granted. Android platform path aliases are supported.

Frozen original Runtime, Store, operator, scheduler, UI and verification files
remain byte-identical. New behavior is staged by the updated existing stager;
all earlier World/Body/context/resume changes and imported scripts/native helpers are retained. The user must execute
activation and start the chat, then send `:idle on`, before this runs on the phone.
Existing false completion flags and all negative evidence remain unchanged.

Validation:

- Real coordinator/SQLite, accelerated clocks: six hourly sleep cycles and more
  than 12 completed existing jobs, zero accepted user turns/messages/native PIDs;
  enablement, sleep state and honest TOO_FEW_TRANSITIONS persisted on restart.
- Combined recovery and six existing real-stage suites: 34 passed, 9 intentional
  child-only skips, 5 subtests passed; nested idle suite separately 9 passed.
- Activation helper: 16 passed under umask 022, including SQLite snapshot,
  restart lease, Android ancestor alias, PREPARED crash recovery and rollback
  preserving new data. Node/Android/native inference was not used by these tests.
- Runtime recovery shell syntax passes. The staged context CI now includes all
  recovery suites. One external anyio/pytest deprecation warning remains local.

Phone instructions and reversible commands:
`code/docs/TERMUX_RUNTIME_RECOVERY_20261112.md`.
Android background process survival and B1 success are still unmeasured by this
repair. Large GGUF body training remains unavailable. Drive storage was already
full at the prior backup attempt; GitHub and local ZIP are the available saves.

# 2026-11-12 — Termux bootstrap / browser-button recovery review

CI follow-up: the first published owner-read run `43165385938` exposed a
test-fixture permission assumption under the runner's umask 022. The fixture
now explicitly creates its private directory with mode 0700; mobile-dashboard
and bootstrap tests pass locally under umask 022. Original bridge-security CI
`43165385950` passed. The Drive ZIP backup attempt was rejected with HTTP 403
`storageQuotaExceeded`; no Drive backup is claimed. The public-source ZIP is
retained locally and the code is saved on the GitHub work branch.

Reviewed source: PR #1794 head `26f6247f63632d7e16bb41ac17e9d9de83458dad`.
Both supplied Actions runs (`43164147674`, `43164147641`) were successful;
these are offline software checks, not proof of phone connectivity.

The existing head already fixes the mobile button URL bug: an input named
`action` shadows `HTMLFormElement.action`; the script uses
`form.getAttribute('action')` and urlencoded POST bodies. The Node regression
rejects the old expression. Real mobile Chromium clicked start, send and
shutdown against the actual local HTTP UI with a disposable echo process;
the transcript was recorded and there were no browser errors. No real model
or Redmi run was performed.

This follow-up fixes the installer: preserve explicit local STOP; refuse a
running V13 before updating; stop only matching same-home idle dashboards
before changing their source/template; briefly pause old UIs while checking
for live children, and resume them unchanged on refusal. Reject unexpected
origins/branches and dirty source; replace branch reset with fast-forward
merge. Keep ancestry when fetching updates to a shallow clone. Run freshly
loaded modules from their own source directory. Treat terminated zombie
bridge processes as stopped. No model/runtime source under `code/v13/` changed.

Validation from `v13/code`:

- `python -m pytest -q tests/test_remote_maintenance_bridge.py tests/test_termux_patch_staging.py tests/test_owner_read_bridge.py tests/test_source_updater.py tests/test_managed_console_dashboard.py tests/test_mobile_dashboard.py tests/test_termux_bootstrap.py`: **81 passed, 7 subtests passed**. One external anyio pytest deprecation warning.
- `node tests/test_mobile_dashboard_browser.js`: PASS; old `form.action` counterexample fails as intended.
- `bash -n scripts/termux_one_command.sh scripts/v13-update`: PASS.
- Ten real-bash bootstrap tests use only local Git fixtures and inert package/auth stubs. They cover STOP, active V13, wrong origin/branch, local edits/history, normal and shallow fast-forward, idle UI shutdown before fetch, and resuming a UI with a live child.
- The broader check initially exposed three stale mobile-dashboard tests omitted by the old CI. They now exercise the current managed-chat path and bounded error categories; the workflow runs both mobile-dashboard and bootstrap suites.

Other agents: the read-only bootstrap reviewer independently found the STOP
and orphaned-child defects, then owned only `test_termux_bootstrap.py`; the
coordinator integrated, ran the combined suite and actual Chromium smoke.

Next phone action: stop any running V13 via **V13 beenden**, then rerun the
one-command installer documented in `code/docs/ONE_COMMAND_TERMUX_20261111.md`
and use the newly opened browser tab. If the bridge was explicitly stopped,
the installer reports a separate local resume command instead of bypassing it.
`v13-update` targets `~/V13-Phone`; the dashboard has a separate update button.
B1/B2 native probe failures still require device evidence; no claim that this
bootstrap repair fixes model loading. Existing negative gates and overall
completion flags remain unchanged. No live relay request or private log was
published by this review.
