from pathlib import Path

import pytest

from fileforge.duplicates import find_duplicates
from fileforge.history import History
from fileforge.operations import UnsafeOperation, execute
from fileforge.organize import plan_organization
from fileforge.rename import RenameRules, plan_renames, validate_plan
from fileforge.validation import validate_filename


def write(path: Path, value: bytes = b"data") -> Path:
    path.write_bytes(value)
    return path


@pytest.mark.parametrize(("name", "invalid"), [("good.txt", False), ("CON.txt", True), ("a?.txt", True), ("tail.", True)])
def test_filename_validation(name: str, invalid: bool) -> None:
    assert (validate_filename(name) is not None) is invalid


def test_rename_preview_and_execute(tmp_path: Path) -> None:
    source = write(tmp_path / "Draft.txt")
    plan = plan_renames([source], RenameRules(find="Draft", replace="Final", prefix="v_"))
    assert plan[0].destination.name == "v_Final.txt"
    execute(plan)
    assert (tmp_path / "v_Final.txt").read_bytes() == b"data"


def test_swaps_are_safe(tmp_path: Path) -> None:
    a, b = write(tmp_path / "a.txt", b"a"), write(tmp_path / "b.txt", b"b")
    from fileforge.models import FileStamp, PlannedChange
    plan = [PlannedChange(a, b, FileStamp.from_path(a)), PlannedChange(b, a, FileStamp.from_path(b))]
    execute(plan)
    assert a.read_bytes() == b"b" and b.read_bytes() == b"a"


def test_collision_and_changed_preview_rejected(tmp_path: Path) -> None:
    a = write(tmp_path / "a.txt")
    write(tmp_path / "b.txt")
    plan = plan_renames([a], RenameRules(find="a", replace="b"))
    assert validate_plan(plan)
    plan = plan_renames([a], RenameRules(prefix="x"))
    a.write_bytes(b"changed")
    with pytest.raises(UnsafeOperation):
        execute(plan)


def test_organize_creates_destination(tmp_path: Path) -> None:
    source = write(tmp_path / "photo.jpg")
    plan = plan_organization([source], tmp_path / "organized")
    execute(plan, kind="organize")
    assert (tmp_path / "organized" / "JPG" / "photo.jpg").exists()


def test_duplicates_empty_and_same_size_different_data(tmp_path: Path) -> None:
    a, b, c, d = (write(tmp_path / "a", b""), write(tmp_path / "b", b""), write(tmp_path / "c", b"ab"), write(tmp_path / "d", b"cd"))
    groups = find_duplicates([a, b, c, d])
    assert list(groups.values()) == [[a, b]]


def test_undo_and_unsafe_undo(tmp_path: Path) -> None:
    source = write(tmp_path / "a.txt")
    history = History(tmp_path / "history.json")
    execute(plan_renames([source], RenameRules(prefix="x")), history)
    assert history.undo_latest() == []
    assert source.exists()
    execute(plan_renames([source], RenameRules(prefix="x")), history)
    source.write_text("new")
    assert history.undo_latest()
