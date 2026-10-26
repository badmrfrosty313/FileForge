from __future__ import annotations

import re
from pathlib import Path

WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
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
    if len(name) > 255:
        return "Filename is longer than 255 characters."
    return None


def safe_destination(source: Path, destination: Path) -> str | None:
    if destination.parent != source.parent and not destination.parent.exists():
        return "Destination folder does not exist."
    return validate_filename(destination.name)
