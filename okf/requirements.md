# Initial requirements

Requirement status is **proposed** unless stated otherwise.

## Functional

- **R1 — Create:** A user can create a note with a title and body.
- **R2 — Read:** A user can view a note and its updates/comments.
- **R3 — Update:** A user can edit note metadata and content.
- **R4 — Append:** A user can add a short update/comment to a note without rewriting its history.
- **R5 — Organize:** Notes can have a small amount of structure such as status, tags, and timestamps.
- **R6 — Find:** A user can list and search/filter notes sufficiently for a small shared collection.
- **R7 — Conflict safety:** A stale editor cannot silently overwrite a newer revision. The user must be shown a conflict and given a safe merge/retry path.
- **R8 — Shared access:** Any user who can reach the service can read and write according to the trusted-network model.
- **R9 — Export/backup:** Data can be backed up and restored using documented operations.
- **R10 — Compact hierarchy:** The primary view can show topics, streams/issues, child items, and recent comments in a compact expandable hierarchy.
- **R11 — Alternate views:** The system can support saved or shareable views ordered/filtered by priority and deadline, last update, and staleness.
- **R12 — Comment window:** A view can show one, two, or N recent comments per stream, with an action to reveal more.
- **R13 — Keyboard operation:** Navigation and common actions—add, edit, move, complete, expand/collapse, and show more—have keyboard shortcuts.
- **R14 — Markdown:** Descriptions, summaries, and comments accept Markdown and render it safely.
- **R15 — Shareable locations:** Users can link directly to a stream or to a specific ordering/filter/view state.
- **R16 — History:** Changes retain enough before/after information to support audit and targeted manual recovery.
- **R17 — External references:** Configured reference patterns can turn identifiers such as `BUG123` into safe links and rendered references.
- **R18 — Edit awareness:** The UI indicates when another user is editing a stream or comment, while still allowing independent objects to be edited concurrently.
- **R19 — Default priority view:** At every hierarchy level, the default view shows open items first, grouped by priority, with closed items optionally included afterward.
- **R20 — View recipes:** The system supports deadline-first, chronological/most-recently-touched, and stale-open views, each optionally flat or hierarchy-preserving.

## Non-functional

- **N1 — Simplicity:** Prefer a small number of moving parts and dependencies.
- **N2 — Performance:** Common list, read, create, and append operations should feel immediate on the intended internal network.
- **N3 — Durability:** A successful write must survive process restart and be included in the backup strategy.
- **N4 — Security:** Dependencies, build inputs, configuration, and exposed endpoints must be reviewable and minimized.
- **N5 — Operability:** Startup, health, logs, backup, restore, and upgrade procedures are documented.
- **N6 — Data portability:** The stored representation should be straightforward to inspect and export.

## Acceptance baseline

The first usable release should support creating and updating short notes, appending comments, compact hierarchy navigation, and safely handling two users editing the same object. Independent objects should remain editable concurrently. A deployment operator must be able to back up and restore the data using the deployment guide.
