import math
import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from raw_ear_vad_compare import (
    LibFvadBackend,
    WebRtcVadBackend,
    _load_temporal_class,
    _load_v3_extractor,
    compare_pcm,
)

ROOT = Path(__file__).resolve().parents[2]
V3_SOURCE = ROOT / "v13" / "code" / "v13" / "audio_voice_cues.py"
TEMPORAL_SOURCE = ROOT / "v13" / "code" / "v13" / "audio_temporal_evidence.py"


def voice_like(sample_rate=16000, seconds=2.0):
    samples = []
    count = int(sample_rate * seconds)
    for i in range(count):
        t = i / sample_rate
        if 0.5 <= t < 1.5:
            envelope = 0.65 + 0.2 * math.sin(2 * math.pi * 3 * t)
            f0 = 135 + 18 * math.sin(2 * math.pi * 2 * t)
            phase = 2 * math.pi * f0 * t
            value = envelope * (
                math.sin(phase) + 0.45 * math.sin(2 * phase) + 0.2 * math.sin(3 * phase)
            )
            sample = int(7000 * value)
        else:
            sample = 0
        samples.append(max(-32768, min(32767, sample)))
    return struct.pack("<" + "h" * len(samples), *samples)


class EnergyBaseline:
    name = "TEST_ENERGY_BASELINE"
    version = "fixture"

    def is_speech(self, frame, sample_rate):
        samples = struct.unpack("<" + "h" * (len(frame) // 2), frame)
        rms = math.sqrt(sum(x * x for x in samples) / len(samples))
        return rms > 1000


def load_sources():
    extractor, sha256, blob = _load_v3_extractor(V3_SOURCE)
    temporal = _load_temporal_class(TEMPORAL_SOURCE)
    return extractor, temporal, sha256, blob


def test_comparison_aligns_both_paths_and_reports_separate_raw_and_smoothed_metrics():
    extractor, temporal, sha256, blob = load_sources()
    result = compare_pcm(
        voice_like(), 16000, [[500, 1500]], extractor=extractor,
        temporal_class=temporal, backend=EnergyBaseline(),
        source_sha256=sha256, source_git_blob=blob,
    )
    assert result["schema"] == "v14.raw-ear-vad-comparison/1"
    assert result["alignment"].startswith("WebRTC 20ms decisions OR-combined")
    assert result["raw_ear_v3"]["raw"]["annotated_speech_intervals"] == 1
    assert result["webrtc_baseline"]["raw"]["annotated_speech_intervals"] == 1
    assert result["processed_duration_ms"] == 2000
    assert result["source"]["v3_source_git_blob"] == blob
    expected_v3 = os.getenv("V14_EXPECTED_RAW_EAR_V3_BLOB")
    expected_temporal = os.getenv("V14_EXPECTED_TEMPORAL_VOICE_BLOB")
    if expected_v3:
        assert blob == expected_v3
    if expected_temporal:
        temporal_blob = __import__("hashlib").sha1(
            b"blob " + str(TEMPORAL_SOURCE.stat().st_size).encode() + b"\0" + TEMPORAL_SOURCE.read_bytes()
        ).hexdigest()
        assert temporal_blob == expected_temporal
    assert result["raw_ear_v3"]["processing_wall_ms"] >= 0
    assert result["webrtc_baseline"]["processing_wall_ms"] >= 0


def test_invalid_sample_rate_and_annotations_fail_closed():
    extractor, temporal, sha256, blob = load_sources()
    with pytest.raises(ValueError, match="sample rate"):
        compare_pcm(b"\x00\x00" * 800, 11025, [], extractor=extractor,
                    temporal_class=temporal, backend=EnergyBaseline(),
                    source_sha256=sha256, source_git_blob=blob)
    with pytest.raises(ValueError, match="sorted and non-overlapping"):
        compare_pcm(b"\x00\x00" * 16000, 16000, [[500, 900], [800, 1000]],
                    extractor=extractor, temporal_class=temporal,
                    backend=EnergyBaseline(), source_sha256=sha256, source_git_blob=blob)


def test_webrtc_backend_handles_valid_silence_frame_when_available():
    pytest.importorskip("webrtcvad")
    backend = WebRtcVadBackend(mode=2)
    silence = bytes(2 * (16000 * 20 // 1000))
    assert backend.is_speech(silence, 16000) is False


def test_real_webrtc_backend_comparison_smoke_when_available():
    pytest.importorskip("webrtcvad")
    extractor, temporal, sha256, blob = load_sources()
    result = compare_pcm(
        voice_like(), 16000, [[500, 1500]], extractor=extractor,
        temporal_class=temporal, backend=WebRtcVadBackend(mode=2),
        source_sha256=sha256, source_git_blob=blob,
    )
    assert result["webrtc_baseline"]["name"] == "WEBRTCVAD_PYTHON_WHEELS"
    assert set(("fpr", "fnr", "f1", "onset_delay_ms_median", "offset_delay_ms_median")) <= set(
        result["webrtc_baseline"]["raw"]
    )
    assert result["process_peak_rss"] is None or result["process_peak_rss"] > 0


def test_libfvad_ctypes_binding_against_documented_c_abi_stub(tmp_path):
    compiler = shutil.which("cc") or shutil.which("gcc")
    if not compiler:
        pytest.skip("C compiler unavailable")
    source = tmp_path / "fvad_stub.c"
    library = tmp_path / "libfvad_stub.so"
    source.write_text(r'''#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
typedef struct { int mode; int rate; } Fvad;
Fvad *fvad_new(void) { return (Fvad *)calloc(1, sizeof(Fvad)); }
void fvad_free(Fvad *p) { free(p); }
int fvad_set_mode(Fvad *p, int mode) { if (!p || mode < 0 || mode > 3) return -1; p->mode=mode; return 0; }
int fvad_set_sample_rate(Fvad *p, int rate) { if (!p || (rate!=8000 && rate!=16000 && rate!=32000 && rate!=48000)) return -1; p->rate=rate; return 0; }
int fvad_process(Fvad *p, const int16_t *frame, size_t length) {
  if (!p || !frame || (length != (size_t)(p->rate/100) && length != (size_t)(p->rate/50) && length != (size_t)(p->rate*3/100))) return -1;
  for (size_t i=0; i<length; ++i) if (frame[i] > 1000 || frame[i] < -1000) return 1;
  return 0;
}
''', encoding="utf-8")
    subprocess.run([compiler, "-shared", "-fPIC", str(source), "-o", str(library)], check=True)
    backend = LibFvadBackend(str(library), mode=2, sample_rate=16000)
    silence = bytes(2 * 320)
    voice = struct.pack("<" + "h" * 320, *([2000] * 320))
    try:
        assert backend.is_speech(silence, 16000) is False
        assert backend.is_speech(voice, 16000) is True
    finally:
        backend.close()
