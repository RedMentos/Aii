"""No-model native C3 transport witness and event-bound SQLite audit tests.

Uses a disposable loopback HTTP server. No owner content or GGUF is involved.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from v13.native_offer_prompt_receipt import inspect, REVISION, VOLATILE_HEAD
from v13.phone_offer_delivery_audit import audit
from v13.runners import LlamaRunner
from v13.prompts import text as prompt_text


HEADER = "Internal hypotheses: "
SECRET = "SECRET_NATIVE_QUOTE_DO_NOT_EXPORT"


def source_ref():
    return {"source_id": "src", "sha256": "a" * 64, "char_start": 0,
            "char_end": len(SECRET), "modality": "text"}


def offer(role, ident, quoted=True):
    return {"role": role, "offer_packet_id": ident,
            "hypothesis": {"summary": "untrusted", "uncertainty": "low",
                           "needs_reentry": False},
            "verified_quotes": ([{"text": SECRET, "source_ref": source_ref(),
                                 "verification": "EXACT_SOURCE_SUBSTRING_ONLY"}]
                                if quoted else [])}


def messages(offers, *, layout="legacy"):
    material = "\n" + HEADER + json.dumps(offers, ensure_ascii=False, sort_keys=True)
    if layout == "legacy":
        return [{"role": "system", "content": "fixed rules" + material},
                {"role": "user", "content": "PRIVATE_CURRENT_USER"}]
    return [{"role": "system", "content": "fixed rules"},
            {"role": "user", "content": VOLATILE_HEAD + material},
            {"role": "user", "content": "PRIVATE_CURRENT_USER"}]


def render(msgs):
    return "<START>" + "".join(x["content"] for x in msgs) + "<ASSISTANT>"


class PurePromptReceipt(unittest.TestCase):
    def test_legacy_and_active_volatile_are_bound_to_native_template(self):
        selected = [offer("B1_DETAIL", "b1"), offer("B2_GIST", "b2")]
        for layout in ("legacy", "active"):
            with self.subTest(layout=layout):
                m = messages(selected, layout=layout)
                receipt = inspect(m, render(m), HEADER)
                self.assertEqual(receipt["status"], "RENDERED_WITH_QUOTES")
                self.assertEqual([r["packet_id"] for r in receipt["offers"]], ["b1", "b2"])
                self.assertEqual([r["rendered_quote_count"] for r in receipt["offers"]], [1, 1])
                self.assertTrue(receipt["native_template_rendered"])
                self.assertNotIn(SECRET, json.dumps(receipt))
                self.assertNotIn("PRIVATE_CURRENT_USER", json.dumps(receipt))

    def test_no_hypotheses_and_unquoted_offer_do_not_promote(self):
        no = [{"role": "system", "content": "fixed"},
              {"role": "user", "content": SECRET}]
        self.assertEqual(inspect(no, render(no), HEADER)["status"], "NO_TYPED_HYPOTHESES")
        m = messages([offer("B1_DETAIL", "b1", quoted=False)])
        self.assertEqual(inspect(m, render(m), HEADER)["status"],
                         "RENDERED_WITH_UNQUOTED_OFFER")

    def test_omitted_native_section_and_history_spoof_fail(self):
        selected = [offer("B1_DETAIL", "b1")]
        m = messages(selected)
        self.assertEqual(inspect(m, "<START>PRIVATE_CURRENT_USER", HEADER)["status"],
                         "HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")
        fake = [{"role": "system", "content": "fixed"},
                {"role": "user", "content": m[0]["content"]},
                {"role": "assistant", "content": "answer"},
                {"role": "user", "content": "PRIVATE_CURRENT_USER"}]
        self.assertEqual(inspect(fake, render(fake), HEADER)["status"],
                         "NO_TYPED_HYPOTHESES")

    def test_unverified_or_inconsistent_source_quotes_do_not_count_as_rendered(self):
        original = offer("B1_DETAIL", "b1")
        for mutation in ("hash", "empty_source", "wrong_span", "unverified"):
            with self.subTest(mutation=mutation):
                candidate = json.loads(json.dumps(original))
                quote = candidate["verified_quotes"][0]
                ref = quote["source_ref"]
                if mutation == "hash":
                    ref["sha256"] = "not-a-hash"
                elif mutation == "empty_source":
                    ref["source_id"] = ""
                elif mutation == "wrong_span":
                    ref["char_end"] += 1
                else:
                    quote["verification"] = "MODEL_GUESSED"
                m = messages([candidate])
                self.assertEqual(inspect(m, render(m), HEADER)["status"],
                                 "INVALID_SELECTED_QUOTES")

    def test_widened_source_verified_by_existing_analyst_consumer_is_rendered(self):
        # cognition.analyst_context checks the source span and quote_span before
        # emitting this distinct marker. The receipt does not re-read sources.
        selected = offer("B1_DETAIL", "b1")
        selected["verified_quotes"][0]["verification"] = "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE"
        m = messages([selected])
        result = inspect(m, render(m), HEADER)
        self.assertEqual(result["status"], "RENDERED_WITH_QUOTES")
        self.assertFalse(result["source_span_revalidated_here"])
        self.assertFalse(result["native_semantic_use_proven"])
        self.assertNotIn(SECRET, json.dumps(result))

    def test_duplicated_role_id_malformed_or_untrusted_shape_fail(self):
        m = messages([offer("B1_DETAIL", "b1"), offer("B1_DETAIL", "b2")])
        self.assertEqual(inspect(m, render(m), HEADER)["status"], "INVALID_SELECTED_OFFERS")
        m = messages([offer("B1_DETAIL", "b1"), offer("B2_GIST", "b1")])
        self.assertEqual(inspect(m, render(m), HEADER)["status"], "INVALID_SELECTED_OFFERS")
        m = messages([offer("B1_DETAIL", "b1")])
        m[0]["content"] += "\n" + HEADER + "[]"
        self.assertEqual(inspect(m, render(m), HEADER)["status"], "AMBIGUOUS_HYPOTHESES")
        m = messages([offer("B1_DETAIL", "b1")])
        m[0]["content"] = m[0]["content"].replace('"char_start": 0', '"char_start": false')
        self.assertEqual(inspect(m, render(m), HEADER)["status"], "INVALID_SELECTED_QUOTES")
        self.assertEqual(inspect([{"role": "user", "content": "x"}],
                                 "x", HEADER)["status"], "INVALID_ENVELOPE")


class FakeCompletionHandler(BaseHTTPRequestHandler):
    answer_status = 200
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(self.answer_status)
        self.send_header("Content-Type", "text/event-stream")
        if self.answer_status == 200:
            payload = b'data: {"content":"ok","tokens":[17],"stop":true}\n\n'
        else:
            payload = b"native error"
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def log_message(self, *_):
        pass


class NativeHTTPBound(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeCompletionHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def runner(self):
        r = LlamaRunner.__new__(LlamaRunner)
        r.purpose = "generate"
        r.role = "C3_LANGUAGE"
        r.model = SimpleNamespace(name="synthetic-gguf-placeholder")
        r.cfg = {"answer_tokens": 64, "context_tokens": 2048,
                 "temperature": .1, "c3_sampling": "normal",
                 "offer_logprobs": False, "native_memory_audit": False}
        r.proc = None
        r.port = self.server.server_address[1]
        r.key = "synthetic-key"
        r._audit_enabled = False
        r.load = lambda cancel, deadline: None
        # A fabricated __new__ fixture has no real process/log to release.
        r.unload = lambda: {"process_reaped": True, "was_loaded": False}
        def post(method, endpoint, payload, deadline, **kwargs):
            if endpoint == "/apply-template":
                return {"prompt": render(payload["messages"])}
            if endpoint == "/tokenize":
                return {"tokens": [1] * 24}
            raise AssertionError(endpoint)
        r._json = post
        return r

    def test_actual_loopback_http_200_sets_receipt_only_after_template(self):
        runner = self.runner()
        m = messages([offer("B1_DETAIL", "b1"), offer("B2_GIST", "b2")])
        output = "".join(runner.generate(m, threading.Event(), time.monotonic() + 20))
        self.assertEqual(output, "ok")
        self.assertEqual(runner.last_metrics["generated_tokens"], 1)
        receipt = runner.last_metrics["native_offer_prompt_receipt"]
        self.assertEqual(receipt["status"], "RENDERED_WITH_QUOTES")
        self.assertTrue(receipt["native_template_submitted"])
        self.assertTrue(receipt["native_completion_http_200"])
        self.assertEqual(runner.last_metrics["status"], "FINAL")
        self.assertNotIn(SECRET, json.dumps(runner.last_metrics))
        self.assertNotIn("PRIVATE_CURRENT_USER", json.dumps(runner.last_metrics))

    def test_rejected_http_call_does_not_report_success(self):
        class Rejected(FakeCompletionHandler):
            answer_status = 500
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Rejected)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        runner = self.runner()
        with self.assertRaises(RuntimeError):
            list(runner.generate(messages([offer("B1_DETAIL", "b1")]),
                                 threading.Event(), time.monotonic() + 20))
        receipt = runner.last_metrics["native_offer_prompt_receipt"]
        self.assertFalse(receipt["native_completion_http_200"])
        self.assertFalse(receipt["native_template_submitted"])


class InstalledStageWitness(unittest.TestCase):
    def test_actual_composed_stage_contains_instrumented_runner_and_helper(self):
        code = Path(__file__).resolve().parents[1]
        stager_path = code / "scripts" / "stage_integrated_candidate.py"
        spec = importlib.util.spec_from_file_location("v13_prompt_witness_stage", stager_path)
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        with tempfile.TemporaryDirectory(prefix="v13-native-witness-stage-") as tmp:
            target = Path(tmp) / "code"
            stager.stage(code, target)
            for relative in ("v13/runners.py", "v13/native_offer_prompt_receipt.py",
                             "v13/phone_offer_delivery_audit.py"):
                source = code / relative
                copied = target / relative
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                                 hashlib.sha256(copied.read_bytes()).hexdigest())
            statement = """from pathlib import Path
