# Run41 preregistration — JEF/C2 balanced heldout negative control

Committed BEFORE any Run41 evaluation. Parent PR #76 95a4f3d0072c530d543c71452f2c1fe3a7022173, Run40 original preregistered FAIL_SYNTHETIC remains immutable and negative. No retuning of Run40 threshold, architecture, optimizer, labels, train data or trained candidate.

Reuse exact Run40 source Git blob b8fcddbc1233e29fad756098af00c68439867cfd and its fixed 512 training rows, 200 updates, seed 20261024, same initial weights and shuffled-label control. Build a new evaluation set with exactly 32 examples per each of the four routes, total 128, by seeded sampling with replacement (seed 20261025) from the full enumerated 64 binary six-feature states. Shuffle evaluation order deterministically. This is class-balanced synthetic evaluation, NOT independent novel states and NOT real user traffic.

PASS_SYNTHETIC_ONLY iff candidate balanced route accuracy >=0.95, report Brier <=0.10, wrong-target balanced route accuracy <=0.40, candidate-minus-wrong route accuracy >=0.40, exactly 32 cases per class, hard missing-source/conflict/pressure report gates hold, and no Age/action/production authority. Report majority baseline 0.25. Retain all failures. No promotion of original Run40 FAIL or any V13 native/Redmi gate.
