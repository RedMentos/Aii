# Run38 prereg — World-JEPA full-six-slot training versus frozen two-slot sampling

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run37 independent audit PR #1364 at exact `9006c30437840383873136862e326b46ffa7abea`; source parent Run36 #1363, frozen Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. This preregistration must be committed **before** any new Run38 candidate implementation, real-file collection or fit.

## Motivation and frozen comparison

Original Run35 exact-row seeds301–303: aligned local 96D World-JEPA covered CF retrieval .9413 vs scrambled .2746, but **W4 FAIL** (rho -.2789 vs <= -.30), **W6 FAIL** (balanced JEPA .9522 vs no-action .9534), W7b/c FAIL. Both-world attribution gains are positive, but action-aware training has not shown a broad balanced advantage. Original Run29/32/35 negative evidence and all gates remain binding.

Hypothesis: the Run28 slot-shared model trains its shared local core on only the affected slot plus one randomly selected unaffected slot per transition. A separate **all-six-slot** candidate trains the same shared core on all six physical slots per transition: one affected slot receives the exact local operation and five unaffected slots receive noop; global noop receives six noop; zero-action control receives six zero action vectors. This changes training sampling distribution and available examples, **not** core architecture, parameter count, latent width, optimizer steps or action support. It is not a matched compute/data-volume comparison and cannot establish causal learning outside the registered synthetic real-file world.

Frozen source hashes: original `world_jepa.py` `99a686a131a1bdc89efe0d0cf9610ec54cbd853b`; original collector `z12b_world_jepa.py` `2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4`; Run28 two-slot candidate `67e14e0d03c50c4767b74d5b02a819a95c6cc262`; Run35 evaluator `219bf7233cb91c746c89a60f9b7789dc3b5ca9ef`. No modification to these files.

## Frozen new cohort and gates

Disjoint real-file seeds **401,402,403**, train4000/cf150/attr300/steps3000 per seed. Exactly one freshly collected file-world train/CF/attribution set per seed; both original two-slot and new six-slot arms consume the **same in-memory rows**. Same 16D shared local latent and 96D concatenated world latent, same parameter count, same trainable architecture and optimizer/steps. Each arm separately trains true-action, zero-action and shuffled-action models using the original Run35 evaluator. Original Z12b W1–W6 and Run35 W7a/b/c thresholds are unchanged; no threshold retuning, seed exclusions or source/model swaps.

Exploratory H1: six-slot action-vs-no-action balanced attribution gap exceeds two-slot gap by >= .02 mean across three seeds, with no seed deterioration worse than -.01. H2: six-slot covered CF retrieval >= .80 in each seed and W2 original no-action/shuffled controls fail. These are descriptive research gates, not promotion. Original binding W1–W6 **and** W7 must all pass for a SHADOW candidate to be considered; even then, production/age/STEP2/JEPA promotion requires separate utility, approvals and Redmi proof.

Software preflight: mock WorldJEPA records exactly 6*N rows, verifies affected/noop/zero action mapping, exact full operation-slot support, exception-atomic publication, original input immutability, and original two-slot source blob unchanged. Run heavy real-file only after software GREEN and no competing native heavy owner; reuse serial concurrency group `v13-native-c3-ag12-20261030`, bounded runtime and closed original raw with all failures. Preserve private evidence, model/seed/source pins, no raw private prompts in GitHub. No automatic merge.

Negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, no Redmi, learned German transfer or whole-system completion.
