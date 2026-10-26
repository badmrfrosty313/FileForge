from pathlib import Path

import pytest

from fileforge.rename import RenameRules, plan_renames, transformed_name, validate_plan


@pytest.mark.parametrize(
    ("filename", "rules", "index", "expected"),
    [
        ("Draft.txt", RenameRules(find="Draft", replace="Final"), 0, "Final.txt"),
        ("aaa.txt", RenameRules(find="a", replace="b"), 0, "bbb.txt"),
        ("Photo.JPG", RenameRules(prefix="2026_"), 0, "2026_Photo.JPG"),
        ("Photo.JPG", RenameRules(suffix="_edited"), 0, "Photo_edited.JPG"),
        ("One.TXT", RenameRules(case="lower"), 0, "one.TXT"),
        ("One.TXT", RenameRules(case="upper"), 0, "ONE.TXT"),
        ("hello world.md", RenameRules(case="title"), 0, "Hello World.md"),
        ("a.txt", RenameRules(numbering_start=1), 0, "a1.txt"),
        ("a.txt", RenameRules(numbering_start=1, numbering_padding=3), 0, "a001.txt"),
        ("a.txt", RenameRules(numbering_start=8, numbering_padding=2), 3, "a11.txt"),
        ("a.tar.gz", RenameRules(prefix="x-"), 0, "x-a.tar.gz"),
        (".env", RenameRules(prefix="old-"), 0, "old-.env"),
        ("Mix.txt", RenameRules(prefix="p-", suffix="-s", case="lower"), 0, "p-mix-s.txt"),
        ("cat.txt", RenameRules(find="cat", replace="dog", suffix="2"), 0, "dog2.txt"),
        ("x", RenameRules(numbering_start=0, numbering_padding=2), 5, "x05"),
    ],
)
def test_transformations(filename: str, rules: RenameRules, index: int, expected: str) -> None:
    assert transformed_name(Path(filename), rules, index) == expected


def test_extension_filter_accepts_without_dot(tmp_path: Path) -> None:
    jpg = tmp_path / "a.jpg"
    txt = tmp_path / "b.txt"
    jpg.write_text("image")
    txt.write_text("text")
    plan = plan_renames([jpg, txt], RenameRules(prefix="x", extension="jpg"))
    assert [change.source.name for change in plan] == ["a.jpg"]


def test_unchanged_names_are_not_planned(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("x")
    assert plan_renames([source], RenameRules()) == []


def test_duplicate_destinations_are_rejected(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a")
    second.write_text("b")
    plan = plan_renames([first, second], RenameRules(find="a", replace="same", prefix=""))
    # Force a genuine duplicate through a second transformation.
    from fileforge.models import PlannedChange

    duplicate = PlannedChange(second.absolute(), plan[0].destination, plan[0].stamp)
    assert any("Multiple files" in error for error in validate_plan([plan[0], duplicate]))
