# Initial requirements

Requirement status is **proposed** unless stated otherwise.

## Functional

- **R1 — Create:** A user can create a note with a title and body.
- **R2 — Read:** A user can view a note and its updates/comments.
- **R3 — Update:** A user can edit note metadata and content, including an ordered owner list and optional date-only deadline.
- **R4 — Append:** A user can add a short update/comment to a note without rewriting its history.
- **R5 — Organize:** Notes can have a small amount of structure such as status, tags, timestamps, owners, and deadlines. Status is one of `open`, `resolved`, or `no_action`; tags are an ordered list of non-empty strings.
- **R6 — Find:** A user can list and search/filter notes sufficiently for a small shared collection.
- **R7 — Conflict safety:** A stale editor cannot silently overwrite a newer revision. The user must be shown a conflict and given a safe merge/retry path.
- **R8 — Shared access:** Any user who can reach the service can read and write according to the trusted-network model.
- **R9 — Export/backup:** Data can be backed up and restored using documented operations.
- **R10 — Compact hierarchy:** The primary view can show topics, streams/issues, child items, and recent comments in a compact expandable hierarchy.
- **R11 — Alternate views:** The system can support saved or shareable views ordered/filtered by priority and deadline, last update, and staleness.
- **R12 — Comment window:** A view can show one, two, or N recent comments per stream, with an action to reveal more.
- **R13 — Keyboard operation:** Navigation and common actions—add, edit, move, change status, expand/collapse, and show more—have keyboard shortcuts.
- **R14 — Markdown:** Descriptions, summaries, and comments accept Markdown and render it safely.
- **R15 — Shareable locations:** Users can link directly to a stream or to a specific ordering/filter/view state.
- **R16 — History:** Changes retain enough before/after information to support audit and targeted manual recovery.
- **R17 — External references:** Configured reference patterns can turn identifiers such as `BUG123` into safe links and rendered references.
- **R26 — Stream references:** Descriptions and comments can reference streams with a stable notation such as `@Stream:<number>`; rendered references expose the target stream and its current status, with future actions such as close/reopen subject to normal edit and conflict handling.
- **R18 — Edit awareness:** The UI indicates when another user is editing a stream or comment, while still allowing independent objects to be edited concurrently.
- **R24 — Lightweight attribution:** A user can provide an unvalidated display username at the root level, which is used as the default creator/commenter attribution and can be selected as an owner.
- **R25 — Separate roles:** The data distinguishes creator from owner/assignee; creating an item does not automatically make the creator its owner in all cases.
- **R19 — Default priority view:** At every hierarchy level, the default view shows open items first, grouped by priority, with closed items optionally included afterward.
- **R20 — View recipes:** The system supports deadline-first, chronological/most-recently-touched, and stale-open views, each optionally flat or hierarchy-preserving.
- **R21 — Pointer support:** Core navigation and editing actions work with mouse/pointer controls as well as keyboard shortcuts.
- **R31 — Mouse text copying:** Ordinary browser text selection and copying must work in stream summaries, descriptions, metadata, comments, and other readable UI content. A selection-release click must not rerender or otherwise clear the selection.
- **R22 — Insertion and movement:** Users can insert an item before, after, or beneath another item, and move existing items around using keyboard and/or pointer interactions.
- **R23 — Reordering usability:** After insertion or movement, the UI preserves context and makes the resulting position clear.
- **R30 — General move operation:** Users can pick up one stream or a contiguous block of sibling streams, navigate to a target, and place the selection before, after, or as a child of that target, or promote it one hierarchy level. The operation is atomic and revision-checked.
- **R27 — Safe deletion:** A user can confirm deletion of a focused stream or comment through a two-key command, or deletion of a completed visual block through `dv`, with revision-checked server-side deletion and visible conflicts for stale data. Deleting selected stream roots deletes their complete subtrees and comments atomically.
- **R28 — Comment editing:** A user can edit a focused comment by keyboard or pointer, with revision-checked saving and a visible conflict when the comment changed elsewhere.
- **R29 — Shared favorites dashboard:** A user can mark any stream as a favorite and view all favorite streams on a separate flat dashboard, with open streams first, closed/resolved streams afterward, and each group ordered by most recent update. Favorite rows show hierarchy breadcrumbs and can open the corresponding rooted hierarchy view.

## Non-functional

- **N1 — Simplicity:** Prefer a small number of moving parts and dependencies.
- **N2 — Performance:** Common list, read, create, and append operations should feel immediate on the intended internal network.
- **N3 — Durability:** A successful write must survive process restart and be included in the backup strategy.
- **N4 — Security:** Dependencies, build inputs, configuration, and exposed endpoints must be reviewable and minimized.
- **N5 — Operability:** Startup, health, logs, backup, restore, and upgrade procedures are documented.
- **N6 — Data portability:** The stored representation should be straightforward to inspect and export.

## Acceptance baseline

The first usable release should support creating and updating short notes, appending comments, compact hierarchy navigation, and safely handling two users editing the same object. Independent objects should remain editable concurrently. A deployment operator must be able to back up and restore the data using the deployment guide.
