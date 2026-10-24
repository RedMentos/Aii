# Run44 — source-staged synthetic context learning, negative result

Preregistered before training on commit `482d6d107ddd4404b76c2f0340d1e486a9b1c7af`, based on Run43 `40bbd200d848d6e65639ffe57d95f0157228044b`. Ownership only this folder; no production changes.

**Experiment:** Fixed synthetic 3-key/3-value association task; 512 training and 256 independent heldout examples; small one-layer 2-head transformer (d=32), 300 Adam steps at lr .005. A mock `SyntheticStore.history` supplies pairs to the **exact Git-blob-pinned Run42 staging candidate**, and the corrected consumer parses the resulting staged JSONL rather than privileged generator tuples. This tests an isolated data path and model behavior, **not** real V13 `native_history` lineage validation or native C3 learning.

**Predeclared synthetic pass**: context >= .60; context - no-context >= .25; context - shuffled-context >= .25; no-context <= .35. Observed heldout: context **.40625**, no-context **.1171875**, shuffled-context **.421875**, untrained **.140625**. **FAIL_SYNTHETIC**: model uses marginal value information but did not learn reliable query-key/value binding. No real-model utility or original gate is promoted.

**Preserved attempts:** Initial run used generator tuples instead of staged JSONL; this was identified during review and corrected before archival. Metrics remained identical on corrected exploratory rerun. A second review replaced security-sensitive `assert` checks with explicit runtime exceptions; optimized Python `-O` test and cohort again produced the same negative metrics. All first/corrected/optimized raw outputs are in the archive.

**Tests:** 8/8 synthetic path tests PASS, 8/8 under Python -O, compileall PASS. No full repository, native model or Redmi test. The original V13 gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.

**Source/evidence:** `evidence/run44-source-evidence.tar.xz.b64` contains source, tests, first/corrected/optimized logs, hashes. Decode: `base64 -d evidence/run44-source-evidence.tar.xz.b64 > run44-source-evidence.tar.xz && tar -xJf run44-source-evidence.tar.xz`. Decoded archive SHA256: `9d35b4e04d1da6ba6e8eae8e148965c20c4241bbeeba99f307644b4c1e46f3d4`. Pinned Run42 source Git blob: `8dcd4b36cbe58f06ea330a510f1735b37f0ad600`.

**Next:** Keep this result negative. Independently preregister a key-conditioned binding architecture, with a real `Store/native_history` source-revocation test and a train-consumer revalidation gate. Do not re-label the post-hoc corrections as a positive preregistered result or commit any synthetic weights to production.
