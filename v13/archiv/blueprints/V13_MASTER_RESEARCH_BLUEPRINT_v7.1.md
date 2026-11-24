# V13 MASTER RESEARCH BLUEPRINT v7.1
## Dual-Hemisphere Latent Continual-Learning System

**Research freeze:** 14 September 2026  
**Status:** authoritative architecture baseline for implementation; not a claim that the system is already complete  
**Primary deployment target:** Redmi Note 10 Pro class Android device, text-first  
**Scaling target:** the same brain contract from Android to workstation/server

---

# 1. Executive definition

V13 is not one language model. It is a persistent learning system made of three pretrained bodies and a set of trainable latent, memory, routing and consolidation systems:

- **Gist hemisphere:** sparse pretrained body, coarse/global representation, higher routing breadth.
- **Detail hemisphere:** different sparse pretrained body, fine/local representation, lower routing breadth.
- **Conscious Core / Judge:** small dense pretrained language model that controls routing, cautiousness, halting and visible output.
- **Global Workspace:** common latent state in which both hemispheres meet without merging their weights.
- **Corpus Callosum:** learned direct bidirectional A↔B communication.
- **Cautiousness κ:** conflict/surprise/uncertainty sensor.
- **Inquisition:** P1/P2 roles inside a nested latent space, optionally extended to multiple hard-assigned JEPA successor modes.
- **Memory:** exact provenance memory, latent semantic memory, readable world notebook and cold archive.
- **JEPA learners:** independent Gist, Detail, Cross, Judge and World predictors.
- **EMA targets:** slow stop-gradient targets for JEPA stabilization.
- **Continual learning:** fast state, adapters, replay, dream, slow consolidation into real body weights.
- **Translator/Teacher ports:** temporary external scaffolds that teach a capability and can later be retired after retention tests.
- **Transfer adapters:** passive LoRA/subspace packages used to move learned behaviour into replacement bodies.
- **Age policy:** controls plasticity, replay, translator dependence, compute and consolidation over development.

The mobile build is a small embodiment of this architecture, not a simplified different architecture.

---

# 2. Non-negotiable laws

## 2.1 Two genuinely different hemispheres

The large bodies must be different model families or materially different architectures. Two copies of the same MobileMoE are not accepted as the final design.

### Gist

- coarse/global,
- baseline 8-token/group hierarchy,
- higher native/effective Top-K than Detail,
- broader expert combination,
- long-horizon semantic structure,
- fewer/larger **V13-level** semantic units.

### Detail

- fine/local,
- baseline 1-token/slot hierarchy,
- lower native/effective Top-K,
- sharper specialization,
- contradiction/detail recovery,
- exact distinctions.

Both bodies should stay in approximately the same total-parameter class so that one hemisphere does not become the real brain and the other a decorative helper.

## 2.2 Preserve native pretrained routing

V13 does not silently change a model trained with Top-4 into Top-1 at inference. Native routers remain authoritative. V13 adds a **Meta-Router above them** and may train descendants with different routing only through real continued training/upcycling.

## 2.3 Direct communication

A and B talk directly through learned latent cross-attention/gated messages. The Judge is not the only bridge. A bounded token-space channel can be requested for literal information, but latent exchange is the default.

## 2.4 Judge is the conscious/output core

The dense core owns judgement, meta-routing, cautiousness policy, halting, time/ability estimates, translator reliance, rule interpretation and final linguistic rendering. Small heads can sit on its shared state, but these are not fifteen unrelated mini-models.

## 2.5 Output always terminates

Uncertainty may request more rounds, recall or verification, but never an infinite loop. A hard deadline always yields the best grounded answer available.

## 2.6 Provenance is structural

User evidence, retrieved evidence, teacher output, Dream, guesses and world-summary text remain distinguishable. Generated text cannot promote itself to verified fact.

## 2.7 Real weights remain learnable over the lifetime

Long-term V13 is not “frozen LLM + permanent LoRA brain.” Real model weights may eventually be consolidated. But “learnable” does not mean every weight receives gradients on every phone prompt.

---

# 3. JEPA, EMA and the “no backdrop” rule

The correct technical interpretation is:

> **No monolithic autoregressive token-CE backdrop dominates lifelong learning. Main knowledge learning happens through latent JEPA objectives. Gradients/backprop still update the trainable student/context/predictor parameters. EMA updates only the target path.**

JEPA path:

```text
context x
   ↓
Context Encoder θ
   ↓
z_context
   ↓
Predictor ψ
   ↓
z_pred
          target y
             ↓
       Target Encoder ξ
             ↓
          z_target
```

Loss:

```text
L_JEPA = D(z_pred, stopgrad(z_target))
```

Updates:

```text
θ, ψ ← gradients / optimizer
ξ    ← EMA(ξ, θ)
```

