# P0X 600-call C3 exact/single/foreign source-ablation — closed Linux-native evidence (2026-10-29)

Owner: GPT-6 isolated review PR #1066. Original prospective registration committed **before the baseline result** at `6f76921f434b769394958c9d05768629e471a060` (blob `27074170ff9e6474e3e181afbd648005ca50a22c`). Frozen P0X fixture SHA256 `ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e`. Original C3-only baseline run `40840179920` verified raw SHA `79be6584d465b0fc3ccd33294d882a41bb1990920f3098ed39203b7aef7d18a1` and score SHA `7c603158c6d821592d5777d46bb4723503f74c063c5c30fcc0f72fe2720b836e`, exact 50/150, oracle headroom 100>=15. No source/model/seed/Canon change.

## Native GREEN, independent verification

- GitHub Actions run `40841374171`, exact workflow head `4a98235e7e17c0dfd0e9a9cc3cb8478f99d9abac`, artifact `12883820129`, original ZIP SHA256 `be222ad4790c6ce92225d9cda37fac3a23cc5cbcd8316231e22bd1feb1a88d4f`.
- Independently downloaded original ZIP: CRC CLEAN, **96/96 internal SHA256SUMS**, **14/14 stage exits 0**, three exact parent artifacts rehashed, 8 focused tests PASS, privacy CLEAN. **600/600 real Linux x86_64 C3 calls FINAL** (150 per arm), frozen C3 GGUF and llama-server SHA unchanged before/after, process reaped, no adapters/training/weight updates.
- Raw SHA256 `41712a41467349069fd8af0b418624636bc3ab122604c611f95d3745ba188332`; score SHA256 `c03e2ad145b17a5aa34f0552db6944516b1310ca14861d83e05ba98bdc5767f7`; comparison SHA256 `85a808cc106d509bbc64b96a70874a282596550ef7716d215985a6c46e22e675`. Permitted private Library backup `/V13/RawEvidence/P0X_40841374171_600native_exact_head_raw.zip` rematerialized and byte-verified against original ZIP SHA.

## Preregistered descriptive result, same 150 heldout tasks

| C3 source view | Exact | Wrong committed | A / B / NONE outputs |
| --- | ---: | ---: | --- |
| C3-only frozen baseline | 50/150 | 100/150 | 0 / 0 / 150 |
| B1 exact only | 51/150 | 99/150 | 0 / 4 / 146 |
| B2 exact only | 50/150 | 100/150 | 0 / 0 / 150 |
| Both B1+B2 exact | **52/150** | **98/150** | 0 / 62 / 88 |
| B2 + foreign B1 | 50/150 | 100/150 | 0 / 0 / 150 |

All 600 source-arm outputs were parseable JSON; UNKNOWN 0, unparseable 0. Both-exact improves **+2/150** vs frozen C3-only baseline, far below preregistered **+15/150**. Both-exact exceeds each single-source arm numerically, but the improvement threshold fails. **No A was ever selected.** Foreign-source arm still committed wrong decisions on 100/150. Thus no reliable semantic complementary-utility proof for STEP2. These are public synthetic diagnostic tasks, not blind real-world holdout or a statistical generalization claim.

## Interpretation and next canonical package

The evidence distinguishes a format confound (HB1b JSON/plain negative) from C3 source-composition failure (P0X both-exact +2). Do not repeat the same six tasks, rewrite source pins, cherry-pick score or promote STEP2. Next substantive work should target a **source-dependent C3 receiver** using the existing `v13/lora_trainer.py` and canonical LP3 causal-state path with disjoint training data, matched no-source/single-source/foreign controls, and QAD GGUF ↔ HF master parity proof. `P2_C3_RECEIVER_TRAINING_PRIMARY_SOURCE_GATE.md` documents official LiquidAI/Transformers/PEFT references and existing V13 trainer/AG6 approval; supervised adapter training is only a baseline and cannot replace LP3 JEPA. Other organs (JEF/C2, B1/B2 learning, Context OS, Callosum, Dream/Sleep) remain required and may proceed independently. Redmi TESTEN.sh sustained device evidence still missing.

**Gates remain:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE, Redmi unmeasured. No production merge, no AGI or whole-system claim.
