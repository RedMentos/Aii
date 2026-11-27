"""Explicit, provenance-recording download of the official UCI M1 dataset.

This command is opt-in and is never called automatically by the model runner.
Only the expected data member is copied out of the ZIP; no archive paths are
extracted directly. Raw data and its provenance sidecar belong in the ignored
experiments/datasets/ directory and must never be committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

UCI_ARCHIVE_URL = (
    "https://archive.ics.uci.edu/static/public/235/"
    "individual%2Bhousehold%2Belectric%2Bpower%2Bconsumption.zip"
)
EXPECTED_MEMBER = "household_power_consumption.txt"
DATASET_DOI = "10.24432/C58K54"
DATASET_LICENSE = "CC BY 4.0"
DATASET_CITATION = (
    "Hebrail, G. & Berard, A. (2006). Individual Household Electric Power "
    "Consumption [Dataset]. UCI Machine Learning Repository."
)
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_DATA_BYTES = 256 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_name(name: str) -> PurePosixPath:
    if not name or "\\" in name:
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    return path


def _write_json_atomic(payload: dict, destination: Path, *, force: bool) -> None:
    if destination.exists() and not force:
        raise FileExistsError(f"provenance sidecar already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8") + b"\n"
    fd, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def extract_dataset_archive(
    archive_path: str | Path,
    destination: str | Path,
    *,
    source_url: str = UCI_ARCHIVE_URL,
    force: bool = False,
) -> dict:
    """Verify a ZIP and atomically copy only the expected dataset member."""
    archive = Path(archive_path)
    target = Path(destination)
    sidecar = target.with_name(target.name + ".provenance.json")
    if (target.exists() or sidecar.exists()) and not force:
        raise FileExistsError(
            "dataset or provenance sidecar already exists; choose another directory "
            "or pass --force explicitly"
        )
    if not archive.is_file():
        raise FileNotFoundError(archive)
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP archive exceeds the configured size limit")

    with zipfile.ZipFile(archive, "r") as bundle:
        infos = bundle.infolist()
        for info in infos:
            _safe_member_name(info.filename)
        damaged = bundle.testzip()
        if damaged is not None:
            raise ValueError(f"ZIP CRC check failed for member {damaged!r}")
        matches = [
            info for info in infos
            if _safe_member_name(info.filename).name == EXPECTED_MEMBER
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one {EXPECTED_MEMBER!r} member, found {len(matches)}"
            )
        info = matches[0]
        if info.is_dir() or info.file_size < 1 or info.file_size > MAX_DATA_BYTES:
            raise ValueError("dataset member has an invalid or excessive uncompressed size")
        if info.compress_size > MAX_ARCHIVE_BYTES:
            raise ValueError("dataset member compressed size exceeds the download limit")
        if info.compress_size and info.file_size / info.compress_size > 1000:
            raise ValueError("dataset member compression ratio exceeds the safety limit")
        mode = info.external_attr >> 16
        if mode and stat.S_ISDIR(mode):
            raise ValueError("expected dataset member is a directory")

        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=target.name + ".", suffix=".tmp", dir=target.parent
        )
        digest = hashlib.sha256()
        copied = 0
        try:
            with os.fdopen(fd, "wb") as output, bundle.open(info, "r") as source:
                while True:
                    chunk = source.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > MAX_DATA_BYTES:
                        raise ValueError("extracted dataset exceeds the configured size limit")
                    output.write(chunk)
                    digest.update(chunk)
                output.flush()
                os.fsync(output.fileno())
            if copied != info.file_size:
                raise ValueError("extracted byte count differs from ZIP metadata")

            archive_sha256 = _sha256_file(archive)
            file_sha256 = digest.hexdigest()
            provenance = {
                "schema": "m1.uci-download-provenance.v1",
                "dataset": "Individual Household Electric Power Consumption",
                "doi": DATASET_DOI,
                "license": DATASET_LICENSE,
                "citation": DATASET_CITATION,
                "source_url": source_url,
                "archive_sha256": archive_sha256,
                "archive_size_bytes": archive.stat().st_size,
                "member_name": info.filename,
                "file_sha256": file_sha256,
                "file_size_bytes": copied,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            os.replace(temporary, target)
            _write_json_atomic(provenance, sidecar, force=force)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    return {
        "dataset_path": str(target),
        "provenance_path": str(sidecar),
        "file_sha256": provenance["file_sha256"],
        "archive_sha256": provenance["archive_sha256"],
        "file_size_bytes": provenance["file_size_bytes"],
        "license": DATASET_LICENSE,
        "doi": DATASET_DOI,
    }


def download_dataset(
    output_dir: str | Path,
    *,
    source_url: str = UCI_ARCHIVE_URL,
    force: bool = False,
    timeout_seconds: int = 45,
) -> dict:
    """Download the official archive to a temporary file, verify it, then extract."""
    parsed_url = urlsplit(source_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "archive.ics.uci.edu":
        raise ValueError("dataset download must use HTTPS on archive.ics.uci.edu")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / EXPECTED_MEMBER
    sidecar = destination.with_name(destination.name + ".provenance.json")
    if (destination.exists() or sidecar.exists()) and not force:
        raise FileExistsError(
            f"{destination} or its provenance sidecar already exists; use --force explicitly"
        )

    request = Request(
        source_url,
        headers={"User-Agent": "M1-clean-room-experiment/1.0 (UCI dataset acquisition)"},
    )
    fd, archive_name = tempfile.mkstemp(
        prefix=".uci-download-", suffix=".zip", dir=directory
    )
    archive_path = Path(archive_name)
    total = 0
    try:
        with os.fdopen(fd, "wb") as output, urlopen(request, timeout=timeout_seconds) as response:
            final_url = urlsplit(response.geturl())
            if final_url.scheme != "https" or final_url.hostname != "archive.ics.uci.edu":
                raise ValueError("UCI download redirected outside the official HTTPS host")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > MAX_ARCHIVE_BYTES:
                raise ValueError("UCI archive Content-Length exceeds the configured download limit")
            while True:
                chunk = response.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError("UCI archive exceeds the configured download limit")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if total == 0:
            raise ValueError("UCI archive download returned no bytes")
        return extract_dataset_archive(
            archive_path, destination, source_url=source_url, force=force
        )
    finally:
        try:
            archive_path.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="experiments/datasets")
    parser.add_argument("--url", default=UCI_ARCHIVE_URL)
    parser.add_argument("--force", action="store_true", help="explicitly replace existing dataset and sidecar")
    args = parser.parse_args(argv)
    result = download_dataset(args.output_dir, source_url=args.url, force=args.force)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
