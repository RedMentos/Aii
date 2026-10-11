# F3 / F9 repeated-confirmation consolidation

The executable path stages exact, independently confirmed human decisions in a
slow source index. It compacts duplicate fact, preference or style records into
one multi-cue memory slot. Each cue and the unchanged value retain the exact
input, MemoryRecord and HumanDecision lineage. Existing real replay and report
consumers read that index through Memory.recall; generated replay text never
becomes the index value.

```
:feedback fact 400 Euro --learn
```

Supply independently authored experiences and explicit corrections first. Three
distinct experiences and distinct normalized input texts confirming the same
exact value for the same entity are the current BOOT minimum. Record-only
corrections, repeated identical inputs, dream hypotheses, provisional events and
unselected reference text do not qualify. This is a conservative confirmation
prior, not a measured universal truth threshold.

```
:learning shadow
:consolidate semantic
:requests
:learning commit
:approve <Request-ID>
:consolidate status
:consolidate rollback <Index-ID>
```

Review the concrete candidate: its value, every authored cue, confirmation
count and immutable source IDs are in the request and checkpoint. No automatic
activation occurs. The individually approved index is preserved across restart
and backups. Rollback removes the index while retaining original experience and
correction records. A source deletion, corrupt artifact, changed correction or
revoked learning permission prevents further use. Independent backups retain
their own data, as documented by the existing forget path.

```
:consolidate procedural
```

Procedural staging uses repeated, agreeing explicit human route decisions. Its
consumer matches an exactly authored query cue after whitespace/case
normalization. Explicit :route overrides remain higher priority. The index
does not infer a new route for an unseen paraphrase. Changed or ambiguous
current evidence falls back to existing routing.

Approved learned memory-retrieval annotations remain higher fidelity than
lexical compaction: a recall using the approved learned relevance callback
retains that callback's rows directly. The index cannot recreate rejected rows
or remove their annotations. Without that callback, compaction requires a
surviving ordinary member memory; an index is not a separate admission bypass.
Entity guards, session/global scope and memory thresholds remain in force.
Unrelated corrections retain their independent slots.

Global corrections supersede the same global key across sessions. A new
conflicting global value or record-only permission revokes the old index for
all consumers. A session-local same-key override suppresses a conflicting
global index only in that session; other sessions retain the global evidence.

BOOT work bounds are 512 source-memory records for staging/active validation
and 64 pending/approved indexes. Queries fetch limit plus one. Overflow refuses
staging before any candidate writes, or falls back to ordinary memory/routing
for active consumers, with a diagnostic. Evidence is never silently sampled.
Individual indexes additionally hold at most 256 confirmations. Rollback frees
index capacity while preserving history. Cancel/deadline checks occur before
work and throughout record and lineage validation; runtime consumers pass their
current cancellation signal and turn deadline.

This path does not merge adapters into native model weights, produce generated
abstractions as factual truth, prove unseen skill transfer or implement the
Canon's entire long-timescale parametric consolidation research. Those remain
separate unavailable capabilities. The implementation is an actual F3/F9
source-bound staging/approval/consumer path, not a claim of those capabilities.

Verification: tests/test_consolidation.py covers independent authority, repeated
input exclusion, compaction, entity/scope guards, permission conflicts,
checkpoint tamper, active-source forget, backup/restore, restart, rollback and
learned retrieval preservation. Selected self/teacher spans additionally retain
the original reference SourceRef; deleting that lineage disables the index.
tests/integration_consolidation.py runs actual
frozen C3 report and replay inference plus production routing; every completed
case and native metrics are saved. The initial statement-input replay failure
is retained in docs/proofs/consolidation-native-20261002.json. The corrected
question-input fixture passes 18 checks in
docs/proofs/consolidation-native-questions-20261002.json and the final complete
selection-lineage implementation in
docs/proofs/consolidation-native-full-lineage-20261002.json. After review, 23
unit tests additionally exercise learned rejection, global supersession, local
overrides, bounded work and cancellation. The native consumer rerun for those
fixes is docs/proofs/consolidation-native-reviewed-20261002.json, followed by
docs/proofs/consolidation-native-approval-bounds-20261002.json for the approval
record-cap guard. Expected-number
presence is a narrow consumer diagnostic, not general reasoning validation.
