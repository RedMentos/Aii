"""V14 RAW EAR acoustic metadata -> A5 -> Enlightened Space, no microphone or ASR."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class AudioObservation:
    source_id: str
    start_ms: int
    end_ms: int
    energy_rms: float
    pitch_hz: float | None = None
    speech_probability: float | None = None
    voice_activity: bool = False
    non_speech: str | None = None
    phase: str = "PROVISIONAL"
    consent: bool = False

    def validate(self):
        if not self.consent:
            raise PermissionError("active local audio consent required")
        if not isinstance(self.source_id, str) or not self.source_id or len(self.source_id) > 96:
            raise ValueError("invalid source")
        if not isinstance(self.start_ms, int) or not isinstance(self.end_ms, int) or self.start_ms < 0 or self.end_ms <= self.start_ms or self.end_ms - self.start_ms > 30000:
            raise ValueError("invalid bounded time span")
        if self.phase not in {"PROVISIONAL", "FINAL"}:
            raise ValueError("invalid provenance")
        if not isfinite(self.energy_rms) or not 0 <= self.energy_rms <= 1:
            raise ValueError("invalid energy")
        if self.pitch_hz is not None and (not isfinite(self.pitch_hz) or not 0 < self.pitch_hz <= 2000):
            raise ValueError("invalid pitch")
        if self.speech_probability is not None and (not isfinite(self.speech_probability) or not 0 <= self.speech_probability <= 1):
            raise ValueError("invalid speech probability")
        if self.non_speech not in {None, "LAUGHTER", "COUGH", "MUSIC", "NOISE", "SILENCE", "OTHER"}:
            raise ValueError("invalid non-speech label")

def make_a5_audio_packet(obs: AudioObservation, event: dict) -> dict:
    obs.validate()
    if not isinstance(event, dict) or not all(isinstance(event.get(k), str) and event[k] for k in ("event_id", "brain_generation_id")):
        raise ValueError("unbound runtime event")
    return {"schema": "v14.a5.audio-percept/1", "event_id": event["event_id"],
            "brain_generation_id": event["brain_generation_id"], "source_id": obs.source_id,
            "start_ms": obs.start_ms, "end_ms": obs.end_ms, "phase": obs.phase,
            "modality": "audio", "energy_rms": obs.energy_rms, "pitch_hz": obs.pitch_hz,
            "speech_probability": obs.speech_probability, "voice_activity": obs.voice_activity,
            "non_speech": obs.non_speech, "authority": "CONTROL_ONLY", "asr_text": None}

def publish_audio_percept(space, obs: AudioObservation, event: dict) -> tuple[dict, dict]:
    """Publish to existing runtime bus. Audio is NOT a verified text SourceRef."""
    packet = make_a5_audio_packet(obs, event)
    summary = (f"audio {obs.phase.lower()} {obs.start_ms}-{obs.end_ms}ms "
               f"vad={int(obs.voice_activity)} energy={obs.energy_rms:.3f} "
               f"non_speech={obs.non_speech or 'UNCLASSIFIED'}")
    result = space.publish(event, "A_PERCEPTION", "CONTROL", summary=summary,
                           authority="CONTROL_ONLY")
    return packet, result
