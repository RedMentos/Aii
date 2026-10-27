# Independent BP2b Linux-native first-step receipt audit + RSS clock review — 2026-10-27

**Review-only child of PR #725 exact `a39d1d3cd62f9ddafc91b33b20e020ae49d3b2b3`**. The original 30-step seed41 legacy timeout remains failed; this is a *different, preregistered one-step diagnostic*, not a replacement. No changes to original source/model/seed hashes, registered cohorts or gates.

## Independently downloaded and checked raw artifact

- Native GitHub Actions run **40520099854**, exact executable commit `b4892519705af0099fc83704c368d53f4b3027b9`; artifact ID **12741617111**, ZIP SHA256 **`d684c7f2944d94c0da89b875cb3b51a718aa27a130e5f862a67b61fb97a4d02b`**.
- ZIP CRC and unique member names passed. Independently parsed `MASTER_PREFLIGHT.json`, `STARTED.json`, `RESULT.json`, `RSS.jsonl`, `NATIVE_RAW.log` and all five exit receipts. **SOURCE/ENV/NATIVE/RECEIPT/PRIVACY exits were all 0**.
- Official FP32 master `LiquidAI/LFM2.5-1.2B-Instruct` exact revision `8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf`, expected SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a`: preflight `FULL_FILE_HASH_PASS`. This is source verification, not a model-quality result.
- `RESULT.json`: `FIRST_STEP_COMMITTED`, `step=1`, `LINUX_NATIVE_DIAGNOSTIC`, checkpoint SHA256 `54123700592999b6441036b69ceae66210cc713ef1b138a8ddd459458f0b51d5`, source SHA256 `7af8de5f8c052c2e008f517cc3b287e7d39d803d30c8efbaea1d9b2dacc08155`, 281.524 s from probe timer to first checkpoint, sampled peak RSS **7,627,480 KiB (7.274 GiB)**. 57 RSS samples, nondecreasing timestamps, maximum agrees with receipt, raw native log repeats checkpoint receipt. No model/optimizer tensors in public ZIP.
- Frozen reference still 30 steps; diagnostic config deliberately 1 step; `jepa_weight=0`, Age authority 0. No heldout, retention, B1/B2 utility or JEPA proof. No Redmi measurement. Peak RSS is Linux FP32 diagnostic only; it does **not** establish Q4 Android footprint.

## Confirmed source/evidence defect

Original `ResourceSamples._loop` writes `'elapsed_monotonic_s': round(time.monotonic(), 3)`, i.e. **absolute monotonic host clock**, not elapsed since sampler start. Actual archived first/last fields are **114.633** and **395.130** seconds; their difference **280.497** seconds is consistent with the 281.524-second first-step receipt. The original evidence is preserved unchanged and must not be silently relabeled. New source stores the monotonic origin in `start()` and writes elapsed `time.monotonic() - origin`; a new software test checks nonnegative, increasing, start-relative samples. This repair affects **future diagnostic evidence only**; no native rerun or retroactive result claimed.

## Tests, next and unchanged gates

Focused no-model CI: `.github/workflows/bp2b-rss-clock-review.yml`, 7 synthetic tests (six inherited plus new clock regression), compile, privacy scan and exact-parent diff. Focused CI **7/7 synthetic tests PASS**, Python compile PASS, privacy CLEAN and diff check PASS on exact tested source commit `38788c6e6413a0363ed89f41c9689e898253c8f8`, Actions `40522267037`. Final metadata-head recheck pending; no new native/Redmi execution. Next: verify CI, review sample-clock counterexample, and keep the original one-step raw artifact as historical Linux evidence. Native BP2b 30-step training remains unproven; do not start a competing heavy run.

STEP2 UTILITY_FAIL; B3 L1 FAIL; BJ1 NO_SIGNAL; registered `jepa_weight=0`; Age authority 0; Redmi unmeasured; V13 incomplete. No main merge without independent integration review.
