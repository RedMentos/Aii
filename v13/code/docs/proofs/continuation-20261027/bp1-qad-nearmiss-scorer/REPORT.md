# BP1 source-bound near-miss/retention scorer — software GREEN (2026-10-27)

Owner: GPT-6 automation11. Preregistered scoring contract committed at `1440b0ee91a0622fa77c1c1971820ea5dd58beac` **before** scorer implementation `219daff269b669efb0bf629b46bbd6ae727da206`, tests `f75aedf95882014ad3e911b386310f56b0b9d2d1` and Actions run. Review-only child of PR #692 at `e894d7670cf56549d1fffed6441ea5e14ab05541`. Original 25-row train/11 heldout, QAD FP32/Q4, seed13, b10964 runner, Age gates and runtime untouched.

**Implemented:** `v13/code/scripts/bp1_qad_nearmiss_score.py` checks exact registered 16 near-miss and 8 retention source files + manifest SHA, 48 unique base/candidate response records, source and prompt hashes, no extra target fields, exact quote-supported source answer, malformed/duplicate/nonfinite JSON, unsupported commitments, abstentions, wrong-hint-answer counts, exact case-sensitive retention responses, offer-vs-no_offer and candidate-vs-base paired wins/losses/ties. Outputs software-only `SCORES.json` with `model_utility_proven=false` and all negative gates. **A response equal to the false B2 hint is a matching wrong answer, not by itself proof of causal hint-following**; compare offer vs no_offer and native controls before making causal claims.

**Closed software evidence:** Actions [40487305415](https://github.com/RedMentos/Aii/actions/runs/40487305415) at `38ea4227ad58a8f2e32b5f59a566a559e3c21498`: **21/21 tests PASS** (9 generator + 12 scorer), compile0, privacy CLEAN. Original raw artifact `12724759831`, ZIP SHA256 `13ade4804fe3981b6abb293d5a526eb5ec77ffe22af96127d6441cd620c6fd5e`, 1,806 bytes, 8 members, CRC PASS, UNIT/COMPILE/PRIVACY exits0. Original ZIP privately backed up in `/V13-Checkpoints/2026-10-27/BP1-QAD-Native-Verified-20261027/NEARMISS-SCORER-40487305415-ORIGINAL.zip`, re-materialized and SHA verified byte-identical.

**Next exact software command** after a separately preregistered 48-response native collector exists:
```bash
python3 v13/code/scripts/bp1_qad_nearmiss_score.py --controls /path/to/exact-controls --predictions /path/to/48-source-bound-native-predictions.jsonl --out /path/to/new-empty-score-dir
```
First independently close original 44-response V2 Actions `40486038454`; do not run competing heavy jobs. No native predictions for these new controls yet, no retention or near-miss utility evidence, no Redmi proof, no production authority. STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, V13 incomplete.
