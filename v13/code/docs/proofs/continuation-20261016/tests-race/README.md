# Deterministic resource-test race fix — 2026-10-16

Exact test-only port from Thread O commit
`c9b7eddf996406a0f3dc128fdcd585e690bd46cd`. All three current files match their
upstream Git blobs (`upstream-provenance.json`): `tests/resource_pins.py`,
`tests/test_bodies.py`, `tests/test_executive.py`. No production change in this
package, and no native inference.

Root cause: assigning `runtime.guard.state` does not pin a resource scenario.
The coordinator's idle `SleepRuntime.resource_state` calls
`guard.update(runtime.resources())`, replacing injected CRITICAL/PRESSURE with
healthy host measurements. Sleep policy OFF still permits that resource tick.
BodyFabric then correctly follows the updated state; RECOVERY maps to GREEN.

`before.json` deterministically forces the actual sleep resource tick between
C3 and B2 requests: CRITICAL becomes RECOVERY and residency becomes C3+B2,
reproducing the combined-suite failure without waiting for thread timing.

The upstream helper installs a fresh ResourceGuard that evaluates one fixed
sample with real transition rules and pins resource reads. A tick already bound
to the old guard can only change that discarded object. Tests otherwise keep
their existing assertions; the bodies fixture gets a NORMAL default, the
pressure test pins CRITICAL and the executive abstention test pins PRESSURE.

`after.json` forces both a stale bound update on the old guard and an actual
sleep tick: old guard updates to NORMAL, current guard remains CRITICAL,
resident roles are only B2. `focused-tests.log`: **20/20 tests pass** across
the complete bodies and executive suites. This establishes deterministic test
resource injection, not new production resource or Redmi behavior.

The parent coordinator owns the full combined suite, status and checkpoint.
