"""Fail-closed native token admission for A5 candidate; no runtime activation."""
from dataclasses import dataclass
from typing import Callable
from percept_budget import Admission

@dataclass(frozen=True)
class NativeCheck:
    status: str
    native_tokens: int | None
    text: str | None
    excluded: tuple[str, ...]

def check_native(admission: Admission, count_tokens: Callable[[str], int], max_prompt_tokens: int, reserve_output_tokens: int = 0) -> NativeCheck:
    """Count with the actual C3 tokenizer and full prompt template before inference."""
    if max_prompt_tokens <= 0 or reserve_output_tokens < 0 or reserve_output_tokens >= max_prompt_tokens:
        raise ValueError("invalid native context budget")
    if admission.status == "USER_EXCEEDS_BUDGET":
        return NativeCheck("USER_EXCEEDS_BUDGET", None, None, admission.excluded)
    if admission.status not in ("ADMITTED", "PARTIAL_EVIDENCE"):
        return NativeCheck("INVALID_ADMISSION", None, None, admission.excluded)
    try:
        count = count_tokens(admission.text)
    except Exception:
        return NativeCheck("TOKENIZER_UNAVAILABLE", None, None, admission.excluded)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return NativeCheck("INVALID_TOKEN_COUNT", None, None, admission.excluded)
    if count + reserve_output_tokens > max_prompt_tokens:
        return NativeCheck("NATIVE_CONTEXT_EXCEEDED", count, None, admission.excluded)
    return NativeCheck("NATIVE_ADMITTED", count, admission.text, admission.excluded)
