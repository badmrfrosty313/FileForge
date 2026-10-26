from __future__ import annotations

import threading
import uuid
from pathlib import Path

from .history import History
from .models import OperationResult, PlannedChange
from .rename import validate_plan
from .transfer import move_no_replace


class UnsafeOperation(RuntimeError):
    pass


_operation_lock = threading.Lock()


def execute(
    changes: list[PlannedChange],
    history: History | None = None,
    kind: str = "rename",
    cancel: threading.Event | None = None,
) -> OperationResult:
    if not changes:
        raise UnsafeOperation("The plan contains no changes.")
    if not _operation_lock.acquire(blocking=False):
        raise UnsafeOperation("Another filesystem operation is already running.")
    staged: list[tuple[Path, PlannedChange]] = []
    completed: list[PlannedChange] = []
    created_folders: set[Path] = set()
    try:
        errors = validate_plan(changes)
        if errors:
            raise UnsafeOperation("\n".join(errors))
        for change in changes:
            if cancel and cancel.is_set():
                raise UnsafeOperation("Operation cancelled before files were changed.")
            parent = change.destination.parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
                created_folders.add(parent)
        for change in changes:
            temporary = change.source.with_name(f".fileforge-{uuid.uuid4().hex}.pending")
            move_no_replace(change.source, temporary)
            staged.append((temporary, change))
        for temporary, change in staged:
            if cancel and cancel.is_set():
                raise OSError("Operation cancelled; rolling back")
            if change.destination.exists():
                raise FileExistsError(f"Destination appeared during execution: {change.destination}")
            move_no_replace(temporary, change.destination)
            completed.append(change)
    except UnsafeOperation:
        raise
    except OSError as exc:
        rollback_errors: list[str] = []
        for change in reversed(completed):
            try:
                if change.destination.exists() and not change.source.exists():
                    move_no_replace(change.destination, change.source)
            except OSError as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        completed_sources = {change.source for change in completed}
        for temporary, change in reversed(staged):
            if change.source in completed_sources:
                continue
            try:
                if temporary.exists() and not change.source.exists():
                    move_no_replace(temporary, change.source)
            except OSError as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        detail = f"Operation failed and was rolled back: {exc}"
        if rollback_errors:
            detail += f"; rollback needs attention: {'; '.join(rollback_errors)}"
        if history:
            history.record(kind, changes, "failed", detail)
        raise UnsafeOperation(detail) from exc
    finally:
        for folder in sorted(created_folders, key=lambda path: len(path.parts), reverse=True):
            try:
                folder.rmdir()
            except OSError:
                pass
        _operation_lock.release()
    if history:
        history.record(kind, completed)
    return OperationResult(completed)
