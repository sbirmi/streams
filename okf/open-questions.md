# Open questions

These are intentionally unresolved and should be answered as implementation and usage become clearer.

- Which language, web framework, and datastore best fit the small-dependency requirement?
- Should the first backend use Flask or an even thinner WSGI/ASGI layer?
- Which Markdown parser and sanitizer combination gives the smallest acceptable reviewed dependency surface?
- Should rendered Markdown be rendered on every read or cached with an invalidation strategy, while retaining raw source as canonical?
- What exact comment-reference notation should complement `Stream:<ID>` (for example `Comment:<ID>` or `@Comment:<ID>`), and should copied IDs include a type prefix?
- What is the exact minimal primary UI layout and which fields appear collapsed versus expanded?
- Which keyboard shortcuts are defaults, and can users customize them?
- Which insertion/move controls are always visible, and which belong in context menus?
- Should pointer reordering use drag-and-drop, explicit move commands, or both?
- How should reordering interact with different view sorts: manual hierarchy order, view-derived order, or both?
- What is the clearest name for a top-level grouping: bundle, collection, notebook, workspace, or topic?
- Should all data be represented as one global tree, with a bundle acting as a view rooted at a chosen node and bundle navigation treated as tree navigation?
- What exact statuses, tags, sorting, and search behavior are needed?
- In the default priority view, should items within a priority group sort by deadline or last update?
- In flat views, how should child items and their parent context be represented?
- Where should items without deadlines appear in the deadline-first view?
- How should priority/deadline, last-update, and stale-item views be saved and shared?
- Should “stale” be based on a fixed duration, a topic recipe, or per-stream metadata?
- Should comments be immutable, editable, or deletable? If mutable, how is history preserved?
- What is the retention and storage cost policy for before/after history?
- What does “owner” mean before individual accounts exist, and how should it be captured?
- Should the current username persist in browser storage, be entered per session, or both?
- How should users correct or distinguish duplicate/mistyped display usernames?
- Should anonymous users have a display label for conflict messages or audit context without introducing accounts?
- What note and comment size limits are appropriate?
- Is a per-note revision sufficient, or do we need finer-grained field revisions?
- What backup retention and recovery-time expectations apply?
- Which internal TLS, proxy, and network access controls are available in the target environment?
- What minimum observability is needed: request logs, change history, metrics, or all three?
- Which external-reference patterns and URL templates should be supported first?
- Should reference matching be case-sensitive, and how are ambiguous/malformed matches handled?
- What exact declarative plugin schema, rule ordering, collision behavior, host allowlist, and URL-encoding rules should apply to external patterns?
- Should copy-link open a rooted stream view, focus a comment, or use a single canonical object URL for each object type?
- When should authentication and authorization become mandatory?
