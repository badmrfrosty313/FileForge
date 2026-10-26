from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .models import FileStamp, JournalEntry, PlannedChange


class History:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".fileforge" / "history.json"

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def record(self, kind: str, changes: list[PlannedChange]) -> None:
        entry = JournalEntry(kind, changes, datetime.now(UTC).isoformat())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data.append(entry.to_dict())
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def latest(self) -> JournalEntry | None:
        data = self._load()
        if not data:
            return None
        raw = data[-1]
        changes = [
            PlannedChange(Path(c["source"]), Path(c["destination"]), FileStamp(**c["stamp"]))
            for c in raw["changes"]
        ]
        return JournalEntry(raw["kind"], changes, raw["created_at"])

    def undo_latest(self) -> list[str]:
        entry = self.latest()
        if not entry:
            return ["No completed operation is available to undo."]
        errors: list[str] = []
        for change in entry.changes:
            if not change.destination.exists():
                errors.append(f"Cannot undo; destination is missing: {change.destination}")
            elif change.source.exists():
                errors.append(f"Cannot undo; source now exists: {change.source}")
        if errors:
            return errors
        for change in reversed(entry.changes):
            change.destination.replace(change.source)
        return []
