# V13 Run26 — WP-Z6b C3 draft arithmetic cross-check (SHADOW candidate)

Base: PR61 Run25 `0590c9334dbbd6d286af2825ed6c4a7712f51c02`, Claude PR38 ancestry. Isolated new package, not integrated, no runtime/model/Canon/AGENTS changes. Owner: Codex Run26 files only.

## Problem and runnable component

Z6a measured `Z6A_EFFORT_ADAPTIVE_FAIL`: adaptive woke a body on 60/60 real-model turns, including all 42/42 turns already solved by C3 disabled. Existing heuristic depends on task type, not first C3 draft reliability. This package adds a deterministic *negative-only* arithmetic contradiction signal for generated C3 drafts. It does not claim that absence of contradictions means correctness, and does not decide wake or execute tools. It can read JSON input records and write a closed, durable, non-overwriting per-record evidence report with source SHA256.

## Evidence

15/15 software tests PASS; compileall PASS. Cross-review checks explicit sums, total-with-parenthesized-sum, subtraction differences, inverted high/low ordering, unknown text, duplicate IDs/keys, large input, atomic report and symlink output non-overwrite.

Retrospective, **not preregistered** diagnostic on the existing Z6a real-model disabled-arm outputs (60, seed 23; source Git blob `995c76b46c334945260b6bd29d33d3012b2992b4`): 9 flagged, of which 8 previously failed and 1 previously passed. 10/18 prior failures unflagged. The flagged PASS (`summary03`) contained an explicit incorrect arithmetic equality despite passing the original answer scorer. This is only a diagnostic; no new model run, no improvement claim. A 10-row local sample (nine flags + one negative) reproduced the flags using the Python component; full 60-row retrospective analysis was performed read-only against GitHub JSON using equivalent JS expressions, not Python. Results are not a prospective gate.

## Next

Prepare and preregister a fresh C3-first versus baseline comparison with exact real drafts, independent verification, equal compute budget and selective wake after verified contradiction. Keep original Z6a thresholds A1–A3 unchanged. Do not infer C3 certainty from lack of a contradiction. Model availability, process ownership, RAM and Redmi proof need fresh verification. Other Canon packages remain required.

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. No unsafe tool/learning rights enabled.
