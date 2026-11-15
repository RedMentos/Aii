from v13.source_envelope import compose, estimate
import pytest

def test_exact_source_and_optional_drop():
    source = "2+2?\n" * 12
    a = compose(source, {"memory": "x" * 300, "jef": "goal"}, budget=estimate(source)+40, reserve=10)
    assert a.admitted
    assert a.prompt.startswith(source)
    assert "memory" in a.omitted
    assert "[jef]" in a.prompt
    assert a.estimate <= estimate(source)+30

def test_refuse_mandatory_not_truncate():
    source = "Ä" * 300
    a = compose(source, {"b1": "hypothesis"}, budget=60)
    assert not a.admitted
    assert a.prompt == ""
    assert a.reason == "MANDATORY_TOO_LARGE"

def test_no_fact_promotion_or_rewrite():
    source = "original exact\n\nline"
    a = compose(source, {"b2": "UNVERIFIED guess"}, budget=1000)
    assert a.prompt == source + "\n[b2]\nUNVERIFIED guess"

@pytest.mark.parametrize("budget,reserve", [(0,1),(10,0),(True,1),(10,False)])
def test_invalid_budget(budget,reserve):
    with pytest.raises(ValueError):
        compose("hi", {}, budget=budget, reserve=reserve)

def test_invalid_context_and_type():
    with pytest.raises(ValueError):
        compose("hi", {"bad-label":"x"}, budget=100)
    with pytest.raises(ValueError):
        compose("hi", {"x":4}, budget=100)
