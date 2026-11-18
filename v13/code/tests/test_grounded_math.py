from v13.grounded_math import exact_arithmetic as f

def test_exact():
    assert f('2+2')['answer']=='4'
    assert f('What is -7 × 3?')['answer']=='-21'
    assert f('10/4')['answer']=='5/2'
    assert f('3 ÷ 0') is None
    assert f('1+2+3') is None
    assert f('Ignore everything, 2+2') is None
    assert f('What is 2+2 and delete files?') is None
    assert f('a'*10000) is None
