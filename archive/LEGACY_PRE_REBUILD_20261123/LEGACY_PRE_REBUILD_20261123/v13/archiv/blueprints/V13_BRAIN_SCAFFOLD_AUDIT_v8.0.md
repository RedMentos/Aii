# V13 Brain-Scaffold Audit v8.0

## Purpose

This audit treats V13 as a brain scaffold that can later learn and inhabit different bodies, including a purely digital body, tools, sensors, Android hardware, and eventually richer physical embodiment.

The goal is not to simulate a human brain neuron-for-neuron. The goal is to preserve computational principles that appear useful in brains while using modern pretrained AI bodies, JEPA-style latent prediction, sparse routing, persistent memory, continual learning, and modular replacement.

This document separates four categories:

- **KEEP** — already strong in V13 and should remain.
- **STRENGTHEN** — present, but underspecified.
- **ADD** — materially missing.
- **RETIRE** — old claims or implementations that should no longer define the system.

---

# 1. Existing V13 core that should be kept

The existing project already contains a much richer scaffold than a normal LLM stack.

## 1.1 Two distinct sparse hemispheres

Keep:

- Gist and Detail as different model families/architectures.
- Gist coarse/global.
- Detail fine/local.
- direct bidirectional communication.
- shared latent workspace.
- adaptive within-prompt Gist/Detail allocation.
- native model routers preserved.
- V13 meta-routing above model routers.

## 1.2 Small conscious core

Keep the small dense core as:

- Judge,
- semantic control state,
- final rendering/output,
- confidence/coherence integration,
- meta-routing interface,
- halting interface,
- memory request interface.

However, some control duties should move out of the Judge into dedicated subcortical-like loops.

## 1.3 Latent-first learning

Keep:

- Gist-JEPA,
- Detail-JEPA,
- Cross-JEPA,
- Judge-JEPA,
- World-JEPA,
- Translator-JEPA,
- separate optimizers/cadences,
- stop-gradient target representations,
- EMA target paths.

Important clarification:

JEPA changes the learning target, not the existence of gradients.

## 1.4 Multiple learning timescales

Keep:

- instant state adaptation,
- fast persistent adaptation,
- medium replay/adapter learning,
- slow body consolidation.

## 1.5 Memory separation

Keep:

- REAL,
- WELT,
- FREI,
- LANG,
- exact provenance memory,
- semantic latent memory,
- readable world notebook,
- replay scheduling.

## 1.6 Age

Keep Age as a multidimensional developmental state, not a token counter.

Useful dimensions:

- experience age,
- competence age,
- stability age,
- memory age,
- body age,
- feedback age.

## 1.7 Translator / Teacher lifecycle

Keep the concept that temporary heavy teachers can help teach a representation and later become less necessary.

But distinguish:

- temporary heavy teacher,
- permanent lightweight sensory transducer.

A raw camera/audio stream always needs some physical/numerical interface into the model. What can disappear is the heavy teacher/encoder, not necessarily every projection layer.

## 1.8 Body replacement

Keep:

- shadow mode,
- latent anchors,
- skill registry,
- transfer adapters,
- replay,
- parity tests,
- rollback.

---

# 2. New central law: activated-path local plasticity

This should become a core V13 law.

## 2.1 Why

The old files already contained the seed:

- only hit slices are copied into trainable master form,
- one layer × one model per learning step,
- no single global backward pass,
- Judge and routing feedback modulate which paths are strengthened.

This should be generalized.

## 2.2 Local Plasticity Law

Every trainable local unit has:

- activation state,
- eligibility trace,
- local predictive error,
- modulatory signal,
- plasticity state.

Conceptually:

```text
local activation
    ↓
eligibility trace e_i
    ↓
local JEPA prediction error δ_i
    ↓
global / regional modulators m
    ↓
plasticity gate
    ↓
Δθ_i
```

Approximate rule:

```text
Δθ_i ∝ e_i × δ_i × m_i
```

where:

- `e_i` says which path actually participated,
- `δ_i` is a local predictive/representation error,
- `m_i` says whether the experience deserves consolidation.

Inactive experts should generally not receive task-specific persistent updates from that experience.

## 2.3 Eligibility trace contents

For a routed expert/layer/path:

- input activation summary,
- output activation summary,
- routing probability,
- contribution to workspace,
- local surprise,
- timestamp,
- decay constant,
- source/experience id.

The trace is temporary.

