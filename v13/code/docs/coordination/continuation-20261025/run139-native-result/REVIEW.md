# Run139 — independent registered C3 challenging native cohort result (negative coverage)

2026-10-25 UTC. PR #170 exact source-under-test `151a01994f16fd9cd513f4b466c19cd295178500`. GitHub Actions run `40156088723` SUCCESS; registered Linux x86_64 native model/runner verified, 80/80 tasks completed in **21.030 seconds**. Raw artifact ID `12584329156` expires 2026-11-24; wrapper SHA256 `a9a712eacf04e44e761497f66493d043274b76b7eea7bac29d287d333face5f7`, inner JSON SHA256 `45b2843f8529d840b22cc6459841ff9719d739b819afe523df9a2be5bbf87370`, raw log SHA256 `0f8598da521f59940ce5b5c447bba8ebaf3b05ffb05a14a749c15b056699ac79`. Private Library backup `/V13_Run139_20261025/V13_RUN139_NATIVE_ARTIFACT.zip` independently materialized and SHA256 byte-identical. Independent offline recomputation confirmed every task ID, response hash, truth parser, AGE0d checker and summary.

**Results:** 80 questions, 4 correct numeric answers, 14 wrong numeric answers, **62 unparseable/unknown**. Checker supported 18/80 = **22.5%** (K3 **FAIL**). False alarms 0/4 but K1 **INSUFFICIENT** (<10 correct); wrong detected 14/14, K2 PASS under prereg threshold. Do not claim general utility or overall success. All wrong numeric answers detected in this narrow format, but 77.5% of answers abstained.

**Important new failure mechanism:** The new system prompt `Return exactly one line: The answer is N. Use digits for N. No brackets, no explanation.` was frequently copied literally by the small C3: many outputs are simply `N` or `The answer is N`. This is not evidence that the checker failed to recognize an actual numeric answer; it is a model-format/elicitation failure. Run136 had a related issue with `<number>`. Both failed prompt choices are preserved; neither cohort is modified post-hoc. Causation remains a hypothesis.

Same registered model GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` and llama.cpp b10964 archive SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. No Redmi. No model bytes in artifact.

**Next:** independently preregister a third fresh holdout with *no answer placeholder token* (e.g. `Calculate accurately. Reply with only the number, no explanation.`), fixed fresh seed/tasks, same pinned model; keep K1/K2/K3 and original negatives. Do not pool Run136+Run139 post-hoc to promote a gate. Parallel: Run140 guide fix, then exact phone ZIP.

Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, DS2 H2 FAIL, V13 INCOMPLETE; AGE0d live delivery OFF.
