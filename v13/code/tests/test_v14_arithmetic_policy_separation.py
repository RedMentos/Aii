from v13.config import initialize
from v13.output_policy import match
from v13.store import Store


def test_builtin_arithmetic_is_not_an_approved_fixed_rule(tmp_path):
    home = tmp_path / "runtime"
    initialize(home)
    store = Store(home)
    try:
        assert match(store, "2+2") is None
        assert match(store, "Was ist 2+2?") is None
        assert match(store, "calculate 7-12") is None
    finally:
        store.close()
