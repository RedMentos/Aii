# P0X / independent source-dependent 150-row structural holdout — preregistration (2026-10-29)

Owner: GPT-6 isolated review child of HB1b PR #1057 exact `d089f08fbf4ee7c3d3d1c9b6789320974f99731b`. This is a **new, disjoint prospective public synthetic evaluation cohort**, not a blind natural-language benchmark or replacement for the existing HB0/HB1a/HB1b registrations. Commit this registration BEFORE implementation, model calls or training. No production activation or gate promotion.

## Question and preregistered headroom

Does source-separated B1_DETAIL and B2_GIST provide C3_LANGUAGE a measurable advantage on **150 held-out tasks** whose correct answer requires both a per-project rule and a per-project option sheet, across five semantic domains? Before native inference, the deterministic reference oracle must solve all 150 with both exact sources and refuse decisions with current-only, B1-only, B2-only and foreign-project B1; this is a **software headroom check**, not a measured model benefit. Before claiming any useful model experiment, measure real C3-only baseline and require oracle headroom >=15/150. If the actual C3-only baseline makes the task trivial, record `P0X_NO_HEADROOM` and do not claim P0 acceptance.

## Fixed generation algorithm and partitions

- New fixed seed `2026102907`, 5 domains × 6 independently named project families = 30 families. Exactly one calibration family per domain (5×6=30 rows) and five held-out families per domain (25×6=**150 heldout**), total 180. Holdout is never used to tune prompt/format/training. IDs use `P0X` + first 16 uppercase hex characters of SHA256(`seed|family|sheet|rule`), never encode answer or indices in clear text.
- Each family has two option-sheet variants × three rule variants. Abstract option attributes (cost, time, flag) and rules (max_cost, max_time, require_flag) use the **new matrix**:
  - sheet 0: A=(15,8,true), B=(85,4,false)
  - sheet 1: A=(65,5,true), B=(40,4,true)
  - rule 0: (30,10,true)
  - rule 1: (80,10,false)
  - rule 2: (55,6,true)
  - Abstract action matrix sheet0=`A,A,NONE`, sheet1=`NONE,B,B`; two A/two B/two NONE per family, and each rule column changes outcome when sheet changes. Deterministic family-wise numeric shifts applied to both limits and attributes; deterministic sheet/rule order permutation and A/B label swaps per family preserve the balance and vary the surface.
- Five domain renderers, one per group of six families: procurement (euros/days/local), compute deployment (RAM MB/startup ms/on-device), shipping (kg/hours/refrigerated), laboratory (watts/minutes/certified), archive (GB/seconds/offline). Each renders current request, archived rule note (B2 only) and latest option sheet (B1 only) with domain-specific terms. The rule always means first/second numeric ceilings plus an optional mandatory boolean flag. Oracle selects the lowest first-attribute eligible option (tie: lower second, then A), else NONE.
- A foreign B1 sheet is from another domain/project at the same sheet/rule indices, with its ORIGINAL project header. No relabeling. Current request contains only project identity and generic action request, never numbers, thresholds, flags or oracle.
- Separate immutable `inputs.jsonl` and `answers.jsonl` after source generation. Exact externally registered fixture SHA256 and Git blob will be checkpointed **before any model-native execution**, never auto-updated after RED. No answer keys, family/sheet/rule indices, generated oracle, or serialized fixture dict in model-facing payloads.

## Fixed future native controls (not authorized as evidence until prerequisites pass)

For 150 held-out rows, preregister C3-only, both-exact, B1-only, B2-only, both-native, single-body-native, foreign-B1-shuffled controls. The actual native call budget, fixed output schema, seed and model/runner source pins must be separately preregistered and resource-admitted **before** execution. Keep pinned existing catalog B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M, original licenses/revisions/hashes unchanged. No extra model or unreviewed download. Age0 RECORD_ONLY, no adapters/training, latents OFF, jepa_weight=0, serial native owner. Separate body-generated offers from exact-source oracle and preserve all raw including failures.

## Software acceptance before native

- Exactly 180 unique IDs, 30 calibration + 150 holdout, 6 per family, 50 A/50 B/50 NONE on holdout and 10 each on calibration. No overlap with HB0/HB1a IDs.
- Each of 30 family grids has two of each action; each rule column changes action across sheets; for each heldout row current-only/B1-only/B2-only/foreign control has no source authority, both exact sources yield the deterministic oracle. No output-side answer leakage.
- Seed reproducibility, source/hash integrity, tamper/duplicate/foreign-project tests, strict separation of inputs and answer keys. All software tests and independent review must pass. Do not infer model capability from the deterministic reference parser.

## Claims and gates

This cohort is a prospective public synthetic **structural holdout**, not blind independent real-world data; it cannot alone prove JEPA learning, B3 latent benefit, Redmi behavior or whole-system completion. Even a positive model result would require confidence intervals, multiple seeds, a truly independent model-native holdout and a source-verified receiver to consider STEP2 promotion. All original negative gates remain Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE; Redmi unmeasured. No production merge. No private user data in public artifacts.