from v13 import runners, native_offer_prompt_receipt as witness
base=Path.cwd().resolve()
assert Path(runners.__file__).resolve().is_relative_to(base)
assert Path(witness.__file__).resolve().is_relative_to(base)
assert 'native_offer_prompt_receipt' in Path(runners.__file__).read_text()
assert witness.inspect([{'role':'system','content':'safe'}, {'role':'user','content':'hi'}],
                       'safe hi','Internal hypotheses: ')['status']=='NO_TYPED_HYPOTHESES'
"""
            process = subprocess.run([sys.executable, "-P", "-c", statement],
                                     cwd=target,
                                     env=dict(os.environ, PYTHONPATH=str(target),
                                              PYTHONDONTWRITEBYTECODE="1"),
                                     capture_output=True, text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


class SQLiteNativeAudit(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE messages(id INTEGER PRIMARY KEY, event_id TEXT,
                status TEXT, metadata TEXT, role TEXT, text TEXT);
            CREATE TABLE packets(id TEXT PRIMARY KEY, event_id TEXT,
                kind TEXT, payload TEXT);
            CREATE TABLE telemetry(id INTEGER PRIMARY KEY, event_id TEXT,
                kind TEXT, metrics TEXT);
        """)

    def tearDown(self):
        self.db.close()

    def seed(self, witness=None, *, selected=("b1", "b2"), tokens=10):
        runner = {"role": "C3_LANGUAGE", "generated_tokens": tokens}
        if witness is not None:
            runner["native_offer_prompt_receipt"] = witness
        self.db.execute(
            "INSERT INTO messages(event_id,status,metadata,role,text) VALUES(?,?,?,?,?)",
            ("E", "FINAL", json.dumps({"selected_offer_ids": list(selected),
                                       "runner": runner}), "assistant", SECRET))
        for role, pid in (("B1_DETAIL", "b1"), ("B2_GIST", "b2")):
            self.db.execute("INSERT INTO packets(id,event_id,kind,payload) VALUES(?,?,?,?)",
                            (pid, "E", "OfferPacket", json.dumps(
                                {"role": role, "evidence_refs": [source_ref()]})))
            self.db.execute("INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)",
                            ("E", "body_offer_delivered",
                             json.dumps({"role": role, "packet_id": pid})))

    def witness(self):
        return {"revision": REVISION, "status": "RENDERED_WITH_QUOTES",
                "native_template_rendered": True,
                "native_template_submitted": True, "native_completion_http_200": True,
                "source_span_revalidated_here": False,
                "native_semantic_use_proven": False,
                "offers": [{"role": r, "packet_id": pid, "rendered_quote_count": 1}
                           for r, pid in (("B1_DETAIL", "b1"), ("B2_GIST", "b2"))]}

    def test_both_native_rendered_and_sent_is_still_metadata_only(self):
        self.seed(self.witness())
        out = audit(self.db)
        gate = out["end_to_end_gate"]
        self.assertEqual(gate["status"], "BOTH_BODY_NATIVE_TEMPLATE_HTTP200_REPORTED")
        self.assertEqual(gate["both_body_native_template_http200_reported_turns"], 1)
        self.assertTrue(gate["native_template_submission_reported_by_runtime"])
        self.assertFalse(gate["native_prompt_offer_inclusion_verified"])
        self.assertFalse(gate["learned_latent_exchange_verified"])
        self.assertNotIn(SECRET, json.dumps(out))

    def test_wrong_packet_boolean_token_no_http_or_no_witness_never_promote(self):
        for change in ("wrong_packet", "bool_quotes", "no_http", "no_witness", "no_tokens"):
            with self.subTest(change=change):
                self.db.execute("DELETE FROM messages")
                self.db.execute("DELETE FROM packets")
                self.db.execute("DELETE FROM telemetry")
                witness = self.witness()
                tokens = 0 if change == "no_tokens" else 10
                if change == "wrong_packet":
                    witness["offers"][0]["packet_id"] = "other"
                elif change == "bool_quotes":
                    witness["offers"][0]["rendered_quote_count"] = True
                elif change == "no_http":
                    witness["native_completion_http_200"] = False
                elif change == "no_witness":
                    witness = None
                self.seed(witness, tokens=tokens)
                out = audit(self.db)
                self.assertEqual(
                    out["end_to_end_gate"]["both_body_native_template_http200_reported_turns"], 0)
                self.assertFalse(out["end_to_end_gate"]["native_template_submission_reported_by_runtime"])


if __name__ == "__main__":
    unittest.main()
