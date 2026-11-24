# STEP2 complementary utility proof

The canonical `G-B-TIMESCALE-DIVERGENCE-001` remains the target. The previous two-case number-presence diagnostic is retained. Its lexical coverage does not demonstrate correct budget assignment, constraints, or complementary utility.

`tests/integration_step2_utility.py` adds ten fixed source-grounded episodes before inference. Six require retaining earlier rules across an unrelated event and restart; four explicitly replace conflicting earlier rules in the latest source. A missing-budget episode requires UNKNOWN rather than fabricated budget/eligibility. The choice oracle uses exact entity, cost, remaining budget, duration, locality, eligibility and selected action. Negative constraints and wrong entity assignment lose credit. Typed equality rejects booleans masquerading as numbers. No generated judge or keyword matching scores an answer.

Seven paired variants share each genuinely generated initial observer state: B1 alone; B2 alone; both with NONE, EXACT or CONTROL; two independent native B1 calls reset to identical earlier state; B1/B2 prompt-only control with B2 retained-source context disabled. Every final consumer is the same native C3 model with the same JSON schema, system instruction, seed and settings. Oracles are never passed to any model. The earlier source reaches C3 only through verified observer quotes and fallible observer hypotheses. Full prior messages or answer caches are not passed directly to C3.

The proof invokes the existing Cognition.offer/communicate/focal observer interfaces, with `probe_only` state version zero, and persists native final text in the existing Store. It is an observer utility experiment, not a proof of every C1/C5/runtime-turn executive or latency path. The original full runtime ablation and vertical proof remain necessary.

Each variant opens an isolated copy of a closed real pre-observation store and checks exact persisted B1/B2 state equality after reopening. Actual sources are re-read for provenance. Model revisions, hashes, state, observer metrics, raw C3 output, exact score, generation, integrity and process release results are recorded incrementally. Failed inference is zero utility and is retained in the fixed paired denominator.

The preregistered primary combination is both EXACT. Scoped utility passes only with complete ten-episode pairing, all structural checks, an episode won by each solo body, and primary mean utility strictly above both solos, the identical-policy control and the prompt-only control. A diagnostic `--fixtures` subset cannot pass this gate. There is no automatic architecture gate promotion.

The currently installed two roles use the same dense GGUF weight file with separate state/prompt policies and sequential execution. This exercises the Canon-permitted shared-body dual-timescale realization. A physical shared-native-process comparison and genuine distinct-weight body comparison are not synthesized. The full Canon timescale gate remains false pending those controls and larger stability/OOD evidence. This proof does not introduce native sparse training, latent receiver authority, or trainable body weights.

Run, after native installation and with exclusive inference ownership:

```bash
python3 tests/integration_step2_utility.py --installed-home "$V13_HOME" --out step2-semantic-utility.json
```

Exit 0 means only UTILITY_PASS_SCOPED. Exit 2 preserves a failed utility gate or incomplete diagnostic. The first fixed corpus should be retained as test data; any later revised corpus must receive a new proof identity rather than overwrite this evidence.

The collector retains the current genuine pre-observation store beside the JSON in a `.checkpoint` directory until its seven paired variants are recorded. `--resume` checks source/config/corpus/variants/device descriptor, completed raw-row hashes, checkpoint file hashes and installed native model hashes; it then runs only unrecorded variants. It preserves interrupted stores separately. Device descriptor equality cannot prove physical device identity when no stable identity port is available. A source change intentionally requires a new proof; earlier native results remain evidence for their own source revision. Twelve unit checks cover strict score failure cases, temporal corpus composition and refused resume mutations.

For the frozen current source, collect one diagnostic episode and retain its report before extending the exact same proof to all 70 rows:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tests/integration_step2_utility.py --installed-home /workspace/scratch/7d5ad9273a5e/native --out docs/proofs/step2-semantic-utility-native-20261007.json --fixtures 1 > docs/proofs/step2-semantic-utility-diagnostic-20261007.log 2>&1
```

The diagnostic deliberately exits 2 with DIAGNOSTIC_INCOMPLETE; inspect the seven raw rows and errors. Preserve its original JSON:

```bash
cp docs/proofs/step2-semantic-utility-native-20261007.json docs/proofs/step2-semantic-utility-diagnostic-20261007.json
```

Then, without changing source, settings, corpus or native artifacts:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tests/integration_step2_utility.py --installed-home /workspace/scratch/7d5ad9273a5e/native --out docs/proofs/step2-semantic-utility-native-20261007.json --resume > docs/proofs/step2-semantic-utility-native-20261007.log 2>&1
```

This keeps the original seven native rows and runs the other 63. A recorded ERROR remains a zero-score observation; --resume does not silently retry failed completed rows. Partial preparations and failed variant stores remain next to the proof. Global model/runner identities are checked even when the completed diagnostic's initial checkpoint was already removed. A failed utility result exits 2 and still provides complete measured evidence. Run only after exclusive native inference ownership is granted.
