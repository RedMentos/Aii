# Run11 four-way cross-organ review integration — preregistration (2026-10-28)

Owner: GPT-6 independent integration. **Review-only**, no production/main merge, no Age promotion. This preregistration precedes importing any source/test/workflow blobs.

## Frozen baseline and exact candidate heads
- Parent integration PR #826: `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b` (tree `c83db6022eb55d6325ec362ce114f2b3d3359b36`).
- #827 STEP2 cross-arm B1 identity: `50c24ee6450feb25cb4660f485c4f13db537de50`.
- #828 World-JEPA fixed-readout heldout action negative ablation: `6ea120820b5d09e652238900976ded8bcdf26b84`.
- #829 JEF control-fabric monotonic latency: `6a5cf1d86a063c1ed0182d8b5fdcadc45157e1a5`.
- #830 World-JEPA inference-only private checkpoint: `f19017095bb8a6a413788061549113f657a96cad`.

## Import / review protocol
Import **exact blob SHAs** for the five changed files from each of #827–#830 (20 distinct paths), without editing owner branches. Check path collision and compare each imported blob to its source; preserve all preregs, negative evidence, RED/GREEN handoffs, existing model/source/seed cohorts and licenses. Multi-parent integration commit records lineage, but neither claims CI nor merges to main.

Run a combined isolated Linux software workflow on the new branch: focused suites for the four packages, existing World-JEPA, STEP2 four-arm scorer/collector, control budget; full `unittest discover` (serial), `compileall`, privacy scan from #826 and `git diff --check`. Preserve raw exit codes/logs and hashes as a GitHub Actions artifact. Inspect every nonzero exit; a green workflow alone does not prove native models or Redmi.

## Original negative gates and limitations
STEP2 = UTILITY_FAIL; B3 = L1_FAIL; Body-JEPA = UNAVAILABLE; LP3 heldout = FAIL; jepa_weight = 0; Age0 = RECORD_ONLY; no live World-JEPA authority; no optimizer resume; no native/Redmi evidence or whole-system completion. Private fitted checkpoint bytes must **not** enter public Git.

Next after green: independent cross-organ review/counterexample and evidence archive, then a separate reviewed integration candidate; actual native four-arm measurements require a fresh exact prereg, compatible pinned artifacts, exclusive measured owner and hardware budget. A blocked native/Redmi path does not block other blueprint work.
