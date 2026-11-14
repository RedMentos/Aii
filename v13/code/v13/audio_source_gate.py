"""Read-only A5 audio source gate; does not grant device or learning authority."""
from copy import deepcopy
import hmac
import math
import re

_SHA = re.compile(r'[0-9a-f]{64}\Z')

def checked_audio_source_view(percept_packet, read_source):
    """Recheck source at consumption; fail closed on revoke/mismatch.

    read_source(source_id) returns dict with sha256, revoked, modality.
    Caller must adapt the real runtime SourceStore; no OS consent is granted here.
    """
    if not callable(read_source):
        raise TypeError('read_source callback required')
    if not isinstance(percept_packet, dict) or percept_packet.get('modality') != 'audio':
        raise ValueError('not an audio PerceptPacket')
    # Packet-level claims are untrusted too: segment checks alone are not enough.
    # A5 acoustic observations never confer action, learning or semantic authority.
    for key in ('action_authority', 'learning_authority', 'semantic_truth_authority'):
        if key in percept_packet and percept_packet[key] is not False:
            raise PermissionError('forged packet-level authority')
    if 'authority' in percept_packet and percept_packet['authority'] != 'SHADOW_ONLY':
        raise PermissionError('unexpected packet-level authority')
    ref = percept_packet.get('source_ref')
    if not isinstance(ref, dict):
        raise ValueError('missing source reference')
    sid, sha = ref.get('source_id'), ref.get('sha256')
    if not isinstance(sid, str) or not sid or not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError('invalid source reference')
    if (ref.get('modality') != 'audio' or type(ref.get('char_start')) is not int
            or type(ref.get('char_end')) is not int or ref['char_start'] != 0
            or ref['char_end'] != 0 or type(percept_packet.get('provenance')) is not list
            or len(percept_packet['provenance']) != 1 or percept_packet['provenance'][0] != ref):
        raise ValueError('provenance mismatch')
    if not all(isinstance(percept_packet.get(k), str) and percept_packet[k]
               for k in ('event_id', 'brain_generation_id')):
        raise ValueError('missing event or generation identity')
    segments = percept_packet.get('segments')
    if not isinstance(segments, list) or not 1 <= len(segments) <= 64:
        raise ValueError('no segments')
    last_end = -1
    for segment in segments:
        if not isinstance(segment, dict) or segment.get('action_authority') is not False or segment.get('learning_authority') is not False:
            raise PermissionError('unexpected authority')
        if segment.get('finality') not in ('FINAL', 'PROVISIONAL'):
            raise ValueError('invalid finality')
        if 'start_ms' not in segment or 'end_ms' not in segment:
            raise ValueError('missing bounded audio window')
        start, end = segment.get('start_ms'), segment.get('end_ms')
        if (type(start) is not int or type(end) is not int or start < 0
                or start < last_end or end <= start or end-start > 1000):
            raise ValueError('invalid or overlapping audio window')
        last_end = end
        if not isinstance(segment.get('consent_receipt_ref'), str) or not segment['consent_receipt_ref'].strip():
            raise PermissionError('missing consent receipt reference')
        acoustic = segment.get('acoustic')
        if not isinstance(acoustic, dict):
            raise ValueError('missing or invalid acoustic features')
        for name in ('rms', 'zcr'):
            value = acoustic.get(name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('invalid normalized acoustic feature')
        # Optional acoustic/prosody features must not carry non-finite values.
        # Keep their domain-specific ranges to the owning feature contract.
        for name, value in acoustic.items():
            if isinstance(value, bool) or (isinstance(value, (int, float)) and not math.isfinite(value)):
                raise ValueError('invalid optional acoustic feature')
        if segment.get('asr_transcript') is not None:
            raise ValueError('unverified transcript in raw-ear packet')
    source = read_source(sid)
    if not isinstance(source, dict) or source.get('revoked') is not False or source.get('modality') != 'audio':
        raise PermissionError('source absent, revoked or wrong modality')
    stored_sha = source.get('sha256')
    if not isinstance(stored_sha, str) or not hmac.compare_digest(sha, stored_sha):
        raise PermissionError('source hash mismatch')
    return {'source_ref': deepcopy(ref), 'segments': deepcopy(segments),
            'modality': 'audio', 'authority': 'SHADOW_ONLY',
            'event_id': percept_packet.get('event_id'),
            'brain_generation_id': percept_packet.get('brain_generation_id')}
