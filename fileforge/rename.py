from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import FileStamp, PlannedChange
from .validation import safe_destination


@dataclass(frozen=True)
class RenameRules:
    find: str = ""
    replace: str = ""
    prefix: str = ""
    suffix: str = ""
    numbering_start: int | None = None
    case: str = "keep"  # keep, lower, upper, title
    extension: str = ""


def transformed_name(path: Path, rules: RenameRules, index: int) -> str:
    stem, ext = path.stem, path.suffix
    stem = stem.replace(rules.find, rules.replace)
    if rules.case == "lower":
        stem = stem.lower()
    elif rules.case == "upper":
        stem = stem.upper()
    elif rules.case == "title":
        stem = stem.title()
    number = "" if rules.numbering_start is None else str(rules.numbering_start + index)
    return f"{rules.prefix}{stem}{rules.suffix}{number}{ext}"


def plan_renames(paths: list[Path], rules: RenameRules) -> list[PlannedChange]:
    selected = [p for p in paths if p.is_file() and (not rules.extension or p.suffix.lower() == rules.extension.lower())]
    return [PlannedChange(p, p.with_name(transformed_name(p, rules, i)), FileStamp.from_path(p)) for i, p in enumerate(selected)]


def validate_plan(changes: list[PlannedChange]) -> list[str]:
    errors: list[str] = []
    sources = {c.source for c in changes}
    destinations: set[Path] = set()
    for change in changes:
        reason = safe_destination(change.source, change.destination)
        if reason:
            errors.append(f"{change.source}: {reason}")
        if change.destination in destinations:
            errors.append(f"Multiple files would target {change.destination}.")
        destinations.add(change.destination)
        if change.destination.exists() and change.destination not in sources:
            errors.append(f"Destination already exists: {change.destination}")
        if not change.source.exists():
            errors.append(f"Source is missing: {change.source}")
        elif FileStamp.from_path(change.source) != change.stamp:
            errors.append(f"Source changed since preview: {change.source}")
    return errors
