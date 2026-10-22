# ToolForecast lifecycle audit and isolated candidate — 2026-10-13

Thread M owns the live files. This review does not alter `v13/toolforecast.py`,
`scripts/install_tool_forecast.py`, the phone driver, existing tests or status.
All evidence here is synthetic Linux software evidence, with no model inference,
native build or third-party install. No Redmi, forecast-quality or AGI claim.

## Reproducible original defects

`reproduce.py` checks the original module, hashes the reviewed sources and writes
`result.json`. The fake encoder never starts a subprocess.

1. **Passing region adaptation is not bound to its competence classifier or
   encoder/retention identity.** `toolforecast.py:333` checks checkpoint and
   adaptation bytes only. The actual v2 reference can mark a context out of
   domain solely because of its mean tap; the earlier last-only reference calls
   it in domain. The old adaptation still loads and now activates for this new,
   unvalidated region. Current learn receipts also omit competence/model/layer,
   retention and runtime-source bindings. Changing the gate requires a new
   validation cohort, not silent reuse of its old receipt.
2. **Failed reinstall destroys the previous passing retention.**
   `install_tool_forecast.py:248` overwrites live retention files before all
   parity gates pass. A failed install writes a separate failure record while
   retaining old `encoder.json`. Repro: exit 1, old encoder JSON byte unchanged
   and still accepted, but both old retention hashes no longer match. Even an
   exception after the first world can leave a partial generation. The main
   encoder pointer itself uses non-atomic `write_text` at line 265.
3. **Pending checkpoint attribution is not checked across restart.**
   `toolforecast.py:563` validates the tool executable hash but does not compare
   the recorded checkpoint hash with the checkpoint being used to score. A
   synthetic same-width replacement with a changed projection still scores and
   appends experience under the new world. The repro injects the replacement
   checkpoint to isolate this guard; it does not assert a real new measured
   checkpoint or infer new native quality.
4. **Damaged encoder JSON breaks status.** `load_encoder` and `report`
   (`toolforecast.py:262,664`) propagate `JSONDecodeError` for a partial JSON
   file. This matters because the installer writes that pointer non-atomically.
5. **Pending cap does not cap context files.** Removing old pending rows at
   `toolforecast.py:546` leaves their `.npy` context files. Repro: 66 context
   files for the 64-row cap. This is a cleanup issue, not a model-quality gate.

The isolated candidate now addresses all five items. The phone driver's
long-stage cancellation and verdict exit-code handling belong to the
coordinator's separate driver review.

## Concrete isolated runtime candidate

`scripts/toolforecast_binding_candidate.py` provides `materialize_runtime()`.
It checks the exact original runtime SHA and applies unique replacements to an
in-memory copy. It never edits M's source or installs a Runtime hook. The copy
wires binding into the actual `predict → pending → observe → Experience →
learn → load_adapted` paths, keeping the original mathematical fit, holdout and
retention gates. It rejects legacy or incompatible experience and adaptation
receipts; it never labels historical buffers as newly validated evidence.

Bindings cover checkpoint, metrics, parity, competence and replay assets;
original runtime and installer source; candidate source; model, tap binary,
capture layer/pooling/normalization; and the exact retention bytes for learning.
Before/after fitting and before/after pre-effect tapping snapshots must match.
Pending snapshots must match before **and after** outcome tapping, before any
projection, score or experience append. A synthetic outcome-tap callback changes
a private competence asset; the candidate closes it without scoring or learning.
Tool effects, OFF/SHADOW
semantics, approval requirements and `used_for_decision=false` remain inherited.

Malformed/truncated encoder JSON or a partial passing configuration now makes
`:toolforecast status` return `ENCODER_CONFIG_INVALID`; unreadable configs return
`ENCODER_CONFIG_UNREADABLE`. Prediction remains unavailable without starting a
tap process. Capacity eviction now returns the evicted IDs from the successful
StateBox mutation, then removes only their coordinator-generated `.npy` names.
The original pending files remain intact when persistence fails. Real candidate
tests verify 66 forecasts leave exactly 64 committed pending rows and 64 matching
context files, unrelated files survive, and an injected state-write failure
deletes none of the 64 original contexts. A failed prediction may still leave its
new, uncommitted context file; this conservative behavior avoids deleting a file
after an ambiguous persistence failure. It is separate from capacity eviction.

`publish_verified_encoder()` is a separate, tested publication helper. It takes
private staged retention files and a source snapshot captured **before** parity,
validates all hashes, seals a new immutable generation and atomically changes
only `encoder.json`. Failed parity performs zero writes; interruption before
pointer commit leaves the previous encoder and retention intact. This helper
is **not wired into M's installer**; M must adopt private staging plus the helper
after the current ownership/cohort boundary permits it. Never overwrite the
live retention before calling this helper.

Existing encoder records do not include dynamic backend/shared-library hashes.
That upstream provenance gap remains unresolved; the candidate does not invent
them. Legacy buffers require explicit archival/reset or a separately justified
migration. They are deliberately not usable for new learning in this candidate.
The strict helper hashes the complete model file on every binding check. Its
additional Redmi I/O and latency are **unmeasured**. This is a correctness
candidate, not a deployment/performance recommendation.

## Tests and limits

`test_toolforecast_binding_candidate.py` has 24 targeted tests, including actual
copy lifecycle across restart and a **new synthetic** dataset running through
the unchanged fit gates. It proves software behavior and source compatibility;
it cannot demonstrate native prediction quality or phone utility. Ten existing
focused classify/live-path/device-build-plan tests are also run in the closed
validation log. Native encoder tests and the full suite are not invoked.

One intermediate candidate-test edit misplaced the nonfinite-weight block and
produced `NameError: p is not defined`. It was corrected; the final 24-test
candidate suite plus 10 existing focused tests passed. The failure history remains
in `report.json` and is not a native-model
failure. Use `test-output.txt` and `report.json` for the final closed check.

```bash
cd v13/code
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests \
  python -m unittest -v test_toolforecast_binding_candidate \
  test_toolforecast.ClassifyTests test_toolforecast.LivePathTests \
  test_toolforecast.DeviceScriptTests
python docs/proofs/continuation-20261013/toolforecast-binding-review/reproduce.py
```
