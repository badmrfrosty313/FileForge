# Architecture

`fileforge.rename` and `fileforge.organize` produce immutable, stamped change plans. `validation` rejects invalid Windows names, collisions, symlinks, unsafe destinations, and files changed after preview. `operations` serializes writes, stages every source under a unique temporary filename, applies the plan, and attempts reverse-order rollback on failure. `transfer` uses atomic no-clobber hard links on one filesystem and exclusive streamed copies across filesystems. This makes cycles and swaps safe without overwriting unrelated files.

`duplicates` walks directories without following symlinked directories, groups candidates by size, and streams SHA-256 reads with cancellation and progress callbacks. `history` uses atomic JSON replacement to persist completed and failed operations. Undo revalidates file stamps and uses its own staging transaction so rename cycles remain reversible.

`app` is the PySide6 presentation and service coordination layer. Hash scans and write operations run in `QThread` workers. The GUI receives immutable results and updates tables on the main thread.

On Windows, history defaults to `%LOCALAPPDATA%\FileForge\history.json`; other systems use the local application-data directory. The journal contains paths, timestamps, stamps, and status—not file contents or hashes from unrelated files.
