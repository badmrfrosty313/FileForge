from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import FileStamp, PlannedChange
from .validation import normalized, validate_change


@dataclass(frozen=True)
class RenameRules:
    find: str = ""
    replace: str = ""
    prefix: str = ""
    suffix: str = ""
    numbering_start: int | None = None
    numbering_padding: int = 1
    case: str = "keep"
    extension: str = ""


def transformed_name(path: Path, rules: RenameRules, index: int) -> str:
    stem, extension = path.stem, path.suffix
    if rules.find:
        stem = stem.replace(rules.find, rules.replace)
    if rules.case == "lower":
        stem = stem.lower()
    elif rules.case == "upper":
        stem = stem.upper()
    elif rules.case == "title":
        stem = stem.title()
    number = ""
    if rules.numbering_start is not None:
        number = str(rules.numbering_start + index).zfill(max(1, rules.numbering_padding))
    return f"{rules.prefix}{stem}{rules.suffix}{number}{extension}"


def plan_renames(paths: list[Path], rules: RenameRules) -> list[PlannedChange]:
    extension_filter = rules.extension.lower().strip()
    if extension_filter and not extension_filter.startswith("."):
        extension_filter = f".{extension_filter}"
    selected = [
        path
        for path in paths
        if path.is_file()
        and not path.is_symlink()
        and (not extension_filter or path.suffix.lower() == extension_filter)
    ]
    changes = []
    for index, path in enumerate(selected):
        source = path.absolute()
        destination = source.with_name(transformed_name(source, rules, index))
        if destination != source:
            changes.append(PlannedChange(source, destination, FileStamp.from_path(source)))
    return changes


def validate_plan(changes: list[PlannedChange]) -> list[str]:
    errors: list[str] = []
    source_keys = {normalized(change.source) for change in changes}
    destination_keys: set[str] = set()
    for change in changes:
        errors.extend(
            f"{change.source}: {reason}"
            for reason in validate_change(change.source, change.destination)
        )
        destination_key = normalized(change.destination)
        if destination_key in destination_keys:
            errors.append(f"Multiple files would target {change.destination}.")
        destination_keys.add(destination_key)
        if change.destination.exists() and destination_key not in source_keys:
            errors.append(f"Destination already exists: {change.destination}")
        try:
            current = FileStamp.from_path(change.source)
        except (FileNotFoundError, PermissionError, OSError) as exc:
            errors.append(f"Source cannot be accessed: {change.source} ({exc})")
        else:
            if current != change.stamp:
                errors.append(f"Source changed since preview: {change.source}")
    return errors
