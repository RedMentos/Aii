# list_arith source-number sign guard — isolated review, 2026-10-16

Confirmed bug in current `v13/agi/listarith.py`: `_INT = (?<![\d.])\d+(?!\d|\.\d)` finds positive `5` inside literal `-5` (and `−5`, U+2212). Given `Items: a -5, b 2. Give the correct total.`, model values `a=5,b=2` pass the source guard and return **7**. The correct signed values `a=-5,b=2` are rejected. The correct total is **−3**. The largest-minus-smallest recipe similarly gives 3 for the sign-flipped reading, while the correct result is 7. `counterexamples.json` preserves direct baseline/candidate results.

This reaches the actual ToolStep proposal path: a deterministic FakeC3 reader returning the sign-flipped values produces a proposal under the baseline; the isolated candidate rejects it before proposal. This is a software-path counterexample, not a claim that the native model actually makes this error.

## Domain and scope

The runtime READ_SCHEMA declares `number` as `integer`, with no nonnegative minimum; READ_SYSTEM requires numbers copied exactly. `compute`, `encode` and `decode` already use Python integers and the same total / largest-minus-smallest recipes. The externally exposed tool therefore does not declare signed integers invalid. However, K's measured fixtures are positive: `scripts/utility_bench2.py` samples expense inputs 12..95 and rainfall 100..899; the tool-choice contexts in `scripts/r4_tool_choice_head.py` use 12..95, 100..900, 3..60 and 5..120. Existing tests use positive listed inputs and reject fabricated values. No measured K signed-reading accuracy is implied by this fix.

`proposed.patch` changes only the `_INT` expression and its token canonicalization. A contiguous ASCII `+`/`-` or Unicode mathematical minus U+2212 remains attached to the integer; positive `5` cannot match the digits inside negative `-5`. Positive plus signs are removed and U+2212 is mapped to ASCII minus solely for comparison with `str(int)` values. Blocking a preceding sign prevents the engine from recovering a positive suffix from malformed multiple signs. Decimal fragments remain rejected, and a sentence-final period remains allowed. Leading-zero behavior is unchanged. No recipe, operation chooser, model prompt/schema or permissions change is proposed.

This is an integer-token membership guard, not a full numeric-language parser. It still does not bind names to specific source occurrences or enforce multiplicity, and it makes no promise for scientific notation, locale separators, ranges or spaced unary signs. It does not establish signed-value extraction accuracy or arithmetic utility on a model/device. Those require separately declared evidence.

## Isolated validation

`PYTHONPATH=.:tests python docs/proofs/continuation-20261016/list-number-guard-review/test_candidate.py`

18/18 tests passed: eleven targeted review cases plus all seven unmodified upstream list_arith tests. Targeted checks include positive/negative total and difference controls, both minus forms, explicit plus, parentheses/sentence punctuation, multi-digit suffixes, malformed multiple signs, decimal rejection, label/tool rejection and the real ToolStep proposal path with only its C3 reader stubbed. All 180 positive arithmetic fixtures drawn from K's six standard seeds produce identical values and labels. Upstream rule checks also exercise unchanged choices across all 360 R4 tasks and the rule families.

An initial harness test accidentally applied the candidate to its own intended baseline contrast; it failed as expected from that setup error. `initial-harness-failure.log` is preserved. The corrected harness explicitly installs baseline `compute` for that first contrast, then candidate `compute` for the new behavior. No numerical or behavioral expectation was changed.

`baseline-listarith.py` and `source-binding.json` preserve the reviewed current source; `candidate-listarith.py` is isolated here. `compute-comparison.json` confirms the compute AST is identical after excluding the one token-assignment change. The final runtime source hash remains unchanged. No native job, source-freeze edit, shared status edit, commit or publication was performed by this package. Integrate only after the coordinator closes the active native cohort and issues any required fresh binding.
