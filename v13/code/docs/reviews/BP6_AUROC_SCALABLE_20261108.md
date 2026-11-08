# BP6 scalable AUROC review checkpoint — 2026-11-08

Owner GPT, isolated review-only branch `codex/bp6-auroc-scalable-20261108` from #1593 commit `27453db1b1fdce6561348762a763521fd790f4ca`. Not integrated with `codex/resume-20261106` or main. This is a BP6 consumer-scale improvement, not a gate change.

## Code and rationale
The old `auroc2` computed every positive-negative pair, O(n_positive*n_negative), and accepted nonbinary truthy labels without validating input. New code uses the existing BP6 finite/domain validator and sorted confidence tie groups. Each positive in a tie group beats all lower-confidence negatives and scores half for equal-confidence negatives. Complexity O(n log n), space O(n), exactly matching the former tie-aware AUROC for valid pairs. `report` still rounds to four places and uses the same field. A new regression module compares to an independently implemented quadratic oracle across 100 seeded small/tied cases, invalid cases and the report consumer.

## Actual evidence and limitations
Direct raw.githubusercontent.com download failed: `URLError [Errno -3] Temporary failure in name resolution`. In an isolated local Python file, copied the candidate `_validated_pairs` and `auroc2` function bodies and executed 3 unittest methods: **3/3 PASS**, including 100 seeded comparisons against quadratic oracle, tie/extreme cases, and invalid inputs. **This is reconstructed-function testing, not byte-identical GitHub code or the committed regression suite.** No full checkout, full suite, privacy scanner, native/Redmi/model run or gate promotion. No frozen inputs, cohorts, source/model pins, preregistration or original evidence altered.

## Negative gates and continuation
STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Age0 RECORD_ONLY; whole-system INCOMPLETE remain unchanged.

Next commands in a full isolated checkout:
`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_metaeff*py' -v`
`python v13/code/scripts/public_repo_privacy_scan.py --base 27453db1b1fdce6561348762a763521fd790f4ca --head codex/bp6-auroc-scalable-20261108`
Run BP6 consumer tests, independent cross-review and #1586/#1589/#1592/#1593 ancestry check before integration. Then prioritize BP1 C3 consumer, BP2 weight learning and BP10 world-model utility over further BP6 polish. Do not launch competing native jobs.
