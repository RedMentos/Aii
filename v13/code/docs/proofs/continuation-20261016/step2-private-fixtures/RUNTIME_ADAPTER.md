# Private-source runtime adapter (new cohort, not yet native-run)

`runtime_adapter.py` connects the saved 39-fixture geometry to actual
`Runtime`, SQLite `Store`, immutable source blobs and `RunnerPool.get().generate()`.
It leaves the historical 10-fixture/70-row experiment and its `UTILITY_FAIL`
unchanged. This is a new quotation transport experiment, not an implementation
or successful measurement of the historical Offer/channel/state architecture.

The producer runner receives public option facts plus only its own private
Store SourceRef and source bytes. B1 receives budget; B2 receives deadline and
local-only clauses in the primary cases. A labeled contradictory-rule control
deliberately adds a conflicting budget clause to its B2-owned source. Producer
output must be strict JSON containing complete,
unchanged source quotations and their supplied SourceRefs. The adapter checks
role visibility, complete identity, the actual Store hash, deletion state and
exact source bytes. It rejects fabricated text, peer refs, modified spans,
duplicate keys/quotes and extra fields. Invalid output fails the row; it is
never replaced by an exact source or an oracle. Empty quotes remain empty.

C3 receives the public source plus the validated model-produced quotations.
The existing `v13.utility.score_decision` runs after C3 returns. The hidden
fixture oracle, completion witnesses and scoring answer never enter a runner
prompt. Captured prompt arguments are written before inference and raw chunks
are saved during streaming. Store messages and prompt hashes are linked to the
actual public event. Blobs and SourceRefs survive a real Store close/restart.

| Implemented arm | Producer calls | Consumer evidence |
| --- | --- | --- |
| `b1_model_quotes` | B1 | B1's validated output |
| `b2_model_quotes` | B2 | B2's validated output |
| `paired_model_quotes` | B1, then B2 | Both validated outputs |
| `same_policy_dual` | B1, then B1 | Same B1-only private input twice; duplicates add no peer source |
| `no_message` | B1, then B2 | Empty quotations |
| `exact_source_control` | None | Deterministic exact sources; explicitly **not model-produced** |

Historical `CONTROL`/`SOURCE_EXACT` channels, persisted dual-timescale Offers,
and a prompt-only retention ablation are **not implemented** by this adapter.
Missing-rule and contradictory-rule fixtures retain explicit kind labels and
their `UNKNOWN` targets. The fixed primary fixture geometry remains 30 cases,
with nine controls. There is no numerical utility promotion gate for this new
adapter, and no native/model-quality claim from its software tests.

From `v13/code`, after source review and installation of all three role models:

```bash
python docs/proofs/continuation-20261016/step2-private-fixtures/runtime_adapter.py register \
  --installed /absolute/installed-home --out /absolute/new-registration.json
```

Publish and verify that registration before starting its native cohort. It
binds fixture bytes, Python/spec source hashes, model paths/revisions/SHA256,
runner/shared-library hashes, hashed V13/loader/backend environment values,
device, fixed runtime config,
explicit row order, token caps and row deadlines. `--fixture-id` and `--variant`
can register a smaller **separately scoped diagnostic** before inference; the
registration records its exact coverage. A registration never overwrites an
existing file. The full default is 234 rows and at most 546 native calls.

```bash
python docs/proofs/continuation-20261016/step2-private-fixtures/runtime_adapter.py run \
  --installed /absolute/installed-home --registration /absolute/new-registration.json \
  --out /absolute/new-run-directory
```

The output directory must be new. Every row has a fresh real Store and starts
without peer/variant history, learning, embeddings or background sleep. Calls
run serially and unload their owned runner after each call. Source/model
bindings are checked before every row and after the cohort. Row deadlines use
the existing runner cancellation mechanism (default 90 seconds per whole row);
hashing, cold setup and process cleanup add wall time outside that sum. The
runner releases must report reaped processes. Incomplete coverage, inference,
source-integrity or lifecycle failures prevent `RECORDED`; native utility
failures remain scored failures. No automatic resume/retry repairs a cohort.

Software verification (real Runtime/Store, fake only at the runner seam):

```bash
python -m unittest discover \
  -s docs/proofs/continuation-20261016/step2-private-fixtures -p 'test*.py' -v
```

The associated `runtime-software-report.json` and `runtime-tests.log` record
that software check separately from the original fixture geometry receipt.

The separately exported `pilot/pilot-fixtures.json` is also accepted, with
explicit diagnostic scope. It selects three fixed complementary geometry
cases (A/B/NONE), giving 18 rows / at most 42 calls with these same six arms.
It cannot promote full STEP2 utility. See `pilot/PILOT_PREPARATION.md` for the
prepared model cache, remaining prerequisites and deferred registration steps.
