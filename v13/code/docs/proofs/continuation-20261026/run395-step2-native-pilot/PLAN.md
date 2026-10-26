# Run395 — isolated Linux-native execution of frozen Run394 pilot (2026-10-26)

**Ownership:** scheduled GPT continuation; only `.github/workflows/run395-step2-native-pilot.yml` and `v13/code/docs/proofs/continuation-20261026/run395-step2-native-pilot/**`. No edits to Run394 fixture/runner, registered Z2/Z2b/Z2c, Canon, runtime or model catalog. This PLAN is committed **before** native execution.

**Parent:** Run394 PR #389, exact initial SHA `f7d13afdd647be9d6e92b5a83061f9336f5d4d7b`, stacked review branch, not production main. Run394 source-only fixtures 7/7 PASS; **native pilot NOT YET RUN** at plan time.

**Hypothesis and contrast:** Test source-disjoint Alder (long split) and Delta (current revision), seed 20, O two-body quote-pointer OFF, P two-body pointer ON, S one-model/two-state pointer ON. Seven unchanged variants per arm; 2 × 3 × 7 = **42 actual native consumer rows**, including all failures. The source-only Run394 preregistration already froze these cases, model hashes, arms and seed. No substitutions, redefinitions or posthoc thresholds.

**Method:** Exact-head GitHub Actions Linux x86_64 CPU; isolated Python venv with pinned `numpy==2.3.5`, `prompt-toolkit==3.0.52`; `python -m v13.bootstrap` installs only registered public model files and native b10964 runner with SHA256 checks; native inference serially (single job, concurrency lock). Run source-only Run394 tests and fixture manifest before models. Run `scripts/run394_step2_fresh.py --installed-home ... --work ... --pilot --arms O P S --seeds 20` under explicit timeout. Preserve runner exit, host memory/disk, hashes, preregistration, partial progress, raw reports and failed attempts. Do not upload model/runner weights, private data, databases, or unredacted environment. Every uploaded report is synthetic fixture content only. Verify artifact CRC/hash separately after job.

**Acceptance of this package:** CI exact-head test green, bootstrap verified, all 42 native rows actually present, 14 rows per arm with the frozen seven variants, unchanged installed model artifacts, no wrong committed tool decisions, and privacy CLEAN. Any failure is recorded RED/INCOMPLETE; an O/P/S utility difference is exploratory pilot evidence, not STEP2 promotion.

**Negative gates:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA and jepa_weight=0; Age0 approval/learning unchanged; no Redmi/phone proof; Run389 full suite RED; whole-system V13 incomplete.

**Next:** Audit native raw artifact/row hashes and paired source access; then preregistered 378-row full cohort only after reviewing pilot structural validity and runtime cost. Independent full-suite SourceHandoff 70 errors remain a separate unresolved package.
