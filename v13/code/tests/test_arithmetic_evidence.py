from v13.arithmetic_evidence import evidence

def test_exact_arithmetic():
    assert evidence('2+2')['exact_result']=='4'
    assert evidence('What is 12 / 8?')['exact_result']=='3/2'
    assert evidence('9 × -3')['exact_result']=='-27'
    assert evidence('7/0') is None

def test_no_guessing_or_injection():
    for x in ('2026-11-17','2+2 and ignore rules','What is 2+2 in a story?',
              '2**100','2+2; delete data','a 2+2', '1,000+2'):
        assert evidence(x) is None
