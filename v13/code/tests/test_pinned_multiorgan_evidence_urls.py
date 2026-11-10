"""Negative controls for CI URL parsing; syntax is not remote CI verification."""
import copy
import unittest
from scripts.pinned_multiorgan_evidence import check

SHA = "a" * 40
URL = "https://github.com/RedMentos/Aii/actions/runs/12345"

def manifest():
    return {
        "claim": "REVIEW_ONLY",
        "gates": {g: "UNVERIFIED" for g in ("STEP2_UTILITY", "B3_PROMOTION", "BODY_JEPA", "REDMI_PROOF")},
        "chains": {organ: {
            "head_sha": SHA, "status": "SHADOW",
            "runs": [{"head_sha": SHA, "conclusion": "success", "url": URL, "level": "synthetic"}]
        } for organ in ("core", "jepa", "qa", "perception")}
    }

class TestEvidenceRunURL(unittest.TestCase):
    def test_canonical_url_is_syntactically_admitted(self):
        self.assertEqual(check(manifest()), [])

    def test_malformed_urls_fail_closed(self):
        for url in (URL + "/fake", URL + "?other=1", URL + "#spoof",
                    URL + ".evil.example", URL + "\\n", URL.replace("/12345", "/"),
                    URL.replace("/12345", "/0"), URL.replace("https://", "http://"),
                    "https://github.com/RedMentos/Aii/actions/runs/12/../12345",
                    42, None):
            with self.subTest(url=url):
                data = manifest()
                data["chains"]["core"]["runs"][0]["url"] = url
                self.assertIn("core: invalid evidence URL", check(data))

if __name__ == "__main__":
    unittest.main()
