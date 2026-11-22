# V13 C3 German arithmetic operator SHADOW probe — prereg 2026-10-30 run11g

Owner `assistant/v13-c3-de-operator-probe-run11g-20261030`, parent #1226 HEAD `773a158463d51687c711250f21c99dad21c26b38`. No shared native runner/model/C3 source edits. Original seed83 native script and registered model/source/seed hashes remain unchanged.

## Concrete utility goal
Existing C3 typed-read → deterministic arithmetic SHADOW is only usable through frozen batch experiments. Add an **explicit, opt-in local operator CLI** for one arbitrary German list-arithmetic source file, with two mutually exclusive modes: `--raw-json-file` (software replay of externally supplied typed JSON, no native claim) and `--native --home <installed V13 home>` (real C3 call only after strict Age0, model SHA/revision, binary SHA and source-pin checks). The CLI never routes to ToolStep/C5, never authorizes external actions, and does not change learning, approval, age or JEPA.

Output is a **new exclusive private file (0600)** containing source SHA256, raw C3 output and its SHA256, baseline typed-read SHADOW result, closed-world conservative SHADOW result, and native/replay provenance plus release/negative gates. Print only a short non-sensitive status. On native failure preserve an explicit failure record and release receipt; do not fabricate model results. No model download/provisioning or automatic install. Input UTF-8 text <= existing `listarith.MAX_TEXT`; output must not overwrite existing file/symlink. No public uploads of operator text.

## Frozen test plan before code
- Software tests of source-only replay: supported exact sum/difference, omitted-item conservative abstention, malformed/unsupported input, no invented native evidence, privacy of printed output, exact SHA256, fresh output permission 0600, no overwrite, no execution of ToolStep/C5, correct gate fields.
- Fake native runner tests may exercise lifecycle and guaranteed unload, but **must not claim real native execution**. Pinned actual native execution requires installed home/model and is a separate gate.
- GitHub Actions isolated software tests, py_compile, privacy/diff, closed raw artifact and hashes. Preserve all original failures; do not alter seed79/83/97/101 cohorts, C3 model hash, runner binary hash, registered seed or scorer.
- Acceptance: CLI works with supplied JSON in software mode and can *attempt* verified local native mode when prerequisites exist. This is an operator SHADOW diagnostic, **not** production ToolStep utility, STEP2 promotion or whole V13 completion.

Next: native operator probe only on available verified installed home; otherwise pursue other canonical organ. Gates: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA unavailable; jepa_weight=0; Redmi UNMEASURED; V13 incomplete.
