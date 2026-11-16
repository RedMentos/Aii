"""V13 A0/A1/A5 RAW EAR: consented, timestamped PCM acoustic observations.
No microphone access, transcript, speaker inference, Android grant or training authority.
"""
from dataclasses import dataclass
from math import sqrt
import hashlib
import struct

@dataclass(frozen=True)
class AudioFrame:
    source_id: str
    pcm16le: bytes
    sample_rate: int
    start_ms: int
    end_ms: int
    consent_id: str
    final: bool = False

def raw_ear_packet(frame: AudioFrame):
    if not isinstance(frame, AudioFrame):
        raise TypeError('AudioFrame required')
    if not frame.consent_id or not frame.source_id:
        raise PermissionError('source and explicit consent required')
    if frame.sample_rate not in (8000,16000,24000,32000,44100,48000):
        raise ValueError('unsupported sample rate')
    if not frame.pcm16le or len(frame.pcm16le)%2:
        raise ValueError('invalid PCM16LE')
    n=len(frame.pcm16le)//2
    if frame.start_ms<0 or frame.end_ms<=frame.start_ms:
        raise ValueError('invalid time bounds')
    duration=1000*n/frame.sample_rate
    if abs(frame.end_ms-frame.start_ms-duration)>max(2.,duration*.02):
        raise ValueError('PCM duration/timestamps disagree')
    samples=struct.unpack('<%dh'%n,frame.pcm16le)
    rms=sqrt(sum(float(x)*x for x in samples)/n)/32768.
    peak=max(abs(x) for x in samples)/32768.
    zcr=sum((a<0)!=(b<0) for a,b in zip(samples,samples[1:]))/max(1,n-1)
    return {'schema':'v13.a5.raw_ear/1','modality':'audio',
      'source_ref':{'source_id':frame.source_id,'sha256':hashlib.sha256(frame.pcm16le).hexdigest(),
        'start_ms':frame.start_ms,'end_ms':frame.end_ms,'consent_id':frame.consent_id},
      'provenance':'RAW_PCM_OBSERVATION','status':'FINAL' if frame.final else 'PROVISIONAL',
      'learning_eligible':False,'sample_rate':frame.sample_rate,'sample_count':n,
      'acoustic_features':{'rms':round(rms,6),'peak':round(peak,6),
        'zero_crossing_rate':round(zcr,6),'silence_candidate':rms<.01,'clipped':peak>=.999},
      'teacher_asr':None,'speaker_identity':None,'speech_effector':None}

def jef_audio_observation(packet):
    """Structured A5->JEF adapter; not a native JEF runtime hook or permission grant."""
    if packet.get('schema')!='v13.a5.raw_ear/1' or not packet.get('source_ref',{}).get('consent_id'):
        raise ValueError('untrusted A5 audio packet')
    return {'kind':'A5_AUDIO_OBSERVATION','source_ref':dict(packet['source_ref']),
      'status':packet['status'],'features':dict(packet['acoustic_features']),
      'may_train':False,'may_act':False,'text':None}
