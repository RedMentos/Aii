# WP-UI1 independent review prereg — generated Termux:Widget shell path quoting

Date 2026-10-29. Owner: `codex/wp-ui1-widget-path-quoting-review-20261029`. Exact original Claude WP-UI1 source branch `claude/project-thread-e53fle` at `61297975a215f284ca86044a54e306b6f1174ec9`; original `v13/code/KNOEPFE_EINRICHTEN.sh` Git blob `73c43485f929a81add056e0b0d0c8a3a0136cab0`. No prior test/RED/GREEN claim is invented.

## Source-observed defect (pre-existing observation)

The script writes generated widget shell commands with unescaped single-quoted interpolation of user-configurable `V13_HOME` and install `APP_DIR`, e.g. `export V13_HOME='$V13_HOME'`, `f='$APP_DIR/docs/BEFEHLE.md'`, `V13_HOME='%s'`. A valid custom path containing an apostrophe can break generated Bash syntax, and crafted shell metacharacters inside a path may be interpreted as shell commands. This is a review hypothesis requiring isolated reproduction; default Termux paths do not prove safety for all allowed paths.

## Locked review and acceptance

Create new isolated test `tests/test_wp_ui1_widget_path_quoting_review.py`: use a temporary HOME and `V13_HOME` containing spaces, apostrophes and a literal `$(touch ...)` marker; run installer with `bash` and no Termux dependencies; verify all five generated scripts `bash -n` parse, that mocked `v13 chat` sees the exact literal home path, that both one-way stop buttons create only intended control files under literal home and do not execute the marker, and that `V13 Befehle` passes the exact installed docs path to a mocked pager. Verify `weg` only removes the five owned shortcut files. Initial test-only branch expected RED; preserve its original raw output. Then make the narrowest `KNOEPFE_EINRICHTEN.sh` quoting change, not the underlying runtime, phone_halt, model, SourceHandoff, age, registered cohort/seed/source, or user permissions. Use `printf %q` Bash shell escaping for generated assignment literals; retain original five button semantics and 0700/0600 permissions.

Run focused tests and full suite in branch-only software CI with original RED preserved, source pins, privacy/diff and SHA256SUMS artifact. No native/Redmi or home-screen UI actually run on phone; Linux subprocess behavior is not Android confirmation. This is not authorization to integrate into frozen production chain or claim the full WP-UI1 gate. All negative gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 incomplete.
