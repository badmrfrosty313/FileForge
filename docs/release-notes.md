# FileForge 1.0.0 release notes

FileForge 1.0 turns the initial safety engine into a complete desktop workflow. All four application areas are operational, lengthy scans and writes run outside the GUI thread, and file-changing operations use preview, confirmation, stale-state validation, journaling, and rollback.

Highlights include composable batch renaming, extension/category organization, recursive duplicate verification, recoverable quarantine, persistent selectable history, and cycle-safe undo. The Windows bundle is produced by the CI packaging job and smoke-tested with `--version` before upload.

Native Windows behavior is validated by automated Windows CI; it has not been manually certified on physical Windows hardware in this development environment.
