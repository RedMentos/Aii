"""A4 bounded acoustic salience for source-bound A3 audio observations.

Deterministic signal prioritization only, not speech, intent, risk or action
authorization. Unknown pitch/speech probabilities must not be interpreted.
"""
import math

def acoustic_salience(rms, zcr, *, duration_ms):
    """Return bounded salience and explicitly identified measurement provenance."""
    for name, value in (("rms", rms), ("zcr", zcr)):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("invalid " + name)
    if type(duration_ms) is not int or not 1 <= duration_ms <= 60000:
        raise ValueError("invalid duration")
    # Energy and change proxy; neither feature alone implies speech.
    score = min(1.0, max(0.0, 0.75 * rms + 0.25 * zcr))
    return {
        "schema": "v13.a4.acoustic.salience.v1",
        "score": score,
        "method": "bounded_rms_zcr_heuristic",
        "duration_ms": duration_ms,
        "evidence": {"rms": rms, "zero_crossing_rate": zcr},
        "unmeasured": ["pitch_hz", "speech_probability", "speaker_identity", "semantic_intent"],
        "learned": False,
        "authority": "observation_only",
    }
