# STEP2 native vertical semantic-gap audit — prereg 2026-10-30

Exact parent `3efc8da2b1b74ecb62992c4efafc55391c2c2924`, built on current review chain PRs #1192–#1194. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. The original real Linux-native Age0 proof is GitHub Actions run **40987192595**, artifact **12947896111**, exact ZIP SHA256 `ad961abb8eea8d567f58cbc4f1fed67f7a79920e36564bb5527b7ea08fa4f3f7`, CRC clean, 27/27 inner hashes, private backup in `/V13-Checkpoints/2026-10-30/Run11-CurrentChain-Age0-Connected/`.

## Fixed hypothesis and measurement
Structural `VERTICAL_CHECKS_PASS` is not semantic STEP2 utility. Score the **actual persisted FINAL text** of the existing frozen STEP12 budget-comparison turn, without generating or editing it. Frozen fixture (from `v13/proofs.py`): 120 Euro budget; Rot 80 Euro, 2 days; Blau 110 Euro, 1 day; both local; user explicitly asks **budget remainders** and short tradeoff. The two exact required remainders are **40 Euro for Rot** and **10 Euro for Blau**. A conservative scorer counts a remainder only when the exact amount is bound to the corresponding option in the output, allowing English/German labels and currency spellings. Mere copying of 120, 80, 110 is not a correct remainder. Reject any artifact with wrong ZIP digest, CRC, inner SHA256SUMS, HEAD, proof schema, missing FINAL output or changed native fixture source hash.

Predeclare: `correct_remainders / 2`; do not score freeform tradeoff as objective truth from one response. Baseline/control absent: `comparative_utility_proven=false` regardless of result. This is an **offline real-native-output diagnostic**, NOT a new native call, not a full paired STEP2 study, not a training or gate result. Retain raw negative findings. A passing software test of the scorer does not turn a failed semantic result green.

## Execution and acceptance
- Add standalone read-only scorer and synthetic positive/negative tests, no Runtime wiring or model/seed/cohort changes.
- Run scorer against exact original raw ZIP, independently record JSON result, code SHA and hashes; keep negative score if observed.
- Focused CI tests and private backup; original full-suite historical Run34/Run37 errors remain RED.
- Next actual utility experiment: fresh preregistered paired no-body/one-body/both with disjoint fixed scorer, same source, native model and seeds. No STEP2/B3/Body-JEPA/JEPA/Age/whole-system promotion from this diagnostic.
