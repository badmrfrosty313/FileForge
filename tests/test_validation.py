from pathlib import Path

import pytest

from fileforge.validation import is_within, validate_filename


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("report.txt", True),
        ("archive.tar.gz", True),
        ("résumé.pdf", True),
        ("name-with-dashes", True),
        ("under_score.csv", True),
        ("space inside.txt", True),
        ("1", True),
        (".gitignore", True),
        ("", False),
        (".", False),
        ("..", False),
        (" leading.txt", False),
        ("trailing.txt ", False),
        ("trailing.", False),
        ("a/b.txt", False),
        ("a\\b.txt", False),
        ("a:b.txt", False),
        ("a*b.txt", False),
        ("a?b.txt", False),
        ("a<b.txt", False),
        ("a>b.txt", False),
        ('a"b.txt', False),
        ("a|b.txt", False),
        ("CON", False),
        ("con.txt", False),
        ("PRN.log", False),
        ("AUX", False),
        ("NUL.data", False),
        ("COM1.txt", False),
        ("COM9", False),
        ("LPT1.doc", False),
        ("LPT9", False),
        ("COM10.txt", True),
        ("LPT10.txt", True),
    ],
)
def test_windows_filename_rules(name: str, valid: bool) -> None:
    assert (validate_filename(name) is None) is valid


def test_path_boundary_accepts_descendant(tmp_path: Path) -> None:
    assert is_within(tmp_path / "child" / "file.txt", tmp_path)


def test_path_boundary_rejects_sibling(tmp_path: Path) -> None:
    assert not is_within(tmp_path.parent / f"{tmp_path.name}-other" / "file.txt", tmp_path)
