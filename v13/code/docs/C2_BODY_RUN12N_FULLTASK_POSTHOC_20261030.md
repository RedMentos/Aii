# Run12N full-task posthoc diagnostic — original raw, no gate (2026-10-30)

Review-only child of PR #1274, original real Linux-native ZIP from Run12N `41061289187`, artifact `12979551173`, SHA256 `c058f33d1055d838000cc31e27b6e6ba6d37f86caa8e7b0d15a643672d44c447`, 60/60 inner hashes, 16 raw/preclose and 4 C2 strict. The preregistered numeric scorer and original RED utility decision are unchanged.

## What this separate exploratory diagnostic measures

The original prompt requests **both** numeric budget remainders **and** which option finishes sooner. The frozen Run11V primary metric only awards the two numeric remainders (out of 2). New standalone stdlib script `scripts/c2_body_run12n_fulltask_readonly.py` requires exact original ZIP SHA256, CRC, complete SHA256SUMS and row identities, then classifies **explicit** faster-choice claims with conservative lexical patterns (CORRECT/WRONG/ABSTAIN/CONTRADICTORY). It does not infer unstated answers or override original scorer. Source and complete 16-row aggregate are in `docs/RUN12N_FULLTASK_POSTHOC_REPORT_20261030.json`.

On the 16 original Linux-native outputs, numeric points (out of 8 per arm) and explicit faster-choice status (out of four turns per arm):

| Arm | Numeric | Faster correct | Faster wrong | Abstain | Strict full answer (both numeric + faster) |
|---|---:|---:|---:|---:|---:|
| C3 only | 0/8 | 3/4 | 1/4 | 0 | 0/4 |
| B1 only | 3/8 | 0/4 | 4/4 | 0 | 0/4 |
| B2 only | 4/8 | 0/4 | 2/4 | 2/4 | 0/4 |
| C2 native-auto | 1/8 | 0/4 | 4/4 | 0 | 0/4 |

All values are **posthoc exploratory**, not a registered STEP2 utility score. A task-specific deterministic exact subtraction + `min(days)` baseline solves 4/4 source cases in principle; it is **not** an LLM learning baseline or generalization proof. Key failure: B1/B2 can compute remainders but often claim the slower option finishes sooner; native-auto selected `both` 3/4 and inherited B1-like incorrect outputs. This is a concrete whole-task utility bottleneck, not evidence that all models lack general reasoning.

Local standalone `python -m unittest -v test_c2_body_run12n_fulltask_readonly.py` with `V13_RUN12N_ORIGINAL_ZIP` set to the original downloaded ZIP: **5/5 PASS**, including original hash/CRC/60-hash and exact aggregate. GitHub Actions read-only cross-run audit `41062417637` launched at exact source HEAD `006074d8550a7d6adbebc84b7a35a861730f2c9d`; original attempt RED at HEAD `006074d8550a7d6adbebc84b7a35a861730f2c9d` (literal escaped-newline syntax in test only; original ZIP download and report comparison PASS). Original RED ZIP artifact `12980891062` SHA256 `7ef359e0498921ef9bfa1a7a007747838bcf7c628cce6521328de310955c5fef`, 20/20 hashes, preserved in private Library. Corrected source-only Actions `41062548821` SUCCESS at exact tested HEAD `36bee6aaacd584eb64a8c334d50ae7c59135a1c8`: 5/5 tests including real original ZIP, 8/8 stage exits 0, exact source pins and report equality, privacy CLEAN. Original corrected audit ZIP artifact `12981340178`, SHA256 `fbf864e650f81b1dedfb539cedef0a2bf2cb80b7a8aa003c681d1d77622e25a0`, CRC CLEAN, 20/20 inner hashes. Private Library copy re-materialized byte-exact. The script/report and test source were privately checkpointed in ChatGPT Library `/V13-Checkpoints/2026-10-30/Run12N-ObserverOff/`.

Limitations: lexical explicit-claim parser is not a calibrated semantic scorer; complex negation, quotes and implicit comparisons may be missed or misclassified. The 16 source cases are not new heldout data for any new policy. No gate promotion, no model training, no route change.

Next exact command: **preregister a new disjoint** full-task comparison with numeric+faster scoring, task-specific deterministic no-model baseline, C3/B1/B2/C2-auto controls and a source-bound contradiction veto. Do not retune or rescore Run12N as if prospective. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole V13 incomplete.