It is not yet a weight update.

## 2.4 Third-factor modulation

Possible modulators:

- actual outcome,
- human correction,
- world-model surprise,
- Cautiousness conflict,
- Judge calibration error,
- memory contradiction,
- skill importance,
- replay priority,
- Age/metaplasticity state.

This separates:

```text
participated
```

from:

```text
should be changed
```

---

# 3. Major missing system: metaplasticity

This is one of the most important missing pieces.

V13 currently has learning rates, Age and rollback, but it still lacks a formal mechanism that learns **how plastic each local pathway is allowed to be**.

## 3.1 Add a plasticity state per unit

Each trainable region receives:

```text
plasticity_state {
    base_lr,
    eligibility_decay,
    consolidation_threshold,
    stability_score,
    novelty_sensitivity,
    saturation,
    last_major_update,
    reopen_factor
}
```

## 3.2 Why

Without metaplasticity:

- frequently active experts may drift constantly,
- a feedback loop can reinforce itself,
- mature skills may remain too plastic,
- new domains may fail to reopen learning.

## 3.3 Rule

Plasticity should itself change slowly.

Example:

```text
stable + frequently correct
→ lower plasticity

new domain + high prediction error
→ temporary reopen

conflicting evidence
→ increase verification before learning

repeated failure
→ reopen relevant local pathways
```

Age becomes one input to metaplasticity, not the sole controller.

---

# 4. Major missing system: homeostasis / inhibitory balance

Hebbian/local predictive learning alone can destabilize a network.

V13 needs a homeostatic controller distinct from task learning.

## 4.1 What it monitors

Per expert/path:

- activation frequency,
- average norm,
- route probability,
- contribution magnitude,
- update frequency,
- gradient/update magnitude,
- saturation,
- deadness.

## 4.2 What it can do

Slowly:

- adjust router bias,
- adjust local gain,
- normalize update budget,
- increase inhibition on chronically dominant paths,
- reopen dead but useful paths,
- reduce plasticity in unstable loops.

## 4.3 Important distinction

Homeostasis should not force equal expert usage.

It should keep the system inside a stable operating envelope.

Useful specialization remains allowed.

---

# 5. Major missing system: a real thalamic-style relay

The old files used “thalamus” mostly as a filter metaphor.

That is not enough.

Modern neuroscience increasingly treats thalamic pathways as active coordinators of cortical communication and uncertainty-sensitive control.

V13 should therefore add a small **Thalamic Relay / Dynamic Network Gate**.

## 5.1 Function

It decides which signals are allowed to become globally relevant.

Inputs:

- sensory ports,
- memory candidates,
- Gist messages,
- Detail messages,
- tool results,
- exact evidence,
- surprise/conflict,
- current task.

Outputs:

- workspace admission,
- inter-region routing,
- priority,
- suppression,
- refresh request.

## 5.2 Why separate it from Judge

The Judge should not perform every low-level traffic decision.

The thalamic relay is faster and more mechanical.

The Judge works on the selected workspace.

Conceptually:

```text
many candidate signals
        ↓
THALAMIC RELAY
        ↓
selected / amplified network
        ↓
GLOBAL WORKSPACE
        ↓
JUDGE
```

---

# 6. Major missing system: basal-ganglia-like action / mental-action selection

V13 already has Halting and Meta-Routing, but the Judge is overloaded.

Add a dedicated **Action Gating Loop**.

## 6.1 Candidate actions

Not only physical actions.

Mental actions:

- recall memory,
- ask Gist,
- ask Detail,
- open exact source,
- run another Inquisition round,
- call a tool,
- update world state,
- suppress a candidate,
- speak,
- wait,
- ask user.

Physical/digital actions:

- tool call,
- file edit,
- shell action,
- API call,
- later motor action.

## 6.2 Function

```text
candidate actions
      ↓
value / expected outcome
      ↓
competition
      ↓
selected action
      ↓
execute
```

Outcome updates action values.

The Judge proposes/frames goals.

The Action Gate chooses and sequences actions.

This is closer to cortical–basal-ganglia cooperation than making the Judge a monolithic executive.

---

# 7. Major correction: do not remove the cerebellar function

Older V13 material sometimes treated the cerebellum as “only body coordination” and therefore removable in a body-less system.

That should be retired.

The cerebellum is strongly implicated in prediction, error correction, timing, motor learning, internal models and cognitive functions.

