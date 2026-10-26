from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fileforge.duplicates import DuplicateGroup, duplicate_groups, scan_files
from fileforge.history import History
from fileforge.models import PlannedChange
from fileforge.operations import UnsafeOperation, execute
from fileforge.organize import plan_organization, plan_quarantine
from fileforge.rename import RenameRules, plan_renames, validate_plan


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    return f"{size} B"


class FileTable(QTableWidget):
    paths_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__(0, 5)
        self.setHorizontalHeaderLabels(["Name", "Extension", "Size", "Location", "Status"])
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTableWidget.DropOnly)

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()


class DuplicateWorker(QThread):
    progress = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, roots: list[Path]) -> None:
        super().__init__()
        self.roots = roots
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            files = scan_files(self.roots, self.cancel_event)
            groups = duplicate_groups(
                files,
                self.cancel_event,
                lambda current, total: self.progress.emit(current, total),
            )
            self.completed.emit(groups)
        except Exception as exc:  # pragma: no cover - defensive thread boundary
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.cancel_event.set()


class OperationWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, changes: list[PlannedChange], history: History, kind: str) -> None:
        super().__init__()
        self.changes = changes
        self.history = history
        self.kind = kind
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            self.completed.emit(execute(self.changes, self.history, self.kind, self.cancel_event))
        except UnsafeOperation as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.cancel_event.set()


