# Decisions

## D001 — Documentation is the source of truth

- **Status:** accepted
- **Decision:** Maintain project knowledge, requirements, design, operations, and decisions in this `okf/` bundle. Update it alongside code and configuration.
- **Reason:** The project is expected to evolve through discussion, and implementation should not become the only record of behavior.

## D002 — Trusted-network, shared-access initial model

- **Status:** accepted for initial scope
- **Decision:** Do not require individual accounts initially; network URL access implies trusted read/write access.
- **Reason:** The service is intended for a secure internal network and should remain simple.
- **Constraint:** This is not approval for public exposure. The security model must change before that.

## D003 — Optimistic concurrency for note edits

- **Status:** proposed baseline
- **Decision:** Use revision-checked writes for whole-note edits and atomic append operations for comments/updates.
- **Reason:** It prevents silent clobbering while keeping the application simple and avoiding locks.

## D004 — Flask, SQLite, and a thin browser client for the initial implementation

- **Status:** accepted for initial implementation
- **Decision:** Use Flask with Python, SQLite through `sqlite3`, server-rendered HTML, vanilla JavaScript, and project-owned CSS. Run application and tests through the project-local virtualenv.
- **Reason:** This keeps the first implementation small, fast to start, and easy to inspect while leaving room for targeted client-side behavior.

## D005 — SQL migrations and repository-owned transactions

- **Status:** accepted for initial implementation
- **Decision:** Keep schema changes as ordered SQL migrations. A repository layer owns SQL and short SQLite transactions; routes and future services do not manage raw connections directly.
- **Reason:** This keeps the data boundary explicit, makes upgrades reviewable, and supports revision checks/history without coupling the UI to SQLite details.

## D006 — Stream deletion promotes children and preserves audit history

- **Status:** accepted for initial implementation
- **Decision:** Deleting a stream removes only that stream. Its direct children are promoted to root-level streams, and its comments are deleted with it. The deletion requires the stream’s current revision. Delete history entries retain before snapshots for the stream, its deleted comments, and promoted children.
- **Reason:** The existing foreign-key model uses `ON DELETE SET NULL` for `parent_stream_id` and `ON DELETE CASCADE` for comments. Promoting children avoids silently deleting a potentially large subtree while preserving the established hierarchy semantics.

## D007 — Explicit insertion commands and rooted-view safety

- **Status:** accepted for initial implementation
- **Decision:** Use `ip`, `in`, and `ic` for insertion before, next, and child. A lone `i` is only a pending command. In a rooted view, sibling insertion at the focused root and toolbar root insertion are blocked in the client. The API accepts optional `root_stream_id` context and validates supplied anchors against that subtree.
- **Reason:** Single-key insertion made the destination ambiguous, and creating a sibling of a rooted view made an invisible mutation. The current stateless trusted-network API cannot know a browser’s active rooted view when the optional context is omitted, so this is deliberately documented as view safety rather than authorization.

## D008 — Complete shortcut configuration as the keyboard source of truth

- **Decision:** Declare every implemented keyboard action in `config/shortcuts.yaml` using a dependency-free flat action-to-binding-list format. Bindings may be aliases (`j`, `ArrowDown`) or sequences (`ds`, `Z Enter`, `ip`). The server validates that all known actions are present and rejects invalid or incomplete files; the browser dispatches only bindings returned by `/api/shortcuts`.
- **Reason:** A partial insertion-only configuration left the effective keyboard API split between configuration and hardcoded JavaScript, making customization misleading and unsafe to reason about. Strict startup failure is preferable to silently accepting undocumented defaults.
## Numeric sibling order keys

Streams preserve hierarchy order with a server-controlled integer `order_key` for each sibling list. New items use gaps of 1000, middle insertion uses a midpoint, and a sibling list is resequenced only when no integer gap remains. This keeps common insertion writes small while retaining a simple SQLite sort. The value is informational in the modal and is not an editable API field.

## Shareable rooted-view URLs

Shareable navigation state uses stable stream/comment identifiers in query parameters: `root`, `view`, and typed `focus`. The index is represented by omitting `root`. Client-local presentation state, including expansion and scroll preferences, is stored separately per bundle/root context, independent of sort mode, so different users can retain their own layout without making links noisy or user-specific. Restoring an explicit or saved focus expands only the target’s required ancestor chain.

## Shared favorites dashboard

Favorites are a boolean property on streams and are shared workspace state under the trusted-network, no-account model. They are presented at `/dashboard` as a flat dashboard rather than as a tree ordering mode. Open favorites sort before closed/resolved favorites, with newest `updated_at` first within each group; rows retain hierarchy breadcrumbs for navigation back to rooted views.

## D009 — General move mode

- **Status:** accepted for initial implementation
- **Decision:** Move one stream or a contiguous sibling block through a single move mode. `m` picks up the selection, navigation chooses a target, and `p`, `n`, or `c` places it before, after, or as a child. `u` promotes it after its current parent. The command HUD describes keys with their actions; separate `>>`/`<<` movement commands are not used.
- **Reason:** One target-and-placement interaction covers local correction, cross-branch movement, promotion, and blocks without requiring users to memorize a command for each source/target combination. Copying is deferred until subtree/comment/history semantics are needed.
