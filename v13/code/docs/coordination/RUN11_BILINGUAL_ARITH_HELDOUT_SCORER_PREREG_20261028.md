# Run11 disjoint bilingual numeric/unsupported-note scorer prereg — 2026-10-28

Owner: GPT-6, independent review child of #849 at `b99ce3ef8dd772130c3a56a1ec02e7ea203f3b5c`. Do not modify #849, #851 or frozen source-handoff runtime. Parent prompt candidate Git blob `646c6f31b52ca2664c1952af7c7e842fc3e20885`; baseline prompt blob `a74d7517a7ab70e801e177b58da057e57fd3460c`. Models, seeds, catalogs, C5, C2, C3, B1/B2, Age0 and approvals unchanged.

## Registered independent cohort (before scorer implementation or model execution)

`v13/code/specs/age0-bilingual-arith-heldout-20261028.json` Git blob **`ceda0a5cb506cf09885652b24893cf7d8fdff63b`**, committed as `b3e6134f8511e5271419f8e359513d66cacc6325`. Exactly 16 public author-defined questions: 12 arithmetic (6 EN, 6 DE) and 4 explicitly unsupported note questions (2 EN, 2 DE). The original 120/2 public test is excluded. Fixed operands and expected arithmetic outputs are author labels, not independently validated human gold. Do not change this fixture after evaluation; any new labels require a new version and registration.

## Software-only scorer design

Implement `scripts/age0_bilingual_arith_scorer.py` using Python standard library only. Inputs: exact frozen fixture and a separate externally produced JSON run manifest with unique per-ID answers, original question text, final status, runner role, tool_call, learning mode, jepa_weight, source commit, model SHA and prompt Git blob. Fail closed for unknown/duplicate/missing IDs, changed question text, non-final status, tool execution in Age0, wrong learning mode/weight, invalid schema or unpinned prompt blob. For numeric tasks, count an exact Decimal result only if present and there is no **additional unexplained numeric output** beyond the registered prompt operands. For unsupported questions, report only an **uncertainty-phrase heuristic**; a lexical match is NOT proof of non-hallucination. Preserve every raw row in the supplied manifest; never silently drop failures.

Predeclared adversarial tests: `37` must not match `137`, `37` must not pass when a contradictory `39` is also asserted, operand repetition `74` is allowed, `67,5` equals 67.5, duplicate/missing/unknown IDs are errors, non-final and unauthorized tool call are errors, unsupported answer `Bob` is not an abstention. Never treat missing output as a pass.

The scorer must emit `SOFTWARE_OFFLINE_SCORER_ONLY`, original negative gates and `whole_system_complete=false`. It cannot claim native execution or evaluate prompt quality until independent **real pinned Linux native** baseline and candidate manifests are captured, SHA-bound to their raw output and inspected. Source manifest strings alone are not cryptographic proof. Compare exact same 16 rows for both prompt cohorts; preserve original #848 RED and #849 single-case result. Any native run requires an exclusive owner and new prereg before execution.

Tests: isolated `python3 -m unittest -v tests.test_age0_bilingual_arith_scorer`, then full suite if CI dependencies permit. No Redmi/Body-JEPA/B3/STEP2/LP3 promotion; Age0 RECORD_ONLY, jepa_weight0, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL remain.
