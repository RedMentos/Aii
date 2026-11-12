"""Read-only A5 audio source gate; does not grant device or learning authority."""
import hmac
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
    ref = percept_packet.get('source_ref')
    if not isinstance(ref, dict):
        raise ValueError('missing source reference')
    sid, sha = ref.get('source_id'), ref.get('sha256')
    if not isinstance(sid, str) or not sid or not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError('invalid source reference')
    if ref.get('modality') != 'audio' or ref not in percept_packet.get('provenance', []):
        raise ValueError('provenance mismatch')
    segments = percept_packet.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ValueError('no segments')
    for segment in segments:
        if not isinstance(segment, dict) or segment.get('action_authority') is not False or segment.get('learning_authority') is not False:
            raise PermissionError('unexpected authority')
        if segment.get('finality') not in ('FINAL', 'PROVISIONAL'):
            raise ValueError('invalid finality')
    source = read_source(sid)
    if not isinstance(source, dict) or source.get('revoked') is not False or source.get('modality') != 'audio':
        raise PermissionError('source absent, revoked or wrong modality')
    stored_sha = source.get('sha256')
    if not isinstance(stored_sha, str) or not hmac.compare_digest(sha, stored_sha):
        raise PermissionError('source hash mismatch')
    return {'source_ref': dict(ref), 'segments': [dict(s) for s in segments],
            'modality': 'audio', 'authority': 'SHADOW_ONLY',
            'event_id': percept_packet.get('event_id'),
            'brain_generation_id': percept_packet.get('brain_generation_id')}
