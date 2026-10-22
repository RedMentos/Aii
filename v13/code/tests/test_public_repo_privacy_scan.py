"""Privacy scan for the public repo (cross-review rule 2026-10-21): added lines only, credentials/contacts/device ids."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import public_repo_privacy_scan as P

def diff(*lines):return 'diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -0,0 +1,%d @@\n'%len(lines)+''.join('+'+l+'\n' for l in lines)

class Scan(unittest.TestCase):
    def test_secrets_contacts_and_device_ids_hit(self):
        for line,kind in (('tok = "ghp_'+'a'*36+'"','github_token'),('key="sk-ant-'+'b'*30+'"','openai_or_anthropic_key'),
                          ('mail me: someone.name@gmail.com','email'),('-----BEGIN OPENSSH PRIVATE KEY-----','private_key'),  # PRIVACY_SCAN_ALLOW synthetic fixture
                          ('"serialno": "AB12CD34EF"','android_device_id'),('password = "hunter22"','password_assignment')):  # PRIVACY_SCAN_ALLOW synthetic fixture
            with self.subTest(kind=kind):self.assertEqual([h[2] for h in P.scan(diff(line))],[kind])
    def test_generic_paths_removed_lines_and_allow_marker_are_clean(self):
        self.assertEqual(P.scan(diff('p = "/workspace/scratch/run1"','home = "/home/user/v13"','x@np.array(y)','a@example.com')),[])
        self.assertEqual(P.scan('--- a/x\n+++ b/x\n@@ -1 +0,0 @@\n-password = "hunter22"\n'),[])  # PRIVACY_SCAN_ALLOW synthetic fixture
        self.assertEqual(P.scan(diff('password = "hunter22"  # PRIVACY_SCAN_ALLOW test fixture')),[])
    def test_line_numbers_follow_hunk(self):
        d='--- a/f\n+++ b/f\n@@ -5,0 +6,2 @@\n+ok\n+x someone@gmail.com\n'  # PRIVACY_SCAN_ALLOW synthetic fixture
        self.assertEqual(P.scan(d)[0][:3],('f',7,'email'))
