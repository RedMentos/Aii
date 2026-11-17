from v13.exact_arithmetic import exact_arithmetic


def test_grounded_arithmetic():
    assert exact_arithmetic("2+2") == "4"
    assert exact_arithmetic("What is (12 + 8) / 4?") == "5"
    assert exact_arithmetic("calculate 0.1 + 0.2") == "0.3"
    assert exact_arithmetic("7 - 9") == "-2"


def test_rejects_ambiguous_or_unsafe():
    for s in ("hi", "2+2 and explain", "2**100", "1/0", "1e100", "2+foo",
              "2+2; delete files", "1,000+2", "2+2=4", "1 + 2 3",
              "9"*90 + "+1", "99999999999999999+1", "2//1"):
        assert exact_arithmetic(s) is None
