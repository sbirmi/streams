# Implementation TODO

This is the active implementation queue. Keep near-term work at the top. When an item is completed, move it to the **Completed** section at the bottom instead of deleting it. Add a short completion note or commit reference when useful.

## Next three

- [ ] **Scaffold the application shell.** Create the Python web app, project-local virtualenv/dependency setup, an automatic test command, configuration loading, basic server-rendered page, static CSS/vanilla JS layout, health endpoint, and logging initialization.
- [ ] **Build the SQLite data layer.** Add migrations/schema for bundles, streams, comments, history, and attribution; configure WAL mode and transactions; implement repository operations with revision checks and conflict results.
- [ ] **Build the first vertical slice.** Implement the default priority view plus create/edit/comment flows, safe server-side Markdown rendering, and enough vanilla JS for expand/collapse and inline refresh without a frontend framework.

## Later

- [ ] Add keyboard navigation and mouse actions for insertion, moving, and reordering.
- [ ] Add alternate deadline, chronological, and stale-open views.
- [ ] Add lightweight edit presence/soft-lock indicators.
- [ ] Add configurable external-reference recognition and scoped plugin rendering styles.
- [ ] Add backup/restore commands and deployment packaging.

## Completed
