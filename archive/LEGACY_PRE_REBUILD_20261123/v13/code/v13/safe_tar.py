"""Transactional extraction of pinned native tarballs on Python 3.10+.

Never writes through an archive symlink or mutates a previous extraction until
all members have been validated and staged. Does not establish model provenance:
the caller must verify the downloaded archive hash against the pinned catalog.
"""
from pathlib import Path, PurePosixPath
import os
import shutil
import tarfile
import tempfile


def _member_path(member):
    name = member.name
    if not name or '\\' in name or name.startswith('/'):
        raise ValueError('Unsicheres Archivmitglied')
    raw = name.split('/')
    if '..' in raw:
        raise ValueError('Unsicheres Archivmitglied')
    relative = PurePosixPath(name)
    if str(relative) == '.':
        if member.isdir():
            return None  # Conventional archive root marker (./).
        raise ValueError('Unsicheres Archivmitglied')
    if not (member.isdir() or member.isfile() or member.issym()):
        raise ValueError('Unsicheres Archivmitglied')
    return relative


def extract(archive, dest):
    """Extract verified tar bytes; preserve the old destination on failure.

    Symlinks may reference only staged in-tree targets. File writes happen
    before any symlink is created, and no member may be nested below a link.
    """
    dest = Path(dest)
    if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
        raise ValueError('Unsicheres Archivziel')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.' + dest.name + '.extract-', dir=dest.parent) as work:
        work = Path(work)
        stage = work / 'tree'
        stage.mkdir()
        entries = []
        seen = set()
        symlinks = set()
        with tarfile.open(archive, mode='r:*') as source:
            for member in source.getmembers():
                rel = _member_path(member)
                if rel is None:
                    continue
                if rel in seen:
                    raise ValueError('Doppeltes Archivmitglied')
                seen.add(rel)
                entries.append((member, rel))
                if member.issym():
                    symlinks.add(rel)
                    if not member.linkname or '\\' in member.linkname or member.linkname.startswith('/'):
                        raise ValueError('Unsicherer Archiv-Symlink')
                    target = (stage / rel.parent / member.linkname).resolve()
                    if not target.is_relative_to(stage.resolve()):
                        raise ValueError('Archiv-Symlink außerhalb Ziel')
            if not entries:
                raise ValueError('Leeres Archiv')
            for member, rel in entries:
                if any(parent in symlinks for parent in rel.parents):
                    raise ValueError('Archivmitglied unter Symlink')
                if member.issym():
                    continue
                path = stage.joinpath(*rel.parts)
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    body = source.extractfile(member)
                    if body is None:
                        raise ValueError('Archivdatei ohne Daten')
                    with body, path.open('xb') as out:
                        shutil.copyfileobj(body, out, length=1024 * 1024)
                    path.chmod(member.mode & 0o755)
            for member, rel in entries:
                if not member.issym():
                    continue
                path = stage.joinpath(*rel.parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(member.linkname)
            for rel in symlinks:
                try:
                    target = stage.joinpath(*rel.parts).resolve(strict=True)
                except (RuntimeError, OSError) as exc:
                    raise ValueError('Zyklischer Archiv-Symlink') from exc
                if not target.is_relative_to(stage.resolve()):
                    raise ValueError('Archiv-Symlink außerhalb Ziel')
        # Same-filesystem renames; failed validation leaves the old tree intact.
        previous = work / 'previous'
        moved_old = False
        if dest.exists():
            os.replace(dest, previous)
            moved_old = True
        try:
            os.replace(stage, dest)
        except BaseException:
            if moved_old and not dest.exists():
                os.replace(previous, dest)
            raise
