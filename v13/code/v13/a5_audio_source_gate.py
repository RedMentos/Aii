"""Revalidate a SHADOW audio observation at consumption time.

Non-authoritative B/C input gate, not canonical A5 or Android permission.
"""
import hashlib
import json

def checked_audio_view(store, candidate, source_ref):
    if not isinstance(candidate, dict) or candidate.get('schema') != 'v13.a5.audio.observation_candidate.v1':
        raise ValueError('A5 audio candidate required')
    if candidate.get('canonical_a5') is not False or candidate.get('status') != 'SHADOW':
        raise PermissionError('candidate cannot claim canonical authority')
    if candidate.get('authority') != 'observation_only' or candidate.get('android_action_allowed') is not False:
        raise PermissionError('action authority forbidden')
    if candidate.get('runtime_consumer') != 'NOT_CONNECTED' or candidate.get('transcript') is not None:
        raise ValueError('unexpected runtime/ASR claim')
    source = candidate.get('source')
    if not isinstance(source, dict) or source.get('final') is not True:
        raise ValueError('final source required')
    if not isinstance(source_ref, dict) or set(source_ref) != {'source_id','sha256','char_start','char_end','modality'}:
        raise ValueError('complete Store SourceRef required')
    if source_ref['modality'] != 'text' or source_ref['source_id'] != source.get('id') or source_ref['sha256'] != source.get('store_sha256'):
        raise ValueError('source lineage mismatch')
    if type(source_ref['char_start']) is not int or source_ref['char_start'] != 0 or type(source_ref['char_end']) is not int:
        raise ValueError('full source required')
    raw = store.read_source(source_ref)
    if len(raw) != source_ref['char_end']:
        raise ValueError('source span mismatch')
    data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if data.get('final') is not True or set(data) != {'features','final','start_ms','end_ms','sample_rate_hz','acoustic'}:
        raise ValueError('stored timed audio schema mismatch')
    t = candidate.get('time')
    if not isinstance(t, dict) or any(t.get(k) != data[k] for k in ('start_ms','end_ms','sample_rate_hz')):
        raise ValueError('time changed')
    if candidate.get('raw_ear',{}).get('rms') != data['acoustic'].get('rms'):
        raise ValueError('acoustic evidence changed')
    if not isinstance(source.get('feature_sha256'),str) or len(source['feature_sha256']) != 64:
        raise ValueError('feature digest missing')
    if store.read_source(source_ref) != raw:
        raise PermissionError('source changed during observation')
    return {'schema':'v13.audio.b_source_view.shadow.v1','source_ref':dict(source_ref),
            'source_sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest(),
            'a3_embedding':list(candidate['a3']['embedding']),
            'a4_salience':candidate['a4']['score'],
            'time':dict(t),'acoustic':dict(data['acoustic']),
            'authority':'observation_only','android_action_allowed':False,
            'body_inference_executed':False,'runtime_activated':False,
            'native_android_verified':False}
