# V13 full-system build-first integration map — user correction 2026-11-19

Goal: make the **complete** V13/Inquisition-JEPA architecture usable as designed, then iterate on correctness/performance. This map is for implementation, not a new Canon or a list of reasons not to build. An isolated experiment does not satisfy the corresponding live/runtime function.

## What already exists; connect these, don't duplicate them

| Required V13 function | Existing code in this repo | Next executable integration |
| --- | --- | --- |
| A perception and typed A5 | `v13/aplane.py`, `v13/episodes.py`, `v13/a5_admission.py`, `v13/raw_ear.py` | Connect source-fresh audio/text A5 to the same `Runtime._turn` path; preserve provenance and consent |
| B1 detail + B2 gist as genuinely distinct concurrent/serial organs | `v13/bodies.py`, `v13/cognition.py`, `v13/observer_schedule.py`, `v13/runners.py` | Observe live model outputs, not only a declared model role; concurrent when RAM permits, sequential otherwise |
| B3 and Enlightened Space across **all** organs | `v13/enlightened_space.py`, `v13/callosum.py`, `v13/b3bridge.py`, `v13/latent_bridge.py` | Complete typed A↔B↔C/world/self exchange; a **real trained latent** needs real sender/receiver activations and native consumer; use exact/control fallback until such a consumer is wired |
| JEF/C2 decision + C3 language | `v13/executive.py`, `v13/cognition.py`, `v13/fastpolicy.py`, `v13/runtime.py` | Reuse existing native Needle + LFM runners; expose measured first-token and useful output before adding elaborate policy |
| World/self/memory | `v13/world.py`, `v13/world_jepa.py`, `v13/memory.py`, `v13/selfmodel.py`, `v13/online_world.py` | Persistent transitions, provenance, recall, prediction, restart and genuine second-attempt tests in the normal answer loop |
| JEPA/body weights and plasticity | `v13/body_jepa.py`, `v13/body_training.py`, `v13/world_jepa_runtime_checkpoint.py`, `v13/plasticity.py` | Make one real lab-only weight-update path selectable with local master weights (not fake GGUF writes), compare before/after and recover on restart |
| Sleep/replay | `v13/sleep.py`, `v13/sleep_offline.py`, `v13/consolidation.py` | Execute from recorded episodes without requiring another user message; no fake autonomous outputs |
| Tools/actions and future controlled self-edit | `v13/toolstep.py`, `v13/actionlearn.py`, `v13/transaction.py` | End-to-end propose→explicit approval→execute→outcome→learn; self-edit is staged diff and review/rollback, not silent live source changes |
| Operator/Android | `v13/managed_console.py`, `v13/mobile_dashboard.py`, `v13/runtime_deploy.py` | Expose whole-stack controls and real statuses, including lab Age vs official Age; one actual phone session tests performance |

These are *candidate implementation locations*, **not** claims of functional completeness. Reuse the existing `Runtime` spine instead of inventing another independent demo/harness.

## Open-source reuse decisions (checked 2026-11-19)

- **llama.cpp** [repository](https://github.com/ggml-org/llama.cpp) / [MIT](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) / [Android-Termux guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md): **primary candidate** for native GGUF/model streaming, prompt caching and bounded sessions, especially C3. Existing V13 native runner should be reused and benchmarked, not replaced with a duplicate inference engine. [LFM2 recurrent-state batching issue #29002](https://github.com/ggml-org/llama.cpp/issues/29002) is a targeted upstream consideration; reproduce against V13 pinned version before any configuration change.
- **ExecuTorch** [repository](https://github.com/pytorch/executorch) / [BSD](https://github.com/pytorch/executorch/blob/main/LICENSE): **candidate** for tiny native/mobile tensor predictor and projector, *not* an automatic replacement for GGUF; requires a concrete export, ABI and memory comparison before Android use.
- **River** [repository](https://github.com/online-ml/river) / [BSD-3](https://github.com/online-ml/river/blob/main/LICENSE): **candidate** for small online-memory, drift and evaluation algorithms, where on-device dependency wheels actually build. Reuse algorithmic references rather than assuming full Python environment fits Termux.
- **Avalanche** [repository](https://github.com/ContinualAI/avalanche) / [MIT](https://github.com/ContinualAI/avalanche/blob/master/README.md): **offline** continual-learning baselines and replay/retention evaluation. No promise of fitting its PyTorch-heavy stack on Redmi.
- **V-JEPA 2** [repository](https://github.com/facebookresearch/vjepa2) / [license caveat](https://github.com/facebookresearch/vjepa2/blob/main/README.md): **research source** for predictor/EMA architecture; the project has separately licensed portions and model weights require separate terms. Not a 6-GB Android runtime plug-in.

**Dependency/legal rule:** record *exact dependency revision* at integration time and verify upstream LICENSE, files with other headers, NOTICE, model-card/weight permissions, Android build feasibility and attribution; never copy an unlicensed snippet. This research map makes no claim a library was installed on the phone.

## New work cadence: build instead of polishing isolated mini-fixes

1. Start from last source-verifiable GitHub branch. Search repo and upstream first. Assign separate ownership for the functional vertical slices above; no multiple agents rewriting the same source files.
2. Make a **single connected in-process runtime** that activates the existing organs and displays real provenance, even when some run in sequential/fallback/shadow mode on the Redmi. No fake substitute weights, latent influence or self-edit promotion.
3. Implement actual test-lab feature and learning-right controls. Allow higher lab stage for experimentation while official Age remains 0; do not conflate Age with token or deadline budgets.
4. Deliver a working Android chat session and measure prompt→first token, successful B1/B2 offers, C3 output, persistence, memory/JEPA training/replay and genuine post-restart behavior. Fix measured failures in **priority order** while continuing independent whole-system integration.
5. Use smoke and negative/security tests for each substantive merge, but CI-only green without real connected behavior is not the deliverable. Never remove license, user consent or safety gates to make a feature appear implemented.
6. After an integration stalls, research an existing upstream alternative, compare it, or switch to a distinct missing Canon subsystem. Do not cycle on the same two fixture failures for a whole development session.

## Reporting
Each agent reports a useful integration step, the actual consumer and evidence category, previous code reused (repo or external), missing behavior, and the next functional connection. All unfinished Canon scope stays visible. This replaces PR-count-oriented progress reporting without falsifying any measured FAIL.
