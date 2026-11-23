"""SHADOW A1→STEP2 source-backed segmentation with Store revalidation.

The frozen A1 segmenters and Runtime are not modified. A structurally valid
but shifted SourceRef must not become a trusted quote without an exact Store
round-trip. No model, learning, tool or age authority is added.
"""
from scripts.a1_partial_source_ref_candidate import segment_excerpt


def verified_segment(store, text, source_ref, width=240, mode='event'):
    if type(text) is not str or type(source_ref) is not dict:
        raise ValueError('Exact text and SourceRef required')
    if type(width) is not int or width <= 0 or mode not in ('fixed', 'event'):
        raise ValueError('Invalid A1 segment settings')
    try:
        actual = store.read_source(source_ref)
    except Exception as exc:
        raise ValueError('Unresolvable A1 source') from exc
    if actual != text:
        raise ValueError('A1 excerpt is not exact Store source')
    pieces = segment_excerpt(text, source_ref, width, mode)
    for piece in pieces:
        try:
            recovered = store.read_source(piece['source_ref'])
        except Exception as exc:
            raise ValueError('Unresolvable A1 child SourceRef') from exc
        if recovered != piece['text']:
            raise ValueError('A1 child SourceRef does not match Store')
    if ''.join(piece['text'] for piece in pieces) != text:
        raise ValueError('A1 segmentation did not preserve complete source')
    return pieces
