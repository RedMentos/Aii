"""V14 A5 timed audio feature adapter: synthetic/offline, no microphone access."""
from dataclasses import dataclass
from hashlib import sha256
from math import sqrt, isfinite
import struct

@dataclass(frozen=True)
class AudioSource:
    source_id: str
    consent_id: str
    started_ms: int
    sample_rate: int
    sample_count: int
    pcm_sha256: str
    provisional: bool = False

def pcm_digest(samples):
    return sha256(b''.join(struct.pack('<h', v) for v in samples)).hexdigest()

def timed_audio_packets(samples, source, window_ms=40):
    """No ASR or speaker identity inference; caller owns consented PCM store."""
    if not source.source_id or not source.consent_id:
        raise PermissionError('explicit source and consent required')
    if source.started_ms < 0 or not 8000 <= source.sample_rate <= 192000:
        raise ValueError('invalid timestamp/sample rate')
    if not 10 <= window_ms <= 1000:
        raise ValueError('invalid window')
    if len(samples) != source.sample_count or pcm_digest(samples) != source.pcm_sha256:
        raise ValueError('source content mismatch')
    step = max(1, source.sample_rate * window_ms // 1000)
    out = []
    for start in range(0, len(samples), step):
        end = min(len(samples), start + step)
        frame = samples[start:end]
        rms = sqrt(sum((v/32768.)**2 for v in frame)/len(frame))
        crossings = sum((a < 0 <= b) or (b < 0 <= a) for a,b in zip(frame,frame[1:]))
        out.append({
            'schema':'v14.a5.timed_audio/1','modality':'audio_raw_features',
            'source_id':source.source_id,'consent_id':source.consent_id,
            'pcm_sha256':source.pcm_sha256,'sample_start':start,'sample_end':end,
            'time_start_ms':source.started_ms+start*1000//source.sample_rate,
            'time_end_ms':source.started_ms+end*1000//source.sample_rate,
            'rms':round(rms,7),'peak':round(max(abs(v) for v in frame)/32768.,7),
            'zero_crossing_rate':round(crossings/max(1,len(frame)-1),7),
            'provenance':'PROVISIONAL' if source.provisional else 'FINAL_SOURCE_BOUND',
            'teacher_asr':None,'speaker_identity':None,
            'receiver_authority':'OBSERVATION_ONLY'})
    return out

def validate_packet_sequence(packets, source):
    cursor = 0
    for p in packets:
        if p['schema'] != 'v14.a5.timed_audio/1' or p['source_id'] != source.source_id:
            raise ValueError('schema/source mismatch')
        if p['consent_id'] != source.consent_id or p['pcm_sha256'] != source.pcm_sha256:
            raise PermissionError('consent/content mismatch')
        if p['sample_start'] != cursor or p['sample_end'] <= cursor:
            raise ValueError('gap/overlap/empty window')
        if p['time_start_ms'] != source.started_ms+cursor*1000//source.sample_rate:
            raise ValueError('timestamp mismatch')
        if p['sample_end'] > source.sample_count or p['time_end_ms'] != source.started_ms+p['sample_end']*1000//source.sample_rate:
            raise ValueError('invalid frame end')
        if p.get('receiver_authority') != 'OBSERVATION_ONLY' or p.get('provenance') != ('PROVISIONAL' if source.provisional else 'FINAL_SOURCE_BOUND'):
            raise PermissionError('authority/provenance mismatch')
        for feature in ('rms', 'peak', 'zero_crossing_rate'):
            value = p.get(feature)
            if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError('invalid feature')
        cursor = p['sample_end']
    if cursor != source.sample_count:
        raise ValueError('incomplete source coverage')
    return True
