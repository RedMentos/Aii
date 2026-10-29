"""Source-only regression for pinned llama-server --lora-scaled FNAME:SCALE argv."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import p2x_candidate360_standalone as M

class P2XLoraScaledCliReview(unittest.TestCase):
    def test_owned_server_receives_single_adapter_colon_scale_argument(self):
        class Proc:
            def poll(self):return None
            def terminate(self):pass
            def wait(self,timeout):return 0
        with tempfile.TemporaryDirectory() as d:
            with patch.object(M.subprocess,"Popen",return_value=Proc()) as launch, \
                 patch.object(M.LocalServer,"request",return_value={"status":"ok"}):
                server=M.LocalServer("pinned-binary","pinned-model",
                                     "synthetic-adapter",Path(d)/"server.log")
            argv=launch.call_args.args[0]
            i=argv.index("--lora-scaled")
            self.assertEqual(argv[i+1],"synthetic-adapter:1")
            self.assertEqual(argv[i+2],"--host")
            # Other flags legitimately use the standalone value "1" (-np).
            # Only the immediate LoRA option boundary must be single-token.
            self.assertEqual(argv[argv.index("--host")+1],"127.0.0.1")
            server.close()

if __name__=="__main__":unittest.main()
