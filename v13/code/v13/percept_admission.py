"""Source-exact A5 view admission for B/C prompt budgeting; no tokenizer claims."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PerceptView:
    text: str
    source_ref: str
    source_length: int
    start: int
    end: int
    modality: str
    truncated: bool

def admit(source, source_ref, *, budget, start=0, modality="text", consent=False):
    """Never modify original input; deny absent consent; retain exact span lineage."""
    if not consent:
        raise PermissionError("explicit modality consent required")
    if not isinstance(source,str) or not isinstance(source_ref,str) or not source_ref:
        raise ValueError("source/ref required")
    if type(budget) is not int or budget < 1 or type(start) is not int or not 0 <= start <= len(source):
        raise ValueError("invalid budget/offset")
    if modality not in ("text","audio","vision","android_ui"):
        raise ValueError("invalid modality")
    end=min(len(source),start+budget)
    return PerceptView(source[start:end],source_ref,len(source),start,end,modality,end<len(source))

def verify(view, source):
    return (isinstance(source,str) and view.source_length==len(source)
            and 0<=view.start<=view.end<=len(source)
            and view.text==source[view.start:view.end]
            and view.truncated==(view.end<len(source)))