EMA does not “learn” by itself. It provides a slowly moving target. A system that removes all gradient computation because it uses JEPA cannot learn representations.

## 3.1 No global backward graph

V13 also avoids the opposite failure mode: one scalar loss backpropagated through A+B+C simultaneously.

Independent learners:

```text
Gist-JEPA        → Gist optimizer / rollback
Detail-JEPA      → Detail optimizer / rollback
Cross A→B JEPA   → bridge optimizer / rollback
Cross B→A JEPA   → bridge optimizer / rollback
Judge-JEPA       → Judge optimizer / rollback
World-JEPA       → world predictor optimizer / rollback
Translator-JEPA  → student/translator optimizer / rollback
Output retention → Judge language optimizer / rollback
Meta-routing     → controller optimizer / rollback
```

Detach boundaries are explicit. A learning phase opens only the edges it intends to train.

## 3.2 Token CE still has one narrow role

The pretrained Judge already knows language, so V13 should not relearn grammar from random initialization. Token CE/preference losses may be used for **output calibration, style, exact corrections or translator/output alignment**, but not as the central world-learning objective.

---

# 4. Large architecture references

## 4.1 DeepSeek V4.1 Flash → Gist inspiration

Official release, 10 Sep 2026: 552B MoE; new Causal Encoder–Decoder architecture; 8B active on input and 16B on output; major KV-cache storage reductions relative to the previous generation; native visual understanding.

V13 borrows the *architecture principles*, not the checkpoint:

- asymmetric compute,
- broad sparse combination,
- context/cache efficiency,
- high-throughput input processing,
- native multimodal representation,
- separation of input and output costs.

Source: https://www.deepseek.com/en/news/deepseek-v4-1-flash/

## 4.2 GLM-5.3-Flash → Detail inspiration

Published architecture: 320B total / 18B active; hybrid sparse + linear attention; Manifold-Constrained Hyper-Connections; native multimodal base.

V13 borrows:

- hybrid state/attention processing,
- fine sparse specialization,
- residual/hyper-connection ideas,
- long-context efficiency,
- multimodal latent compatibility.

Source: https://huggingface.co/zai-org/GLM-5.3-Flash

These models are architectural ancestors. They are not mobile runtime bodies.

---

# 5. Current mobile bootstrap bodies

This is a **bootstrap proposal to benchmark**, not a frozen product decision.

## 5.1 Gist bootstrap — MobileMoE-S-QAT

Public properties:

- 1.3B total,
- 272M active,
- 20 layers,
- d=768,
- 60 routed experts,
- native Top-4,
- projected INT4 weight memory ≈0.68 GB,
- explicitly designed for on-device inference.

Role:

- higher-k hemisphere,
- coarse 8-token/group view above the native model,
- global semantic structure,
- broad expert combination.

Mismatch: MobileMoE uses many fine-grained experts, whereas the *ideal descendant Gist* ultimately wants fewer/larger V13-level semantic units. Therefore the checkpoint is a boot body, not the definition of the Gist architecture.

**License blocker:** MobileMoE is FAIR Noncommercial Research License. Research use is fine; a commercial/product release needs a separately licensed alternative/descendant.

Sources:
- https://huggingface.co/facebook/MobileMoE-M-Base
- https://huggingface.co/facebook/MobileMoE-L-QAT

## 5.2 Detail bootstrap — ETET-1.0-24E-1.8B-A1B Preview language body

Public properties:

- language body ≈1.42B,
- active ≈1B,
- 24 layers,
- layers 0–15 dense,
- layers 16–23 custom MoE,
- 3 experts per MoE layer,
- native Top-1,
- 131K context,
- built by Dense-to-MoE sparse upcycling from MiniCPM5-1B.

Role:

- lower-k hemisphere,
- 1-token/fine slots,
- exact/detail path,
- local contradiction detection.

It is genuinely architecturally different from MobileMoE. Its public repository also exposes sparse-upcycling and multimodal connector training, which is useful for V13 body evolution.

Caveat: the checkpoint is explicitly a Preview with limited fine-tuning. It is a research bootstrap, not a release-quality foundation.

Sources:
- https://huggingface.co/RheoEcho/ETET-1.0-24E-1.8B-A1B-Preview
- https://github.com/Rheoecho-Studio/ETETMoE

## 5.3 Dense Conscious Core — Qwen3.5-0.8B

Public text config:

- hidden 1024,
- 24 layers,
- linear-attention / full-attention hybrid,
- full attention every 4 layers,
- dense FFN 3584,
- 262K positions,
- MTP layer,
- Apache-2.0.

Role:

- Judge,
- Meta-Router,
- Cautiousness controller,
- Halting,
- Time,
- Ability,
- Unification,
- Memory requests,
- visible output.

It must not become a third world model that bypasses A/B. Its input is the processed V13 state; raw user tokens cannot become a hidden shortcut around both hemispheres.

