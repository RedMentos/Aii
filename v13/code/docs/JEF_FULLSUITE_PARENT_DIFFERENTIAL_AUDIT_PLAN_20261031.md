# JEF full-suite exact-parent differential audit plan (2026-10-31)

**Owner:** GPT-6 scheduled continuation. **Scope:** read-only retrospective comparison of original raw ZIPs from PR #1425 (unmodified parent control) and PR #1423 (JEF Sleep-policy isolation child). This is **not** a preregistered scientific intervention, no inference, no fresh cohort, no utility gate, no permission change.

Original Actions runs: parent `41176551097`, tested HEAD `611724bee6b6511826c36af64421d96d1b276016`, artifact `13032807337`; child `41175500095`, tested HEAD `4ff58c0cb79d77b760b90163e52a16a90807b4a8`, artifact `13033007113`. Exact original ZIP SHA256: parent `4adbb12881a0d91660f8085da37c12b726d0a856b135463d74dea4d0e722e396`, child `aee143795316319f9945a52d8892bbbb5b0d2ca0432cc1e34751e5ab7e6cf3ae`. Both original runs completed FAILURE. No source/model/seed hashes are changed.

**Check before any inference:** ZIP byte SHA256, duplicate/path/symlink/size/CRC, complete inner SHA256SUMS, expected HEAD, every prerequisite exit zero and original FULL_EXIT=1. Compare final unfiltered unittest totals and a multiset of all retained ERROR/FAIL headers (including nested package tests). Report count delta separately. Do not interpret header equivalence as traceback equivalence or regression absence. Retain all RED evidence; reject mismatch without waivers. Use stdlib-only code, synthetic negative tests, and a separate review branch; never extract or execute ZIP members.

**Original observations already known before this retrospective plan:** parent 4612 tests, child 4616; both 4 failures, 66 errors, 28 skipped. The audit checks rather than presupposes the equality of detailed retained headers.

**Next:** run independent bounded audit and negative tests, publish exact commands/results, remote-readback verify, then continue a distinct authorized package. No production merge, TTY/tool/learning, STEP2, B3, Body-JEPA, jepa_weight or Redmi promotion.
