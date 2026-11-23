"""Install exactly the pinned B1/B2/C3 models and the pinned b10964 Linux runner into a new pilot home (no needle, no inference)."""
import json, subprocess, sys
from pathlib import Path
home = Path(sys.argv[1])
from v13.config import initialize
from v13.models import ModelManager, catalog, platform_tag, download_file
from v13.bootstrap import extract
from v13.common import file_hash
home.mkdir(parents=True, exist_ok=False)
initialize(home)
m = ModelManager(home)
for key in ('body', 'language', 'gist'):
    m.install(key)
r = catalog()['runner']; tag = platform_tag()
archive = home / 'tmp/llama-bin.tar.gz'; download_file(r['linux_binaries'][tag], archive)
dest = home / 'bin' / r['tag']; extract(archive, dest)
found = list(dest.rglob('llama-server')); assert len(found) == 1, found
found[0].chmod(0o700); (home / 'bin/llama-server').symlink_to(found[0])
print(json.dumps({'runner': str(found[0]), 'runner_sha256': file_hash(found[0]),
                  'version': subprocess.run([str(found[0]), '--version'], capture_output=True, text=True).stderr.strip()[-200:]}))
