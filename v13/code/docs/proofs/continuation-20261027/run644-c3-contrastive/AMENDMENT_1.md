# Run644 amendment 1 — workflow source-binding typo found before native measurement

Independent inspection of first native workflow commit `9c5e45e4fc6bdeeadd2b30a423d05496e34ca549` found that automated reuse of the prior Run642 workflow incorrectly renamed the **historical Run639** cohort path to `run642-c3-kl-anchor/COHORT.json` (nonexistent). The source preflight will fail; this is a workflow path error, not a native model/utility result. Do not alter new Run644 cohort, model pins, original Run642 adapter/proofs or acceptance.

**Prospective narrow correction:** restore the original `run639-c3-kl-anchor/COHORT.json` SHA `ccec34634714b760b6cba6ce626536928f229ed3` and add an independent `run642-c3-protocol-locality/COHORT.json` SHA `249d4be0e0663cccf5d1165347fa37c0db924791` check. Preserve any resulting original RED Actions run and raw logs, then execute corrected exact source. Native training must remain serialized.
