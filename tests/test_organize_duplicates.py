from pathlib import Path

import pytest

from fileforge.duplicates import duplicate_groups, scan_files, sha256
from fileforge.organize import category_for, plan_organization, plan_quarantine


@pytest.mark.parametrize(
    ("extension", "category"),
    [
        ("jpg", "Images"),
        ("png", "Images"),
        ("svg", "Images"),
        ("pdf", "Documents"),
        ("docx", "Documents"),
        ("csv", "Documents"),
        ("mp3", "Audio"),
        ("flac", "Audio"),
        ("ogg", "Audio"),
        ("mp4", "Video"),
        ("mkv", "Video"),
        ("webm", "Video"),
        ("zip", "Archives"),
        ("7z", "Archives"),
        ("rar", "Archives"),
        ("py", "Code"),
        ("js", "Code"),
        ("json", "Code"),
        ("unknown", "Other"),
    ],
)
def test_categories(extension: str, category: str) -> None:
    assert category_for(Path(f"file.{extension}")) == category


def test_custom_organization_rules(tmp_path: Path) -> None:
    source = tmp_path / "book.epub"
    source.write_text("book")
    plan = plan_organization([source], tmp_path / "out", "custom", {"epub": "Books"})
    assert plan[0].destination == tmp_path / "out" / "Books" / "book.epub"


def test_unsafe_custom_folder_rejected(tmp_path: Path) -> None:
    source = tmp_path / "book.epub"
    source.write_text("book")
    with pytest.raises(ValueError):
        plan_organization([source], tmp_path / "out", "custom", {"epub": "../escape"})


def test_quarantine_skips_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("x")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("Symlinks are not available")
    plan = plan_quarantine([source, link], tmp_path / "quarantine")
    assert [change.source for change in plan] == [source.absolute()]


def test_recursive_scan_does_not_follow_directory_symlink(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "one.txt").write_text("1")
    link = tmp_path / "linked"
    try:
        link.symlink_to(folder, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks are not available")
    assert scan_files([tmp_path]) == [folder / "one.txt"]


def test_hash_is_streamed_and_stable(tmp_path: Path) -> None:
    path = tmp_path / "large.bin"
    path.write_bytes(b"abcdef" * 1000)
    assert sha256(path, chunk_size=7) == sha256(path, chunk_size=4096)


def test_duplicate_group_savings(tmp_path: Path) -> None:
    paths = []
    for index in range(3):
        path = tmp_path / f"copy-{index}.bin"
        path.write_bytes(b"same")
        paths.append(path)
    groups = duplicate_groups(paths)
    assert len(groups) == 1
    assert groups[0].recoverable_bytes == 8


def test_same_size_different_content_not_duplicate(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.write_bytes(b"ab")
    second.write_bytes(b"cd")
    assert duplicate_groups([first, second]) == []
