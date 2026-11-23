"""Final native-token verification after conservative organ prompt admission.

A caller must pass the actual model template renderer and tokenizer. This
module never authorizes execution or drops an essential source.
"""
from dataclasses import dataclass
from typing import Callable, Sequence
from .prompt_admission import Segment, Admission, PromptAdmissionError, admit

@dataclass(frozen=True)
class NativePromptDecision:
    admission: Admission
    exact_prompt_tokens: int
    status: str

def verify_native_prompt(segments: Sequence[Segment], *,
                         context_tokens: int, output_tokens: int,
                         prompt_cap_tokens: int,
                         count_rendered: Callable[[Sequence[Segment]], int],
                         framing_reserve: int = 32) -> NativePromptDecision:
    """Check the *final* native template, not just summed segment estimates.

    Conservative admission may underestimate template overhead. Fail closed
    instead of silently removing organ evidence or the user's source.
    """
    if not callable(count_rendered):
        raise TypeError("native rendered tokenizer is required")
    result = admit(segments, context_tokens=context_tokens,
                   output_tokens=output_tokens,
                   prompt_cap_tokens=prompt_cap_tokens,
                   framing_reserve=framing_reserve)
    count = count_rendered(result.accepted)
    if type(count) is not int or count < 0:
        raise ValueError("native tokenizer returned invalid count")
    available = min(prompt_cap_tokens,
                    context_tokens - output_tokens - framing_reserve)
    return NativePromptDecision(result, count,
                                "VERIFIED" if count <= available
                                else "RENDERED_OVER_BUDGET")
