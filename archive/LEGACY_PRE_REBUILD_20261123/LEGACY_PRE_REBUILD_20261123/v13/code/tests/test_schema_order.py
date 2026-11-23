"""WP-W1: JSON schemas reach llama-server in their original key order (grammar follows property order)."""
import json
from pathlib import Path
import time
import unittest
from unittest import mock

from v13 import runners
from v13.cognition import OFFER_SCHEMA, offer_schema


class FakeResponse:
    status = 200

    def read(self, *a):
        return b'{"ok":true}'


class FakeConn:
    sent = []

    def __init__(self, *a, **k):
        pass

    def request(self, method, path, body, headers):
        FakeConn.sent.append(body)

    def getresponse(self):
        return FakeResponse()

    def close(self):
        pass


class SchemaOrderTests(unittest.TestCase):
    def test_wire_json_keeps_order_and_common_dumps_still_sorts(self):
        doc = {'properties': {'options': 1, 'action': 2}}
        self.assertEqual(runners.wire_json(doc), '{"properties":{"options":1,"action":2}}')
        self.assertEqual(runners.dumps(doc), '{"properties":{"action":2,"options":1}}')

    def test_runner_request_body_keeps_offer_property_order(self):
        runner = runners.LlamaRunner.__new__(runners.LlamaRunner)
        runner.port, runner.key = 1, 'k'
        FakeConn.sent = []
        payload = {'prompt': 'x', 'json_schema': offer_schema(96)}
        with mock.patch.object(runners.http.client, 'HTTPConnection', FakeConn):
            runner._json('POST', '/completion', payload, time.monotonic() + 5)
        sent = json.loads(FakeConn.sent[0])
        self.assertEqual(list(sent['json_schema']['properties']), list(OFFER_SCHEMA['properties']))
        self.assertEqual(list(sent['json_schema']['properties'])[0], 'summary')

    def test_no_sorted_serialisation_on_the_wire(self):
        src = Path(runners.__file__).read_text()
        self.assertNotIn('conn.request("POST","/completion",dumps(', src)
        self.assertNotIn("conn.request('POST','/completion',dumps(", src)
        self.assertNotIn('conn.request(method,path,dumps(', src)


if __name__ == '__main__':
    unittest.main()
