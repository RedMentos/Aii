"""Regression: URL validation must be callable and reject spoofed run URLs."""
import unittest
from scripts.pinned_multiorgan_evidence import check

SHA = "a" * 40
URL = "https://github.com/RedMentos/Aii/actions/runs/123"

def manifest(url):
    return {
        "claim": "REVIEW_ONLY",
        "gates": {g: "UNVERIFIED" for g in ("STEP2_UTILITY", "B3_PROMOTION", "BODY_JEPA", "REDMI_PROOF")},
        "chains": {organ: {"head_sha": SHA, "status": "SHADOW",
                            "runs": [{"head_sha": SHA, "conclusion": "success",
                                      "url": url, "level": "synthetic"}]}
                   for organ in ("core", "jepa", "qa", "perception")},
    }

class EvidenceURLDefinitionRegression(unittest.TestCase):
    def test_valid_url_does_not_raise_nameerror(self):
        self.assertEqual(check(manifest(URL)), [])

    def test_spoofed_url_fails_closed(self):
        for url in (URL + "/evil", URL + "?foo=1", URL.replace("github.com", "github.com.evil")):
            with self.subTest(url=url):
                self.assertIn("core: invalid evidence URL", check(manifest(url)))
