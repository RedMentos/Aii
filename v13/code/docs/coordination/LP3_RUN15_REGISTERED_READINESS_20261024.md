# V13 LP3 Run15 — independent registered-source readiness review (2026-10-24)

## Base and file ownership

Read remote refs, open PRs, AGENTS, current HANDOFF/BUILD_STATE/ROADMAP, user decisions and complete-canon headings before editing. Base is verified PR #50 head `0b4652359094b3497306f36fbe663f30858e338b`, stacked through Codex PR #42 on Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`. No newer Claude integration PR was visible at inspection. The current production runtime, original preregistered LP3 runner, canon and original STEP2/B3 gates are unchanged. Package owner: `scripts/lp3_native_readiness.py`; independent adversarial reviewer owns new `tests/test_lp3_readiness_review_run15.py`; coordinator owns only new scoped docs/proofs. No subagent execution claimed; packages were sequential and independently tested.

## Confirmed fail-open readiness bug

The Run14 read-only host preflight read `PINNED_MASTER_SHA256`, `HF_ASSETS`, and `PINNED_HF_REVISION` from the **candidate it was supposed to verify**. With a synthetic candidate setting `HF_ASSETS=()` and arbitrary 64-hex weight digest, plus two arbitrary nonempty fixture files, it reported `LOCAL_ASSETS_READY_OWNER_UNVERIFIED` even with **zero model files**. Similarly, an edited fixture and an alternate revision could be accepted. Raw pre-fix reproduction: `adversarial_red.log` (three false readiness claims, two missing-guard errors; all five tests intentionally red).

## Fix and bounded proof

Readiness now compares candidate constants against independently pinned seven HF asset names, exact revision and weight SHA-256, and checks the candidate + two transitive fixture files against the **actual PR50 Git blob identities** before reporting local readiness. It never trusts the candidate's asset list to decide what to scan. It follows regular-file HF cache symlinks (required), hashes their contents, and fails closed for unreadable sources/assets. Git blob identities are exact content identity within the reviewed Git tree; they do not independently authenticate upstream nonweight HF assets or prove a native model was executed. A legitimate future candidate or fixture change needs a new source-bound preregistration and explicit readiness update, not silent acceptance.

Registered source Git blobs from PR50 tree:
- `scripts/lp3_memory_key_candidate.py`: `4006a461b82df58dbdf4fe98886207686ca30c42`
- `scripts/lp2_assignment_objective.py`: `7cc55996bd9016a05614d6f11b91fd33d1605f2e`
- `scripts/lora_bench.py`: `8a7b725bb450a21775cc1c0ab98dedba5d123278`

## Verification and evidence levels

- Previous focused baseline: 84/84 software/synthetic PASS.
- Pre-fix adversarial reproduction: five red tests, including three actual false-READY claims (preserved).
- Post-fix: 89/89 focused software/synthetic PASS; `compileall` PASS. Synthetic positive control uses test-local monkeypatches; never a native model run.
- Current local host: cgroup memory max 4,294,967,296 bytes, `transformers` missing, pinned HF assets absent, LP2/LoRA fixture scripts absent from partial source bundle, no local LP3 process detected at check time. `BLOCKED`. Global owner/other hosts unverified. `native_executed=false`, `phone_measured=false`.
- Complete repository checkout/full suite: NOT RUN (container git DNS fails). The exact official privacy scanner was independently retrieved by Git blob SHA and applied to a **scoped synthetic local diff** only; this is NOT a complete repository branch privacy scan.
- Original gates: STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full architecture INCOMPLETE.

## Primary research and provenance (accessed 2026-10-24)

- Python AST docs: https://docs.python.org/3.13/library/ast.html — `ast.Assign`/`ast.literal_eval` can extract a literal but do **not** establish its source authority; independent exact source binding is needed. No external code incorporated.
- Hugging Face official cache docs: https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache — snapshots commonly symlink to blobs; keep supported regular-file symlinks and hash the bytes.
- Official model revision: https://huggingface.co/LiquidAI/LFM2.5-350M/tree/55e5a53e8637c4522a0577040fe68682db3fbbb6 — weight SHA-256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, custom `lfm1.0` license. Model NOT downloaded or incorporated. Upstream nonweight authenticity remains unverified.
- Git object identity documentation: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects — Git blob object ID hashes `blob <size>\0<content>`; the exact SHA-1 values are pinned to the verified PR50 tree. Standard Python library only, no added dependencies.

## Exact next step

Independently review this source-binding fix in a complete current checkout, run full suite and official `public_repo_privacy_scan.py` against the real remote base/head, then verify pinned HF assets + actual fixture Git blobs + current global native job ownership. Only then run the **unchanged** preregistered four-seed LP3 cohort serially, close and independently anchor raw evidence, and design a separate equal-budget generated-answer ablation. Do not use the previously rejected anyone-writable Drive backup destination.
