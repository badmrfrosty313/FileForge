from __future__ import annotations

import os
import uuid
from pathlib import Path

from .history import History
from .models import OperationResult, PlannedChange
from .rename import validate_plan


class UnsafeOperation(RuntimeError):
    pass


def execute(changes: list[PlannedChange], history: History | None = None, kind: str = "rename") -> OperationResult:
    # Folder creation is limited to planned destinations and happens only after confirmation.
    for change in changes:
        change.destination.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_plan(changes)
    if errors:
        raise UnsafeOperation("\n".join(errors))
    staged: list[tuple[Path, PlannedChange]] = []
    completed: list[PlannedChange] = []
    try:
        for change in changes:
            temporary = change.source.with_name(f".fileforge-{uuid.uuid4().hex}")
            os.replace(change.source, temporary)
            staged.append((temporary, change))
        for temporary, change in staged:
            os.replace(temporary, change.destination)
            completed.append(change)
    except OSError as exc:
        # Keep a precise result. Staged files remain recoverable and are reported, never overwritten.
        raise UnsafeOperation(f"Operation stopped after {len(completed)} changes: {exc}") from exc
    if history and completed:
        history.record(kind, completed)
    return OperationResult(completed, [])
