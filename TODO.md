# Implementation TODO

This is the active implementation queue. Keep near-term work at the top. When an item is completed, move it to the **Completed** section at the bottom instead of deleting it. Add a short completion note or commit reference when useful.

## Next three

- [ ] **Review and settle the UI prototype.** Use `prototype/` to decide the primary hierarchy, density, controls, comment presentation, and mouse/keyboard interaction before building the production UI.
- [ ] **Build the first vertical slice.** Implement the default priority view plus create/edit/comment flows, safe server-side Markdown rendering, and enough vanilla JS for expand/collapse and inline refresh without a frontend framework.
- [ ] Add keyboard navigation and mouse actions for insertion, moving, and reordering.
- [ ] Add alternate deadline, chronological, and stale-open views.
- [ ] Persist view, filter, rooted-view, expansion, and other UI preferences in browser storage/cookies where useful.

## Later

- [ ] Add lightweight edit presence/soft-lock indicators.
- [ ] Add configurable external-reference recognition and scoped plugin rendering styles.
- [ ] Add backup/restore commands and deployment packaging.

## Completed

- [x] **Build comment editing.** Added keyboard and pointer comment editing, revision-checked PATCH saves, conflict-preserving modal behavior, and focus restoration documentation/tests.

- [x] **Scaffold the application shell.** Added the Python/Flask app, project-local virtualenv workflow, pinned dependency and lock files, automatic test command, configuration loading, server-rendered page, static CSS/vanilla JS layout, health endpoint, and logging initialization. Verified with `./scripts/test` (2 tests passing).
- [x] **Build the SQLite data layer.** Added ordered SQL migrations, WAL/foreign-key setup, repository operations for bundles/streams/comments, before/after history, independent revisions, and stale-write conflict results. Verified with `./scripts/test` (7 tests passing).
- [x] **Build the deletion workflow.** Added revision-checked stream/comment deletes, confirmation UI for `ds`/`dc`, accessible stream-row deletion, ordered child promotion, delete audit history, and stale-delete tests/documentation.
- [x] **Make insertion commands explicit and rooted-view safe.** Replaced single-key insertion with `ip`/`in`/`ic`, blocked invisible sibling/root mutations in rooted views, and added rooted-context API validation.
- [x] **Make keyboard configuration authoritative.** Moved all implemented keyboard actions, aliases, and sequences into `config/shortcuts.yaml`; the server validates the complete map and the browser dispatches only configured bindings.