Source: https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/config.json

## 5.4 Size envelope

```text
Gist   ~1.30B
Detail ~1.42B
Judge  ~0.80B
----------------
Total  ~3.52B stored language parameters
```

This is close to the requested class. It is **not** proof of a 6 GB runtime fit. Runtime must include quantization overhead, native states/KV, activations, page cache, Python/runtime, learner state and optimizer state.

## 5.5 Open-license Gist research alternative

Sutra-1.3B is Apache-2.0, 1.32B total / ~0.28B active, 48 routed + 1 shared expert, Top-4, MLA and DeepSeek-style auxiliary-loss-free routing. Architecturally it is attractive, but its own card says it was trained on only 18B tokens and is weak on facts and multi-step reasoning. It is a useful architecture experiment, not automatically the best semantic Gist.

Source: https://huggingface.co/Abhisingh-18/Sutra-1.3B-Chat

---

# 6. Full forward graph

```text
USER / PORT
    │
    ▼
INPUT + provenance
    │
    ▼
CONTEXT CONTROLLER
    ├─ recent exact context
    ├─ hot native KV/recurrent state
    ├─ compressed context
    ├─ Stream A latent memory
    ├─ Stream B exact memory
    └─ readable World Notebook
    │
    ├─────────────────────────────────────┐
    ▼                                     ▼
GIST BODY                           DETAIL BODY
MobileMoE-S boot                    ETET boot
higher-k / coarse                   lower-k / fine
8-token groups                      1-token slots
    │                                     │
    └───────── CORPUS CALLOSUM A↔B ───────┘
                      │
                      ▼
              GLOBAL WORKSPACE
       slots · ring · age · memory refs
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
 Cautiousness κ     Memory        World-JEPA
 disagreement       exact/latent  surprise
       └──────────────┼──────────────┘
                      ▼
                 Z_INQUISITION
                P1 ↔ P2 / modes
                      │
               adaptive rounds
                      │
                      ▼
            QWEN3.5-0.8B CORE
 Judge · Meta-Router · Halting · Time · Ability
                      │
                      ▼
                  OUTPUT
                      │
                      ▼
             feedback / outcome
                      │
                      ▼
                 EXPERIENCE
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
    Replay           JEPA           Memory
      │               │                │
      └───────────────┼────────────────┘
                      ▼
            multi-speed learning
                      │
         slow validated consolidation
```

---

# 7. BodyPort contract

Every body implements the same V13-facing interface:

```python
class BodyPort:
    def tokenize(self, text): ...
    def prefill(self, tokens, state=None): ...
    def readout(self): ...
    def hidden_slots(self): ...
    def native_state(self): ...        # KV / recurrent state
    def router_telemetry(self): ...
    def apply_fast_adapter(self, id): ...
    def export_adapter(self, id): ...
    def checkpoint_identity(self): ...
```

Optional:

```python
vision_port()
audio_port()
mtp_port()
expert_prefetch_hint()
```

Different tokenizers and hidden dimensions are allowed. Learned projections map them into the shared workspace.

---

# 8. Shared latent workspace

```text
Gist hidden d_G  → P_G→W → workspace d_W
Detail hidden d_D→ P_D→W → workspace d_W
Judge hidden d_C ↔ P_C↔W ↔ workspace d_W
```

The conceptual full blueprint may retain a 4096-d workspace; Android can start smaller. Workspace dimension is a preset, not the identity of the system.

The workspace contains:

- Gist contribution,
- Detail contribution,
- direct cross messages,
- Ring/modulation,
- age vector,
- memory references,
- previous state,
- world prediction,
- Inquisition candidates,
- Judge control state.

---

# 9. Corpus Callosum

Three channels:

1. **Latent slot channel:** main bidirectional cross-attention.
2. **Control metadata:** uncertainty, contradiction, route entropy, memory request.
3. **Bounded token channel:** requested only when literal details cannot survive latent compression.

No A/B weight merge occurs.

Biological split-brain/corpus-callosum research is used only as functional inspiration: specialization plus dynamic bidirectional coordination, not as proof that V13 reproduces human consciousness.

---

# 10. Cautiousness κ

κ is a sensor, not a truth oracle.

Inputs may include:

- A/B disagreement,
- cross-JEPA error,
- world-model surprise,
- exact-vs-latent memory conflict,
- Judge confidence,
- router instability,
- translator dependence.

Outputs:

- conflict,
- uncertainty,
- novelty.

Actions:

```text
increase Detail share
increase Inquisition depth
request exact memory
request token channel
lower learning confidence
continue thinking
```

κ never overwrites a fact by itself.

---

# 11. Nested Inquisition and MoP-JEPA

Workspace state is projected into `Z_Inq`.

P1 role:

