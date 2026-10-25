# Run160 follow-up registration after first bounded-prefix failure

After run 40162856977 proved the 8 MiB prefix too small for B2's GGUF tokenizer metadata, increase the **maximum bounded prefix from 8 MiB to 32 MiB** before a new CI attempt. Preserve the original 8 MiB protocol and failed job. This changes only a read-only metadata budget, not model weights, source hashes, training authority or V13 gates.

The new CI must fetch at most 32 MiB for each of the same pinned public B1/B2 GGUF revisions, keep HTTP Range / Content-Range checks and still mark `full_model_sha256_verified=false`. If 32 MiB is insufficient, fail closed and register another explicit follow-up rather than silently unbounding the read. No native model inference or weight writes.