A V13 brain scaffold should include a **Fast Forward Controller** even before it has a physical body.

## 7.1 Digital use

For tool use:

```text
planned tool action
      ↓
FAST FORWARD MODEL
      ↓
predicted result / latency / side effects
      ↓
actual result
      ↓
fast error correction
```

## 7.2 Later body

For a physical body:

```text
desired state
      ↓
inverse/action model
      ↓
motor command
      ↓
forward model predicts sensory outcome
      ↓
compare actual feedback
      ↓
correct
```

## 7.3 Relationship to World-JEPA

World-JEPA is broad and semantic.

The Cerebellar/Fast Forward Controller is:

- faster,
- lower-level,
- action-conditioned,
- timing-sensitive,
- specialized for repeated sensor-action mappings.

Do not merge these into one model.

---

# 8. Major missing system: corollary discharge / self-vs-world tagging

This is especially important for a digital agent.

The current provenance system distinguishes sources in memory, but the online action loop lacks a formal **self-action copy**.

## 8.1 Rule

Every action emits a parallel internal copy:

```text
ACTION COMMAND
   ├─→ environment/tool
   └─→ corollary copy
             ↓
        expected feedback
```

When new input arrives:

```text
observed input
vs
predicted consequence of self-action
```

The system can mark:

- self-generated,
- externally generated,
- mixed,
- uncertain.

## 8.2 Why useful

This directly helps with:

- tool outputs,
- own file edits,
- generated text,
- external retrieval,
- hallucination/source confusion,
- later robotics.

It also complements provenance.

Provenance says where a stored item came from.

Corollary discharge says whether a current change was caused by the system itself.

---

# 9. Major missing system: explicit body schema / digital embodiment model

The project says the brain should later learn a body.

Then the scaffold needs a **Body Schema** now.

It should begin with the digital body.

## 9.1 Digital body state

Examples:

- available RAM,
- storage,
- battery,
- temperature,
- network state,
- tools installed,
- permissions,
- files accessible,
- sensors available,
- current process state,
- model bodies loaded,
- latency,
- action costs.

## 9.2 Body schema API

```text
capability
action
expected cost
expected latency
expected observation
risk
permission
reliability
```

## 9.3 Why

This is the digital equivalent of knowing:

- what effectors exist,
- what sensors exist,
- what actions are possible,
- what their costs are.

Later physical embodiment plugs into the same contract.

---

# 10. Major missing system: affordance learning

A body schema says what the system can do.

Affordance learning says what actions are possible **in the current environment**.

Example:

```text
file path
→ editable?
→ readable?
→ executable?

web page
→ searchable?
→ clickable?
→ authenticated?

robot object
→ graspable?
→ movable?
```

Affordances belong between perception/world model and Action Gate.

---

# 11. Action-conditioned World-JEPA must become mandatory

Current V13 World-JEPA often predicts:

```text
state_t → state_(t+1)
```

That is insufficient for agency.

It should predict:

```text
(state_t, action_t) → state_(t+1)
```

and ideally:

```text
(state_t, action_t, body_state_t)
→
(state_(t+1), observation_(t+1), cost)
```

This is essential for planning.

Without action conditioning, the system learns what tends to happen, not what **its actions cause**.

---

# 12. Event segmentation

The current memory design is heavily turn/message oriented.

Human episodic memory is better described as events.

Prediction error is strongly linked to event boundaries.

Add an **Event Boundary Detector**.

## 12.1 Boundary signals

- sharp world-model surprise,
- goal change,
- context shift,
- tool/action completion,
- source change,
- time gap,
- user topic shift.

## 12.2 Event record

```text
event_id
start_state
goal
observations
actions
outcomes
important moments
end_state
sources
```

Replay should often replay events, not isolated messages.

---

# 13. Multiple replay systems

Current V13 replay is too unified.

2026 neuroscience evidence shows procedural replay can occur outside the hippocampus.

Therefore separate at least:

## Episodic replay

Experience/event memory.

## Procedural replay

Skills, routes, tool/action sequences.

## Semantic replay

Concept/world-state consolidation.

## Counterfactual replay

Dream/Inquisition-generated alternatives.

Different replay stores should have different admission rules and frequencies.

---

# 14. Sleep should become multiple offline phases

One generic Dream mode is too coarse.

Use functional phases, without pretending to simulate biological sleep exactly.

## SLEEP-A: replay/consolidation

