"""Bounded RAW EAR -> canonical A5 PerceptPacket. Not Android microphone authorization."""
import math
import re
from .contracts import packet, validate

_SHA = re.compile(r"[0-9a-f]{64}\Z")


def audio_measurement_provenance(*, rms, zcr, voice_cues=None,
                                 speaker_evidence=None, speaker_decision=None,
                                 vad_expected=False, finality="FINAL"):
    """Describe RAW EAR measurement, heuristic and unavailable feature provenance.

    Sample-derived RMS/ZCR are measurements of the supplied PCM window.
    Pitch/activity/prosody remain uncalibrated estimates or rule scores, never
    calibrated probabilities. Speaker diagnostics do not establish identity.
    This metadata carries no learning, action or truth authority.
    """
    if any(type(value) not in (int, float) or not math.isfinite(float(value))
           for value in (rms, zcr)):
        raise ValueError("measurement provenance requires finite PCM features")
    if not 0.0 <= float(rms) <= 1.0 or not 0.0 <= float(zcr) <= 1.0:
        raise ValueError("measurement provenance PCM features are out of range")
    if type(vad_expected) is not bool or finality not in ("FINAL", "PROVISIONAL"):
        raise ValueError("measurement provenance state is invalid")
    if speaker_evidence is not None and type(speaker_evidence) is not dict:
        raise ValueError("measurement provenance speaker evidence is invalid")

    cues = voice_cues
    if cues is not None:
        required = {
            "method", "frame_count", "voiced_fraction", "voicing_confidence",
            "f0_median_hz", "f0_range_hz", "energy_range_db",
            "voiced_energy_range_db", "activity_hint", "activity_score",
            "prosody_change_score",
        }
        if (type(cues) is not dict or cues.get("method") != "RAW_EAR_AUTOCORR_V3"
                or not required.issubset(cues)):
            raise ValueError("measurement provenance voice cues are invalid")

    def entry(status, method, calibration_status, **extra):
        value = {"status": status, "method": method,
                 "calibration_status": calibration_status}
        value.update(extra)
        return value

    method = "RAW_EAR_AUTOCORR_V3"
    frame_count = 0 if cues is None else cues["frame_count"]
    voiced_count = 0 if cues is None else round(cues["voiced_fraction"] * cues["frame_count"])
    features = {
        "rms": entry("MEASURED_FROM_PCM16", "PCM16_WINDOW_RMS", "NO_SPL_CALIBRATION"),
        "zcr": entry("MEASURED_FROM_PCM16", "PCM16_ZERO_CROSSING_RATE", "NOT_APPLICABLE"),
        "f0_median_hz": entry(
            "HEURISTIC_ESTIMATE_UNCALIBRATED"
            if cues is not None and cues["f0_median_hz"] is not None
            else "UNAVAILABLE_NO_VALID_VOICED_FRAMES",
            method, "NOT_CALIBRATED",
            value_present=bool(cues is not None and cues["f0_median_hz"] is not None),
        ),
        "f0_range_hz": entry(
            "HEURISTIC_ESTIMATE_UNCALIBRATED"
            if cues is not None and cues["f0_range_hz"] is not None
            else "UNAVAILABLE_OR_INSUFFICIENT_FRAMES",
            method, "NOT_CALIBRATED",
            value_present=bool(cues is not None and cues["f0_range_hz"] is not None),
        ),
        "voiced_fraction": entry(
            "HEURISTIC_ESTIMATE_UNCALIBRATED" if frame_count else "UNAVAILABLE_NO_FRAMES",
            method, "NOT_CALIBRATED",
        ),
        "voicing_confidence": entry(
            "HEURISTIC_SCORE_NOT_PROBABILITY" if frame_count else "UNAVAILABLE_NO_FRAMES",
            method, "NOT_A_PROBABILITY",
        ),
        "energy_range_db": entry(
            "RELATIVE_PCM_LEVEL_NO_SPL_CALIBRATION"
            if cues is not None and cues["energy_range_db"] is not None
            else "UNAVAILABLE_NO_FRAMES",
            method, "NO_SPL_CALIBRATION",
        ),
        "voiced_energy_range_db": entry(
            "RELATIVE_LEVEL_OVER_HEURISTIC_VOICED_FRAMES"
            if cues is not None and cues["voiced_energy_range_db"] is not None
            else "UNAVAILABLE_NO_VOICED_FRAMES",
            method, "NO_SPL_CALIBRATION",
        ),
        "activity_hint": entry(
            "RULE_BASED_CLASS_NOT_PROBABILITY" if cues is not None else "NOT_PROVIDED",
            method, "NOT_A_PROBABILITY",
        ),
        "activity_score": entry(
            "RULE_BASED_SCORE_NOT_CALIBRATED" if cues is not None else "NOT_PROVIDED",
            method, "NOT_CALIBRATED",
        ),
        "prosody_change_score": entry(
            "HEURISTIC_SCORE_NOT_CALIBRATED" if voiced_count >= 2
            else "UNAVAILABLE_INSUFFICIENT_VOICED_FRAMES",
            method, "NOT_CALIBRATED",
        ),
        "vad": None,
        "speaker_identity": entry(
            "NOT_PRODUCED", "NO_SPEAKER_IDENTIFICATION", "NOT_APPLICABLE",
            authority=False,
        ),
        "speaker_timbre": entry(
            "NOT_PRODUCED", "NO_SPEAKER_TIMBRE_MODEL", "NOT_APPLICABLE",
            authority=False,
        ),
        "speaker_change": None,
        "calibrated_speech_probability": entry(
            "NOT_AVAILABLE", "NO_CALIBRATED_SPEECH_PROBABILITY", "NOT_CALIBRATED",
        ),
        "asr_transcript": entry(
            "NOT_IN_PACKET", "TEACHER_EAR_IS_SEPARATE_OPTIONAL_CHANNEL", "NOT_APPLICABLE",
        ),
    }

    vad = None if cues is None else cues.get("vad")
    if isinstance(vad, dict):
        features["vad"] = entry(
            "MODEL_SCORE_NOT_CALIBRATED", vad.get("method", "UNKNOWN_VAD"),
            "NOT_CALIBRATED",
            model_revision=vad.get("model_revision"),
            model_sha256=vad.get("model_sha256"),
            output_semantics="SCORES_AND_THRESHOLD_FLAG_NOT_CALIBRATED_PROBABILITY",
        )
    elif vad_expected and finality == "PROVISIONAL":
        features["vad"] = entry("NOT_ADVANCED_PROVISIONAL", "SILERO_VAD_ONNX", "NOT_APPLICABLE")
    elif vad_expected:
        features["vad"] = entry("NO_VAD_EVIDENCE", "SILERO_VAD_ONNX", "NOT_APPLICABLE")
    else:
        features["vad"] = entry("NOT_RUN", "OPTIONAL_VAD", "NOT_APPLICABLE")

    if speaker_evidence is None:
        features["speaker_change"] = entry(
            "NOT_PROVIDED", "OPTIONAL_CALLER_SUPPLIED_EMBEDDING_DIAGNOSTIC",
            "NOT_CALIBRATED", decision="DEFER", identity_authority=False,
        )
    else:
        receipt_sha = speaker_evidence.get("calibration_receipt_sha256")
        calibration_id = speaker_evidence.get("calibration_id")
        confidence_threshold = speaker_evidence.get("confidence_threshold")
        calibrated = (
            speaker_evidence.get("status") == "MEASURED"
            and speaker_evidence.get("threshold_status") == "CALIBRATED_VERIFIED"
            and type(receipt_sha) is str and len(receipt_sha) == 64
            and all(char in "0123456789abcdef" for char in receipt_sha)
            and type(calibration_id) is str and bool(calibration_id.strip())
            and type(confidence_threshold) in (int, float)
            and math.isfinite(float(confidence_threshold))
            and -1.0 <= float(confidence_threshold) <= 1.0
            and speaker_decision in {"CONTINUITY_SUPPORTED", "CHANGE_OR_OVERLAP_CANDIDATE"}
        )
        features["speaker_change"] = entry(
            "CALIBRATED_DIAGNOSTIC" if calibrated else "DIAGNOSTIC_ONLY_UNCALIBRATED",
            "OPTIONAL_CALLER_SUPPLIED_EMBEDDING_DIAGNOSTIC",
            "VERIFIED" if calibrated else "UNVERIFIED",
            decision=speaker_decision if speaker_decision in {
                "DEFER", "CONTINUITY_SUPPORTED", "CHANGE_OR_OVERLAP_CANDIDATE"
            } else "DEFER",
            identity_authority=False,
        )

    return {
        "schema": "v14.audio-measurement-provenance/1",
        "features": features,
        "authority": {
            "learning": False, "action": False, "truth": 0,
            "speaker_identity": False, "calibrated_speech_probability": False,
        },
    }



