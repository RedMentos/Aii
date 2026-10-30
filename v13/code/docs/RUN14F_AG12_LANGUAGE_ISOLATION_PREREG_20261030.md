# Run14F prereg — AG12 English-first/German-later language-isolated evaluation state (2026-10-30)

Owner GPT-6 scheduled continuation. Review-only child of Run14E `b2e8cc28cf05538f81cc5fd913c9f216c746d8bd`. This is a substantive language-transfer prerequisite from explicit user decision 2026-10-09: English first, German later as a learning/transfer test. No native model execution, model/source/seed/cohort/scorer changes, no Age authority.

## Observed current failure
`GeneralityEval(store,lang='en')` and `GeneralityEval(store,lang='de')` share `KEY='G12_GENERALITY_EVAL'` and StateBox. Constructing German overwrites the suite hash/holdout, resets `last_items`, and mixes English/German `runs`, curves and forgetting baselines. This prevents trustworthy future cross-language transfer measurement and can silently invalidate the English default. The English source suite and hash must stay byte-identical.

## Fixed acceptance
Preserve exact existing English `KEY`, `REVISION`, suite hash, seed and serialized state schema. Use a separate persistent `G12_GENERALITY_EVAL_DE` StateBox key only when `lang='de'`; do not change `build_suite`, `calibration`, `summarize`, training guards, existing English datasets or Runtime default. Add read-only language identifier to `report()['suite']` for unambiguous operator/diagnostic interpretation; `run` already records suite hash. Test-first real SQLite Store: create English and German evals on same Store, run oracle English and null German, verify separate run histories/curves/holdout hashes, both survive Runtime close/reopen, German `guard_training` rejects its own unseen prompts and English guard remains intact. The default English suite hash must match pre-patch. Invalid confidence containment from Run14B and AG9 from Run14A remain unchanged. No implicit German evaluation, model calls, scheduling, or training activation. German results are **diagnostic only**, not proof that V13 learned German.

Capture original test-first RED and candidate GREEN via pinned isolated GitHub Actions, compile, privacy, CRC/inner hashes, private backup; preserve any new full-suite RED. No STEP2/B3/Body-JEPA/jepa_weight/Redmi or whole-system promotion.

Next command: commit real Store bilingual test first, run original RED against unmodified AG12 language key, patch isolated state key and report language, run focused GREEN and existing G12Eval, verify raw and remote bytes, checkpoint. Later separate operator/scheduler German transfer run requires new prereg and genuine model evidence.
