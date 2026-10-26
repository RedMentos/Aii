# Run614 — new independent native B1/B2 paraphrase cohort, frozen before inference

2026-10-26 UTC. Owner GPT automation11, child of verified Run613 PR608 exact `d95656b848c2eaaa054d39560435f4545d8539ef`. **This cohort is distinct from Run608**; all 80 source texts, labels, topics and train/test split were committed at `ef33155cf6f23610b4e12b7d4a0ce6557ee125d4` before any new native model call. Frozen cohort blob `7068267d41a1719abea3a54c84b1d0223444df1d`, schema `V13_RUN614_INDEPENDENT_PARAPHRASE_COHORT_V1`, seed 2026102614. Source statements are original synthetic mini-events, not externally validated facts.

## Motivation, scope and fixed source

Run608 original native 20 heldout prompts showed B2-only cosine .65 and B1-only .55 (posthoc Run613) while mapped B1→B2 .25, lexical .30, 50/50 fusion .40. This Run614 tests whether within-body paraphrase structure survives **new topics, facts and paraphrases**. No source from Run608 is replaced, re-labeled, used as Run614 training, or promoted.

40 new fact pairs A/B, 8 topics×5 facts×2 variants. Train 60 prompts in architecture/ecology/navigation/chemistry/history/biology; heldout 20 in literature/geography. Both A/B variants of a fact stay in the same topic split. Exact pinned original Run608 native runner/model revisions, SHA256 and tap IDs are reused read-only: B1 LFM2 2048 dimensions and B2 Qwen 1024. No parameter updates, training, receiver injection, native bridge or cloud model substitutions.

## Frozen analyses and gates

1. Capture exactly one native read-only final hidden-state vector per source prompt per body. Verify prompt SHA, model and runner SHA, exact native receipts, dimensions and finite values; save original raw states and every failure. No retry that changes cohort/seed/source/model. Use serialized native concurrency group; do not run alongside other active owners.
2. On 20 heldout queries, retrieve the paired opposite paraphrase among the 19 nonself heldout candidates. Report top1/MRR for lexical Jaccard, B1-only cosine, B2-only cosine, original-style ridge B1→B2 mapped cosine (alpha=1 trained only on 60), and fixed 50/50 per-row minmax lexical+mapped fusion. Deterministic first-index tie break, no parameter tuning. For cross-body mapped and fusion, 200 fixed-seed train-label permutations. For B2-only, 200 fixed-seed random bijective opposite-label permutations excluding self.
3. **Within-body B2 replication proxy** only if B2-only top1 >=.55, exceeds lexical by >=.15, and B2 label-permutation p<=.05. **Cross-body exploratory proxy** only if mapped OR fusion exceeds best(B1-only,B2-only,lexical) by >=.10 and its train-shuffle p<=.05. Report all metrics and failures even when both fail. These are synthetic retrieval proxies, not end-to-end utility or B3/JEPA/learning gates.
4. Independent CI numeric recomputation, adversarial software fixtures, source/Canon/model hashes, privacy scan and SHA-closed raw artifact. Distinguish new Linux-native B1/B2 evidence from original Run608, synthetic software and Redmi.
5. All original negative gates stay: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; V13 INCOMPLETE; canonical/user full scope false. No Age/approval/learning changes.

Owned new `scripts/run614_independent_native_paraphrase.py`, `tests/test_run614_independent_native_paraphrase.py`, new proof and inherited source-only/native workflow review-branch copy. Model registry, Canon, original Run608 source/cohort/seed/receipts unchanged.

Next command (isolated Linux-native, when no active owner): `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python scripts/run614_independent_native_paraphrase.py --home <pinned-bootstrapped-home> --out <report.json> --states <states.npz>`.
