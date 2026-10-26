from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class FileStamp:
    size: int
    mtime_ns: int

    @classmethod
    def from_path(cls, path: Path) -> FileStamp:
        stat = path.stat()
        return cls(stat.st_size, stat.st_mtime_ns)


@dataclass(frozen=True)
class PlannedChange:
    source: Path
    destination: Path
    stamp: FileStamp


@dataclass
class OperationResult:
    completed: list[PlannedChange]
    failures: list[str] = field(default_factory=list)
    rolled_back: bool = False


@dataclass
class JournalEntry:
    id: str
    kind: Literal["rename", "organize", "quarantine"]
    changes: list[PlannedChange]
    created_at: str
    status: Literal["completed", "undone", "failed"] = "completed"
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "created_at": self.created_at,
            "status": self.status,
            "message": self.message,
            "changes": [
                {
                    "source": str(change.source),
                    "destination": str(change.destination),
                    "stamp": asdict(change.stamp),
                }
                for change in self.changes
            ],
        }
