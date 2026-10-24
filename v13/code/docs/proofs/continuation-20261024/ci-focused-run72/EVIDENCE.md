# Run72 public CI prereg/evidence

Goal: replace repeated isolated local excerpts with actual GitHub full-checkout imports of Run68-71 plus Run64/65 World Model integration tests. No paid provisioning: repo visibility PUBLIC (GitHub REST), standard ubuntu-latest runner free for public repos per https://docs.github.com/en/actions/concepts/billing-and-usage.

Workflow: sparse code checkout, `permissions: contents: read`, no secrets, no native model downloads, 10-minute job timeout, concurrency cancel. Official checkout action SHA `11bd71901bbe5b1630ceea73d27597364c9af683` verified against actions/checkout v4.2.2 GitHub commit. Python deps pinned numpy 2.3.5, prompt-toolkit 3.0.52. Official added-lines privacy scan requested with PR base SHA.

Before PR creation, CI result NOT RUN; no actual V13 Store or native evidence. This is test infrastructure only, not a completed V13 organ or promotion of any acceptance gate.

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.

## Verified real Linux CI — 2026-10-24

GitHub Actions workflow run **40129254641**, job **120977241720**, commit `a102f9a5055238480d1eed0dfdbde1c07511a34b`, completed SUCCESS. Raw log is stored unchanged in `CI_JOB_120977241720_RAW.log` (Git blob `bbadfcb14b82e0da7d4545631968539e70e6976b`), remote readback exact. Actual full-checkout V13 module imports and six focused suites: **46 tests, 46 PASS**; `compileall` PASS. Official `public_repo_privacy_scan.py` output: `privacy scan 8af0ac967..HEAD: CLEAN`. Job steps and outcome verified from GitHub Actions API.

This upgrades evidence from isolated excerpt to **real public Linux software/SQLite tests**, not native model training, target Redmi, whole-repository test suite or semantic utility. CI path filter was subsequently tightened to avoid re-running on evidence-only docs.
