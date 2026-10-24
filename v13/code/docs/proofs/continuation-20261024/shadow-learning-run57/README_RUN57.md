# Run57 — source-validated SHADOW gradient path to durable receipt (synthetic)

Base PR90 `dc474011057eee7c5d5cf37e9bfa24e030891a52`; prereg commit `983cfa8614257acc6a8e796a40431ec14df6ebd2`. Own only `shadow-learning-run57/*` proof files. Snapshot of unchanged Run56 `shadow_commit.py` included under `upstream_run56/` for offline exact reproduction; no production edits.

**Data flow:** synthetic Store-shaped SQLite source blobs → full SourceRef hash/range/deleted checks → exact text parser (16 keys, 4 train + 4 heldout/key, fixed seed 20261024) → PyTorch CPU linear head 120 Adam steps (fixed seed 1337, lr .10) → deterministic safetensors F32 checkpoint with dataset/source-ref hashes → Run56 fsynced immutable shadow delta + SQLite receipt → independent source/generation/base/delta revalidation → safe tensor read. Source revocation before publication or after publication prevents a verified read. The frozen base file is never overwritten, even on a colliding path.

**Preregistered metrics (Linux synthetic only):** 64 train / 64 heldout, untrained exact .0625 (threshold <=.25), trained exact 1.0000 (>=.90), shuffled-label control exact .0000 (<=.50). No production model/JEPA utility claim. Base SHA256 `38542f42b2565b205570b508c42d884343a4e58a92c12f881a8e81d731a553a5`; final deterministic delta SHA256 `34b646f8ccf8a20baec06865c1b5f2f36c00778c64fce6332c52b4fb750f9f27`, independently repeated across three fresh Python processes.

**Tests:** 6/6 synthetic integration tests PASS; 6/6 under Python `-O`; `compileall` PASS. Exploratory 4/4 first tests PASS. Adversarial test RED found pre-existing base file overwritten; fixed with exclusive-create and hash compare. Second RED found nondeterministic safetensors metadata ordering despite identical weight bytes; fixed with a canonical single-tensor safetensors v1 serializer, official safe_open parser still used for read. Both original RED logs retained.

**Limitations:** This is a toy lookup task (same key distribution in heldout), not real C3/B1/B2, no native models/Redmi, no real Store/Runtime, no optimizer crash/restart proof, no retention across tasks, no causal JEPA or general language transfer. Run56 receipt is not cryptographically authenticated against a malicious DB writer; consumer-time source revalidation is required. The canonical data source is synthetic only. No Age or action rights, no production weight changes.

**Reproduce:** unpack archive, `cd shadow_learning_run57 && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m unittest -v test_shadow_learning && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -O -m unittest -q test_shadow_learning`.

**Next:** Integrate the isolated candidate with actual Store, real C3 SHADOW training path and registered source-grounded heldout text utility; test crash/restart, retention and revocation at optimizer time. Independently run full suite and official privacy scan in full checkout. Do not alter original registered cohorts or gates.

**Gates unchanged:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, full V13 INCOMPLETE.

**Primary source/provenance:** safetensors v1 format specification https://github.com/huggingface/safetensors (Apache-2.0), PyTorch https://pytorch.org (BSD-style), NumPy https://numpy.org (BSD-3-Clause), SQLite https://www.sqlite.org/lang_transaction.html (public domain); accessed 2026-10-24. No third-party model weights bundled.
