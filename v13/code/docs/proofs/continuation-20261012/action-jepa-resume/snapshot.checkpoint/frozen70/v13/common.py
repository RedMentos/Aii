import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import uuid
import unicodedata

APP = Path(__file__).resolve().parent.parent
def uid(prefix): return prefix + "_" + uuid.uuid4().hex
def now(): return time.time()
def dumps(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(v): return hashlib.sha256(v if isinstance(v,bytes) else v.encode()).hexdigest()
def file_hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def atomic_write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".pending-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data.encode() if isinstance(data,str) else data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        with contextlib.suppress(OSError):
            d=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(d)
            finally:os.close(d)
    finally:
        with contextlib.suppress(FileNotFoundError):os.unlink(tmp)
def safe_text(v):
    # Keep ordinary multilingual text and emoji. Terminal controls, malformed
    # Unicode surrogates and directional overrides must not disguise the UI.
    return "".join(c for c in str(v) if c in "\n\t" or (ord(c)>=32 and not 127<=ord(c)<=159 and not 0xD800<=ord(c)<=0xDFFF and not 0x202A<=ord(c)<=0x202E and not 0x2066<=ord(c)<=0x2069))
def visible_text(v):
    return any(not c.isspace() and unicodedata.category(c) not in {'Cc','Cf','Cs'} for c in str(v))
class Cancelled(RuntimeError): pass
class Unavailable(RuntimeError): pass
class Limits(RuntimeError): pass
