"""No native model, device or live tool authorization in these tests."""
from v13.arithmetic_verifier import arithmetic_agreement

def test_exact_source_equation_rejects_wrong_answer_even_if_correct_number_elsewhere():
    assert arithmetic_agreement("2+2", 4, "2 + 2 = 2. Maybe 4 elsewhere.") is False

def test_exact_source_equation_accepts_correct_answer():
    assert arithmetic_agreement("2+2", 4, "2 + 2 = 4.") is True

def test_conflicting_equations_are_not_positive_evidence():
    assert arithmetic_agreement("2+2", 4, "2+2=4; 2+2=2") is False

def test_unrelated_equation_does_not_grant_agreement():
    assert arithmetic_agreement("2+2", 4, "3+1=4") is None

def test_plain_number_is_weak_evidence_only_when_unambiguous():
    assert arithmetic_agreement("2+2", 4, "4") is True
    assert arithmetic_agreement("2+2", 4, "The numbers 2 and 4") is False

def test_unsafe_or_unbounded_expression_is_unscorable():
    assert arithmetic_agreement("__import__('os')", 4, "4") is None
    assert arithmetic_agreement("2+2", float("nan"), "4") is None
    assert arithmetic_agreement("2+2", 4, "No number") is None
