# Run422 — WP-HX2 same-task harness comparison, blind and preregistered

2026-10-26 · owner GPT · isolated review branch `codex/run422-hx2-blind-harness-eval-20261026`, stacked on Run420/PR418. No production merge, no native STEP2 source changes or model download.

## Canonical purpose

HX1 already provides allow-listed, human-gated harness changes; HX3 stores evidence-bound experience; HX4 blinds and reverses candidate ordering. HX2 was missing the **same-task** comparison loop: one frozen reference and one proposed harness variant on exactly the same holdout tasks/seeds, no gold answer, blind preference judgement, disjoint preregistration and preserved NO_PICK. This lab implements that loop without wiring any live prompt or learning consumer.

## Lab contract

`harness_compare.preregister(tasks,diff,seed)` hashes the exact holdout task text, IDs, allow-listed single-target diff and seed. `compare(...,solver,judge,preregistration)` refuses changed inputs, duplicate IDs, train/test leakage, protected targets and unsafe baseline; calls the supplied solver twice per task with the same seed and independent deep-copied overlays, then calls HX4's two-order blind selector. Identical outputs are ties; judge position bias or errors are NO_PICK/INCONSISTENT. It reports all per-task output SHA256 and blinded commitment, paired wins/losses and exact one-sided sign-test p-value. Even a strong signal is named `PREFERENCE_SIGNAL_ONLY`, **not** accuracy, AG8 shield PASS, user approval, AGI or live learning. No model or tool call occurs inside this module.

## Proof and next

Source-only tests cover paired seed parity, blind labels, position bias, identical outputs, missing solver, protected targets, mutable overlay isolation and altered preregistration. Native evaluation on a disjoint preregistered R4 task cohort and an independent judge remains necessary. AG8 human approval and regression shield still required before HarnessLibrary.apply; live consumers remain 0. All Age/learning/STEP2/B3/Body-JEPA/Redmi gates unchanged.
