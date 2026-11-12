# Core Android stop latch review checkpoint — 2026-11-12 05:04 Europe/Berlin

Owner: Core & Harness. Branch `core/v13-android-stop-latch-hardening-20261112-0504`, draft PR #1822 stacked on Core #1820; no other owner's source edited.

## Two functional fixes
1. `StopLatch.engaged()` now uses `os.lstat` to distinguish a genuinely absent marker (allow) from an inaccessible marker (deny), preserving fail-closed symlink and malformed-marker behavior.
2. The already-open `android_local_console` checks the marker before each operator command and stops its registry if another local session engaged the marker. No automatic reset, permissions, or native execution added.

## Evidence and limits
- Source and three targeted regressions committed; GitHub readback required after this checkpoint.
- Direct clone unavailable in this execution environment: DNS failure `Could not resolve host: github.com`. GitHub Actions exact-head result not observed; tests therefore **UNVERIFIED**, not PASS.
- Same-UID Termux process/file controls are not an OS-enforced security boundary. A marker arriving *during* transport/approval is not covered by a pre-command check; independent native companion stop enforcement is still required.
- No Redmi proof, no production integration, no STEP2/B3/Body-JEPA/whole-system gate promotion.

## Exact next command
`PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_android_local_console.py v13/code/tests/test_android_operator_audited_session.py v13/code/tests/test_android_operator_validation.py` on exact PR #1822 head. If green, independent review of stop-vs-inflight race and OS companion; then integrate authenticated Android ActionOutcome into JEF/C5→T8. Continue B1/B2/C3 training/export and voice contracts on separate owned modules.
