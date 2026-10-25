# Run375 — B3 Callosum human ratings and channel softmax must be finite (preregistered)

Parent: Run374/PR369 checkpoint `11a4eb18220d64f7b6ac1c546de0ee854b33ebf4` (review chain, not main). Independent of Run373 pinned native C3 owner and B3 latent/native gates.

Owned: `v13/code/v13/callosum.py`, new `v13/code/tests/test_callosum_finite_rating_run375.py`, isolated `.github/workflows/run375-callosum-finite-rating.yml`, this proof directory. No changes to B3 channel ladder, model/seed hashes, Age, calibration, training, permissions or latent availability.

Observed hazard: `Callosum.on_rating` uses `max(0., min(1., float(utility)))`. Python NaN can silently clamp to **1.0** depending on operand order, making a malformed rating appear maximally positive; +/-Infinity and booleans also coerce. `Callosum.probabilities` softmax accepts nonfinite/corrupted utility values and may produce NaN probabilities. Both can poison B3-H9 learned channel selection or reports.

RED-first actual SQLite/Store tests: NaN, +/-Inf, bool, numeric strings, None ratings must raise ValueError with no utility update; valid finite human rating still updates the selected channel, and finite out-of-range ratings retain existing 0..1 clamping. Crafted corrupted utility state must fail closed in `probabilities` instead of returning nonfinite probabilities; valid softmax remains normalized with positive floor and LATENT=0.

GREEN: exact numeric int/float (excluding bool) and `math.isfinite` at human rating entry; validate each channel utility finite before softmax. Raise ValueError rather than silently promoting invalid evidence. Preserve original B3-H9 floor, channel names, SHADOW default, and all latent negative gates. This does not establish real B3 utility/calibration or permit ACTIVE without explicit human authority.

Evidence: source-bound RED/GREEN Actions with inherited Callosum tests, compileall/privacy, closed raw receipts and private Library byte comparison. Do not promote STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole V13.
