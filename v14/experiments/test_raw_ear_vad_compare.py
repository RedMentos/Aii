import contextlib
import io
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from raw_ear_vad_compare import (
    LibFvadBackend,
    WebRtcVadBackend,
    _load_temporal_class,
    _load_v3_extractor,
    _metrics,
    compare_pcm,
    main,
)

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_RAW_EAR_V3_BLOB = "81ae3e453c9ef378b072dfc9d243098427e24baa"
EXPECTED_TEMPORAL_VOICE_BLOB = "098ce2ec6bb0b744166d711a3401b7acf0252de1"
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


class RawEarVadCompareTests(unittest.TestCase):
    def load_sources(self):
        extractor, sha256, blob = _load_v3_extractor(V3_SOURCE)
        temporal = _load_temporal_class(TEMPORAL_SOURCE)
        return extractor, temporal, sha256, blob

    def test_comparison_alignment_metrics_and_exact_source_hashes(self):
        extractor, temporal, sha256, blob = self.load_sources()
        result = compare_pcm(
            voice_like(), 16000, [[500, 1500]], extractor=extractor,
            temporal_class=temporal, backend=EnergyBaseline(),
            source_sha256=sha256, source_git_blob=blob,
        )
        self.assertEqual(result["schema"], "v14.raw-ear-vad-comparison/1")
        self.assertTrue(result["alignment"].startswith("20ms VAD decisions OR-combined"))
        self.assertEqual(result["raw_ear_v3"]["raw"]["annotated_speech_intervals"], 1)
        self.assertEqual(result["vad_baseline"]["raw"]["annotated_speech_intervals"], 1)
        self.assertEqual(result["processed_duration_ms"], 2000)
        self.assertNotIn("webrtc_baseline", result)
        self.assertEqual(result["source"]["v3_source_git_blob"], blob)
        expected_v3 = os.getenv("V14_EXPECTED_RAW_EAR_V3_BLOB", EXPECTED_RAW_EAR_V3_BLOB)
        expected_temporal = os.getenv("V14_EXPECTED_TEMPORAL_VOICE_BLOB", EXPECTED_TEMPORAL_VOICE_BLOB)
        self.assertEqual(expected_v3, EXPECTED_RAW_EAR_V3_BLOB)
        self.assertEqual(expected_temporal, EXPECTED_TEMPORAL_VOICE_BLOB)
        self.assertEqual(blob, expected_v3)
        if expected_temporal:
            import hashlib
            temporal_blob = hashlib.sha1(
                b"blob " + str(TEMPORAL_SOURCE.stat().st_size).encode() + b"\0" + TEMPORAL_SOURCE.read_bytes()
            ).hexdigest()
            self.assertEqual(temporal_blob, expected_temporal)
        self.assertGreaterEqual(result["raw_ear_v3"]["processing_wall_ms"], 0)
        self.assertGreaterEqual(result["vad_baseline"]["processing_wall_ms"], 0)

    def test_invalid_sample_rate_and_annotations_fail_closed(self):
        extractor, temporal, sha256, blob = self.load_sources()
        with self.assertRaisesRegex(ValueError, "sample rate"):
            compare_pcm(b"\x00\x00" * 800, 11025, [], extractor=extractor,
                        temporal_class=temporal, backend=EnergyBaseline(),
                        source_sha256=sha256, source_git_blob=blob)
        with self.assertRaisesRegex(ValueError, "sorted and non-overlapping"):
            compare_pcm(b"\x00\x00" * 16000, 16000, [[500, 900], [800, 1000]],
                        extractor=extractor, temporal_class=temporal,
                        backend=EnergyBaseline(), source_sha256=sha256, source_git_blob=blob)

    def test_webrtc_backend_handles_valid_silence_frame_when_available(self):
        try:
            import webrtcvad  # noqa: F401
        except ImportError:
            self.skipTest("test-only WebRTC wrapper is not installed")
        backend = WebRtcVadBackend(mode=2)
        silence = bytes(2 * (16000 * 20 // 1000))
        self.assertFalse(backend.is_speech(silence, 16000))

    def test_real_webrtc_backend_comparison_smoke_when_available(self):
        try:
            import webrtcvad  # noqa: F401
        except ImportError:
            self.skipTest("test-only WebRTC wrapper is not installed")
        extractor, temporal, sha256, blob = self.load_sources()
        result = compare_pcm(
            voice_like(), 16000, [[500, 1500]], extractor=extractor,
            temporal_class=temporal, backend=WebRtcVadBackend(mode=2),
            source_sha256=sha256, source_git_blob=blob,
        )
        self.assertEqual(result["vad_baseline"]["name"], "WEBRTCVAD_PYTHON_WHEELS")
        self.assertEqual(result["webrtc_baseline"], result["vad_baseline"])
        self.assertTrue({"fpr", "fnr", "f1", "onset_delay_ms_median", "offset_delay_ms_median"} <=
                        set(result["webrtc_baseline"]["raw"]))
        self.assertTrue(result["process_peak_rss"] is None or result["process_peak_rss"] > 0)

    def test_libfvad_ctypes_binding_against_documented_c_abi_stub(self):
        compiler = shutil.which("cc") or shutil.which("gcc")
        if not compiler:
            self.skipTest("C compiler unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fvad_stub.c"
            library = root / "libfvad_stub.so"
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
                self.assertFalse(backend.is_speech(silence, 16000))
                self.assertTrue(backend.is_speech(voice, 16000))
                silence_8k = bytes(2 * 80)
                self.assertFalse(backend.is_speech(silence_8k, 8000))
            finally:
                backend.close()




    def test_real_libfvad_shared_library_comparison_smoke_when_available(self):
        library = os.getenv("V14_LIBFVAD_LIBRARY")
        if not library or not Path(library).is_file():
            self.skipTest("pinned native libfvad shared library was not built")
        extractor, temporal, sha256, blob = self.load_sources()
        version = os.getenv("V14_LIBFVAD_VERSION", "libfvad-revision-unpinned")
        backend = LibFvadBackend(
            library, mode=2, sample_rate=16000, version=version
        )
        try:
            result = compare_pcm(
                voice_like(), 16000, [[500, 1500]], extractor=extractor,
                temporal_class=temporal, backend=backend,
                source_sha256=sha256, source_git_blob=blob,
            )
        finally:
            backend.close()
        self.assertEqual(result["vad_baseline"]["name"], "LIBFVAD_C_API")
        self.assertEqual(result["vad_baseline"]["version"], version)
        self.assertEqual(result["processed_duration_ms"], 2000)
        self.assertGreaterEqual(result["vad_baseline"]["processing_cpu_ms"], 0)

    def test_cli_libfvad_backend_uses_pinned_version_environment(self):
        library = os.getenv("V14_LIBFVAD_LIBRARY")
        if not library or not Path(library).is_file():
            self.skipTest("pinned native libfvad shared library was not built")
        version = "dpirch/libfvad@test-cli-entrypoint"
        previous_version = os.environ.get("V14_LIBFVAD_VERSION")
        os.environ["V14_LIBFVAD_VERSION"] = version
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                wav_path = root / "voice-like.wav"
                annotation_path = root / "annotations.json"
                pcm = voice_like()
                with wave.open(str(wav_path), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(pcm)
                annotation_path.write_text(
                    json.dumps({"speech_intervals_ms": [[500, 1500]]}),
                    encoding="utf-8",
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result_code = main([
                        str(wav_path), str(annotation_path),
                        "--backend", "libfvad",
                        "--libfvad-path", library,
                    ])
                self.assertEqual(result_code, 0)
                result = json.loads(output.getvalue())
                self.assertEqual(result["vad_baseline"]["name"], "LIBFVAD_C_API")
                self.assertEqual(result["vad_baseline"]["version"], version)
                self.assertEqual(result["processed_duration_ms"], 2000)
        finally:
            if previous_version is None:
                os.environ.pop("V14_LIBFVAD_VERSION", None)
            else:
                os.environ["V14_LIBFVAD_VERSION"] = previous_version

    def test_transition_latency_uses_state_change_window_end(self):
        predictions = [
            {"start_ms": 420, "end_ms": 460, "positive": False},
            {"start_ms": 440, "end_ms": 480, "positive": True},
            {"start_ms": 460, "end_ms": 500, "positive": True},
            {"start_ms": 1460, "end_ms": 1500, "positive": True},
            {"start_ms": 1480, "end_ms": 1520, "positive": False},
            {"start_ms": 1500, "end_ms": 1540, "positive": False},
        ]
        result = _metrics(predictions, [(500, 1500)], 2000)
        self.assertEqual(result["onset_delay_ms_median"], -20)
        self.assertEqual(result["offset_delay_ms_median"], 20)
        self.assertEqual(result["transition_time"], "end_of_state-changing_window")

    def test_partial_twenty_ms_tail_is_rejected_instead_of_dropped(self):
        extractor, temporal, sha256, blob = self.load_sources()
        pcm = bytes(2 * 16000) + bytes(2)
        with self.assertRaisesRegex(ValueError, "align to the 20 ms hop"):
            compare_pcm(
                pcm, 16000, [[100, 200]], extractor=extractor,
                temporal_class=temporal, backend=EnergyBaseline(),
                source_sha256=sha256, source_git_blob=blob,
            )

if __name__ == "__main__":
    unittest.main()
