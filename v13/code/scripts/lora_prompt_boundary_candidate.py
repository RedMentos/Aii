"""Opt-in candidate: reject training pairs that lost their entire prompt.

The frozen trainer's JEPA branch uses hidden[plen - 1]. At plen == 0 this
selects an answer state, while its separate cosine probe receives an empty
prompt. This candidate fails before optimization instead of redefining data
truncation or silently training a different objective. No default registration.
"""
from pathlib import Path
from v13 import lora_trainer as original
from v13.common import file_hash, Unavailable

SOURCE_SHA256 = '45ee09f701239d2a09285edcc970d87652e2cadc17f43bc3c4fe3b546d8895cb'
CANDIDATE_REVISION = 'lora-prompt-boundary-v1'


class PromptBoundLoraTrainer(original.LoraTrainer):
    """Explicitly selected replacement for LoraTrainer on a new cohort only."""
    method = 'lora-torch-cpu-prompt-boundary-v1'

    def __init__(self, *args, **kwargs):
        if file_hash(Path(original.__file__)) != SOURCE_SHA256:
            raise Unavailable('Unsupported source for prompt-bound LoRA candidate')
        super().__init__(*args, **kwargs)
        # Never resume an original/unprotected checkpoint with this candidate.
        self.candidate_sha256 = file_hash(Path(__file__))
        self.work = self.work / CANDIDATE_REVISION / self.candidate_sha256

    def _encode(self, tok, prompt, target=None):
        if target is not None:
            budget = self.cfg['max_tokens']
            if type(budget) is not int or budget < 2:
                raise ValueError('Training requires an integer max_tokens >= 2')
        ids, labels = super()._encode(tok, prompt, target)
        if target is None:
            return ids, labels
        if len(ids) != len(labels) or not labels or labels[0] != -100:
            raise ValueError('Training pair lost its prompt; increase max_tokens or shorten the target')
        if not any(value != -100 for value in labels):
            raise ValueError('Training pair has no supervised target tokens')
        return ids, labels