- perturbation,
- counter-hypothesis,
- alternative interpretation.

P2 role:

- reconstruction,
- inconsistency detection,
- re-grounding.

P1/P2 are roles inside a shared trainable family, not two foundation models.

A July-2026 MoP-JEPA result is highly relevant: a single latent regressor can average multiple valid next states, while hard-assigned predictor mixtures can represent distinct successor modes. V13 should therefore allow multiple hard modes rather than force one averaged “future.”

Initial modes:

```text
M0 = P1 hypothesis
M1 = P2 reconstruction
```

Later:

```text
M2 = memory-consistent successor
M3 = novel-plausible successor
```

Candidate existence is not evidence of truth; Judge/Memory verification still applies.

Source: https://arxiv.org/abs/2607.05238

---

# 12. Adaptive thought depth

The historical 1..7 loop is the boot curriculum, not a metaphysical constant.

Each round estimates:

```text
expected quality gain
vs
compute + latency + thermal cost
```

Judge control tokens/states:

```text
CONTINUE
HALT
RECALL
VERIFY
TOKEN_CHANNEL
OUTPUT
```

A hard maximum and wall-clock deadline always exist.

---

# 13. Judge internals

Qwen3.5-0.8B supplies pretrained language/semantic competence. V13 adds shared-state heads for:

- quality,
- coherence,
- confidence,
- diversity,
- JEPA similarity,
- novelty/RND,
- Cautiousness,
- halting,
- time estimate,
- ability estimate,
- Gist/Detail allocation,
- memory request,
- translator reliance,
- unification,
- rule/security state,
- output mode.

The heads are not separate language models. They read the same Conscious Core state.

---

# 14. Judge-JEPA

Judge predicts its own next internal state:

```text
J_t + context → Predictor → Ĵ_(t+1)
                         compare
EMA target J_(t+1) ───────────┘
```

Judge surprise feeds Cautiousness and Halting.

This makes the “conscious core” a predictive control system rather than only a classifier.

---

# 15. Independent JEPA learners

V13 maintains at least:

1. **Gist-JEPA** — coarse/global masked/future representations.
2. **Detail-JEPA** — fine/local masked/future representations.
3. **Cross-JEPA Gist→Detail** — predicts relevant fine target from coarse context.
4. **Cross-JEPA Detail→Gist** — predicts coarse state from fine evidence.
5. **Judge-JEPA** — predicts future conscious/control state.
6. **World-JEPA** — predicts future workspace/world state.
7. **Translator-JEPA** — teaches body representations to match a temporary external port.

Each has independent optimizer, cadence, checkpoint and rollback.

Collapse controls can include VICReg variance/covariance and contrastive/InfoNCE terms. Batch-1 paths must not pretend covariance estimates are meaningful; they fall back to safe latent regression/normalization.

---

# 16. EMA implementation on mobile

The phone cannot keep three duplicate billion-parameter target models in active RAM.

Mobile v1 therefore starts with EMA targets at **adapter/readout/predictor level**:

```text
slow base body
+ live readout/adapter
+ EMA readout/adapter target
```

As hardware increases, EMA coverage can move deeper into the body.

This preserves the JEPA principle without pretending the phone can resident-load full live+target copies of every body.

---

# 17. Learning timescales

## 17.1 Instant state (per prompt)

No persistent weight update required:

- Gist/Detail mix,
- context choice,
- thinking depth,
- memory lookup,
- P1/P2 mode,
- translator gate for this case.

## 17.2 Fast persistent (seconds/minutes)

- Judge heads,
- P1/P2,
- Callosum/projectors,
- fast adapters,
- memory/replay priorities,
- temporary meta-routing policy.

## 17.3 Medium (after answer / idle / charging)

- Gist/Detail JEPA adapters,
- cross-JEPA,
- replay,
- translator internalisation,
- context policy,
- cache-quality adapters.

## 17.4 Slow consolidation

- selected real body parameters,
- durable expert specialization,
- stable routing priors,
- adapter-to-body consolidation.

This last phase is limited on the Redmi and can migrate to better hardware.

---

# 18. LoRA is scaffolding, not the brain

The latest design allows LoRA but changes its role.

Four classes:

```text
ACTIVE LoRA       = fast current plasticity
CONSOLIDATED LoRA = validated update waiting for merge
TRANSFER LoRA     = old body teaches new body
TRANSLATOR LoRA   = external capability teaches internal body
```

Long-term goal:

```text
fast adapter
→ validated by replay/regression
→ slow consolidation
→ real body knowledge
```

This reconciles “weights=knowledge” with practical mobile learning.

---

# 19. Memory-efficient real-weight learning

For stronger hardware, V13 evaluates full-weight optimizers such as:

- **GaLore / Q-GaLore:** low-rank gradient projection, full-parameter updates with reduced optimizer memory.
- **APOLLO/APOLLO-Mini:** compact gradient-scaling state with near-SGD optimizer-memory target.

