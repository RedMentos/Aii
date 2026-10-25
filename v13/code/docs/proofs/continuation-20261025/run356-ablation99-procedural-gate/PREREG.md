# Run356 prereg — synthetic ablation must not demand unmeasured procedural authority

Parent: Run355 source-only review head `fa889e5cce02911317e58c749c7a22900bf803c9`, chain PR351→PR350→PR349, not main. Owner: `v13/code/tests/test_ablation99.py` plus isolated proof/CI only. Do not edit `fastforward.py`, Runtime, safety/learning/age gates or canonical source.

## Observed RED and conflict
Run354 exact-head full Python suite `40227346223`, job `121271424097`: `test_proceduralization_v13_is_cheaper_than_deliberation_and_safer_than_static` fails `AssertionError: 3.0 not less than 3.0`. The old synthetic ablation expected V13 to execute a READY shortcut based on predicted latency. The newer reviewed Run342 FastForward canonical §85.6/G-PROCEDURALIZATION-004 gate intentionally denies shortcut authority until **measured paired latency AND energy**, noninferior accuracy, reopening and source/rule preservation are verified. `FastForward.procedural()` has no complete measured receipt writer and remains shadow even when ACTIVE was explicitly selected. Loosening this safety gate to make an old cost benchmark pass is forbidden.

## Frozen acceptance
1. Keep the original synthetic stream, V13/full/static arms and comparative error-after-drift/salience assertions. Require `v13.fast_path_share == 0`, `v13.cost_per_turn == full.cost_per_turn`, and `static.fast_path_share > 0` while the canonical measured receipt is absent. This tests the correct fail-closed cost, not a claimed speedup.
2. Run original `tests.test_ablation99` plus `tests.test_fastforward_canonical_gate_run342` and `tests.test_fastforward_latency_gate_run300` on exact-head source-only CI. Require that fake/predicted-only READY does not grant action authority. Preserve every negative gate and failed full-suite baseline.
3. No new model/native/Redmi/energy measurements; no proceduralization utility PASS. Privacy and source hashes, raw evidence and private checkpoint required.
4. If any test fails, preserve RED and diagnose rather than retune measured-gate criteria.

Next command: `cd v13/code && python -m unittest -v tests.test_ablation99 tests.test_fastforward_canonical_gate_run342 tests.test_fastforward_latency_gate_run300` with pinned CPU-only dependencies.