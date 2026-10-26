import json
import threading
from pathlib import Path

import pytest

from fileforge.history import History
from fileforge.models import FileStamp, PlannedChange
from fileforge.operations import UnsafeOperation, execute
from fileforge.rename import RenameRules, plan_renames


def test_empty_plan_is_rejected() -> None:
    with pytest.raises(UnsafeOperation, match="no changes"):
        execute([])


def test_completed_history_can_be_selected_and_undone(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("a")
    history = History(tmp_path / "history.json")
    execute(plan_renames([source], RenameRules(prefix="x")), history)
    entry = history.entries()[0]
    assert history.undo(entry.id) == []
    assert history.entries()[0].status == "undone"


def test_undo_rejects_modified_destination(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("a")
    history = History(tmp_path / "history.json")
    execute(plan_renames([source], RenameRules(prefix="x")), history)
    destination = tmp_path / "xa.txt"
    destination.write_text("changed content")
    assert any("changed" in error for error in history.undo_latest())


def test_corrupt_history_is_treated_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text("not json")
    assert History(path).entries() == []


def test_history_file_remains_valid_json(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("a")
    path = tmp_path / "history.json"
    execute(plan_renames([source], RenameRules(prefix="x")), History(path))
    assert isinstance(json.loads(path.read_text()), list)


def test_missing_source_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("a")
    plan = plan_renames([source], RenameRules(prefix="x"))
    source.unlink()
    with pytest.raises(UnsafeOperation, match="cannot be accessed"):
        execute(plan)


def test_existing_destination_is_never_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    destination = tmp_path / "xa.txt"
    source.write_text("source")
    destination.write_text("keep")
    plan = plan_renames([source], RenameRules(prefix="x"))
    with pytest.raises(UnsafeOperation, match="already exists"):
        execute(plan)
    assert destination.read_text() == "keep"
    assert source.read_text() == "source"


def test_swap_can_be_undone(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a")
    second.write_text("b")
    history = History(tmp_path / "history.json")
    plan = [
        PlannedChange(first, second, FileStamp.from_path(first)),
        PlannedChange(second, first, FileStamp.from_path(second)),
    ]
    execute(plan, history)
    assert first.read_text() == "b"
    assert history.undo_latest() == []
    assert first.read_text() == "a"
    assert second.read_text() == "b"


def test_cancelled_operation_leaves_sources_untouched(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("a")
    plan = plan_renames([source], RenameRules(prefix="x"))
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(UnsafeOperation, match="cancelled"):
        execute(plan, cancel=cancel)
    assert source.read_text() == "a"


def test_mid_operation_failure_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a")
    second.write_text("b")
    plan = plan_renames([first, second], RenameRules(prefix="x"))
    original_rename = Path.rename
    calls = 0

    def flaky_rename(path: Path, target: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise PermissionError("simulated locked destination")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(UnsafeOperation, match="rolled back"):
        execute(plan)
    assert first.read_text() == "a"
    assert second.read_text() == "b"
