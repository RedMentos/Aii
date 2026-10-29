"""P2X frozen training16 schema-toggle source/synthetic tests; never native proof."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_schema_toggle_train16 as M


def request(mode, prompt):
    payload = {"prompt": prompt, "n_predict": M.candidate.MAX_TOKENS,
               "stream": False, "temperature": .1, "top_k": 50,
               "repeat_penalty": 1.05, "seed": M.scorer.SEED,
               "cache_prompt": True, "id_slot": 0, "return_tokens": True}
    if mode == "on":
        payload["json_schema"] = M.candidate.hb1.C3_SCHEMA
    return payload


def synthetic():
    prompts, answers = M.plan()
    oracle = {a["id"]: a["target_action"] for a in answers}
    records = [
        M.candidate.record_call(
            p, json.dumps({"action": oracle[p["id"]]}), .01,
            {"status": "FINAL", "schema_mode": p["arm"],
             "completion_request": request(p["arm"], p["id"])},
            M.ADAPTER_SHA)
        for p in prompts
    ]
    return prompts, answers, records


class SchemaToggleTrainingOnly(unittest.TestCase):
    def test_exact_balanced_frozen_training_only_plan(self):
        p, a = M.plan()
        self.assertEqual((len(p), len(a)), (32, 16))
        self.assertEqual([x["arm"] for x in p], ["on"] * 16 + ["off"] * 16)
        self.assertEqual([x["messages"] for x in p[:16]],
                         [x["messages"] for x in p[16:]])
        self.assertEqual({v: sum(x["target_action"] == v for x in a)
                          for v in M.base.resources.LABELS},
                         dict.fromkeys(M.base.resources.LABELS, 4))
        self.assertEqual({x["id"] for x in p}, {x["id"] for x in a})

    def test_one_factor_request_mutation_only(self):
        original = M.candidate.LocalServer.request
        captured = []
        def fake_request(self, method, path, data=None, timeout=None):
            captured.append((method, path, data))
            return {"content": "ok"}
        with patch.object(M.candidate.LocalServer, "request", fake_request):
            for mode in M.MODES:
                s = object.__new__(M.SchemaServer)
                s.mode = mode
                s.completion_request = None
                s.request("POST", "/completion", request("on", "prompt"))
        self.assertEqual(captured[0][2], request("on", "prompt"))
        self.assertEqual(captured[1][2], request("off", "prompt"))
        self.assertEqual(captured[0][2].keys() - captured[1][2].keys(),
                         {"json_schema"})

    def test_synthetic_positive_control_no_gate(self):
        p, a, rows = synthetic()
        result = M.score(rows, p, a)
        self.assertEqual(result["correct_strict_in_sample"], {"on": 16, "off": 16})
        self.assertEqual(result["paired_strict_action_changes"], 0)
        self.assertEqual(result["unparseable_bare_label_only"], {"on": 0, "off": 0})
        self.assertEqual(result["native_calls"], 32)
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["ag6_approved"])
        self.assertFalse(result["whole_system_complete"])

    def test_unconstrained_bare_label_is_not_counted_as_structured_success(self):
        p, a, rows = synthetic()
        rows[16]["output"] = a[0]["target_action"]
        result = M.score(rows, p, a)
        self.assertEqual(result["correct_strict_in_sample"]["off"], 15)
        self.assertEqual(result["unparseable_bare_label_only"]["off"], 1)
        self.assertEqual(result["per_label"]["off"][a[0]["target_action"]]["unparseable"], 1)

    def test_rejects_schema_mode_swap_and_extra_request_setting(self):
        p, a, rows = synthetic()
        rows[16]["metrics"]["completion_request"]["json_schema"] = M.candidate.hb1.C3_SCHEMA
        with self.assertRaisesRegex(ValueError, "SCHEMA_OFF"):
            M.score(rows, p, a)
        p, a, rows = synthetic()
        rows[16]["metrics"]["completion_request"]["temperature"] = .9
        with self.assertRaisesRegex(ValueError, "REQUEST_SETTINGS"):
            M.score(rows, p, a)
        p, a, rows = synthetic()
        rows[16]["metrics"]["completion_request"]["extra"] = "unregistered"
        with self.assertRaisesRegex(ValueError, "NONSCHEMA_REQUEST_DIFFERENCE"):
            M.score(rows, p, a)

    def test_rejects_duplicate_or_wrong_adapter_and_tampered_cohort(self):
        p, a, rows = synthetic()
        rows[1] = rows[0].copy()
        with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
            M.score(rows, p, a)
        p, a, rows = synthetic()
        rows[0]["adapter_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
            M.score(rows, p, a)
        p, a, rows = synthetic()
        p[0]["messages"][0]["content"] += " target_action:B"
        with self.assertRaisesRegex(ValueError, "FROZEN_PLAN"):
            M.score(rows, p, a)

    def test_preflight_refuses_missing_native_assets(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            with self.assertRaisesRegex(ValueError, "BINARY_FILE"):
                M.preflight(d / "missing", d / "runtime", d / "model",
                            d / "adapter", d / "new")

    def test_synthetic_owned_loopback_replay_and_tamper(self):
        p, a = M.plan()
        oracle = {x["id"]: x["target_action"] for x in a}
        class FakeServer:
            def __init__(self, binary, model, adapter, log, mode):
                self.mode = mode
                self.proc = None
            def generate(self, messages, timeout):
                ident = next(x["id"] for x in p if x["messages"] == messages)
                return json.dumps({"action": oracle[ident]}), {
                    "status": "FINAL", "schema_mode": self.mode,
                    "completion_request": request(self.mode, ident)}
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            with patch.object(M, "preflight", return_value=(
                    d / "binary", d / "model", d / "adapter", p, a,
                    {"synthetic": True})), patch.object(
                        M.candidate, "admit_file", side_effect=lambda path, *args: Path(path)):
                receipt = M.run_native(d / "binary", d / "runtime", d / "model",
                                       d / "adapter", d / "out",
                                       server_factory=FakeServer)
                self.assertEqual(receipt["recorded_calls"], 32)
                self.assertEqual(M.verify(d / "out")["correct_strict_in_sample"],
                                 {"on": 16, "off": 16})
                rows = json.loads((d / "out" / "RAW.json").read_text())
                rows[0]["metrics"]["schema_mode"] = "off"
                (d / "out" / "RAW.json").write_text(json.dumps(rows))
                with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
                    M.verify(d / "out")


if __name__ == "__main__":
    unittest.main()