- grounded episodic replay,
- exact source retained,
- strengthen stable transitions,
- transfer from fast memory to slow weights.

## SLEEP-B: abstraction / recombination

- semantic compression,
- schema formation,
- Gist building,
- controlled Dream combinations.

## SLEEP-C: homeostatic renormalization

- reduce runaway gains,
- normalize route/activity statistics,
- prune redundant traces,
- lower stale plasticity.

The historical 7% Dream budget can remain a default compute budget, not the definition of sleep.

---

# 15. Neuromodulation should be a vector, not one scalar

Judge/κ/Outcome currently risk collapsing into one “good/bad” learning factor.

A more brain-inspired and technically useful design uses several modulatory channels.

Example V13 Neuromodulator Bus:

```text
M_value       reward/outcome prediction error
M_surprise    unexpected event
M_uncertainty ambiguity / hidden-state uncertainty
M_novelty     unfamiliarity
M_arousal     urgency / resource mobilisation
M_safety      constraint / danger
M_social      user approval / correction
```

These are computational signals, not claims of literal dopamine/acetylcholine/etc.

Different learners subscribe to different channels.

Example:

```text
router plasticity
← uncertainty + novelty

action-value learning
← outcome error

memory encoding
← novelty + surprise + importance

body consolidation
← stability + repeated success

Cautiousness
← conflict + uncertainty
```

This is much better than one global reward.

---

# 16. Predict both WHAT and WHEN

The current world model mostly asks what state comes next.

Timing should be explicit.

Each event/action prediction can contain:

```text
identity
expected time
probability
uncertainty
```

Useful for:

- tool latency,
- action sequencing,
- timeout/halting,
- causal inference,
- delayed feedback.

The project already has a Time head, but timing should also be part of local predictive state, not only an output estimate.

---

# 17. Workspace should become slot-based, not just one residual vector

A single shared residual risks:

- destructive overwrite,
- source mixing,
- loss of simultaneous hypotheses,
- poor provenance.

Use a small set of persistent workspace slots.

Example:

```text
slot 0 current goal
slot 1 active percept
slot 2 Gist hypothesis
slot 3 Detail evidence
slot 4 contradiction
slot 5 action plan
slot 6 exact memory pointer
slot 7 self/body state
```

The slots can remain latent and dynamic.

The Judge sees/broadcasts over them.

Write access is gated by the Thalamic Relay.

This is closer to functional working-memory competition than one giant overwrite tensor.

---

# 18. Working-memory interference control

Add explicit operations:

```text
WRITE
REFRESH
LOCK
REPLACE
SUPPRESS
BIND
RELEASE
```

A slot should be able to survive several reasoning cycles even if new information arrives.

This avoids the current “everything writes to Ring” failure mode.

---

# 19. Source binding inside latent state

Provenance currently exists mostly in memory metadata.

Important workspace representations should carry lightweight source tags.

Example:

```text
latent_slot {
  vector,
  source_ref,
  confidence,
  self_generated,
  age,
  timestamp
}
```

The vector itself is not enough.

This helps prevent self-generated hypotheses from losing their status after several latent transformations.

---

# 20. Causal memory graph

The memory graph already has relations.

Extend it with explicit action/causal edges:

```text
CAUSES
ENABLES
PREVENTS
PREDICTS
RESULTED_IN
SELF_GENERATED_BY
OBSERVED_AFTER
```

The graph should distinguish correlation from action-conditioned evidence.

---

# 21. Synaptic tagging / consolidation tags

Eligibility traces are short.

Some useful experiences need a slower “tag” before permanent consolidation.

Add a Consolidation Tag:

```text
candidate update
↓
tagged
↓
reappears in replay / receives confirming outcome
↓
promote
```

This prevents one surprising event from immediately changing long-term body weights.

---

# 22. Local JEPA should exist below whole-body level

Current designs often describe one Gist-JEPA and one Detail-JEPA.

For local plasticity, each important region should be able to learn from a local predictive target.

Possible hierarchy:

```text
expert-local predictor
layer-local predictor
hemisphere predictor
cross-hemisphere predictor
workspace/world predictor
```

Not all need to run all the time.

Only active paths instantiate/store local traces.

This makes credit assignment more local.

---

# 23. Dendritic-like compartment analogy can be useful, but optional

A practical analogue:

```text
feedforward representation
+
top-down context
+
modulatory learning signal
```

