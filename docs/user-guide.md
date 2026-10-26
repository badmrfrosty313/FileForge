# User guide

## Add files

Use **Add Files**, **Add Folder**, or drag local paths into the inventory. Folder scanning does not follow symbolic links or junction-like entries. Use **Remove Selected** to remove rows from FileForge without changing files on disk.

## Rename

Combine find/replace, prefix, suffix, case conversion, extension filtering, and sequential numbering. The preview updates live. FileForge omits unchanged names and blocks duplicate destinations, reserved Windows names, existing targets, and stale sources.

## Organize

Choose extension or broad category grouping, select a destination, and preview every move. The engine also supports custom extension-to-folder rules for integrations. New folders are created only after confirmation.

## Duplicates and quarantine

Scanning is read-only. Files are grouped by size before streamed SHA-256 comparison. Potential savings assumes keeping one file per group. Select rows and choose **Quarantine Selected** to move files to a recovery folder; FileForge never permanently deletes them.

## History and undo

History records timestamps, operation kinds, statuses, file counts, and failure details. Select a completed row and choose **Undo Selected**. Undo stops if a file is missing, modified, or an unrelated file occupies the original path.

## Shortcuts

- `Ctrl+O`: add files
- `Ctrl+L`: clear the inventory
- `Ctrl+Z`: undo the selected or latest reversible operation
