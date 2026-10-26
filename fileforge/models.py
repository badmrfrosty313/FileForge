from __future__ import annotations

from dataclasses import asdict, dataclass
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
    failures: list[str]


@dataclass
class JournalEntry:
    kind: Literal["rename", "organize"]
    changes: list[PlannedChange]
    created_at: str

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "created_at": self.created_at,
            "changes": [
                {"source": str(c.source), "destination": str(c.destination), "stamp": asdict(c.stamp)}
                for c in self.changes
            ],
        }
