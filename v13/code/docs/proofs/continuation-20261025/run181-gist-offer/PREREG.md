# Run181 — prospective real B2 Gist-view offer utility, fixed 36-memo cohort

Base: verified Run180 native raw Gist consumer checkpoint `fdaa5c50fb68ccd8a7b43a25e137d380e5298edd`, PR209. Owner: **new** `scripts/run181_gist_offer_audit.py`, `tests/test_run181_gist_offer_audit.py`, this proof and dedicated CI. Existing `scripts/gist_utility_bench.py` and all frozen Runtime/Body/Cognition/Gist/model files remain **byte-identical**. Registration is published before any Run181 native cohort execution. Heavy jobs serialized with `v13-native-c3-run131-serialized`, no concurrent model owner.

## Immutable native cohort and primary question

Does the already-existing Age-0 **text-grouped B2 Gist view** improve B2 offer factual extraction relative to fixed 960-char segments, without worse exact-quote validity or >10% more prompt tokens? This is a B2 offer proxy, not final C3 answer utility and not JEPA learning.

Use existing `gist_utility_bench.py` Git blob `f2b6d00cbe100152bb77a3b04187324eb379abd6`, `gist.py` blob `025baa96db50664348f140d3f3a22263500ea6da`, `cognition.py` blob `1a9eb6f7c7cbfce83d91cc09b4ff9516cff310cf`, `episodes.py` blob `48354f1f1764d76228f923ebc89e567e73331f3e`. Fixed script seed `20261012`, N=36 deterministic synthetic English project memos (owner/budget/revised deadline, 12 each), exactly one question per memo. Arms, in frozen script order: `fixed960`, `event960`, `gist`; same pinned Qwen3.5-0.8B Q4_0 B2 model, greedy JSON schema and fixed offer instructions; only source-view representation differs. No model/seed/answer/scorer modifications.

Registered B2 GGUF: `ggml-org/Qwen3.5-0.8B-GGUF`, revision `8fea620810c4afa23dd6443f999a48574c1611a3`, 563036064 bytes SHA-256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf` (Apache-2.0 per existing model registry). llama.cpp b10964 Ubuntu x64 archive 16825086 bytes SHA-256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Pinned `specs/models.json` blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`. Linux Ubuntu 24.04 runner only, not Redmi. The bench already specifies temperature 0, seed 13, 220 max tokens, 4 CPU threads, 8192 context, native server. No training, no adapter, no user data, no activation of `:gist active`.

## Frozen acceptance and independent audit

Use the bench's existing decision rule exactly: `GIST_HELPS_CANDIDATE` only if **paired Gist hit wins > losses** versus fixed960, **exact quote validity not lower**, and **mean prompt tokens <=110%** of fixed960; otherwise `GIST_NO_GAIN`. Preserve all 108 raw JSON outputs, prompt-token counts, timings, score fields, native hashes and deterministic corpus hash in `report.json`, including partial progress on failure. A new independent auditor recomputes every one of the 108 scores from raw JSON and original memo keys, verifies 36 unique IDs/arm, paired wins/losses, summary and verdict, and **never grants activation**. Four synthetic audit tests PASS locally; they are not native evidence.

The original script references a historical prereg file that is absent in the current checkout; this **new** registration is the binding Run181 protocol. Do not claim an earlier measured result. If native script or download fails, keep raw logs and partial report, mark FAIL; do not adjust pins or acceptance post hoc. GitHub artifact ZIP must be downloaded, hash-verified and audited independently. Any result only concerns B2 offer proxy utility, not STEP2's required B1+B2/C3 final-answer benefit.

## Gates and next command

`STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. No promotion from this experiment. After source+prereg checkpoint, run CI `python3 v13/code/scripts/gist_utility_bench.py --home $RUNNER_TEMP/run181/home --out $RUNNER_TEMP/run181/report`, then independent `run181_gist_offer_audit.py report.json --output audit.json`; preserve all raw files even on failure. Next: examine paired per-kind errors, and only if prereg criteria pass consider a **separate** human-authorized active trial. No rejected Drive backup.