kept as separable inputs until late integration.

This resembles compartmentalized computation without pretending to model real dendrites.

Useful for:

- local prediction error,
- separating context from teaching signals,
- preventing teacher leakage.

---

# 24. Separate perception confidence from belief confidence

Current confidence often risks mixing:

- model confidence,
- evidence quality,
- memory confidence,
- action prediction confidence.

They should be separate.

Recommended:

```text
percept_confidence
source_confidence
world_belief_confidence
action_outcome_confidence
judge_output_confidence
```

Cautiousness integrates them but does not replace them.

---

# 25. Judge should be decomposed functionally without splitting the model

Keep one dense semantic core.

Move these functions outside as lightweight loops:

- Thalamic Relay,
- Action Gate,
- Fast Forward Controller,
- Homeostatic Controller,
- Neuromodulator Bus.

Judge remains the conscious semantic controller.

This reduces Judge overload without creating five extra language models.

---

# 26. Self-model

V13 needs an explicit model of itself.

Not autobiographical prose alone.

Structured self-state:

```text
current bodies
current skills
known limitations
available tools
body capabilities
memory health
confidence calibration
learning status
current age
current open goals
current resource state
```

This helps planning and prevents impossible actions.

---

# 27. Identity continuity should not equal weight continuity

Body swaps are allowed.

Therefore identity continuity should be defined through:

- persistent memory,
- skill registry,
- goals/rules,
- world model,
- self-model,
- latent anchor history,
- behavioural continuity.

Not “same exact neural weights.”

This makes hardware/model evolution coherent.

---

# 28. Development should be skill-sensitive, not globally age-sensitive

Age already has multiple dimensions.

Improve it by giving subsystems their own developmental maturity.

Example:

```text
language_age
tool_age
vision_age
memory_age
body_age
social_age
```

A newly attached vision port can be “young” while language is mature.

This is much more realistic than one global age.

---

# 29. Critical-period analogue

For a newly attached port/body:

```text
early:
high plasticity
high teacher reliance
high replay
strong provenance

later:
plasticity falls
teacher gate falls
stable skills consolidate
```

This provides a principled use for Age/metaplasticity.

---

# 30. Body learning should include inverse and forward models

When a new body is attached:

## Forward

```text
action → expected sensation/state
```

## Inverse

```text
desired state → candidate action
```

The inverse model can be learned slower and verified through the forward model.

For digital tools:

```text
goal → tool/action plan
action → predicted tool result
```

For physical bodies the same API generalizes to motor control.

---

# 31. Reflex layer

A future physical/digital body needs fast reactions that do not wait for full conscious reasoning.

Examples:

- thermal overload,
- imminent timeout,
- API failure,
- unsafe physical condition,
- memory corruption,
- process OOM.

Add a small hard/learned Reflex layer below the Judge.

The Judge can later interpret what happened.

---

# 32. Resource interoception

The project already monitors thermal/RAM.

Make this part of the internal state, not just runtime telemetry.

Digital interoception:

```text
battery
temperature
RAM pressure
storage pressure
latency
network
model load
error rate
```

These signals can modulate:

- Dream,
- learning,
- body wake/sleep,
- context budget,
- action selection.

This is the first actual “body feeling” V13 can have on Android.

---

# 33. Reward is not truth

Important existing rule to keep.

Outcome/value signals decide what behaviour helped.

They do not decide whether a factual proposition is true.

Truth/evidence path and value/action path remain separate.

This prevents reward hacking from directly rewriting memory facts.

---

# 34. Separate epistemic and instrumental learning

## Epistemic

What is true/predictive?

Main signals:

- JEPA error,
- source evidence,
- exact memory,
- prediction consistency.

## Instrumental

What action helps achieve goals?

Main signals:

- outcome,
- cost,
- reward,
- user preference,
- safety.

The two interact but should not share one loss.

---

# 35. Missing counterfactual evaluator

P1/P2 generates alternatives, but V13 still needs an explicit counterfactual evaluation path:

```text
candidate action/hypothesis
→ World-JEPA rollout
→ Fast Forward model
→ memory constraints
→ expected outcome distribution
```

Then Action Gate/Judge chooses.

This turns Inquisition into useful planning instead of internal debate only.

---

# 36. Uncertainty should be decomposed

At least:

```text
aleatoric-like: multiple plausible outcomes
epistemic-like: model does not know
source uncertainty: evidence unreliable
state uncertainty: hidden context unclear
action uncertainty: tool/body response unclear
```

