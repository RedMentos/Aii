# Run58 — source-bound exact Adam restart, manifest-last (synthetic)

Base PR91 `1a8823d7eb5baaa11ddd20681f741baf73c9f3bd`, prereg commit `e0fe7ae214e77f10f90377f9b6c00becb08f5868`. Owned only `optimizer-resume-run58/*`; frozen Run57/Run56 sources copied for reproducibility, no production code edits.

**Implementation:** actual PyTorch CPU Adam for 16×16 synthetic linear head, fixed Run57 source-bound 64 train/64 heldout, 120 steps, seed 1337. `save_checkpoint` at step 60 records F32 model weight, Adam step and two moment tensors in a bounded, no-pickle NPZ, hashes each array, binds exact source dataset hash, SourceRefs hash, base hash, generation, and writes NPZ with fsync before a canonical manifest-last sidecar. `load_checkpoint` refuses missing/tampered manifest, source revocation, changed generation/base/dataset, wrong optimizer step/shape, unexpected fields, and oversized ZIP decompression. Resume creates a fresh model/optimizer, restores all state, trains steps 61–120, then Run56 stages a SHADOW-only delta receipt after source revalidation. Frozen base remains unchanged.

**Results:** Uninterrupted 120-step vs 60+restart+60 bitwise-identical weights and all Adam moments. Heldout exact 1.0 (toy same-key task); resumed delta receipt validates; source revocation after checkpoint blocks resume. Fresh Python process restart matches SHA256 of all four state arrays. Real subprocess `os._exit(97)` after durable NPZ but before manifest leaves no accepted checkpoint; retry and resume succeed. 12/12 tests PASS, 12/12 Python `-O` PASS, 3 repeat subprocess crash tests PASS, compileall PASS. Linux synthetic SQLite/PyTorch only.

**Independent review:** adversarial RED proved a small compressed NPZ could expand into a 4 MiB array before hash rejection. A central-directory precheck now rejects oversized decompressed members before NumPy loads them. Original RED log retained. This is a bounded 16×16 candidate, not a general tensor loader.

**Limitations:** No real Store/Runtime/C3/B1/B2 or native training, no Redmi, no full repo suite/privacy scan, no real retention or general-language utility, no complete TrainRunnerProof. SQLite/NPZ SHA checks detect corruption, not a malicious actor able to forge all files/DB. Revalidate sources at actual optimizer/commit time. No Age authority, no base consolidation.

**Reproduce:** unpack archive, `cd optimizer_resume_run58 && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m unittest -v test_optimizer_resume && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -O -m unittest -q test_optimizer_resume`.

**Next:** full checkout independent review; actual Store schema/Run48 learning integration with unchanged source/age/approval gates; native C3 train path and true TrainRunnerProof including measured RAM/energy/thermal and Redmi; register realistic retention/utility before any promotion.

**Gates unchanged:** STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; V13 INCOMPLETE.

**Primary source:** SQLite transaction semantics https://www.sqlite.org/lang_transaction.html; NumPy NPZ https://numpy.org/doc/stable/reference/generated/numpy.savez.html; safetensors https://github.com/huggingface/safetensors. 2026-10-24.
