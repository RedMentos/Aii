"""Synthetic consumer regression only; not Android/native latent receiver proof."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from v13.cognition import Cognition

class TapReadIntegrity(unittest.TestCase):
    def test_read_tap_rejects_corrupt_native_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); blob=home/'data'/'blobs';blob.mkdir(parents=True)
            path=blob/'tap.json'
            packet={'packet_id':'tap-test','source_ref':{'source_id':'source-test'},
                    'feature_path':'data/blobs/tap.json','feature_sha256':'synthetic',
                    'token_ids':[7],'shape':[1,2]}
            store=SimpleNamespace(one=lambda *args:{'payload':json.dumps(packet)},
                                  read_source=lambda ref:'source')
            reader=Cognition(SimpleNamespace(store=store,home=home))
            def attempt(data,shape=None):
                path.write_text(json.dumps(data))
                if shape is not None:packet['shape']=shape
                with patch('v13.cognition.file_hash',return_value='synthetic'):
                    return reader.read_tap(packet)
            self.assertEqual(attempt({'token_ids':[7],'vectors':[[.1,.2]]})['token_ids'],[7])
            for bad in (
                {'token_ids':[7],'vectors':[[float('nan'),.2]]},
                {'token_ids':[7],'vectors':[[float('inf'),.2]]},
                {'token_ids':[7],'vectors':[['0.1',.2]]},
                {'token_ids':[7,8],'vectors':[[.1,.2]]},
                {'token_ids':[7],'vectors':[[.1]]},
                {'token_ids':[7],'vectors':{'x':1}},
            ):
                with self.subTest(bad=str(bad)),self.assertRaises(ValueError):
                    attempt(bad)
            with self.assertRaises(ValueError):
                attempt({'token_ids':[7],'vectors':[[.1,.2]]},[1,1000000])

if __name__=='__main__':unittest.main()
