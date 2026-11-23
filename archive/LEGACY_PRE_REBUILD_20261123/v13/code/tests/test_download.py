import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from v13.models import download_file
class Downloads(unittest.TestCase):
    def test_resume_and_corrupt_existing_replaced(self):
        payload=b'real file content\x00'*8192;seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                start=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);seen.append(start)
                self.send_response(206 if start else 200)
                if start:self.send_header('Content-Range',f'bytes {start}-{len(payload)-1}/{len(payload)}')
                self.send_header('Content-Length',str(len(payload)-start));self.end_headers();self.wfile.write(payload[start:])
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'model';p.write_bytes(b'x'*len(payload));p.with_suffix('.partial').write_bytes(payload[:5000]);spec={'url':f'http://127.0.0.1:{server.server_port}/file','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
                download_file(spec,p,lambda _:None);self.assertEqual(p.read_bytes(),payload);self.assertEqual(seen,[5000]);self.assertFalse(p.with_suffix('.partial').exists())
                download_file(spec,p,lambda _:None);self.assertEqual(seen,[5000])
        finally:server.shutdown();server.server_close();thread.join()
    def test_wrong_hash_never_activates(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'bad!')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'model'
                with self.assertRaises(RuntimeError):download_file({'url':f'http://127.0.0.1:{server.server_port}/file','size':4,'sha256':'0'*64},p,lambda _:None)
                self.assertFalse(p.exists())
        finally:server.shutdown();server.server_close();thread.join()
