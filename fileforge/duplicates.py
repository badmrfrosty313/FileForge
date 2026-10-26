from __future__ import annotations

import hashlib
import os
import threading
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .validation import is_link_like


@dataclass(frozen=True)
class DuplicateGroup:
    digest: str
    size: int
    paths: tuple[Path, ...]

    @property
    def recoverable_bytes(self) -> int:
        return self.size * max(0, len(self.paths) - 1)


def scan_files(roots: Iterable[Path], cancel: threading.Event | None = None) -> list[Path]:
    files: list[Path] = []
    pending = [path.absolute() for path in roots]
    while pending:
        if cancel and cancel.is_set():
            break
        path = pending.pop()
        try:
            if is_link_like(path):
                continue
            if path.is_file():
                files.append(path)
                continue
            with os.scandir(path) as entries:
                for entry in entries:
                    candidate = Path(entry.path)
                    if is_link_like(candidate):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(candidate)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(candidate)
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return files


def sha256(
    path: Path,
    chunk_size: int = 1024 * 1024,
    cancel: threading.Event | None = None,
) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            if cancel and cancel.is_set():
                raise InterruptedError("Hashing cancelled")
            digest.update(chunk)
    return digest.hexdigest()


def duplicate_groups(
    paths: Iterable[Path],
    cancel: threading.Event | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[DuplicateGroup]:
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in paths:
        try:
            if path.is_file() and not is_link_like(path):
                by_size[path.stat().st_size].append(path)
        except (PermissionError, FileNotFoundError, OSError):
            continue
    candidates = [item for items in by_size.values() if len(items) > 1 for item in items]
    hashed = 0
    results: list[DuplicateGroup] = []
    for size, items in by_size.items():
        if len(items) < 2:
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in items:
            if cancel and cancel.is_set():
                return results
            try:
                by_hash[sha256(path, cancel=cancel)].append(path)
            except (PermissionError, FileNotFoundError, OSError, InterruptedError):
                continue
            hashed += 1
            if progress:
                progress(hashed, len(candidates))
        results.extend(
            DuplicateGroup(digest, size, tuple(group))
            for digest, group in by_hash.items()
            if len(group) > 1
        )
    return sorted(results, key=lambda group: group.recoverable_bytes, reverse=True)


def find_duplicates(paths: list[Path]) -> dict[str, list[Path]]:
    return {group.digest: list(group.paths) for group in duplicate_groups(paths)}
