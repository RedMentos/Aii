import json, tempfile, unittest, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import bp_readiness as r


def _w(bs):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"bausteine": bs}, f); f.close(); return f.name


class T(unittest.TestCase):
    def test_not_ready(self):
        _, miss = r.check(_w([{"id": "BP1", "name": "a", "stand": "offen"}]))
        self.assertEqual(miss, ["BP1"])

    def test_ready(self):
        _, miss = r.check(_w([{"id": "BP1", "name": "a", "stand": "drin", "beleg": "x"}]))
        self.assertEqual(miss, [])

    def test_drin_needs_proof(self):
        with self.assertRaises(ValueError):
            r.check(_w([{"id": "BP1", "name": "a", "stand": "drin"}]))

    def test_shipped_status_is_valid_and_not_ready(self):
        rows, miss = r.check(pathlib.Path(r.__file__).resolve().parent.parent / "docs/bp-bereitschaft/status.json")
        self.assertEqual(len(rows), 12); self.assertIn("BP12", miss)


if __name__ == "__main__":
    unittest.main()
