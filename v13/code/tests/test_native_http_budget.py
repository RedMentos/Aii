"""Real loopback HTTP budgets; these are transport tests, not model proofs."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from v13.common import Limits
from v13.runners import LlamaRunner

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        time.sleep(.12)
        try:
            self.send_response(200);self.end_headers();self.wfile.write(b'{"transport":true}')
        except (BrokenPipeError,ConnectionResetError):pass

class NativeHttpBudget(unittest.TestCase):
    def test_long_prefill_transport_uses_remaining_budget_and_still_expires(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                h=Path(folder);r=LlamaRunner(h,'C3_LANGUAGE',h/'not-a-model',{})
                r.port=server.server_address[1]
                with self.assertRaises(socket.timeout):r._json('POST','/embeddings',{},time.monotonic()+1,timeout_cap=.03)
                self.assertEqual(r._json('POST','/embeddings',{},time.monotonic()+1,timeout_cap=None),{'transport':True})
                with self.assertRaises(socket.timeout):r._json('POST','/embeddings',{},time.monotonic()+.03,timeout_cap=None)
                with self.assertRaises(Limits):r._json('POST','/embeddings',{},time.monotonic()-1,timeout_cap=None)
        finally:server.shutdown();server.server_close();thread.join(1)

if __name__=='__main__':unittest.main()
