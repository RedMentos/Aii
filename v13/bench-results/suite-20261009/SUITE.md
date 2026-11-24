# V13 Messsuite 2026-10-09T17:01:30Z

| § | Benchmark | Status | Braucht | Hinweis |
|---|---|---|---|---|
| 24.1 | Second-Attempt Advantage | MEASURED | models | paraphrase transfer measured; restart/negative-transfer families via integration_second_attempt (models) |
| 24.2 | Immediate Memory | TESTED | none |  |
| 24.3 | Automaticity | TESTED | none | skill fast path and effort; quality-at-fewer-steps not measured |
| 24.4 | Re-open / De-automatization | TESTED | none | skill reopen + age demotion; live salience reopen not measured |
| 24.5 | Retention | TESTED | none |  |
| 24.6 | Output Guarantee | TESTED | none |  |
| 24.7 | Provenance | TESTED | none |  |
| 24.8 | Local Plasticity | TESTED | none |  |
| 24.9 | Body Swap | TESTED | none | slot lifecycle; parity on real bodies not measured |
| 24.10 | Action Safety | TESTED | none | tool gate + C5 suppression; real external actions blocked until WP-K |
| 24.11 | Callosum Utility ohne Homogenisierung | MEASURED_FAILING | models |  |
| 24.12 | Response Governor | TESTED | none |  |
| 24.13 | Controlled Exploration | TESTED | none | curiosity budget only; route discovery under shadow not measured |
| 24.14 | Control-Fabric Overhead | NEEDS_REDMI | redmi |  |
| 24.15 | Channel Utility / Latent-vs-Fallback | MEASURED | models | latent channel not implemented (B3 OFF) |
| 24.16 | World Grounding / Counterfactual Reliability | TESTED | none |  |
| 24.17 | Deliberation Trajectory / Halting | TESTED | none |  |
| 24.18 | Fast Episodic Parametric Trace | NOT_IMPLEMENTED | none | MEM.parametric_fast_trace = 0 at Age 0 (blueprint optional) |
| 24.19 | Shared Pre-Router Forgetting | NOT_IMPLEMENTED | models | needs MoE body (WP-N11) |
| 24.20 | Multiscale Gist/Detail Resolution | MEASURED | models |  |
| 24.21 | Developmental Age Control | TESTED | none |  |
| 24.22 | C-native / Selective Body-Wake | TESTED | none |  |
| 24.23 | Adaptive Reasoning Effort | TESTED | models | quality vs fixed low/high baselines needs model run |
| 24.24 | Native Cache/Attention Capability Ablation | MEASURED | models |  |
| 24.25 | Observer-Pass Utility | TESTED | models |  |
| 24.26 | JEF-KV/Broadcast Bridge | NOT_IMPLEMENTED | models | WP-N3 |
| 24.27 | Focal Coalition / Unity Test | TESTED | none |  |
| 24.28 | Corollary-Copy / Self-vs-World | TESTED | none |  |
| 24.28B | Teacher Reference / Human Feedback Integrity | TESTED | none |  |
| 24.29 | Modality Scaffold Internalisation | TESTED | models | text A3 student only; no camera/audio (STEP8) |
| 24.30 | Live / Full-duplex Interaction | NOT_IMPLEMENTED | none | not built |
| 24.31 | Cross-modal Learning | NOT_IMPLEMENTED | none | text only until STEP8 |
| 24.32 | Fluid Experience Lifecycle | TESTED | none |  |
| 24.33 | Redmi Scheduling / Memory Residency | NEEDS_REDMI | redmi |  |
| 24.34 | Needle-class Additive Control Experiment | TESTED | models |  |

## §99 Ablationen

| Hypothese | Kontrollen vorhanden | fehlend |
|---|---|---|
| Fine/Gist split helps | identical policies, shared-body dual state, single body | – |
| Callosum helps | no-message, exact, symbolic | latent |
| Focal coalition helps | – | full context only, retrieval only, fixed slots |
| Episodic fast memory helps | no memory | response cache, param delta only |
| JEPA predictor helps | – | supervised readout, next-token-like probe, no predictor |
| Eligibility helps | – | gradient only, random mask, recency only |
| Typed modulators help | – | scalar reward, human-only, outcome-only |
| Dream helps | no dream, replay only, dream no writes | dream policy-only |
| Proceduralization helps | – | full deliberation, static shortcut |
| Age helps stability | – | fixed conservative, fixed permissive |
| Two bodies worth mobile cost | shared body + two states, one body | – |

Gates: {'GREEN': 8, 'PARTIAL': 11}
Register: 299 Blueprint-Regler, 60 im Code gleich, 0 abweichend, 239 nur deklariert (Abdeckung 20%).
