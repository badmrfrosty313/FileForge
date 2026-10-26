import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_gui_starts() -> None:
    from PySide6.QtWidgets import QApplication

    from fileforge.app import FileForgeWindow

    _app = QApplication.instance() or QApplication([])
    window = FileForgeWindow()
    assert window.windowTitle() == "FileForge"
    window.close()