def audio_percept_packet(*, event_id, generation_id, source_id, source_sha256,
                         start_ms, end_ms, rms, zcr, finality="FINAL",
                         consent_receipt=None):
    """Build a non-authoritative acoustic packet; caller must verify OS permission.

    Consent receipt is an opaque local reference, not proof of OS permission.
    Recheck source revocation when a downstream consumer reads this packet.
    """
    if not all(isinstance(x, str) and x for x in (event_id, generation_id, source_id)):
        raise ValueError("missing event/generation/source identity")
    if not isinstance(source_sha256, str) or not _SHA.fullmatch(source_sha256):
        raise ValueError("invalid source hash")
    if not isinstance(consent_receipt, str) or not consent_receipt.strip():
        raise PermissionError("local authorized input receipt required")
    if finality not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid finality")
    if any(type(x) is not int for x in (start_ms, end_ms)) or not 0 <= start_ms < end_ms or end_ms-start_ms > 1000:
        raise ValueError("invalid bounded audio interval")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in (rms, zcr)):
        raise ValueError("nonfinite acoustic feature")
    if not 0 <= rms <= 1 or not 0 <= zcr <= 1:
        raise ValueError("feature outside normalized range")
    source_ref = {"source_id":source_id,"sha256":source_sha256,
                  "char_start":0,"char_end":0,"modality":"audio"}
    validate("SourceRef", packet("SourceRef", "A_RAW_EAR", event_id, generation_id, **source_ref))
    segment = {"start_ms":start_ms,"end_ms":end_ms,"finality":finality,
               "acoustic":{"rms":float(rms),"zcr":float(zcr)},
               "unmeasured":["pitch","speaker","speech_probability","prosody"],
               "measurement_provenance":audio_measurement_provenance(rms=rms,zcr=zcr,finality=finality),
               "asr_transcript":None,"learning_authority":False,
               "action_authority":False,"consent_receipt_ref":consent_receipt}
    return packet("PerceptPacket", "A5_AUDIO", event_id, generation_id,
                  provenance=[source_ref], source_ref=source_ref,
                  segments=[segment], modality="audio")
