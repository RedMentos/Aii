# C3 deterministic source operator — preregistered question-boundary and seeded robustness review (2026-10-30)

**Owner:** GPT-6 scheduled review, isolated files `tests/test_c3_deterministic_boundary_run11.py`, `v13/agi/listarith_de_deterministic_source_candidate.py` only after RED, and a new branch-scoped CI workflow. Parent exact head `10b3c8d01ff8ed55ba1bfcafd42a90be677a2c5b` (#1233); never rewrite frozen seed83/109 data, source/model/binary hashes, scorer, or prior raw.

**Hypothesis:** the new operator accepts a trailing question *block* containing multiple sentences when its existing `question_part` returns all digit-free trailing sentences. The parser currently checks only `question.endswith("?")`, so a source with two separate questions (one sum, one unsupported) can be emitted as a single result. This contradicts the parser's explicit one-question narrow contract. No native calls are required.

**Frozen negative cases (must abstain, closedworld must be null):**
1. `Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe? Welche Farbe hat die Kiste?`
2. `Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe. Und welche Farbe?`
3. `Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Welche Farbe? Wie hoch ist die Summe?`
4. `Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe? Wie lautet die Uhrzeit?`
5. `Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe! Und welche Farbe?`

**Frozen positive controls:** original eight seed109 narrow sources remain accepted (without changing their original scores), plus seeded generated lists with 2..8 distinct alphabetic names, repeated/signed integers in [-999999,999999], operation total and max-minus-min, 40 cases with Python `random.Random(117)`; for supported cases the exact `SHADOW_RESULT` value must match Python `sum` or `max-min`. No case may claim native/Redmi/learning/tool/age promotion. Use a deterministic fixed seed; no model inference or external action.

**Test-first:** commit test + branch-scoped workflow, run CI and preserve original RED; only then add minimal fail-closed parser fix; run same CI GREEN and recheck existing C3 operator, closedworld and native-receipt software tests. If a frozen positive control proves outside current narrow syntax, preserve the RED and report rather than silently changing fixtures. Do not change existing `german.propose`, `question_part`, scorer, source hashes or any authority flags.

**Expected safe resolution:** refuse multi-sentence trailing questions in this *opt-in deterministic mode only*. No effect on original model/native operator path. Evidence is synthetic/software; STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA unavailable, jepa_weight=0, Redmi unmeasured, V13 incomplete. No automatic merge.
