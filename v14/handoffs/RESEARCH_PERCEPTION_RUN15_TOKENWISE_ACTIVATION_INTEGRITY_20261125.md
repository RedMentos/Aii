# Research & Perception — Run 15 handoff

Date: 2026-11-25
Owner: Research & Perception
Whole-system epic: [#1984](https://github.com/RedMentos/Aii/issues/1984)
Blocking native chat gate: [#1904](https://github.com/RedMentos/Aii/issues/1904)

## Work completed

Updated the existing Research/Perception child PR [#2501](https://github.com/RedMentos/Aii/pull/2501); no new stacked PR was opened.

- Branch: research-perception/v14-token-span-alignment-20261125-run14b
- Exact code/test SHA: 6cc34b122caecfa340d36b08c9cc1e1bdbbbb2e2
- Parent branch: research-perception/latent-event-scope-20261125-run12 (PR #2496)
- Release-development ancestor: 8d93236c753f0194224c19edc7411d8d7082b1d6

The previous tokenwise pair ID and aggregate alignment digest bound source/span metadata but not the numeric activation rows. The adapter now:

1. Hashes each sender and receiver activation row using canonical little-endian float64 bytes.
2. Binds the pair ID to source ID/hash, token position/span, alignment ID/coverage and both activation digests.
3. Includes both row digests in the aggregate token-alignment digest.
4. Rejects activation mutation after alignment and a stale pair ID even when one row digest is recomputed.

Event-pooled schema-v2 is unchanged. This is a self-consistency check, not a signature or trusted provenance proof.

## Tests

- Exact adapter CI [45630124154](https://github.com/RedMentos/Aii/actions/runs/45630124154): 37/37 PASS on Python 3.13 and 3.14; exact py_compile PASS; public privacy scan CLEAN.
- Runtime-deployment integrity [45630124121](https://github.com/RedMentos/Aii/actions/runs/45630124121): offline Python 3.11 and 3.14 PASS.
- LOCAL_LINUX isolated helper reproduction: 3/3 PASS (different-tokenizer alignment positive; changed activation rejected; stale pair ID rejected).
- Full local Aii checkout/pytest: BLOCKED / NOT_RUN. No checkout is mounted; git ls-remote failed because github.com DNS cannot resolve.
- An earlier code/test head 4477cb7 had four failing fixtures; they were corrected. The exact tested code/test head is 6cc34b1.

## Product and Canon boundary

- No normal Runtime production behavior changed.
- No real tokenwise persisted tap cohort or trusted tokenwise tap writer exists yet.
- No native GGUF pair, native receiver task-utility, gradient/parameter update, retention, restart/rollback, Redmi/Termux test or deployment was performed.
- production_route=false, semantic_use_proven=false, training/native authority remain zero; B3 remains OFF.
- Redmi: REDMI_UNVERIFIED. No current phone receipt, model process, user data, permissions, model or weights were touched.
- PR #2501 remains OPEN / DRAFT / NOT_RELEASED.

## Research

R-007 records the full-paper review of Cardenas Piepereit, Architecture-Dependent Causal Transfer of Activation States Across Large Language Models, arXiv:2608.16347v2: representational alignment and retrieval can be above chance while causal injection utility fails for two of three tested decoder-only pairs. R-144 records the full-PDF review of dense KV-cache latent communication; it is a different interface from one pooled prefix. Both support separate geometric alignment, receiver-effect and task-utility gates. No third-party code, weights or data were imported in this run.

## Next executable work

1. Core to finish and independently review [#2499](https://github.com/RedMentos/Aii/pull/2499), which adds a separate LATENT_PREFIX_V1 receiver for one event-pooled vector. Keep it distinct from tokenwise schema-v3.
2. Research + Core to add a trusted tokenwise tap producer with exact packet IDs, feature blob hashes, event/generation, model/tap/tokenizer revisions, source hash and character offsets. Current tokenwise API still accepts caller-supplied spans and vectors; content hashes alone do not authenticate them.
3. After a real source-disjoint cohort exists, compare event-prefix, aligned tokenwise rows, exact-text and no-message/zero/shuffle/repeat/OOD controls on held-out receiver tasks. Do not promote on cosine/MSE alone.
4. Native probe only through the existing local-TTY one-shot approval path and a separate explicit user decision; no remote shell or phone action.

User action: NONE. Do not change installed models/weights or send a manual Termux command.

 
## Latest available private device boundary

Read-only private V13OBS #115 snapshot (last device check 2026-11-24T09:22:33Z): auto-update enabled and dashboard/runtime UP_TO_DATE at 8d93236c753f0194224c19edc7411d8d7082b1d6; AI runtime STOPPED_BY_USER, autostart false, model process stopped. Recorded five-turn metadata has two failed native attempts and zero valid offers for each of B1/B2; native latent exchange and C3 semantic use are not proven. No newer receipt was available in this run. This does not validate PR #2501. No UPDATE_REQUEST, CHAT_SEND, restart, shell, LOG_PAGE, model/weight/permission change or data mutation was performed. Redmi remains REDMI_UNVERIFIED / NOT_RELEASED.

 
## Additional research note — R-146 S-JEPA

Full main-paper review: Giakoumoglou et al., *A Stochastic Latent Variable Generalization of Joint-Embedding Predictive Architectures*, arXiv:2611.09302v1 (2026-11-06). The method uses a target-conditioned posterior during training and a context-conditioned prior at inference for one stochastic latent per image. Its reported experiments use ViT-B/L, 600 ImageNet epochs and four A100 GPUs; it is not an Android candidate. Uncertainty-error correlation is weak within images (mean Spearman about 0.16, positive in 76%), and uncertainty maps require repeated predictor passes. The paper's code URL was not retrievable and software/weight licenses remain unverified; no code or weights were reused. V14 may later test a tiny uncertainty-gated stochastic residual z for ambiguous temporal outcomes, only after source-bound taps exist, with deterministic/zero/shuffle controls and measured calibration/RSS/TTFT.
