# Run30 actual-original-raw auditor CI — prereg amendment (2026-10-28)

**Owner:** Run30 independent review child, no native model dispatch. The original Run26 Actions `40715223545` artifact id `12826794972` is a fixed public-repository artifact with raw ZIP SHA256 `989abb8ac7b8fcd91ec047f97b735c9c8f84342e49251855b3375f7b3519762b`. Independently verified original CRC, 26/26 inner SHA and 7/7 row SHA; private Library backup byte-identical.

**Purpose:** A separate GitHub Actions read-only job downloads the *same original* ZIP through GitHub's Actions artifact endpoint using only scoped `actions:read` and `contents:read`, verifies exact archive SHA and invokes the new stdlib `run30_native_keldara_aggregate_audit.py` against it. Upload only aggregate JSON and status/hashes, never raw source/user/model text or original ZIP. If download, SHA or auditor fails, preserve RED status and log; no model download, no paid provisioning, no native run, no gate promotion. This supplements (does not replace) source-only full-suite CI and local original-byte audit.

**Expected aggregate:** Seven variants, `both_exact_minus_b1_only=0.0`, common failures `project,action,A.remaining,B.remaining`, no exact variants, all negative gates unchanged. Next command: `python3 v13/code/scripts/run30_native_keldara_aggregate_audit.py <original-run26-private-zip>`.