These are consolidation tools, not magic phone-training solutions.

Sources:
- https://proceedings.mlr.press/v235/zhao24s.html
- https://arxiv.org/abs/2412.05270

---

# 20. Translator lifecycle

A Translator is a temporary teacher bridge.

```text
foreign modality / specialist output
            ↓
       Translator T
            ↓
         z_teacher
            ↓
         A/B bodies
            ↓
         z_student
```

Training uses independent objectives such as:

```text
JEPA future consistency
latent teacher/student alignment
real task outcome
retention on old skills
```

Gate:

```text
g_T ∈ [0,1]
```

is learned, not time-decayed blindly.

Retirement criteria:

- body-only performance close to translator-assisted,
- no old-skill regression,
- stable latent alignment,
- calibration preserved,
- enough diverse validation cases.

Then:

```text
active → shadow → occasional verification → archived
```

Archived translators can return after regression.

This is the generalised lesson behind unified multimodal training: use a projection/teacher to make a foreign representation native, then reduce the external dependency after the body has learned the mapping.

---

# 21. Body replacement

Bodies are replaceable organs; the brain history is not thrown away.

Protocol:

```text
1 snapshot old body
2 keep old body serving
3 load new body in shadow mode
4 learn projection compatibility
5 transfer adapter priors
6 Cross-LoRA/subspace mapping where valid
7 replay skill registry
8 match latent anchors
9 match outcomes and provenance behaviour
10 compare calibration/hallucination
11 gradual traffic shift
12 rollback window
13 retire old body after parity
```

Transfer package:

- source LoRAs,
- consolidated adapters,
- routing history,
- skill tests,
- exact experience samples,
- latent anchor pairs,
- world-state anchors.

Cross-LoRA is a candidate tool for heterogeneous LoRA projection; if it fails, the old body remains a teacher and latent distillation takes over.

Source: https://arxiv.org/abs/2508.05232

---

# 22. Router system

Three distinct routers:

## R1 Native router

Inside the pretrained MoE. Chooses actual experts.

## R2 V13 Meta-Router

Chooses:

- A/B share,
- compute budget,
- context budget,
- Gist grouping,
- Inquisition depth,
- translator use,
- wake/sleep,
- body choice.

## R3 Prefetch predictor

Only predicts likely future expert use for storage/cache. It never overrides R1.

Continual-learning literature warns that router/expert or router/LoRA co-drift can cause forgetting. V13 therefore logs router entropy, route-change rate, expert usefulness and adapter-path association, and gradually reduces router plasticity after stabilization.

Relevant sources:
- https://aclanthology.org/2026.acl-long.1474/
- https://arxiv.org/abs/2607.21978

---

# 23. Expert usefulness and future growth

Per expert:

```text
usage
quality_delta
latency_cost
memory_cost
skill_links
failure_links
route_stability
```

High usage is not automatically high value.

Future growth only occurs when persistent saturation + useful specialization + hardware budget justify it. Clone/split candidates are A/B tested and rolled back if worse.

---

# 24. Memory hierarchy

```text
M0 current latent state
M1 native hot KV/recurrent context
M2 compressed body-specific context
M3 Stream A persistent semantic latent
M4 Stream B exact provenance memory
M5 readable World Notebook
M6 cold flash archive
```

“Long context” therefore does not mean “keep all previous tokens active forever.”

---

# 25. Context controller

Per prompt, controller estimates:

- required evidence,
- memory budget,
- latency budget,
- body type,
- current κ,
- device state.

Then chooses cache/compression/retrieval policy.

**MetaKV** is the correct conceptual pattern: select compression configuration per prompt under latency/memory/quality constraints rather than one static cache policy.

Source: https://arxiv.org/abs/2609.07966

**SGD-KV** suggests allocating cache budget based on head summarisation roles. Its reported 75% reduction is a paper result on tested models, not a guaranteed V13 number.

Source: https://arxiv.org/abs/2609.03235

Exact memory remains a fallback when compressed state is uncertain.

---

# 26. Memory classes and provenance

## REAL

Exact human/environment evidence.

## WELT

Grounded condensates / world model.

## FREI

Dream, hypotheses, unverified generations.

## LANG

Long-term accepted condensates with source links.

## RULES

Confirmed policy text.

## PROTOCOL

Logs, never automatically facts.

Every important entry stores source type/id, timestamp, exact hash, derivation chain, confidence and confirmation status.

---

# 27. Plain-text World Picture

V13 periodically writes an auditable mirror:

```text
KNOWN
UNCERTAIN
RECENT CHANGES
RELATIONS
OPEN CONFLICTS
SKILLS
BODY STATE
AGE
SOURCES
```

