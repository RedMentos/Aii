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
    if (type(frame.source_id) is not str or not 0 < len(frame.source_id) <= 128 or
            any(ord(c) < 32 or ord(c) == 127 for c in frame.source_id)):
        raise ValueError('invalid source id')
    if (type(frame.consent_id) is not str or not 0 < len(frame.consent_id) <= 128 or
            any(ord(c) < 32 or ord(c) == 127 for c in frame.consent_id)):
        raise PermissionError('valid explicit consent reference required')
    if type(frame.final) is not bool:
        raise ValueError('final must be boolean')
    if type(frame.start_ms) is not int or type(frame.end_ms) is not int:
        raise ValueError('timestamps must be integers')
    if type(frame.pcm16le) is not bytes:
        raise ValueError('PCM16LE must be bytes')
    if type(frame.sample_rate) is not int or frame.sample_rate not in (8000,16000,24000,32000,44100,48000):
        raise ValueError('unsupported sample rate')
    if not frame.pcm16le or len(frame.pcm16le)%2:
        raise ValueError('invalid PCM16LE')
    if len(frame.pcm16le)>2*1024*1024:
        raise ValueError('PCM frame exceeds 2 MiB bound')
    n=len(frame.pcm16le)//2
    if n/frame.sample_rate>30:
        raise ValueError('PCM frame exceeds 30 second bound')
    if frame.start_ms<0 or frame.end_ms<=frame.start_ms:
        raise ValueError('invalid time bounds')
    duration=1000*n/frame.sample_rate
    if abs(frame.end_ms-frame.start_ms-duration)>max(2.,duration*.02):
        raise ValueError('PCM duration/timestamps disagree')
    samples=struct.unpack('<%dh'%n,frame.pcm16le)
    rms=sqrt(sum(float(x)*x for x in samples)/n)/32768.
    peak=max(abs(x) for x in samples)/32768.
    zcr=sum((a<0)!=(b<0) for a,b in zip(samples,samples[1:]))/max(1,n-1)
    # 20 ms envelope retains temporal acoustic changes without pretending ASR.
    width=max(1,frame.sample_rate//50)
    envelope=[round(sqrt(sum(float(x)*x for x in samples[i:i+width])/len(samples[i:i+width]))/32768.,5)
              for i in range(0,n,width)]
    return {'schema':'v13.a5.raw_ear/1','modality':'audio',
      'source_ref':{'source_id':frame.source_id,'sha256':hashlib.sha256(frame.pcm16le).hexdigest(),
        'start_ms':frame.start_ms,'end_ms':frame.end_ms,'consent_id':frame.consent_id},
      'provenance':'RAW_PCM_OBSERVATION','status':'FINAL' if frame.final else 'PROVISIONAL',
      'learning_eligible':False,'sample_rate':frame.sample_rate,'sample_count':n,
      'acoustic_features':{'rms':round(rms,6),'peak':round(peak,6),
        'zero_crossing_rate':round(zcr,6),'silence_candidate':rms<.01,'clipped':peak>=.999,
        'envelope_20ms':envelope},
      'teacher_asr':None,'speaker_identity':None,'speech_effector':None}

def jef_audio_observation(packet):
    """Structured A5->JEF adapter; not a native JEF runtime hook or permission grant."""
    if type(packet) is not dict or packet.get('schema') != 'v13.a5.raw_ear/1':
        raise ValueError('untrusted A5 audio packet')
    source = packet.get('source_ref')
    if (type(source) is not dict or type(source.get('consent_id')) is not str or
            not source['consent_id'] or type(source.get('sha256')) is not str or
            len(source['sha256']) != 64 or
            any(c not in '0123456789abcdef' for c in source['sha256'])):
        raise ValueError('invalid source provenance')
    if packet.get('status') not in ('FINAL', 'PROVISIONAL') or type(packet.get('acoustic_features')) is not dict:
        raise ValueError('invalid acoustic observation')
    return {'kind':'A5_AUDIO_OBSERVATION','source_ref':dict(packet['source_ref']),
      'status':packet['status'],'features':dict(packet['acoustic_features']),
      'may_train':False,'may_act':False,'text':None}
