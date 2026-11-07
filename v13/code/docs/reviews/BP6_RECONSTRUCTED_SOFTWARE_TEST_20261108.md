# BP6 isolated reconstructed software test — 2026-11-08

Owner: GPT, PR #1593 (head `9b0b90dfc9ba47522fde8d629b82412b48046a2b`), base #1592. **This is not a byte-identical checkout test.**

## Actual execution
Direct container network probe: `urllib.request.urlopen('https://raw.githubusercontent.com/...')` -> `URLError: Temporary failure in name resolution`. GitHub connector remains fully operational.

Reconstructed `v13.agi.metaeff` and the two relevant test modules from the fetched source in an isolated local directory, then ran `python -m unittest discover -s tests -v`. Result: **10 tests run, 10 passed, 0 skips, 0 failures, 0 errors** in 0.024s. Covered tie invariance, invalid bin/permutation/bootstrap counts, abstention confidence/cost/step guards and expected payoff. This is an independent behavior check, **not** a claim that the exact remote bytes or the full repository passed. Local reconstruction git blob `25801ef1741ed06afc1692d6415bae528fc0d70e` differs from remote source blob `d5734720008a23006a9be7718cf2c9558f13bf2f` due to manual reconstruction/formatting; do not conflate them.

## Next
Run exact remote source+tests in a full checkout, consumer suite, privacy scan, independent counterexamples, and #1586/#1589/#1592/#1593 dependency review before integration. Do not change frozen cohorts or gate statuses. STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0 RECORD_ONLY, whole-system INCOMPLETE unchanged. No native/Redmi proof.
