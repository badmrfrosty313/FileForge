from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(paths: list[Path]) -> dict[str, list[Path]]:
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in paths:
        if path.is_file() and not path.is_symlink():
            by_size[path.stat().st_size].append(path)
    groups: dict[str, list[Path]] = {}
    for candidates in by_size.values():
        if len(candidates) > 1:
            by_hash: dict[str, list[Path]] = defaultdict(list)
            for path in candidates:
                by_hash[sha256(path)].append(path)
            groups.update({digest: group for digest, group in by_hash.items() if len(group) > 1})
    return groups
