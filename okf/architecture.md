# Initial architecture

Status: proposed.

## Shape

Start with a single web application process backed by one durable datastore. Keep the browser client thin and expose a small HTTP API. A reverse proxy or private-network gateway may terminate transport security and provide access controls appropriate to the deployment.

```text
browser(s) -> private network / reverse proxy -> web app -> durable datastore
                                                   |
                                                   +-> structured logs
```

The first implementation should avoid requiring a queue, search cluster, cache, or separate frontend deployment unless measurements show a need.

## Domain model (initial)

The working domain vocabulary is **topic**, **stream**, and **comment**. “Issue” is a useful UI label for a stream in an issue-oriented topic; it should not force every topic into an issue tracker shape.

### Stream

- `stream_id`
- summary/title
- Markdown description
- owners (initially a placeholder string/list, not authenticated identities)
- priority, with P0 as highest priority
- snooze-until date
- deadline
- creation, last-update, and close timestamps
- close status such as resolved, no-action-needed, or duplicate
- optional parent stream identifier
- tags/labels
- revision/version for optimistic concurrency
- ordered comments/updates

### Comment

- `comment_id`
- stream identifier
- Markdown body
- placeholder owner string
- creation and last-update timestamps
- optional sticky-note flag

Comments are append-oriented. A comment’s order can be derived from creation/order timestamps; explicit `prev_comment_id` and `next_comment_id` links are not part of the initial model unless a later requirement needs them.

### History

Mutations should produce history entries with object, actor placeholder, timestamp, changed fields, and before/after values. History must be usable for audit and targeted recovery without requiring every object to expose its full history in the primary view.

### Topics and recipes

A topic groups streams and may carry a presentation recipe: default columns/fields, hierarchy labels, ordering, filters, and keyboard behavior. Recipes should be configuration/data-driven where practical, but the first implementation should avoid a general-purpose scripting language.

## API expectations

Use resource-oriented endpoints with explicit version or revision preconditions on mutating stream/comment operations. A write that supplies an old revision should return a conflict response and the current representation, rather than overwriting it. Deep links should use stable identifiers and encode view/filter/sort state in a bookmarkable form.

External-reference recognition and rendering is described in [Integrations](integrations.md). Markdown rendering must use an allowlisted/sanitized renderer.

The exact framework, database, wire format, and deployment packaging remain open until implementation begins; record the choice in `decisions.md`.
