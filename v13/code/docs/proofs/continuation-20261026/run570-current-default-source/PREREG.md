# Run570 prospective prereg — NEW disjoint current-default vs legacy-config STEP2 source cohort

2026-10-26. Source-only development package, independent of original Run568 FUTURE_005 native owner and original Run569 immutable audit prereg. Base Run569 prereg commit `4e895b16d12fef706d45ac530ce29960b1a4d6f1`. This is **not** a replacement or rescore of original frozen Run491/500/504/558, which remains unchanged; no native/model work is authorized by this prereg.

Problem: the 126 original FUTURE_001–003 rows diagnosed by Run565 yielded 126/126 UNKNOWN, but the original frozen arms are legacy settings, not current user-authorized default quote pointer, B1 recent-source, body questions, fixed reader and answer-first. A separate **disjoint** end-to-end native cohort must compare the *actual current* defaults with the documented legacy quote path before claiming that the current live path improves STEP2.

Register six new source episodes using unchanged `step2_z2_timescale.episode` constructor, with exact specs:
- Helios SPLIT rules (132,6,true), A (95,4,true), B (87,7,false).
- Iris SPLIT rules (86,5,false), A (73,6,false), B (77,4,true).
- Jade SPLIT rules (118,4,true), A (98,4,true), B (102,3,false).
- Kepler RULE rules (105,5,true), A (88,4,true), B (79,6,true).
- Lyra RULE rules (92,3,false), A (81,4,false), B (83,2,true).
- Mistral DETAIL rules (124,5,true), A (109,6,true), B (117,4,true).

All six names must be disjoint from original Z2 and Run491, history length exactly three, old rule and recent detail separation validated, no oracle included in native consumer messages. Two paired arms on identical source/seed `41`: `CURRENT` copies current `v13.config.DEFAULTS` relevant STEP2 fields; `LEGACY` copies `v13.config.LEGACY_QUOTE_PATH` relevant fields and explicitly uses `tool_answer_first=False`. Both retain `answer_language=en`, `b2_control=two_body`, `learning_mode=RECORD_ONLY`, `system_stage=0`, `latents_enabled=False`, `teacher_enabled=False`. Seven original frozen variant labels per fixture per arm: 6 × 2 × 7 = **84 planned native consumer rows**, zero actual at source prereg. Current vs legacy is a new comparison, **not** original Run491 arm A/B/C/D/E and not historical-exact replay.

First package implements deterministic JSON source-only plan, SHA256 of six full fixture bytes and explicit config snapshot, source/role/seed/variant row key closure, refuse overwrite, CLI `--plan` only (no `--execute`), adversarial tests for duplicates, overlap, altered history/source, invalid configs, and no gate promotion. Separate future prereg is required before any native execution; verify pinned public models/runner and original frozen-source hashes, serialized owner and raw/safe evidence. Future analysis should report paired per-episode utility, exact decision, wrong committed, UNKNOWN, quote coverage, same-policy and single-body controls; any confidence interval must cluster by episode, not pretend seven variants are independent. No user-private data or paid provisioning.

Gate state unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, Redmi UNMEASURED, V13 INCOMPLETE. No default behavior change, no learning/age/approval rights.
