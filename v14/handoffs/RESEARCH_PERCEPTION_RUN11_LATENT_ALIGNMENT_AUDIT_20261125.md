# Research & Perception handoff — latent alignment audit
Date: 2026-11-25; research source v2 revised 2026-11-09
Owner lane: Research & Perception
Base: gpt6/v13-private-remote-bridge-20261111 @ 8d93236c753f0194224c19edc7411d8d7082b1d6
Branch: research-perception/latent-alignment-audit-20261125-run11
PR: #2489 (OPEN / DRAFT / NOT_RELEASED)
Implementation SHA: 8ebc18b322745dfb96b524e25933408597ae92eb

## Product gap addressed
The current native probe can persist source-bound LatentTapPacket records, but no accepted method exists to screen whether B1 and B2 final-output tap spaces preserve the same source neighbourhoods. The research paper R-007 demonstrates why raw cosine/CKA or successful retrieval must not be treated as causal communication evidence. It also identifies position-0 domination in its tested causal decoders.

## Change
- Added v13/code/v13/latent_alignment_audit.py.
- Added v13/code/tests/test_latent_alignment_audit.py.
- Updated R-007 in v14/V14_RESEARCH_LEDGER.md from abstract-only to full-text review and linked the executable audit.

The audit reads the existing packets table and data/blobs in read-only mode. It accepts only B1_DETAIL/B2_GIST taps with matching source_ref, event_id and generation_id; verifies packet authority flags and final-RMSNorm tap metadata, token IDs, shapes, hashes and blob containment; and caps memory/work for mobile use. It excludes position 0 from the pooled alignment vectors, reports its norm ratio and all-vs-excluded cosine, then calculates cross-space kNN-neighbourhood overlap with a permutation null. It does not reproduce the paper's exact MNN implementation; the paper's Zenodo archive must be inspected before claiming an exact replication.

## Exact local tests
Environment: LOCAL_LINUX container, CPython 3.13.5.

- python -m py_compile v13/code/v13/latent_alignment_audit.py — PASS.
- PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_latent_alignment_audit.py — PASS, 9/9.
- PYTHONPATH=v13/code python -m v13.latent_alignment_audit --help — PASS.
- Synthetic Store/blob fixture uses the real V13 packets table column layout; DB file hash unchanged across audit.
- Negative checks: mismatched event, missing counterpart, tampered blob, authority escalation, path traversal, symlinked blob root — PASS.

The full Aii checkout and full repository test suite were not run locally: GitHub DNS/network access from the container is unavailable. The Zenodo archive was also inaccessible from this environment. CI is separate and pending.

## Research update and licensing
The v2 full text says the archive includes concept-pair sets, extraction/projection scripts, the injection mechanism, raw results for all 180 generation trials, logs, pre-registration, and a recomputation script. It explicitly describes the activation-level channel as a monitoring/interpretability risk because it removes human-readable text and can evade ordinary filters/logs. V14 must keep future latent exchange opt-in, source/age/consent-bound and control-plane-auditable. The paper's explicitly open research item is a formal information-theoretic channel characterization (capacity, coding scheme, error rate) compared against token-path cost. The Zenodo archive should be inspected before adapting its code.

## Runtime and claim boundary
This tool consumes the same persisted LatentTapPacket/blob contract produced by Cognition.tap and the opt-in native-probe path being developed in PR #2488. It is a read-only research diagnostic, not a production Runtime route. No real tap cohort was available in this run. No native model was loaded; no weights, model files, permissions, or runtime state were changed.

Current tap vectors are final RMSNorm output embeddings, not middle-layer residual-stream activations. The current native receiver accepts input embeddings through llama_batch.embd; it does not implement the paper's middle-layer injection loop. B1/B2 dimensions differ (2048/1024), and there is no trained projector. Therefore:
- latent alignment: NOT_MEASURED
- learned cross-organ adapter: NOT_IMPLEMENTED
- causal generation transfer: NOT_PROVEN
- B3 production route: OFF / UNVERIFIED
- Redmi: REDMI_UNVERIFIED

## Coordination
- Related Core work: PR #2488, native receiver/probe matrix. This audit only consumes its persisted tap contract; it does not modify Core-owned files.
- Existing Perception PRs #2486 and #2487 remain separate A3/audio changes; this branch is based on the verified release development SHA, not on their stacked branches.
- Whole-canon blocker remains issue #1984; real Redmi chat failure remains issue #1904. This audit does not address or close either.
- Work Board and Live Workplan remain Boss/Integrator-owned; Boss should add the audit as an evidence tool under the B3/latent acceptance path after review.

## Next executable step
Once Core's opt-in tap writer is integrated and an explicitly authorized local runtime is running, gather >=20 distinct paired B1/B2 source groups from matching event/generation receipts, run the audit, and retain only aggregate metrics. If alignment exceeds the permutation null, proceed to a separate pair-specific projector experiment with source-disjoint train/held-out sets and a receiver-side causal task test. Do not train or inject from this audit tool.
