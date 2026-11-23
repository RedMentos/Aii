# V13 Run60 — independent original C3 seed607 native raw audit (2026-10-31 UTC)

**Owner:** GPT-6, independent review branch `assistant/v13-seed607-raw-audit-gpt6-20261031`, based on frozen PR #1400 source commit `d36fbfd169694445f6239dc39f04e933851a6c9c`. No changes to the registered source, fixture, scorer, model, seed or original workflow. This is an independent post-run audit, **not** a new experiment or a gate re-score.

## Original evidence and independent replay

- Original GitHub Actions run `41168128647` (2026-10-31 04:19–04:20 UTC) **FAILURE** at the deliberate utility/report-check gate. The preceding PINS, FIXTURE, VENV, DEPS, TEST, BOOTSTRAP, NATIVE, COMPILE, PRIVACY and DIFF stage exits are all **0**. `REPORT_CHECK_EXIT=1`, with `errors=[]` and `status=UTILITY_RED_DIAGNOSTIC`. Do not call the overall workflow GREEN.
- Original GitHub artifact `13030500333` at source head `d36fbfd169694445f6239dc39f04e933851a6c9c`; original ZIP SHA256 `5a2cc66bbc5a016dc9b23757829c75c1ac2546eca1e76d0963bd314f0f0610b0`. ZIP CRC PASS, **25/25** inner SHA256SUMS PASS, exact HEAD present, **9/9** native C3 FINAL rows, all nine processes reaped, Store closed SQLite integrity PASS, no output/tool/learning authority.
- Independent offline reimplementation of frozen numeric/strict rules from the original nine output strings, original row hashes and input hashes: **PLAIN 3/3 numeric, 2/3 strict; SOURCE_FIRST 3/3 numeric, 0/3 strict; JSON_ENVELOPE 3/3 numeric, 2/3 strict**. Exact equality to frozen report. No utility gain: SOURCE_FIRST numeric is not greater than PLAIN, so the preregistered threshold fails.
- Original first software RED `41167943923` is separate and preserved; original Run59 C6 grounding RED `41166130751` remains unchanged. These runs must not be combined or rewritten into success.
- Original ZIP and independent replay script are backed up privately at `/V13-Checkpoints/2026-10-31/Automation11-C6-and-Raw-Audit/C3_SEED607_NATIVE_UTILITY_RED_41168128647_SHA_5a2cc66b.zip` and `C3_SEED607_INDEPENDENT_AUDIT.py`. Library ZIP was re-materialized and `cmp` matched the original byte-for-byte (SHA256 identical).

## Interpretation / limitations

The pinned 350M C3 model reproduced the three numeric values in all three prompt arms, but the SOURCE_FIRST arm did not satisfy the preregistered stricter project-name-and-Euro-word criterion. This **does not** demonstrate a general C3 failure or that SOURCE_FIRST is intrinsically worse; sample size is three, the strict metric is intentionally narrow, and the frozen primary utility comparison is numeric. No posthoc currency alias expansion or other rescore is allowed to promote the original result. This is C3-only Linux-native evidence, not B1/B2 second-attempt utility, not Redmi, not a real TTY approval, and not an end-to-end proof.

**Negative gates preserved:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; Redmi unmeasured; whole-system incomplete.

## Next authorized work

Continue a **new default-OFF source-bound C6 output verification candidate** with disjoint positive/negative language fixtures, actual persisted Store source/DRAFT rechecks, explicit narrow grammar, and independent negative tests. It may improve *candidate admission* without changing the frozen seed607 scorer, original native outputs, source hashes or any delivery authority. Keep the original Run59/seed607 REDs visible; only a separately preregistered fresh native cohort could establish a measured utility change.

**Exact local replay command (private ZIP already backed up):** `python /mnt/data/audit_seed607.py` after restoring the two named private Library files to those paths; expected frozen audit status `UTILITY_RED_DIAGNOSTIC`, not GREEN. **Prerequisite for new candidate:** read the current head and original C6 source/fixtures, use a separate review branch and software CI, then test against real SQLite. No Redmi/native re-run required for this read-only audit.
