"""Explicit local Termux build for the pinned V14 native input-row extractor.

This command builds only the diagnostic helper. It never downloads or changes
model weights, active model selection, runtime permissions, or production routes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import tempfile
import time

LLAMA_CPP_REPOSITORY = "https://github.com/ggml-org/llama.cpp.git"
LLAMA_CPP_REVISION = "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40"
BUILD_TIMEOUT_SECONDS = 1800
MIN_FREE_BYTES = 1024 * 1024 * 1024
MIN_AVAILABLE_RAM_BYTES = 1024 * 1024 * 1024


class NativeExtractorBuildError(RuntimeError):
    pass


def _mem_available_bytes():
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _run(argv, *, cwd=None, timeout=BUILD_TIMEOUT_SECONDS, env=None):
    merged = os.environ.copy()
    merged.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "CMAKE_BUILD_PARALLEL_LEVEL": "1",
        "DO_NOT_TRACK": "1",
    })
    if env:
        merged.update(env)
    try:
        result = subprocess.run(
            [str(value) for value in argv],
            cwd=str(cwd) if cwd is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            close_fds=True,
            env=merged,
        )
    except subprocess.TimeoutExpired as exc:
        raise NativeExtractorBuildError("pinned native extractor build command timed out") from exc
    except OSError as exc:
        raise NativeExtractorBuildError("pinned native extractor build command could not start") from exc
    if result.returncode != 0:
        # Do not echo arbitrary build output into the user-facing runtime log.
        raise NativeExtractorBuildError(
            "pinned native extractor build failed at " + Path(str(argv[0])).name
            + " (exit " + str(result.returncode) + ")"
        )
    return result.stdout.strip()


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise NativeExtractorBuildError("native extractor metadata path is linked")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + secrets.token_hex(8) + ".partial")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build_native_input_embedding_extractor(home, *, confirmed=False, timeout_seconds=BUILD_TIMEOUT_SECONDS):
    """Build/install the exact pinned helper after an explicit local operator confirmation."""
    if confirmed is not True:
        raise PermissionError("native extractor build requires explicit local --confirm")
    if type(timeout_seconds) is not int or not 60 <= timeout_seconds <= BUILD_TIMEOUT_SECONDS:
        raise ValueError("native extractor build timeout is outside its bounded range")
    prefix = os.environ.get("PREFIX", "")
    if (platform.system() != "Linux"
            or platform.machine().lower() not in {"aarch64", "arm64"}
            or not prefix.endswith("/com.termux/files/usr")):
        raise NativeExtractorBuildError("native extractor build is restricted to Termux Android arm64")
    git = shutil.which("git")
    cmake = shutil.which("cmake")
    clang = shutil.which("clang")
    clangxx = shutil.which("clang++")
    if not all((git, cmake, clang, clangxx)):
        raise NativeExtractorBuildError("Termux requires git, cmake, clang and clang++")
    home = Path(home).expanduser()
    if home.is_symlink() or not home.is_dir():
        raise NativeExtractorBuildError("V13 home is missing or linked")
    home = home.resolve(strict=True)
    source_dir = Path(__file__).resolve().parent / "native/input_embedding_extractor"
    if (source_dir.is_symlink() or not source_dir.is_dir()
            or (source_dir / "CMakeLists.txt").is_symlink()
            or not (source_dir / "CMakeLists.txt").is_file()):
        raise NativeExtractorBuildError("pinned native input-extractor source is missing or linked")
    free = shutil.disk_usage(home).free
    available = _mem_available_bytes()
    if free < MIN_FREE_BYTES:
        raise NativeExtractorBuildError("native extractor build requires at least 1 GiB free storage")
    if available is None or available < MIN_AVAILABLE_RAM_BYTES:
        raise NativeExtractorBuildError("native extractor build requires a valid 1 GiB MemAvailable headroom")

    tmp_root = home / "tmp"
    if tmp_root.is_symlink():
        raise NativeExtractorBuildError("V13 temporary directory is linked")
    tmp_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="native-input-extractor-", dir=tmp_root))
    try:
        checkout = work / "llama.cpp"
        checkout.mkdir()
        _run([git, "init"], cwd=checkout, timeout=60)
        _run([git, "remote", "add", "origin", LLAMA_CPP_REPOSITORY], cwd=checkout, timeout=60)
        _run([git, "fetch", "--depth", "1", "origin", LLAMA_CPP_REVISION],
             cwd=checkout, timeout=240)
        _run([git, "checkout", "--detach", "FETCH_HEAD"], cwd=checkout, timeout=60)
        actual_revision = _run([git, "rev-parse", "HEAD"], cwd=checkout, timeout=30)
        if actual_revision != LLAMA_CPP_REVISION:
            raise NativeExtractorBuildError("llama.cpp checkout differs from the pinned revision")
        license_path = checkout / "LICENSE"
        header_path = checkout / "src/llama-ext.h"
        if (license_path.is_symlink() or not license_path.is_file()
                or "MIT License" not in license_path.read_text(encoding="utf-8", errors="replace")
                or header_path.is_symlink() or not header_path.is_file()
                or "llama_model_get_tok_embd_rows" not in header_path.read_text(encoding="utf-8", errors="replace")):
            raise NativeExtractorBuildError("pinned llama.cpp license/API source check failed")

        build_dir = work / "build"
        configure = [
            cmake, "-S", source_dir, "-B", build_dir,
            "-DLLAMA_CPP_DIR=" + str(checkout),
            "-DV14_LLAMA_REVISION=" + LLAMA_CPP_REVISION,
            "-DCMAKE_BUILD_TYPE=Release",
            "-DGGML_NATIVE=OFF",
            "-DGGML_OPENMP=OFF",
        ]
        if shutil.which("ninja"):
            configure.extend(["-G", "Ninja"])
        _run(configure, cwd=work, timeout=timeout_seconds)
        _run([cmake, "--build", build_dir, "--target", "native_input_embedding_extractor", "--parallel", "1"],
             cwd=work, timeout=timeout_seconds)
        candidate = build_dir / "bin/native_input_embedding_extractor"
        if candidate.is_symlink() or not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise NativeExtractorBuildError("native extractor build produced no executable")
        selftest = _run([candidate, "--selftest"], cwd=work, timeout=30)
        version = _run([candidate, "--version"], cwd=work, timeout=15)
        if LLAMA_CPP_REVISION not in version or "PASS" not in selftest.upper():
            raise NativeExtractorBuildError("native extractor self-test/version did not verify the pinned build")

        bin_dir = home / "bin"
        if bin_dir.is_symlink():
            raise NativeExtractorBuildError("V13 bin directory is linked")
        bin_dir.mkdir(parents=True, exist_ok=True)
        target = bin_dir / "native_input_embedding_extractor"
        if target.is_symlink():
            raise NativeExtractorBuildError("existing native extractor is linked")
        target_sha_before = _sha256(target) if target.is_file() else None
        candidate_sha = _sha256(candidate)
        staged = bin_dir / (".native_input_embedding_extractor." + secrets.token_hex(8) + ".partial")
        try:
            shutil.copyfile(candidate, staged)
            staged.chmod(0o700)
            with staged.open("rb") as stream:
                os.fsync(stream.fileno())
            if _sha256(staged) != candidate_sha:
                raise NativeExtractorBuildError("staged native extractor hash mismatch")
            _run([staged, "--selftest"], cwd=work, timeout=30)
            staged_version = _run([staged, "--version"], cwd=work, timeout=15)
            if LLAMA_CPP_REVISION not in staged_version:
                raise NativeExtractorBuildError("staged native extractor revision mismatch")

            backup_path = None
            if target_sha_before is not None:
                backups = home / "backups"
                if backups.is_symlink():
                    raise NativeExtractorBuildError("V13 backup directory is linked")
                backups.mkdir(parents=True, exist_ok=True)
                backup_path = backups / ("native_input_embedding_extractor." + target_sha_before[:16] + ".bak")
                if not backup_path.exists():
                    shutil.copy2(target, backup_path)
                    if _sha256(backup_path) != target_sha_before:
                        raise NativeExtractorBuildError("previous native extractor backup hash mismatch")
            os.replace(staged, target)
            _fsync_directory(bin_dir)
        finally:
            try:
                staged.unlink()
            except FileNotFoundError:
                pass

        metadata = {
            "schema": "v14.native-input-embedding-extractor-install/1",
            "status": "INSTALLED",
            "llama_cpp_repository": LLAMA_CPP_REPOSITORY,
            "llama_cpp_revision": LLAMA_CPP_REVISION,
            "license": "MIT",
            "api_symbol": "llama_model_get_tok_embd_rows",
            "api_stability": "STAGING_WIP",
            "binary_path": "bin/native_input_embedding_extractor",
            "binary_sha256": candidate_sha,
            "previous_binary_sha256": target_sha_before,
            "previous_binary_backup": str(backup_path.relative_to(home)) if backup_path else None,
            "built_at_unix": int(time.time()),
            "model_downloaded": False,
            "model_changed": False,
            "production_route_changed": False,
        }
        _atomic_json(home / "config/native_input_embedding_extractor.json", metadata)
        return metadata
    finally:
        shutil.rmtree(work, ignore_errors=True)
