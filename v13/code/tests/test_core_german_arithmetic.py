"""Source-bound German arithmetic proposal regression (no tool activation)."""
from v13.toolstep import propose
from v13.fastpolicy import answer_type


def test_german_word_arithmetic_is_proposed_without_execution():
    cases = {
        "Was ist 2 mal 3?": "2*3",
        "Wie viel ist 12 geteilt durch 4?": "12/4",
        "Was ergibt 7 plus 5?": "7+5",
        "Wie viel ist 9 minus 2?": "9-2",
    }
    for question, expression in cases.items():
        proposal = propose(question)
        assert proposal is not None
        assert proposal["tool"] == "calc"
        assert proposal["args"]["expression"] == expression


def test_german_arithmetic_proposer_does_not_execute_or_enable_tool():
    assert propose("Bitte erkläre mir die Multiplikation.") is None
    assert propose("Was ist heute am 2026-11-15 passiert?") is None
    assert answer_type("Was ist 2+2?") == "number"
