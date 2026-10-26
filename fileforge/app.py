from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fileforge.history import History
from fileforge.operations import UnsafeOperation, execute
from fileforge.rename import RenameRules, plan_renames, validate_plan


class FileForgeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[Path] = []
        self.history = History()
        self.setWindowTitle("FileForge")
        self.resize(920, 620)
        self.setStyleSheet("QWidget { background:#1e2127; color:#e6e9ef; } QPushButton { padding:8px; background:#3b82f6; border:0; border-radius:4px; }")
        root = QWidget()
        layout = QVBoxLayout(root)
        buttons = QHBoxLayout()
        for label, handler in (("Add Files", self.add_files), ("Add Folder", self.add_folder), ("Clear List", self.clear)):
            button = QPushButton(label); button.clicked.connect(handler); buttons.addWidget(button)
        layout.addLayout(buttons)
        self.files = QListWidget(); self.files.setAcceptDrops(True); layout.addWidget(self.files)
        tabs = QTabWidget(); tabs.addTab(self._rename_tab(), "Rename"); tabs.addTab(QLabel("Organization previews are available through the engine."), "Organize"); tabs.addTab(QLabel("Duplicate detection is read-only."), "Duplicates"); tabs.addTab(QLabel("Undo the latest completed operation safely."), "History")
        layout.addWidget(tabs)
        self.status = QLabel("Add files or folders to begin."); layout.addWidget(self.status)
        self.setCentralWidget(root)

    def _rename_tab(self) -> QWidget:
        widget = QWidget(); layout = QVBoxLayout(widget)
        self.find = QLineEdit(); self.find.setPlaceholderText("Find")
        self.replace = QLineEdit(); self.replace.setPlaceholderText("Replace")
        preview = QPushButton("Preview and Rename"); preview.clicked.connect(self.rename)
        layout.addWidget(self.find); layout.addWidget(self.replace); layout.addWidget(preview)
        return widget

    def add_files(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(self, "Add files")
        self.add_paths([Path(name) for name in names])

    def add_folder(self) -> None:
        name = QFileDialog.getExistingDirectory(self, "Add folder")
        if name:
            root = Path(name)
            self.add_paths([p for p in root.rglob("*") if p.is_file() and not p.is_symlink()])

    def add_paths(self, paths: list[Path]) -> None:
        self.paths.extend(p for p in paths if p not in self.paths)
        self.files.clear(); self.files.addItems([str(p) for p in self.paths])
        self.status.setText(f"{len(self.paths)} file(s) selected")

    def clear(self) -> None:
        self.paths.clear(); self.files.clear(); self.status.setText("List cleared")

    def rename(self) -> None:
        plan = plan_renames(self.paths, RenameRules(find=self.find.text(), replace=self.replace.text()))
        errors = validate_plan(plan)
        if errors:
            QMessageBox.warning(self, "Unsafe rename", "\n".join(errors)); return
        preview = "\n".join(f"{c.source.name} → {c.destination.name}" for c in plan)
        if QMessageBox.question(self, "Confirm rename", preview) == QMessageBox.Yes:
            try:
                execute(plan, self.history)
                self.add_paths([]); self.status.setText("Rename completed and recorded for undo.")
            except UnsafeOperation as exc:
                QMessageBox.critical(self, "Rename stopped", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="FileForge desktop file manager")
    parser.add_argument("--version", action="version", version="FileForge 0.1.0")
    parser.parse_args()
    app = QApplication(sys.argv)
    window = FileForgeWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
