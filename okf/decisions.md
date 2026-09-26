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
- **Decision:** Deleting a stream removes only that stream. Its direct children are promoted to root-level streams, and its comments are deleted with it. A leaf nested below a root does not affect root sibling ordering; its sibling-list `order_key` is never compared with root keys. When promotion or root deletion does require root reordering, every changed sibling receives a history snapshot so undo/redo can restore the complete logical ordering. The deletion requires the stream’s current revision. Delete history entries retain before snapshots for the stream, its deleted comments, and promoted children.
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

## D010 — Single stream status field

- **Status:** accepted for initial implementation
- **Decision:** Use one revision-checked `status` field with `open`, `resolved`, and `no_action` values. Resolved and no-action items share muted/crossed-out presentation; the status icon distinguishes them with a check mark versus a muted open circle. Duplicate context remains in descriptions or comments.
- **Reason:** The initial workflow needs to distinguish completed work from an intentional decision not to act without introducing separate lifecycle and resolution fields. More outcomes can be added if real usage requires them.

## D011 — Shared transaction history with linear undo/redo

- **Status:** accepted for initial transaction implementation
- **Decision:** Group each user-visible mutation, including atomic bulk operations, into a durable transaction envelope above object-level history. Support shared latest-transaction undo and redo using revision-checked semantic inverses. Undo and redo are recorded as new transactions. A new ordinary transaction after undo abandons the redo path for normal user navigation, while retaining the abandoned branch for backend inspection and a future searchable `/transactions` page. Use `tu` and `tr` as the proposed multi-key commands; a lone `t` only opens command feedback.
- **Reason:** A transaction is the correct unit for bulk move/delete/status actions and makes shared undo understandable without pretending that history was erased. Revision checks prevent undo from clobbering intervening work, while retained abandoned branches preserve debugging context without requiring a full branching-history UI in the first cut.

## D012 — Markdown bodies and declarative reference rendering

- **Status:** accepted for the enhancement
- **Decision:** Store descriptions and comments as raw Markdown; keep stream summaries plain text. Render Markdown on the server at read/display time with a maintained parser and sanitizer. Existing descriptions/comments open rendered-first in the modal, with an edit toggle for the original Markdown. Ordinary hyperlinks are clickable. Built-in stream and comment references, plus configured external patterns, use declarative reference rules that produce validated links. Streams and comments provide copy-link and copy-reference affordances; copied references include their type prefix.
- **Constraints:** No external CSS or JavaScript is introduced. Raw HTML, unsafe URL schemes, arbitrary plugin HTML/JavaScript, and substitutions inside existing links or code are disallowed. History and concurrency operate on raw source text, not rendered HTML.
- **Reason:** Rich display is useful for full descriptions/comments while plain summaries preserve compact navigation. A shared server pipeline keeps rendering consistent and makes future integrations reviewable and safe.

## D013 — Compact rendered-first modal actions

- **Status:** accepted for initial implementation
- **Decision:** Existing stream and comment dialogs place Copy ref, Copy link, and Edit in that order, focus Edit on open, and omit a redundant heading close button. Stream summaries and metadata remain editable by default; only the Markdown description is rendered-first and switches to source editing through Edit. Comments remain rendered-first and switch their Markdown body to editing through Edit.
- **Reason:** The common modal action is editing the meaningful plain-text fields, while Markdown source editing is a deliberate mode change. Removing duplicate close affordances keeps keyboard focus and the heading compact.

## D014 — Hierarchy-based zoom out

- **Status:** accepted for initial implementation
- **Decision:** `Z Backspace` always zooms from the current rooted stream to its actual `parent_stream_id`, or to `Index` when that parent is absent. This applies regardless of whether the root was entered interactively, loaded from a deep link, or displayed through a flat view such as Deadline. At `Index`, the command is a no-op.
- **Reason:** Zooming out should have one predictable hierarchy meaning independent of navigation history or presentation ordering.

## D015 — Clickable complete rooted-view breadcrumbs

- **Status:** accepted for initial implementation
- **Decision:** The header displays the complete hierarchy from `Index` through the current rooted stream, including ancestors not present in the navigation stack. Index and ancestor segments re-root the current view at that stream while preserving the active view/sort mode; the current stream is a non-interactive `aria-current="page"` label.
- **Reason:** Deep links and one-shot navigation should expose the same orientation and direct path back to any ancestor.