Different uncertainty types should trigger different behaviour.

Examples:

- epistemic → retrieve/ask/learn
- multiple plausible futures → preserve modes
- source uncertainty → verify provenance
- action uncertainty → use cautious forward model / smaller action

---

# 37. Surprise should not equal learning rate directly

A huge prediction error may mean:

- valuable novelty,
- bad data,
- corrupted memory,
- distribution shift,
- model failure.

So:

```text
surprise
→ investigate
→ classify
→ then set plasticity
```

not:

```text
big surprise = big update
```

---

# 38. Memory admission needs a bottleneck

Not every interaction should enter long-term memory.

Admission should depend on:

- novelty,
- future utility,
- emotional/value significance,
- source quality,
- recurrence,
- unresolved conflict.

Exact raw logs may stay archived, but semantic long-term memory should be selective.

---

# 39. Memory deletion should be conservative

Deleting low-confidence text can destroy useful evidence.

Prefer:

```text
demote
archive
mark contradicted
supersede
```

before physical deletion.

Deletion should mainly target redundant/generated/cache material.

---

# 40. Forgetting can be useful

The system currently treats forgetting mostly as failure.

Some forgetting is necessary.

Allow:

- compression,
- decay of low-value associations,
- removal of stale fast adapters,
- reduced replay of obsolete skills.

But exact provenance archives should be preserved when cheap.

---

# 41. Structural plasticity

Existing expert clone/split ideas should expand into general structural adaptation.

Possible later operations:

- add predictor mode,
- prune unused adapter,
- split overloaded skill path,
- merge redundant paths,
- add workspace slot,
- retire obsolete translator.

All structural changes require shadow evaluation and rollback.

---

# 42. Stability envelope

Regression testing happens after an update.

Add a pre-update Stability Envelope.

Every subsystem keeps limits:

```text
max update norm
max route shift
max workspace drift
max calibration shift
max memory promotion rate
```

Updates beyond the envelope are deferred to offline consolidation.

---

# 43. Event clock, not fake biological oscillations

Do not force literal theta/alpha/etc.

Instead use functional clocks:

- perception tick,
- reasoning cycle,
- action cycle,
- replay phase,
- consolidation phase.

If oscillatory scheduling proves useful later, test it experimentally.

Avoid biological numerology.

---

# 44. What should be retired from old V13 material

## 44.1 “Cerebellum is basically only body coordination”

Retire.

Current neuroscience supports broader predictive/error-correction/cognitive roles.

## 44.2 “Body-less means body feedback can simply be replaced by human feedback”

Retire.

Human feedback is useful but incomplete.

A digital agent already has an environment:

- tools,
- files,
- operating system,
- network,
- time,
- compute,
- outcomes.

Environment feedback should be first-class.

## 44.3 Single residual vector as whole Global Workspace

Retire as strict requirement.

Keep shared latent workspace, but implement multi-slot/gated persistent state.

## 44.4 One scalar Judge reward controlling everything

Retire.

Use a vector of modulatory signals.

## 44.5 “Translator eventually disappears completely”

Refine.

A heavy teacher/encoder can retire.

A minimal modality transducer/projection may remain permanently.

## 44.6 “All weights learn on every inference”

Retire literal interpretation.

All relevant components remain lifetime-plastic, but local activation + eligibility + metaplasticity determine what actually changes.

## 44.7 “Inference = immediate gradient update”

Refine.

Better:

```text
inference creates state + eligibility + experience
learning may occur during, immediately after, idle, replay or sleep
```

## 44.8 “Top-k/sparsity makes model brain-like by itself”

Retire.

Sparse activation is only one computational analogy.

Local plasticity, modulation, replay, homeostasis, specialized loops and action-conditioned prediction matter much more.

---

# 45. Revised V13 brain scaffold

