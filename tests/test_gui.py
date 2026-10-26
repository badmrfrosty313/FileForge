import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_gui_starts() -> None:
    from PySide6.QtWidgets import QApplication

    from fileforge.app import FileForgeWindow

    _app = QApplication.instance() or QApplication([])
    window = FileForgeWindow()
    assert window.windowTitle() == "FileForge 1.0"
    assert window.tabs.count() == 4
    window.close()


def test_file_addition_updates_inventory(tmp_path: Path) -> None:
    from PySide6.QtWidgets import QApplication

    from fileforge.app import FileForgeWindow
    from fileforge.history import History

    _app = QApplication.instance() or QApplication([])
    source = tmp_path / "report.txt"
    source.write_text("report")
    window = FileForgeWindow(History(tmp_path / "history.json"))
    window.add_paths([source])
    assert window.file_table.rowCount() == 1
    assert window.file_table.item(0, 0).text() == "report.txt"
    window.close()


def test_live_rename_preview_updates(tmp_path: Path) -> None:
    from PySide6.QtWidgets import QApplication

    from fileforge.app import FileForgeWindow
    from fileforge.history import History

    _app = QApplication.instance() or QApplication([])
    source = tmp_path / "draft.txt"
    source.write_text("draft")
    window = FileForgeWindow(History(tmp_path / "history.json"))
    window.add_paths([source])
    window.find_input.setText("draft")
    window.replace_input.setText("final")
    assert window.rename_preview.item(0, 1).text().endswith("final.txt")
    window.close()


def test_clear_removes_inventory(tmp_path: Path) -> None:
    from PySide6.QtWidgets import QApplication

    from fileforge.app import FileForgeWindow

    _app = QApplication.instance() or QApplication([])
    source = tmp_path / "one.txt"
    source.write_text("one")
    window = FileForgeWindow()
    window.add_paths([source])
    window.clear()
    assert window.file_table.rowCount() == 0
    assert window.paths == []
    window.close()
