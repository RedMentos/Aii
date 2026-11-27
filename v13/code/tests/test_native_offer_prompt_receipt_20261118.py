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

from v13.native_offer_prompt_receipt import (
    inspect, REVISION, VOLATILE_HEAD, TOKEN_SPAN_REVISION,
)
from v13.phone_offer_delivery_audit import audit
from v13.runners import LlamaRunner
from v13.prompts import text as prompt_text


HEADER = "Internal hypotheses: "
SECRET = "SECRET_NATIVE_QUOTE_DO_NOT_EXPORT"


def source_ref(text=SECRET):
    return {"source_id": "src", "sha256": "a" * 64, "char_start": 0,
            "char_end": len(text), "modality": "text"}


def offer(role, ident, quoted=True, text=SECRET):
    return {"role": role, "offer_packet_id": ident,
            "hypothesis": {"summary": "untrusted", "uncertainty": "low",
                           "needs_reentry": False},
            "verified_quotes": ([{"text": text, "source_ref": source_ref(text),
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


def render_with_special(msgs):
    return ("<|im_start|>system\n" + msgs[0]["content"] + "<|im_end|>\n"
            + "<|im_start|>user\n" + msgs[-1]["content"] + "<|im_end|>\n"
            + "<|im_start|>assistant\n")


def messages_ascii(offers):
    material = "\n" + HEADER + json.dumps(offers, ensure_ascii=True, sort_keys=True)
    return [{"role": "system", "content": "fixed rules" + material},
            {"role": "user", "content": "PRIVATE_CURRENT_USER"}]


def pieces_for_prompt(prompt, split_offsets=(), *, bos=True, special_markers=()):
    data = prompt.encode("utf-8")
    offsets = {0, len(data)}
    offsets.update(x for x in split_offsets if type(x) is int and 0 < x < len(data))
    for marker in special_markers:
        marker_bytes = marker.encode("utf-8")
        start = data.find(marker_bytes)
        while start >= 0:
            offsets.add(start)
            offsets.add(start + len(marker_bytes))
            start = data.find(marker_bytes, start + len(marker_bytes))
    ordered = sorted(offsets)
    rows = [{"id": 1, "piece": "<s>"}] if bos else []
    for index, (start, end) in enumerate(zip(ordered, ordered[1:])):
        chunk = data[start:end]
        try:
            piece = chunk.decode("utf-8")
        except UnicodeDecodeError:
            piece = list(chunk)
        rows.append({"id": 100 + index, "piece": piece})
    return rows


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


    def test_native_token_spans_bind_utf8_pieces_bos_and_special_tokens(self):
        selected = [
            offer("B1_DETAIL", "b1", text="source café 🤗 exact"),
            offer("B2_GIST", "b2", text="second naïve quote"),
        ]
        m = messages(selected)
        prompt = render_with_special(m)
        prompt_bytes = prompt.encode("utf-8")
        first_literal = json.dumps(selected[0]["verified_quotes"][0]["text"],
                                    ensure_ascii=False).encode("utf-8")
        second_literal = json.dumps(selected[1]["verified_quotes"][0]["text"],
                                     ensure_ascii=False).encode("utf-8")
        first_start = prompt_bytes.find(first_literal)
        second_start = prompt_bytes.find(second_literal, first_start + len(first_literal))
        self.assertGreaterEqual(first_start, 0)
        self.assertGreaterEqual(second_start, 0)
        cafe = prompt_bytes.find("é".encode("utf-8"), first_start)
        self.assertGreaterEqual(cafe, 0)
        rows = pieces_for_prompt(
            prompt,
            split_offsets=(first_start, cafe + 1, first_start + len(first_literal),
                           second_start, second_start + len(second_literal)),
            bos=False,
            special_markers=("<|im_start|>", "<|im_end|>"),
        )
        native_ids = [1] + [row["id"] for row in rows]
        result = inspect(m, prompt, HEADER, token_pieces=rows,
                         native_token_ids=native_ids)
        span = result["native_prompt_token_span_receipt"]
        self.assertEqual(result["status"], "RENDERED_WITH_QUOTES")
        self.assertEqual(span["revision"], TOKEN_SPAN_REVISION)
        self.assertEqual(span["status"], "VERIFIED")
        self.assertEqual(span["leading_added_special_token_count"], 1)
        self.assertEqual(span["trailing_added_special_token_count"], 0)
        self.assertEqual(span["token_count"], len(native_ids))
        self.assertEqual({x["role"] for x in span["offers"]},
                         {"B1_DETAIL", "B2_GIST"})
        first = next(x for x in span["offers"] if x["role"] == "B1_DETAIL")
        first_quote = first["quote_spans"][0]
        self.assertGreaterEqual(first_quote["token_start"], 1)
        self.assertGreaterEqual(first_quote["token_count"], 2)
        self.assertEqual(first_quote["first_token_byte_start"], 0)
        self.assertEqual(first_quote["last_token_byte_end"],
                         first_quote["last_token_piece_bytes"])
        self.assertGreater(first_quote["token_end_exclusive"], first_quote["token_start"])
        self.assertNotIn("source café", json.dumps(span))
        self.assertNotIn("second naïve", json.dumps(span))


    def test_native_token_spans_support_ascii_escaped_unicode_and_no_added_bos(self):
        selected = [
            offer("B1_DETAIL", "b1", text="naïve résumé"),
            offer("B2_GIST", "b2", text="plain summary"),
        ]
        m = messages_ascii(selected)
        prompt = render(m)
        data = prompt.encode("utf-8")
        literals = [json.dumps(x["verified_quotes"][0]["text"], ensure_ascii=True).encode("utf-8")
                    for x in selected]
        offsets = []
        cursor = 0
        for literal in literals:
            start = data.find(literal, cursor)
            self.assertGreaterEqual(start, 0)
            offsets.extend((start, start + len(literal)))
            cursor = start + len(literal)
        rows = pieces_for_prompt(prompt, split_offsets=offsets, bos=False)
        native_ids = [row["id"] for row in rows]
        result = inspect(m, prompt, HEADER, token_pieces=rows,
                         native_token_ids=native_ids)
        span = result["native_prompt_token_span_receipt"]
        self.assertEqual(span["status"], "VERIFIED")
        self.assertEqual(span["leading_added_special_token_count"], 0)
        self.assertEqual(span["trailing_added_special_token_count"], 0)
        self.assertEqual(len(span["offers"]), 2)


    def test_native_token_span_mismatch_partial_and_special_controls_fail_closed(self):
        selected = [offer("B1_DETAIL", "b1"), offer("B2_GIST", "b2")]
        m = messages(selected)
        prompt = render(m)
        prompt_bytes = prompt.encode("utf-8")
        first_literal = json.dumps(SECRET, ensure_ascii=False).encode("utf-8")
        literal_start = prompt_bytes.find(first_literal)
        self.assertGreaterEqual(literal_start, 0)

        rows = pieces_for_prompt(prompt, bos=False)
        rows[0]["piece"] = "mismatched"
        native_ids = [row["id"] for row in rows]
        result = inspect(m, prompt, HEADER, token_pieces=rows,
                         native_token_ids=native_ids)
        self.assertEqual(result["native_prompt_token_span_receipt"]["status"],
                         "TOKEN_PIECES_DO_NOT_RECONSTRUCT_PROMPT")

        partial = pieces_for_prompt(prompt, split_offsets=(literal_start + 1,), bos=False)
        partial_ids = [row["id"] for row in partial]
        result = inspect(m, prompt, HEADER, token_pieces=partial,
                         native_token_ids=partial_ids)
        self.assertEqual(result["native_prompt_token_span_receipt"]["status"],
                         "PARTIAL_TOKEN_BOUNDARY")

        clean = pieces_for_prompt(prompt, bos=False)
        content_ids = [row["id"] for row in clean]
        result = inspect(m, prompt, HEADER, token_pieces=[{"id": 7, "piece": prompt}],
                         native_token_ids=[7, 7])
        self.assertEqual(result["native_prompt_token_span_receipt"]["status"],
                         "AMBIGUOUS_OR_MISSING_CONTENT_TOKEN_SUBSEQUENCE")
        result = inspect(m, prompt, HEADER, token_pieces=clean,
                         native_token_ids=[1, 2, 3] + content_ids)
        self.assertEqual(result["native_prompt_token_span_receipt"]["status"],
                         "UNEXPECTED_SPECIAL_TOKEN_PREFIX_SUFFIX")

        fragment = "\n" + HEADER + json.dumps(selected, ensure_ascii=False, sort_keys=True)
        duplicate_prompt = prompt + fragment
        duplicate_rows = pieces_for_prompt(duplicate_prompt, bos=False)
        result = inspect(m, duplicate_prompt, HEADER, token_pieces=duplicate_rows,
                         native_token_ids=[row["id"] for row in duplicate_rows])
        self.assertEqual(result["native_prompt_token_span_receipt"]["status"],
                         "AMBIGUOUS_RENDERED_FRAGMENT")

        absent_prompt = prompt.replace(first_literal.decode("utf-8"), '"not-present"')
        absent = inspect(m, absent_prompt, HEADER,
                         token_pieces=pieces_for_prompt(absent_prompt, bos=False),
                         native_token_ids=[row["id"] for row in pieces_for_prompt(absent_prompt, bos=False)])
        self.assertEqual(absent["status"], "HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")


class FakeCompletionHandler(BaseHTTPRequestHandler):
    answer_status = 200
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        prompt = request.get("prompt")
        if isinstance(prompt, str):
            self.server.last_prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
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
                prompt = payload["content"]
                data = prompt.encode("utf-8")
                literal = json.dumps(SECRET, ensure_ascii=False).encode("utf-8")
                first = data.find(literal)
                second = data.find(literal, first + len(literal))
                offsets = (first, first + len(literal), second, second + len(literal))
                rows = pieces_for_prompt(prompt, split_offsets=offsets, bos=False)
                full_ids = [1] + [row["id"] for row in rows]
                return {"tokens": rows if payload.get("with_pieces") else full_ids}
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
        self.assertTrue(receipt["native_request_prompt_submitted"])
        self.assertTrue(receipt["native_request_prompt_matches_admission"])
        self.assertEqual(receipt["native_request_prompt_sha256"], self.server.last_prompt_sha256)
        span = receipt["native_prompt_token_span_receipt"]
        self.assertEqual(span["status"], "VERIFIED")
        self.assertEqual(span["leading_added_special_token_count"], 1)
        self.assertEqual(len(span["offers"]), 2)
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
        runner = {"role": "C3_LANGUAGE", "generated_tokens": tokens,
                  "prompt_tokens": 521, "timings": {"prompt_n": 500, "cache_n": 21}}
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
                "native_prompt_sha256": "a" * 64,
                "native_token_ids_sha256": "b" * 64,
                "native_prompt_tokens": 521,
                "native_request_prompt_sha256": "a" * 64,
                "native_request_prompt_submitted": True,
                "native_request_prompt_matches_admission": True,
                "source_span_revalidated_here": False,
                "native_semantic_use_proven": False,
                "offers": [{"role": r, "packet_id": pid, "rendered_quote_count": 1}
                           for r, pid in (("B1_DETAIL", "b1"), ("B2_GIST", "b2"))],
                "native_prompt_token_span_receipt": {
                    "revision": TOKEN_SPAN_REVISION, "status": "VERIFIED",
                    "prompt_sha256": "a" * 64, "token_ids_sha256": "b" * 64,
                    "token_count": 521, "leading_added_special_token_count": 1,
                    "trailing_added_special_token_count": 0,
                    "content_token_ids_sha256": "e" * 64,
                    "offers": [
                        {"role": "B1_DETAIL", "packet_id": "b1", "quote_spans": [{
                            "quote_index": 0, "source_sha256": "a" * 64,
                            "source_char_start": 0, "source_char_end": len(SECRET),
                            "prompt_byte_start": 100, "prompt_byte_end": 140,
                            "token_start": 5, "token_end_exclusive": 8, "token_count": 3,
                            "first_token_byte_start": 0, "last_token_byte_end": 4,
                            "first_token_piece_bytes": 10, "last_token_piece_bytes": 4,
                            "token_ids_sha256": "c" * 64}]},
                        {"role": "B2_GIST", "packet_id": "b2", "quote_spans": [{
                            "quote_index": 1, "source_sha256": "a" * 64,
                            "source_char_start": 0, "source_char_end": len(SECRET),
                            "prompt_byte_start": 200, "prompt_byte_end": 240,
                            "token_start": 9, "token_end_exclusive": 12, "token_count": 3,
                            "first_token_byte_start": 0, "last_token_byte_end": 5,
                            "first_token_piece_bytes": 8, "last_token_piece_bytes": 5,
                            "token_ids_sha256": "d" * 64}]},
                    ],
                }}

    def test_both_native_rendered_and_sent_is_still_metadata_only(self):
        self.seed(self.witness())
        out = audit(self.db)
        gate = out["end_to_end_gate"]
        self.assertEqual(gate["status"], "BOTH_BODY_NATIVE_PROMPT_INCLUSION_VERIFIED")
        self.assertEqual(gate["both_body_native_template_http200_reported_turns"], 1)
        self.assertEqual(gate["both_body_native_prompt_inclusion_verified_turns"], 1)
        self.assertTrue(gate["native_template_submission_reported_by_runtime"])
        self.assertTrue(gate["native_prompt_offer_inclusion_verified"])
        self.assertTrue(gate["native_prompt_token_span_receipt_verified"])
        self.assertEqual(gate["both_body_native_prompt_token_span_receipts_verified_turns"], 1)
        self.assertTrue(out["turns"][0]["native_prompt_token_span_receipt_verified"])
        self.assertEqual(set(out["turns"][0]["native_prompt_token_span_receipt_roles"]),
                         {"B1_DETAIL", "B2_GIST"})
        self.assertTrue(out["turns"][0]["c3_prompt_inclusion_proven"])
        self.assertFalse(out["turns"][0]["c3_semantic_use_proven"])
        self.assertFalse(gate["learned_latent_exchange_verified"])
        self.assertNotIn(SECRET, json.dumps(out))


    def test_prompt_inclusion_requires_exact_request_hash_and_prefill_count(self):
        for change in ("request_hash_mismatch", "request_not_submitted",
                       "admission_mismatch", "prefill_count_mismatch"):
            with self.subTest(change=change):
                self.db.execute("DELETE FROM messages")
                self.db.execute("DELETE FROM packets")
                self.db.execute("DELETE FROM telemetry")
                self.seed(self.witness())
                raw = self.db.execute(
                    "SELECT metadata FROM messages WHERE event_id=?", ("E",)
                ).fetchone()[0]
                metadata = json.loads(raw)
                witness = metadata["runner"]["native_offer_prompt_receipt"]
                if change == "request_hash_mismatch":
                    witness["native_request_prompt_sha256"] = "b" * 64
                elif change == "request_not_submitted":
                    witness["native_request_prompt_submitted"] = False
                elif change == "admission_mismatch":
                    witness["native_request_prompt_matches_admission"] = False
                elif change == "prefill_count_mismatch":
                    metadata["runner"]["timings"]["prompt_n"] = 499
                self.db.execute(
                    "UPDATE messages SET metadata=? WHERE event_id=?",
                    (json.dumps(metadata), "E"),
                )
                out = audit(self.db)
                gate = out["end_to_end_gate"]
                self.assertEqual(gate["both_body_native_template_http200_reported_turns"], 1)
                self.assertFalse(gate["native_prompt_offer_inclusion_verified"])
                self.assertFalse(out["turns"][0]["c3_prompt_inclusion_proven"])
                self.assertFalse(gate["learned_latent_exchange_verified"])

    def test_native_prompt_token_span_audit_rejects_mismatch_and_bad_bounds(self):
        for change in ("prompt_hash", "token_hash", "token_count", "token_start",
                       "missing_role", "quote_count", "malformed_role",
                       "partial_boundary", "overlap_prompt", "overlap_tokens"):
            with self.subTest(change=change):
                self.db.execute("DELETE FROM messages")
                self.db.execute("DELETE FROM packets")
                self.db.execute("DELETE FROM telemetry")
                self.seed(self.witness())
                raw = self.db.execute(
                    "SELECT metadata FROM messages WHERE event_id=?", ("E",)
                ).fetchone()[0]
                metadata = json.loads(raw)
                span = metadata["runner"]["native_offer_prompt_receipt"][
                    "native_prompt_token_span_receipt"]
                if change == "prompt_hash":
                    span["prompt_sha256"] = "e" * 64
                elif change == "token_hash":
                    span["token_ids_sha256"] = "e" * 64
                elif change == "token_count":
                    span["token_count"] = 520
                elif change == "token_start":
                    span["offers"][0]["quote_spans"][0]["token_start"] = 521
                elif change == "missing_role":
                    span["offers"].pop()
                elif change == "quote_count":
                    span["offers"][0]["quote_spans"].pop()
                elif change == "malformed_role":
                    span["offers"][0]["role"] = []
                elif change == "partial_boundary":
                    span["offers"][0]["quote_spans"][0]["first_token_byte_start"] = 1
                elif change == "overlap_prompt":
                    span["offers"][1]["quote_spans"][0]["prompt_byte_start"] = 120
                elif change == "overlap_tokens":
                    span["offers"][1]["quote_spans"][0]["token_start"] = 7
                    span["offers"][1]["quote_spans"][0]["token_end_exclusive"] = 10
                    span["offers"][1]["quote_spans"][0]["token_count"] = 3
                self.db.execute(
                    "UPDATE messages SET metadata=? WHERE event_id=?",
                    (json.dumps(metadata), "E"),
                )
                out = audit(self.db)
                self.assertFalse(out["turns"][0]["native_prompt_token_span_receipt_verified"])
                self.assertFalse(out["end_to_end_gate"]["native_prompt_token_span_receipt_verified"])


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
