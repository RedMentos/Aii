# Run105 unfiltered current Run104 integration full-suite — prereg 2026-10-31

Owner GPT-6 automation11; review-only child of Run104 PR #1475 exact parent `35113fc42f0b4594ca46ef33194877b8e277054f`. This is a new **software acceptance run**, not a native model run, and does not touch active Run103 native owner or original Run94 test artifacts.

## Motivation and fixed execution

Run94 #1459 full-suite original-ZIP proof was GREEN at older exact HEAD `8d3d4d28313394de7ec023fcd29497d56bfd3b81` (4907 tests, 28 skipped, 461.260s). Since then the review chain added C3 Context OS, phone packaging, STEP2_EXIT graph, and Run104 JEF/C5/C6 optional smoke. Run94 result cannot be relabeled current-source PASS. Independent container full-suite attempt at 180s was incomplete; no verdict.

Copy Run94 `.github/workflows/v13-run94-fullsuite-original-raw.yml` **execution method** with only scoped names/branch/base/trigger updates. Use Ubuntu 24.04 isolated pinned numpy 2.2.6, prompt-toolkit 3.0.52, CPU torch 2.5.1+cpu, transformers 4.44.2, peft 0.13.2, psutil, PyYAML, Pillow. Fetch original STEP2 native ZIP artifact `12951963045` pinned SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46` and original Run13T ZIP artifact `12996917793` SHA256 `86f728599312518bfa67efa0ae16e66be0eaec9ccfd8c3da8710fba40192717c`; verify ZIP CRC, 53/39 inner hashes, no substitutions. Run **unfiltered** `python -m unittest discover -s tests -p 'test_*.py'` on exact current branch, 25-minute bounded timeout and 40-minute Actions job limit. No test exclusions or gate changes. Preserve full stdout/stderr, errors, skips, exact HEAD, original ZIPs, SHA256SUMS, pip freeze, compile, privacy scan and diff in Actions artifact even if RED.

Expected outcome is **unknown** until original raw evidence is checked. If RED, preserve original and investigate failing cases in a new child, not change frozen native evidence or historical cohorts. No native model execution/Redmi, no STEP2/B3/JEPA/age/whole-system promotion from software suite. Private Library backup when permitted; no rejected anyone-writable Drive destination.
