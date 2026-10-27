from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "bp1-qad-train-plus-v2-samejob.yml"


class NativeV2ShellSyntaxTests(unittest.TestCase):
    def test_binding_step_shell_heredoc_and_nested_guards(self):
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        start = next(i for i, line in enumerate(lines)
                     if line.strip() == "- name: Bind actual trained adapter and collect+score genuine 44-response V2")
        run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
        end = next(i for i in range(run + 1, len(lines))
                   if lines[i].startswith("      - name:") or lines[i].startswith("      - uses:"))
        body = "\n".join(line[10:] if line.startswith("          ") else line
                         for line in lines[run + 1:end]) + "\n"
        self.assertIn("<<'PY'", body)
        self.assertIn("\nPY\n", body)
        result = subprocess.run(["bash", "-n"], input=body, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('V2_ADAPTER_LOCATOR_EXIT.txt', body)
        self.assertIn('V2_EXIT.txt', body)


if __name__ == "__main__":
    unittest.main()
