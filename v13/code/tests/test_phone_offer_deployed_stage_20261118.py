"""Verify the staged/installed V13 snapshot contains the corrected B1/B2 audit.

No models, real-phone access, automatic release or external data. This
simulates the actual stage composer rather than importing the raw source.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]


class DeployedPhoneAudit(unittest.TestCase):
    def test_composed_runtime_keeps_receipt_attribution_and_never_claims_latent_proof(self):
        builder = CODE / "scripts" / "stage_integrated_candidate.py"
        spec = importlib.util.spec_from_file_location("v13_phone_audit_stage", builder)
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        with tempfile.TemporaryDirectory(prefix="v13-phone-audit-stage-") as tmp:
            dest = Path(tmp) / "release"
            stager.stage(CODE, dest)
            original = CODE / "v13" / "phone_offer_delivery_audit.py"
            installed = dest / "v13" / "phone_offer_delivery_audit.py"
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                             hashlib.sha256(installed.read_bytes()).hexdigest())
            # The subprocess imports solely from the materialized stage, not
            # from the developer's source PYTHONPATH or Python module cache.
            script = """
import json, sqlite3
from pathlib import Path
from v13 import phone_offer_delivery_audit as a
assert Path(a.__file__).resolve().is_relative_to(Path.cwd().resolve())
db = sqlite3.connect(':memory:')
db.executescript('''
CREATE TABLE messages(id INTEGER PRIMARY KEY,event_id TEXT,status TEXT,metadata TEXT,role TEXT,text TEXT);
CREATE TABLE packets(id TEXT PRIMARY KEY,event_id TEXT,kind TEXT,payload TEXT);
CREATE TABLE telemetry(id INTEGER PRIMARY KEY,event_id TEXT,kind TEXT,metrics TEXT);
''')
db.execute('INSERT INTO messages(event_id,status,metadata,role,text) VALUES(?,?,?,?,?)',
           ('synthetic','FINAL',json.dumps({'selected_offer_ids':['b1','b2'],
             'runner':{'role':'C3_LANGUAGE','generated_tokens':4}}),
            'assistant','PRIVATE_SYNTHETIC'))
for role,pid in (('B1_DETAIL','b1'),('B2_GIST','b2')):
    db.execute('INSERT INTO packets(id,event_id,kind,payload) VALUES(?,?,?,?)',
               (pid,'synthetic','OfferPacket',json.dumps({'role':role,
               'offer':{'summary':'PRIVATE_SYNTHETIC'},'evidence_refs':[]})))
db.execute('INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)',
           ('synthetic','body_offer_delivered',json.dumps({'role':'B1_DETAIL','packet_id':'b1'})))
r = a.audit(db)
assert r['turns'][0]['roles']['B1_DETAIL']['delivery']=='IN_FINAL_C3_REPORT',r
assert r['turns'][0]['roles']['B2_GIST']['delivery']=='SELECTED_WITHOUT_DELIVERY_RECEIPT',r
assert r['end_to_end_gate']['status']=='B1_B2_TO_C3_CHAIN_NOT_OBSERVED',r
assert r['end_to_end_gate']['native_prompt_offer_inclusion_verified'] is False,r
assert r['end_to_end_gate']['learned_latent_exchange_verified'] is False,r
assert 'PRIVATE_SYNTHETIC' not in json.dumps(r)
"""
            env = dict(os.environ, PYTHONPATH=str(dest),
                       PYTHONDONTWRITEBYTECODE="1", NO_MODEL_DOWNLOADS="1")
            process = subprocess.run(
                [sys.executable, "-P", "-c", script],
                cwd=dest, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
