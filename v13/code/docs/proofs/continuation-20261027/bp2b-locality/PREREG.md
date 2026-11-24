# WP-BP2b · preregistration · 2026-10-27

Owner: automation11, isolated child of PR #703 `89055e5b5542336bd24f521382a3fd5cd1d8c616`; review-only. Scope: `v13/code/v13/locality_anchors.py`, opt-in hook in `v13/code/v13/body_jepa.py`, `v13/code/tests/test_bp2b_locality_anchors.py`, workflow and this proof directory. Do not change frozen BP1/BP2a cohorts, model files, existing scores, or user authority.

Problem: BP2a measured near-miss leakage falling from .75 to .16 with manually curated locality anchors, but `LoraTrainer.locality_prompts` only rewrites `my <noun>` and misses `I/do I/am I/did I` prompts. The manual anchors are not yet reproducibly available for new everyday facts.

Package: implement deterministic English first-person **subject-shift** anchor generation, using only the question, a fixed explicitly disjoint training subject list, and no target or heldout strings. Require one short single-line question and recognized grammar; fail closed to zero anchors on unsupported forms. Emit distinct grammatical near-miss questions; never transform target answers, approve learning, or perform inference. Wire only into `BodyJepaTrainer` behind `locality_policy='bp2b'` (default `legacy`), leaving all original arms byte-identical.

Prospective checks: (1) source question unchanged; (2) target and answer keys not consumed; (3) 16+ first-person grammar forms; (4) no duplicate or identity anchors; (5) deterministic output and bounded count; (6) no reserved evaluation subjects; (7) malformed/unsafe/multi-line/unsupported input yields zero anchors; (8) integration test confirms legacy default and opt-in behavior. Run `PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_bp2b_locality_anchors.py' -v`, compileall and public privacy scan. Run GitHub Actions source-bound software review if available.

**Acceptance:** all tests pass in software-only CI, no changes to age/learning gates, and a follow-up *new* preregistered native experiment compares base CE, legacy locality, BP2b locality and BP2b+minor on fresh subjects and paraphrases, preserving original BP2a results. Do not claim reduced leakage or real-world transfer from this generator-only package. Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA utility unavailable, jepa_weight=0, Redmi unmeasured, full V13 incomplete.

Exact next command after source implementation: `cd v13/code && PYTHONPATH=. python -m unittest discover -s tests -p 'test_bp2b_locality_anchors.py' -v`.
