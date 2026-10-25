# Run294 — current-option authority in the eligibility tool (software-only)

2026-10-25 UTC. Owner: `v13/code/v13/agi/eligibility.py`, `tests/test_run294_eligibility_option_authority.py`, CPU-only workflow and this scoped proof. Base PR293 exact `df5f29c1f4a1ac4f9e58d83cecd9bccc3ba6fe7a`; PR284 Runtime, PR293 output adapter, registered models/seeds, original Canon, thresholds and learning gates untouched.

## Concrete defect

The direct READ_LOCAL eligibility recipe previously accepted Option A values from an older exact quote even when the current message explicitly changed Option A's cost. Multiple contradictory current option clauses were resolved to the first; Option A could borrow missing `local` from an adjacent Option B in the same sentence. The recipe also silently accepted conflicting current budget values if the extracted value matched one of them, and `bool("false")` made a string into true. A fixed-reader path already mitigated some cases; the tool and model-reader fallback did not.

The new `option_clauses` separates A/B markers even without a period; `decide` treats a current field-bearing option clause as authoritative and refuses stale or contradictory values, while bare mentions still allow earlier exact evidence. `fixed_option` refuses inconsistent duplicate current clauses. Exact typed option comparison replaces truthy string conversion. Current conflicting rule values refuse. The original `A:option_not_stated` diagnostic is retained alongside the new `A:conflicts_current` reason to avoid breaking existing consumers. No new permissions or autonomous action were introduced.

## Preregistered RED → GREEN (real GitHub Actions, not fabricated)

- RED exact head `c7ca0f67194039d222ba35df2ffa785acf00df87`, workflow `40200578065`: **38 tests, five expected adversarial FAIL, 33 PASS**; original eligibility tests PASS; official privacy CLEAN. Raw ZIP artifact `12601323687`, SHA256 `fc3decb1aacf33b787e285084862834a1afacdb7b039887418d7a119cbab1727`.
- First GREEN attempt `665f660a1f8cdc12ffc03fe2368c854ff7d5da57`, workflow `40200630433`: **37 PASS, one legacy FAIL** because its original diagnostic `A:option_not_stated` was replaced by `A:conflicts_current`; privacy CLEAN. Kept the failure, repaired backward-compatible reason emission. Raw ZIP artifact `12601403687`, SHA256 `c56ca42171574946d382157f158a8bca671e93bed4105f0b1ffa29769603fa73`.
- Final GREEN exact source `e340631388676b942a8af0e920e5dd5a53839e8d`, workflow `40200695273`: **38/38 PASS**, including eight new adversarial cases, original tool/fixed/live tests; official privacy CLEAN. Raw ZIP artifact `12601239110`, SHA256 `d0a5071bbf8a2c413c0346e33602bfdebd4eca5914d22361ea656830533d3e22`.
- Focused source-bound workflow `40200695257` on the same source: **401/401 PASS**, extracted Phone **114/114 PASS** plus restart, official privacy CLEAN; phone source ZIP 1008 manifest entries, SHA256 `4e13712f7c5c926423b17377cc6484703d0ab055cc6c3d950f854831cdd8ee15`; outer artifact `12601202652` SHA256 `08226285b9bb72fed6877503748b21ecfdb6ff75eae9d1d1624aff3859032064`. This is source packaging and Linux software, **not** a Redmi execution.
- Independent local extracted exact Phone source, Python 3.13, `python -m unittest -q tests.test_run294_eligibility_option_authority tests.test_eligibility_tool tests.test_eligibility_fixed tests.test_eligibility_live`: **38/38 PASS**. Full `unittest discover` was separately attempted with a 150-second cap; it did not produce a terminal unittest summary before the cap and the process is no longer running. Its partial stdout/stderr is preserved locally; **NOT a full-suite PASS**. The dedicated 401+114 CI source-bound checks above are complete.

## Integrity and backup

Canonical SHA256 remains `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`. Exact source Git blobs: eligibility `1778752f4a92de660a48a3c208134ef601bcbb9f`; new test `f2dfccaa45199fa130c7c651dd2dc2d9a78c3317`; workflow `a0bc2c9f98eadbcf37b8b600136dd661f6eb361d`. Three raw RED/failed-GREEN/final-GREEN ZIPs stored in private ChatGPT Library `/V13-Inquisition/Proofs/Run294/` and downloaded back; each SHA256 and byte comparison matched. The final phone-source outer archive is also uploaded to that private folder; downloaded back and byte/SHA256 verified (`08226285b9bb72fed6877503748b21ecfdb6ff75eae9d1d1624aff3859032064`). The rejected anyone-writable Drive destination was not used.

## Negative gates / next

This is an eligibility evidence precedence repair, not proof of semantic learning or native model quality. Original `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, Redmi UNMEASURED and whole V13 INCOMPLETE remain. No learning age or tool permissions changed.

Next: finish independent local full-suite outcome; verify Library readback of the source ZIP; checkpoint any new evidence. Then pursue a **different substantive blueprint package** (prefer the actual native retrieval / halt / body-learning utility failures, while PR284 Runtime and PR293 adapter remain owned), with separate preregistration and unchanged cohorts. Native inference requires pinned model artifacts and serialized owner check; never claim it from software tests.
