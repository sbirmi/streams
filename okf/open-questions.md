# Open questions

These are intentionally unresolved and should be answered as implementation and usage become clearer.

- Which language, web framework, and datastore best fit the small-dependency requirement?
- Should the note body be plain text, Markdown, or another restricted format?
- What is the exact minimal primary UI layout and which fields appear collapsed versus expanded?
- Which keyboard shortcuts are defaults, and can users customize them?
- Are topic recipes data, static configuration, or a constrained combination of both?
- What exact statuses, tags, sorting, and search behavior are needed?
- In the default priority view, should items within a priority group sort by deadline or last update?
- In flat views, how should child items and their parent context be represented?
- Where should items without deadlines appear in the deadline-first view?
- How should priority/deadline, last-update, and stale-item views be saved and shared?
- Should “stale” be based on a fixed duration, a topic recipe, or per-stream metadata?
- Should comments be immutable, editable, or deletable? If mutable, how is history preserved?
- What is the retention and storage cost policy for before/after history?
- What does “owner” mean before individual accounts exist, and how should it be captured?
- Should anonymous users have a display label for conflict messages or audit context without introducing accounts?
- What note and comment size limits are appropriate?
- Is a per-note revision sufficient, or do we need finer-grained field revisions?
- What backup retention and recovery-time expectations apply?
- Which internal TLS, proxy, and network access controls are available in the target environment?
- What minimum observability is needed: request logs, change history, metrics, or all three?
- Which external-reference patterns and URL templates should be supported first?
- Should reference matching be case-sensitive, and how are ambiguous/malformed matches handled?
- When should authentication and authorization become mandatory?