class FileForgeWindow(QMainWindow):
    def __init__(self, history: History | None = None) -> None:
        super().__init__()
        self.paths: list[Path] = []
        self.scan_roots: list[Path] = []
        self.history = history or History()
        self.settings = QSettings("FileForge", "FileForge")
        self.duplicate_groups: list[DuplicateGroup] = []
        self.worker: QThread | None = None
        self.setWindowTitle("FileForge 1.0")
        self.resize(1180, 760)
        self.setAcceptDrops(True)
        self._build_ui()
        self._build_actions()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 12)
        layout.setSpacing(12)
        title = QLabel("FileForge")
        title.setObjectName("title")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        toolbar.addWidget(self._button("Add Files", self.add_files))
        toolbar.addWidget(self._button("Add Folder", self.add_folder))
        toolbar.addWidget(self._button("Remove Selected", self.remove_selected, secondary=True))
        toolbar.addWidget(self._button("Clear", self.clear, secondary=True))
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.file_table = FileTable()
        self.file_table.paths_dropped.connect(self.add_dropped_paths)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.file_context_menu)
        layout.addWidget(self.file_table, 2)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._rename_tab(), "Rename")
        self.tabs.addTab(self._organize_tab(), "Organize")
        self.tabs.addTab(self._duplicates_tab(), "Duplicates")
        self.tabs.addTab(self._history_tab(), "History")
        layout.addWidget(self.tabs, 3)
        footer = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(280)
        self.status = QLabel("Drop files or folders here to begin.")
        footer.addWidget(self.status, 1)
        footer.addWidget(self.progress)
        layout.addLayout(footer)
        self.setCentralWidget(root)

    def _build_actions(self) -> None:
        add_action = QAction("Add files", self)
        add_action.setShortcut(QKeySequence.Open)
        add_action.triggered.connect(self.add_files)
        self.addAction(add_action)
        clear_action = QAction("Clear", self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.triggered.connect(self.clear)
        self.addAction(clear_action)
        undo_action = QAction("Undo latest operation", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo_selected)
        self.addAction(undo_action)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background: #171a21; color: #e8ecf3; font-size: 13px; }
            QLabel#title { font-size: 27px; font-weight: 700; color: #7db5ff; }
            QPushButton { background: #397ce8; border: 0; border-radius: 6px; padding: 8px 14px; font-weight: 600; }
            QPushButton:hover { background: #4b8df5; }
            QPushButton[secondary='true'] { background: #303641; }
            QLineEdit, QComboBox, QSpinBox, QTableWidget { background: #20252e; border: 1px solid #353d49; border-radius: 5px; padding: 5px; }
            QHeaderView::section { background: #292f39; padding: 7px; border: 0; }
            QTabWidget::pane { border: 1px solid #353d49; }
            QTabBar::tab { background: #242a33; padding: 9px 18px; }
            QTabBar::tab:selected { background: #397ce8; }
            """
        )

    def _button(self, text: str, handler, secondary: bool = False) -> QPushButton:  # type: ignore[no-untyped-def]
        button = QPushButton(text)
        button.setProperty("secondary", secondary)
        button.clicked.connect(handler)
        return button

    @staticmethod
    def _table(columns: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        return table

    def _rename_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        self.prefix_input = QLineEdit()
        self.suffix_input = QLineEdit()
        self.extension_input = QLineEdit()
        self.extension_input.setPlaceholderText("e.g. jpg (blank means all)")
        self.case_combo = QComboBox()
        self.case_combo.addItems(["keep", "lower", "upper", "title"])
        number_row = QHBoxLayout()
        self.number_check = QCheckBox("Enable")
        self.number_start = QSpinBox()
        self.number_start.setRange(0, 999999)
        self.number_start.setValue(1)
        self.number_padding = QSpinBox()
        self.number_padding.setRange(1, 8)
        self.number_padding.setValue(3)
        number_row.addWidget(self.number_check)
        number_row.addWidget(QLabel("Start"))
        number_row.addWidget(self.number_start)
        number_row.addWidget(QLabel("Padding"))
        number_row.addWidget(self.number_padding)
        form.addRow("Find", self.find_input)
        form.addRow("Replace", self.replace_input)
        form.addRow("Prefix", self.prefix_input)
        form.addRow("Suffix", self.suffix_input)
        form.addRow("Case", self.case_combo)
        form.addRow("Extension filter", self.extension_input)
        form.addRow("Sequential numbers", number_row)
        layout.addLayout(form)
        self.rename_preview = self._table(["Original", "Proposed", "Validation"])
        layout.addWidget(self.rename_preview)
        layout.addWidget(self._button("Apply Rename…", self.apply_rename))
        for control in (
            self.find_input,
            self.replace_input,
            self.prefix_input,
            self.suffix_input,
            self.extension_input,
        ):
            control.textChanged.connect(self.refresh_rename_preview)
        self.case_combo.currentTextChanged.connect(self.refresh_rename_preview)
        self.number_check.toggled.connect(self.refresh_rename_preview)
        self.number_start.valueChanged.connect(self.refresh_rename_preview)
        self.number_padding.valueChanged.connect(self.refresh_rename_preview)
        return widget

    def _organize_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        self.organize_mode = QComboBox()
        self.organize_mode.addItems(["extension", "category"])
        self.organize_destination = QLineEdit(str(self.settings.value("organize_destination", "")))
        controls.addWidget(QLabel("Mode"))
        controls.addWidget(self.organize_mode)
        controls.addWidget(QLabel("Destination"))
        controls.addWidget(self.organize_destination, 1)
        controls.addWidget(self._button("Browse", self.choose_organize_destination, secondary=True))
        controls.addWidget(self._button("Preview", self.refresh_organize_preview, secondary=True))
        layout.addLayout(controls)
        self.organize_preview = self._table(["Source", "Destination", "Status"])
        layout.addWidget(self.organize_preview)
        layout.addWidget(self._button("Move Files…", self.apply_organization))
        self.organize_mode.currentTextChanged.connect(self.refresh_organize_preview)
        return widget

    def _duplicates_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        controls.addWidget(self._button("Scan for Duplicates", self.start_duplicate_scan))
        controls.addWidget(self._button("Cancel", self.cancel_worker, secondary=True))
        controls.addWidget(self._button("Open Containing Folder", self.open_selected_folder, secondary=True))
        controls.addWidget(self._button("Quarantine Selected…", self.quarantine_selected, secondary=True))
        controls.addStretch()
        self.savings_label = QLabel("Potential savings: 0 B")
        controls.addWidget(self.savings_label)
        layout.addLayout(controls)
        self.duplicates_table = self._table(["Group", "File", "Size", "SHA-256"])
        layout.addWidget(self.duplicates_table)
        return widget

    def _history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        controls.addWidget(self._button("Refresh", self.refresh_history, secondary=True))
        controls.addWidget(self._button("Undo Selected", self.undo_selected))
        controls.addStretch()
        layout.addLayout(controls)
        self.history_table = self._table(["Time", "Operation", "Files", "Status", "Details"])
        layout.addWidget(self.history_table)
        self.refresh_history()
        return widget

    def add_files(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(self, "Add files")
        self.add_paths([Path(name) for name in names])

    def add_folder(self) -> None:
        name = QFileDialog.getExistingDirectory(self, "Add folder")
        if name:
            self.add_paths([Path(name)])

    def add_dropped_paths(self, paths: list[Path]) -> None:
        self.add_paths(paths)

    def add_paths(self, paths: list[Path]) -> None:
        self.scan_roots.extend(path for path in paths if path not in self.scan_roots)
        discovered = scan_files(paths)
        existing = {str(path) for path in self.paths}
        self.paths.extend(path for path in discovered if str(path) not in existing)
        self.paths = sorted(set(self.paths), key=lambda path: str(path).lower())
        self.refresh_file_table()

    def refresh_file_table(self) -> None:
        self.file_table.setSortingEnabled(False)
        self.file_table.setRowCount(len(self.paths))
        for row, path in enumerate(self.paths):
            try:
                size, status = path.stat().st_size, "Ready"
            except OSError:
                size, status = 0, "Unavailable"
            values = [path.name, path.suffix.lstrip("."), human_size(size), str(path.parent), status]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, str(path))
                self.file_table.setItem(row, column, item)
        self.file_table.setSortingEnabled(True)
        self.status.setText(f"{len(self.paths)} file(s) loaded")
        self.refresh_rename_preview()
        self.refresh_organize_preview()

    def selected_file_paths(self) -> list[Path]:
        rows = {index.row() for index in self.file_table.selectionModel().selectedRows()}
        return [Path(self.file_table.item(row, 0).data(Qt.UserRole)) for row in rows]

    def remove_selected(self) -> None:
        selected = set(self.selected_file_paths())
        self.paths = [path for path in self.paths if path not in selected]
        self.refresh_file_table()

    def clear(self) -> None:
        self.paths.clear()
        self.scan_roots.clear()
        self.duplicate_groups.clear()
        self.refresh_file_table()
        self.duplicates_table.setRowCount(0)
        self.status.setText("List cleared")

    def file_context_menu(self, position) -> None:  # type: ignore[no-untyped-def]
        menu = QMenu(self)
        menu.addAction("Remove selected", self.remove_selected)
        menu.addAction("Open containing folder", self.open_selected_folder)
        menu.exec(self.file_table.viewport().mapToGlobal(position))

    def rename_rules(self) -> RenameRules:
        return RenameRules(
            find=self.find_input.text(),
            replace=self.replace_input.text(),
            prefix=self.prefix_input.text(),
            suffix=self.suffix_input.text(),
            numbering_start=self.number_start.value() if self.number_check.isChecked() else None,
            numbering_padding=self.number_padding.value(),
            case=self.case_combo.currentText(),
            extension=self.extension_input.text(),
        )

    def refresh_rename_preview(self) -> None:
        if not hasattr(self, "rename_preview"):
            return
        plan = plan_renames(self.paths, self.rename_rules())
        errors = validate_plan(plan)
        self.rename_preview.setRowCount(len(plan))
        for row, change in enumerate(plan):
            status = "Ready" if not errors else "Review validation messages"
            for column, value in enumerate((str(change.source), str(change.destination), status)):
                self.rename_preview.setItem(row, column, QTableWidgetItem(value))

    def apply_rename(self) -> None:
        plan = plan_renames(self.paths, self.rename_rules())
        self.confirm_and_run(plan, "rename", "Rename files")

    def choose_organize_destination(self) -> None:
        name = QFileDialog.getExistingDirectory(self, "Choose organization destination")
        if name:
            self.organize_destination.setText(name)
            self.settings.setValue("organize_destination", name)
            self.refresh_organize_preview()

    def organization_plan(self) -> list[PlannedChange]:
        destination = self.organize_destination.text().strip()
        if not destination:
            return []
        return plan_organization(self.paths, Path(destination), self.organize_mode.currentText())

    def refresh_organize_preview(self) -> None:
        if not hasattr(self, "organize_preview"):
            return
        try:
            plan = self.organization_plan()
            errors = validate_plan(plan)
        except ValueError as exc:
            plan, errors = [], [str(exc)]
        self.organize_preview.setRowCount(len(plan))
        for row, change in enumerate(plan):
            status = "Ready" if not errors else "Conflict"
            for column, value in enumerate((str(change.source), str(change.destination), status)):
                self.organize_preview.setItem(row, column, QTableWidgetItem(value))

    def apply_organization(self) -> None:
        self.confirm_and_run(self.organization_plan(), "organize", "Move files")

    def confirm_and_run(self, plan: list[PlannedChange], kind: str, title: str) -> None:
        errors = validate_plan(plan)
        if not plan:
            QMessageBox.information(self, title, "There are no changes to apply.")
            return
        if errors:
            QMessageBox.warning(self, "Unsafe operation", "\n".join(errors))
            return
        message = f"Apply {len(plan)} changes? Existing files will never be overwritten."
        if QMessageBox.question(self, title, message) != QMessageBox.Yes:
            return
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        worker = OperationWorker(plan, self.history, kind)
        worker.completed.connect(self.operation_completed)
        worker.failed.connect(self.operation_failed)
        worker.finished.connect(self.worker_finished)
        self.worker = worker
        worker.start()

    def operation_completed(self, result) -> None:  # type: ignore[no-untyped-def]
        destinations = {change.source: change.destination for change in result.completed}
        self.paths = [destinations.get(path.absolute(), path) for path in self.paths]
        self.status.setText(f"Completed {len(result.completed)} changes safely.")
        self.refresh_file_table()
        self.refresh_history()

    def operation_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Operation stopped", message)
        self.status.setText("Operation stopped; see History for details.")
        self.refresh_file_table()
        self.refresh_history()

    def worker_finished(self) -> None:
        self.progress.setVisible(False)
        self.worker = None

    def start_duplicate_scan(self) -> None:
        roots = self.scan_roots or self.paths
        if not roots:
            QMessageBox.information(self, "Duplicates", "Add files or folders before scanning.")
            return
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        worker = DuplicateWorker(roots)
        worker.progress.connect(self.duplicate_progress)
        worker.completed.connect(self.show_duplicate_results)
        worker.failed.connect(self.operation_failed)
        worker.finished.connect(self.worker_finished)
        self.worker = worker
        worker.start()

    def duplicate_progress(self, current: int, total: int) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(current)
        self.status.setText(f"Hashing candidate {current} of {total}")

    def show_duplicate_results(self, groups: list[DuplicateGroup]) -> None:
        self.duplicate_groups = groups
        rows = sum(len(group.paths) for group in groups)
        self.duplicates_table.setSortingEnabled(False)
        self.duplicates_table.setRowCount(rows)
        row = 0
        for group_index, group in enumerate(groups, 1):
            for path in group.paths:
                values = [str(group_index), str(path), human_size(group.size), group.digest]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setData(Qt.UserRole, str(path))
                    self.duplicates_table.setItem(row, column, item)
                row += 1
        self.duplicates_table.setSortingEnabled(True)
        savings = sum(group.recoverable_bytes for group in groups)
        self.savings_label.setText(f"Potential savings: {human_size(savings)}")
        self.status.setText(f"Found {len(groups)} duplicate group(s); no files were changed.")

    def cancel_worker(self) -> None:
        if hasattr(self.worker, "cancel"):
            self.worker.cancel()  # type: ignore[union-attr]
            self.status.setText("Cancellation requested…")

    def selected_duplicate_paths(self) -> list[Path]:
        rows = {index.row() for index in self.duplicates_table.selectionModel().selectedRows()}
        return [Path(self.duplicates_table.item(row, 1).data(Qt.UserRole)) for row in rows]

    def quarantine_selected(self) -> None:
        selected = self.selected_duplicate_paths()
        if not selected:
            QMessageBox.information(self, "Quarantine", "Select duplicate rows to quarantine.")
            return
        destination = QFileDialog.getExistingDirectory(self, "Choose recoverable quarantine folder")
        if destination:
            plan = plan_quarantine(selected, Path(destination))
            self.confirm_and_run(plan, "quarantine", "Quarantine duplicates")

    def open_selected_folder(self) -> None:
        paths = self.selected_duplicate_paths() or self.selected_file_paths()
        if not paths:
            return
        folder = str(paths[0].parent)
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError as exc:
            QMessageBox.warning(self, "Open folder", str(exc))

    def refresh_history(self) -> None:
        if not hasattr(self, "history_table"):
            return
        entries = self.history.entries()
        self.history_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                entry.created_at.replace("T", " ")[:19],
                entry.kind.title(),
                str(len(entry.changes)),
                entry.status.title(),
                entry.message or "Completed successfully",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, entry.id)
                self.history_table.setItem(row, column, item)

    def undo_selected(self) -> None:
        rows = self.history_table.selectionModel().selectedRows() if hasattr(self, "history_table") else []
        entry_id = self.history_table.item(rows[0].row(), 0).data(Qt.UserRole) if rows else None
        entry = next(
            (candidate for candidate in self.history.entries() if candidate.id == entry_id),
            self.history.latest(),
        )
        if QMessageBox.question(self, "Undo operation", "Restore files from the selected operation?") != QMessageBox.Yes:
            return
        errors = self.history.undo(entry_id)
        if errors:
            QMessageBox.warning(self, "Undo unavailable", "\n".join(errors))
        else:
            self.status.setText("Operation undone safely.")
            self.refresh_history()
            if entry:
                restored = {change.destination: change.source for change in entry.changes}
                self.paths = [restored.get(path, path) for path in self.paths]
            self.paths = [path for path in self.paths if path.exists()]
            self.refresh_file_table()


def main() -> int:
    parser = argparse.ArgumentParser(description="FileForge desktop file manager")
    parser.add_argument("--version", action="version", version="FileForge 1.0.0")
    parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("FileForge")
    window = FileForgeWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
