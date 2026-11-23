import io
from v13.android_control_cli import main


def test_cli_refuses_noninteractive_approval(tmp_path):
    output = io.StringIO()
    assert main(["--db", str(tmp_path / "audit.sqlite")], stdin=io.StringIO("propose back {}\nYES\n"), stdout=output) == 2
    assert "Refusing non-interactive" in output.getvalue()
    assert not (tmp_path / "audit.sqlite").exists()
