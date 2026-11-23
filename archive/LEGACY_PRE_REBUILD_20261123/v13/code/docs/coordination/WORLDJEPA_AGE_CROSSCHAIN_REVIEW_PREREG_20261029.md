# V13 cross-organ World-JEPA + Age evidence integration — prospective review registration (2026-10-29)

## Frozen starting state and ownership
- Exact parent: PR #1100 review head `46ba21b13cd7801713a2c5616f16f61d4b4441cd` (itself descendant of PR #1090); main remains older. This is a **new review-only child**, not a merge into production.
- Preserve the entire Canon `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` unchanged, and the existing registered model, cohort, seed and native proof hashes.
- Independent donor #1091: World-JEPA single-member confidence guard source blob `5ada6e93ae4cab2e3dedfec82c315d559fb9cd6b` and test blob `5b066d6a6c3a3fd0088c177910f84889f99f3056`. Donor GREEN Actions 40874868249, software only.
- Independent donor #1092: Age0 typed direct-record admission source blob `964048c47ddb5a8f11ea6706d72a1f37ab41f5d4`, new test blob `fe4afc659676ae55a20b4c8cfe90a428c70602d1`, corrected historical test blob `533f3cc9c9ec23ddb4afc2dec3954e0e98f99c8b`. Original Age source blob `d4c38ae344746811fedecff706a9affe9cf8b375`; original RED retained by donor. Verify latest Age GREEN evidence independently; do not assume CI name alone proves full suite.
- File ownership: only these exact donor blobs plus this preregistration, a dedicated cross-chain integration regression test, scoped Actions workflow, and new handoff. No changes to either donor/parent branch.

## Question and test protocol (registered before integration)
Can both independently reviewed guards coexist in a real Store/Runtime software path on the current trusted-skill chain without changing age/learning/latent authority, while rejecting malformed Age evidence and avoiding false World-JEPA single-member confidence?
1. Import **exact** donor source/test blobs, no manual edits to donor logic.
2. Test positive finite Age evidence and None-as-unmeasured; negative bool, nonfinite, malformed IDs and invalid retention must fail closed without promoting the stage or persisting unsafe evidence. Exercise actual Store and AgeControl.
3. Test World-JEPA confidence with a single member (zero epistemic ensemble confidence) and a multi-member positive control; no native model inference or JEPA utility claim.
4. Run pinned focused tests, compile, dependency checks, full software suite and public privacy scan in a source-only GitHub Actions workflow. Record original raw logs, SHA256SUMS, exact head and stage exits. Preserve RED as RED.
5. If historical frozen-source identity tests fail solely due changed source, retain failures and do not rewrite frozen pins. No gate promotion.

## Unchanged negative gates
Age0 `RECORD_ONLY`, BUILD_CEILING=0; STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; LP3 `FAIL`; `jepa_weight=0`; AG6 not approved; Redmi not measured; whole V13 incomplete.

## Next exact command
After import and isolated dependency setup, from repository root:
`cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_run49_world_jepa_single_ensemble_confidence tests.test_age_record_typed_evidence_candidate tests.test_age_evidence_id_preflight_candidate tests.test_skilllive_crossskill_conflict_20261029`
Then full `PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py' -q`.
