# Run135 — WP-HX2 SHADOW same-task blinded holdout review

2026-10-25 UTC. Base exact Run134 `787290a3a198b2cfab6ef89cd530354266b44b9b`; prereg separately committed `026e60752a218b12c9beb0bf2b5927526de127f6`. Owner ONLY new HX2 pure module/tests/workflow/proofs. Existing HX4 blind_select is reused unchanged. Frozen Runtime remains Git blob `a691d27bd0772a4fa1f03d57ec90663237bf6825`.

Local Linux Python 3.13.5 test-first RED: missing `v13.agi.hx2_paired_shadow` -> 1 ERROR. First implementation: 6/7 PASS, one test expected 80 tasks despite predeclared max 64 (test corrected to 60; failed attempt preserved). Independent adversarial reviewer added a new unguided-control case: guided beats reference but unguided beats guided; initial implementation incorrectly reported positive synthetic signal -> 1 FAIL. Fixed by requiring positive lower95 on BOTH guided-vs-reference and guided-vs-unguided for general AND domain. Final `python -m unittest -v tests.test_hx2_paired_run135 tests.test_age0d_answer_arithmetic_run134` **13/13 PASS**, compileall PASS. New HX2 tests 8/8 PASS.

The 60-task synthetic positive fixture (30 general + 30 domain) yields a diagnostic statistical signal, but `gate=UNVERIFIED` by construction. Two-round HX4 reversal detects position-biased judges; invalid labels yield NO_PICK; identical outputs TIE; generation exceptions INCOMPLETE; no prompts/output bytes in returned audit, only hashes. All three arms receive identical prompt and seed per task; calls are serialized.

Source Git blobs verified by independent remote fetch: module `7ecf704dc6c7df97a0888e756a24141a66f299cd`; test `1ef96c927e7c52d895b1dd8be91653ccaee782f2`.

Claim limits: This is software/synthetic evidence only. No registered B2 STEP2 rule-quote native holdout, no human-blinded real judge, no source/model/seed pin, no real CI>0 gain, no HX2 PASS or live consumer. Run131 native owner separate. Run129 full-suite 4 FAIL / 1 ERROR inherited, not rerun.

Gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE.

Exact next step: preregister registered B2 rule-quote real holdout with same-task reference/guided/unguided and judge, source/model/seed hashes, after Run131 releases native resources. Continue independent Canon work meanwhile. Do not activate harness overrides without HX2 and explicit user approval.

## Independent review follow-up: small-n false signal

Adversarial 6-task fixture (3 general + 3 domain) initially yielded `SYNTHETIC_DIAGNOSTIC_ONLY` despite tiny sample: RED 1/9 FAIL. Fixed by requiring at least 20 decisive blinded comparisons per axis and both guided-vs-reference and guided-vs-unguided lower95 > 0.5. Final local 14/14 PASS (9 HX2 + 5 AGE0d), compileall PASS. Remote module Git blob now `42967cece1a95ee918a43054241d81049877e79f`; test blob `d52b03cba3285071f86f47a8443eb6d9324b7d46`. No gate promotion.