This is not the primary latent world state. It is a readable recovery/audit surface. Every factual entry points back to exact provenance.

---

# 28. Experience and replay

Every interaction becomes a structured Experience record containing input, context IDs, A/B states, workspace before/after, Judge state, routing, translator usage, answer, feedback/outcome and sources.

Feedback may be:

```text
gut
schlecht
note N
correct: ...
environment success/failure
tool/test result
teacher comparison
```

Feedback does not directly rewrite truth. It changes labels, replay priority and learning targets.

Recent Chain-of-Experience work supports the systems-level principle of iterative experience/feedback loops. V13 uses that loop but keeps its internal objective latent-first rather than converting everything to SFT.

Source: https://arxiv.org/abs/2608.18027

NeoHorse similarly motivates a closed outer loop of routing → experience collection → evaluation → training selection → update → re-evaluation.

Source: https://arxiv.org/abs/2609.08183

---

# 29. Spaced replay

Uniform replay is not enough. Each experience keeps:

```text
last_review
review_interval
forgetting_risk
importance
error_history
skill_links
```

Spaced Repetition Training (Aug 2026) shows that per-example review scheduling can substantially improve old-knowledge retention over naive continual pretraining in its experiments.

Source: https://arxiv.org/abs/2608.17530

Initial V13 priority:

```text
forgetting risk
+ recent error
+ source importance
+ contradiction
+ skill dependency
+ underexposure
- redundancy
```

---

# 30. Dreaming

Historical baseline: approximately 7% free-Dream opportunity.

Modern interpretation: 7% is a compute budget baseline, not a probability that hallucinations become truth.

Dream seeds:

- grounded workspace,
- unresolved conflicts,
- high-surprise transitions,
- skill gaps,
- memory combinations.

Correct Dream learning:

```text
grounded s
→ perturb/dream
→ candidate s'
→ world predictor
→ plausibility/evidence checks
→ FREI transition
→ JEPA replay candidate
```

A `no_grad` dream loop that never creates learning transitions is not genuine learning.

---

# 31. Age

Age is not just tokens processed.

```text
Age = {
  experience_age,
  competence_age,
  stability_age,
  memory_age,
  body_age,
  feedback_age
}
```

## AGE 0 Boot

- strong external help,
- conservative persistent updates,
- low Dream influence,
- heavy provenance checks,
- body consolidation almost zero.

## AGE 1 Acclimation

Learns Gist/Detail routing, halting, memory relevance, Judge calibration and P1/P2 dynamics.

## AGE 2 Stable learning

Selective replay, reduced router LR, stronger adapter learning, translator ablation begins.

## AGE 3 Self regulation

More autonomous compute/context/replay/Dream/translator decisions.

## AGE 4 Consolidation

Validated fast learning can move into real body weights on capable hardware.

## AGE 5 Expansion

New bodies/modalities/specialists are integrated with less scaffolding.

No age unlock is granted from token count alone; experience + competence + stability are all required.

---

# 32. Age-dependent plasticity

Typical trend:

```text
fast adapter LR       high → lower
router LR             medium → low
memory policy LR      adaptive
body LR               tiny throughout
consolidation budget  low → higher when stable
teacher reliance      high → low
translator reliance   high → low
```

Novel domains may temporarily reopen plasticity.

Penalty/external constraint can decay with demonstrated competence but keeps a non-zero floor.

---

# 33. Regression shield

Every persistent update is evaluated on:

```text
NEW       new capability
OLD       historical capability
IDENTITY  stable behaviour
MEMORY    source/retrieval correctness
HALLUC    known uncertainty cases
ROUTER    route stability
```

Failure path:

```text
rollback
→ lower plasticity
→ increase replay
→ mark harmful experience/update
```

Checkpoints are modular: a bad Gist update does not automatically roll back Judge or Detail.

---

# 34. Android runtime reality

The first phone runtime should be split:

```text
Python / Termux
  orchestration
  memory/provenance
  learning scheduler
  JEPA microlearners
  checkpoint/debug

Native quantized backend
  tokenizer
  body forward
  matmul
  native KV/recurrent state
  MoE expert dispatch
  cache/prefetch
```

Sparse activation reduces FLOPs but does not erase total weight-traffic cost. Expert paging/caching must be measured; mmap alone is not assumed to provide perfect expert offload.

---

# 35. Quantized inference vs learning masters

Do not attempt to SGD-update a GGUF mmap file.

Persistent learnable parameters use:

```text
master/trainable state
      ↓
validated update
      ↓
quantized export
      ↓
inference copy
```

On phone, the master state is limited mainly to thin modules/adapters and selected slices. Full deep body consolidation happens blockwise or on stronger hardware.

---

# 36. Phone-first learning scope

The Redmi version should first prove persistent learning in:

