"""Privacy-safe point-in-time census of V13-owned native llama-server processes.

The trusted AI supervisor creates its own process group; only native children
within that exact group are included. No PIDs, paths, arguments, prompts,
credentials or other apps are exported. This is *not* proof a role was used
in a prior answer, and free Android RAM cannot substitute for this reading.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SCHEMA = "v13.phone-native-residency/1"
ROLES = {"body": "B1_DETAIL", "gist": "B2_GIST", "language": "C3_LANGUAGE"}
MAX_PROC_ENTRIES = 4096
MAX_ARG_BYTES = 8192
MAX_MANIFEST_BYTES = 128 * 1024


def _model_paths(home):
    path = home / "config/models.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        return {}
    result = {}
    for key, role in ROLES.items():
        entry = value.get(key)
        if type(entry) is not dict or entry.get("download_complete") is not True:
            continue
        files, main = entry.get("files"), entry.get("main_file")
        item = files.get(main) if type(files) is dict else None
        rel = item.get("path") if type(item) is dict else None
        if type(rel) is not str or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            continue
        result.setdefault(str((home / rel).resolve()), []).append(role)
    return result


def _memory_mib(procdir, filename, field):
    try:
        for line in (procdir / filename).read_text(errors="replace")[:65536].splitlines():
            if line.startswith(field + ":"):
                fields = line.split(":", 1)[1].split()
                if len(fields) >= 2 and fields[1] == "kB" and fields[0].isdigit():
                    amount = int(fields[0])
                    if amount < 1024 * 1024 * 1024:
                        return round(amount / 1024, 1)
    except (OSError, ValueError, UnicodeError):
        pass
    return None


def snapshot(supervisor_pid, home=None, *, proc_root=Path("/proc"), group_of=os.getpgid):
    result = {"schema": SCHEMA, "availability": "UNAVAILABLE",
              "sample_kind": "INSTANT_NATIVE_PROCESSES",
              "roles": {role: {"processes": 0} for role in ROLES.values()},
              "unmapped_native_processes": 0,
              "memory_accounting": "PROCESS_PSS_NOT_FREE_RAM"}
    if type(supervisor_pid) is not int or not 1 <= supervisor_pid <= 1_000_000_000:
        result["reason"] = "NO_VERIFIED_MODEL_SUPERVISOR"
        return result
    try:
        if group_of(supervisor_pid) != supervisor_pid:
            result["reason"] = "SUPERVISOR_GROUP_MISMATCH"
            return result
        known = _model_paths(Path(home or Path.home() / "v13"))
        entries = list(proc_root.iterdir())
        if len(entries) > MAX_PROC_ENTRIES:
            result["reason"] = "PROCESS_CENSUS_LIMIT"
            return result
        pss_sum, rss_sum, sampled, scanned = 0., 0., 0, 0
        for procdir in entries:
            if not procdir.name.isdigit():
                continue
            pid = int(procdir.name)
            if pid == supervisor_pid:
                continue
            try:
                if group_of(pid) != supervisor_pid:
                    continue
                raw = (procdir / "cmdline").read_bytes()[:MAX_ARG_BYTES]
                scanned += 1
            except (OSError, ProcessLookupError, PermissionError):
                continue
            args = [arg.decode("utf-8", "replace") for arg in raw.split(b"\x00") if arg]
            if not args or Path(args[0]).name not in ("llama-server", "llama-server-mem"):
                continue
            model = None
            if "-m" in args:
                index = args.index("-m") + 1
                model = args[index] if index < len(args) else None
            mapped = known.get(str(Path(model).resolve())) if model else None
            if not mapped:
                result["unmapped_native_processes"] += 1
                continue
            pss = _memory_mib(procdir, "smaps_rollup", "Pss")
            rss = _memory_mib(procdir, "status", "VmRSS")
            for role in mapped:
                entry = result["roles"][role]
                entry["processes"] += 1
                if pss is not None:
                    entry["pss_mib"] = round(entry.get("pss_mib", 0.) + pss, 1)
                if rss is not None:
                    entry["rss_mib"] = round(entry.get("rss_mib", 0.) + rss, 1)
            if pss is not None:
                pss_sum += pss
            if rss is not None:
                rss_sum += rss
            sampled += 1
        result.update(availability="AVAILABLE", mapped_native_processes=sampled,
                      mapped_pss_mib=round(pss_sum, 1),
                      mapped_rss_mib=round(rss_sum, 1))
        if scanned == 0 and not any(result["roles"][r]["processes"] for r in ROLES.values()):
            result["readability"] = "UNKNOWN_NO_GROUP_CHILDREN"
        else:
            result["readability"] = "OBSERVED"
        return result
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        result["reason"] = "PROCESS_CENSUS_UNAVAILABLE"
        return result
