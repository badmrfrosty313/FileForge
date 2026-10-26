# Architecture

`fileforge.rename` produces immutable, stamped change plans. `validation` rejects invalid Windows names, collisions, and changes made after preview. `operations` stages every source under a unique temporary filename before applying destinations, making rename cycles safe. `organize` produces move plans, `duplicates` streams SHA-256 digests, and `history` persists completed changes for conservative undo. The GUI is a thin PySide6 client over these modules; filesystem work belongs in the engine and can be run outside the GUI thread as the interface expands.

The history journal defaults to `~/.fileforge/history.json`. It contains paths and operation metadata, not file contents.
