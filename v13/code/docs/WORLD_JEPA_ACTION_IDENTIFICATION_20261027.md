# World-JEPA 31-action consequence identification — verified 2026-10-27

**Owner:** `codex/automation11-world-action-identification-20261027`, draft PR #664, review-only child of PR #663 at exact `21342a61188f79d7d76870b22b3b3a013fe02829`. Preregistration `docs/proofs/continuation-20261027/world-action-identification/PREREG.md` committed **before new collection** (`7093838f7a21c42db7ed9b9b5754db31645087f4`). Not merged into main, AG5 or Claude.

## Frozen model and independent task

Same frozen 200-step checkpoint SHA256 `7cb6158b3f39de2d9fa589906c5ed24ce92869709ce18fc09a70f3804e8b20c0`, budget Actions 40456356170 ZIP SHA256 `8413b6abcdd2651c0e3346f348f0372b13dc4a407199e29a7e24cb9c1f23979a`, original Actions 40453512115 ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`. The checkpoint was selected using earlier heldout seeds313–315 and later checked on seeds401–403; these task results use **new** predeclared seeds **501, 502, 503**, 160 transitions each. No retraining, calibration, seed selection or runtime model change.

The model receives a file-world before-state and observed after-state, evaluates all 31 possible candidate actions with its frozen predictor, and ranks them by target-latent consequence distance. It is **inverse action identification after observing the outcome**, not prospective planning or reward-based causal intervention. Controls: prior-only guess from original training prefix (action30/noop), deterministic raw changed-slot heuristic, fixed rotated-label control, chance reference. All new real Linux temporary file-world process logs, schedules, SHA-bound timing receipts, raw cohorts and per-row rankings are preserved.

## Focused CI and main task result

Actions **40457153980** at `6024e7a63f7133779c9c935b92330b17f3f21a46`: **8/8 tests PASS**, independent restart VERIFY/COMPILE/PRIVACY exits0, original/budget ZIP SHA/CRC/path guards PASS. Raw artifact ID **12712826548**, ZIP SHA256 `b7bab8004dff0d30e8be0d6eba5c7d1a9a00c7673e7b0c5db2f928391753870d`, CRC/HEAD/exit independently checked. Original model and budget checkpoint bytes unchanged.

| New seed | Model top-1 | Model top-5 (reported) | Prior top-1 | Changed-slot top-1 | Rotated-label top-1 | World overlap |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 501 | **66.25%** | 91.25% | 12.50% | 28.75% | 0.625% | 3/160 |
| 502 | **71.875%** | 93.75% | 15.625% | 33.75% | 0.625% | 1/160 |
| 503 | **64.375%** | 89.375% | 8.75% | 21.25% | 0.625% | 3/160 |
| Weighted 480 | **67.50%** | **91.458%** | 12.292% | 27.917% | 0.625% | 7/480 |

Predeclared exploratory **top-1** rule beats all three empirical controls in each seed; top-5 also far exceeds 5/31. The original source reports mean true rank 2.0958. **This is not causal/semantic utility:** the after-state is already observed, the data are synthetic-content files in a real Linux process, and the checkpoint was previously selected. No native Body-JEPA, Redmi or AGI evidence.

## Independent numeric review: rank near-tie caveat (RED retained)

A first independent NumPy-only reference **failed exact rank reproduction**: seed502 row2, true action28, original rank3 vs independent rank6, despite same predicted top-1 action. Several candidate scores differ by only ~1.7e-18, so stable sorting exact floating-point values is not a portable near-tie policy. This failure is retained; no silent tolerance increase, cohort replacement or rerun was used to relabel the original result.

A separate **post-result** NumPy-only numeric-tie audit (no V13 imports, no fitting, exact frozen ZIP/model/cohort hashes) used an explicit 1e-12 absolute near-tie band **only to bound machine-dependent ranks**, not to rewrite the preregistered scores. It found **16/480 ambiguous true-action ranks**; all 480 original stored ranks fall inside the independent near-tie bounds. Crucially, **all 324/480 top-1 correct classifications are robust** (no top-1 ambiguity), so 67.5% and all three seed-level control wins survive. Top-5 is bounded at **437–440/480** (91.042–91.667%), original 439/480 (91.458%) lies inside. Mean rank should not be described as machine-invariant. Tie-audit source SHA256 `34ceb59a09d0c5f4a403ab1a27b961212736f203baed9c1c42d3fc0b11106e6a`; result JSON SHA256 `640e2072f9d362bffbdf63ee12ad24be59f3d9ccfd1bc35704eeb9e345c80647`. Original independent-reference RED note SHA256 `a69d3855c235f24cc8f3183ac629c270163dd613ffbaa85f455ce6715ea34bfe`.

Original workflow Actions **40457143913** ran the predecessor test module by mistake; **FAIL** retained and fixed before GREEN 40457153980. No fabricated first-pass green. All raw task ZIP, tie-audit source/results and RED note privately saved at `/V13-Checkpoints/2026-10-27/World-Action-Identification/` and re-materialized byte-exact. No rejected anyone-writable Drive destination used.

## Gates and next highest-priority package

STEP2 `UTILITY_FAIL`, B3 `L1_FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Age-0 approvals and full-system completion false remain. The confidence/uncertainty problem from fresh forward prediction remains 479/480 SIMULATION_UNCERTAIN; high inverse-action top-1 does **not** cure it. No runtime/default changes or owner/main merge.

Next: stop expanding isolated World-JEPA metrics and prioritize **AG5/World two-conflict integration candidate** (PR #658 analysis) with independent review and broad suite. Resolve `handy_pflicht.py` by retaining AG5 V2 atomic resume, and `v13/operator.py` by retaining AG5 locks/routing while adding only World `:world shadow`, `:ersetze`, `:effort detail|gist` under unchanged gates. Separately design prospective task-level intervention/semantic utility and native/Redmi proof, rather than promote this inverse metric.

Replay from `v13/code`: `V13_FROZEN_WORLD_ROOT=/original/closed V13_FROZEN_BUDGET_ROOT=/budget/trained V13_TASK_OUTPUT_ROOT=/new/task PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_world_jepa_action_identification`; persisted read-only: `python3 scripts/world_jepa_action_identification.py --original-root /original/closed --budget-root /budget/trained --output-dir /task --verify-only`.
