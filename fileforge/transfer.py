from __future__ import annotations

import errno
import os
import shutil
from pathlib import Path


def _copy_exclusive(source: Path, destination: Path) -> None:
    created = False
    try:
        with source.open("rb") as input_stream, destination.open("xb") as output_stream:
            created = True
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        shutil.copystat(source, destination, follow_symlinks=False)
        if source.stat().st_size != destination.stat().st_size:
            raise OSError("Copied file size does not match the source")
    except Exception:
        if created:
            try:
                destination.unlink()
            except OSError:
                pass
        raise


def move_no_replace(source: Path, destination: Path) -> None:
    """Move a regular file without ever replacing an existing destination."""
    try:
        os.link(source, destination, follow_symlinks=False)
    except FileExistsError:
        raise
    except OSError as exc:
        if exc.errno not in {errno.EXDEV, errno.EOPNOTSUPP, errno.ENOTSUP}:
            raise
        _copy_exclusive(source, destination)
    try:
        source.unlink()
    except OSError as exc:
        try:
            destination.unlink()
        except OSError as cleanup_exc:
            raise OSError(
                f"Source cleanup failed and the new destination could not be removed: "
                f"{exc}; {cleanup_exc}"
            ) from exc
        raise
