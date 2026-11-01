import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from v13.sample_labels import modulate, label_class


def it(kind, **k):
    return dict({'memory_id': kind, 'kind': kind, 'prompt': 'q', 'target': 'a'}, **k)


def test_sources_ordered_and_normalised():
    items = [it('fact'), it('sdft'), it('tool_outcome'), it('x', origin='dream')]
    out, rep = modulate(items)
    w = {i['memory_id']: i['weight'] for i in out}
    assert 'x' not in w and rep['dropped'][0]['class'] == 'dream'
    assert w['tool_outcome'] == 1.0 and w['fact'] < 1.0 and 0 < w['sdft'] < w['fact']


def test_rating_sign_kept_and_veto_dropped():
    out, _ = modulate([it('rated_answer', weight=-0.4), it('fact', safety_veto=True), it('fact')])
    assert len(out) == 2 and out[0]['weight'] < 0 < out[1]['weight']


def test_disabled_and_labels():
    items = [it('fact')]
    assert modulate(items, False)[0] == items
    assert label_class(it('tool_outcome', origin='self')) == 'outcome'
