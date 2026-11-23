"""Source-revalidated A5 -> C3 admission boundary (read-only, SHADOW).

No microphone, OS permission, model activation, or learning authority.
The caller supplies the actual SourceStore reader; this function never invents
source validity or treats acoustic features as semantic truth.
"""
from .audio_shadow_consumer import audio_shadow_observation
from .audio_prompt_admission import admit_audio_shadow


def admit_checked_audio_percept(packet, read_source, *, max_utf8_bytes=256):
    """Revalidate the original PerceptPacket before building bounded prompt data.

    Never admit a previously cached observation without checking its source:
    a source may have been revoked between A5 capture and C3 consumption.
    """
    observation = audio_shadow_observation(packet, read_source)
    result = admit_audio_shadow(observation, max_utf8_bytes=max_utf8_bytes)
    return {
        "status": result["status"],
        "prompt_text": result["prompt_text"],
        "utf8_bytes": result["utf8_bytes"],
        "omitted_windows": result["omitted_windows"],
        "finality": observation["finality"],
        "source_sha256": observation["source_ref"]["sha256"],
        "authority": "SHADOW_ONLY",
        "action_authority": False,
        "learning_authority": False,
        "semantic_truth_authority": False,
    }
