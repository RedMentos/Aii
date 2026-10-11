# Genuine causal-live output label exports

The adjacent exporter reuses the installed Store and the existing `:feedback output` human-control label contract. It does not change Runtime, train a model, approve an update or activate a head. Native answers remain previews, never human labels. Previously saved client and streaming proofs stay unchanged.

First generate an ordinary authoritative C3 answer in your V13 chat, then enter `:feedback output <your intended reference text> --learn`. A `record` label cannot be exported as learning authority. Stop chat before the exporter opens the same Store; an active coordinator is refused before native work.

From the source folder, list valid original labels and select the exact printed packet and source IDs:

```bash
python3 scripts/export_live_output_dataset.py labels --installed-home "$V13_HOME"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 scripts/export_live_output_dataset.py capture \
  --installed-home "$V13_HOME" --decision pkt_ACTUAL_ID --label-source src_ACTUAL_ID \
  --learn --out "$V13_HOME/exports/live-label-001"
```

Use a previously prepared exact causal-stream native build. The exporter does not download, rebuild or replace a missing binary. Each capture has one absolute maximum 90-second deadline, 768 MiB default process RSS bound and a maximum 64 native output tokens. The template/tokenizer server is reaped before the causal worker starts; both stages are sampled, cancellable and reaped on failure. The causal worker pauses once, exports its actual returned observation, resumes once with zero bias and performs no extra prefill. The label's token IDs are obtained from the pinned model's actual LlamaRunner `/tokenize` endpoint with `add_special=false`, independently of the preview.

The original human decision packet bytes, event, context packet, exact query and human label are preserved. Before and after native capture, the exporter checks the original typed feedback permission, source presence/hash, authoritative event, current model/context revision and exact context messages. A superseding human correction invalidates the old label. Different current model/runner/optimizer revisions require a fresh ordinary C3 context and human label.

`--learn` is a new explicit operator intent to export the unchanged, already authorized label for this exact context. The exporter persists a new typed `F5_HUMAN_CONTROL` decision in the real Store. It references the original packet/source and the actual observation source, and adds the exact causal feature ABI and observation hash required by the existing trainer. Its `export_binding` explicitly records `human_saw_future_features=false`. It does not pretend that the original human decision contained or saw subsequently captured native features, and it does not alter the original decision or manufacture permission from a model preview.

Collect distinct source queries and genuine labels. Repeated query-source hashes cannot be split across train/calibration/test. Assemble explicitly selected capture fragments offline:

```bash
python3 scripts/export_live_output_dataset.py assemble \
  --fragment "$V13_HOME/exports/live-label-001/fragment.json" \
  --fragment "$V13_HOME/exports/live-label-002/fragment.json" \
  --out "$V13_HOME/exports/live-cohort-001"
python3 scripts/train_live_output_adapter.py \
  --dataset "$V13_HOME/exports/live-cohort-001/dataset.json" \
  --out "$V13_HOME/exports/live-cohort-check-001" --validate-only
```

Assembly rehashes all original decision/context/event links and the nine exact native/source artifacts. It copies them into a portable dataset and invokes the unchanged causal-live trainer's full input validator. It requires 2–16 distinct native first-token target IDs and an identical model/library/worker/feature ABI across every observation; it cannot convert old heads or combine different native builds. All destination directories must be new. Partial failed exports/assemblies remain as diagnostic artifacts and are never labelled successful.

Two labels are only enough to assemble and inspect input validation. A usable training cohort must satisfy the existing source-group-disjoint folds: each train/calibration/test split needs at least eight sources and two labels for every target row, plus the unchanged calibration, finite-gradient, utility and retention gates. After validate-only reports readiness, omit `--validate-only` and choose another new output directory to run shadow training. A passing candidate still has zero approval/activation authority.

This implementation's focused tests use actual temporary Store databases and explicitly nonnative software artifact fixtures. They do not establish that a genuine operator-labelled native cohort exists or that any trained live adapter improves answers. Actual exporter native capture is a separate proof and must be run on the intended installed hardware/build.
