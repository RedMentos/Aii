# LP3 Run20 open questions and exact next actions

1. Obtain a complete current Git checkout and independently review Run20 code-only candidate against PR #55 plus all newer Claude-owned work. Run complete unittest suite and official `public_repo_privacy_scan.py`; neither is proven here.
2. On an authorized writable delegated cgroup-v2 Linux host, execute a **synthetic-only** setsid-detached child negative control. Verify cgroup join marker, recursive populated=1, `cgroup.kill`, populated=0, no receipt, fixed-slot crash recovery. Do not run this on the current read-only host or signal unowned processes. Test PID/cgroup namespace and migration caveats. Candidate has only mocked/synthetic software proof.
3. Review potential malicious/privileged cgroup migration and permissions: this mechanism is process-lifecycle containment for cooperative native jobs, not a security sandbox. Require independent global owner attestation even with same-parent slot.
4. Recheck 7 pinned LFM2.5-350M snapshot files, 2 registered fixtures, `transformers`, memory fit and no competing native jobs before *any* LP3 four-seed native experiment. Current host is blocked (4 GiB, missing files/module).
5. Publish closed raw native evidence + externally anchored receipt only after kernel/full-checkout review. LP3 memory-key results cannot promote Body-JEPA or generated-answer utility; run separate equal-budget answer ablation.
6. Continue full V13 ROADMAP beyond LP3; STEP2/B3 gates, mobile hardware and many organs remain incomplete. No user decision currently needed.
