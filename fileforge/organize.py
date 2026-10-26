from __future__ import annotations

from pathlib import Path

from .models import FileStamp, PlannedChange

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a"},
    "Video": {".mp4", ".mov", ".mkv", ".avi"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
}


def category_for(path: Path) -> str:
    for category, extensions in CATEGORIES.items():
        if path.suffix.lower() in extensions:
            return category
    return "Other"


def plan_organization(paths: list[Path], root: Path, by_category: bool = False) -> list[PlannedChange]:
    changes = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        folder = category_for(path) if by_category else (path.suffix[1:].upper() or "NO_EXTENSION")
        changes.append(PlannedChange(path, root / folder / path.name, FileStamp.from_path(path)))
    return changes