- Workspace projections,
- Corpus Callosum,
- Cautiousness,
- P1/P2,
- Judge heads,
- Judge-JEPA predictor,
- body readout adapters,
- fast LoRAs,
- replay priorities,
- memory policy.

Only after memory/thermal measurements should selected base-model slices be opened.

This is not “freezing forever”; it is staged plasticity.

---

# 37. Workstation consolidation

A phone can later send a signed/versioned learning package to stronger hardware:

```text
experience
adapters
latent anchors
skill tests
world state
```

Workstation performs:

- deeper JEPA updates,
- selected full-weight consolidation,
- GaLore/APOLLO experiments,
- body upcycling,
- translator absorption,
- regression suite.

Then a new quantized body is returned to the phone and rolled out through parity tests.

The system still works offline without a workstation; stronger hardware is acceleration, not a permanent cloud dependency.

---

# 38. Body swap and skill preservation

Skill registry stores:

```text
skill_id
success tests
representative experiences
body dependencies
memory dependencies
last use
forgetting risk
teacher dependency
translator dependency
adapter ids
```

New body runs shadow mode, receives latent anchor pairs and skill replay, and only replaces the old one after parity in capability, grounding, calibration and latency.

“Copy a LoRA and hope” is not sufficient.

---

# 39. Multimodal rollout

Development order:

```text
TEXT
→ IMAGE
→ AUDIO
→ VIDEO
→ ACTION/TOOLS
```

The port API is modality-neutral from day one.

First multimodal experiment should be Image:

```text
strong image teacher
→ z_teacher
→ tiny projection + A/B
→ body learns mapping
→ teacher ablation
→ retention test
```

The same translator lifecycle then applies to audio/video/tools.

---

# 40. Testing discipline

## Architecture gates

- real Gist loads,
- real Detail loads,
- real Judge loads,
- three different intended roles,
- native routers preserved,
- A/B direct channel works,
- no raw-input shortcut around A/B.

## Learning gates

- intended parameters change,
- target path receives no gradient,
- EMA moves correctly,
- independent optimizers stay isolated,
- JEPA loss improves without collapse.

## Memory gates

- exact source round-trip,
- latent memory differs from exact memory,
- self-generated text never becomes source automatically,
- restart persistence.

## Transfer gates

- translator-assisted vs body-only comparison,
- old-body vs new-body parity,
- rollback works.

## Android gates

- RSS/peak RSS,
- prefill/decode latency,
- latent-loop latency,
- thermal stability,
- page faults/storage reads,
- crash recovery.

No guessed performance number becomes a project fact.

---

# 41. Implementation repository

```text
v13/
  brain/
    system.py
    workspace.py
    callosum.py
    cautiousness.py
    inquisition.py
    judge.py
    age.py

  bodies/
    base.py
    mobilemoe.py
    etet.py
    qwen35.py
    registry.py

  learning/
    jepa_base.py
    gist_jepa.py
    detail_jepa.py
    cross_jepa.py
    judge_jepa.py
    world_jepa.py
    replay.py
    consolidation.py
    transfer.py
    regression.py

  memory/
    real.py
    welt.py
    frei.py
    lang.py
    graph.py
    provenance.py

  context/
    controller.py
    native_state.py
    compression.py
    stream_a.py
    stream_b.py

  adapters/
    active.py
    consolidated.py
    transfer.py
    translator.py

  ports/
    text.py
    image.py
    audio.py
    teacher.py
    tools.py

  runtime/
    android.py
    native_backend.py
    quant.py
    mmap.py
    expert_cache.py
    thermal.py

  tests/
    ...
```

The research code becomes modular. The end-user installer can still be one command.

---

# 42. Build sequence

**B0 — Canonical requirements registry**  
Parse historical V13 material, preserve user decisions, mark conflicts and assistant hallucinations.

**B1 — Real body benchmark harness**  
Load MobileMoE/ETET/Qwen, inspect real hidden states, native routers, RAM and latency.

**B2 — BodyPort adapters**  
Stable interfaces independent of model family.

**B3 — Dual-resolution forward**  
8-token Gist vs 1-token Detail.

**B4 — Corpus Callosum**  
Bidirectional latent cross-attention.

**B5 — Shared Workspace**  
Persistent latent state and projections.

**B6 — Real Judge/output**  
Qwen core + V13 heads, visible language.

**B7 — Cautiousness + Halting**  
Conflict/surprise and finite adaptive thinking.

**B8 — Inquisition**  
P1/P2 / MoP-JEPA modes.

**B9 — Memory + provenance**  
REAL/WELT/FREI/LANG, graph and exact archive.

**B10 — JEPA learners**  
Gist/Detail/Cross/Judge/World.

**B11 — Fast continual adapters**  
Online/after-answer/idle learning.

**B12 — Replay/SRT**  
Forgetting-aware review scheduling.

**B13 — Translator lifecycle**  
Temporary teacher, learned ablation, retention.

