# Run565 — original 126-row STEP2 evidence completeness / abstention diagnosis

Date 2026-10-26. Exploratory posthoc analysis, preregistration `b75ac5a28a806fb7239006a6142aba84e43bc3cb` committed before diagnostic source. No new native inference or model download. Review branch PR #563; no main merge.

## Verified original data and checks

Original safe artifacts (already independently source/oracle-audited in Runs559,560,563):
- Run507 FUTURE_001 artifact `12644358345`, SHA256 `406c5e6467c8666e257be73842c3bbf0b5ab53c73d7b46fb7e7cc155beb6677b`.
- Run557 FUTURE_002 artifact `12665895129`, SHA256 `ecd1ece00a2e82396bbd716b4fab93c84efe81ce60d9e853b8b450a437d4eb03`.
- Run561 FUTURE_003 artifact `12666848624`, SHA256 `503a1a4c0ad900f71758b42cfda40ff75b440240db7d469f06fe8b976877ed77`.

Run565 pinned Actions `40363093211` at exact source head `5a0919868d742e7cb878cc4ac2b3ec0c215a6981`: SUCCESS, 7/7 adversarial software tests, original three ZIP SHA verified, 126/126 original rows (7 arms ×18), exact stage keys and source-quote substrings checked, privacy CLEAN, all four exit receipts 0. SHA-closed artifact `12669935636`, ZIP SHA256 `8a186fbba190882218a2b9bb8b890c22848093b3262c2fc828c76171435eb815`, 12/12 manifest entries verified, report SHA256 `1204ed8ad5cc28ca545f3c3e3cceae43aa8f881b6a170c430da2b4384cf1c3ce`. Original artifact preserved privately in `/V13-Checkpoints/2026-10-26/Run565/`. Two superseded interim source runs were RED from deliberately stale exact blob pins during edits; preserved in Actions history, not relabeled GREEN.

## Actual finding

**All 126 recorded C3 consumer actions are `UNKNOWN`** across all seven variants and three original frozen FUTURE batches. The consumer was instructed to abstain when required historical rules were unavailable; `UNKNOWN` is therefore not itself a wrong committed action. The original utility score still awards correct partial cost/day/local fields, so a nonzero 12-field utility score is not proof of successful option choice.

Conservative **complete exact-input coverage** (three decision rules and two full supplier-option sentences, each present in current source or exactly quoted from source-verified B1/B2 offers) is **0/126**. For the primary `both_exact` arm, 18/18 actions UNKNOWN, 2/18 have all three rules available, 4/18 have both full option sentences available, and 0/18 have all five simultaneously. The same conservative all-five count is zero in the other six arms. Earlier Run508 observed B2 historical local-only quote absence; separate Run527 fresh 60-offer RULE_FOCUS vs BASE comparison had only a +2/24 paired all-rule quote advantage, below its preregistered threshold. These are different cohorts, not a pooled efficacy estimate.

**Important configuration boundary:** these three frozen consumer batches use the preregistered `LEGACY_QUOTE_PATH` / C3 decision setup. The current `v13/config.py` already defaults to `b2_quote_select='pointer'`, `offer_quote_context_chars=200`, `b1_recent_source_chars=600`, `eligibility_reader='fixed'`, and `tool_answer_first=True` per the 2026-10-21 user decision. Therefore this diagnosis **does not establish that the current live/default path has the same bottleneck** and is not a request to reimplement an already present pointer/fixed reader. The next useful controlled experiment must test current-path end-to-end actual FINAL decisions, source lineage, latency, abstention and wrong commits against the frozen legacy control on a new disjoint cohort. Keep both cohorts' original hashes unchanged.

This is **not** a proof that the model cannot reason with complete information: the exact-sentence criterion may miss semantically sufficient fragmented quotations, and no controlled complete-input consumer arm was executed here. It is evidence of an upstream *source-to-consumer transport bottleneck*, not grounds to force a guess. The existing fixed-reader / quote-pointer candidate (WP-Z2d) is a potential separately preregistered intervention; evaluate with full original source lineage, wrong-commit/abstention and b1-only/dual ablations on new disjoint tasks, without altering or retroactively rescoring the frozen cohort.

## Scope and continuation

The frozen Run491/500/504 sources, models, seeds, runner, Canon, learning and age rights were not changed. Native evidence remains from original Run507/557/561 Linux Actions only; Run565 is software/offline. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, `V13=INCOMPLETE`. Separate Run562 FUTURE_004 native owner is active and serialized; do not compete or rerun it. Next after its completion: independent original raw/safe FUTURE_004 replay per Run564 prereg, then another disjoint frozen batch only after GREEN audit and idle native owner. The full coupled V13 remains required.
