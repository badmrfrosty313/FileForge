from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .models import FileStamp, JournalEntry, PlannedChange


def default_history_path() -> Path:
    appdata = os.environ.get("LOCALAPPDATA")
    base = Path(appdata) if appdata else Path.home() / ".local" / "share"
    return base / "FileForge" / "history.json"


class History:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_history_path()

    def _load_raw(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def _save_raw(self, data: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix="history-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _parse(raw: dict) -> JournalEntry:
        changes = [
            PlannedChange(
                Path(change["source"]),
                Path(change["destination"]),
                FileStamp(**change["stamp"]),
            )
            for change in raw.get("changes", [])
        ]
        return JournalEntry(
            raw.get("id", str(uuid.uuid4())),
            raw["kind"],
            changes,
            raw["created_at"],
            raw.get("status", "completed"),
            raw.get("message", ""),
        )

    def entries(self) -> list[JournalEntry]:
        return [self._parse(raw) for raw in reversed(self._load_raw())]

    def record(
        self,
        kind: str,
        changes: list[PlannedChange],
        status: str = "completed",
        message: str = "",
    ) -> JournalEntry:
        entry = JournalEntry(
            str(uuid.uuid4()), kind, changes, datetime.now(UTC).isoformat(), status, message
        )
        data = self._load_raw()
        data.append(entry.to_dict())
        self._save_raw(data)
        return entry

    def latest(self) -> JournalEntry | None:
        return next((entry for entry in self.entries() if entry.status == "completed"), None)

    def undo(self, entry_id: str | None = None) -> list[str]:
        data = self._load_raw()
        target_index = None
        target = None
        for index in range(len(data) - 1, -1, -1):
            candidate = self._parse(data[index])
            if candidate.status == "completed" and (entry_id is None or candidate.id == entry_id):
                target_index, target = index, candidate
                break
        if target is None or target_index is None:
            return ["No completed reversible operation was found."]
        errors: list[str] = []
        destination_paths = {change.destination for change in target.changes}
        for change in target.changes:
            if not change.destination.exists():
                errors.append(f"Destination is missing: {change.destination}")
            elif change.source.exists() and change.source not in destination_paths:
                errors.append(f"Original path is occupied: {change.source}")
            else:
                try:
                    if FileStamp.from_path(change.destination) != change.stamp:
                        errors.append(f"File changed after the operation: {change.destination}")
                except OSError as exc:
                    errors.append(f"Cannot inspect {change.destination}: {exc}")
        if errors:
            return errors
        staged: list[tuple[Path, PlannedChange]] = []
        completed: list[PlannedChange] = []
        try:
            for change in target.changes:
                temporary = change.destination.with_name(
                    f".fileforge-undo-{uuid.uuid4().hex}.pending"
                )
                change.destination.rename(temporary)
                staged.append((temporary, change))
            for temporary, change in reversed(staged):
                if change.source.exists():
                    raise FileExistsError(f"Original path became occupied: {change.source}")
                temporary.rename(change.source)
                completed.append(change)
        except OSError as exc:
            rollback_errors: list[str] = []
            for change in reversed(completed):
                try:
                    if change.source.exists() and not change.destination.exists():
                        change.source.rename(change.destination)
                except OSError as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            completed_sources = {change.source for change in completed}
            for temporary, change in staged:
                if change.source in completed_sources:
                    continue
                try:
                    if temporary.exists() and not change.destination.exists():
                        temporary.rename(change.destination)
                except OSError as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            message = f"Undo failed and rollback was attempted: {exc}"
            if rollback_errors:
                message += f"; manual recovery may be needed: {'; '.join(rollback_errors)}"
            return [message]
        data[target_index]["status"] = "undone"
        data[target_index]["message"] = "Undone safely"
        self._save_raw(data)
        return []

    def undo_latest(self) -> list[str]:
        return self.undo()
