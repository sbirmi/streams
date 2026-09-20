# Initial architecture

Status: proposed.

## Proposed implementation baseline

- **Backend:** Python 3 with Flask. Keep the HTTP/API layer thin and use server-rendered HTML where that improves startup and responsiveness.
- **Storage:** SQLite through Python’s built-in `sqlite3` module. It requires no separate database service and is appropriate for the expected small, trusted-network deployment. Enable WAL mode and use short transactions; SQLite still permits only one simultaneous write transaction, so optimistic object revisions remain necessary.
- **Frontend:** Server-rendered HTML, one small vanilla JavaScript module, and project-owned CSS. Avoid a frontend framework and build pipeline until the interaction model proves it needs one.
- **Markdown:** Render Markdown on the server with a maintained parser, enable only the required extensions, and sanitize/allowlist the resulting HTML before storing or serving it. Do not implement a Markdown parser or HTML sanitizer from scratch.

Flask is selected for the initial implementation. Any additional framework or package should be pinned, reviewed, and recorded before implementation.

## Development environment

The application and its tests must run inside a project-local Python virtualenv. The repository provides scripts that create the virtualenv automatically, using the system `virtualenv` tool when available and falling back to `python3 -m venv`, then install the pinned requirements and run commands through that environment. Tests must not depend on globally installed Python packages or tools.

## Shape

Start with a single web application process backed by one durable datastore. Keep the browser client thin and expose a small HTTP API. A reverse proxy or private-network gateway may terminate transport security and provide access controls appropriate to the deployment.

```text
browser(s) -> private network / reverse proxy -> web app -> durable datastore
                                                   |
                                                   +-> structured logs
```

The first implementation should avoid requiring a queue, search cluster, cache, or separate frontend deployment unless measurements show a need.

## High-level request flow

```text
browser
  -> reverse proxy / internal TLS boundary
  -> Flask routes
  -> request validation and username/session context
  -> application services
       -> repositories / SQLite transactions
       -> Markdown and reference rendering
       -> history and presence events
  -> HTML response or small JSON response
  -> vanilla JavaScript updates the affected region
```

Keep these responsibilities separate even if they initially live in one Python process. Routes should translate HTTP requests; application services should enforce product rules; repositories should own SQL and transaction boundaries; renderers should own Markdown/reference output.

## Frontend boundary

The first UI should be server-rendered HTML with project-owned CSS and a small vanilla JavaScript layer for expansion, keyboard actions, inline editing, optimistic updates, presence indicators, and targeted refreshes. The browser should not need a large client-side state framework or a full client-side copy of the database.

## Logging and observability

Use Python’s standard logging facilities behind a small application logging wrapper. Emit structured, line-oriented events where practical so they remain readable locally and can later be ingested by a log collector.

At minimum, log:

- application startup/shutdown and selected configuration (never secrets);
- request method, route name, status, duration, and request/correlation ID;
- create/update/close/comment/conflict events with object IDs and actor display name where useful;
- database lock, migration, backup, restore, and unhandled-error events;
- presence/soft-lock failures at debug or warning level as appropriate.

Do not log Markdown bodies, full usernames, cookies, authorization headers, secrets, or arbitrary request payloads by default. Note contents and history remain in the datastore, not the operational log. Logging must not become a second copy of private user data.

The deployment should define log destination, retention, rotation, time format, and a way to correlate a user-visible error with its server-side event.

## Domain model (initial)

The working domain vocabulary is **topic**, **stream**, and **comment**. “Issue” is a useful UI label for a stream in an issue-oriented topic; it should not force every topic into an issue tracker shape.

### Stream

- `stream_id`
- summary/title
- Markdown description
- owners/assignees (initially placeholder string/list values, not authenticated identities)
- creator attribution (separate from owner/assignee)
- optional priority, with P0 as highest priority when set
- snooze-until date
- deadline
- creation, last-update, and close timestamps
- close status such as resolved, no-action-needed, or duplicate
- optional parent stream identifier
- favorite flag, shared across the workspace
- tags/labels
- revision/version for optimistic concurrency
- ordered comments/updates

### Comment

- `comment_id`
- stream identifier
- Markdown body
- creator attribution (separate from any owner/assignee)
- creation and last-update timestamps
- optional sticky-note flag

Comments are append-oriented. A comment’s order can be derived from creation/order timestamps; explicit `prev_comment_id` and `next_comment_id` links are not part of the initial model unless a later requirement needs them.

