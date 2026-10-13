# Scoped branch-content audit candidate, 2026-10-13

Read-only comparison of 44 declared package files, pinned to locally fetched origin refs.
No network, inference, merge, checkout, runtime change, shared status edit or thread-completion claim.
The parent coordinator independently checks whether these fetched pins still match the remote.

| Owner | Fetched source commit | Working match | Working missing | Working different |
|---|---|---:|---:|---:|
| K | `42a28dda70b1` | 0 | 3 | 2 |
| L | `b0d00ef17571` | 0 | 3 | 3 |
| M | `673e3fb20196` | 6 | 0 | 0 |
| N | `434b19b1889f` | 0 | 10 | 2 |
| O | `c9b7eddf9964` | 0 | 3 | 2 |
| P | `3d7d8e8386df` | 0 | 5 | 0 |
| G | `483af03452ad` | 0 | 1 | 4 |

The source baseline is Thread M (`673e3fb20196ec77f0f32eecc5f6e149f8423a15`).
The working checkout HEAD is `d826f55f677a5ab7668af3762e00703178c1b2b7`, so the report records
`WORKTREE_HEAD_DIFFERS`. No scoped source path is missing at its pinned owner commit,
and no scoped file is dirty in this receipt. Missing/different working files describe
blob/mode comparisons only: they do not establish that a merge is required or safe.
The plan intentionally assigns ownership only to selected files; it does not redefine
ongoing Claude ownership or exhaustively cover all branches.

Important evidence boundaries: M's competence-v2 path contains the preregistration;
its active experiment is not resumed or declared complete. K/L/N/G have runtime
files absent/different from the M-derived checkout despite cumulative roadmap notes.
Thread activity cannot be observed from Git. Existing STEP2/B3 failures and all
Redmi gates remain unchanged. Other package files and runtime usability are not certified.

## Reproduction

From the repository root:

```bash
python v13/code/scripts/branch_content_audit_candidate.py --repo . --plan v13/code/docs/proofs/continuation-20261013/branch-content-audit/plan.json --output /tmp/v13-branch-content-audit.json
```

Exit 1 means audit issues such as HEAD mismatch, moved refs, missing required source
files or scoped dirt. A clean comparison can still report differences/missing files
relative to an owner's source; those are informative comparisons, not utility failures.
The audit does not fetch and disables Git lazy fetch and optional index locks.

Validation: 7/7 unittest tests in real temporary repositories. Tests exercise missing
source requirements, conflicting declared owners, changed/staged/untracked worktree
files, moved refs preserving original source pins, wrong tree pins, path traversal,
repeated byte-identical JSON output and unchanged repository status after audit.
Only software/read-only Git evidence; no model or Redmi run.
