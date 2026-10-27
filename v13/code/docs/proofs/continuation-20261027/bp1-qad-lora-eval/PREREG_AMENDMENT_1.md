# BP1 QAD LoRA V2 collector hardening — prospective package 2 (2026-10-27)

Initial V2 software Actions `40476523264` source `dec1430b1aaf9c6237d7838e9cf89161849e75d5` **34/34 PASS**, compile0, privacy CLEAN; artifact `12720537041`, ZIP SHA256 `c1e5c983632db6ebdb3e1ea5aa0d14a809a7ca2d491a2fba520096b094abe7e0`, private Library byte-identical. This is software only, not native heldout.

Before native collection, bind the actual **train proof file** to `train_proof_sha256` in V2 binding and verify its source/train/model/adapter/config/negative gates and two nonzero optimizer steps; a mere 64-character declared hash must not authorize collection. Add explicit `--train-proof` argument. Negative tests: forged proof, wrong proof bytes/hash, absent adapter evidence, heldout used during training, authority changed, and no optimizer.

Add crash-resumable collection with exact binding bytes, source/prompt hash checks and append-only predictions; reject partial trailing JSONL or duplicate records rather than silently repairing. A second call with identical completed result must refuse to overwrite `FINAL_MANIFEST.json`. Negative tests: changed binding, duplicate/partial records, mismatched source. No model or heldout targets in software tests.

No change to V1 scorer, registered cohort, seed13, 44 rows, decoding, source hashes, or native gates. No native heldout or utility claim until separately executed on pinned b10964 with original raw evidence.