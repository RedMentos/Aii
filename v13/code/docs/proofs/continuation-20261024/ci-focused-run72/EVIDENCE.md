# Run72 public CI prereg/evidence

Goal: replace repeated isolated local excerpts with actual GitHub full-checkout imports of Run68-71 plus Run64/65 World Model integration tests. No paid provisioning: repo visibility PUBLIC (GitHub REST), standard ubuntu-latest runner free for public repos per https://docs.github.com/en/actions/concepts/billing-and-usage.

Workflow: sparse code checkout, `permissions: contents: read`, no secrets, no native model downloads, 10-minute job timeout, concurrency cancel. Official checkout action SHA `11bd71901bbe5b1630ceea73d27597364c9af683` verified against actions/checkout v4.2.2 GitHub commit. Python deps pinned numpy 2.3.5, prompt-toolkit 3.0.52. Official added-lines privacy scan requested with PR base SHA.

Before PR creation, CI result NOT RUN; no actual V13 Store or native evidence. This is test infrastructure only, not a completed V13 organ or promotion of any acceptance gate.

Gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
