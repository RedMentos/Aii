# Run12L — preregistered disjoint C2 route-label proxy, Linux-native (2026-10-30)

Owner: GPT-6 automation. Review-only child of Run12K PR #1267, parent HEAD `0470e5c06f7382d0fea1263691bbbdca636d692e`. **This preregistration and fixture were committed before any Run12L native execution.** No existing cohort, source/model/seed, training head, runtime route policy or frozen negative gate is changed.

## Fixed data and identity

- Fixture: `docs/fixtures/c2_route_proxy_run12l_20261030.json`, 15 new synthetic prompts, exact original seed **43** because the original `c2_native_route_provenance_20261030._turn` remains frozen. First 12 have boot scaffold `simple`: four greeting/acknowledgement controls labelled `simple`, four explicit arithmetic/reasoning requests labelled `detail`, four condensation/overview requests labelled `gist`. Last three are non-simple scaffold controls labelled detail/gist/both. The labels are **manually defined route-role proxies**, not measured user benefit, correctness or body answer utility.
- SHA256 of canonical UTF-8 `json.dumps(fixture, sort_keys=True, separators=(',',':'), ensure_ascii=False)`: `9d65d64ffeca0291b27809b572696c27c74c45ac0df9975e3aceda4ee24181dd`. Prompt tuple SHA256 using original Run12K tuple canonicalization: `ecf13d17b7be4f8516d4c193d2e8bef05f6d0c5e5577985f64e73cd9f2252655`. All prompts must be disjoint from original Run12K and seed43 three-case cohort.
- Parent pinned Run12J runtime Git blob `22ed11e4a53d9eeae8fbc74a1753082b5785be2b`, original native `_turn` blob `fb34dba97ae3700ba5accdcb928bfb72afcf4fcb`, Run12K strict classifier blob `cee1980787f1217e9a7aa2a1f180686b4add67fb`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Pinned Cactus-Compute/needle3 model SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38` (Apache-2.0, revision b274efcb211a9eef48c9a88da4b43bd569696a39); original worker build, no replacement model.

## Predeclared readouts, pass/fail

1. **Structural native provenance**: 15/15 actual native C2 operation C/FINAL with source/event/session/ExecutiveControlContext evidence before release and process reaping; 15/15 Run12K strict unique-tool admission matches; three non-simple controls stay scaffold. Any miss is structural RED. Save all rows including failures.
2. **Route-label proxy** on first 12: compare the exact final route (native-advised only when strictly admitted; otherwise scaffold) against the fixed reference labels. Count correct for both boot scaffold and final selected route; report all 12 per-case changes, selection count, gains and regressions. Predeclared exploratory proxy threshold: **at least 3/12 actual native admissions, at least +2 net correctly routed cases, and zero regressions on four greeting controls**. Do not move threshold after seeing outputs. This is a proxy threshold, not a runtime activation gate.
3. **Not measured**: semantic answer accuracy, route utility on actual C3/Body outputs, latency/cost tradeoff, learned calibration, Redmi, STEP2, B3, Body-JEPA, JEPA weights, age progression or whole-system acceptance. Even a proxy PASS leaves all these gates negative.

## Execution, containment and evidence

- Add isolated source-only tests and runner first; only after source/pins verification trigger a serialized GitHub Actions Linux-native run in existing `v13-step2-budget-paired-native-20261030` concurrency group. Download only pinned Needle3 and build original native worker; no C3/Body invocation, no user-facing answer or training. Age0 `RECORD_ONLY`, `jepa_weight=0`, latents OFF, per-prompt isolated Store.
- Record exact HEAD, Git blob pins, stage exit codes, raw native packets, original failures, model/worker SHA256, ZIP SHA256, CRC and inner hashes. Preserve raw on RED as well as GREEN. Independently audit original artifact and private byte-exact backup when accessible; an Actions status alone is not a validated native result.
- Original Run12K greeting selecting `gist` is retained as negative evidence; this disjoint cohort tests whether such regressions generalize. No promotion or automatic production merge.

**Next after this package:** preregister an actual paired C2 route → C3/B1/B2 response utility and resource-cost experiment, with task-bound truth labels, stable source/seed hashes and independent blind scoring; continue Context OS and Body-JEPA work in parallel.
