# V13 ADDITIVE CONTEXT COMPANION — Memorilla/Context-Aware Learning (Draft, 2026-11-15)

## User requirement: EXTEND, NEVER REPLACE

Keep ALL previously planned V13 organs and Context OS behavior. The permanent fixed header and operator rules remain byte-identical, raw history and original source-backed events remain available, and the existing Context OS, memory, sleep/dream replay, B1/B2, JEF, C3, world/self models, JEPA, neuromodulation, Age and approval gates remain authoritative in their own roles. No replacement with a generic single summarizer, no single central model directing all others.

**Add** one small optional model (working name: Context Companion) *above/alongside* the current context:
- extra *query-specific* context: surface indirect cross-session relationships and forgotten cues missing from ordinary B1/B2/C3 views;
- overflow *continuity* context: synthesize older content that does not fit an individual model's window, without deleting, rewriting or hiding the original raw context.

## Three layers, cumulative

1. LOCKED: system rules/fixed header + exact recent/pinned source text (unchanged).
2. EXISTING: Context OS RAW_HISTORY / COMPRESSED / SOURCE_LINKS / ACTIVE_VIEW / HYPOTHESES / LATENT_STATE / MEMORY_POINTERS / ARCHIVE + B4 workspace + indexed and warm memories.
3. NEW OPTIONAL: source-linked OVERFLOW_CONTEXT, created by a small *supporting* LLM or learned memory slots from material not fully visible to the receiving body.

The third layer is a *hint*, NOT a source of fact or a new operator. Every claim carries source IDs and uncertainty. Exact details (numbers, code, names, quotes), conflicts and source critique trigger normal exact restoration instead of trusting a digest. The raw original is never destroyed. Deleted or out-of-scope sources cannot reappear through cached summaries. Support distinct personal/world/self memory namespaces and role-specific context for B1, B2 and C3. Keep both rolling task continuity and query-dependent cross-links, not just a single summary.

## Pipeline

CURRENT QUESTION + FIXED HEADER -> original Context OS -> B1/B2/JEF/C3 unchanged.
Context OS SOURCE_LINKS + archived exact sources + current goal -> Context Companion small model -> (query-sensitive synopsis, reasoning links, uncertainty, cited original event IDs) -> optional ADDITIONAL_CONTEXT volatile layer.
Source proof/restore remains separate; companion cannot edit the fixed prefix, direct tools, overwrite facts, change body weights or gain Age authority.

Use an existing EmbeddingGemma/retrieval index for initial cheap source selection. A small text-producing LLM can compose cited notes. A MEMORILLA-style learned latent-token encoder is a different later experiment; its learned continuous embeddings cannot simply be fed into a GGUF model without compatible embedding geometry and runtime support. MEMORILLA uses a frozen receiving LLM; full coupled training is not in the demonstrated method.

## Learning *together*, not independently (research extension)

Jointly improve memory writer/selector M_theta and role-specific reader adapters R_phi(B1,B2,C3, optional A3/JEF) from common *verified* experiences: delayed task success, false recall, exact-source checks, JEPA predictive residuals, human corrections, and compute cost. Attribute credit *locally* via existing eligibility × prediction-error × modulator gates, with role-specific objectives, not an indiscriminate gradient across every model. Stabilize with EMA, source-grounding, frozen targets/anchors and replay before any slow approved weight updates. During Age 0: observe, record/shadow candidate, measure; active context/weights only via existing explicit permission/approval logic. Don't silently edit base GGUF.

Suggested loss: L = task_success + memory_grounding + JEPA_prediction + retention/stability + latency_budget. Never use the same unverified model claim as both memory evidence and its own evaluation label.

## Implementation order

A. Add SHADOW-only source-linked overflow candidate API (no runtime mutation); check exact header, original raw history, deletion/session isolation, source IDs, failure/timeout.
B. Introduce optional small-LLM worker through existing RunnerPool/ModelManager, only when overflow/uncertainty/idle warrants it; avoid permanently loading multiple models on Redmi 6GB.
C. Integrate under *separate volatile layer* AFTER native planning (no duplicate ContextOS.plan state transitions; replan API if needed), default off, explicit acceptance only.
D. Long-term summaries, per-role reader heads and optional latent-slot research; register new objective as PARTIAL until real training and evaluation exist.
E. On-device A/B ablation: native only vs deterministic overflow digest vs small LLM vs learned latent hybrid vs jointly-trained writer/reader. Measure exact recall, contradictions, cross-session inference, latency, peak RSS, energy, OOD and retention. Roll back the companion alone on regression.

Sources: https://memory.stanford.edu/ | https://arxiv.org/abs/2610.21375 | https://github.com/snap-stanford/memorilla

**Status:** design contract only; neither full MEMORILLA nor integrated joint learning exists in V13 as a result of this document.
