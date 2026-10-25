# Run292 — learned wake=none now vetoes late B1/B2; native wake-only PASS

Date 2026-10-25 UTC. Independent owner `v13/code/v13/latewatch.py`, new test, dedicated CPU and serialized pinned-native wake-only workflows, scoped proof. Base Run291 source `6855943f5d568f08fc5b64faa958a3cf51866310`. No edits to PR284 Runtime, PR289 Store, PR290 Memory, registered models/seeds or Canon.

## Actual defect and repair

Frozen Run288 readouts native evidence had `wake_decision.learned=true,action=none`, but `late_watch.status=STILL_RUNNING`, `offered=B1_DETAIL` and `wake_consumed_by_runtime_no_body_wake=false`. `latewatch.start` independently launched a B1 body while C3 streamed, silently defeating the approved bounded observer wake decision.

Run292 checks `meta.wake_decision` before residency/thread creation: only `learned is True and action=='none'` returns inert Watcher `LEARNED_WAKE_NONE`. Unlearned `none`, learned `detail`, explicit latewatch off, residency, source and output policies remain unchanged.

## Closed RED -> GREEN and genuine native retest

- RED exact source `7777ba0ba08296e8cf361fb7484477a3e6f1e31e`; CI `40196892228`: **33 tests, 1 FAIL** (learned none spawned a thread), 32 PASS; privacy CLEAN. Raw artifact `12600287362` SHA256 `3e76f661750ad298dcaa2f2c0b5a098834edbf81d99fcb9a13ede12ab3e0631e`.
- GREEN exact patched source `d5c97bf67e542a7a89dcf2ca9bef9dc28cb89d3d`; CI `40196956066`: **33/33 PASS**, privacy CLEAN. Final workflow rerun `40197117997` SUCCESS, raw artifact `12599718135` SHA256 `d04fb80b9120d7eb15e0aa36342156560529342f34c8e8bcc126ab304eb28bfa`.
- **Genuine pinned Linux-native** wake-only lifecycle exact source `ef3645f2b649f967fd86534122884b29b3dcdf1b`; CI `40197118017` SUCCESS, actual `tests/integration_readouts.py --wake-only` returned `READOUT_LIFECYCLE_PASS`, **11/11 checks true**, including `wake_consumed_by_runtime_no_body_wake=true`. Observed actual `wake_decision.learned=true,action=none` and `late_watch.status=LEARNED_WAKE_NONE`; no OfferPacket for the event. Source/model bootstrap and host evidence retained. Raw artifact `12600692048` SHA256 `9b590bb3a209a72d0bd2eb4b27b8ec169c627af3fad6b9ef00ed629bbdec1cd0`.
- Focused source-bound CI `40197117956`: 401/401 software PASS, extracted Phone 114/114 PASS and restart PASS, official privacy CLEAN. Independently verified 1005-file Phone ZIP SHA256 `ded94bb8d2ca79e5317af5d5b8466447fdf23a6615e689364a4e4410802f55a1`; outer artifact `12600552263` SHA256 `3dd9b5655ba735a96206410a998df09c6272e2b210f7848851dc601bd1844b70`.
- Independent local exact-source `git hash-object` matched `f213cc646d90ca5528c435aa335472741413b4a7`, 29/29 existing latewatch/readout software regressions PASS, separate learned-none no-body counterexample PASS (`LOCAL_INDEPENDENT.log`). No actual native model ran locally.
- Historical Run118 `40196956052` and `40197117952` FAIL at their **intentional immutable old `latewatch.py` Git blob pin** `5df03a7c8a8f5709b5ed2ceb6a08851c780d8480`; no functional Run118 tests ran on the changed source. Preserve this as a historical pin conflict, **not** silently rebaseline its original proof. Run292 has separate exact-head and native evidence.

## Hashes and durable backup

- Canon SHA256 unchanged `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.
- Patched `latewatch.py` Git blob `f213cc646d90ca5528c435aa335472741413b4a7`; new test `aa77aafa04032ce4d4afea63afa2648129c8568d`; CPU workflow `b54c2f8382f0a555cd37dceaa3b9b1098eef0637`; native workflow `06b5e0f9e906747b96301fc520eda296daa9b379`.
- Four complete raw RED, GREEN, native wake-only and Phone source archives saved to **private ChatGPT Library** `/V13-Inquisition/Proofs/Run292/`, all four downloaded back and SHA256 verified byte-for-byte. Rejected anyone-writable Drive destination not used.

## Unchanged negative gates / next

**This proves only the wake-only native subset**, not the full readouts stage. The original full Run288 readouts remains `READOUT_LIFECYCLE_PARTIAL`: halt readout `EVALUATED_FAIL` because Pareto `cost_after=0.5 > cost_before=0.0`. Do not promote full readouts. `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, `V13=INCOMPLETE`.

**Next substantive independent package:** Analyze the Run288 output-adapter actual native `output-adapter.features.json.gz` under the unchanged max-bias bound and frozen 19-case test partition. Quantify whether 80% first-token accuracy is even feasible before changing optimizer or labels. Preserve exact registered cohort and every negative gate. PR284 cancellation remains separately owned.
