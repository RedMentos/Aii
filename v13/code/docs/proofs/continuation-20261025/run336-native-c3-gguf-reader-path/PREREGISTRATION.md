# Run336 preregistration — restore pinned GGUF Python reader path in Run334 native experiment

UTC 2026-10-25. Owner: isolated Run336 workflow, preregistration, tests and proof only. Parent exact remote Run334 head `7702f98490c2773c76a3b13e41c72523ce881c7e`, PR #331. Do not modify original Run334 files or frozen 8/6/5/12 Run320 cohort, Run334 8/6/5/12 new cohort, model weights, model/source/seed hashes, selection criteria, native C++ trainer, original Canon, or any negative gates.

## Observed RED before code

Run334 exact-head GitHub Actions `40218827356` / job `121245740278` concluded FAILURE 2026-10-25 18:00:59 UTC, although all 26 source-only tests, pinned source/FP32 conversion and privacy passed. Raw artifact `12609405610`, ZIP SHA256 `9900d10ca527a5181eca39047a38002d1f1539f4f79a92a2735630a672cba0d1`; independently verified all **35/35** ZIP raw SHA manifest entries. Private backup: `/V13/checkpoints/2026-10-25/V13_Run334_Native_ThreeArm_RED_raw_sha9900d10c.zip`. Baseline 0/8 facts, 0/6 paraphrases, 10/12 retention. Native A all-token ran **two real epochs**, both 0/8 facts, 0/6 then 1/6 paraphrases, 12/12 retention, selection NONE. Before the tensor-byte audit, Run334 stopped with `ModuleNotFoundError: No module named 'gguf'`; B and C never trained. No full three-arm evidence or promotion. Preserve this original failure.

## Single isolated prerequisite change

Create a distinct `run336-native-c3-gguf-reader-path.yml` based on Run334 workflow, without editing Run334. Native invocation must prepend the **official b10964 archive's** `gguf-py` directory to `PYTHONPATH`, as already used by Run333. Add a preflight import test that requires `gguf.__file__` to reside under that exact source directory; pinned official source tar SHA256 remains `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`. Fail closed if import resolves to an unpinned pip package. No changes to the native train/evaluation Python, registered cohorts, hyperparameters, source/model hashes or original audit strictness. Run under existing serialized native concurrency group.

## Predeclared verification

1. Source-only static assertions: the new workflow differs from the Run334 workflow only by workflow identity/path trigger, reader-path preflight and native invocation `PYTHONPATH`; no changes to original native code, frozen questions or thresholds.
2. Exact-head GitHub CI: original source tests 26/26, pinned native build and model conversion, reader preflight, **all three native two-epoch arms**, original strict GGUF selected-only tensor audit and independent Run334 raw-score postflight, privacy.
3. Independently download and hash raw artifact, validate full manifest; preserve RED if any stage fails. Report all A/B/C numerators/denominators and no activation.

Claim limit: even if CI passes, this establishes only pinned Linux-native synthetic C3 experiment and strict receipts, not learned practical utility, Body-JEPA, STEP2, B3, Redmi, AG6, or V13 completion. All negative gates remain unchanged. No model weights in public artifacts.
