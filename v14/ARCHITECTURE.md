# V14 active architecture direction

**Status:** working synthesis, not a frozen implementation specification.

V14 is intended to become a distributed, recurrent, brain-inspired learning system. It is not a set of chatbots taking turns, a conventional agent pipeline, or a thin orchestration harness. The desired organization must emerge through learned representations, recurrent interaction and measurable adaptation.

## Keep these dimensions separate

- **JEPA:** a learning/prediction principle. Context is encoded, a predictor estimates a target representation, and a target encoder supplies the representation of the observed target. EMA target updates may be used as a training mechanism; this does not make the whole architecture a frozen-teacher system.
- **Recurrence:** shared weights are applied repeatedly to changing hidden states. Iteration count is not the number of modules or agents.
- **GIST / DETAIL:** representational scale and specialization. DETAIL consists of many smaller, more local/specialized representations. GIST holds broader, more connected representations and may require larger weight regions. They can overlap and interact through learned latent pathways.
- **World / Self prediction:** distinct target families. World prediction concerns external observations; Self prediction concerns internal states, processing, decisions, actions, outputs and system evolution. Action-conditioned prediction links them.
- **Resources:** execution constraints, not cognitive identity. SSD capacity, resident RAM, compute, bandwidth/I/O, energy, thermal limits and latency are separate budgets.
- **Structure and residency:** what the model has learned to represent, what is currently active, and what is resident in RAM are not the same thing.

## GIST and DETAIL

DETAIL should support many small, precise and selectively activated representations: local patterns, exact values, code, errors and retrievable details. GIST should support larger and more connected representations of broader relationships and abstractions. Do not reduce this to "numbers versus summaries" or to two isolated chat models.

A learned latent bridge may allow information to move between scales. A bridge is not validated merely because tensors can be copied: it must carry useful source-bound activations, be consumed by a receiver and improve held-out utility against exact/no-bridge/shuffle controls. Production B3 remains off until those conditions are demonstrated.

## World, Self and action-conditioned prediction

Maintain separate evaluation targets for:
1. the next external observed state;
2. the next internal state;
3. the next state conditioned on a proposed action.

Internal prediction must be compared with identity/copy baselines so it cannot pass by trivially copying its current state. The model should learn relations between its own states/actions and subsequent observed consequences.

## Activity and learning

Record which representations, components and weight versions participated in a prediction or action, which downstream components consumed them, and what outcome followed. Activity traces are initially observability data. Eligibility traces are separate learning state used by an update rule. Delayed credit must attach to the actual participating pathway and version; stale feedback must not silently update a different weight version.

Replay/consolidation and sleep-like processing are later learning stages, not substitutes for online evidence. Updates require held-out validation, rollback and ablation. Structural plasticity should eventually support adding, strengthening, modifying, merging, shrinking and removing structures within explicit storage and compute limits; do not equate it with selecting from a permanently fixed expert list.

## Resource-aware execution

The resource manager enforces hard limits while the model learns/selects useful work within them. Keep separate budgets for:
- total on-disk model/weight size;
- resident RAM and active working set;
- compute and concurrency;
- bandwidth and component-swapping I/O;
- energy, thermal headroom and latency.

A compact global index or representation must remain available when large components are not resident. SSD capacity is not RAM. More parallelism is not automatically better when it causes contention. The historical Redmi Android 13 ARM64 device is the primary target; its current resource envelope must be remeasured rather than copied from old probes.

## Evidence discipline

Do not call a component implemented unless code, a real data/state path, persistence, tests, telemetry and ablation are present. Distinguish specification, synthetic wiring, local execution, native Android execution, weight updates and held-out utility. CI success is not a device result.
