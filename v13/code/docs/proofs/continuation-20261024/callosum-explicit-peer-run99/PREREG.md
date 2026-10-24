# Run99 — B3 utility from explicit peer-message causality, not rowid alone

Base Run98 PR #130 `cdf51f580731e60cea6477021814641915caa5f8`. Run94 World Model owner untouched.

Owner: `v13/code/v13/callosum.py` only `Callosum.outcome`, new `tests/test_callosum_peer_link_run99.py`, isolated workflow `.github/workflows/v13-run99-callosum.yml`, this proof. Historical synthetic tests `tests/test_callosum.py`, `tests/test_callosum_message_lineage_run98.py`, `tests/test_callosum_outcome_integration_run66.py` may need minimal positive fixture updates to explicitly identify consumed peer messages; preserve original once/CAS/utility assertions.

Hypothesis: even after Run98 source validation, a receiver OfferPacket produced later in SQLite rowid order may have `peer_message_packet_id=None` or point to another message, meaning the receiver never consumed the pending B3 message. Scoring such an offer poisons B3-H9 channel utility. SQLite documents rowid as a storage key that may change after VACUUM; rowid order is not a causal link (https://www.sqlite.org/rowidtable.html).

Preregistered RED: SOURCE_EXACT unlinked and wrong-link offers must score0; exact peer id scores once; a later linked offer must be selected over earlier unlinked offer. NO_MESSAGE control baseline intentionally has no peer and must remain measurable, with valid source/event/generation packet ordering. Keep B3 LATENT=0, SHADOW default, human ACTIVE gate unchanged.

Narrow candidate: for non-NO_MESSAGE channels require `OfferPacket.peer_message_packet_id == pending MessagePacket.packet_id` in addition to Run98 source/generation checks; continue scanning later receiver offers when an earlier offer is unlinked. For NO_MESSAGE baseline require absence of peer link, but do not claim message influence. Never infer causality from rowid alone.

Original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a/Z8 FAIL, full V13 INCOMPLETE.