**B14 — Body transfer**  
Cross-LoRA/latent parity/shadow rollout.

**B15 — Context engine**  
Adaptive cache/compression/storage.

**B16 — Android native runtime**  
Quantized bodies, cache, expert prefetch.

**B17 — Slow full-weight consolidation**  
GaLore/APOLLO on capable hardware.

**B18 — Long-run validation**  
Multi-hour/day restart, forgetting, thermal and memory-growth tests.

---

# 43. Current decision table

| Role | Bootstrap | Native role fit | Problem |
|---|---|---|---|
| Gist | MobileMoE-S-QAT | 1.3B, Top-4, 272M active, mobile-first | noncommercial license; expert geometry not ideal long-term |
| Gist alt | Sutra-1.3B | Apache, Top-4, MLA, DeepSeek-like routing | small training corpus / weak reliability |
| Detail | ETET 1.8B Preview LM | ~1.42B, Top-1, different architecture, sparse-upcycled | preview quality; only 3 experts per MoE layer |
| Judge | Qwen3.5-0.8B | dense/hybrid, modern, Apache, real language | must not bypass A/B or become third world model |

The long-term desired descendant geometry stays:

```text
GIST:   same size class, fewer/larger semantic units, higher k, coarse hierarchy
DETAIL: same size class, finer specialization, lower k, fine hierarchy
JUDGE:  <1B dense semantic/control model
```

If no public checkpoint fits perfectly, V13 evolves toward that geometry through continued training/upcycling rather than pretending a mismatched body already has it.

---

# 44. Definition of “implemented” and “finished”

A feature is **implemented** only when:

```text
spec + code + test
```

A feature is **validated** only when:

```text
test + benchmark + regression result
```

V13 v1 is not finished because a smoke test says OK. It is finished only when one end-to-end system demonstrates:

- two real different pretrained bodies,
- real sparse inference,
- real dense Judge output,
- Gist/Detail resolution difference,
- direct A↔B communication,
- persistent Workspace,
- Cautiousness-driven control,
- P1/P2 latent iteration,
- exact + latent memory,
- provenance,
- JEPA parameter learning,
- EMA targets,
- continual replay without immediate forgetting,
- translator internalisation and removal,
- passive adapter/body transfer,
- body swap with retained skills,
- restart persistence,
- bounded Android operation.

---

# 45. Research source inventory

1. DeepSeek — DeepSeek-V4.1-Flash, 10 Sep 2026  
   https://www.deepseek.com/en/news/deepseek-v4-1-flash/

2. Z.ai — GLM-5.3-Flash  
   https://huggingface.co/zai-org/GLM-5.3-Flash

3. Meta — MobileMoE  
   https://huggingface.co/facebook/MobileMoE-M-Base

4. RheoEcho — ETETMoE  
   https://huggingface.co/RheoEcho/ETET-1.0-24E-1.8B-A1B-Preview  
   https://github.com/Rheoecho-Studio/ETETMoE

5. Qwen — Qwen3.5-0.8B  
   https://huggingface.co/Qwen/Qwen3.5-0.8B

6. Huang, LeCun, Balestriero — LLM-JEPA  
   https://arxiv.org/abs/2509.14252

7. Song et al. — MoP-JEPA  
   https://arxiv.org/abs/2607.05238

8. Tu et al. — Chain-of-Experience  
   https://arxiv.org/abs/2608.18027

9. Atreya et al. — Spaced Repetition Training  
   https://arxiv.org/abs/2608.17530

10. NeoHorse Team — NeoHorse-1  
    https://arxiv.org/abs/2609.08183

11. Wang et al. — MetaKV  
    https://arxiv.org/abs/2609.07966

12. Liu et al. — SGD-KV  
    https://arxiv.org/abs/2609.03235

13. Xia et al. — Cross-LoRA  
    https://arxiv.org/abs/2508.05232

14. Hou et al. — PASs-MoE, ACL 2026  
    https://aclanthology.org/2026.acl-long.1474/

15. Yang et al. — MoE²-LoRA  
    https://arxiv.org/abs/2607.21978

16. Zhao et al. — GaLore  
    https://proceedings.mlr.press/v235/zhao24s.html

17. Zhu et al. — APOLLO  
    https://arxiv.org/abs/2412.05270

---

# 46. Final architecture sentence

**V13 is a persistent dual-MoE brain in which a higher-k coarse Gist body and a lower-k fine Detail body exchange information directly through a learned latent callosum, write into a common workspace, are challenged by a multi-mode latent Inquisition, and are managed/rendered by a small dense Judge; the system learns primarily through separate JEPA objectives with stop-gradient EMA targets, experience replay, temporary translators and transferable adapters, while validated knowledge is slowly consolidated into real model weights and survives body replacements and hardware generations.**
