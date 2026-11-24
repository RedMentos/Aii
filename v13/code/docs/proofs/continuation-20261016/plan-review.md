# Plan continuation review — 2026-10-16

Read-only source review of GitHub M commit `1941d07afeb57299d7d5a466fd1eb44ec2569dfe`
and K commit `4ed1539fb9fd6ea961fc6145bd98745e5f63adac`. Local M checkout was
also inspected. No model process, runtime edit, shared-status mutation or branch
operation was performed. This note is the only created project file.

## What supersedes the October 13 review

* M's competence-v2 experiment is now closed: 420/420 live calls, both worlds
  pass; arithmetic AUROC .98, in-world flagged .03, out-of-world flagged .90;
  notes 1.00 / .00 / 1.00. Evidence:
  `continuation-20261013/tool-forecast-competence-v2/{README.md,report.json,live-report.json,rows.json}`.
  It is no longer an uncompleted preregistration.
* M, as file owner, incorporated the five Codex lifecycle/binding defect fixes.
  `continuation-20261013/toolforecast-binding-fixes/README.md` explicitly says
  Codex's old hash-bound candidate remains on its original branch and must not be
  reapplied over the newer source. Adaptation/experience lineage, atomic
  installation, pending-checkpoint changes, malformed encoder configuration and
  orphaned pending arrays are addressed. This is software robustness evidence.
* Confirmed region-learning round 2 used competence **v1**. It cannot certify
  the current v2 learner. V2 competence success is a detection result, not a new
  learning-quality result. New bindings also make old unbound adaptation proofs
  ineligible; a device needs installation and fresh compatible experience.
* K's new handoff is a concrete integration instruction. `list_arith` and M's
  note/forecast path both need to survive. The shared Claude folder reported as
  combined is a historical reference, not a remotely accessible working tree.

## Freeze and historical status

AGENTS' freeze sentence is conditional: isolated fixes until the SourceHandoff
cohort permits integration. M ROADMAP sections "16-Fall-SourceHandoff-Ablation"
and "Freeze-Status 2026-10-12 08:00Z" explicitly lift it. The native evidence
`continuation-20261012/source-handoff-ablation-claude-rebound/BEFUND.md` records
16/16 FINAL rows, all processes reaped, unchanged run artifacts and no utility
gain. Thus the **original 121-source cohort freeze is over**. It does not block
normal owned integration. New native experiments still require separate source,
model, library and numerical bindings; an active later cohort remains protected.

HANDOFF_CURRENT and BUILD_STATE retain older capture/2-of-15 Dream pointers.
They must not be treated as instructions to repeat completed old work:

* Original Action-JEPA NumPy seeds 13/21/34 were completed and failed their
  candidate gate (`docs/continuation-20261012-action-jepa-native-seeds.md`).
  Later changed objectives and fresh rounds are separately scoped evidence.
* `docs/DREAM2_PROTOCOL.md` now documents v3 **15/15**, with the numeric protocol
  unchanged and a fresh directory because platform binding prevented v2 resume.
  `continuation-20261012/dream2-b40-v3-comparisons.json` reports
  `COMPLETE_SCOPED_COMPARISONS`, no missing arms, no phone/canonical pass.
  Validated dreams improve A paraphrase .75 vs replay .42 but reduce generic
  probe retention .19 vs .61; "Dream helps overall" is unsupported.
  Preserve old v2, do not resume it as if the full cohort is still missing.

STEP2 UTILITY_FAIL, B3 L1 FAIL, native body/sparse-learning gaps and Redmi gates
remain. None is promoted by the above completion corrections.

## Recommended immediate substantive package

Integrate K's measured R4 tool path with current M's tool forecast on a separate
coordinator branch. This is concrete missing product behavior, not another audit.
K's handoff lists the exact scope:

| File | Preserve from K | Preserve from M |
|---|---|---|
| `v13/toolstep.py` | `_propose_list`, list shadow/layer behavior, `LIST_*` | `propose_note_edit`, `_forecast`, current forecast lifecycle |
| `v13/agi/tools.py` | `list_arith` registry entry | tool execution/forecast behavior |
| `v13/transaction.py` | WP-W2c `text` argument contract | existing transaction and approval behavior |
| `v13/broker.py` | concise list-arithmetic correction | current broker behavior |
| `v13/agi/listarith.py` | R3 operation/typed recipe and source-number guard | new module, no M replacement |

Tests should exercise the actual combined path: a list request, a note-edit
proposal/approval with forecast enabled, a calculator request, an unrelated
request, persistence/restart and the existing SHADOW/Age/permission boundaries.
Preserve both owners' tests; run focused suites then the full combined suite.
No native resources are required for the first software integration. Do not
change default tool permissions, Age ceilings, measured protocols or B2 switches.
Native quality belongs to a subsequently bound validation run.

Following that, the original-plan STEP2 bottleneck admits an independent new
fixture package: source-disjoint tasks that actually give B1 private necessary
information and B2 different necessary information, with no oracle in prompts.
The old producer evidence explicitly says current fixtures give B1 no independent
advantage. Generate and test source visibility, solo insufficiency, paired
solvability, contradiction and exact-control cases first; preregister a fresh
native cohort before measurement. Keep the original failing cohort immutable.
This package can own new scripts/tests/data without editing live runtime.

## Real resources and prerequisites

At inspection, the locally materialized M checkout had **zero `.gguf` files**.
No present executable/library installation or old live worker was certified.
Pinned rebuild/recovery recipes and closed historical results exist; neither
substitutes for current verified runnable native resources.

All twelve referenced ToolForecast asset files were present and hash-matched
`specs/tool-forecast.json`: checkpoint, competence, replay, drift sample, metrics
and parity for `calc_counter` and `note_edit`. Their trained source is already
available; it should not be retrained merely because scratch is new.

For a fresh v2 learning experiment or Redmi run:

1. Restore the exact B2 Qwen capture GGUF, SHA-256
   `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`.
2. Restore/rebuild pinned b10964 libraries and `native_layer_taps.cpp`; verify
   actual native identities, current resource/lifecycle registration and the
   device/install parity gate. A different build requires transparent binding,
   not pretending it is byte-identical to capture binary `c00d6829...`.
3. Install current v2 retention with token-mean taps; collect compatible fresh
   experience under current binding. A v2 learning-quality claim needs a new
   preregistered plan with untouched held-out states, not reused v1 round-2 data.
4. Serialize native work, hold the coordinator lock, honor measured memory limits
   and reap only owned processes. Device script `TESTEN_TOOLFORECAST.sh` already
   implements the build/parity/live path; `--with-learning` runs the stored plan
   with current source, which is a new-source measurement, not original v1 proof.

Automatic sleep-triggered learning remains an original-plan follow-up, but first
requires N's sleep/scheduler changes to be integrated or explicitly owned. It
must not silently claim that this M-only checkout already includes them.

## Limits

These are pinned source/proof readings and a local asset-hash check. The full
raw native arrays and recorded experimental scores were not independently
recomputed. Claude's live thread activity is unobservable here. The parent
coordinator owns remote freshness verification, integration and current status.
