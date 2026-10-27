# V13 integration review: Z1 + JEF Run554 + BP11 module lifecycle (preregistered 2026-10-27)

Owner: GPT-6 automation continuation; review-only, NOT main. Source baseline: five-parent review integration PR #672 commit `9eae3cc175512382038cc5f55887e7a8dbc9797f`, tree `9ff3f1e7cbe6fe3508ccb38e2265c614e0a8463a`.

Pinned independent parents (verify freshness before constructing tree):
- Z1 gate evidence typing + path integrity PR #696: `968932a20ed963f1e27554510a6903546e219918` (includes #695).
- JEF Run554 fixture/nonanswer regression PR #698: `2ff03034f490fff2b79e23bb6dc650c6a92e795e`.
- BP11 module lifecycle CAS + direct typed recall ban PR #676: `4c006395733a282a69a863c79d4e5847b80e0057` (includes #675).

**Pre-implementation hypothesis:** these three branches are exact descendants of #672 and change disjoint paths. Construct a Git tree from the prereg branch with the union of exact head blobs, preserve all three source commits as additional parents. Reject path collisions, missing/non-blob paths, changed head refs, or byte differences. Do not auto-merge main or activate tools/models.

**Acceptance / independent tests:** run Z1 verdict/path/registered gate tests, BP11 module lifecycle and direct-ban tests plus original modules-gate tests, JEF Run554 + Run552 FINAL receipt + Run553 USER-only safety + AG live tests, compile and privacy scanner. Capture raw logs, exit codes, source HEAD/tree and SHA256; independently verify remote tree/blob parity. Retain historical broad-suite RED (4,496 tests, 5 FAIL/73 ERROR at Actions 40488716919) and original raw evidence. A focused PASS does not imply full-suite GREEN.

**Negative gates unchanged:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; Redmi sustained UNMEASURED; full V13 INCOMPLETE. New code is review-only and does not grant model/module/learning authority.

**Next after verification:** reconcile focused integration with new BP1 native V2 results on a separate branch; address remaining source-lineage full-suite failures without changing frozen pins; continue executable user-facing canonical packages.
