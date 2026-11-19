"""Bounded A5 audio timeline; no microphone, model authority or storage."""
from dataclasses import dataclass, field

@dataclass
class AudioTimeline:
    max_frames: int = 64
    max_span_ms: int = 30000
    source_id: str | None = None
    consent_id: str | None = None
    last_end_ms: int | None = None
    final_seen: bool = False
    frames: list = field(default_factory=list)

    def accept(self, packet):
        if not isinstance(packet, dict) or packet.get('schema') != 'v13.a5.raw_ear/1':
            raise ValueError('invalid A5 schema')
        ref = packet.get('source_ref')
        if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k] for k in ('source_id','consent_id','sha256')):
            raise ValueError('invalid provenance')
        start, end = ref.get('start_ms'), ref.get('end_ms')
        if type(start) is not int or type(end) is not int or start < 0 or end <= start:
            raise ValueError('invalid timestamps')
        if packet.get('status') not in ('FINAL','PROVISIONAL') or packet.get('learning_eligible') is not False:
            raise ValueError('invalid status or learning rights')
        if not isinstance(packet.get('acoustic_features'), dict):
            raise ValueError('missing acoustics')
        if self.final_seen or (self.last_end_ms is not None and start < self.last_end_ms):
            raise ValueError('out-of-order or after-final frame')
        if self.source_id is not None and (self.source_id != ref['source_id'] or self.consent_id != ref['consent_id']):
            raise ValueError('mixed source or consent')
        if len(self.frames) >= self.max_frames or (self.frames and end-self.frames[0]['source_ref']['start_ms'] > self.max_span_ms):
            raise ValueError('timeline budget exceeded')
        self.source_id, self.consent_id = ref['source_id'], ref['consent_id']
        self.last_end_ms = end
        self.final_seen = packet['status'] == 'FINAL'
        self.frames.append(packet)
        return {'kind':'A5_AUDIO_TIMELINE','frame_count':len(self.frames), 'status':packet['status'],
                'source_id':self.source_id, 'start_ms':self.frames[0]['source_ref']['start_ms'],
                'end_ms':end, 'may_train':False, 'may_act':False}