```text
SENSORS / TEXT / TOOLS / DIGITAL BODY
                 │
                 ▼
        SENSORY TRANSDUCERS
                 │
                 ▼
          THALAMIC RELAY
     selective admission/routing
                 │
        ┌────────┴────────┐
        ▼                 ▼
   GIST BODY          DETAIL BODY
   coarse/high-k      fine/low-k
        │                 │
        └──── CALLLOSUM ──┘
                 │
                 ▼
        MULTI-SLOT WORKSPACE
                 │
      ┌──────────┼───────────┐
      ▼          ▼           ▼
    MEMORY    WORLD-JEPA   SELF/BODY
      │          │           │
      └──────────┼───────────┘
                 ▼
           CAUTIOUSNESS
                 │
                 ▼
          Z_INQUISITION
            P1 ↔ P2
                 │
                 ▼
         CONSCIOUS CORE
              JUDGE
                 │
     ┌───────────┼────────────┐
     ▼           ▼            ▼
 ACTION GATE   HALTING      OUTPUT
     │
     ▼
FAST FORWARD / CEREBELLAR MODEL
     │
     ├─ expected result
     │
     ▼
ACTION / TOOL / BODY COMMAND
     │
     ├──────────► COROLLARY COPY
     │                    │
     ▼                    ▼
ENVIRONMENT          expected feedback
     │                    │
     └──────────┬─────────┘
                ▼
          actual vs expected
                │
                ▼
            EXPERIENCE
                │
    ┌───────────┼────────────┐
    ▼           ▼            ▼
episodic     procedural    semantic
 replay        replay       replay
    └───────────┼────────────┘
                ▼
       LOCAL JEPA PLASTICITY
 activation × eligibility × error × modulators
                │
                ▼
        METAPLASTICITY GATE
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
     hold     fast      tag
              update   for consolidation
                         │
                         ▼
                    SLEEP PHASES
                         │
                         ▼
                SLOW CONSOLIDATION
                         │
                         ▼
                   REAL WEIGHTS
```

---

# 46. Revised control hierarchy

## Reflex

Fast hard/local reactions.

## Thalamic Relay

Traffic and network configuration.

## Action Gate

Selects cognitive and external actions.

## Judge

Semantic conscious integration, goals, confidence, final output.

## Homeostatic Controller

Keeps network stable.

## Neuromodulator Bus

Controls learning conditions.

This hierarchy is more brain-like and removes excessive responsibility from Judge.

---

# 47. Revised learning hierarchy

```text
local activation
     ↓
eligibility trace
     ↓
local prediction error
     ↓
regional/global modulators
     ↓
metaplasticity gate
     ↓
fast local update or consolidation tag
     ↓
replay
     ↓
slow consolidation
```

This should become the canonical V13 learning doctrine.

---

# 48. Digital body first

Before a physical robot body, Android itself becomes Body-0.

Body-0 sensors:

- battery,
- thermal state,
- RAM,
- storage,
- clock,
- network,
- filesystem,
- installed tools,
- permissions,
- camera/mic later.

Body-0 effectors:

- text output,
- file operations,
- tool calls,
- shell/app actions,
- notifications,
- network/API actions.

This gives V13 real action–consequence loops immediately.

---

# 49. What to build before multimodality

The next brain-scaffold milestone should not be image/audio.

It should be:

1. Local eligibility traces.
2. Neuromodulator bus.
3. Metaplasticity.
4. Homeostatic controller.
5. Multi-slot workspace.
6. Thalamic relay.
7. Action gate.
8. Action-conditioned World-JEPA.
9. Fast Forward Controller.
10. Corollary discharge.
11. Event segmentation.
12. Multi-replay sleep phases.
13. Digital body schema.
14. Exact experience/outcome ledger.

Once those exist, image/audio/body ports fit much more naturally.

---

# 50. Priority matrix

## P0 — required for coherent brain scaffold

- local eligibility traces,
- metaplasticity,
- homeostasis,
- multi-slot workspace,
- thalamic relay,
- action gate,
- action-conditioned world model,
- corollary discharge,
- digital body schema,
- event-based experience.

## P1 — required before serious lifelong learning

- multiple replay types,
- consolidation tags,
- sleep phases,
- neuromodulator vector,
- procedural skill memory,
- source binding in workspace,
- uncertainty decomposition.

## P2 — later but architecturally supported now

- structural plasticity,
- expert growth/split,
- physical body,
- vision/audio/video,
- server consolidation,
- body replacement at scale.

---

# 51. Scientific positioning

The safe description is:

**brain-inspired continual-learning architecture**

or:

**functionally neuro-inspired AI scaffold**

It should not be described as:

- a simulation of the human brain,
- biologically faithful consciousness,
- proven neural equivalence.

The strongest biologically inspired parts are:

