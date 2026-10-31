# Run94 pre-registration — historical Run34/37 source pin drift regression (2026-10-31)

Owner: GPT-6 Auto11. New review-only child of Run93 at exact parent 4ef9017f876444e2d31719f4e194fe6a4315a9f9; do not merge to main. Independent test-only work; no concurrent mutation of Run93/Run91 branches.

## Original evidence and problem
- Run91 unfiltered Actions 41198456896 terminal FAILURE, 4905 tests, 1 FAIL/2 ERROR/28 SKIP; original ZIP 13042120427 SHA256 6397e47f0c8f719c5a741d68b38f23c41a88fdb9890cde38f35d806e4322b7ba, CRC PASS, 23/23 inner SHA PASS.
- Run93 exact test-only Run92 fake-C3 fix, focused 12/12 GREEN; combined full-suite marker 4ef9017f876444e2d31719f4e194fe6a4315a9f9 triggered after Run91 terminal.
- Run34/37 historical prereg expects frozen `v13/utility.py` Git blob `f4a92dab9c4a40761d64394cdca1c052e9a76bfd`. Current live utility Git blob `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53` (separate legitimate later score-validation hardening). Other frozen Run34 pins still match: models `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, Run33 `b1d58d7e0c3937787cf15dd801e278de25845879`, runners `efda7aa1aa5729e974d0d641870d4da05d21c961`. Thus historical native prereg **must refuse** current live drift, not be silently repinned.
- Two historical test cases incorrectly assume the old full source pin still matches. Preserve original RED evidence and add explicit refusal assertions for current drift plus isolated historical pin simulation for metadata contract. Do not patch production, native scripts, prereg constants, frozen source, model, seed or scores.

## Ownership and acceptance
Only edit `v13/code/tests/test_run34_c3_native_quote_intervention_pilot.py` and `v13/code/tests/test_run37_c3_rule_use_native_pilot.py`; new scoped docs/workflow owned by this run. Existing test source behavior must still assert fail-closed on mismatched utility; separate isolated mock can validate frozen prereg metadata only after all other real hashes checked. Include adversarial extra drift (models/runner/run33) refusing even under utility-only simulation.
Focused CI: source pin drift refusal + historical metadata simulation + existing Run83 fake-C3 and strict SourceHandoff tests, privacy scan CLEAN, compile, diff. Unfiltered CI must include exact original STEP2 and Run13T ZIPs with SHA/CRC and 53/39 inner manifests; no selective exclusions. All tests 0 FAIL/0 ERROR required for engineering suite, but does not promote scientific gates.

## Negative gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight 0; Redmi UNMEASURED; whole V13 INCOMPLETE. No native execution claim. Next: implement test-only correction, focused CI, independent review, remote checkpoint; run unfiltered suite after Run93 terminal and preserve original failures.
