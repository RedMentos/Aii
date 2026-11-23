# Causal live first-token shadow training

`scripts/train_live_output_adapter.py` is an offline executable entry point.
It makes no native calls, changes no Runtime state, and grants no approval.
The currently saved native probes contain no genuine exported HumanDecision
`--learn` cohort, so an actual trained live candidate is still unavailable.

```bash
python3 scripts/train_live_output_adapter.py \
  --dataset exported-cohort/dataset.json --out validation-attempt --validate-only
python3 scripts/train_live_output_adapter.py \
  --dataset exported-cohort/dataset.json --out fresh-shadow-attempt
```

Validation writes a diagnostic even for missing/invalid labels or insufficient
source folds. Existing output directories are never reused. The original
worker requires at least eight sources per train/calibration/test split and
at least two labelled examples per selected native vocabulary row in each.

The exporter must preserve the actual return from the existing pause call.
The already saved streaming diagnostic does not include that return as a
separate file; its frozen source/proof must remain unchanged. A future caller
exports it immediately, without another prefill:

```python
observed = session.pause()
atomic_write(export_dir / 'observed.json', dumps(observed))
```

Dataset schema is `V13_CAUSAL_LIVE_OUTPUT_TRAIN_INPUT_V1`. Top-level fields:
`schema`, `feature_abi` (the exact full returned ABI), `token_ids` (two to
sixteen selected native rows), `config`, `observations`, and optionally
`active_checkpoint`. Each observation supplies artifact descriptors
`{"path": "relative-file", "sha256": "exact-file-sha256"}` for:

| Artifact | Required content |
|---|---|
| `observed` | Actual pause return, including feature ABI and context handle |
| `features` | Full raw actual 1024D state plus 65536 logits/probabilities |
| `context` | Exact messages, measured prompt, tokens and `history_trimmed: false` |
| `tokens` | Existing token file with exact IDs and context source hash |
| `result` | Actual completed same-context native result with no extra prefill |
| `query_source` | Exact authoritative user query text |
| `label_source` | Exact explicitly supplied human output-reference text |
| `human_decision` | Typed existing F5 `HumanDecision`, output kind, permission `learn` |
| `label_tokenization` | Exact native tokenization of that human reference; no specials |

The HumanDecision must be produced by the human-control path for this live
observation. Its selection binds `target_position: 0`, the exact
`feature_abi`, `live_observation_sha256`, and a `context_ref.sha256` matching
canonical serialized messages. Its label SourceRef covers the whole exact
label file. Do not retrofit or fabricate a HumanDecision by editing an old
stored record. `label_tokenization` binds `source_sha256`, `model_sha256`,
`worker_sha256`, `add_special: false`, and actual `token_ids`. The first token
must be one of the configured target rows. Native answers never supply labels.

The six explicit optimizer config fields use existing knob bounds:
`output_adapter_steps`, `output_adapter_lr`, `max_update_norm`,
`retention_max_delta`, `output_adapter_max_bias`, and
`output_adapter_support_cosine`. Query-source hashes define deterministic
source groups; duplicate groups are rejected. Feature/model/library/source ABI
must agree across every raw observation, decision, and active live checkpoint.
Separate-prefill v2 checkpoint weights, anchors and normalizers are never
converted or reused.

Training reuses the unchanged existing numerical function and its gradients,
optimizer, split, calibration, held-out utility, support, retention, reload and
repeatability gates. Only a private function-global serializer format binding
sets `c3-live-prefill-first-token-delta-v1`; production module state is unchanged.
The fresh candidate additionally contains exact scalar JSON `feature_abi`.
Original retention anchors are preserved. More than the live executor's 512
anchors fails an explicit execution-capacity gate rather than dropping anchors.

A mathematically eligible candidate remains pending human review. The report
grants zero approval, native-body parameter, semantic-truth or production
authority. Six focused software tests exercise bindings, revocation, ABI/hash
failure, group leakage, legacy refusal, real numerical gradients/reload and
contradictory retention. Synthetic unit vectors are not native training proof.
