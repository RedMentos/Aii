# Run66 — B3-H9 Callosum outcome idempotence

Base Run65 PR98 `0d48e8354f442c8badc86cca6074e46d8d166e51`. This is a branch-scoped change to the existing Callosum utility-learning path, not a latent L1 implementation.

**Original bug:** `Callosum.outcome` sets `m['scored']=True` but subsequent invocations score the same message again. Reproduced two calls yielding channel count 2 for one packet. Repeated finalization/retry can bias B3-H9 utility history and baseline channel selection.

**Patch:** filter unscored pending messages before evidence lookup; inside existing optimistic `_mutate` CAS, apply each packet ID at most once using `callosum_outcome_once.apply_once`. Mark only packets with an observed receiver offer. Duplicate IDs are collapsed, already-scored duplicates are reconciled without new utility. Report only actually applied utilities and channel IDs to neuromod telemetry. `on_rating` (explicit human feedback), B3-H10 degradation, latent gates and active/shadow approval unchanged.

**Tests:** 10/10 pure software regressions PASS; 10/10 Python -O PASS; 1000/1000 randomized duplicate/replay synthetic trials PASS; compileall PASS. Original RED and raw test logs in a lossless `RUN66_RAW_EVIDENCE.tar.xz.b64` (decoded SHA256 `dafd515666937e198a71bad04d82e21b525287854850cbe302d07e23bbfbc874`). Source/test Git blobs verified. Actual Callosum+SQLite integration test authored but NOT RUN because complete checkout inaccessible.

**Limitations:** no full repository suite, official privacy scan, actual Store CAS race, native bodies, Redmi or response-utility proof. Existing B3 L1 FAIL remains; a passing synthetic L0 accounting test cannot promote it.

**Reproduce:** `cd v13/code && python -m unittest -v tests.test_callosum_outcome_once tests.test_callosum_outcome_integration_run66`; second module requires full checkout. Review: `PYTHONPATH=. python docs/proofs/continuation-20261024/callosum-once-run66/independent-review.py` after decoding evidence archive.

**Next:** independently run actual SQLite/Store integration test, simulate concurrent CAS conflict, full suite/privacy scan and check neuromod feedback accounting. Continue independent organs while native/Redmi prerequisites remain blocked.

Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, full V13 INCOMPLETE.
