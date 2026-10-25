# Run151 prereg correction v2 — BEFORE any native launch

The first preregistration commit `7d984144e24bd86d75f3ea9627adda1dfe5bfe24` contains a generator/seed mismatch: the provisional task SHA was computed with a slightly different local generator (division operands 2..40 rather than original Run147 2..30, and a different draw sequence). This was caught during independent source comparison **before code upload or any native execution**. The first prereg remains in Git history and is NOT a measured cohort.

**Binding correction:** use the **exact Run147 `tasks()` algorithm** (including `EXCLUDED_PRIOR`), with 24 rather than 8 per operation × phrasing stratum. Fixed seed **15132**, 288 rows, zero exact question overlap with Run147 96 rows, canonical JSON SHA-256 **`9418de94428bb51a42d4d5e292ab9f5ef5e94acea61382d3f88c1694a7712144`**. This v2 correction supersedes only the provisional seed/hash in PREREG.md; all model/runner/prompt hashes, thresholds, authority and gates stay unchanged.

No native job is authorized until source asserts this corrected task digest and the workflow references this correction. Any future native output is bound to v2, never to the provisional v1 seed/hash. Preserve both prereg records and this correction in the final report.
