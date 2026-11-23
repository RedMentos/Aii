# WP-BP2b source-only review checkpoint · 2026-10-27

## State and lineage
- Owner: automation11 BP2b locality; separate review-only PR #705, branch `codex/automation11-bp2b-locality-generator-20261027`, child of PR #703 exact `89055e5b5542336bd24f521382a3fd5cd1d8c616` (Claude BJ1/BP2a source included). main untouched.
- Original prereg before implementation: `f2b0c3fcc9f1501f84063312d10d39934b566770`. Adversarial prereg before RED tests: `09dbd006e17f05033b60662e5e21f9f86921176a`.
- Source package: `v13/code/v13/locality_anchors.py`, opt-in `BodyJepaTrainer._locality_for`, test suite and Actions workflow. `locality_policy='bp2b'` must be explicitly selected; legacy remains the default, with original config/dataset hash unchanged. No training run or runtime activation.

## Closed raw evidence
1. Initial software Actions `40501008646`, exact head `631c532f6e01db579d2b29ac39ad86c3a10fef2d`: **6/6 PASS**, compile0, privacy CLEAN. Original raw ZIP SHA256 `1ba68d762d5b7effdde8056213112f63af4f2179e8c82eeb02e848bd48f0ba8a`, CRC PASS; privately backed up and re-materialized byte-exact.
2. Prospective counterexamples Actions `40501233597`, exact head `f4e8628e35c98245f667a6ea1a23521172946a4a`: **8 tests, 2 FAIL**, compile0, privacy CLEAN. Lowercase free `i` and single-quoted literal `'my cat'` were incorrectly rewritten. Original RED raw ZIP SHA256 `716da7614976964f68c999dcb03e57d59f35f9369dc20062d660c9dc28b52d98`, CRC PASS, private Library backup retained.
3. Narrow source fix `2cd891165def1d6762b386bf92c76bb6d698764e`, Actions `40501390689`: **8/8 PASS**, compile0, privacy CLEAN, source blob `1957e8a787324df51eab9ebfdf476e01190c908c`, BodyJepa blob `3aa603436927dcb03bb33ab617331350caea94ae`. Original GREEN raw ZIP SHA256 `1cbf7013d0f0243c99d5528238db146f4fbbbfd8de636eb7eb02e40811b7e153`, CRC PASS; private Library backup re-materialized byte-exact. Exact original `UNIT_EXIT=0`, `COMPILE_EXIT=0`, `PRIVACY_EXIT=0`.
- Private backups: `/V13-Checkpoints/2026-10-27/BP2b-Locality-Generator/` (not the rejected anyone-writable Drive location).
- CI command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_locality_anchors`.

## Meaning and limitations
- Software shows 19 English grammar examples, all original 24 BP2a source questions producing 48 unique question-only anchors, bounded deterministic generation, no answer/target use, reserved-subject exclusion, fail-closed malformed input, legacy vs opt-in behavior.
- No fp32/Q4 native BP2b training, no heldout cross-subject/paraphrase utility, no Redmi data, no approval to activate learning. New locality prompts could suppress independently true facts about a substituted subject; contextual conflict filtering and fresh source-disjoint evaluation are required before practical adoption.
- Negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1_NO_SIGNAL / jepa_weight=0, no whole-system acceptance. Original BP2a_PASS is narrow fp32 synthetic-fact evidence only.

## Next authorized package
- Pre-register a **new** heldout transfer cohort with unseen people/subjects and genuinely different paraphrases, separate train vs evaluation prompts and target metadata. Build an explicit optional `--prepare-only` software fixture, then run a serialized native comparison only after confirming the current heavy-job owner is free.
- Compare CE legacy, BP2b locality, BP2b+minor, and existing manual-locality reference on identical seeds, weights, train facts, probes and decode settings. Include independent scoring, false-positive leakage controls, retention and Q4 adapter path before any learning gate.
- Exact next read/command: `git fetch origin && git checkout codex/automation11-bp2b-locality-generator-20261027 && cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_locality_anchors`. Recheck remote PR #705 head before stacking. No active native job owned by this package.
