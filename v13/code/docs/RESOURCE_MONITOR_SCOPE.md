# Existing F7 resource observation

`v13/resources.py` reads the current Python process through `/proc/self`.
For a numeric child PID, it verifies `/proc/self/ns/pid` identity and the last
`NSpid` element before reading memory. This handles a `/proc` mounted from an
outer PID namespace, where the Python PID can name an unrelated host process.
A maximum of 4096 directory entries is examined per resolution; negative
lookups wait two seconds before scanning again. A verified process start time
is cached. The identity is checked again after reading memory. If the process
exits or its identity changes, its numeric PID remains unavailable for this
resolver lifetime, because the original child cannot be identified by number
alone. Tracking is bounded to 4096 identities; exhaustion returns unavailable.

The public PID, RSS, PSS, mapped-file and fault fields remain present. Additional
`resolved_proc_pid` and `measurement_status` describe the verified observation.
Missing permissions, an unsupported namespace or PID reuse produce null
measurements rather than reading a coincidentally matching host process. A
missing `smaps_rollup` leaves PSS null while preserving verified RSS. Mapped file
bytes are virtual file-backed mappings, not resident memory or a KV measurement.

`v13/pressure.py:NativePressureMonitor` repeatedly uses actual `snapshot()`
results and the existing `ResourceGuard` thresholds. Its single-use context
starts with an immediate snapshot, followed by a bounded 0.1–1.0 second cadence
(default 0.25 seconds). It retains 64 snapshots, 32 state transitions and up to
32 supplied child PIDs. Runtime may supply the existing shared guard, phase
callback and cancellation Event:

```python
monitor = NativePressureMonitor(home, cfg, pids=pool.pids,
                                cancel=cancel_event, guard=guard)
with monitor:
    # Existing native operations keep their existing cancellation checks.
    run_existing_native_path()
resource_report = monitor.report()
```

`PRESSURE` updates the shared state for the existing scheduler/fallback policy.
Measured `CRITICAL` latches `MEMORY_CRITICAL`, `THERMAL_CRITICAL` or
`MEMORY_AND_THERMAL_CRITICAL`, captures the actual triggering snapshot and sets
the existing cancellation Event. It never kills a process, clears user cancel,
or writes database state from the observer thread. The operation owner maps
this reason to its resource interruption diagnostic, keeps native partial text
and performs native unload through the existing cancellation path. The monitor
must remain active across load, prefill and streaming, then stop before the
next queued operation clears cancellation.

Stop wakes the observer immediately; a delayed sample cannot publish or signal
cancel after stop. Observer errors are counted, not converted into invented
normal/critical measurements. Peaks are the highest measured single-process
RSS/PSS across snapshots, not a sum of resident bodies. Missing battery sensors
remain null. `native_kv_bytes` remains null because no exact KV-byte port exists.
This primitive does not invent a cold-cache eviction policy or neural resource
policy; it makes the existing measured pressure state/cancellation continuous.

Verified artifacts:

- `docs/proofs/process-memory-unit-20261004.log`: 10 tests, including unrelated
  namespace, reuse between reads, missing permissions and bounded tracking.
- `docs/proofs/resource-monitor-unit-20261004.log`: 7 tests, including unchanged
  critical thresholds, missing measurements, recovery and immediate stop.
- `docs/proofs/process-memory-actual-20261004.json`: actual Linux child with
  32 MiB allocated. Inner PID 11 resolved to proc PID 3208; measured RSS
  40,144,896 bytes and PSS 38,029,312 bytes. This is a process-identity/memory
  check, not a Redmi model, thermal, energy or sustained-pressure proof.

Runtime/native-model interruption proof is recorded separately by the owner
that integrates this primitive. These isolated tests do not assert that such a
full-path proof has already passed.

The owner subsequently integrated `NativePressureMonitor` across Runtime turn
processing. `tests/integration_resources.py` now exercises the actual installed
C3 model through an isolated Runtime and durable queue. The final raw proof
`docs/proofs/resource-monitor-native-20261004.json` passed all 15 checks:
load/prefill/stream observed, verified native RSS/PSS, actual native partial
text before user cancel, retained cancelled text, native child reaped, monitor
stopped, restart preservation, subsequent actual C3 response, model SHA
unchanged and database integrity. Inner PID 13 resolved to proc PID 4250;
observed native RSS was 308,989,952 bytes and PSS 307,597,312 bytes. Eight
continuous monitor snapshots included seven native RSS observations.

The first proof is preserved as `resource-monitor-native-first-20261004.json`:
it correctly failed the cancellation checks because a 0.6-second delayed
cancellation missed a real 0.17-second stream. The collector now cancels on the
first stored native chunk. No threshold or success criterion was relaxed.
Neither native run created real critical memory/thermal pressure; those flags
remain false. Critical threshold behavior is covered by the isolated sensor
input tests, separately from this measured native/user-cancellation proof.
