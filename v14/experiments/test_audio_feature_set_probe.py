import hashlib
import math
import random
import struct
import sys
import unittest
from pathlib import Path

from audio_feature_set_probe import (
    evaluate_feature_set, evaluate_relative_incremental_information,
    feature_values_from_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CODE_ROOT = REPO_ROOT / "v13" / "code"
A4_AVAILABLE = CODE_ROOT.is_dir()
if A4_AVAILABLE:
    sys.path.insert(0, str(CODE_ROOT))
    from v13.audio_ear import observe_pcm16
    from v13.audio_percept_contract import audio_percept_packet
    from v13.audio_voice_cues import extract_voice_cues


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pcm(pitch_bit, prosody_bit, index, sample_rate=16000, duration_ms=200):
    count = sample_rate * duration_ms // 1000
    frequency = 300 if pitch_bit else 140
    phase = index * 0.0137
    samples = []
    for i in range(count):
        if prosody_bit:
            amplitude = 2000 if i < count // 2 else 10000
        else:
            amplitude = 6000
        samples.append(int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate + phase)))
    return struct.pack("<" + "h" * count, *samples)


def _manual_packet(index, pitch_bit, prosody_bit, activity="VOICED", pitch_override=None):
    pitch = pitch_override if pitch_override is not None else (300.0 if pitch_bit else 140.0)
    score = 0.8 if prosody_bit else 0.1
    if activity == "UNVOICED_NOISE":
        pitch, score = None, 0.0
    source = {
        "source_id": "synthetic-mic",
        "sha256": _sha(f"pcm:{index}:{pitch_bit}:{prosody_bit}:{activity}"),
        "char_start": 0,
        "char_end": 0,
        "modality": "audio",
    }
    start, end = index * 220, index * 220 + 200
    return {
        "schema_version": "1.0",
        "packet_id": f"packet-{index}",
        "producer_component": "A5_AUDIO",
        "producer_version": "0.1.0",
        "event_id": f"event-{index}",
        "created_monotonic_ns": index + 1,
        "created_wall_time": 1700000000.0 + index,
        "brain_generation_id": "generation-fixture",
        "provenance": [source],
        "source_ref": source,
        "segments": [{
            "start_ms": start,
            "end_ms": end,
            "finality": "FINAL",
            "acoustic": {
                "rms": 0.2,
                "zcr": 0.1,
                "voice_cues": {
                    "method": "RAW_EAR_AUTOCORR_V3",
                    "f0_median_hz": pitch,
                    "prosody_change_score": score,
                    "activity_hint": activity,
                },
            },
            "unmeasured": ["speaker_identity", "ASR"],
            "asr_transcript": None,
            "learning_authority": False,
            "action_authority": False,
            "consent_receipt_ref": f"synthetic-consent-{index}",
        }],
        "modality": "audio",
    }


def _build_packet(index, pitch_bit, prosody_bit):
    if not A4_AVAILABLE:
        return _manual_packet(index, pitch_bit, prosody_bit)
    sample_rate = 16000
    pcm = _pcm(pitch_bit, prosody_bit, index, sample_rate=sample_rate)
    start_ms = index * 220
    raw = observe_pcm16(
        pcm, sample_rate, start_ms, consent=True, source_id="fixture:audio-feature-set"
    )
    cues = extract_voice_cues(pcm, sample_rate)
    if cues["activity_hint"] != "VOICED" or cues["f0_median_hz"] is None:
        raise AssertionError(f"synthetic voiced fixture was not measured: {cues}")
    expected_pitch = "HIGH" if pitch_bit else "LOW"
    actual_pitch = "HIGH" if cues["f0_median_hz"] >= 220.0 else "LOW"
    if actual_pitch != expected_pitch:
        raise AssertionError(f"pitch-band fixture mismatch: {cues}")
    if (cues["prosody_change_score"] >= 0.5) != bool(prosody_bit):
        raise AssertionError(f"prosody-band fixture mismatch: {cues}")
    segment = raw["segments"][0]
    packet = audio_percept_packet(
        event_id=f"event-{index}",
        generation_id="generation-fixture",
        source_id="fixture:audio-feature-set",
        source_sha256=raw["source_ref"]["sha256"],
        start_ms=segment["start_ms"],
        end_ms=segment["end_ms"],
        rms=segment["acoustic"]["rms"],
        zcr=segment["acoustic"]["zero_crossing_rate"],
        finality="FINAL",
        consent_receipt=f"synthetic-fixture-only-{index}",
    )
    packet["segments"][0]["acoustic"]["voice_cues"] = cues
    packet["segments"][0]["unmeasured"] = [
        "speaker_identity", "speaker_timbre", "calibrated_speech_probability", "ASR"
    ]
    return packet


