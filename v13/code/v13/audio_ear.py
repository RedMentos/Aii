"""Consent-bound, transcript-independent PCM16 A-plane acoustic observations.

No microphone access, persistence, speaker identity inference, or native-model claim.
The caller owns audio capture and must supply explicit permission and a source digest.
Voice cues are deterministic heuristics, not a trained VAD or speaker recognizer.
"""
import math
import struct
from hashlib import sha256
from statistics import median


def _estimate_pitch(frame, sample_rate):
    """Cheap normalized-autocorrelation F0 estimate over a 65..400 Hz range."""
    minimum_lag = max(2, int(sample_rate / 400))
    maximum_lag = min(len(frame) // 2, int(sample_rate / 65))
    correlations = []
    for lag in range(minimum_lag, maximum_lag + 1):
        left = frame[:-lag]
        right = frame[lag:]
        left_energy = sum(value * value for value in left)
        right_energy = sum(value * value for value in right)
        denominator = math.sqrt(left_energy * right_energy)
        if denominator <= 1e-9:
            continue
        correlation = sum(a * b for a, b in zip(left, right)) / denominator
        correlations.append((correlation, lag))
    if not correlations:
        return None, 0.0
    peak = max(item[0] for item in correlations)
    threshold = max(0.55, peak * 0.90)
    candidates = [(lag, corr) for corr, lag in correlations if corr >= threshold]
    if not candidates:
        return None, max(0.0, min(1.0, peak))
    # Select the first strong periodic peak to avoid choosing a multiple period.
    lag, confidence = min(candidates, key=lambda item: item[0])
    return sample_rate / lag, max(0.0, min(1.0, confidence))


def _voice_cues(samples, sample_rate, overall_rms, overall_peak):
    """Summarize 40 ms frames at 20 ms hops; never identifies a person."""
    factor = max(1, int(round(sample_rate / 8000.0)))
    usable = (len(samples) // factor) * factor
    if usable < factor:
        low_rate_samples = []
    else:
        low_rate_samples = [
            sum(samples[index:index + factor]) / factor
            for index in range(0, usable, factor)
        ]
    effective_rate = sample_rate / factor
    frame_ms, hop_ms = 40, 20
    frame_size = max(32, int(round(effective_rate * frame_ms / 1000.0)))
    hop_size = max(1, int(round(effective_rate * hop_ms / 1000.0)))
    frame_rms = []
    pitches = []
    voicing_scores = []
    for start in range(0, max(0, len(low_rate_samples) - frame_size + 1), hop_size):
        raw_frame = low_rate_samples[start:start + frame_size]
        if len(raw_frame) != frame_size:
            continue
        mean = sum(raw_frame) / frame_size
        frame = [value - mean for value in raw_frame]
        rms = math.sqrt(sum(value * value for value in frame) / frame_size) / 32768.0
        frame_rms.append(rms)
        if rms < 0.002:
            continue
        pitch, confidence = _estimate_pitch(frame, effective_rate)
        if pitch is not None and confidence >= 0.55:
            pitches.append(pitch)
            voicing_scores.append(confidence)

    voiced_fraction = len(pitches) / len(frame_rms) if frame_rms else 0.0
    voicing_confidence = median(voicing_scores) if voicing_scores else 0.0
    f0_median = median(pitches) if pitches else None
    f0_range = (max(pitches) - min(pitches)) if len(pitches) >= 2 else None
    if frame_rms:
        low = max(min(frame_rms), 1e-6)
        energy_range_db = min(120.0, max(0.0, 20.0 * math.log10(max(frame_rms) / low)))
    else:
        energy_range_db = 0.0
    crest = overall_peak / max(overall_rms, 1e-6)

    if overall_rms < 0.003:
        activity_hint = "SILENCE"
        activity_score = max(0.0, min(1.0, 1.0 - overall_rms / 0.003))
    elif voiced_fraction >= 0.25 and voicing_confidence >= 0.55:
        activity_hint = "VOICED"
        activity_score = min(1.0, 0.5 * voiced_fraction + 0.5 * voicing_confidence)
    elif crest >= 8.0 and voiced_fraction < 0.15:
        activity_hint = "IMPULSIVE"
        activity_score = min(1.0, crest / 16.0)
    elif overall_rms >= 0.01 and voiced_fraction < 0.15:
        activity_hint = "UNVOICED_NOISE"
        activity_score = min(1.0, overall_rms / 0.08)
    else:
        activity_hint = "UNCERTAIN"
        activity_score = 0.25

    return {
        "method": "RAW_EAR_AUTOCORR_V1",
        "frame_ms": frame_ms,
        "hop_ms": hop_ms,
        "frame_count": len(frame_rms),
        "voiced_fraction": round(voiced_fraction, 6),
        "voicing_confidence": round(voicing_confidence, 6),
        "f0_median_hz": round(f0_median, 2) if f0_median is not None else None,
        "f0_range_hz": round(f0_range, 2) if f0_range is not None else None,
        "energy_range_db": round(energy_range_db, 2),
        "activity_hint": activity_hint,
        "activity_score": round(activity_score, 6),
    }


def observe_pcm16(pcm, sample_rate, start_ms, *, consent, source_id, max_seconds=5):
    if consent is not True:
        raise PermissionError('audio observation requires explicit consent')
    if not isinstance(pcm, bytes) or len(pcm) % 2:
        raise ValueError('expected complete little-endian mono PCM16 bytes')
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 48000:
        raise ValueError('sample_rate must be 8000..48000')
    if not isinstance(start_ms, int) or start_ms < 0 or not isinstance(source_id, str) or not source_id:
        raise ValueError('invalid time or source id')
    n = len(pcm) // 2
    if not n or n > sample_rate * max_seconds:
        raise ValueError('empty or over-budget audio')
    samples = struct.unpack('<' + 'h' * n, pcm)
    energy = sum(x*x for x in samples) / n
    rms = math.sqrt(energy) / 32768
    peak = max(abs(x) for x in samples) / 32768
    crossings = sum((a < 0) != (b < 0) for a,b in zip(samples,samples[1:]))
    voice_cues = _voice_cues(samples, sample_rate, rms, peak)
    return {'modality':'audio', 'source_ref':{'source_id':source_id,
            'sha256':sha256(pcm).hexdigest(),'char_start':0,'char_end':len(pcm),
            'modality':'audio/pcm16le'}, 'segments':[{'start_ms':start_ms,
            'end_ms':start_ms + (1000*n)//sample_rate,
            'acoustic':{'rms':round(rms,6),'peak':round(peak,6),
                        'zero_crossing_rate':round(crossings/max(1,n-1),6),
                        'voice_cues':voice_cues},
            'transcript':None,'provenance':'RAW_EAR_PCMC16',
            'finality':'FINAL_WINDOW','speaker_identity':None}],
            'authority':'ACOUSTIC_FEATURES_ONLY','learning_authority':False}
