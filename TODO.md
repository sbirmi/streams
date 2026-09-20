# Implementation TODO

This is the active implementation queue. Keep near-term work at the top. When an item is completed, move it to the **Completed** section at the bottom instead of deleting it. Add a short completion note or commit reference when useful.

## Next three

- [ ] **Review and settle the UI prototype.** Use `prototype/` to decide the primary hierarchy, density, controls, comment presentation, and mouse/keyboard interaction before building the production UI.
- [ ] **Build the first vertical slice.** Implement the default priority view plus create/edit/comment flows, safe server-side Markdown rendering, and enough vanilla JS for expand/collapse and inline refresh without a frontend framework.
- [ ] Add keyboard navigation and mouse actions for insertion, moving, and reordering.
- [ ] Add alternate deadline, chronological, and stale-open views.
- [ ] Persist view, filter, and other remaining UI preferences in browser storage/cookies where useful.

## Later

- [ ] Build the searchable `/transactions` history explorer with retained abandoned branches.
- [ ] Add lightweight edit presence/soft-lock indicators.
- [ ] Add configurable external-reference recognition and scoped plugin rendering styles.
- [ ] Add backup/restore commands and deployment packaging.

## Completed

- [x] **Add shared transaction undo/redo.** Added durable transaction envelopes above object history, atomic revision-checked undo/redo for existing mutations including bulk operations, retained abandoned redo branches, `tu`/`tr` shortcuts, affected-stream focus metadata, and compact UI feedback. Verified with `./scripts/test` (49 tests passing).

- [x] **Implement general stream move mode.** Added atomic revision-checked before/after/child moves, promotion, contiguous sibling blocks, keyboard/pointer entry, and descriptive command HUD hints.

- [x] **Add shareable rooted-view permalinks.** Added URL-driven root/view/stream-or-comment focus state, Copy link support, and per-root/view client presentation persistence.
- [x] **Remember rooted hierarchy state.** Persisted expansion and focus per bundle/root, independent of sort mode, with minimum ancestor expansion for restored focus targets.
- [x] **Add shared favorites dashboard.** Added the revision-checked stream favorite property and separate flat `/dashboard` destination with breadcrumbs and rooted-view navigation.
- [x] **Add order-preserving sibling keys.** Replaced dense position handling with server-controlled numeric `order_key` gaps, midpoint insertion, migration/resequencing, and a read-only modal display.

- [x] **Add stream owners and deadlines.** Added normalized owner/deadline persistence, create/edit modal fields, compact row metadata, validation, and tests.
- [x] **Add stream tags to the modal.** Added compact create/edit input with comma/whitespace parsing, ordered normalization, persistence tests, and UI documentation.

- [x] **Build comment editing.** Added keyboard and pointer comment editing, revision-checked PATCH saves, conflict-preserving modal behavior, and focus restoration documentation/tests.

- [x] **Scaffold the application shell.** Added the Python/Flask app, project-local virtualenv workflow, pinned dependency and lock files, automatic test command, configuration loading, server-rendered page, static CSS/vanilla JS layout, health endpoint, and logging initialization. Verified with `./scripts/test` (2 tests passing).
- [x] **Build the SQLite data layer.** Added ordered SQL migrations, WAL/foreign-key setup, repository operations for bundles/streams/comments, before/after history, independent revisions, and stale-write conflict results. Verified with `./scripts/test` (7 tests passing).
- [x] **Build the deletion workflow.** Added revision-checked stream/comment deletes, confirmation UI for `ds`/`dc`, accessible stream-row deletion, ordered child promotion, delete audit history, and stale-delete tests/documentation.
- [x] **Make insertion commands explicit and rooted-view safe.** Replaced single-key insertion with `ip`/`in`/`ic`, blocked invisible sibling/root mutations in rooted views, and added rooted-context API validation.
- [x] **Make keyboard configuration authoritative.** Moved all implemented keyboard actions, aliases, and sequences into `config/shortcuts.yaml`; the server validates the complete map and the browser dispatches only configured bindings.
