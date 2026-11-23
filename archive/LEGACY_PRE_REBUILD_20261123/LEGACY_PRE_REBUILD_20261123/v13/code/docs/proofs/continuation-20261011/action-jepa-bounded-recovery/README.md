# Bounded native action-JEPA recovery

Original driver SHA: `42b38b8d0f3f96a811f330895de62e35ec81bfea89383edd3ba00da52d06defd` (unchanged).

Final offline lifecycle registration SHA: `93d0283a2c84f7abf31e214f7e3780954e42a53fce54eb357f4e5cc85a049216`.

At registration: no native inference; two control workers only registered; old 736×1024 / 46-batch closed prefix restored and verified. Runner and all 19 adjacent shared-library entries match the old registration exactly. Main `exact-resume` is a copy; the restored `action-jepa-native-capture` remains the unchanged historical reference. New native outputs are appended only to `exact-resume`.

`run-arguments.json` holds exact argument values. Launch `scripts/bounded_action_jepa_capture.py --run` with those flags only after the root agent has verified the registration on GitHub and released the serialized native inference slot.

First, two independent fresh workers each capture the same first sixteen inputs and stop at their successful atomically saved batch. Both arrays must compare exactly equal. Since native bytes match, their result must also exactly match the historical first sixteen rows. Each reused control additionally requires an observation of actual native startup/RSS, controlled checkpoint interruption and completed owned-worker reap. Any failure is preserved and prevents automatic main capture.

Then each owned main worker captures at most eight new batches of sixteen inputs. At the successful checkpoint boundary, the wrapper raises a classified lifecycle exception; the unchanged driver's own Popen cleanup terminates and waits for its child. Discovered host `/proc` PIDs are read only, never signaled. The next worker starts only after validated checkpoint lineage and previous child reap. Native request payloads, input order, context 2048, threads two, batch 16 and mean pooling are unchanged.

All numbered `main-worker-*.json` and control observations preserve actual return codes, cleanup operations, namespace-aware process identity/RSS and cgroup event baselines/deltas. Controlled interruptions also remain in the original driver's `failed-attempt-*.json` history; they are explicitly classified by the wrapper rather than deleted.

`scripts/checkpoint_action_jepa_prefix.py` can make additional portable closed partial ZIPs from a single atomic NPZ read plus its immutable batch records. The resulting archive never asserts completed capture or worker exit. Root must save them durably during the run.

After all 1875 actual rows are captured and native workers reaped, use the existing source-bound exporter and sealer. Retain old failure/prefix artifacts separately; main-cohort sealing does not copy or rewrite the historical failure archive. Publish exact dataset/native taps SHA before any training. `training-preregistration.json` fixes seeds 13/21/34 and unchanged original defaults/gates before results. Store every checkpoint, raw metrics and four-action external prediction replay, including failures. No runtime or learning authority is activated by this experiment.
