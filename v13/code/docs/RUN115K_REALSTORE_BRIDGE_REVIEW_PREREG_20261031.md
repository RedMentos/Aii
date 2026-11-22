# Run115K-R2 real-Store cross-organ integration test prereg (2026-10-31)

Owner: independent GPT-6 reviewer; child of Run115K-R authority patch. This is a second test package, not a change to Run115K owner's branch or frozen native cohorts.

Hypothesis: the default-OFF Run115K bridge can combine **actual persisted** B1/B2 OfferPacket/QueryPacket records from a real SQLite Store and Context OS SHADOW ContextPlan with exact prior/current USER SourceRefs and deterministic JEF A/10. Synthetic B1/B2 runners deliberately return wrong summaries and an invented quote; this must never be relabeled a verified body quote. The bridge must also refuse ACTIVE Context OS, later USER correction, tampered persisted offer and deleted source.

Fixed checks: new `test_run115k_realstore_bridge_review.py` builds `Runtime`, `TopicPartitionOfferConsumer`, and synthetic body stubs, asserts 0 output/actions, source-data only in C3 user role, zero quote authority, and real ContextPlan persistence. Run CI in isolated venv alongside authority and inherited tests; keep RED attempts, source hashes and negative gates. If fixture assumptions differ from the actual Store contract, preserve the failure and adjust only the isolated test fixture, never the production source or registered native cohort.

No native models, no Redmi, no STEP2/B3/Body-JEPA/age promotion; `jepa_weight=0` and Canon intact.
