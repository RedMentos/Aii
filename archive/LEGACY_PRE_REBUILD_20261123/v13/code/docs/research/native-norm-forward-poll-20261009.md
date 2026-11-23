# Isolated native norm: bounded forward-only optimization

The previous isolated experiment retains valid FP32 master, native decode,
independent dequantized gradient, restart and rollback evidence. Its four
surrogate-SGD candidates worsened the deployed quantized full-vocabulary CE.
Those outcomes remain preserved. A dequantized analytic gradient is not an
exact derivative through the deployment activation quantizer.

`scripts/test_native_norm_shadow.py --forward-poll` adds a separate optimizer
that chooses by actual quantized forward evaluations. Before inference, the
collector saves its exact source and policy hashes, fixtures, numerical caps,
directions, radii and maximum evaluations. The unchanged original four
surrogate trials and all analytic/reference/finite-difference fields still run.

The fixed poll uses the unit surrogate direction and coordinates 0, 341, 682,
1023, each with both signs at radius .001 and .0005: at most 20 evaluations.
The surrogate is one proposed direction, not a claimed exact derivative.
All resulting FP32 master updates must remain within the existing .0010001
rounding allowance. Radius/direction adaptation and repeated training epochs
are absent. Every poll observation retains its actual measured quantized CE,
native logits hash, candidate master values/hash, execution status and timing.

A proposed best master must improve the actual full native prefill CE against
the actual full native baseline, while native-tail logits agree with the full
prefill within the unchanged 1e-5 tolerance. The fresh process then reloads
the exact candidate checkpoint and verifies exact logits and original rollback,
source bindings, frozen tied output and unchanged original GGUF. A failed poll
does not erase failed surrogate candidates or become an approved update.

```sh
python3 scripts/test_native_norm_shadow.py \
  --installed-home "$V13_HOME" --forward-poll --fixtures 2 --seconds 120 \
  --out-dir "$V13_HOME/exports/native-norm-forward-poll-fresh"
```

This optimizes one authored numerical target, not human-label training or
semantic/generalization/retention performance. The actual evaluator currently
uses the existing native tail graph, which also computes its surrogate backward
observations; the optimizer's selection criterion uses only actual forward CE.
The exact quantized-gradient gate, human approval, production import authority,
phone learning gate and sparse expert claims remain false/zero. The dense C3
final-norm FP32 master is the only mutable tensor in a disposable worker.

The shared compiled policy test uses an expressly authored staircase objective
to verify deterministic directions, bounded updates, evaluation count, strict
improvement and refusal of zero/equal/worse/nonfinite/oversized candidates.
That software test supplies no native model proof. Native measurements are
separately recorded under `docs/proofs/native-norm-forward-poll-actual-20261009`.

The authorized actual run completed without retuning. On the short 28-token
fixture, two of 20 poll candidates improved measured CE, and 18 were refused.
The selected dense C3 norm master changed 1005 FP32 coordinates. Actual full
native CE changed from 2.1504847459711165 to 2.150208647341106; its tail/full
prefill logits difference was exactly zero. On the long 268-token fixture,
all 20 poll candidates were refused: the minimum CE equalled the unchanged
baseline 2.234306991419235. All four original surrogate-SGD candidates failed
on each fixture. Both numerical reload/rollback suites passed; all four
workers were reaped and the original GGUF remained unchanged.

`NUMERICAL_UPDATE_RELOAD_SCOPE_PASS` describes lifecycle/numerical checks;
it does not mean that both optimization cases improved. This measured native
C3 dense final-norm update is not B1/B2 body training or sparse expert training.
