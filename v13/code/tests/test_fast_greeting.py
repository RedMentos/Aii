import pytest

from v13.fast_greeting import is_text_only_event, match, match_unclaimed


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hi", "Hi."),
        ("HI!", "Hi."),
        ("  Hallo…  ", "Hallo."),
        ("Guten Morgen.", "Guten Morgen."),
        ("good evening?", "Good evening."),
    ],
)
def test_exact_standalone_greetings(text, expected):
    result = match(text)
    assert result is not None
    assert result["reply"] == expected
    assert result["rule_id"] == "BUILTIN_GREETING_ACK_V1"


@pytest.mark.parametrize(
    "text",
    [
        "hi there",
        "hi, can you calculate 2+2?",
        "hello, open settings",
        "guten  morgen",
        "what's up?",
        "yes",
        "",
        None,
        12,
        "hi" + (" " * 63),
    ],
)
def test_non_greetings_and_requests_fall_through(text):
    assert match(text) is None


def test_policy_validation_and_user_rule_precedence_are_mandatory():
    assert match_unclaimed("hi", policy_match_ok=False, fixed_policy=None) is None
    assert match_unclaimed("hi", policy_match_ok=True, fixed_policy={"rule_id": "user"}) is None
    assert match_unclaimed("hi", policy_match_ok=True, fixed_policy=None)["reply"] == "Hi."


def test_text_guard_rejects_audio_and_audio_backed_transcript():
    assert is_text_only_event({"source_ref": {"modality": "text"}})
    assert not is_text_only_event({"source_ref": {"modality": "audio"}})
    assert not is_text_only_event({
        "source_ref": {"modality": "text"},
        "_audio_window": {"pcm16": b"\x00\x00"},
    })
    assert not is_text_only_event({"source_ref": None})
    assert not is_text_only_event(None)

# Exercise the staged Runtime patch independently of the full repository builder.
import importlib.util
from pathlib import Path

_overlay_path = Path(__file__).resolve().parents[1] / "scripts" / "integrated_greeting_fastpath_candidate_20261123.py"
_overlay_spec = importlib.util.spec_from_file_location("v14_greeting_overlay_test", _overlay_path)
assert _overlay_spec is not None and _overlay_spec.loader is not None
_overlay_module = importlib.util.module_from_spec(_overlay_spec)
_overlay_spec.loader.exec_module(_overlay_module)
_patch_worker_learning = _overlay_module._patch_worker_learning


def _run_worker_variant(worker_body):
    source = (
        "class Runtime:\n"
        "    def _worker(self, payload):\n"
        + worker_body
        + "    def _turn(self, payload):\n"
        "        self.turns += 1\n"
        "        return self.result\n"
        "    def online_world_update(self, limit=64):\n"
        "        self.updates += 1\n"
    ).encode("utf-8")
    patched = _patch_worker_learning(source)
    namespace = {}
    exec(compile(patched, "<staged-runtime>", "exec"), namespace)
    runtime = namespace["Runtime"]()
    runtime.turns = 0
    runtime.updates = 0
    runtime.result = {"skip_online_world_update": True}
    runtime._worker({})
    assert runtime.turns == 1
    assert runtime.updates == 0
    runtime.result = {}
    runtime._worker({})
    assert runtime.turns == 2
    assert runtime.updates == 1


def test_worker_guard_handles_unassigned_turn_result_and_keeps_normal_learning():
    _run_worker_variant(
        "        if True:\n"
        "            self._turn(payload)\n"
        "            try:self.online_world_update(limit=64)\n"
        "            except Exception as exc:\n"
        "                raise RuntimeError(type(exc).__name__)\n"
    )


def test_worker_guard_handles_existing_turn_result_capture_and_comments():
    _run_worker_variant(
        "        if True:\n"
        "            turn_result = self._turn(payload)\n"
        "            # Existing composed-runtime comments remain intact.\n"
        "            try:\n"
        "                self.online_world_update(limit=64)\n"
        "            except Exception as exc:\n"
        "                raise RuntimeError(type(exc).__name__)\n"
    )


def test_worker_guard_rejects_ambiguous_duplicate_turn_calls():
    source = (
        "class Runtime:\n"
        "    def _worker(self, payload):\n"
        "        self._turn(payload)\n"
        "        self._turn(payload)\n"
        "        try:self.online_world_update(limit=64)\n"
        "        except Exception:pass\n"
    ).encode("utf-8")
    with pytest.raises(ValueError, match="expected one _turn"):
        _patch_worker_learning(source)