def _records(count=64, seed=11):
    if count % 4 or count < 32:
        raise ValueError("fixture count must be divisible by four and at least 32")
    rng = random.Random(seed)
    combinations = [(0, 0), (0, 1), (1, 0), (1, 1)]
    per_goal = count // 2
    goal_sequences = {}
    for goal_bit in (0, 1):
        sequence = combinations * (per_goal // len(combinations))
        sequence += combinations[: per_goal % len(combinations)]
        rng.shuffle(sequence)
        goal_sequences[goal_bit] = sequence

    records = []
    for index in range(count):
        goal_bit = index % 2
        pitch_bit, prosody_bit = goal_sequences[goal_bit][index // 2]
        action_bit = pitch_bit ^ prosody_bit ^ goal_bit
        action = "INTERRUPT" if action_bit else "CONTINUE"
        packet = _build_packet(index, pitch_bit, prosody_bit)
        end_ms = packet["segments"][0]["end_ms"]
        outcome_source = {
            "source_id": f"world-outcome-{index}",
            "sha256": _sha(f"outcome:{index}:{goal_bit}:{action}"),
            "char_start": 0,
            "char_end": 0,
            "modality": "world/action-outcome",
        }
        records.append({
            "evidence_class": "SYNTHETIC_FIXTURE",
            "session_id": f"session-{index // max(1, count // 4)}",
            "packet": packet,
            "outcome": {
                "goal_id": "goal-follow" if goal_bit else "goal-turn-taking",
                "action_id": f"action-{index}",
                "action_type": action,
                "observed_at_ms": end_ms + 20,
                "source_ref": outcome_source,
                "learning_authority": False,
                "action_authority": False,
            },
        })
    return records


class AudioFeatureSetProbeTests(unittest.TestCase):
    def test_goal_conditioned_joint_features_capture_synergy(self):
        result = evaluate_feature_set(_records())
        self.assertAlmostEqual(result["feature_set_goal_action_cmi_bits"], 1.0, delta=1e-9)
        self.assertLess(result["single_feature_goal_action_cmi_bits"]["pitch_band"], 1e-9)
        self.assertLess(result["single_feature_goal_action_cmi_bits"]["prosody_band"], 1e-9)
        self.assertGreater(result["joint_gain_over_best_single_bits"], 0.999999)
        self.assertLess(result["goal_only_action_mi_bits"], 1e-9)

    def test_shuffled_time_permutation_control_breaks_pairing(self):
        result = evaluate_feature_set(_records(), seed=17, permutations=64)
        self.assertLess(result["shuffled_time_cmi_p95_bits"], 0.35)
        self.assertLessEqual(result["permutation_p_value"], 0.05)
        self.assertGreater(result["feature_set_goal_action_cmi_bits"],
                           result["shuffled_time_cmi_p95_bits"] + 0.5)

    def test_individually_weak_self_prediction_can_coexist_with_joint_goal_value(self):
        result = evaluate_feature_set(_records())
        self.assertLess(result["feature_self_predictive_mi_bits"]["pitch_band"], 0.2)
        self.assertLess(result["feature_self_predictive_mi_bits"]["prosody_band"], 0.2)
        self.assertGreater(result["feature_set_goal_action_cmi_bits"], 0.9)

    def test_non_speech_activity_is_retained_as_its_own_feature(self):
        values = feature_values_from_packet(
            _manual_packet(0, 0, 0, activity="UNVOICED_NOISE")
        )
        self.assertEqual(values["activity_hint"], "UNVOICED_NOISE")
        self.assertEqual(values["pitch_band"], "NO_PITCH")

    def test_provisional_audio_is_not_promoted_into_predictive_cohort(self):
        packet = _manual_packet(0, 0, 0)
        packet["segments"][0]["finality"] = "PROVISIONAL"
        with self.assertRaisesRegex(ValueError, "FINAL audio evidence"):
            feature_values_from_packet(packet)

    def test_source_and_outcome_must_be_separately_bound(self):
        records = _records()
        records[0]["outcome"]["source_ref"] = records[0]["packet"]["source_ref"]
        with self.assertRaisesRegex(ValueError, "separate source binding"):
            evaluate_feature_set(records)

    def test_wrong_generation_or_duplicate_source_fails_closed(self):
        records = _records()
        records[1]["packet"]["brain_generation_id"] = "generation-other"
        with self.assertRaisesRegex(ValueError, "cross brain generations"):
            evaluate_feature_set(records)
        records = _records()
        records[1]["packet"]["source_ref"]["sha256"] = records[0]["packet"]["source_ref"]["sha256"]
        records[1]["packet"]["provenance"] = [records[1]["packet"]["source_ref"]]
        with self.assertRaisesRegex(ValueError, "duplicate source/event/action"):
            evaluate_feature_set(records)

    def test_authority_and_raw_pcm_are_rejected(self):
        records = _records()
        records[0]["packet"]["segments"][0]["action_authority"] = True
        with self.assertRaisesRegex(PermissionError, "cannot grant learning or action"):
            evaluate_feature_set(records)
        packet = _manual_packet(0, 0, 0)
        packet["pcm"] = b"secret"
        with self.assertRaisesRegex(ValueError, "raw PCM"):
            feature_values_from_packet(packet)

    def test_action_outcome_must_follow_audio_interval(self):
        records = _records()
        records[0]["outcome"]["observed_at_ms"] = records[0]["packet"]["segments"][0]["end_ms"] - 1
        with self.assertRaisesRegex(ValueError, "occur after its audio source"):
            evaluate_feature_set(records)

    def test_actual_a4_extractor_maps_all_four_feature_combinations(self):
        if not A4_AVAILABLE:
            self.skipTest("full Aii checkout is not mounted in this scratch run")
        for pitch_bit, prosody_bit in ((0, 0), (0, 1), (1, 0), (1, 1)):
            packet = _build_packet(100 + pitch_bit * 2 + prosody_bit, pitch_bit, prosody_bit)
            values = feature_values_from_packet(packet)
            self.assertEqual(values["pitch_band"], "HIGH" if pitch_bit else "LOW")
            self.assertEqual(values["prosody_band"], "HIGH" if prosody_bit else "LOW")
            self.assertEqual(values["activity_hint"], "VOICED")


    def test_relative_incremental_information_uses_session_local_history(self):
        result = evaluate_relative_incremental_information(
            _records(128), seed=17, permutations=128,
        )
        self.assertEqual(result["session_count"], 4)
        self.assertEqual(result["minimum_records_per_session"], 32)
        self.assertTrue(result["session_history_reset_verified"])
        self.assertFalse(result["history_crosses_sessions"])
        self.assertEqual(result["history_window_ms"], 5000)
        self.assertGreater(result["history_nonempty_fraction"], 0.9)
        self.assertGreater(result["rimi_proxy"], 0.99)
        self.assertLessEqual(result["permutation_p_value"], 0.05)
        self.assertTrue(all(item["rimi_proxy"] > 0.99 for item in result["per_session"]))
        self.assertFalse(result["paper_exact_rimi"])
        self.assertFalse(result["runtime_integrated"])

    def test_relative_incremental_information_rejects_missing_or_single_session(self):
        records = _records(64)
        for record in records:
            record.pop("session_id")
        with self.assertRaisesRegex(ValueError, "session identity is missing"):
            evaluate_relative_incremental_information(records)

        records = _records(64)
        for record in records:
            record["session_id"] = "one-session"
        with self.assertRaisesRegex(ValueError, "at least two sessions"):
            evaluate_relative_incremental_information(records)

    def test_relative_incremental_information_rejects_nonmonotonic_session_time(self):
        records = _records(64)
        records[1]["packet"]["segments"][0]["start_ms"] = (
            records[0]["packet"]["segments"][0]["start_ms"]
        )
        with self.assertRaisesRegex(ValueError, "session audio windows must advance monotonically"):
            evaluate_relative_incremental_information(records)

    def test_relative_incremental_information_rejects_invalid_window_and_bool_permutations(self):
        records = _records(64)
        with self.assertRaisesRegex(ValueError, "history window"):
            evaluate_relative_incremental_information(records, history_window_ms=0)
        with self.assertRaisesRegex(ValueError, "permutations"):
            evaluate_relative_incremental_information(records, permutations=True)


if __name__ == "__main__":
    unittest.main()
