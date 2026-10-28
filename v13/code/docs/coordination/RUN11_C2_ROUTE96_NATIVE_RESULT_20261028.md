# Run11 C2 Needle3 frozen 96-route Linux native benchmark — verified checkpoint 2026-10-28

Owner: Codex; review-only PR #850 child of #844. Original prereg `RUN11_C2_ROUTE96_NATIVE_EVAL_PREREG_20261028.md` and **pre-native** worker-adapter amendment `RUN11_C2_ROUTE96_WORKER_PROTOCOL_AMENDMENT_20261028.md` retained. Frozen `specs/c2-benchmark.json` Git blob `758c5a7dea93bfb178bc3778428ee262178b6a58`, 96 author-labelled items exactly 24 per simple/detail/gist/both, items SHA256 `54f3da390fb79c3f966edd61d3390d94dc59d850987174c644ef45ef531a54e6`. Model/catalog/tools/seed/protocol unchanged; no training, no row filtering, no threshold optimization.

**Software guards:** workflow `40633503979` source `fcd114443a1d4359217b652f575347840793cd53`, 9/9 PASS, compile/privacy/diff0, artifact 12791644612 ZIP SHA256 `90035731bba56aeb68e1552ff41cf641320fdee14713051280926549637cc5d2`, CRC and 12/12 internal hashes verified. Original focused RED `40633325137` (test mock import) retained and corrected.

**Actual native 96-row evaluation:** workflow `40634077824`, source `26873769861cfd899daad04a05181d679c8066a8`, SUCCESS as an **execution and evidence-closure benchmark**, not a quality PASS. Artifact 12792493532 ZIP SHA256 `c4dd65ba18b446447271d4780b0741a4dc6994ab489496592ab3447123747076`, CRC valid and **17/17 SHA256SUMS verified**. Bootstrap exact current public models/Needle worker PASS; benchmark, report binding, privacy, diff exit0. No model/binary bytes uploaded. `needle.rows.json`, `scaffold.rows.json`, `report.json` preserve all 96 IDs/labels/predictions and raw per-row validation/error/latency metadata. One Needle row was invalid due `Unavailable:tool call truncated: token budget exhausted`, counted wrong, not discarded.

## Observed route quality (author labels, Linux x86_64 only)

| Metric | Native Needle3 C2 worker | Current regex scaffold |
|---|---:|---:|
| Accuracy | **15/96 = 15.62%** | **46/96 = 47.92%** |
| Macro-F1 | **0.1515** | **0.4698** |
| Valid route rate | **95/96 = 98.96%** | 96/96 = 100% |
| Native validation rate | 95/96 = 98.96% | n/a |
| Latency p50 | 0.2348 s | near 0 (software) |
| Latency p95 | 0.4387 s | near 0 |
| Peak Needle worker RSS | 102281216 bytes | n/a |
| Confidence AUROC vs correctness | **0.4583** | n/a |

Needle per-class F1: simple0.1304, detail0.1509, gist0.2069, both0.1176. Needle 95 validated rows accuracy 0.1579. The model's valid JSON/function calls are **not evidence of good routing**. On this frozen author-labelled corpus, native Needle underperforms the existing scaffold substantially. Confidence AUROC below 0.5 is not calibrated confidence; do not activate a confidence-based promotion from these results. Across the 95 valid native rows, mean reported confidence was **0.5723** versus observed accuracy **0.1579**. Among the **20** rows reporting confidence >=0.9, only **3/20** were correct (15% accuracy; mean confidence **0.9836**). These are descriptive on the frozen author labels, not a calibrated probability estimate. These labels are author-generated and subjective, not a user-labelled gold standard; this result does not prove general control ability or inability.

**Runtime implication (not a code change):** `Runtime._route` starts from `scaffold_route` and treats an uncalibrated native C2 proposal as `NATIVE_C2_ADVISORY` only when the scaffold selected `simple`. On the 24 author-labelled `simple` items, native Needle predicted `simple` only **3/24** times (12 detail, 9 gist), while the scaffold predicted `simple` **24/24**. Across all 96 rows the two candidates agreed on only **14**, were both correct on **5**, Needle alone correct on **10**, and scaffold alone correct on **41**. This is a concrete reason not to infer that a valid native control function call improves routing. It does not prove the runtime's overall accuracy without a separate end-to-end evaluation. Frozen `runtime.py` source-handoff hashes were not changed.

**Durable private backup:** native quality-fail ZIP and focused software ZIP are in private ChatGPT Library `/V13-Checkpoints/2026-10-28/Run11-Native-Singleturn/`. Both were re-materialized and SHA256-matched against their GitHub artifacts. The folder also contains the original C3 962MB interactive RED and separate C3/B1/B2/C2 native proofs. No rejected anyone-writable Drive destination was used. Current `BUILD_STATE.json` on PR #850 has scoped `run11_c2_route96_native_20261028` and `run11_native_linux_chain_20261028` entries, without changing frozen model/source hashes or negative gates.

## Gates and next work

**C2 route-quality gate remains FAIL/NOT_PROMOTED** for this candidate; keep current safe scaffold and explicit approval/age gates. Do not tune/fit on these same 96 evaluation rows and then claim a heldout improvement. If calibration or an embedding readout is pursued, preregister an independent train/validation/heldout split and external labels, preserve original cohort, compare native worker/scaffold on untouched heldout with confidence calibration and Linux/Redmi distinctions. Separately review #848 native JEF/STEP12 structural PASS but public arithmetic ask RED, and #849 prompt candidate without merging until independent proof.

Original gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY; no JEF control promotion, no Redmi thermal/RSS, no whole-system claim. Current owner Codex review-only. Remaining platform budget UNKNOWN.

Next exact command (software recheck): `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_c2_benchmark tests.test_current_c2_native_linux_smoke_20261028`. Native reproduction only after exclusive owner and fresh pinned bootstrap: `PYTHONPATH=v13/code python3 scripts/c2_benchmark.py --home <installed> --cache <fresh> --out <fresh> --only needle scaffold`.
