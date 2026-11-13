"""Pure source-bound C3 prompt-frame preflight. Candidate only; not live wired."""
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class FrameReceipt:
    status: str
    tokens: int | None
    prompt: str | None

def preflight(source_text: str, frame: Callable[[str], str], tokenizer: Callable[[str], int], context_limit: int, output_reserve: int, prompt_limit: int | None = None) -> FrameReceipt:
    """Count FULL native frame, including system/chat template, not only evidence.

    Does not truncate user text or claim native phone timing. Caller must supply
    the actual deployed model's framing and tokenizer, otherwise fail closed.
    """
    if type(context_limit) is not int or type(output_reserve) is not int or context_limit <= 0 or not 0 <= output_reserve < context_limit:
        raise ValueError('invalid context/output budget')
    if prompt_limit is not None and (type(prompt_limit) is not int or prompt_limit <= 0):
        raise ValueError('invalid prefill budget')
    if not isinstance(source_text, str) or not source_text:
        return FrameReceipt('INVALID_SOURCE', None, None)
    try:
        prompt = frame(source_text)
        if not isinstance(prompt, str) or not prompt or source_text not in prompt:
            return FrameReceipt('SOURCE_NOT_PRESERVED', None, None)
        count = tokenizer(prompt)
    except Exception:
        return FrameReceipt('FRAME_OR_TOKENIZER_UNAVAILABLE', None, None)
    if type(count) is not int or count < 0:
        return FrameReceipt('INVALID_TOKEN_COUNT', None, None)
    if count + output_reserve > context_limit:
        return FrameReceipt('CONTEXT_OVERFLOW', count, None)
    if prompt_limit is not None and count > prompt_limit:
        return FrameReceipt('PREFILL_BUDGET_EXCEEDED', count, None)
    return FrameReceipt('ADMITTED', count, prompt)
