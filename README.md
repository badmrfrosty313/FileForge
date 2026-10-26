# FileForge

FileForge is a Windows-first desktop utility for previewing and safely executing batch file renames and organization. It never deletes files or silently overwrites a destination.

## Features

- Dark PySide6 desktop interface with file selection, rename preview, confirmation, and status feedback.
- Batch rename transformations: find/replace, prefix/suffix, sequential numbering, case conversion, and extension filters (engine support).
- Collision, invalid-name, Windows reserved-name, and changed-since-preview detection.
- Cycle-safe renames (including swaps) using temporary staging names.
- Extension/category organization previews, streamed SHA-256 duplicate detection, and JSON-backed undo journal.
- Pytest, Ruff, PyInstaller and Windows/Linux GitHub Actions CI.

## Screenshots

Screenshots will be added with the first Windows release. The application is functional without bundled sample user files.

## Install and run

Requires Python 3.11 or newer.

```bash
python -m pip install -e '.[dev]'
fileforge
```

## Usage

1. Use **Add Files** or **Add Folder** to select files.
2. Open **Rename**, enter a find/replace rule, and inspect the confirmation preview.
3. Confirm only when every destination is correct. FileForge revalidates files immediately before changing them.
4. Use the history journal to undo the latest completed operation if both source and destination state are still safe.

## Development

```bash
ruff check .
pytest -q
pyinstaller --noconfirm --windowed --name FileForge fileforge/app.py
```

The Windows executable is written to `dist/FileForge/FileForge.exe`.

## Safety notes

FileForge never auto-deletes duplicate files, never overwrites an existing destination, skips symlinks while scanning, and requires an explicit confirmation in the GUI. An interruption can leave temporary `.fileforge-*` names, which are intentionally retained for diagnosis rather than deleted automatically.

See [architecture.md](docs/architecture.md), [example-workflows.md](docs/example-workflows.md), and [release-notes.md](docs/release-notes.md).
