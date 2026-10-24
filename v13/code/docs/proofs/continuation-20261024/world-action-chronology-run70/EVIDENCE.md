# Run70 evidence and independent review

Original `world_model.transitions` uses the most recently inserted ActionSelection for the event regardless of when an action was created. Synthetic SQLite with two actions/selections shows earlier action relabelled by future selection; original 3/5 adversarial RED (two-action, future-only, between-actions). Full original RED log retained in local checkpoint.

Fix: require same-event `packets.created<=actions.created`, deterministic `ORDER BY created DESC,rowid DESC`; malformed action timestamps excluded before lookup. This changes only the existing transition read model, not the registered model objective, action producer or native runtime. `world_model.py` Git blob old `6e02ff7e8547dd4ef2912b1e168feacd29f9f0ea` -> new `6ebe347d989b8dbbc80d3e54baadcb8d36c45436`.

Isolated exact-function SQLite tests **5/5 PASS**, Python -O **5/5 PASS**, compileall PASS. New full-checkout test file authored but actual V13 Store, full suite, privacy, native and Redmi NOT RUN.

Review limitation: chronological prior selection is a bounded improvement but not a strict action-ID link; wall-clock ties may not establish true order. No new causal or utility claim. SQLite ORDER BY tie semantics: https://www.sqlite.org/lang_select.html

Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.

## Independent review after checkpoint

The original Run64 synthetic SQLite Store fixture omitted `packets.created` although the real V13 Store schema includes it. The new chronological query would have raised `sqlite3.OperationalError` in the existing integration tests. This was found by reading the existing tests before attempting full-suite promotion; no false full-suite PASS is claimed.

Updated only the Run64 test fixture DDL and insert to include a selection timestamp earlier than its action (Git blob `0527010232799633c79776dd96cfeb4ed94614b0`). Run65 tests import the same Store fixture. Full repo still NOT RUN. No production fallback to an unbounded future selection was introduced.
