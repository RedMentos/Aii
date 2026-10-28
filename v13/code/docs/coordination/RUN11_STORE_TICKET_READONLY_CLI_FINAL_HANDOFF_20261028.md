# Run11 Store SHADOW ticket read-only operator CLI — verified handoff (2026-10-28)

**Owner / scope:** GPT review-only PR #941, branch `assistant/v13-run11-store-ticket-readonly-cli-20261028`, parent PR #939 exact `76b78dc0650b3284f975048d7e202a49f7732d8d`. Source/test proof at `f91efdb447e5edcae5cad29774c327386ea92bb3`. **Do not merge to main without independent review.** The new CLI is an optional standalone inspection command, not a live Runtime/Operator integration and not completion of the Canon.

## Implemented

- `scripts/run11_store_ticket_readonly_cli.py`: standalone `python3 -m scripts.run11_store_ticket_readonly_cli` using SQLite URI `mode=ro` and `PRAGMA query_only=ON`, with a minimal Store reader. It does **not** call the normal Store constructor, acquire its coordinator lock, migrate/recover data, invoke models, tools, learning or Runtime, or write application rows. It can inspect while the normal Store owns its lock. Existing source/user-message/generation/temporal revalidation and private ticket IO are reused.
- Emits only `SHADOW_ONLY`, `A|B|NONE`, and explicit false authority/native/learning flags; errors are generic `REFUSED`. Source text, source IDs, session, project and filesystem paths are not printed on the successful path. This is not an approved answer or a signed permission.
- `tests/test_run11_store_ticket_readonly_cli.py`: eight real SQLite/CLI tests for live lock, no Store constructor, query-only SQL, closed-store unchanged DB bytes, restart, revocation, wrong scope, corrupt/nonprivate ticket, missing home without creation, and subprocess output.

## Original raw evidence and durability

- Prereg first: `bcda87993fec717012b00492f55fcde63ef7a17f`.
- Test-only RED: Actions `40728049098` at `d7dd5a18fac5116120f423d5f32645d86050a658`, expected missing-module ImportError; 34 focused tests, one expected import error; FROZEN/COMPILE/PRIVACY/DIFF zero, full intentionally skipped. Original ZIP SHA256 `a82989231626cbf3a4d2d9ec0dc8ce03f816a9f381be5308304e1c9197869c2e`, CRC PASS, 15/15 inner hashes PASS.
- GREEN: Actions `40728106074` at source `f91efdb447e5edcae5cad29774c327386ea92bb3`: **41 focused PASS, 2556 full OK (1 skipped), 7/7 proof exits zero, privacy CLEAN**. Original ZIP SHA256 `a9b42f240b2d84a1c70492fac4e51930c6fc282b7b5c36ff39f7ab3b31036471`, CRC PASS, 15/15 inner hashes PASS.
- Both original ZIPs and independently audited parent PR #939 GREEN and Run32 original-raw quote aggregate GREEN are saved privately at `/V13-Checkpoints/2026-10-28/Run11-Store-Ticket-ReadOnly-CLI/`; each independently re-materialized and SHA256 byte-matched. **No private raw in public Git.**
- Parent #939 independent audit: Actions `40726099745`, 48 focused PASS, 2548 full OK (1 skipped), ZIP SHA256 `e4287986c3912cddb069a1db922a4f6db971e1d90d4fd50459184bd35d46d296`; CRC/15 inner PASS, privacy CLEAN.
- Independent Run32 #940 original-raw aggregate: Actions `40726753785`, ZIP SHA256 `a145edccb4bff190bd349358196de4378ea946ef289e288429a8b50b939ca077`; CRC/16 inner PASS, seven proof stages zero. B1 options present in both_exact, B2 rules absent, B2 verified quote count 0; `b2_only` has two quotes but no complete rules. This is one-fixture descriptive evidence, not causal proof.

## Reproduction / exact next command

```bash
git fetch origin assistant/v13-run11-store-ticket-readonly-cli-20261028
cd v13/code
PYTHONPATH=.:tests python3 -m unittest -v tests.test_run11_store_ticket_readonly_cli tests.test_run11_store_shadow_ticket_io tests.test_run11_store_shadow_use_boundary
python3 -m scripts.run11_store_ticket_readonly_cli --home <existing-V13-home> --session <original-session-id> --project <project-name> --directory <existing-private-0700-ticket-dir> --filename candidate.json
```

The CLI requires an already sealed private ticket from PR #939 and an existing Store; it does not create them. Source-only Linux CI is not an Android/Termux filesystem or native-model proof. SQLite WAL-mode read-only connections may coordinate through `-wal/-shm` files; do not claim zero OS-level filesystem activity (SQLite primary docs: https://www.sqlite.org/uri.html and https://www.sqlite.org/wal.html). The ordinary live Operator `:` command is not wired; user-facing end-to-end and telemetry remain open.

**Next independent high-priority work:** Review this source and parent #939 for post-return revocation and Android filesystem behavior before any Operator integration. In parallel, prioritize **fresh disjoint B2 quote-selection × C3 extraction controlled native experiment** following original Run32 aggregate: preserve frozen Keldara cohort, source/model/seed pins and failed raw, compare no-B2/B2-source-exact/B2-shuffled and single-body controls without oracle in prompts. Native exclusive owner and pinned installed artifacts are prerequisites; do not launch competing heavy jobs. Continue STEP2, B3, Body-JEPA, Context OS, Dream/Sleep and Redmi gates independently.

**All negative gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; canonical and user full scope incomplete. Remaining platform budget UNKNOWN.
