# V13 Boss integration handoff — 2026-11-11 05:45 Europe/Berlin

## Purpose and verified baseline

Based on integration PR #1716 head `ebf32205d91d0b1f2cdb097b193d72a0cd023f76` (`codex/v13-integrated-continuation-20261110`), NOT stale main. Read root and v13 AGENTS.md, Canon v10.16.1, v13/ROADMAP.md, v13/NUTZER_ENTSCHEIDUNGEN.md, code/BUILD_STATE.json and code/docs/HANDOFF_CURRENT.md. Reviewed current #1731–#1735 specialist PRs; none is implicitly merged into this branch.

## Concrete implementation

`scripts/stage_integrated_candidate.py` now materializes the existing hash-pinned feedback/memory/C3/Body/World composite into a separate destination with one CLI command:

```bash
cd v13/code
python scripts/stage_integrated_candidate.py --output /tmp/v13-integrated-review
python -m unittest -v tests.test_stage_integrated_candidate
```

The original runtime and model files are never overwritten; the stage is published only after the builder validates all source pins and files are written. Existing destination fails closed. A manifest marks SHADOW_REVIEW_ONLY. The stage itself does NOT automatically enable learning, download models, or run a native backend. It is a runnable staging tool, NOT an integrated live runtime proof.

Three synthetic unit tests passed in a local isolated copy before publication (staging, pin mismatch, traversal). **Exact GitHub-head CI and the real builder execution remain UNVERIFIED** due to unavailable local GitHub checkout/DNS; no production promotion.

## Completion ledger (strict claims)

| Organ/path | Code | Wired in disposable composite | Integrated runtime E2E | Redmi |
|---|---|---|---|---|
| A0–A5 perception / A3 | candidate, checkpoint audit | partial | OFF/UNVERIFIED | UNVERIFIED |
| B1/B2 body + body JEPA | tiny Torch/PEFT candidate | test copy | native runtime trainer route not proven | UNVERIFIED |
| C2/JEF + C3 | native route and C3 adapter candidates | partial / synthetic | no whole-chain proof | UNVERIFIED |
| T8 episodic memory / source lifecycle | yes | yes in test copy | bounded normal retrieval still missing | UNVERIFIED |
| World predictor / World-JEPA EMA | partial | test copy | full real-world JEPA utility unproven | UNVERIFIED |
| Rollback/restart | multiple scoped tests | partial | no single release-wide transaction | UNVERIFIED |
| Operator PC harness | permission designs | partial | not active | UNVERIFIED |

## Highest-impact next integration slice and non-overlap

1. **Boss**: execute staged composite with exact source pins, add one genuine interactive synthetic turn spanning C3, T8, retrieved archived context and output; record failing baseline before repair. Do not count the staging tool as that test.
2. **Core**: wire regular Runtime B1/B2/C3/JEF response path to bounded retrieved ContextOS spans; keep human permission gating for tools.
3. **JEPA**: make trusted T8 -> bounded World/Body predictor update -> checkpoint/restart -> disjoint holdout an explicitly authorized callable path, not just a disposable test.
4. **QA**: run combined regression on exact integrated SHA and repair blockers in QA-owned tests; real Redmi measurements remain separate.
5. **Perception**: deliver A0–A5 PerceptPacket consumed by regular Runtime, not merely A3 checkpoint auditing.

No merge, gate promotion, AGI claim, or Redmi claim. Canon remains fully binding; security, provenance, retention and rollback remain release conditions.

## Concurrent PRs discovered during final recheck

- [#1736](https://github.com/RedMentos/Aii/pull/1736): Research already proposes an opt-in A5 PerceptPacket→B1/B2 source-view route; candidate-only and no native inference. Boss must REVIEW/INTEGRATE it, not assign Research a duplicate from scratch.
- [#1737](https://github.com/RedMentos/Aii/pull/1737): JEPA already proposes actual Runtime→T8→WorldJEPA update→holdout→restart readback; tests pending. Boss must pin and execute this chain rather than reimplement its tests.

Both arrived after the base integration commit; neither is included in #1738. The next Boss E2E slice should integrate #1736/#1737 only after exact-head tests and cross-owner contract checks.
