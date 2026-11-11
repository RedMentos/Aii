"""Read-only GitHub Actions reconciliation for pinned V13 organ evidence.

Network verification is opt-in; syntactic manifest validation alone is insufficient.
No gate promotion or branch mutation is performed.
"""
import json
import re
import sys
from urllib.request import Request, urlopen

try:
    from .pinned_multiorgan_evidence import check, REQUIRED
except ImportError:  # direct script invocation
    from pinned_multiorgan_evidence import check, REQUIRED

RUN = re.compile(r"https://github\.com/RedMentos/Aii/actions/runs/([1-9][0-9]*)\Z")


def verify(data, fetch_run):
    """Return errors; fetch_run(run_id) must return GitHub REST Actions run JSON."""
    errors = check(data)
    if errors:
        return errors
    cache = {}
    for organ in REQUIRED:
        chain = data["chains"][organ]
        for entry in chain["runs"]:
            match = RUN.fullmatch(entry["url"])
            if not match:
                errors.append(organ + ": invalid run URL")
                continue
            run_id = int(match.group(1))
            if run_id not in cache:
                try:
                    cache[run_id] = fetch_run(run_id)
                except Exception as exc:
                    errors.append(organ + ": GitHub verification unavailable: " + type(exc).__name__)
                    continue
            run = cache.get(run_id)
            if not isinstance(run, dict):
                errors.append(organ + ": missing GitHub run")
                continue
            repository = run.get("repository")
            if not isinstance(repository, dict) or repository.get("full_name") != "RedMentos/Aii":
                errors.append(organ + ": wrong GitHub repository")
            if run.get("id") != run_id:
                errors.append(organ + ": GitHub run ID mismatch")
            if run.get("head_sha") != chain["head_sha"]:
                errors.append(organ + ": GitHub run head mismatch")
            if run.get("status") != "completed" or run.get("conclusion") != "success":
                errors.append(organ + ": GitHub run not successful")
            if run.get("html_url") != entry["url"]:
                errors.append(organ + ": GitHub canonical URL mismatch")
    return errors


def github_run(run_id):
    request = Request(
        "https://api.github.com/repos/RedMentos/Aii/actions/runs/" + str(run_id),
        headers={"Accept": "application/vnd.github+json", "User-Agent": "v13-readonly-evidence-audit"},
    )
    with urlopen(request, timeout=12) as response:
        return json.load(response)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python verify_actions_evidence.py MANIFEST.json")
    try:
        with open(sys.argv[1], encoding="utf-8") as source:
            manifest = json.load(source)
        errors = verify(manifest, github_run)
    except (OSError, ValueError) as exc:
        errors = ["manifest read failed: " + type(exc).__name__]
    print(json.dumps({"verified": not errors, "errors": errors}, indent=2))
    raise SystemExit(bool(errors))
