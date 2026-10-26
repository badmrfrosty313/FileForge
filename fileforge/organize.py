from __future__ import annotations

from pathlib import Path

from .models import FileStamp, PlannedChange
from .validation import is_within, validate_filename

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx", ".csv"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Video": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json"},
}


def category_for(path: Path) -> str:
    for category, extensions in CATEGORIES.items():
        if path.suffix.lower() in extensions:
            return category
    return "Other"


def plan_organization(
    paths: list[Path],
    root: Path,
    mode: str = "extension",
    custom_rules: dict[str, str] | None = None,
) -> list[PlannedChange]:
    root = root.absolute()
    changes: list[PlannedChange] = []
    rules = {key.lower().lstrip("."): value for key, value in (custom_rules or {}).items()}
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        extension = path.suffix.lower().lstrip(".")
        if mode == "category":
            folder = category_for(path)
        elif mode == "custom":
            folder = rules.get(extension, "Other")
        else:
            folder = extension.upper() or "NO_EXTENSION"
        if validate_filename(folder):
            raise ValueError(f"Unsafe organization folder name: {folder}")
        destination = root / folder / path.name
        if not is_within(destination, root):
            raise ValueError("Organization destination escaped the selected root.")
        changes.append(PlannedChange(path.absolute(), destination, FileStamp.from_path(path)))
    return changes


def plan_quarantine(paths: list[Path], root: Path) -> list[PlannedChange]:
    root = root.absolute()
    changes = []
    for path in paths:
        if path.is_file() and not path.is_symlink():
            destination = root / path.name
            if not is_within(destination, root):
                raise ValueError("Quarantine destination escaped the selected root.")
            changes.append(PlannedChange(path.absolute(), destination, FileStamp.from_path(path)))
    return changes
