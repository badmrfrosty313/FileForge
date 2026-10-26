# FileForge 1.0.0 release notes

FileForge 1.0 turns the initial safety engine into a complete desktop workflow. All four application areas are operational, lengthy scans and writes run outside the GUI thread, and file-changing operations use preview, confirmation, stale-state validation, journaling, and rollback.

Highlights include composable batch renaming, extension/category organization, recursive duplicate verification, recoverable quarantine, persistent selectable history, and cycle-safe undo. The Windows bundle is produced by the CI packaging job and smoke-tested with `--version` before upload.

Native Windows behavior is validated by automated Windows CI; it has not been manually certified on physical Windows hardware in this development environment.

## Install and use

Download `FileForge-Setup-1.0.0.exe` to install FileForge with a Start Menu shortcut and an optional desktop shortcut. The installer is unsigned. Windows may display a SmartScreen warning; review the publisher and download source before continuing.

Alternatively, extract `FileForge-Portable-1.0.0.zip` and run `FileForge.exe` from the included directory. Keep all files in that directory together.

Verify downloads against `SHA256SUMS.txt`. Standard uninstallation removes application files while preserving FileForge history stored under the user application-data directory.

## Verification scope

Windows CI builds the executable and installer, checks the portable archive, installs silently, launches the installed executable with `--version`, runs the uninstaller, and verifies user history remains. The FileForge GUI was also launched and visually verified on Windows by the release owner.