- sparse specialized processing,
- local activity-dependent plasticity,
- eligibility traces / third-factor modulation,
- predictive representation learning,
- recurrent workspace,
- direct subsystem communication,
- fast/slow learning,
- replay and consolidation,
- metaplasticity/homeostasis,
- action-conditioned prediction,
- corollary discharge,
- specialized control loops.

---

# 52. Sources

## Existing V13 material reviewed

- `AI-Consciousness-Blueprint-Theses-(Copy)-(Copy)-(Copy)-(Copy)-(Copy)-(Copy)-(Copy).json`
- `V13_MASTER_RESEARCH_BLUEPRINT_v7.1.md`
- `V13_RND_MASTERPLAN_v6.0.md`
- `V13_MASTER_MERGE_BAUPLAN_v4.0.md`
- `V13_RND_MASTER_PLAN_v5.0.md`
- historical B1–B6 code and audit traces embedded in the JSON

## Neuroscience / learning

1. Gerstner et al. Eligibility Traces and Plasticity on Behavioral Time Scales.
   https://pubmed.ncbi.nlm.nih.gov/30108488/

2. Whitford & Ford. A primer on corollary discharges: neural signals that distinguish Self from World. 2026.
   https://www.nature.com/articles/s44277-026-00063-2

3. Spampinato et al. Cerebellar rhythms: mechanisms, functions and translational opportunities. 2026.
   https://www.nature.com/articles/s41583-026-01072-y

4. Nguyen & Person. Cerebellar circuit computations for predictive motor control. 2025.
   https://www.nature.com/articles/s41583-025-00936-z

5. Koster & Mo. The role of transthalamic pathways in perception. 2026.
   https://www.nature.com/articles/s42003-026-10042-0

6. Zhang et al. Mediodorsal thalamus regulates task uncertainty to enable cognitive flexibility. 2025.
   https://www.nature.com/articles/s41467-025-58011-1

7. Redinbaugh & Saalmann. Contributions of Basal Ganglia Circuits to Perception, Attention, and Consciousness. 2024.
   https://pubmed.ncbi.nlm.nih.gov/38695762/

8. Galliano & Keck. Interactions between homeostatic plasticity and statistical learning. 2025.
   https://pubmed.ncbi.nlm.nih.gov/40543333/

9. Chang et al. Sleep microstructure organizes memory replay. 2025.
   https://www.nature.com/articles/s41586-024-08340-w

10. Robinson et al. Large sharp-wave ripples promote hippocampo-cortical memory reactivation and consolidation during sleep. 2026.
    https://pubmed.ncbi.nlm.nih.gov/41205608/

11. Thompson et al. Replay of procedural memory is independent of the hippocampus. 2026.
    https://pubmed.ncbi.nlm.nih.gov/42493550/

12. Prediction error and event segmentation in episodic memory.
    https://pubmed.ncbi.nlm.nih.gov/38184184/

13. Yamada & Chao. Joint encoding of what and when predictions through error-modulated plasticity in biologically plausible spiking networks. 2026.
    https://www.nature.com/articles/s42003-026-10836-2

14. de Cothi et al. Acetylcholine: a candidate substrate for hippocampal predictive learning? 2026.
    https://www.nature.com/articles/s41583-026-01058-w

15. Yaghoubi et al. Predictive coding of reward in the hippocampus. 2026.
    https://www.nature.com/articles/s41586-025-09958-0

## AI / multimodal interface

16. Google DeepMind. Gemma 4 12B: unified encoder-free multimodal model. 2026.
    https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/

17. Google Developers. Gemma 4 12B Developer Guide.
    https://developers.googleblog.com/gemma-4-12b-the-developer-guide/

Note: “encoder-free” still includes lightweight modality-specific numerical interfaces. Vision uses a lightweight embedding/projection module and audio is linearly projected to the language-model space. This supports the V13 distinction between a removable heavy teacher and a possibly permanent small transducer.

---

# 53. Final recommendation

The largest conceptual upgrade is not another model.

It is changing V13 from:

```text
two models + Judge + JEPA + memory
```

into:

```text
specialized hemispheres
+ dynamic relay
+ multi-slot workspace
+ conscious core
+ action selection
+ fast forward control
+ world prediction
+ self/world distinction
+ body schema
+ local eligibility-based plasticity
+ metaplasticity
+ homeostasis
+ multiple replay/consolidation loops
```

That is a substantially stronger and more coherent brain-inspired scaffold.

The body can then be learned as an organ plugged into this system instead of defining the system itself.
