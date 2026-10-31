# JEF full-suite exact-parent RED differential — independently audited (2026-10-31)

**Owner:** GPT-6 scheduled continuation; review-only child of PR #1425 at exact `611724bee6b6511826c36af64421d96d1b276016`. Branch `codex/jef-fullsuite-parent-differential-audit-20261031-auto11`. No frozen runtime, Canon, model, runner, cohort, source hash or active native owner modified. Parent control PR #1425 and policy child PR #1423 remain open and RED; no production merge.

## Original raw, not a rerun

| Original Actions | Tested SHA | ZIP SHA256 | CRC / inner hashes | Unfiltered unittest |
| --- | --- | --- | --- | --- |
| #1425 parent `41176551097`, artifact `13032807337` | `611724bee6b6511826c36af64421d96d1b276016` | `4adbb12881a0d91660f8085da37c12b726d0a856b135463d74dea4d0e722e396` | PASS / 31 of 31 | **4612; 4 fail, 66 errors, 28 skipped** |
| #1423 child `41175500095`, artifact `13033007113` | `4ff58c0cb79d77b760b90163e52a16a90807b4a8` | `aee143795316319f9945a52d8892bbbb5b0d2ca0432cc1e34751e5ab7e6cf3ae` | PASS / 31 of 31 | **4616; 4 fail, 66 errors, 28 skipped** |

Both original workflows terminal **FAILURE**; `FULL_EXIT=1` retained. All 13 other prerequisite/compile/privacy/diff stage exits were 0 in each raw. Both used Ubuntu 24.04, Python 3.12, NumPy 2.2.6, torch 2.5.1+cpu, transformers 4.44.2, peft 0.13.2, the same unfiltered unittest discover command and same timeout. Both ZIPs were read directly; never extracted or executed. The new stdlib-only bounded tool validates exact outer SHA256, ZIP CRC, duplicate/path/symlink/size, every inner SHA256SUMS, original tested HEAD and prerequisite exits.

**Observed differential:** exactly +4 tests in the child; the same 4 failures, 66 errors, 28 skipped; the retained ERROR/FAIL header **multisets are identical** (121 occurrences, 87 distinct, including nested phone-package failures). Status: `MATCHING_RETAINED_FAILURE_HEADERS_NOT_A_GREEN_SUITE`. This supports **pre-existing failures at the exact parent** rather than attributing those identical failures to the Sleep-policy fix. It **does not prove** all stack traces or passing-test behavior identical, nor exclude an undetected regression. Main causes include historical source-handoff/native-firing identity mismatches and nested extracted-package checks; original RED is not waived.

## Independent software verification

Source: `scripts/jef_fullsuite_parent_compare.py` (Git blob `a0aea11c278af9ee4dd7cb0b700bea5490b32d45`). Negative tests: `tests/test_jef_fullsuite_parent_compare.py` (Git blob `0cb6d1057d95b8c20e2ef2827405b44eb2135022`). Local original ZIP comparison returned status above; 10/10 local synthetic negative tests PASS. Remote GitHub Actions `41179381498` tested `fddabf9d3c603fd42d269dcb97a80b5975786526`, terminal **SUCCESS**; 10/10 tests PASS, 4/4 stage exits 0, privacy `CLEAN`, diff/compile PASS. Original CI artifact `13034451468` ZIP SHA256 `b8e40b886372f7761e4870970b6c6c2decac8fb8bd798619d7d31605ee7d2d8c`, CRC PASS, 9/9 inner hashes PASS, HEAD matched.

Reproduce (from repo root with both original ZIPs supplied locally):
```sh
python3 v13/code/scripts/jef_fullsuite_parent_compare.py \
  --baseline ORIGINAL_PARENT.zip --candidate ORIGINAL_CHILD.zip \
  --baseline-sha 4adbb12881a0d91660f8085da37c12b726d0a856b135463d74dea4d0e722e396 \
  --candidate-sha aee143795316319f9945a52d8892bbbb5b0d2ca0432cc1e34751e5ab7e6cf3ae \
  --baseline-head 611724bee6b6511826c36af64421d96d1b276016 \
  --candidate-head 4ff58c0cb79d77b760b90163e52a16a90807b4a8
python3 -m unittest discover -s v13/code/tests -p 'test_jef_fullsuite_parent_compare.py' -v
```

Private original parent raw backup `/V13-Checkpoints/2026-10-31/Run1425-JEF-Parent-Baseline/ORIGINAL_PARENT_RAW_41176551097_SHA4ADBB128.zip` uploaded and re-materialized SHA256 byte-equal. Child original raw already backed up by #1423. Software CI original raw should likewise be privately retained. Never use the rejected anyone-writable Drive destination.

**Open:** full unfiltered suite still RED; do not rewrite historical frozen SourceHandoff/native-firing pins or promote this patch. Future source-handoff integration requires separate reviewed hash-bound candidate and full regression. C3 native formatter remains 1/3 strict in Run66, source-only fallback 2/3, not useful language fidelity. Actual TTY/Redmi, STEP2, B3, Body-JEPA, jepa_weight and whole-system gates remain negative. **Next command:** review latest open PR heads and choose another independent Canon organ or a separately registered fresh C3 receiver cohort, not a rescore of original P2X. Heavy native jobs serialize under `v13-native-c3-ag12-20261030`.
