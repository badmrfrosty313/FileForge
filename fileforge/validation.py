from __future__ import annotations

import os
import re
from pathlib import Path

WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_filename(name: str) -> str | None:
    if not name or name in {".", ".."}:
        return "A filename is required."
    if name != name.strip() or name.endswith((".", " ")):
        return "Windows filenames cannot end in a space or period."
    if INVALID_CHARS.search(name):
        return "Filename contains characters Windows does not allow."
    if name.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        return "Filename uses a reserved Windows device name."
    if len(name.encode("utf-8")) > 255:
        return "Filename is longer than the supported 255-byte limit."
    return None


def normalized(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def is_within(path: Path, root: Path) -> bool:
    try:
        Path(normalized(path)).relative_to(Path(normalized(root)))
        return True
    except ValueError:
        return False


def validate_change(source: Path, destination: Path) -> list[str]:
    errors: list[str] = []
    reason = validate_filename(destination.name)
    if reason:
        errors.append(reason)
    if source == destination:
        errors.append("Source and destination are identical.")
    if source.is_symlink():
        errors.append("Symbolic links and junction-like entries are not changed.")
    if not destination.is_absolute():
        errors.append("Destination must be an absolute path.")
    return errors
