# Native embedding worker accumulation: source-grounded review

The restored durable evidence contains 736 actual rows / 46 native raw request-response batches. Later live rows and a later observer revision were not saved to Git or the closed ZIP before scratch was cleared; they are not recovered evidence. The old 384-row failure's return code was never persisted, and its cgroup counters have no start baseline. It cannot be individually attributed to an OOM kill.

The previous session reported native RSS increasing about 0.25 GB per 16-input batch even after Dream training paused, followed by a later owned worker return code -9. That later observation is session history, not a recovered raw artifact. The new wrapper records process identity, RSS and cgroup start/end values directly so future measurements have durable raw lineage.

Inspection of the pinned, patched llama.cpp b10964 source identifies a concrete cache accumulation path:

* `common/common.h` defaults `cache_idle_slots=true` and `cache_ram_mib=8192`. The unchanged capture command supplies neither cache flag.
* `server-context.cpp::process_single_task` handles completion, embedding and rerank in the same launch branch. After launch it visits idle slots whenever `cache_idle_slots` is enabled; this block has no completion-only condition. It calls `slot.prompt_save(*prompt_cache)` and `prompt_cache->update()`.
* `server_slot::prompt_save` serializes the full sequence state via `llama_state_seq_get_size_ext` / `llama_state_seq_get_data_ext`, requesting `LLAMA_STATE_SEQ_FLAGS_NONE`.
* `server-task.cpp::server_prompt_cache::alloc` retains each new state in the `states` list. It skips contained prompts, removes obsolete contained prompts, and evicts oldest entries when aggregate serialized state would exceed the configured cache bound.
* The completion-only guards elsewhere do not disable this idle-slot block. Embeddings release their slot after `send_embedding`; the prompt remains available unless it is a child slot.
* The queue-result path consumes/removes delivered result entries; it does not by itself establish an unbounded queue-retention leak.

This path can retain serialized recurrent/KV state across differing embedding prompts, and the default 8-GB cache alone exceeds the practical worker allowance inside an 8-GiB cgroup once models and other processes are counted. It is a source-supported candidate explanation for the observed accumulation. No heap profile or cache-size measurement currently proves that all growth came from this path; allocator retention and other allocations remain unmeasured.

This experiment preserves the original native command, pooling, batch size, templates and input order. It addresses lifetime accumulation by terminating only the driver's owned Popen after eight successfully committed new batches, then validating and continuing with a fresh worker. Changing cache flags would change the original protocol and is not silently introduced.

Source hashes inspected:

| Source | SHA-256 |
|---|---|
| tools/server/server-context.cpp | 929e58f8e7b6db428aa82f5b0459f82c32b2cd906757b477617a71867ce73b80 |
| tools/server/server-task.cpp | 0fd5c8df2525e61214986e8abe3fc4edbb92f5dd652c9c2bfd1bc2712218a585 |
| common/common.h | 7cfcc6a57122702ea35d04ed20861aef162bd94f55cfbbf9fd23ee3127fe6cb4 |
| tools/server/server-queue.cpp | 0e196113d16f130230d2cc0b232915e1f5b4f1dda184790afbfdc4986dd1fd58 |

Receiver authority remains zero. This is an extraction lifecycle repair, not evidence of semantic learning quality or a completed architecture.
