# Concurrent editing model

The application has shared, anonymous-by-default access. Concurrent edits are therefore a normal case, not an exceptional one.

## Initial strategy: optimistic concurrency

Each independently editable object (stream, comment, and eventually other editable entities) has a monotonically increasing revision. When a client reads or starts editing an object, it remembers revision `N`. A write must include `N` as a precondition:

1. Server accepts the write only if the stored revision is still `N`.
2. On success, the server stores the change as revision `N+1`.
3. If the stored revision is greater than `N`, the server rejects the write as a conflict and returns the current object.
4. The client shows the user their draft and the newer server version, with a retry/merge flow.

This prevents silent last-write-wins clobbering without requiring locks or user accounts. Editing a stream should not block someone else from editing a different stream or comment.

Deletion uses the same revision precondition as editing. A stale stream or comment delete returns the normal conflict response with the current representation; it never removes newer data. Successful deletions retain before snapshots in history, and stream deletion records the promotion of direct children as separate stream changes.

Undo and redo use the same optimistic concurrency principle. Applying an inverse or replaying a transaction must verify all affected object revisions and must be atomic. If any affected object has changed since the original transaction or since the last undo/redo step, the whole operation is rejected with a visible conflict rather than partially applying. The original transaction remains in history, and the failed attempt must not mutate the data.

## UI edit awareness

The UI should show a lightweight “being edited” indicator when another browser has an active edit session for the same object. This is an advisory presence/soft-lock signal, not the correctness mechanism: it may expire, disappear, or be stale, and the revision check remains authoritative. The initial implementation can use short-lived heartbeats or another simple presence mechanism; it does not need full real-time collaboration.

## Append operations

Adding a comment/update is an atomic append against the stream. It does not require the editor to submit the entire stream body, so unrelated comment additions do not conflict unnecessarily. Comments have their own revisions for later edits, while the parent stream’s revision remains independent.

## Future options

If conflicts are frequent, consider field-level updates or an explicit merge editor. Do not introduce a complex CRDT or real-time collaboration protocol until actual usage justifies it.