### History

Mutations should produce history entries with object, actor placeholder, timestamp, changed fields, and before/after values. History must be usable for audit and targeted recovery without requiring every object to expose its full history in the primary view.

The current username is client-provided, unvalidated display attribution. It must not be treated as proof of identity or used for authorization.

### Bundles and topics

A bundle groups related streams, such as todos, recipes, or side projects. A topic is a possible label for a bundle or grouping within one; the exact vocabulary remains open. These are generic containers, not domain-specific schemas. A recipe is simply a user’s content organized with streams and child streams, with no special recipe support required.

Future tree model: the underlying data may be one large tree rather than a set of independent bundle-owned trees. In that model, navigating bundles is itself tree navigation: the root tree is the starting view, and choosing a node as a bundle opens that node’s subtree as the bundle view. This is recorded as a design direction only; the initial implementation should preserve enough stable parent and identity information to support that evolution.

## SQLite data layer

The database is migrated on application startup from ordered SQL files in `migrations/`. The repository layer owns SQL statements and exposes application-level operations rather than leaking connections into routes. Each write uses a short `BEGIN IMMEDIATE` transaction, foreign keys are enabled, and file-backed databases use WAL mode with a busy timeout.

The initial schema contains `bundles`, `streams`, `comments`, `history`, and `schema_migrations`. Stream and comment revisions are independent. History stores actor attribution, changed fields, and before/after JSON snapshots. Each stream has a server-controlled numeric `order_key` scoped to its sibling list. New sibling keys start at gaps of 1000; insertion uses the midpoint between neighboring keys and resequences that sibling list with the same gaps when no integer space remains. Hierarchy-preserving views order children by `order_key`; alternate view sorting must not change it. The key is shown read-only in the stream modal for troubleshooting, but is not an editable API field.

## API expectations

Use resource-oriented endpoints with explicit version or revision preconditions on mutating stream/comment operations. A write that supplies an old revision should return a conflict response and the current representation, rather than overwriting it. Deep links should use stable identifiers and encode rooted-view, focus, filter, and view/sort state in a bookmarkable form. Shareable URL state is separate from client-local presentation preferences such as expansion and scroll position. Client-local hierarchy state is keyed by bundle and root, not sort mode; restoring a target expands only the minimum ancestor chain needed to reveal it.

The initial JSON API exposes bundle listing/creation, bundle stream listing/creation, stream read/update/delete, and comment listing/creation/update/delete under `/api/`. Stream reads and bundle stream listings include comments for the first UI slice. Mutating stream/comment requests include an `actor` display name; stream updates and deletes include a `revision` precondition. Stream owners and tags are stored as ordered lists of trimmed, non-empty strings, and deadlines use the date-only `YYYY-MM-DD` representation (empty values become null). The modal converts comma/whitespace-separated tag input to that list before sending it. Favorite changes are revision-checked stream updates and are shared workspace state. A stream delete promotes direct children to roots and deletes its comments. Delete operations retain before snapshots in history and return HTTP 409 with the current object when its revision is stale.

The `/dashboard` page is a separate flat favorite-stream destination, not a tree view option. It reuses the application header and view bar, shows a favorite count, and orders favorites with open streams first, then closed/resolved streams, newest `updated_at` first within each group. Rows include current hierarchy breadcrumbs and links back to rooted hierarchy views.

The move endpoint accepts a list of stream IDs with their expected revisions, a target stream, and placement (`before`, `after`, or `child`). It can move a contiguous sibling block while preserving its order; the `promote` UI action is represented as placement after the current parent. The repository validates bundle membership, ancestor cycles, rooted-view boundaries, and stale revisions in one transaction. All affected sibling order changes and moved-parent changes receive revisions and history entries; a conflict or validation failure leaves the tree unchanged.

Rooted-view state currently lives in the browser and is not part of the authenticated/server session model. Create requests may include `root_stream_id`; when present, the repository rejects sibling or child insertion anchors outside that rooted subtree and rejects siblings of the root itself. Direct API callers that omit this optional UI context can still perform ordinary bundle-level insertion, consistent with the trusted-network product assumption; this is a view-safety guard, not an authorization boundary.

External-reference recognition and rendering is described in [Integrations](integrations.md). Markdown rendering must use an allowlisted/sanitized renderer.

The wire format and deployment packaging remain open; record future choices in `decisions.md`.
