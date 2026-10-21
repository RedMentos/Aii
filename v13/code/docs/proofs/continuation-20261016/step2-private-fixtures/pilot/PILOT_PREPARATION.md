# Diagnostic pilot prepared; no native run or registration yet

The pilot selects the lexicographically first complementary fixture per solved
geometry action, in fixed A/B/NONE order. This selection uses source constraints
only and was exported before any native outcomes:

| Fixture | Geometry action |
| --- | --- |
| `private_bfzwzwww` | A |
| `private_eztsxxpt` | B |
| `private_amvcghct` | NONE |

`pilot-fixtures.json` and `pilot-selection-manifest.json` bind this selection to
the original full fixture document and the selection/generator source SHA256.
The six existing adapter arms produce 18 rows and at most 42 native calls.
This is a transport/quotation diagnostic and cannot promote STEP2 utility.
The separate full benchmark remains 39 fixtures / 234 rows / 546 maximum calls.

Downloaded into the **new** isolated cache
`/workspace/scratch/f24630d7727d/private16-pilot-home`:

| Role | Pinned model | Revision | Bytes |
| --- | --- | --- | ---: |
| B1 | LiquidAI/LFM2.5-1.2B-Instruct-GGUF QAD Q4_0 | `6767265158422fb8a19c62ceb45f16f05363615b` | 695755488 |
| C3 | LiquidAI/LFM2.5-350M-GGUF QAD Q4_0 | `657e078c94084481950a2d555a941481f715536b` | 219312832 |

Both actual file SHA256 values match the pinned catalog and download manifest.
`model-cache-receipt.json` records the full hashes, file paths, revisions and
license metadata (`LFM Open License 1.0`, linked at each pinned revision).
License metadata comes from the repository's pinned catalog; this preparation
does not invent a user license-acceptance record. No weights were loaded.

B2, runner and shared libraries are deliberately absent from this pilot cache.
No main native-home model, runner or library was copied, linked or changed.
Registration is therefore intentionally deferred until the main native cohort
and its replay are closed and verified by the coordinator.

Read-only runner resolution observed during preparation:

```text
/workspace/scratch/f24630d7727d/native16-evening-home/bin/llama-server
  resolves to
/workspace/scratch/f24630d7727d/native16-evening-home/bin/b10964/llama-b10964/llama-server
```

The same resolved directory contains the runner's `lib*.so*` files. After
cohort closure, the coordinator can make an independent physical copy of that
directory into the pilot cache, preserving relative shared-library links, and
create its own `bin/llama-server` link. B2 also needs its own physical model
copy and a merged `gist` entry in the pilot `config/models.json`; preserve the
already downloaded `body` and `language` entries. Do not use hardlinks or write
back into the main native home. Verify the completed pilot artifact hashes.
These setup actions have **not** been performed by this preparation.

Then review/freeze current sources, register this exact pilot document, publish
and verify the registration, and only afterward start its serial native run:

```bash
python docs/proofs/continuation-20261016/step2-private-fixtures/runtime_adapter.py register \
  --installed /workspace/scratch/f24630d7727d/private16-pilot-home \
  --fixtures docs/proofs/continuation-20261016/step2-private-fixtures/pilot/pilot-fixtures.json \
  --out /absolute/new-private-pilot-registration.json

python docs/proofs/continuation-20261016/step2-private-fixtures/runtime_adapter.py run \
  --installed /workspace/scratch/f24630d7727d/private16-pilot-home \
  --fixtures docs/proofs/continuation-20261016/step2-private-fixtures/pilot/pilot-fixtures.json \
  --registration /absolute/new-private-pilot-registration.json \
  --out /absolute/new-private-pilot-run
```

The registration CLI has a machine test exercising real argument parsing,
saved fixture loading, diagnostic scope validation, source hashing and output
generation. Only installed-artifact lookup is replaced in that software test;
it does not assert that native prerequisites are already installed or create
a real native registration. Native processes have not been started here.
